"""Markdown readout. Numbers and registered labels only; no interpretation."""
from __future__ import annotations

def _f(x, nd=1):
    return "–" if x is None else f"{x:.{nd}f}"


def _n(x):
    return "–" if x is None else str(x)


def _iv(b):
    return "–" if b is None else f"[{b['lo']:.1f}, {b['hi']:.1f}]"


def _status(ic: list) -> str:
    """Each input cell with its §3 parity verdict AND consequence, so a
    job-level parity failure shows on every E2/E3/R line, as in E1. The
    consequence is bracketed because CONSEQ_CELL_FAIL itself contains '; '."""
    return "; ".join(f"{c['cell']}: {c['parity_verdict']} [consequence: {c['consequence']}]"
                     for c in ic)


def render(res: dict) -> str:
    L: list[str] = []
    L.append(f"# Delivered rerun readout ({res['mode']})\n")
    L.append(f"Package sha256: `{res['package_sha256']}`. Prereg: "
             "`development/reference/delivered_rerun_prereg.md`.\n")
    if res["mode"] == "fixture":
        L.append("**FIXTURE MODE: synthetic data, not an experiment result.**\n")
    if res["audited_tripwires"]:
        L.append("## Audited tripwires (§8b item 15)\n")
        L.append("Fired, then released by the operator with the audit note below "
                 "(verbatim).\n")
        for k, v in res["audited_tripwires"].items():
            L.append(f"- `{k}`: {v}")
            L.append(f"  - audit note: {res['audit_notes'][k]}")
        L.append("")

    L.append("## Corpus checks (§2, §7, §8a)\n")
    L.append("The last three columns are descriptive (rerun cells only): answers starting "
             "with the registered leaked prefix, answers starting with it twice (only the "
             "first is stripped), and answers that still contain a channel marker after the "
             "strip.\n")
    L.append("| cell | rows | torn lines | exception rows | infra rows | scoring-error rows "
             "| storage cuts | leaked prefix | doubled prefix | marker left after strip |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for c in res["corpus"]:
        L.append(f"| {c['cell']} | {c['rows']} | {c['torn_lines']} | {c['exception_rows']} "
                 f"| {c['infra_rows']} | {c['scoring_error_rows']} | {_n(c['storage_cuts'])} "
                 f"| {_n(c['prefix_rows'])} | {_n(c['doubled_prefix_rows'])} "
                 f"| {_n(c['residual_marker_rows'])} |")
    L.append("")

    p = res["parity"]
    L.append("## Parity guard (§3), evaluated before any delivered number\n")
    L.append(f"Job level: **{p['job']}**. Qwen cells meeting the criterion: "
             f"{p['qwen_met']} / 20. Cells with |Δ̂| > 10: "
             f"{', '.join(p['gross_cells']) or 'none'}. Gemma evaluated first: "
             f"{p['gemma_evaluated_first']}; any Gemma cell failed: {p['gemma_failed']}; "
             f"noise floor F = {_f(p['noise_floor_F'])}.\n")
    L.append("Apparatus deltas against the canonical corpus (§2):\n")
    L.extend(f"- {d}" for d in res["apparatus_deltas"])
    L.append("")
    L.append("| model | task | arm | paired | unpaired (rerun/canon) | TV rerun | TV canon "
             "| Δ̂ | 90% CI (domain boot) | verdict | Newcombe 90% (secondary) "
             "| clipped before a tool call | consequence |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in p["cells"]:
        nc = c["newcombe90"]
        L.append(f"| {c['model']} | {c['task']} | {c['arm']} | {c['n_paired']} | "
                 f"{c['unpaired_rerun']}/{c['unpaired_canonical']} | {_f(c['tv_rerun_pct'])} | "
                 f"{_f(c['tv_canonical_pct'])} | {c['delta']:+.1f} | {_iv(c['ci90'])} | "
                 f"{c['verdict']} | [{nc[1]:+.1f}, {nc[2]:+.1f}] | "
                 f"{c['clipped_before_tool_call']} | {c['consequence']} |")
    L.append("")

    L.append("## Part C parity (§2; reported, not a gate on E2)\n")
    L.append("Part C − canonical no-tools on the stored online grade, paired; simulate "
             "excluded.\n")
    L.append("| model | task | paired | unpaired (rerun/canon) | Part C | canonical | Δ̂ "
             "| 90% CI (domain boot) | verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for c in res["part_c_parity"]:
        L.append(f"| {c['model']} | {c['task']} | {c['n_paired']} | "
                 f"{c['unpaired_rerun']}/{c['unpaired_canonical']} | {_f(c['tv_rerun_pct'])} "
                 f"| {_f(c['tv_canonical_pct'])} | {c['delta']:+.1f} | {_iv(c['ci90'])} | "
                 f"{c['verdict']} |")
    L.append("")

    L.append("## E1. Delivered rate per cell (§4), exact\n")
    L.append("No-room rows (§8a) and harness exception rows (§7) are counted as delivered "
             "failures; their counts are shown. Each rate carries its cell's §3 parity "
             "verdict and consequence. The last two count columns are descriptive: "
             "answers starting with the leaked prefix twice (only the first is stripped) "
             "and answers that still contain a channel marker after the strip.\n")
    L.append("| model | task | arm | n | delivered | 95% CI | tool-verified | invocation "
             "| no-room n (%) | exception rows | leaked prefix stripped | doubled prefix "
             "| marker left after strip | parity verdict | consequence |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in res["e1"]:
        L.append(f"| {c['model']} | {c['task']} | {c['arm']} | {c['n']} | "
                 f"{_f(c['delivered_pct'])} | {_iv(c['ci95'])} | {_f(c['tool_verified_pct'])} "
                 f"| {_f(c['invocation_pct'])} | {c['no_room_n']} ({_f(c['no_room_pct'])}) "
                 f"| {c['exception_n']} | {c['prefix_n']} | {c['doubled_prefix_n']} "
                 f"| {c['residual_marker_n']} | {c['parity_verdict']} | {c['consequence']} |")
    L.append("")

    for key, title in (("e2", "E2. Availability contrast, tools-plain (Part A) − no-tools "
                              "(Part C) (§4)"),
                       ("e3", "E3. Steering contrast, steered − plain (§4)")):
        # Column names come from the contrast rows (analysis.CONTRAST_SIDES,
        # review F5), so the column holding the no-tools rate is named for it.
        sides = {(c["a_label"], c["b_label"]) for c in res[key]}
        if len(sides) != 1:
            raise ValueError(f"{key}: rows disagree on their side labels {sides}")
        a_name, b_name = sides.pop()
        L.append(f"## {title}\n")
        if key == "e2":
            L.append(res["e2_caveat"] + "\n")
        L.append(f"Δ̂ = {b_name} − {a_name}, paired.\n")
        L.append(f"| model | task | pairs | unpaired ({a_name} / {b_name}) | {a_name} "
                 f"| {b_name} | Δ̂ | 95% CI | p (domain sign-flip) | p (Holm, 15) "
                 f"| input cells: parity verdict [consequence] |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for c in res[key]:
            L.append(f"| {c['model']} | {c['task']} | {c['n_pairs']} | "
                     f"{c['unpaired_a']} / {c['unpaired_b']} | {_f(c['a_pct'])} | "
                     f"{_f(c['b_pct'])} | {_f(c['delta'])} | {_iv(c['ci95'])} | "
                     f"{c['p']:.4g} | {c['p_holm']:.4g} | {_status(c['input_cells'])} |")
        L.append("")

    L.append("## E4. Delivery gap among trials with a correct tool result (§4)\n")
    cats = list(res["e4"][0]["categories"]) if res["e4"] else []
    L.append("| model | task | arm | tool-correct | gap | gap % | " + " | ".join(cats) + " |")
    L.append("|---|---|---|---|---|---|" + "---|" * len(cats))
    for g in res["e4"]:
        L.append(f"| {g['model']} | {g['task']} | {g['arm']} | {g['n_tool_correct']} | "
                 f"{g['n_gap']} | {_f(g['gap_pct'])} | "
                 + " | ".join(str(g["categories"][c]) for c in cats) + " |")
    L.append("")

    r = res["readings"]
    L.append("## Registered readings (§5)\n")
    L.append(f"- **R1** (E2, Gemma validate_plan; Δ̂ {r['R1']['delta']:+.1f}, 95% CI "
             f"[{r['R1']['ci95'][0]:.1f}, {r['R1']['ci95'][1]:.1f}]): {r['R1']['label']}")
    L.append(f"  - input cells: {_status(r['R1']['input_cells'])}")
    L.append(f"- **R2** (E3, Gemma validate_plan; Δ̂ {r['R2']['delta']:+.1f}, 95% CI "
             f"[{r['R2']['ci95'][0]:.1f}, {r['R2']['ci95'][1]:.1f}]): {r['R2']['label']}")
    L.append(f"  - input cells: {_status(r['R2']['input_cells'])}")
    L.append(f"- **R3**: {r['R3']['label']} (models with an E3 validate_plan gain above +5: "
             f"{', '.join(r['R3']['models_with_e3_gain_above_5']) or 'none'})")
    L.append(f"  - input cells: {_status(r['R3']['input_cells'])}")
    per = "; ".join(f"{m} {_f(v['delivered_pct'])}% of {v['n']}"
                    for m, v in r["R4"]["per_model"].items())
    L.append(f"- **R4** (solve, tool-verified, full uncut answer: {per}): {r['R4']['label']}")
    L.append(f"  - input cells: {_status(r['R4']['input_cells'])}")
    pl = r["R5"]["neutral_minus_minimal_plain"]
    st = r["R5"]["neutral_minus_minimal_steered"]
    L.append(f"- **R5** (neutral-plain − minimal-plain invocation {pl['est']:+.1f}, 90% CI "
             f"{_iv(pl)}): {r['R5']['label']}")
    L.append(f"- **R5, steering** (neutral-steered − minimal-steered invocation "
             f"{st['est']:+.1f}, 90% CI {_iv(st)}): {r['R5']['steering_label']}")
    L.append("")
    L.append("| 2 × 2 cell | n | invocation | 95% CI | delivered | 95% CI |")
    L.append("|---|---|---|---|---|---|")
    for name, c in r["R5"]["cells"].items():
        L.append(f"| {name} | {c['n']} | {_f(c['invocation_pct'])} | {_iv(c['invocation_ci95'])} "
                 f"| {_f(c['delivered_pct'])} | {_iv(c['delivered_ci95'])} |")
    L.append("")
    return "\n".join(L) + "\n"
