"""formalization_match (prereg §4) over the WT confirmatory side-logs.

Decomposes the model-authored formalization per WT trial as
parseable -> solvable -> equivalent-to-gold (Planetarium-style), plus the
companion domain-equivalence check (24 arity-constrained bijections,
behavioral fallback = replay the gold plan through the model's
domain+problem). Wilson CIs on the realized 600/cell denominator.

Instrument: the pddl-parser plugin's own tool functions (inspect_problem /
inspect_domain / get_trajectory), imported directly — analysis-time only;
the plugin was deliberately kept out of the model's roster.

Operationalization (recorded for the memo):
- A trial's formalization = the LAST classic_planner call's (domain, problem)
  arguments (the model's final settled statement of the problem). A
  diagnostic "any-call" upper bound is reported alongside.
- solvable = the logged Fast Downward result of that same call contains a
  non-empty plan (all PlanBench instances are solvable, so a correct
  formalization must yield a plan).
- Problem equality = (objects, init, goal) literal-set equality under the
  config-declared object bijection (encoded_objects) and an
  arity-constrained injective predicate map (brute-forced; <=6 candidates).
  Model object names outside the declared bijection count as no-match and
  are tallied separately.

Run with the plugin venv:
  /Users/omereliyahu/personal/pddl-copilot/plugins/pddl-parser/.venv/bin/python3 \
      .local/wt_run/formalization_match.py [--limit N]
"""
import argparse
import hashlib
import itertools
import json
import os
import math
import re
import sys
from pathlib import Path

PLUGIN_SERVER = "/Users/omereliyahu/personal/pddl-copilot/plugins/pddl-parser/server"
sys.path.insert(0, PLUGIN_SERVER)
import parser_server as ps  # noqa: E402

R = Path(__file__).resolve().parents[2]
PB = R / "external/LLMs-Planning/plan-bench"
ENGINE = "pddl_copilot__anthropic-tools__claude-haiku-4-5"
HERE = Path(os.environ.get("WT_SIDELOG_DIR",
    Path(__file__).resolve().parents[2] / "results/planbench/wt-anthropic-20260801/sidelogs"))

CONFIGS = {
    "blocksworld": ("clean", "blocksworld/generated_basic"),
    "blocksworld_3": ("clean", "blocksworld/generated_basic_3"),
    "mystery_blocksworld": ("mystery", "blocksworld/mystery/generated_basic"),
    "mystery_blocksworld_3": ("mystery", "blocksworld/mystery/generated_basic_3"),
}
GOLD_DOMAIN = {
    "clean": str(PB / "instances/blocksworld/generated_domain.pddl"),
    "mystery": str(PB / "instances/blocksworld/mystery/generated_domain.pddl"),
}
COLOR2LETTER = {"red": "a", "blue": "b", "orange": "c", "yellow": "d",
                "white": "e", "magenta": "f", "black": "g", "cyan": "h",
                "green": "i", "violet": "j", "silver": "k", "gold": "l"}
LETTERS = set("abcdefghijkl")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


# ---------------------------------------------------------------- s-expr ----

def sexp(tokens):
    tok = tokens.pop(0)
    if tok == "(":
        out = []
        while tokens[0] != ")":
            out.append(sexp(tokens))
        tokens.pop(0)
        return out
    return tok


def parse_sexp(s):
    tokens = re.findall(r"\(|\)|[^\s()]+", s)
    return sexp(tokens)


def flatten_literals(node, sign=True):
    """Flatten an (and ...) / literal tree into {(sign, pred, args)}.
    Returns None on any construct beyond and/not/literal."""
    if not isinstance(node, list) or not node:
        return None
    head = node[0]
    if head == "and":
        out = set()
        for child in node[1:]:
            sub = flatten_literals(child, sign)
            if sub is None:
                return None
            out |= sub
        return out
    if head == "not":
        if len(node) != 2:
            return None
        return flatten_literals(node[1], not sign)
    if any(isinstance(x, list) for x in node):
        return None
    return {(sign, head.lower(), tuple(a.lower() for a in node[1:]))}


def literal_set(strings):
    """Parse a list of literal strings (each possibly an (and ...)) into
    {(pred, args)}. Returns None on unparseable/negative content."""
    out = set()
    for s in strings:
        try:
            lits = flatten_literals(parse_sexp(s))
        except (IndexError, ValueError):
            return None
        if lits is None:
            return None
        for sign, pred, args in lits:
            if not sign:
                return None
            out.add((pred, args))
    return out


# ---------------------------------------------------------- object mapping --

def norm_obj(name, kind):
    n = name.lower().strip().replace("_", "-")
    if kind == "clean":
        for suf in ("-block", "block"):
            if n.endswith(suf) and n != suf:
                n = n[: -len(suf)].rstrip("-")
                break
        if n in COLOR2LETTER:
            return COLOR2LETTER[n]
        return None
    for pre in ("object-", "object"):
        if n.startswith(pre) and n != pre:
            n = n[len(pre):].lstrip("-")
            break
    if n in LETTERS:
        return n
    return None


# ------------------------------------------------------ predicate mapping ---

def pred_maps(model_arity, gold_arity):
    """Injective arity-preserving maps model-pred -> gold-pred (<= 3!*1*1)."""
    by_ar = {}
    for p, a in model_arity.items():
        by_ar.setdefault(a, []).append(p)
    gold_by_ar = {}
    for p, a in gold_arity.items():
        gold_by_ar.setdefault(a, []).append(p)
    per_class = []
    for ar, mpreds in by_ar.items():
        gpreds = gold_by_ar.get(ar, [])
        if len(mpreds) > len(gpreds):
            return
        per_class.append([dict(zip(mpreds, perm))
                          for perm in itertools.permutations(gpreds, len(mpreds))])
    for combo in itertools.product(*per_class):
        m = {}
        for d in combo:
            m.update(d)
        yield m


def problem_equal(model, gold, kind):
    """model/gold = (objects:set, init:{(p,args)}, goal:{(p,args)}).
    Returns (equal, why)."""
    omap = {}
    for o in model[0]:
        g = norm_obj(o, kind)
        if g is None:
            return False, "unmapped_object"
        if o in omap or g in omap.values():
            pass
        omap[o] = g
    if len(set(omap.values())) != len(omap):
        return False, "object_collision"
    if set(omap.values()) != gold[0]:
        return False, "object_set_mismatch"
    model_arity = {}
    for p, args in model[1] | model[2]:
        if model_arity.setdefault(p, len(args)) != len(args):
            return False, "inconsistent_arity"
    gold_arity = {}
    for p, args in gold[1] | gold[2]:
        gold_arity.setdefault(p, len(args))
    for pmap in pred_maps(model_arity, gold_arity):
        def apply(lits):
            out = set()
            for p, args in lits:
                out.add((pmap[p], tuple(omap[a] for a in args)))
            return out
        try:
            if apply(model[1]) == gold[1] and apply(model[2]) == gold[2]:
                return True, "ok"
        except KeyError:
            continue
    return False, "no_predicate_map"


# ------------------------------------------------------- domain structure ---

def action_signature(action):
    """Positional-normalized (npars, precond set, effect set) with params as
    ?0..?k and predicate names left raw. None if unparseable."""
    params = list(action["parameters"].keys())
    pmap = {p.lower(): f"?{i}" for i, p in enumerate(params)}

    def conv(litset):
        out = set()
        for sign, pred, args in litset:
            try:
                out.add((sign, pred, tuple(pmap[a] for a in args)))
            except KeyError:
                return None
        return out

    try:
        pre = flatten_literals(parse_sexp(action["precondition"]))
        eff = flatten_literals(parse_sexp(action["effect"]))
    except (IndexError, ValueError):
        return None
    if pre is None or eff is None:
        return None
    pre, eff = conv(pre), conv(eff)
    if pre is None or eff is None:
        return None
    return (len(params), pre, eff)


def domain_structural_equiv(model_di, gold_di):
    model_preds = {p["name"].lower(): len(p["parameters"]) for p in model_di["predicates"]}
    gold_preds = {p["name"].lower(): len(p["parameters"]) for p in gold_di["predicates"]}
    if sorted(model_preds.values()) != sorted(gold_preds.values()):
        return False
    msigs = {}
    for a in model_di["actions"]:
        msigs[a["name"].lower()] = action_signature(a)
    gsigs = {}
    for a in gold_di["actions"]:
        gsigs[a["name"].lower()] = action_signature(a)
    if any(s is None for s in msigs.values()) or any(s is None for s in gsigs.values()):
        return False
    m_by_ar = {}
    for n, (k, _, _) in msigs.items():
        m_by_ar.setdefault(k, []).append(n)
    g_by_ar = {}
    for n, (k, _, _) in gsigs.items():
        g_by_ar.setdefault(k, []).append(n)
    if {k: len(v) for k, v in m_by_ar.items()} != {k: len(v) for k, v in g_by_ar.items()}:
        return False

    def act_maps():
        per = []
        for ar, mnames in m_by_ar.items():
            per.append([dict(zip(mnames, perm))
                        for perm in itertools.permutations(g_by_ar[ar])])
        for combo in itertools.product(*per):
            m = {}
            for d in combo:
                m.update(d)
            yield m

    for pmap in pred_maps(model_preds, gold_preds):
        def rename(litset):
            return {(s, pmap[p], a) for s, p, a in litset}
        for amap in act_maps():
            if all(
                (msigs[mn][0] == gsigs[gn][0]
                 and rename(msigs[mn][1]) == gsigs[gn][1]
                 and rename(msigs[mn][2]) == gsigs[gn][2])
                for mn, gn in amap.items()
            ):
                return True
    return False


# ------------------------------------------------------ behavioral fallback -

STATE_LIT_RX = re.compile(r"\(([^()]+)\)")


def behavioral_equiv(model_dom, model_prob, gold_plan, kind, model_info):
    """Replay the gold plan (NL-encoded object names) through the model's
    domain+problem under every arity-consistent action map; success = full
    execution + model's own goal satisfied."""
    inv_omap = {}
    for o in model_info["objects_raw"]:
        g = norm_obj(o, kind)
        if g is None:
            return False
        inv_omap[g] = o
    gold_di = gold_domain_info(kind)
    gold_names = {a["name"].lower(): len(a["parameters"]) for a in gold_di["actions"]}
    try:
        model_di = inspect_domain_cached(model_dom)
    except RuntimeError:
        return False
    model_names = {a["name"].lower(): len(a["parameters"]) for a in model_di["actions"]}
    steps = []
    for line in gold_plan.strip().splitlines():
        toks = line.strip().strip("()").split()
        if not toks:
            continue
        name, args = toks[0].lower(), [t.lower() for t in toks[1:]]
        mapped_args = []
        for a in args:
            g = a if a in LETTERS and kind == "mystery" else norm_obj(a, kind)
            if g is None or g not in inv_omap:
                return False
            mapped_args.append(inv_omap[g])
        steps.append((name, mapped_args))
    g_by_ar = {}
    for n, k in gold_names.items():
        g_by_ar.setdefault(k, []).append(n)
    m_by_ar = {}
    for n, k in model_names.items():
        m_by_ar.setdefault(k, []).append(n)
    per = []
    for ar, gnames in g_by_ar.items():
        mnames = m_by_ar.get(ar, [])
        if len(mnames) < len(gnames):
            return False
        per.append([dict(zip(gnames, perm))
                    for perm in itertools.permutations(mnames, len(gnames))])
    goal = model_info["goal"]
    for combo in itertools.product(*per):
        amap = {}
        for d in combo:
            amap.update(d)
        try:
            plan_lines = [f"({amap[n]} {' '.join(a)})".replace("  ", " ").strip()
                          for n, a in steps]
        except KeyError:
            continue
        res = ps.get_trajectory(domain=model_dom, problem=model_prob,
                                plan=plan_lines)
        if res.get("error") or res.get("num_steps", -1) != len(plan_lines):
            continue
        final = literal_set([f"({m})" for m in
                             STATE_LIT_RX.findall(res.get("final_state", ""))])
        if final is not None and goal <= {(p, a) for p, a in final}:
            return True
    return False


# ------------------------------------------------------------- inspection ---

_domain_cache = {}
_gold_domain_cache = {}
_gold_prob_cache = {}


def inspect_domain_cached(dom_str):
    key = hashlib.sha256(dom_str.encode()).hexdigest()
    if key not in _domain_cache:
        res = ps.inspect_domain(domain=dom_str)
        _domain_cache[key] = res
    res = _domain_cache[key]
    if res.get("error"):
        raise RuntimeError(res["message"])
    return res


def gold_domain_info(kind):
    if kind not in _gold_domain_cache:
        res = ps.inspect_domain(domain=GOLD_DOMAIN[kind])
        assert not res.get("error"), res
        _gold_domain_cache[kind] = res
    return _gold_domain_cache[kind]


def gold_problem_sets(kind, inst_dir, iid):
    key = (inst_dir, iid)
    if key not in _gold_prob_cache:
        res = ps.inspect_problem(domain=GOLD_DOMAIN[kind],
                                 problem=str(PB / "instances" / inst_dir /
                                             f"instance-{iid}.pddl"))
        assert not res.get("error"), (key, res)
        objs = {o["name"].lower() for o in res["objects"]}
        init = literal_set(res["init"])
        goal = literal_set(res["goal"])
        assert init is not None and goal is not None, key
        _gold_prob_cache[key] = (objs, init, goal)
    return _gold_prob_cache[key]


def inspect_model_problem(dom_str, prob_str):
    """Returns dict with objects_raw, objects(set), init, goal — or None if
    unparseable (stage-1 fail)."""
    res = ps.inspect_problem(domain=dom_str, problem=prob_str)
    if res.get("error"):
        return None
    init = literal_set(res["init"])
    goal = literal_set(res["goal"])
    if init is None or goal is None:
        return None
    return {"objects_raw": [o["name"].lower() for o in res["objects"]],
            "objects": {o["name"].lower() for o in res["objects"]},
            "init": init, "goal": goal,
            "parser_used": res.get("parser_used")}


def classify_result(head):
    if not head:
        return "missing"
    if re.search(r'"plan"\s*:\s*\[\s*\]', head):
        return "empty"
    if re.search(r'"plan"\s*:\s*\[\s*"', head):
        return "plan"
    if '"error"' in head or head.lstrip().startswith("Error"):
        return "error"
    return "other"


# ------------------------------------------------------------------ trial ---

def eval_call(call, kind, gold_sets):
    """Evaluate one classic_planner call. Returns dict of stage bools."""
    args = call.get("arguments") or {}
    dom, prob = args.get("domain"), args.get("problem")
    out = {"has_args": bool(dom and prob), "parseable": False,
           "solvable": classify_result(call.get("result_head")) == "plan",
           "match": False, "why": None, "info": None, "dom": dom, "prob": prob}
    if not out["has_args"]:
        out["why"] = "missing_arguments"
        return out
    info = inspect_model_problem(dom, prob)
    if info is None:
        out["why"] = "unparseable"
        return out
    out["parseable"] = True
    out["info"] = info
    eq, why = problem_equal((info["objects"], info["init"], info["goal"]),
                            gold_sets, kind)
    out["match"] = eq
    out["why"] = why
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="first N trials per config (smoke)")
    ap.add_argument("--rows", default=str(HERE / "formalization_match_rows.jsonl"))
    args = ap.parse_args()

    rows = []
    for config, (kind, inst_dir) in CONFIGS.items():
        resp = json.load(open(PB / "responses" / config / ENGINE /
                              "task_1_plan_generation.json"))
        gt_plan = {str(i["instance_id"]): i["ground_truth_plan"]
                   for i in resp["instances"]}
        graded = json.load(open(PB / "results" / config / ENGINE /
                                "task_1_plan_generation.json"))
        correct = {str(i["instance_id"]): bool(i.get("llm_correct"))
                   for i in graded["instances"]}
        last = {}
        for line in open(HERE / f"{config}__anthropic-tools.jsonl"):
            rec = json.loads(line)
            last[str(rec["instance_id"])] = rec
        items = sorted(last.items(), key=lambda kv: int(kv[0]))
        if args.limit:
            items = items[: args.limit]
        for n_done, (iid, rec) in enumerate(items):
            gold = gold_problem_sets(kind, inst_dir, iid)
            calls = [tc for tc in rec["tool_calls"]
                     if tc.get("name") == "classic_planner"]
            row = {"config": config, "kind": kind, "instance_id": iid,
                   "n_planner_calls": len(calls),
                   "llm_correct": correct.get(iid, False)}
            if not calls:
                row.update(delegated=False, parseable=False, solvable=False,
                           match=False, why="no_planner_call",
                           domain_equiv=False, domain_via=None, any_match=False)
                rows.append(row)
                continue
            primary = eval_call(calls[-1], kind, gold)
            row.update(delegated=True, parseable=primary["parseable"],
                       solvable=primary["parseable"] and primary["solvable"],
                       match=primary["match"], why=primary["why"])
            # domain equivalence on the primary call
            dequiv, via = False, None
            if primary["has_args"]:
                try:
                    mdi = inspect_domain_cached(primary["dom"])
                    dequiv = domain_structural_equiv(mdi, gold_domain_info(kind))
                    via = "structural" if dequiv else None
                except RuntimeError:
                    mdi = None
                if not dequiv and primary["info"] is not None:
                    if behavioral_equiv(primary["dom"], primary["prob"],
                                        gt_plan[iid], kind, primary["info"]):
                        dequiv, via = True, "behavioral"
            row.update(domain_equiv=dequiv, domain_via=via)
            # any-call diagnostic (upper bound)
            any_match = primary["match"]
            if not any_match:
                for call in reversed(calls[:-1]):
                    e = eval_call(call, kind, gold)
                    if e["match"]:
                        any_match = True
                        break
            row["any_match"] = any_match
            rows.append(row)
            if (n_done + 1) % 50 == 0:
                print(f"  {config}: {n_done + 1}/{len(items)}", file=sys.stderr)

    with open(args.rows, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    # ------------------------------------------------------------ summary --
    def cell(rows_, name):
        n = len(rows_)
        stages = [("delegated", "delegated"),
                  ("parseable", "parseable"),
                  ("solvable", "solvable (FD plan on last call)"),
                  ("match", "formalization_match (problem == gold)"),
                  ("domain_equiv", "domain equivalent"),
                  ("any_match", "any-call match (diagnostic)")]
        print(f"\n== {name} (n={n}) ==")
        for key, label in stages:
            k = sum(r[key] for r in rows_)
            lo, hi = wilson(k, n)
            print(f"  {label:42s} {k:4d}/{n}  {k / n * 100:5.1f}%  "
                  f"[{lo * 100:.1f}, {hi * 100:.1f}]")
        both = sum(r["match"] and r["domain_equiv"] for r in rows_)
        print(f"  {'match AND domain_equiv':42s} {both:4d}/{n}  {both / n * 100:5.1f}%")
        for cond, lab in ((True, "P(correct | match)"),
                          (False, "P(correct | no match)")):
            sub = [r for r in rows_ if r["match"] == cond]
            if sub:
                k = sum(r["llm_correct"] for r in sub)
                print(f"  {lab:42s} {k:4d}/{len(sub)}  {k / len(sub) * 100:5.1f}%")
        why = {}
        for r in rows_:
            if not r["match"]:
                why[r["why"]] = why.get(r["why"], 0) + 1
        print(f"  no-match reasons: {dict(sorted(why.items(), key=lambda kv: -kv[1]))}")
        via = {}
        for r in rows_:
            if r["domain_equiv"]:
                via[r["domain_via"]] = via.get(r["domain_via"], 0) + 1
        print(f"  domain equivalence via: {via}")

    clean = [r for r in rows if r["kind"] == "clean"]
    myst = [r for r in rows if r["kind"] == "mystery"]
    for config in CONFIGS:
        cell([r for r in rows if r["config"] == config], config)
    cell(clean, "CLEAN WT (pooled, amendment-K 600)")
    cell(myst, "MYSTERY WT (pooled, amendment-K 600)")

    if clean and myst:
        kc, km = sum(r["match"] for r in clean), sum(r["match"] for r in myst)
        loc, hic = wilson(kc, len(clean))
        lom, him = wilson(km, len(myst))
        print(f"\nRESCUE-branch requirement 3: Mystery formalization_match "
              f"[{lom * 100:.1f}, {him * 100:.1f}] vs clean "
              f"[{loc * 100:.1f}, {hic * 100:.1f}] -> "
              f"{'CI-DISJOINT BELOW (requirement FAILS)' if him < loc else 'NOT CI-disjointly below (requirement MET)'}")


if __name__ == "__main__":
    main()
