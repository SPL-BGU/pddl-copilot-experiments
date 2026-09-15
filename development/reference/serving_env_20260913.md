# Serving environment audit — 2026-09-13

**Purpose.** Pins the "computing infrastructure" facts for the paper (Methodology,
"Models and Serving", and the Reproducibility Checklist item) and records the vLLM
version that actually served every canonical cell. Sources: the read-only probe
`cluster-experimenting/probe_serving_env.sh` (login node + one 3-minute `srun` per GPU
class), the preserved serve logs under `cluster-experimenting/logs/` (the
`Initializing a V1 LLM engine (vX.Y.Z)` banner, one per job), `sacct`, GitHub blob
hashes of the parser files at the two release tags, and a local comparison of the one
cell that exists at both versions. Tex landed as `paper/aaai27` `4eb4751`, pushed 2026-09-14 and
Overleaf-synced (`d884bd3`, Action run 34814416712).

## 1. Versions the tex states

| component | value | how it was read |
|---|---|---|
| vLLM | **0.20.2** — `docker://vllm/vllm-openai:v0.20.2` (sbatch pin), served banner `v0.20.2` in 166 of 178 preserved serve logs | pip metadata inside `~/vllm.sif` on a compute node; serve-log banners |
| PyTorch | 2.11.0+cu130 | image |
| CUDA runtime | 13.0 (`nvcc` cuda_13.0.r13.0); cuDNN 91900 | image |
| other image packages | transformers 5.8.0, triton 3.6.0, flashinfer-python 0.6.8.post1, xformers absent | image |
| image OS | Ubuntu 22.04.5 LTS | image |
| Apptainer | 1.4.5-3.el9 | compute node |
| host OS | Rocky Linux 9.7 (Blue Onyx), kernel 5.14.0-611.47.1.el9_7.x86_64 (kernel built 2026-04-08, i.e. before every sweep) | `srun` on `ise-6000-01` and `ise-6000p-03`; `scontrol show node` `OS=` identical on every GPU node |
| NVIDIA driver | 595.58.03 (driver CUDA API 13.2) | `nvidia-smi` on both GPU classes |
| GPU | NVIDIA RTX 6000 Ada Generation, 49,140 MiB (48 GB) | the `nvidia-smi` line at the top of every canonical job `.out`; `sacct` `gres/gpu:rtx_6000=1` |
| per-job allocation | 1 GPU, 6 CPU cores, 48 GB host RAM, partition `main` | `sacct` `AllocTRES` |

Caveat: the driver and OS readings are the node image as of 2026-09-13. The kernel
build date predates all sweeps (first canonical job 2026-05-24), but the driver's
install date is not recorded anywhere and the sweep-time job logs do not print it.

## 2. GPU class per corpus

- **RTX 6000 Ada (48 GB)**: all 40 canonical cells (`sweep5v2-live` + `sweep6-live`,
  jobs 2026-05-24 → 06-02), `decoupled-rollup` (06-26/27), `iss024d-e2e-live`
  (07-11/12), `ntster-h4-live` (08-20/22). Every one of these jobs' `.out` files
  prints `NVIDIA RTX 6000 Ada Generation, 49140 MiB`.
- **RTX PRO 6000 Blackwell (96 GB)**: used only by pre-roster jobs (`gemma4_31b`,
  2026-05-01 → 05-14; one 0.8B job on 05-01), PlanBench open-weight smoke jobs
  (05-18, 06-15) and the gpt-oss-120b smoke. None of them feeds a paper number.
  The tex's earlier "single 48 GB and 96 GB GPUs" was therefore corrected to 48 GB.
- **RTX 3090 (24 GB)**: PlanBench open-weight jobs (06-02, 06-06); not in the paper.
- Frontier corpora (Haiku, Sonnet) are Anthropic-API served; no vLLM.

## 3. Served vLLM version per canonical cell (authoritative = serve-log banner)

**Timeline of the drift.** Job `17929029_1` (raw id 17929031, Qwen3.5-0.8B
think=off with-tools, canonical) started 2026-05-29 16:38 with no cached image,
built `docker://vllm/vllm-openai:latest` (then 0.22.0) and re-cached it at 16:54.
Every job that started between 16:54 and the 2026-05-31 23:34 reseed copied 0.22.0
while logging `Using cached vllm.sif`. Array tasks receive their own raw job ids when
they start (e.g. `17929029_4` = 17929034), which is why the `.out` file names carry
the parent template's model name; the cell is identified by the `OUT_DIR` inside.

| corpus / cell (with-tools unless noted) | writer job(s) | server start | served vLLM |
|---|---|---|---|
| canonical Qwen3.5-0.8B off | 17929031 (05-29 16:38, **0.22.0**, backed up `.v0220-bak`), 17938767 (05-31 00:03, **0.22.0**, `.v0220-2nd-bak`), 17952038 (06-01 12:12, 0.20.2, FAILED after 8 min), 17952335 (06-01 13:01, 0.20.2, resumed, COMPLETED) | — | **0.20.2** (live cell = the 06-01 rerun) |
| canonical Qwen3.5-0.8B on | 17929029_0 = 17929030 | 05-29 11:42 | 0.20.2 |
| canonical Qwen3.5-4B on | 17929029_2 = 17929032 | 05-29 16:57 | **0.22.0** |
| canonical Qwen3.5-4B off | 17929029_3 = 17929033 | 05-29 18:46 | **0.22.0** |
| canonical Qwen3.5-9B on | 17929029_4 = 17929034 | 05-30 00:45 | **0.22.0** |
| canonical Qwen3.5-9B off | 17929029_5 = 17929035 | 05-30 03:12 | **0.22.0** |
| canonical Gemma off / on | 17929029 / 17929446 | 05-28 | 0.20.2 |
| canonical Qwen3.6-35B off / on | 17929392 / 17929374 | 05-28 | 0.20.2 |
| canonical no-tools, all 10 cells | reused from sweep-5 (jobs 17810530–17813112, 05-24/25) | 05-24/25 | 0.20.2 |
| anon Qwen3.5-0.8B on / off | 17929036_0 = 17929037 / 17929036_1 = 17929038 | 05-30 04:10 / 08:47 | **0.22.0** |
| anon Qwen3.5-4B on / off | 17929036_2 = 17929039 / 17929036_3 = 17929040 | 05-30 15:54 / 19:11 | **0.22.0** |
| anon Qwen3.5-9B on | 17929036_4 (05-30 20:52, **0.22.0**, FAILED 06-01 09:49 at 7,240 rows) + 17952040 (06-01 12:12, 0.20.2, resumed to 9,120) | — | **mixed: 7,240 rows 0.22.0 + 1,880 rows 0.20.2** |
| anon Qwen3.5-9B off | 17929036_5 = 17929042 | 05-30 22:26 | **0.22.0** |
| anon Gemma on | 17929036_8 = 17932112 | 05-29 23:10 | **0.22.0** (Gemma tool parser differs, §4) |
| anon Gemma off | 17929036 | 05-28/29 | 0.20.2 |
| anon Qwen3.6-35B off / on | 17931462 / 17931319 | 05-28 | 0.20.2 |
| anon no-tools, all 10 cells | 17929022–17929028, 17929043/44, 17929341 | 05-28/29 (before the flip) | 0.20.2 |
| decoupled-rollup, iss024d-e2e, ntster-h4 (all cells) | see logs 06-26 → 08-22 | — | 0.20.2 |

**Blast radius.** Canonical corpus: 4 cells fully at 0.22.0 (Qwen3.5-4B and 9B,
both modes, with-tools; 36,480 trials). Anonymized corpus: 6 cells fully at 0.22.0
plus the 9B think=on cell for its first 7,240 rows, plus the Gemma think=on
with-tools cell. Everything else at 0.20.2. The anonymized with-tools cells enter no
reported number (the tex's contamination tables are no-tools only).

**Correction to the 2026-05-31 audit** (memory note, never written to the repo): it
listed five affected cells and assumed the rest "started before the flip". `sacct`
start times show the 4B/9B canonical tasks started 16:57–03:12 on 05-29/30, after
it. The serve-log banner is the only authoritative per-cell check.

## 4. Parser code between the two releases (GitHub blob SHAs at tags `v0.20.2` and `v0.22.0`)

| file | status |
|---|---|
| `vllm/tool_parsers/qwen3xml_tool_parser.py` (the Qwen3.5 tool parser, `--tool-call-parser qwen3_xml`) | **identical** |
| `vllm/reasoning/qwen3_reasoning_parser.py` (the Qwen3.5 reasoning parser) | **identical** |
| `vllm/reasoning/gemma4_reasoning_parser.py`, `vllm/tool_parsers/gemma4_utils.py`, `functiongemma_tool_parser.py`, the qwen3xml/qwen3/gemma4-reasoning/hermes tests | identical |
| `vllm/tool_parsers/gemma4_tool_parser.py` | **changed** |
| `vllm/tool_parsers/abstract_tool_parser.py`, `hermes_tool_parser.py`, `qwen3coder_tool_parser.py`, `tool_parsers/__init__.py` | changed (not used by the roster: Qwen3.5 → qwen3_xml, Gemma → gemma4) |

So at the parser level the Qwen3.5 cells are unaffected; the one Gemma cell served by
0.22.0 (anonymized, think=on, with-tools) ran a different tool parser and is not
quoted anywhere.

## 5. Measure-first comparison: the cell that exists at both versions

Qwen3.5-0.8B, think=off, with-tools, canonical corpus, 9,120 trials each.
`r1` = 0.22.0 run 17929031 (`results/sweep5-cluster-20260601/…_sweep5v2.v0220-bak`),
`r2` = 0.22.0 run 17938767 (`….v0220-2nd-bak`), `live` = 0.20.2 rerun 17952335
(`results/sweep5v2-live/slurm_vllm_Qwen3_5_0_8B_off_tools_all_minimal`). Harness
`success` field; Δ = live − r1 with a normal-approximation 95% CI.

| task / arm | 0.22.0 r1 | 0.22.0 r2 | 0.20.2 | Δ (pp) | 95% CI | n |
|---|---|---|---|---|---|---|
| simulate / neut | 6.67 | 5.67 | 6.33 | −0.33 | [−4.28, +3.61] | 300 |
| simulate / ster | 2.33 | 1.67 | 2.67 | +0.33 | [−2.16, +2.83] | 300 |
| solve / neut | 9.33 | 11.00 | 12.00 | +2.67 | [−2.27, +7.60] | 300 |
| solve / ster | 13.33 | 16.33 | 14.00 | +0.67 | [−4.83, +6.16] | 300 |
| validate_domain / neut | 88.61 | 88.61 | 87.50 | −1.11 | [−5.85, +3.63] | 360 |
| validate_domain / ster | 90.56 | 90.56 | 89.17 | −1.39 | [−5.80, +3.02] | 360 |
| validate_plan / neut | 22.00 | 23.07 | 23.23 | +1.23 | [−0.88, +3.35] | 3,000 |
| validate_plan / ster | 24.07 | 23.70 | 24.80 | +0.73 | [−1.44, +2.91] | 3,000 |
| validate_problem / neut | 27.50 | 27.33 | 26.17 | −1.33 | [−6.35, +3.68] | 600 |
| validate_problem / ster | 20.67 | 17.17 | 18.50 | −2.17 | [−6.66, +2.32] | 600 |
| **pooled** | 26.44 | — | 26.86 | **+0.43** | **[−0.86, +1.71]** | 9,120 |

No task×arm cell is CI-disjoint. The two 0.22.0 repeats of the same cell (identical
9,120 trial keys, temperature 0) differ from each other by as much as either differs
from the 0.20.2 run (e.g. solve/neut 9.33 vs 11.00), i.e. batched serving at
temperature 0 is not bit-reproducible and the version effect is inside that noise.
Failure-reason mix, pooled: r1 `tool_error` 4,911 / `ok` 2,411 / `verdict_mismatch`
749 / `loop_exhausted` 591 / `tool_not_selected` 330; 0.20.2: 4,854 / 2,450 / 767 /
567 / 336.

## 6. What the tex says, and the open decision

The Methodology sentence now states the versions in §1, drops the 96 GB claim, and
carries a footnote with the §3 provenance, the §4 parser identity and the §5
comparison. The checklist item "computing infrastructure" is `yes`.

**Decision (Omer, 2026-09-14): (a) keep the disclosure footnote** as the
reproducibility statement. The alternative, (b) rerunning the affected cells on
0.20.2 (4 canonical + 7 anonymized `rtx_6000` jobs of 10–45 h each, then
regenerating the e2e overlay, the pooled table, the figures, the decks and every
NUMBERS row that touches Qwen3.5-4B/9B with-tools), is not planned; it would only
become worth it if a reviewer or advisor asks for corpus uniformity. The parsers are
identical and the rerun check is within noise.

## 7. Re-running the probe

```
ssh omereliy@slurm.bgu.ac.il 'bash ~/pddl-copilot-experiments/cluster-experimenting/probe_serving_env.sh'
```
(the script needs the cluster checkout to carry it; on 2026-09-13 it was run from a
copy at `~/probe_serving_env.sh` because the cluster checkout sits on
`paper/iter2-decoupled-run`, whose remote branch no longer exists, so `git pull`
fails there). Raw outputs of this audit are in the session scratchpad only; every
number above is reproducible from the logs and results named.
