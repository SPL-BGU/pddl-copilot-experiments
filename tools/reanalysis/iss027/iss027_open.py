"""ISS-027 open-model check (read-only). Run with the experiments venv from the repo root."""
import json, re, sys, os, tempfile
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path("/Users/omereliyahu/personal/pddl-copilot-experiments")
sys.path.insert(0, str(REPO))
sys.path.insert(0, "/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-validator/server")
os.environ.setdefault("PDDL_TEMP_DIR", tempfile.mkdtemp())
from pddl_eval.scoring import SolveResponse, _safe_pydantic_validate, extract_plan_lines, strip_leaked_channel_prefix
from tools.e2e_regrade import extract_plan_lines_tolerant
from tools.delivered_rerun.grade import solve_plan as rerun_solve_plan
import validator_server as vs

UPPER = {}  # (domain, problem) -> set of declared names with upper case (lowercased form -> declared)
def declared_upper(dom, prob):
    d = REPO/"domains"
    names = {}
    for f in [*(d.rglob(f"{dom}/domain.pddl")), *(d.rglob(f"{dom}/{prob}.pddl"))]:
        t = re.sub(r";[^\n]*", "", f.read_text())
        for tok in re.findall(r"[A-Za-z][\w\-]*", t):
            if any(c.isupper() for c in tok): names[tok.lower()] = tok
    return names
AFFECTED_P = {("satellite", p) for p in ("p02","p03","p04","p05")}
def affected(dom, prob):
    return (dom, prob) in AFFECTED_P or dom == "pogo_stick"

FIX = {}
def fixture(dom, prob):
    if (dom, prob) not in FIX:
        base = next((REPO/"domains").rglob(f"{dom}/domain.pddl")).parent
        FIX[(dom, prob)] = ((base/"domain.pddl").read_text(), (base/f"{prob}.pddl").read_text())
    return FIX[(dom, prob)]

CACHE = {}
def pyval(dom, prob, lines):
    k = (dom, prob, tuple(lines))
    if k not in CACHE:
        if not lines:
            CACHE[k] = (False, "empty"); return CACHE[k]
        dt, pt = fixture(dom, prob)
        r = vs.validate_plan(dt, pt, "\n".join(lines), verbose=False)
        if r.get("error"): CACHE[k] = (None, r.get("message","")[:200])
        else: CACHE[k] = (bool(r["valid"]), r.get("report","")[:400])
    return CACHE[k]

def uses_upper(lines, names):
    """plan writes a declared upper-case name in a non-lower case"""
    toks = set()
    for ln in lines:
        toks |= set(re.findall(r"[A-Za-z][\w\-]*", ln))
    return any(t.lower() in names and t != t.lower() for t in toks)

def load(f):
    rows = {}
    bad = 0
    with open(f, errors="replace") as fh:
        for ln in fh:
            if not ln.strip(): continue
            try: o = json.loads(ln)
            except json.JSONDecodeError: bad += 1; continue
            rows[tuple(o["key"])] = o["result"]
    return rows, bad

def cap_of(rows):
    lens = Counter(len(r.get("response") or "") for r in rows.values())
    for c in (500, 16384, 65536):
        if lens.get(c, 0) >= 3: return c
    return None

out = []
notdecl_tc = Counter()
for corpus in ("sweep5v2-live", "sweep6-live", "delivered-rerun"):
    for cell in sorted((REPO/"results"/corpus).iterdir()):
        tf = cell/"trials.jsonl"
        if not tf.exists(): continue
        rows, bad = load(tf)
        cap = cap_of(rows)
        anon = corpus == "sweep6-live"
        stats = Counter()
        for k, r in rows.items():
            dom, prob = r["domain_name"], r["problem_name"]
            if not affected(dom, prob) or r.get("infra_failure"): continue
            # any tool call whose result says "not declared" (any task)
            for tc in r.get("tool_calls") or []:
                res = str(tc.get("result", ""))
                if "not declared" in res:
                    notdecl_tc[(corpus, cell.name, r["task"], tc.get("name"))] += 1
            if r["task"] != "solve": continue
            stats["n"] += 1
            if anon:  # renamed tree: no upper-case names exist
                continue
            names = declared_upper(dom, prob)
            resp = r.get("response") or ""
            at_cap = cap is not None and len(resp) == cap
            if not r["with_tools"]:
                # ONLINE grade (harness check_success, unaided)
                if at_cap:
                    stats["online_at_cap"] += 1
                    vis = strip_leaked_channel_prefix(resp).lstrip()
                    if any(n != n.lower() and n in vis for n in names.values()) and not r["success"]:
                        stats["online_at_cap_fail_visible_upper"] += 1
                        if vis.startswith("{") or vis.startswith("```json"):
                            stats["online_at_cap_fail_visible_upper_json"] += 1
                    # cannot regrade
                else:
                    parsed = _safe_pydantic_validate(SolveResponse, resp)
                    lines = parsed.plan if parsed else extract_plan_lines(resp)
                    v, rep = pyval(dom, prob, lines)
                    stats["online_regraded"] += 1
                    stats["online_reproduces_stored"] += (bool(v) == bool(r["success"]))
                    if bool(v) != bool(r["success"]):
                        stats["online_mismatch"] += 1
                    if uses_upper(lines, names):
                        stats["online_plan_uses_upper"] += 1
                        if not r["success"]:
                            stats["online_upper_failed"] += 1
                            if "not declared" in rep: stats["online_upper_failed_notdeclared"] += 1
                            vl, _ = pyval(dom, prob, [x.lower() for x in lines])
                            if vl:
                                stats["online_would_flip"] += 1
                                out.append((corpus, cell.name, "unaided-online", k, rep[:120]))
                # DELIVERED grade for the rerun Part C (tools/delivered_rerun/grade.py)
                if corpus == "delivered-rerun":
                    lines, mode = rerun_solve_plan(resp)
                    v, rep = pyval(dom, prob, lines)
                    if uses_upper(lines, names):
                        stats["dlv_plan_uses_upper"] += 1
                        if not v:
                            vl, _ = pyval(dom, prob, [x.lower() for x in lines])
                            stats["dlv_upper_failed"] += 1
                            if vl:
                                stats["dlv_would_flip"] += 1
                                out.append((corpus, cell.name, "unaided-delivered", k, rep[:120]))
            else:
                # tool arm, online = planner plans
                for tc in r.get("tool_calls") or []:
                    if tc.get("name") in ("classic_planner", "numeric_planner"):
                        res = str(tc.get("result", ""))
                        if any(n in res for n in names.values() if n != n.lower()):
                            stats["planner_result_has_upper"] += 1
                # delivered
                if at_cap or not resp.strip():
                    stats["dlv_cap_or_empty"] += 1
                    continue
                if corpus == "delivered-rerun":
                    lines, mode = rerun_solve_plan(resp)
                else:
                    parsed = _safe_pydantic_validate(SolveResponse, resp)
                    lines = parsed.plan if parsed else extract_plan_lines_tolerant(resp)[0]
                v, rep = pyval(dom, prob, lines)
                if uses_upper(lines, names):
                    stats["dlv_plan_uses_upper"] += 1
                    if not v:
                        stats["dlv_upper_failed"] += 1
                        if "not declared" in rep: stats["dlv_upper_failed_notdeclared"] += 1
                        vl, _ = pyval(dom, prob, [x.lower() for x in lines])
                        if vl:
                            stats["dlv_would_flip"] += 1
                            out.append((corpus, cell.name, "tools-delivered", k, rep[:120]))
        print(corpus, cell.name, "cap", cap, "torn", bad, dict(stats), flush=True)
print("\nnot-declared tool results on affected problems:", dict(notdecl_tc))
print("\nFLIPS:")
for o in out: print(o)
json.dump([list(map(str, o)) for o in out], open(Path(__file__).parent/"iss027_flips.json", "w"), indent=1)
