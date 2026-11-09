"""Shared helpers of the ISS-027 checks (`iss027_unaided.py`, `iss027_replay.py`).

ISS-027 (development/OPEN_ISSUES.md): the plan grader, pyval 0.1.5 behind the
pddl-validator plugin, looks plan names up case-sensitively, while PDDL names are
case-insensitive. unified_planning lower-cases the domain and the problem on read,
so a plan step that writes a name with the fixture's own capitals (satellite
`Star0`, pogo_stick `CRAFT_PLANK`) is rejected as "not declared".

Most of this module is pure (no results data, no validator) so that
tests/test_iss027.py can check it. `load_validator` and `environment` are the
only parts that touch the sibling repo or the installed packages; both are
read-only.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"

# pyval release the frozen corpora were graded with. 0.1.6 (SPL-BGU/pyvalidator #3)
# folds case, so under it every as-is replay already passes and no flip can be seen.
PYVAL_EXPECTED = "0.1.5"

# Stored-answer cap (`RESPONSE_SNAPSHOT_LEN`, pddl_eval/runner.py) each corpus was
# written under. History in the comment above that constant and in CHANGELOG.md:
# 500 until 2026-06-25, then 16384, then 65536 from 2026-10-02.
#   sweep5v2-live, sweep6-live  500. The 9B think-off no-tools cell of sweep5v2-live
#                               also holds one 503-character row from a resume after
#                               2026-06-25; it is not at the cap, so it is complete.
#   iss024d-e2e-live            16384 ("14% of rows in the iss024d-e2e full-storage
#                               rerun sat at 16384", runner.py).
#   delivered-rerun             65536, and every row carries
#                               `response_truncated_by_storage` (False on every row;
#                               the loader of tools/delivered_rerun asserts it).
SNAPSHOT_CAP = {"sweep5v2-live": 500, "sweep6-live": 500,
                "iss024d-e2e-live": 16384, "delivered-rerun": 65536}

# Fixtures that declare a name with an upper-case letter (checked against the
# fixture trees by `upper_case_fixtures`): satellite p02-p05 (objects) and
# pogo_stick (action names, in domain.pddl and domain_neg.pddl, so every problem).
AFFECTED_SATELLITE = ("p02", "p03", "p04", "p05")

PLAIN, STEERED = (11, 12, 13), (14, 15, 16)
TASK_TOOL = {"validate_plan": "validate_plan", "simulate": "get_state_transition"}
_NAME = re.compile(r"[A-Za-z][\w\-]*")


def affected(domain: str, problem: str) -> bool:
    return (domain == "satellite" and problem in AFFECTED_SATELLITE) or domain == "pogo_stick"


def arm_of(row: dict) -> str:
    """unaided (no-tools cell), plain (v11-13) or steered (v14-16)."""
    if not row.get("with_tools"):
        return "unaided"
    return "plain" if row["prompt_variant"] in PLAIN else "steered"


def is_anon(corpus: str) -> bool:
    """sweep6* rows carry the renamed symbols under the canonical names (D7b)."""
    return "sweep6" in corpus


def at_cap(row: dict, corpus: str) -> bool:
    """True when the stored answer may be cut: the row's own flag where it has one,
    else a length exactly at the corpus's snapshot cap."""
    flag = row.get("response_truncated_by_storage")
    if flag is not None:
        return bool(flag)
    return len(row.get("response") or "") == SNAPSHOT_CAP[corpus]


def strip_comments(text: str) -> str:
    return re.sub(r";[^\n]*", "", text)


def names(text: str) -> set[str]:
    """Identifier-like tokens of a PDDL text, comments removed."""
    return set(_NAME.findall(strip_comments(text)))


def upper_declared(domain_text: str, problem_text: str) -> dict[str, str]:
    """{lower-case form: declared form} for every declared name with a capital."""
    return {t.lower(): t for t in names(domain_text) | names(problem_text) if t != t.lower()}


def declared_lower(domain_text: str, problem_text: str) -> set[str]:
    return {t.lower() for t in names(domain_text) | names(problem_text)}


def writes_capitals(text_or_lines, declared: set[str]) -> bool:
    """The plan writes some declared name (case-insensitive match) with a capital."""
    text = text_or_lines if isinstance(text_or_lines, str) else "\n".join(map(str, text_or_lines))
    return any(t != t.lower() and t.lower() in declared for t in _NAME.findall(text))


def has_upper(plan) -> bool:
    s = plan if isinstance(plan, str) else json.dumps(plan)
    return bool(re.search(r"[A-Z]", s))


def lower_plan(plan):
    """The plan argument with every letter lower-cased (list, string or other)."""
    if isinstance(plan, list):
        return [x.lower() if isinstance(x, str) else x for x in plan]
    if isinstance(plan, str):
        return plan.lower()
    return plan


def _section(text: str, kw: str) -> str:
    m = re.search(r"\(\s*:" + kw + r"\b", text, re.I)
    if not m:
        return ""
    i, depth = m.end(), 1
    while depth and i < len(text):
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _typed_names(sec: str) -> list[str]:
    out, skip = [], False
    for tok in sec.split():
        if tok == "-":
            skip = True
        elif skip:
            skip = False
        else:
            out.append(tok)
    return out


def upper_case_fixtures(tree: Path) -> dict[str, list[str]]:
    """{file relative to the tree: declared names with a capital} for the objects,
    constants and action names of every .pddl file, and any capital word in a
    .plan file."""
    out = {}
    for f in sorted(tree.rglob("*.pddl")):
        t = strip_comments(f.read_text())
        found = [n for kw in ("objects", "constants") for n in _typed_names(_section(t, kw))
                 if n != n.lower()]
        found += [a for a in re.findall(r"\(:action\s+([^\s()]+)", t, re.I) if a != a.lower()]
        if found:
            out[str(f.relative_to(tree))] = sorted(set(found))
    for f in sorted(tree.rglob("*.plan")):
        ups = sorted(w for w in names(f.read_text()) if w != w.lower())
        if ups:
            out[str(f.relative_to(tree))] = ups
    return out


def expected_upper_files() -> set[str]:
    """The files `upper_case_fixtures(domains/)` must return (see AFFECTED_SATELLITE)."""
    return ({f"classical/satellite/{p}.pddl" for p in AFFECTED_SATELLITE}
            | {"numeric/pogo_stick/domain.pddl", "numeric/pogo_stick/domain_neg.pddl"})


def load_rows(path: Path) -> tuple[dict[tuple, dict], int]:
    """{trial key: result} (last row per key wins) and the number of torn lines."""
    rows, torn = {}, 0
    with path.open(errors="replace") as fh:
        for ln in fh:
            if not ln.strip():
                continue
            try:
                o = json.loads(ln)
            except json.JSONDecodeError:
                torn += 1
                continue
            rows[tuple(o["key"])] = o["result"]
    return rows, torn


def fixture_texts(tree: Path):
    """{(domain, problem): (domain text, problem text)} loader with a cache."""
    cache: dict = {}

    def get(domain: str, problem: str) -> tuple[str, str]:
        if (domain, problem) not in cache:
            base = next(tree.glob(f"*/{domain}/domain.pddl")).parent
            cache[(domain, problem)] = ((base / "domain.pddl").read_text(),
                                        (base / f"{problem}.pddl").read_text())
        return cache[(domain, problem)]
    return get


# ------------------------------------------------------------------ environment
def environment(marketplace: Path) -> dict:
    """Versions the checks depend on, for the output files: the pyval release, the
    sibling repo's commit, the last commit that touched the validator server, and
    whether that file differs from the commit."""
    server = marketplace / "plugins" / "pddl-validator" / "server" / "validator_server.py"

    def git(*a):
        return subprocess.run(["git", "-C", str(marketplace), *a], capture_output=True,
                              text=True, check=True).stdout.strip()
    return {
        "pyval": importlib.metadata.version("pddl-pyvalidator"),
        "unified_planning": importlib.metadata.version("unified-planning"),
        "mcp": importlib.metadata.version("mcp"),
        "marketplace_head": git("rev-parse", "HEAD"),
        "validator_server_last_commit": git("log", "-1", "--format=%H", "--", str(server)),
        "validator_server_modified": bool(git("status", "--porcelain", "--", str(server))),
        "validator_server_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
    }


def check_environment(env: dict) -> list[str]:
    """Problems that make the replay meaningless (empty list = fine)."""
    bad = []
    if env["pyval"] != PYVAL_EXPECTED:
        bad.append(f"pddl-pyvalidator is {env['pyval']}, the corpora were graded with "
                   f"{PYVAL_EXPECTED}; under a case-folding release no flip can be seen")
    if env["validator_server_modified"]:
        bad.append("validator_server.py has uncommitted changes in the sibling repo")
    return bad


_REQ_DIR = re.compile(r"[^\s'\"]*/[0-9a-f]{8}/")


def norm_result(text: str):
    """A tool result as the grader compares it: the per-request temporary
    directory (`PDDL_TEMP_DIR/<8 hex>/`, a cluster path in the stored rows, a local
    one in a replay) is replaced by `<req>/`, then the JSON is parsed when it parses."""
    text = _REQ_DIR.sub("<req>/", text if isinstance(text, str) else json.dumps(text))
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


async def call_tool(vs, name: str, arguments: dict) -> str:
    """One tool call the way the harness made it (pddl_eval/chat.py MCPPlanner):
    through the plugin's FastMCP server, `verbose` pinned to False for the
    validator tools, the text of the first content block returned. A tool
    exception becomes its message, as the MCP server sends it to the client."""
    try:
        res = await vs.mcp.call_tool(name, {**(arguments or {}), "verbose": False})
    except Exception as e:  # noqa: BLE001 - the server reports any exception as text
        return str(e)
    if isinstance(res, tuple):
        res = res[0]
    if hasattr(res, "content"):
        res = res.content
    return res[0].text if res else ""


def parse_cell(name: str) -> dict:
    """slurm_vllm_<model>_<on|off>_<no-tools|tools_all_<style>>[_<run tag>]."""
    m = re.match(r"^slurm_vllm_(.+?)_(on|off)_(no-tools|tools_all_[a-z]+)(?:_(.+))?$", name)
    if not m:
        raise ValueError(f"not a cell name: {name}")
    return {"model": m.group(1), "think": m.group(2),
            "tools": m.group(3) != "no-tools",
            "style": m.group(3).replace("tools_all_", "") if m.group(3) != "no-tools" else "none"}


def load_validator(marketplace: Path):
    """Import the pddl-validator plugin server in process (read-only). Its request
    files go to a fresh temporary directory."""
    os.environ["PDDL_TEMP_DIR"] = tempfile.mkdtemp(prefix="iss027_")
    sys.path.insert(0, str(marketplace / "plugins" / "pddl-validator" / "server"))
    import validator_server  # noqa: E402
    return validator_server


# ------------------------------------------------------------------ NUMBERS.md blocks
HEADLINE = ("Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b")
MAIN, RERUN, MECH = "sweep5v2-live", "delivered-rerun", "iss024d-e2e-live"
# NUMBERS.md generated block -> file under out/ (registered in numbers_fill.BLOCKS)
NUMBERS_FILES = {"iss027": "numbers_iss027.md", "iss027_mech": "numbers_iss027_mech.md",
                 "iss027_summary": "numbers_iss027_summary.md", "iss027_t1": "numbers_iss027_t1.md",
                 "iss027_t2": "numbers_iss027_t2.md", "iss027_t5": "numbers_iss027_t5.md",
                 "iss027_t8a": "numbers_iss027_t8a.md"}


def cell_table(replay: dict, unaided: dict) -> dict[tuple, dict]:
    """{(corpus, model, think, task, arm): n, k, lo, hi, called} from the two JSON
    outputs; lo/hi = trials added under case folding (equal except where an unaided
    answer is cut at the cap). Tool cells of the `minimal` style only."""
    out = {}
    for c in replay["cells"]:
        if c["style"] != "minimal":
            continue
        add = c.get("flips_up", 0) - c.get("flips_down", 0)
        out[(c["corpus"], c["model"], c["think"], c["task"], c["arm"])] = dict(
            n=c["n"], k=c["k"], lo=add, hi=add, called=c["called"])
    for c in unaided["cells"]:
        if c["tools"]:
            continue
        lo = c.get("online_flips", 0)
        out[(c["corpus"], c["model"], c["think"], c["task"], "unaided")] = dict(
            n=c["n"], k=c["k_stored"], lo=lo, hi=lo + c.get("at_cap_candidates", 0), called=None)
    return out


def moves(table: dict, corpus: str, think: str = "off", models=HEADLINE) -> dict[tuple, dict]:
    """The cells of one corpus that move: {(model, task, arm): row}."""
    return {(m, t, a): v for (c, m, th, t, a), v in table.items()
            if c == corpus and th == think and m in models and v["hi"]}


def _p(k, n):
    return f"{100 * k / n:.1f}"


def _after(v, field="n"):
    n = v[field]
    lo, hi = _p(v["k"] + v["lo"], n), _p(v["k"] + v["hi"], n)
    return lo if lo == hi else f"{lo}–{hi}"


def _add(v):
    return f"+{v['lo']}" if v["lo"] == v["hi"] else f"+{v['lo']} to +{v['hi']}"


def _arm(task, arm):
    return f"{task} {'unaided' if arm == 'unaided' else 'tool-verified ' + arm}"


def render_numbers(replay: dict, unaided: dict, name=None) -> dict[str, str]:
    """{block name: markdown} for the NUMBERS.md blocks (NUMBERS_FILES)."""
    if name is None:
        import gen_common
        name = gen_common.model_name
    T = cell_table(replay, unaided)
    env, sr, su = replay["env"], replay["self_check"], unaided["self_check"]
    S1 = moves(T, MAIN)
    out = {}
    tag = "**ISS-027, post hoc (grader case fault; the frozen values above stay).**"
    out["iss027_t1"] = (tag + " With plan names case-folded, these cells move: " + "; ".join(
        f"{name(m)} {_arm(t, a)} {_p(v['k'], v['n'])} → {_after(v)} ({_add(v)} trial{'s' if v['hi'] > 1 else ''})"
        for (m, t, a), v in sorted(S1.items())) + ". No other cell of this table moves. Counts and "
        "method: \"ISS-027 post hoc corrections\" below.")
    called = {k: v for k, v in S1.items() if k[2] != "unaided"}
    out["iss027_t2"] = (tag + " Correct given a call, names case-folded: " + "; ".join(
        f"{name(m)} {t} {a} {_p(v['k'], v['called'])} → {_after(v, 'called')} "
        f"({v['k'] + v['lo']}/{v['called']})" for (m, t, a), v in sorted(called.items()))
        + ". Calling does not change.")
    g = S1.get(("gemma4_26b-a4b", "simulate", "plain")), S1.get(("gemma4_26b-a4b", "simulate", "steered"))
    out["iss027_summary"] = (tag + " Gemma simulate correct given a call reads "
                             f"{_after(g[0], 'called')} / {_after(g[1], 'called')} with plan names "
                             f"case-folded (frozen {_p(g[0]['k'], g[0]['called'])} / "
                             f"{_p(g[1]['k'], g[1]['called'])}); see T2.")
    # T5: paired contrasts as point estimates
    parts = []
    for m in HEADLINE:
        for t in ("solve", "validate_domain", "validate_problem", "validate_plan", "simulate"):
            for lab, a, b in (("availability", "unaided", "plain"), ("steering", "plain", "steered")):
                va, vb = T[(MAIN, m, "off", t, a)], T[(MAIN, m, "off", t, b)]
                if not (va["hi"] or vb["hi"]):
                    continue
                d0 = 100 * (vb["k"] / vb["n"] - va["k"] / va["n"])
                d1 = 100 * ((vb["k"] + vb["lo"]) / vb["n"] - (va["k"] + va["lo"]) / va["n"])
                parts.append(f"{name(m)} {t} {lab} {d0:+.1f} → {d1:+.1f}")
    out["iss027_t5"] = (tag + " Δ with plan names case-folded, point estimates (the clustered "
                        "intervals and Holm p-values are not recomputed): " + "; ".join(parts)
                        + ". No other row of T5 moves.")
    # T8a: main sweep vs rerun, tool cells
    parts = []
    for m in HEADLINE:
        for t in ("validate_plan", "simulate"):
            for a in ("plain", "steered"):
                vm, vr = T.get((MAIN, m, "off", t, a)), T.get((RERUN, m, "off", t, a))
                if vm is None or vr is None or not (vm["lo"] or vr["lo"]):
                    continue
                d0 = 100 * (vr["k"] / vr["n"] - vm["k"] / vm["n"])
                d1 = 100 * ((vr["k"] + vr["lo"]) / vr["n"] - (vm["k"] + vm["lo"]) / vm["n"])
                parts.append(f"{name(m)} {t} {a}: main {_p(vm['k'], vm['n'])} → {_after(vm)}, rerun "
                             f"{_p(vr['k'], vr['n'])} → {_after(vr)}, Δ {d0:+.1f} → {d1:+.1f}")
    out["iss027_t8a"] = (tag + " Tool-verified cells that move with plan names case-folded (point "
                         "estimates; the paired intervals and the ±5 verdicts are not recomputed): "
                         + "; ".join(parts) + ". Calling does not change.")
    mech = moves(T, MECH, think="on", models=("Qwen3_5_4B", "Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b"))
    mp = mech[("gemma4_26b-a4b", "simulate", "plain")]
    rest = {k: v for k, v in mech.items() if k != ("gemma4_26b-a4b", "simulate", "plain")}
    still = [name(m) for m in ("Qwen3_5_4B", "Qwen3_5_9B", "qwen3_6_35b")
             if (m, "simulate", "plain") not in mech]
    out["iss027_mech"] = (tag + f" Gemma plain {_p(mp['k'], mp['n'])}% ({mp['k']} of {mp['n']}) reads "
                          f"{_after(mp)}% ({mp['k'] + mp['lo']} of {mp['n']}, {_add(mp)} trials) with plan "
                          "names case-folded. On the same corpus "
                          + "; ".join(f"{name(m)} {t} {a} {_p(v['k'], v['n'])} → {_after(v)} ({_add(v)})"
                                      for (m, t, a), v in sorted(rest.items()))
                          + " move as well. The plain-arm values of " + ", ".join(still)
                          + " in this row do not move.")
    # the main block
    def lst(mv):
        return "; ".join(f"{name(m)} {_arm(t, a)} {_p(v['k'], v['n'])} → {_after(v)} ({_add(v)})"
                         for (m, t, a), v in sorted(mv.items())) or "none"
    on = moves(T, MAIN, think="on", models=("Qwen3_5_0_8B", "Qwen3_5_4B") + HEADLINE)
    small = moves(T, MAIN, models=("Qwen3_5_0_8B", "Qwen3_5_4B"))
    rer = moves(T, RERUN)
    anon_on = moves(T, "sweep6-live", "on", ("Qwen3_5_0_8B", "Qwen3_5_4B") + HEADLINE)
    anon_off = moves(T, "sweep6-live", "off", ("Qwen3_5_0_8B", "Qwen3_5_4B") + HEADLINE)
    partc = [c for c in unaided["cells"] if c["corpus"] == RERUN and c["task"] == "solve"]
    partc_aff = sum(c["n_affected"] for c in partc if not c["tools"])
    partc_flip = sum(c.get("online_flips", 0) + c.get("delivered_flips", 0) for c in partc)
    N = [f"*Generated by `tools/reanalysis/iss027_replay.py` and `iss027_unaided.py` (outputs "
         f"`tools/reanalysis/out/iss027_*.{{json,md}}`); do not edit between the markers, rerun the "
         f"scripts. pddl-pyvalidator {env['pyval']} (the frozen grader; 0.1.6 folds case), sibling "
         f"`../pddl-copilot` at `{env['marketplace_head'][:10]}`. Self-check: {sr['calls_equal']:,} of "
         f"{sr['calls_replayed']:,} replayed tool calls return the stored result ({sr['calls_known_difference']} "
         f"known wording difference in the free-text report, same verdict, listed in `iss027_replay.md`); "
         f"the harness rule on the as-is replay equals the stored `success` on all {sr['rows_replayed']} "
         f"replayed rows; the unaided re-grade equals the stored `success` on all "
         f"{su['regraded_rows']:,} rows not cut at the snapshot cap.*", "",
         "| figure | frozen → post hoc (names case-folded) | source | do NOT quote |", "|---|---|---|---|",
         f"| Study 1, think=off, headline (T1, T2, T5) | {lst(S1)} | `iss027_replay.md`, `iss027_unaided.md` | "
         "a post hoc value in place of the frozen one; the frozen value without this caveat |",
         f"| Study 1, think=on (main sweep) | {lst(on)} | same | same |",
         f"| Study 1, think=off, Qwen3.5-0.8B and 4B | {lst(small)} | same | same |",
         f"| contamination twin (`sweep6-live`, renamed tree, no capitals declared) | off: {lst(anon_off)}; "
         f"on: {lst(anon_on)} | same | — |",
         f"| delivered rerun, tool-verified (T8a inputs) | {lst(rer)} | `iss027_replay.md` | same |",
         f"| delivered rerun, solve graded from the answer (Part C online and delivered, tool-arm "
         f"delivered E1/E2) | **{partc_flip} flips**; Part C has {partc_aff} rows on the affected "
         "fixtures and none of their plans keeps a capital | `iss027_unaided.md` | — |",
         f"| rerun simulate mechanism layer (`iss024d-e2e-live`, think on) | {lst(mech)} | "
         "`iss027_replay.md` | same |",
         "", "Ranges (\"+a to +b\") come from unaided answers stored cut at the 500-character "
         "snapshot: the low end re-grades what is stored; the high end adds the cut answers whose "
         "stored reason is `plan_invalid` and whose visible JSON writes a capitalised fixture name. "
         "A replay changes only the tool's answer, so it corrects the tool-verified grade only; the "
         "delivered grade of the tool arms stays as stored. Every flip is on satellite p02–p05 or pogo_stick. "
         "Not recomputed here: intervals, p-values and equivalence verdicts (point estimates only)."]
    out["iss027"] = "\n".join(N)
    return out


def write_numbers_files(out_dir: Path) -> list[Path]:
    replay = json.loads((out_dir / "iss027_replay.json").read_text())
    unaided = json.loads((out_dir / "iss027_unaided.json").read_text())
    written = []
    for block, text in render_numbers(replay, unaided).items():
        f = out_dir / NUMBERS_FILES[block]
        f.write_text(text.rstrip("\n") + "\n")
        written.append(f)
    return written


def s1_moves(out_dir: Path = OUT) -> dict[tuple, tuple]:
    """For s1_breakdowns_md.py: {(model, task, arm): (trials added, rate before, rate
    after)} for the Study 1 think=off headline cells that move. Halts (ValueError)
    on a range, which no think=off headline cell has."""
    replay = json.loads((out_dir / "iss027_replay.json").read_text())
    unaided = json.loads((out_dir / "iss027_unaided.json").read_text())
    out = {}
    for key, v in moves(cell_table(replay, unaided), MAIN).items():
        if v["lo"] != v["hi"]:
            raise ValueError(f"ISS-027 range on a think=off headline cell: {key}")
        out[key] = (v["lo"], round(100 * v["k"] / v["n"], 1), round(100 * (v["k"] + v["lo"]) / v["n"], 1))
    return out
