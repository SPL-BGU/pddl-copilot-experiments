# nt-ster H4 checkpoint (2026-08-29)

Frozen copy of the nt-ster H4 corpus and its derived artefacts, so the analysis can be
reproduced **without re-syncing from the cluster and without re-running the regrader**.

Every number in `development/ntster_h4_final_readout_20260829.md` (as revised
2026-08-30 after the PR #96 review — the frozen scripts were fixed and re-frozen, see
prereg §8 item 9 second addendum and §9.2) comes from these files. The run is closed:
all six units PASS, paper-level branch PASS.

## Restore recipes

**You want to re-run the verdict scripts** (no resync, no regrade). Since the 08-30
revision `ntster_h4.py` also needs the RAW cells: its §3.7 mechanism section joins each
overlay row back to `results/ntster-h4-live/<cell>/trials.jsonl` for `failure_reason` /
`response` / `tokens`, which the overlay does not carry.

```bash
unzip -q checkpoints/e2e-overlay/ntster-h4-live_overlay.zip -d results/derived/e2e_overlay/
mkdir -p results/ntster-h4-live
for z in checkpoints/ntster-h4-live/*_trials.zip; do
    case "$z" in *void-parseron*) continue;; esac
    unzip -q "$z" -d results/ntster-h4-live/
done
python3 tools/ntster_f_gate.py --overlay-dir results/derived/e2e_overlay/ntster-h4-live \
    --out results/derived/ntster_f_gate.json
python3 tools/ntster_h4.py --overlay-dir results/derived/e2e_overlay/ntster-h4-live \
    --f-gate results/derived/ntster_f_gate.json
```

Verified 2026-08-30 (clean-room restore into a temp tree): restoring overlay + raw
cells from these zips and re-running the re-frozen scripts reproduces the revised
results **bit-identically** modulo the recorded input paths. (The pre-revision reports
and the pre-revision `derived_reports.zip` are in git history if the 08-29 shipped
values are ever needed for comparison.)

**You want the numbers without running anything:**

```bash
unzip -q checkpoints/ntster-h4-live/derived_reports.zip -d results/derived/
```

**You want to re-grade from raw trials** (only if the grader or ground truth changes):

```bash
mkdir -p results/ntster-h4-live
for z in checkpoints/ntster-h4-live/*_trials.zip; do
    case "$z" in *void-parseron*) continue;; esac
    unzip -q "$z" -d results/ntster-h4-live/
done
python3 tools/e2e_regrade.py results/ntster-h4-live --no-mcp
```

Note `results/derived/gt_cache.json` must be present — the frozen scripts call
`assert_gate()` before reading a single trial and will refuse to start without it
(rebuild with `tools/build_gt_cache.py` on a fresh clone). `gt_cache_stamp.json` is
committed to the repo since 2026-08-30, and the gate additionally compares the cache
against the preregistered pin `6af57125bde3…` hard-coded in `gt_cache_gate.py`, so a
rebuilt cache is checked against the ratified apparatus, not just its own stamp.

## Contents

| file | size | holds |
|---|---:|---|
| `../e2e-overlay/ntster-h4-live_overlay.zip` | 684K | all 6 `*.e2e.jsonl` overlays — **the analysis input** |
| `Qwen3_5_4B_off_trials.zip` | 9.3M | raw cell, 9,120 rows |
| `Qwen3_5_9B_off_trials.zip` | 13M | raw cell, 9,120 rows |
| `Qwen3_5_9B_on_trials.zip` | 15M | raw cell, 9,120 rows (parser-off rerun) |
| `gemma4_26b-a4b_off_trials.zip` | 5.2M | raw cell, 9,120 rows |
| `qwen3_6_35b_off_trials.zip` | 12M | raw cell, 9,120 rows |
| `qwen3_6_35b_on_trials.zip` | 13M | raw cell, 9,120 rows (parser-off rerun) |
| `void-parseron_trials.zip` | 884K | **the failure record** — the two void parser-on cells |
| `derived_reports.zip` | 310K | F gate, H4 results + report, §4(b) factorial (all 08-30 revised), the GT-cache stamp, and the 08-22 partials |

639 MB raw → 70 MB stored. Largest single file 15 MB, well inside GitHub's 100 MB limit.
Layout mirrors `checkpoints/iss024d-e2e-live/`; unlike that set the cell name carries
`_off`/`_on`, because 9B and 35b each contribute two cells here.

**`void-parseron_trials.zip` is evidence, not junk.** It holds the two cells from job
`20392801` whose rows came back with empty `response` and empty `thinking` — the
apparatus failure declared in prereg §9.1 deviation 2 and §2.3(A)'s amendment. The
appendix cites it. Do not prune it, and do not let it near `results/ntster-h4-live/`:
its cell directories share names with the live reruns, so unpacking it into the live
corpus would merge void rows into good cells.

## sha256

```
93a76b2bc750749191416c1a72accb14ddf5ad9d8cb65ef38bb65c30adc2cd1b  ../e2e-overlay/ntster-h4-live_overlay.zip
9c7c048873721c3ed54c5269ed8ae57281f1419c8270dea0bbd40af135633451  Qwen3_5_4B_off_trials.zip
60cc9af55476acaaba5521fda51878be42a3dadee16306699f7ce79ef6f57478  Qwen3_5_9B_off_trials.zip
3162a0954e1578f6c9259787dfc9b147066d0cb3030375902b2b94b0c66f362a  Qwen3_5_9B_on_trials.zip
9ea4df45aa2638323e62f2d8e98c018bd861ca3003587799f0eec083814272dd  gemma4_26b-a4b_off_trials.zip
2c05c1c33441de84af09e4751f2eb6d0a1f0dceeb2573e183bd8456b5654ed4b  qwen3_6_35b_off_trials.zip
a2d47eb4986ea15115cb497648ca8f7379b8528c9b381a18d9336b54e2077a5d  qwen3_6_35b_on_trials.zip
8ffe967cab5f638ed974e3d3187d2cfb4ee59f9b7544b899a0a41bceebc85281  void-parseron_trials.zip
7242df7f123c9b8a85be01245685d93064ad0ba50ad0cda0a32231429281ad23  derived_reports.zip
```

Verify with `shasum -a 256 -c` after adding a `checkpoints/ntster-h4-live/` prefix, or
just `unzip -tqq` each file — all nine tested OK at commit time.

## Provenance

Jobs `20392775` (off-mode 9B/gemma/35b), `20490174` (4B off-mode), `20489912` (on-mode
parser-off rerun); all COMPLETED `0:0`. Analysis scripts: originally frozen at
`ff7bbd7` (+ `ntster_factorial.py` 2026-08-29), **superseded by the 2026-08-30
post-review corrective re-freeze** — current five sha256s in
`development/reference/ntster_h4_prereg.md` §8 item 9 second addendum, deviations in
§9.2. GT gate `6af57125bde3…` (now also pinned as a constant in `gt_cache_gate.py`).
Cluster pinned at `6007032` / `5e4f9c0`, vLLM v0.20.2.
