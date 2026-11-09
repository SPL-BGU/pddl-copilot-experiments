# Draft: licence and attribution, the Llama weight check, more small or MoE models

*Agent research, 2026-11-09. Nothing in the repo was changed. The licence part needs a check with the advisor or BGN before anything is published.*

I answered all three parts. I wrote nothing in the repo. Scratch files are in /private/tmp/claude-501/-Users-omereliyahu-personal-pddl-copilot-experiments/d36f9bd6-86d1-4650-9e26-e80ce0009ed2/scratchpad.

# 1. Licence and attribution

## 1a. BGU policy (what I checked, and what is still unclear)

**Source.** BGU University Procedure **14-007**, "קניין רוחני, המצאות שרות ומניעת ניגוד עניינים" (intellectual property, service inventions and conflicts of interest). Its published date is January 2011 (Tevet 5771). The live PDF is at https://www.bgu.ac.il/media/cj2hbgzy/14007.pdf. The old address, https://in.bgu.ac.il/osh/ResearchcharP/14007.pdf, now redirects to the BGU home page. Web Archive copies from 2022 to 2026 have the same content digest, so this text is current. The translations below are mine.

What I read in the procedure:
- **Software counts as an "invention".** Clause 3.1 lists "ידע, תוכנה או יישום מחשב ... אלגוריתם ... מודל" (know-how, software or a computer application ... algorithm ... model).
- **An MSc student counts as an "inventor".** Clause 3.5 says: "וכן סטודנט לתואר שני ומעלה או כל אדם אחר העוסק במחקר באוניברסיטה" ("and also a student for a master's degree or higher, or anyone else doing research at the university").
- **The university or BGN owns service inventions.** Clause 4.2.1: "הבעלות על כל המצאות השירות ועל כל הקניין הרוחני הקשור אליהן היא של האוניברסיטה ו/או ב.ג. נגב" (ownership of all service inventions and all related IP belongs to the University and/or B.G. Negev, which is BGN Technologies).
- **Disclosure is only required for commercial potential.** Clause 4.3.1 makes the duty to tell BGN apply to an inventor "הסבור שהמצאה ... הנה בעלת פוטנציאל מסחרי ומעוניין שהיא תנוצל" (who believes the invention has commercial potential and wants it exploited). Once someone has disclosed, clause 4.3.5 forbids publishing without BGN's written consent.
- **If BGN declines, the inventor may publish.** Clause 4.4.2(a): if BGN answers "not a service invention" or "no intent to exploit", "רשאי הממציא לפרסם את פרטי ההמצאה" (the inventor may publish).
- **A stipend changes the status.** A footnote on the disclosure form (Annex A) says an MSc student who gets no stipend or salary from BGU is treated as "פרטי" (private).
- **What the procedure does not cover.** It says nothing about copyright in papers or code, open-source licences, or who must be named as copyright holder. I found no separate BGU copyright or open-source procedure online.

**How the lab already does it** (checked with `gh api`, SPL-BGU org):
- 15 of the lab's own (non-fork) repos are MIT, 1 is Apache-2.0 (NumericPDDLGym), and 24 have no licence.
- The holder lines read "Copyright (c) 2025 SPL@BGU" (PlanningCopilot, pddl-problem-generator, BSS-Heuristics, pyvalidator) or "Search-BGU" (numeric-sam, PolyPlan).
- `../pddl-copilot` is MIT with "Copyright (c) 2025 SPL-BGU".
- This repo is **public and has no LICENSE file**.

**Verdict:**
- **Checked:** BGU's procedure treats research software by MSc students as a possible service invention owned by BGU or BGN. Telling BGN is required only when commercial potential is claimed.
- **Unclear:** whether an open-source release needs BGN sign-off, and whether the holder must be "Ben-Gurion University of the Negev", "BGN Technologies", or the author together with BGU.
- **Who to ask:**
  1. The advisor first: does the lab have a standing arrangement with BGN for open-source releases? The existing MIT repos suggest yes.
  2. Then BGN Technologies (https://bgn.bgu.ac.il/technology-licensing): a one-line email saying "research code, no commercial claim, MIT plus CC-BY-4.0, holder Omer Eliyahu and BGU".
  3. Whether Omer gets a BGU stipend changes his status under the Annex A footnote.

## 1b. MIT or Apache-2.0

**Evidence.** Papers with Code has shut down, so I took fresh counts from the GitHub search API:

| Topic | MIT | Apache-2.0 | Repos with 100+ stars (MIT / Apache) |
|---|---|---|---|
| machine-learning | 69,067 | 10,641 | 2,443 / 1,412 |
| deep-learning | 33,297 | 6,542 | 2,873 / 1,368 |
| llm | 83,442 | 15,755 | 2,455 / 1,455 |
| reinforcement-learning | 7,841 | 1,720 | 555 / 297 |
| pddl | 77 | 10 | |
| automated-planning | 35 | 18 | |

- MIT leads on every topic.
- Apache-2.0 leads for released model weights: 38.1% Apache vs 17.5% MIT on Hugging Face (arXiv 2402.05979).
- Software Heritage overall: MIT 39.3%, Apache 5.5% (arXiv 2405.16746).

**What actually differs between the two:**
- **Patents.** Apache-2.0 gives users an explicit patent licence and ends it if they sue over patents. MIT says nothing about patents. Under 14-007, BGU or BGN may hold patent rights in service inventions, so BGN may care which one is used. This is one more reason to ask them.
- **NOTICE file.** With Apache-2.0, a NOTICE file (for example "Developed by Omer Eliyahu, Ben-Gurion University of the Negev (SPL-BGU)") must be kept by anyone who redistributes the code. That is stronger attribution than MIT's copyright line. Apache also requires marking changed files.
- **Length.** MIT is short and fits the lab and sibling repo.

**Recommendation: MIT.** It is the more common licence for academic ML and planning code, it matches `../pddl-copilot` and 15 lab repos, and it avoids the patent question. Credit still comes through the copyright line, CITATION.cff and the DOI.

**Data notes:**
- CC-BY-4.0 should cover only data we made (results, generated broken variants).
- `domains/README.md` says 10 domains come from olam-compatible and patty/IPC-2023, and PlanBench material is third party. Those keep their own terms and need attribution.

## 1c. Drafts

**Copyright line** (for LICENSE; first commit is 2026-03-28, so update the years if the code is older):
```
Copyright (c) 2026 Omer Eliyahu and Ben-Gurion University of the Negev (SPL-BGU)
```
If BGN says the holder must be the university, the fallback is "Copyright (c) 2026 Ben-Gurion University of the Negev (SPL-BGU). Author: Omer Eliyahu."

**CITATION.cff:**
```yaml
cff-version: 1.2.0
message: "If you use this software or data, please cite it as below."
title: "pddl-copilot-experiments: evaluation harness for the PDDL Planning Copilot study"
type: software
authors:
  - family-names: Eliyahu
    given-names: Omer
    affiliation: "Ben-Gurion University of the Negev (SPL-BGU)"
    orcid: "https://orcid.org/XXXX-XXXX-XXXX-XXXX"   # placeholder
  # - add co-authors / advisor here (placeholder)
repository-code: "https://github.com/SPL-BGU/pddl-copilot-experiments"
license: MIT          # data files: CC-BY-4.0, stated in LICENSE-DATA and README
version: "X.Y.Z"      # placeholder, match the tagged release
date-released: "YYYY-MM-DD"
doi: "10.5281/zenodo.XXXXXXX"   # placeholder, filled after first Zenodo release
keywords: [PDDL, automated planning, LLM, tool use, MCP, evaluation]
references:
  - type: software
    title: "pddl-copilot (MCP planning tools marketplace)"
    authors:
      - name: "SPL-BGU"
    repository-code: "https://github.com/SPL-BGU/pddl-copilot"
    license: MIT
# preferred-citation: add the journal paper once it is no longer anonymous
```

**Zenodo setup:**
- Zenodo reads CITATION.cff when a GitHub release is made, and each release gets its own DOI.
- An SPL-BGU org owner has to switch the repo on in Zenodo's GitHub settings.
- If the venue is double-blind (TMLR is), only publish the CITATION.cff and DOI after decisions, or point reviewers at an anonymous mirror.

# 2. Llama 3.1 8B: are unsloth's weights the same as Meta's?

Pinned revision: `unsloth/Llama-3.1-8B-Instruct` @ `4699cc75b550f9c6f3173fb80f4703b62d946aa5` (in `cluster-experimenting/lib/defaults.sh`).

**Verdict: the weights are identical, byte for byte. No token was needed.**

**How I checked:**
- The Meta tree listing (`/api/models/meta-llama/Llama-3.1-8B-Instruct/tree/main`, rev `0e9e39f`) opens without a token. It hides the LFS sha256 values ("****") but shows the git id of each LFS pointer file.
- I rebuilt each pointer from unsloth's sha256 and file size and hashed it. All four shards match Meta's pointer ids exactly. A matching pointer means the same sha256 and size, so the files are the same bytes.

| Shard | sha256 (unsloth, now proven equal to Meta's) | Pointer git id (both repos) |
|---|---|---|
| model-00001-of-00004 | 2b1879f356aed350030bb40eb45ad362c89d9891096f79a3ab323d3ba5607668 | a59dca2886... |
| model-00002-of-00004 | 09d433f650646834a83c580877bd60c6d1f88f7755305c12576b5c7058f9af15 | 4ab0726caf... |
| model-00003-of-00004 | fc1cdddd6bfa91128d6e94ee73d0ce62bfcdb7af29e978ddcab30c66ae9ea7fa | 5864b15557... |
| model-00004-of-00004 | 92ecfe1a2414458b4821ac8c13cf8cb70aed66b5eea8dc5ad9eeb4ff309d6d7b | b8babcaa5a... |

`model.safetensors.index.json` is also identical (same git id, 0fd8120f).

**Small files differ only in metadata.** For the comparison I used ungated mirrors whose git ids equal Meta's, so they are exact copies: NousResearch (config, generation_config, special_tokens_map, tokenizer.json) and mlx-community (tokenizer_config.json).

| File | What differs |
|---|---|
| `config.json` | unsloth adds `pad_token_id: 128004`, `head_dim: 128` and `unsloth_fixed: true`, and sets `eos_token_id: 128009`. Meta has `[128001, 128008, 128009]`. |
| `generation_config.json` | unsloth adds `pad_token_id` and `max_length: 131072`. The eos list, temperature 0.6 and top_p 0.9 are the same. |
| `tokenizer.json` | Same vocabulary, same merges (unsloth stores them as pairs, Meta as strings) and same added tokens. Normalizer, pre-tokenizer, post-processor and decoder are all equal. |
| `tokenizer_config.json` | The chat template is identical. unsloth adds a pad token and `padding_side: left`, and names the class `PreTrainedTokenizer` where Meta has `PreTrainedTokenizerFast`. Transformers still loads the fast tokenizer from `tokenizer.json`. |
| `special_tokens_map.json` | unsloth adds a pad token. |

**Effect on our runs: none expected.**
- The harness sends temperature 0.
- vLLM takes its stop tokens from `generation_config`, and the eos lists there are equal.
- The chat template is replaced by vLLM's `tool_chat_template_llama3.1_json.jinja`.
- Padding does not matter for serving.

Omer does not need to run anything to settle this. If he wants a direct Meta-side listing anyway: `curl -s -H "Authorization: Bearer $HF_TOKEN" "https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct/tree/main" | python3 -c "import sys,json;[print(f['path'],f['lfs']['oid']) for f in json.load(sys.stdin) if f.get('lfs')]"`

# 3. More small or MoE models

## Smoke evidence from `results/d1-smokes/`

These are smoke-scale numbers, not study results, and they do not go in NUMBERS.md. Decode speed is tokens per second for each request while 4 requests run at once, taken from `eval_duration`. The task mix differs between runs, so only the speed column is a fair comparison.

| Model | Type | Speed (tok/s, with tools / no tools) | Empty answers (tools / no tools) | Calling rate with tools |
|---|---|---|---|---|
| gpt-oss-20b | MoE | 105 / 107 | 7% / 15% (all "truncated_no_answer") | 0.47 overall; validate_plan 18/20 skipped |
| Gemma 26B official BF16 | MoE | 84 / 86 | 0% / 0% | 0.88 |
| Gemma 26B AWQ | MoE | ~95 | | |
| Qwen3.6-35B | MoE | ~90 | | |
| Llama 3.1 8B | dense | 51 / 54 | 0% / 0% | 1.00 |
| Ministral 3 14B | dense | 47 / 50 | 11% / 0% (960 tool trials) | 0.89 |
| Qwen3.5-9B | dense | 43 to 47 | | |

The data backs Omer: the MoE models decode about twice as fast as the dense 8 to 14B models.

One finding on Llama: in both solve trials it called the planner with elided PDDL, `"(define (domain blocksworld) ...)"`, and got a tool error. This is data, not a serving fault.

## Candidates

Every name below was checked against the vLLM v0.20.2 source (tag `bc150f5`): the tool-parser registry, the reasoning-parser registry and the model architecture registry.

| Rank | Model (HF id) | Total / active params | Licence (gated?) | vLLM 0.20.2 parsers | Thinking control | GPU fit | What it adds |
|---|---|---|---|---|---|---|---|
| 1 | `zai-org/GLM-4.7-Flash` (Jan 2026) | 31.2B / ~3B, MoE | MIT (no) | tool `glm47`, reasoning `glm45`, arch `Glm4MoeLiteForCausalLM`, all present | `enable_thinking` in its chat template | BF16 62 GB: rtx_pro_6000 (an FP8 copy would fit rtx_6000) | New vendor (Zhipu), fast MoE, fits the think on/off design |
| 2 | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` (Dec 2025) | 31.6B / ~3.5B, hybrid Mamba plus MoE | NVIDIA Nemotron Open Model License (no) | tool `qwen3_coder`, reasoning `nemotron_v3` built in, arch `NemotronHForCausalLM` | `enable_thinking` True/False (model card) | 32.7 GB: rtx_6000 | New vendor and a new architecture type. Risk: prefix caching on hybrid models is not yet checked in our setup |
| 3 | `ibm-granite/granite-4.2-8b` (Aug 2026) | 8.8B, dense | Apache-2.0 (no) | `qwen3_coder` plus `nemotron_v3` (the card says vLLM 0.20+) | thinking on, off, or low effort | 17.6 GB: rtx_6000 | New vendor (IBM), fills the 8B rung, thinking on/off. It is dense, so expect speed like the 9B |
| 4 | `openai/gpt-oss-120b` | 117B / 5.1B, MoE | Apache-2.0 (no) | `openai`, `openai_gptoss` (already verified on the 20b) | effort low/medium/high | 65 GB: rtx_pro_6000, runs alone | A larger size of a family we already run, so a within-family size test |
| 5 | `allenai/Olmo-3-7B-Instruct` (`-Think` is a separate checkpoint) | 7.3B, dense | Apache-2.0 (no) | `olmo3`, arch `Olmo3ForCausalLM` | separate checkpoints, no switch | 14.6 GB: rtx_6000 | New vendor (AI2). Its training data is public, so contamination can be checked directly |

**Also possible:**
- `ibm-granite/granite-4.0-h-tiny`: MoE, 6.9B total and about 1B active, Apache-2.0, `granite4` parser, no thinking, 13.9 GB. The fast IBM option.
- `baidu/ERNIE-4.5-21B-A3B-PT`: MoE, Apache-2.0, `ernie45` parser, 44 GB. Too tight for rtx_6000, so rtx_pro_6000.
- Cheap size rungs that reuse flags we already verified: `Qwen/Qwen3.5-2B`, `google/gemma-4-E4B-it` and `-E2B-it` (`gemma4` parser), `mistralai/Ministral-3-8B` and `-3B-Instruct-2512` (`mistral` parser).

**Ruled out under the vLLM 0.20.2 pin:**
- LiquidAI LFM2.5-8B-A1B, LFM2.5-24B-A2B and LFM3-1.7B: they need the `lfm2` tool parser, and Liquid's docs say vLLM 0.23 or newer. LFM3's architecture is also missing from 0.20.2.
- `google/gemma-4-12B-it`: its architecture, `Gemma4UnifiedForConditionalGeneration`, is not in 0.20.2.
- Hunyuan-A13B: 80B, and its licence is not a standard open one.
- Mistral Small 4: 119B, too big for one card.
- Phi-4-mini (Feb 2025) and SmolLM3-3B: they work (`phi4_mini_json` and `hermes`), but they add little.

## Wave 1: which two families go first

**I agree with Omer's lean: gpt-oss-20b and Llama 3.1 8B.**
- **Two new vendors with very different behaviour.** gpt-oss is the fastest model we have, an MoE that always reasons and often skips the tool. Llama is dense, calls the tool every time, and gives no empty answers. That contrast is the most useful one for the calling gate.
- **Both serving paths are clean.** Neither needed a fix after the cache problem.
- **Llama's licence question is settled by part 2**, since the weights match Meta's.

**Trade-off against Ministral 3 14B:**
- Ministral would add a European vendor and the newest weights (Dec 2025). Its calling rate is 0.89.
- It is the slowest of the three (about 47 to 50 tok/s at 14B dense), and it has the most fragile serving path: it needed three fixes (9-character tool ids, no chat_template_kwargs, the context-overflow message).
- It also had 11% empty answers with tools.
- It fits better as the wave-2 tier.

**One caveat on gpt-oss.** The smoke sent no effort setting (the harness has none on main or the D1a branch), so it ran at the model's own default, which I believe is medium. Wave 1 plans low effort, so that exact setting has not been smoke-tested, and the 15% empty rate may change.

## Side finding (outside this brief, worth a check)

The Gemma 4 model card describes a thinking mode switched by `enable_thinking`, and vLLM 0.20.2 has a `gemma4` reasoning parser. The repo serves Gemma with `REASONING_PARSER=none`, and `development/CHANGELOG.md` says "gemma4 has no `<think>` tokens and ignores the kwarg". If the card is right, Gemma's think=on cells may have had real thinking turned on. I have not checked this against the stored rows.

**Sources:**
- BGU procedure 14-007: https://www.bgu.ac.il/media/cj2hbgzy/14007.pdf (Web Archive record at https://web.archive.org/cdx/search/cdx?url=in.bgu.ac.il/osh/ResearchcharP/14007.pdf)
- BGN technology licensing: https://bgn.bgu.ac.il/technology-licensing
- BGU constitution: https://www.bgu.ac.il/media/uusaqjoy/rules.pdf
- Licence shares on Hugging Face: https://arxiv.org/pdf/2402.05979
- Software Heritage and LLM4Code licences: https://arxiv.org/pdf/2405.16746
- Hugging Face supply chain: https://arxiv.org/html/2502.04484v2
- GitHub search API counts (gh CLI, 2026-11-09)
- HF API tree listings for `meta-llama/Llama-3.1-8B-Instruct`, `unsloth/Llama-3.1-8B-Instruct@4699cc7`, `NousResearch/Meta-Llama-3.1-8B-Instruct` and `mlx-community/Llama-3.1-8B-Instruct`
- vLLM v0.20.2 source: https://github.com/vllm-project/vllm/tree/v0.20.2 (`vllm/tool_parsers`, `vllm/reasoning`, `model_executor/models/registry.py`)
- Model cards: https://huggingface.co/zai-org/GLM-4.7-Flash, https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16, https://huggingface.co/ibm-granite/granite-4.2-8b, https://huggingface.co/allenai/Olmo-3-7B-Instruct, https://huggingface.co/LiquidAI/LFM2.5-24B-A2B, https://huggingface.co/google/gemma-4-26B-A4B-it
- Liquid's vLLM docs: https://docs.liquid.ai/lfm/inference/vllm
- vLLM Nemotron 3 Nano recipe: https://recipes.vllm.ai/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
- Repo files: `/Users/omereliyahu/personal/pddl-copilot-experiments/cluster-experimenting/lib/defaults.sh`, `/Users/omereliyahu/personal/pddl-copilot-experiments/development/reference/d1_smokes_20261027.md`, `/Users/omereliyahu/personal/pddl-copilot-experiments/results/d1-smokes/`, `/Users/omereliyahu/personal/pddl-copilot/LICENSE`