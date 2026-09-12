"""First-draw statistics for the PlanBench clean-WT cell (2026-08-06 brief).

Reconstructs the first-draw outcome vector for clean WT (600 instances:
blocksworld[1..500] + blocksworld_3[1..100]) from:
  - the graded corpus (results/{cfg}/{engine}/task_1_plan_generation.json),
    used as-is for the 582 single-record instances (first draw == last draw);
  - the side-log JSONL (.local/wt_run/{cfg}__anthropic-tools.jsonl), whose
    FIRST record (file order = draw order) is re-graded with VAL for the 18
    duplicate-id instances in the "blocksworld" (500-pool) config only.

Then computes, with pure Python (math.comb / closed-form Wilson, no scipy):
  (a) Wilson 95% CI on the first-draw clean-WT count.
  (b) Exact two-sided McNemar of first-draw clean WT vs matched-NT clean,
      paired by (cfg, instance_id).
  (c) The clean-vs-Mystery WT paired delta under first-draw, using the same
      pairing convention as .local/wt_run/analyze_confirmatory.py: pair
      (cfg, iid) in clean against (("mystery_" + cfg), iid) in Mystery.
      Mystery WT is a single-record cell (unaffected by the resume) so its
      values come straight from its graded corpus.

Run from repo root:
  /Users/omereliyahu/personal/pddl-copilot-experiments/.venv-planbench-wt/bin/python \
    firstdraw_analysis.py
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/omereliyahu/personal/pddl-copilot-experiments")
PB = REPO / "external/LLMs-Planning/plan-bench"
SIDELOG = REPO / ".local/wt_run"
VAL_DIR = REPO / "external/LLMs-Planning/planner_tools/VAL/bin/MacOSExecutables"

sys.path.insert(0, str(PB))
os.chdir(PB)  # text_to_plan / configs are loaded via relative paths

import yaml  # noqa: E402
from tarski.io import PDDLReader  # noqa: E402
from utils.text_to_pddl import text_to_plan  # noqa: E402

WT_ENGINE = "pddl_copilot__anthropic-tools__claude-haiku-4-5"
NT_ENGINE = "pddl_copilot__anthropic-scaffold__claude-haiku-4-5"
CLEAN_CFGS = ["blocksworld", "blocksworld_3"]
MYSTERY_CFGS = ["mystery_blocksworld", "mystery_blocksworld_3"]

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-omereliyahu-personal-pddl-copilot-experiments/"
    "4721bdc4-1a3f-4ecb-86e9-672fa71b56d1/scratchpad/firstdraw-stats"
)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def mcnemar_exact(b, c):
    """Two-sided exact binomial test on discordant pairs."""
    n, k = b + c, min(b, c)
    if n == 0:
        return 1.0
    p = sum(math.comb(n, i) for i in range(k + 1)) * 0.5 ** n
    return min(1.0, 2 * p)


def load_config(cfg):
    return yaml.safe_load(open(f"configs/{cfg}.yaml"))


def load_graded(cfg, engine):
    """{instance_id(int): {'correct': bool, 'text': str}} from the graded corpus."""
    path = PB / f"results/{cfg}/{engine}/task_1_plan_generation.json"
    data = json.load(open(path))
    out = {}
    for r in data["instances"]:
        out[int(r["instance_id"])] = {
            "correct": bool(r.get("llm_correct")),
            "text": r.get("llm_raw_response") or "",
        }
    return out


def load_sidelog_first_records(cfg):
    """{instance_id(int): [(lineno, record), ...]} in file order (draw order)."""
    path = SIDELOG / f"{cfg}__anthropic-tools.jsonl"
    by_id = {}
    with open(path) as f:
        for lineno, ln in enumerate(f):
            r = json.loads(ln)
            iid = int(r["instance_id"])
            by_id.setdefault(iid, []).append((lineno, r))
    return by_id


def grade_response_text(cfg_data, domain_pddl, instance_path, text, plan_file):
    """Mirror ResponseEvaluator.evaluate_plan's grading path exactly:
    text_to_plan -> validate_plan (VAL 'validate' binary), any exception -> False.
    """
    try:
        reader = PDDLReader(raise_on_error=True)
        reader.parse_domain(domain_pddl)
        problem = reader.parse_instance(instance_path)
        text_to_plan(text, problem.actions, plan_file, cfg_data)
        cmd = [str(VAL_DIR / "validate"), domain_pddl, instance_path, plan_file]
        resp = subprocess.run(cmd, capture_output=True, text=True).stdout
        if "Problem in domain" in resp:
            raise Exception("Problem in domain: Check PDDL Writer")
        return "Plan valid" in resp
    except Exception as exc:
        print(f"  [grade] extraction/VAL exception for text len={len(text)}: {exc}",
              file=sys.stderr)
        return False


def reconstruct_clean_wt_first_draw():
    """Returns {(cfg, iid): bool_correct} for the first-draw clean-WT cell,
    plus a diagnostics dict."""
    out = {}
    diag = {"duplicate_ids": [], "first_draw_regraded": []}
    plan_file = str(SCRATCH / "llm_plan_scratch")

    for cfg in CLEAN_CFGS:
        cfg_data = load_config(cfg)
        domain_pddl = f"./instances/{cfg_data['domain_file']}"
        inst_tpl = f"./instances/{cfg_data['instance_dir']}/{cfg_data['instances_template']}"
        lo, hi = cfg_data["start"] + 1, cfg_data["end"] + 1  # pool ids 2..end+1

        graded = load_graded(cfg, WT_ENGINE)
        assert len(graded) == (hi - lo + 1), (cfg, len(graded))

        sidelog = load_sidelog_first_records(cfg)
        dup_ids = sorted(iid for iid, recs in sidelog.items() if len(recs) > 1)
        if dup_ids:
            diag["duplicate_ids"].extend((cfg, iid) for iid in dup_ids)

        for iid in range(lo, hi + 1):
            if iid in dup_ids:
                lineno, first_rec = sidelog[iid][0]
                first_text = first_rec.get("final_text_head", "") or ""
                first_len = first_rec.get("final_text_len", 0) or 0
                truncated = first_len > 500
                if truncated:
                    print(f"WARNING: {cfg} id={iid} first-draw text truncated in "
                          f"side-log ({first_len} chars, only 500 stored) — "
                          f"grading on truncated text, flag for review",
                          file=sys.stderr)
                inst_path = inst_tpl.format(iid)
                correct = grade_response_text(
                    cfg_data, domain_pddl, inst_path, first_text, plan_file
                )
                diag["first_draw_regraded"].append({
                    "cfg": cfg, "iid": iid, "lineno": lineno,
                    "first_text_len": first_len,
                    "first_loop_exhausted": first_rec.get("loop_exhausted"),
                    "first_draw_correct": correct,
                    "last_attempt_correct": graded[iid]["correct"],
                    "truncated_in_sidelog": truncated,
                })
                out[(cfg, iid)] = correct
            else:
                out[(cfg, iid)] = graded[iid]["correct"]
    return out, diag


def load_single_record_cell(cfgs, engine):
    """{(cfg, iid): bool_correct} for a cell with no re-draws (NT, Mystery WT)."""
    out = {}
    for cfg in cfgs:
        graded = load_graded(cfg, engine)
        cfg_data = load_config(cfg)
        lo, hi = cfg_data["start"] + 1, cfg_data["end"] + 1
        assert len(graded) == (hi - lo + 1), (cfg, len(graded), hi - lo + 1)
        for iid in range(lo, hi + 1):
            out[(cfg, iid)] = graded[iid]["correct"]
    return out


def main():
    print("=" * 70)
    print("STEP 1: reconstruct clean-WT first-draw outcome vector")
    print("=" * 70)
    clean_wt_first, diag = reconstruct_clean_wt_first_draw()
    n = len(clean_wt_first)
    x_first = sum(1 for v in clean_wt_first.values() if v)

    print(f"\nDuplicate ids found: {diag['duplicate_ids']}")
    print(f"n duplicates: {len(diag['duplicate_ids'])}")
    print("\nPer-duplicate first-draw regrade detail:")
    for row in diag["first_draw_regraded"]:
        print(f"  {row['cfg']} id={row['iid']}: first_text_len={row['first_text_len']} "
              f"loop_exhausted={row['first_loop_exhausted']} "
              f"first_draw_correct={row['first_draw_correct']} "
              f"last_attempt_correct={row['last_attempt_correct']} "
              f"truncated_in_sidelog={row['truncated_in_sidelog']}")

    # cross-check: last-attempt total from the same reconstruction path
    # (should reproduce 418/600 exactly, using graded-corpus values throughout)
    last_attempt_vals = {}
    for cfg in CLEAN_CFGS:
        graded = load_graded(cfg, WT_ENGINE)
        for iid, r in graded.items():
            last_attempt_vals[(cfg, iid)] = r["correct"]
    x_last = sum(1 for v in last_attempt_vals.values() if v)

    print(f"\nTotal pool n = {n} (expect 600)")
    print(f"First-draw correct  = {x_first}/600  (anchor: 410)")
    print(f"Last-attempt correct = {x_last}/600  (anchor: 418, published)")
    if n != 600:
        print("*** DISCREPANCY: pool size != 600 ***")
    if x_first != 410:
        print(f"*** DISCREPANCY: first-draw total {x_first} != anchor 410 — "
              f"reporting measured value, NOT forcing the anchor ***")
    if x_last != 418:
        print(f"*** DISCREPANCY: last-attempt total {x_last} != published anchor 418 ***")

    print("\n" + "=" * 70)
    print("STEP 2a: Wilson 95% CI on first-draw clean-WT count")
    print("=" * 70)
    lo_ci, hi_ci = wilson(x_first, 600)
    print(f"first-draw clean WT: {x_first}/600 = {100*x_first/600:.1f}%  "
          f"Wilson 95% CI [{100*lo_ci:.1f}, {100*hi_ci:.1f}]")

    print("\n" + "=" * 70)
    print("STEP 2b: McNemar first-draw clean WT vs matched-NT clean")
    print("=" * 70)
    nt_clean = load_single_record_cell(CLEAN_CFGS, NT_ENGINE)
    assert set(nt_clean.keys()) == set(clean_wt_first.keys())
    x_nt = sum(1 for v in nt_clean.values() if v)
    b = sum(1 for k in clean_wt_first if clean_wt_first[k] and not nt_clean[k])
    c = sum(1 for k in clean_wt_first if not clean_wt_first[k] and nt_clean[k])
    p = mcnemar_exact(b, c)
    delta = (x_first - x_nt) / 6
    p1, p2 = x_first / 600, x_nt / 600
    se = math.sqrt((b + c) / 600**2 - ((b - c) / 600) ** 2 / 600)
    ci_lo = (p1 - p2) - 1.959964 * se
    ci_hi = (p1 - p2) + 1.959964 * se
    print(f"matched-NT clean: {x_nt}/600 = {100*x_nt/600:.1f}%")
    print(f"first-draw WT {x_first}/600 vs NT {x_nt}/600  "
          f"paired delta = {delta:+.1f}pp [{100*ci_lo:+.1f}, {100*ci_hi:+.1f}]")
    print(f"discordant pairs: b={b} (WT correct, NT wrong)  "
          f"c={c} (WT wrong, NT correct)")
    print(f"exact two-sided McNemar p = {p:.6g}")

    print("\n" + "=" * 70)
    print("STEP 2c: clean-vs-Mystery WT paired delta, first draw")
    print("=" * 70)
    mystery_wt = load_single_record_cell(MYSTERY_CFGS, WT_ENGINE)
    x_mystery = sum(1 for v in mystery_wt.values() if v)
    diffs_b = diffs_c = 0
    for (cfg, iid), correct in clean_wt_first.items():
        mkey = ("mystery_" + cfg, iid)
        mcorrect = mystery_wt[mkey]
        if correct and not mcorrect:
            diffs_b += 1
        elif mcorrect and not correct:
            diffs_c += 1
    d = (x_first - x_mystery) / 6
    p_cm = mcnemar_exact(diffs_b, diffs_c)
    print(f"Mystery WT (unaffected, single-record): {x_mystery}/600 = "
          f"{100*x_mystery/600:.1f}%")
    print(f"clean WT (first draw) {x_first}/600 vs Mystery WT {x_mystery}/600")
    print(f"|clean_WT_first - mystery_WT| = {abs(d):.2f}pp  "
          f"(signed clean-minus-mystery = {d:+.2f}pp)")
    print(f"discordant pairs: b={diffs_b} c={diffs_c}  exact p={p_cm:.6g}")
    margin = 7.5
    within = abs(d) <= margin
    print(f"pre-registered margin check: |delta| = {abs(d):.2f}pp vs +-{margin}pp margin "
          f"-> {'WITHIN margin' if within else 'EXCEEDS margin'}")

    print("\n" + "=" * 70)
    print("SUMMARY (paste-ready)")
    print("=" * 70)
    print(f"first-draw clean WT: {x_first}/600 = {100*x_first/600:.1f}% "
          f"[{100*lo_ci:.1f}, {100*hi_ci:.1f}]")
    print(f"paired delta vs matched-NT: {delta:+.1f}pp  b={b} c={c}  p={p:.3g}")
    print(f"clean-vs-Mystery first-draw paired delta: {d:+.2f}pp  "
          f"b={diffs_b} c={diffs_c}  p={p_cm:.3g}  "
          f"({'within' if within else 'EXCEEDS'} +-{margin}pp margin)")


if __name__ == "__main__":
    main()
