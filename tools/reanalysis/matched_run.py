#!/usr/bin/env python3
"""The matched run (tools against no tools on solve and simulate, one job): the registered analysis.

    python -m tools.reanalysis.matched_run --print-package-hash
    python -m tools.reanalysis.matched_run --fixture tests/fixtures/matched_run --out OUT \\
        --run-dates "..." --tools-repo-checked-by-hand NOTE
    python -m tools.reanalysis.matched_run --smoke-check results/matched-run-smoke \\
        [--serve-logs DIR | --version-checked-by-hand NOTE] --tools-repo-checked-by-hand NOTE
    python -m tools.reanalysis.matched_run --dry-run-existing --results /abs/results \\
        --marketplace /abs/pddl-copilot --out OUT
    python -m tools.reanalysis.matched_run --results /abs/results --marketplace /abs/pddl-copilot \\
        --run-dates "..." [--serve-logs DIR | --version-checked-by-hand NOTE] \\
        --tools-repo-checked-by-hand NOTE --i-have-frozen <package hash>

Spec: development/reference/matched_run_prereg.md (sections 2 to 8). The clause-by-clause
map from the spec to this file is development/reference/matched_run_traceability.md.

Three arms per model: N (no tools, the format-stated system message of the control's
cell B, wordings v11 to v13), P (tools offered, plain wordings v11 to v13) and S (tools
offered, steered wordings v14 to v16). N is one cell folder; P and S share the other.

This file imports the frozen code and edits none of it. Every row is read through the
frozen loader of the delivered rerun (`tools.delivered_rerun.schema.parse_row`, called by
the control's `read_folder`). The grade is built from the frozen delivered grader
(`tools.delivered_rerun.grade.grade`), the control's second reading
(`control_prompt_fix.second_reading`, which calls `rq1_layout_regrade.block_plan` and
`rq3_context_pilot.line_reader_exact`) and the control's validator route. Where a
function of the control hard-codes the control's three cells (O, A, B) it cannot be
called here; the matched-run version is written in this file and its comment says so.

Modes:
  --print-package-hash   sha256 over this script and every repo file it imports.
  live (default)         reads the matched run only with --i-have-frozen <that hash>.
  --fixture DIR          the same pipeline on the synthetic fixture (small design,
                         injected validator verdicts, no results/ and no validator).
  --smoke-check ROOT     the seven checks of prereg section 7, nothing else.
  --dry-run-existing     the same pipeline with the arms filled from EXISTING data (N =
                         cell B of the control, P and S = Part A of the rerun). It reads
                         no row of the matched run and its numbers are not results of it.

Order (live and fixture): registered constants -> the six cell folders through the typed
loader (completeness, duplicate keys, storage cuts, VOID) -> audit preconditions (section
7 items 4 to 7) and apparatus checks -> the earlier runs (Part A of the rerun, cell B of
the control; their frozen grades must reproduce the filed readouts) -> trial keys equal to
the rerun's -> validator route check -> the registered grade and the two descriptive
grades -> M1 to M3, K1 to K3 -> readings Q1 and Q2 -> secondary tables and the measures
of section 6 rules 3 and 4 -> tripwires -> JSON and markdown. Any failure exits 2 and
writes nothing.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pddl_eval.prompts import WITH_TOOLS_SYSTEM_BY_TASK
from pddl_eval.runner import DEFAULT_NUM_PREDICT, build_messages
from pddl_eval.scoring import strip_leaked_channel_prefix
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import e4 as E4
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.delivered_rerun import stats as ST
from tools.reanalysis import control_prompt_fix as M
from tools.reanalysis import iss027_common as C27
from tools.reanalysis import rq1_control_metrics as RC
from tools.reanalysis import rq1_layout_regrade as RG
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq23_metrics as R23
from tools.reanalysis import rq3_context_pilot as PILOT
from tools.reanalysis.bc_common import domain_track
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
SCRIPT = "tools/reanalysis/matched_run.py"
NUMBERS_TAG = "MATCHED-RUN"
FIXTURE_MARKER = "SYNTHETIC_FIXTURE"

# Every repo file this script imports, directly or through the modules it imports
# (sorted). Part of the freeze: an edit to any of them changes the package hash, so
# --i-have-frozen refuses until the change is declared. tests/test_matched_run.py checks
# this list covers sys.modules. The control's own list is `control_prompt_fix.DEPENDENCIES`
# and is not changed; this list is that one, the control's script, and the modules the
# measures of section 6 rules 3 and 4 need.
DEPENDENCIES = tuple(sorted(M.DEPENDENCIES + (
    M.SCRIPT,
    "tools/reanalysis/bc_common.py", "tools/reanalysis/rq1_control_metrics.py",
    "tools/reanalysis/rq1_figures.py", "tools/reanalysis/rq1_tex.py",
    "tools/reanalysis/rq23_metrics.py",
)))

Halt = M.Halt
AuditFailed = M.AuditFailed
_check = M._check            # raises RegisteredCheckFailed; `python -O` cannot strip it

# ------------------------------------------------------------------ registered constants
# prereg section 2.1: arms, their wordings, cell folders and system texts.
ARMS: tuple[str, ...] = ("N", "P", "S")
ARM_WORDINGS = {"N": (11, 12, 13), "P": (11, 12, 13), "S": (14, 15, 16)}
FOLDERS: tuple[str, ...] = ("N", "T")                  # two cell folders per model
ARM_FOLDER = {"N": "N", "P": "T", "S": "T"}
CELL_TOKENS = {"N": "no-tools-sysformat", "T": "tools_all_minimal"}
FOLDER_WORDINGS = {"N": (11, 12, 13), "T": (11, 12, 13, 14, 15, 16)}
CONTROL_CELL = "B"                                     # arm N sends the control's cell B text
N_SYSTEM_SHA256 = {
    "solve": "3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588",
    "simulate": "7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9",
}
# The with-tools system text of Part A (`build_messages(..., with_tools=True,
# prompt_style="minimal")`), one per task, the same for plain and steered wordings.
TOOLS_SYSTEM_SHA256 = {
    "solve": "9b179ca12c2cd2220b46c5478bc637f6dd47356a2f81a4795d3541ecdf6dbb2c",
    "simulate": "ebf8e7fe9d55ab56b9d2d4ba02be4f2b7770fe1b9fdd4d77bba790a68a0d0ac6",
}
TOOLS_AUDIT_MODE = "registered"                        # vllm_client._write_audit, no swap
TOOLS_SETTINGS_SYSTEM = "not-applicable-with-tools"    # client_settings.json of a tools cell
# section 2.2: models, tasks, size.
MODELS = dict(M.MODELS)
MODEL_ORDER: tuple[str, ...] = ("Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b")
TASKS: tuple[str, ...] = ("solve", "simulate")
TOTAL_TRIALS = 5_400
# section 2.3 and 2.4: apparatus and run tags.
TOOLS_REPO_COMMIT = "5e4f9c0"
CONTEXT_WINDOW = 16_384
OUTPUT_CAP = {"solve": 8_192, "simulate": 6_144}
STORAGE_CAP = 65_536
VLLM_VERSION = "0.20.2"
RUN_TAG = "matched-run"
SMOKE_TAG = "matched-run-smoke"
R2_TAG = "matched-run-r2"
RERUN_PACKAGE = "822aace9ef8a6493592b5b08d73091094fd2602fc0180d1482af83db1ee45cc9"
# prereg section 9: the four input files outside the package hash, by sha256. Keys are
# the command-line arguments that name them.
INPUT_SHA256 = {
    "regrade_json": "eb56a2e4c1fa38e5a04c3357e9776732871f506906d8d1bb8124a9d4f8164017",
    "control_json": "f50452ad5a3d03e8070cd391e8ff1f44c0fcd0aa91176322cedf1335abe4fc3d",
    "readout_json": "81bd59ffd153dafe20e9d9d7422785fff05d8dba894e9f8a331b919a7334c674",
    "plan_verdicts": "3c945faeafbdd36ec921d97bb554ef6ef6e9c53225f61e943056571284c6afb0",
}
CONTROL_PACKAGE = "825dab6313ef2d18c33bed8d584d596e29b35f92eff6c41f0325045602bf0d79"
# section 3: the grade.
PYVALIDATOR = "0.1.5"
# The simulate answer key is the cached reference trace. On these six problems the plan
# placed in the prompt can differ from the plan of the cached key (ISS-029): 18 of the
# 300 simulate trials of an arm. A descriptive count is printed for them.
KEY_PLAN_DIFFERS: tuple[tuple[str, str], ...] = (
    ("barman", "p01"), ("barman", "p02"), ("barman", "p03"), ("barman", "p04"),
    ("barman", "p05"), ("gripper", "p03"))
KEY_PLAN_DIFFERS_TRIALS = 18
GRADES: tuple[str, ...] = ("registered", "frozen", "second")
REGISTERED_GRADE = "registered"
DESCRIPTIVE_GRADES: tuple[str, ...] = ("frozen", "second")
# section 4: contrasts and statistics.
CONTRASTS = {"M1": ("N", "P"), "M2": ("N", "S"), "M3": ("P", "S")}      # y minus x
CONTINUITY = {"K1": ("B", "N"), "K2": ("plain", "P"), "K3": ("steered", "S")}
N_CONTRASTS = 18
N_CONTINUITY = 18
STEER_OFFSET = 3              # v14 pairs with v11, v15 with v12, v16 with v13
MARGIN = 5.0
LEVEL = 0.95
B_BOOT = 10_000
SEED = 20261002
HOLM_FAMILY = 6
HOLM_ALPHA = 0.05
PART_A_DATES = "2026-10-03 to 2026-10-09"
CONTROL_DATES = "2026-11-23 to 2026-11-24"
# section 7: smoke and stop rules.
SMOKE_NONEMPTY = 0.95
VOID_FRAC = 0.01
# section 8: tripwires.
TRIPWIRE_POINTS = 20.0
UNREAD_FRAC = 0.05                       # arm N: more than 5% unread final answers (15 of 300)
UNREAD_KNOWN = ("gemma4_26b-a4b", "simulate")
UNREAD_KNOWN_COUNT, UNREAD_KNOWN_OF = 90, 300   # the case known in advance: above 90 of 300
UNREAD_KNOWN_CONTROL = 52                # what the control counted there

GRADE_WORDS = {"registered": "registered grade (delivered right)",
               "frozen": "the rerun's frozen grade (descriptive)",
               "second": "registered grade without the lower-casing (descriptive)"}
ARM_WORDS = {"N": "N (no tools, format stated)", "P": "P (tools, plain wordings)",
             "S": "S (tools, steered wordings)"}
CONTRAST_WORDS = {"M1": "P minus N", "M2": "S minus N", "M3": "S minus P",
                  "K1": "N minus cell B of the control", "K2": "P minus Part A, plain",
                  "K3": "S minus Part A, steered"}
EARLIER_WORDS = {"B": "cell B of the control", "plain": "Part A, plain",
                 "steered": "Part A, steered"}
EARLIER_DATES = {"K1": CONTROL_DATES, "K2": PART_A_DATES, "K3": PART_A_DATES}
ARM_REC = {"N": "none", "P": "plain", "S": "steered"}       # arm names of rq1_metrics.rec


@dataclass(frozen=True)
class Design:
    """Size constants (live = REGISTERED; smoke = SMOKE; the fixture carries its own)."""
    name: str
    per_task_arm: int       # trials per model, task and arm
    n_folder: int           # rows of an N cell folder
    tools_folder: int       # rows of a tools cell folder (P and S)
    per_wording: int        # rows per wording in either folder
    per_task_wording: int   # rows per task and wording
    k_domains: int          # domain clusters


REGISTERED = Design("registered", per_task_arm=300, n_folder=600, tools_folder=1_200,
                    per_wording=200, per_task_wording=100, k_domains=20)
SMOKE = Design("smoke", per_task_arm=60, n_folder=120, tools_folder=240, per_wording=40,
               per_task_wording=20, k_domains=20)


def tools_system_text(task: str) -> str:
    """The system text a tools cell sends on a task (section 2.1), from the harness."""
    return WITH_TOOLS_SYSTEM_BY_TASK[task]


def check_constants() -> None:
    """Gate 2: every quantity sections 2 to 8 name, as a raised check. Reads the module
    globals at call time, so a test can flip one and see it fire."""
    g = globals()
    M.check_constants()
    _check(g["TASKS"] == ("solve", "simulate") == M.TASKS, "tasks solve and simulate")
    _check(g["ARMS"] == ("N", "P", "S"), "arms N, P, S")
    _check(g["ARM_WORDINGS"] == {"N": (11, 12, 13), "P": (11, 12, 13), "S": (14, 15, 16)},
           "wordings of each arm")
    _check(g["ARM_WORDINGS"]["P"] == C.PLAIN and g["ARM_WORDINGS"]["S"] == C.STEERED,
           "plain and steered wordings are the rerun's")
    _check(g["FOLDERS"] == ("N", "T") and g["ARM_FOLDER"] == {"N": "N", "P": "T", "S": "T"},
           "two cell folders per model; P and S share one")
    _check(g["CELL_TOKENS"] == {"N": "no-tools-sysformat", "T": "tools_all_minimal"},
           "cell folder tokens")
    _check(g["CELL_TOKENS"]["N"] == M.CELL_TOKENS["B"], "the N token is the control's cell B token")
    _check(g["CELL_TOKENS"]["T"] == f"tools_{C.TOOL_FILTER}_{C.STYLE_A}",
           "the tools token is Part A's")
    _check(g["FOLDER_WORDINGS"] == {"N": C.PLAIN, "T": C.VARIANTS}, "wordings of each folder")
    _check(g["CONTROL_CELL"] == "B" and M.WRAPPER["B"] == "format-stated",
           "arm N sends the format-stated text of the control's cell B")
    for t in TASKS:
        _check(g["N_SYSTEM_SHA256"][t] == M.SYSTEM_SHA256["B"][t]
               == M._text_sha(M.system_text("B", t)), f"N system text sha256 on {t}")
        want = g["TOOLS_SYSTEM_SHA256"][t]
        _check(M._HEX64.match(want) is not None, f"tools sha256 literal on {t}")
        _check(M._text_sha(tools_system_text(t)) == want,
               f"with-tools system text on {t} has the registered sha256")
        for v in C.VARIANTS:       # the same text for plain and steered wordings
            sent = build_messages(t, "(d)", "(p)", v, True, {"plan": ["(a)"]}, C.STYLE_A)
            _check(sent[0]["role"] == "system"
                   and M._text_sha(sent[0]["content"]) == want,
                   f"build_messages sends the registered with-tools text on {t} v{v}")
    _check(len({*g["N_SYSTEM_SHA256"].values(), *g["TOOLS_SYSTEM_SHA256"].values()}) == 4,
           "four distinct system texts")
    _check(g["TOOLS_AUDIT_MODE"] == "registered", "audit mode of a tools cell")
    _check(g["TOOLS_SETTINGS_SYSTEM"] == "not-applicable-with-tools",
           "client_settings no_tools_system of a tools cell")
    _check(g["MODELS"] == {"Qwen3_5_9B": "Qwen/Qwen3.5-9B",
                           "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
                           "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"}, "model ids")
    _check(all(C.MODEL_IDS[m] == i for m, i in g["MODELS"].items()), "model ids are the rerun's")
    _check(set(g["MODEL_ORDER"]) == set(g["MODELS"]) == set(C.PART_A_MODELS)
           and len(g["MODEL_ORDER"]) == 3, "three models, the rerun's")
    _check(C.THINK == "off", "thinking off")
    _check(g["TOTAL_TRIALS"] == 5_400, "5,400 trials")
    _check(g["TOOLS_REPO_COMMIT"] == "5e4f9c0" == C.MARKETPLACE_PIN, "tools repo at 5e4f9c0")
    _check(g["CONTEXT_WINDOW"] == 16_384 == C.CONTEXT_WINDOW, "16,384-token window")
    _check(g["OUTPUT_CAP"] == {"solve": 8_192, "simulate": 6_144}, "output caps")
    _check(all(g["OUTPUT_CAP"][t] == DEFAULT_NUM_PREDICT[t] for t in g["TASKS"]),
           "output caps are the harness's DEFAULT_NUM_PREDICT")
    _check(g["STORAGE_CAP"] == 65_536 == C.STORAGE_CAP, "storage cap 65,536")
    _check(g["VLLM_VERSION"] == "0.20.2" == M.VLLM_VERSION, "vLLM 0.20.2")
    _check(g["RUN_TAG"] == "matched-run", "run tag")
    _check(g["SMOKE_TAG"] == "matched-run-smoke", "smoke run tag")
    _check(g["R2_TAG"] == "matched-run-r2", "VOID rerun tag")
    _check(g["RERUN_PACKAGE"].startswith("822aace9") and g["RERUN_PACKAGE"] == R1.FROZEN_SHA,
           "the rerun's frozen package 822aace9")
    _check(g["CONTROL_PACKAGE"].startswith("825dab63") and g["CONTROL_PACKAGE"] == RC.FROZEN,
           "the control's frozen package 825dab63")
    _check(g["PYVALIDATOR"] == "0.1.5" == C27.PYVAL_EXPECTED, "pddl-pyvalidator 0.1.5")
    _check(g["KEY_PLAN_DIFFERS"] == (("barman", "p01"), ("barman", "p02"), ("barman", "p03"),
                                     ("barman", "p04"), ("barman", "p05"), ("gripper", "p03")),
           "the six problems whose prompt plan can differ from the cached key")
    _check(g["KEY_PLAN_DIFFERS_TRIALS"] == 18 == len(g["KEY_PLAN_DIFFERS"]) * 3,
           "18 of 300 simulate trials per arm")
    _check(g["INPUT_SHA256"] == {
        "regrade_json": "eb56a2e4c1fa38e5a04c3357e9776732871f506906d8d1bb8124a9d4f8164017",
        "control_json": "f50452ad5a3d03e8070cd391e8ff1f44c0fcd0aa91176322cedf1335abe4fc3d",
        "readout_json": "81bd59ffd153dafe20e9d9d7422785fff05d8dba894e9f8a331b919a7334c674",
        "plan_verdicts": "3c945faeafbdd36ec921d97bb554ef6ef6e9c53225f61e943056571284c6afb0"},
        "sha256 of the four input files outside the package hash")
    _check(g["GRADES"] == ("registered", "frozen", "second"), "one grade and two descriptive")
    _check(g["REGISTERED_GRADE"] == "registered"
           and g["DESCRIPTIVE_GRADES"] == ("frozen", "second"), "which grade is registered")
    _check(g["CONTRASTS"] == {"M1": ("N", "P"), "M2": ("N", "S"), "M3": ("P", "S")},
           "M1 = P minus N, M2 = S minus N, M3 = S minus P")
    _check(g["CONTINUITY"] == {"K1": ("B", "N"), "K2": ("plain", "P"), "K3": ("steered", "S")},
           "K1 to K3")
    _check(g["N_CONTRASTS"] == 18 == len(g["CONTRASTS"]) * len(g["MODELS"]) * len(g["TASKS"]),
           "18 contrasts")
    _check(g["N_CONTINUITY"] == 18 == len(g["CONTINUITY"]) * len(g["MODELS"]) * len(g["TASKS"]),
           "18 continuity checks")
    _check(g["STEER_OFFSET"] == 3 == C.STEER_OFFSET
           and all(s - p == 3 for p, s in zip(C.PLAIN, C.STEERED)),
           "v14 with v11, v15 with v12, v16 with v13")
    _check(g["MARGIN"] == 5.0 == C.MARGIN == M.MARGIN, "margin 5 points")
    _check(g["LEVEL"] == 0.95 == C.CI_ENDPOINT == M.LEVEL, "95% intervals")
    _check(g["B_BOOT"] == 10_000 == C.B_BOOT, "10,000 resamples")
    _check(g["SEED"] == 20261002 == C.SEED, "seed 20261002")
    _check(g["HOLM_FAMILY"] == 6 == len(g["MODELS"]) * len(g["TASKS"]) == M.HOLM_FAMILY,
           "Holm family 6")
    _check(g["HOLM_ALPHA"] == 0.05 == C.HOLM_ALPHA == M.HOLM_ALPHA, "Holm alpha 0.05")
    _check(g["PART_A_DATES"] == "2026-10-03 to 2026-10-09" == M.PART_A_DATES, "dates of Part A")
    _check(g["CONTROL_DATES"] == "2026-11-23 to 2026-11-24", "dates of the control")
    _check(g["SMOKE_NONEMPTY"] == 0.95, "smoke: 95% non-empty")
    _check(g["VOID_FRAC"] == 0.01 == C.EXCEPTION_VOID_FRAC, "VOID above 1%")
    _check(C.EXCEPTION_REASONS == frozenset({"exception", "ollama_parse_error"}),
           "exception reasons of the rerun")
    _check(g["TRIPWIRE_POINTS"] == 20.0, "tripwire 20 points")
    _check(g["UNREAD_FRAC"] == 0.05 == M.UNREAD_FRAC, "unread final answers: more than 5%")
    _check(g["UNREAD_KNOWN"] == ("gemma4_26b-a4b", "simulate"), "the case known in advance")
    _check((g["UNREAD_KNOWN_COUNT"], g["UNREAD_KNOWN_OF"]) == (90, 300),
           "Gemma-26B simulate: above 90 of 300")
    _check(g["UNREAD_KNOWN_CONTROL"] == 52, "the control counted 52 of 300")


def check_design(design: Design, registered: bool) -> None:
    """Size constants. Live mode passes REGISTERED and checks every field."""
    if registered:
        _check(design is REGISTERED, "live mode runs on the REGISTERED design")
        _check(design.per_task_arm == 300, "300 trials per model, task and arm")
        _check(design.n_folder == 600, "600 rows per N cell folder")
        _check(design.tools_folder == 1_200, "1,200 rows per tools cell folder")
        _check(design.per_wording == 200, "200 rows per wording")
        _check(design.per_task_wording == 100, "100 problems per task and wording")
        _check(design.k_domains == 20, "k = 20 domains")
        _check(design.per_task_arm * len(ARMS) * len(TASKS) * len(MODELS) == TOTAL_TRIALS,
               "5,400 trials")
        _check((design.n_folder + design.tools_folder) * len(MODELS) == TOTAL_TRIALS,
               "six cell folders hold the 5,400 trials")
        _check(UNREAD_FRAC * design.per_task_arm == 15, "unread tripwire: more than 15 of 300")
        _check(design.per_task_arm == UNREAD_KNOWN_OF, "the known case is counted of 300")
    _check(design.n_folder == design.per_task_arm * len(TASKS), "rows per N folder")
    _check(design.tools_folder == 2 * design.n_folder, "rows per tools folder")
    for fo in FOLDERS:
        rows = design.n_folder if fo == "N" else design.tools_folder
        _check(rows == design.per_wording * len(FOLDER_WORDINGS[fo]), f"rows per wording, {fo}")
    _check(design.per_task_arm == design.per_task_wording * 3, "rows per task and wording")
    _check(design.per_wording == design.per_task_wording * len(TASKS), "rows per wording")


def check_smoke_design() -> None:
    _check(SMOKE.n_folder == 120, "smoke: 120 rows in each N folder")
    _check(SMOKE.tools_folder == 240, "smoke: 240 rows in each tools folder")
    _check(SMOKE.k_domains == 20 and SMOKE.per_task_wording == 20,
           "smoke: the first problem of every domain")
    check_design(SMOKE, registered=False)


def unread_limit(design: Design, model: str, task: str) -> float:
    """Section 8: arm N halts above 5% unread final answers; Gemma-26B on simulate above
    90 of 300 (scaled with the design, so the fixture can exercise it)."""
    if (model, task) == UNREAD_KNOWN:
        return UNREAD_KNOWN_COUNT / UNREAD_KNOWN_OF * design.per_task_arm
    return UNREAD_FRAC * design.per_task_arm


check_constants()


# ------------------------------------------------------------------ package hash
# The construction of `control_prompt_fix.package_sha256`, over this script's own file
# list (the control's functions hash the control's list and are not changed).
def frozen_files() -> list[tuple[str, Path]]:
    return [(rel, REPO / rel) for rel in sorted((SCRIPT,) + DEPENDENCIES)]


def file_hashes() -> list[tuple[str, str]]:
    return [(rel, hashlib.sha256(p.read_bytes()).hexdigest()) for rel, p in frozen_files()]


def package_sha256() -> str:
    h = hashlib.sha256()
    for rel, digest in file_hashes():
        h.update(rel.encode() + b"\0" + digest.encode() + b"\n")
    return h.hexdigest()


# ------------------------------------------------------------------ names and specs
def folder_name(model: str, folder: str, tag: str) -> str:
    return f"slurm_vllm_{model}_{C.THINK}_{CELL_TOKENS[folder]}_{tag}"


def matched_spec(design: Design, model: str, folder: str, tag: str) -> S.CellSpec:
    """The cell spec of one matched-run folder: the rerun's Part C spec (no tools) or
    Part A spec (tools) with this run's folder, tasks, wordings and sizes."""
    base = (S.spec_rerun_c if folder == "N" else S.spec_rerun_a)(C.REGISTERED, model)
    return dataclasses.replace(
        base, name=folder_name(model, folder, tag), tasks=TASKS,
        variants=FOLDER_WORDINGS[folder],
        n_rows=design.n_folder if folder == "N" else design.tools_folder,
        per_variant=design.per_wording,
        per_task_variant={t: design.per_task_wording for t in TASKS},
        k_domains=design.k_domains)


def part_a_spec(design: Design, model: str) -> S.CellSpec:
    """Fixture only: a Part A cell of the rerun holding solve and simulate, six wordings."""
    return dataclasses.replace(
        S.spec_rerun_a(C.REGISTERED, model), tasks=TASKS, variants=C.VARIANTS,
        n_rows=design.tools_folder, per_variant=design.per_wording,
        per_task_variant={t: design.per_task_wording for t in TASKS},
        k_domains=design.k_domains)


def control_design(design: Design) -> M.Design:
    """The control's design record for a cell B folder of the same size as an N folder."""
    return M.Design(name=design.name, per_task_cell=design.per_task_arm,
                    per_folder=design.n_folder, per_wording=design.per_wording,
                    per_task_wording=design.per_task_wording, k_domains=design.k_domains)


# ------------------------------------------------------------------ typed load boundary
# Rows are read by `control_prompt_fix.read_folder` (the frozen `schema.parse_row`, the
# storage-cut rule, duplicate keys, torn lines, the frozen completeness check).
def check_void(f: M.Folder) -> None:
    """Section 7: VOID above 1% exception or infrastructure-failure rows. The control's
    `check_void` names the control's three cells in its message; this is the same rule
    with the matched run's consequence."""
    if f.void_rule_rows > VOID_FRAC * len(f.rows):
        raise Halt(f"VOID (section 7): {f.spec.name} has {f.void_rule_rows} exception or "
                   f"infrastructure-failure rows of {len(f.rows)} (more than "
                   f"{100 * VOID_FRAC:.0f}%); both cells of {f.model} are run again from "
                   f"scratch, together, under the run tag {R2_TAG}, not analysed")


def load_matched(root: Path, design: Design, tags: dict[str, str],
                 domains: frozenset | None = None) -> dict:
    """{model: {folder: Folder}} for the six cell folders, with the section 7 load rules."""
    out = {}
    for m in MODEL_ORDER:
        out[m] = {}
        for fo in FOLDERS:
            f = M.read_folder(root, matched_spec(design, m, fo, tags[m]), m, fo, domains)
            check_void(f)
            out[m][fo] = f
    return out


def first_run_void(root: Path, design: Design, model: str,
                   domains: frozenset | None = None) -> str:
    """Section 7: the second run of a model is read only after the analysis has found a
    cell of that model's first run VOID. Returns the VOID finding; halts when the first
    run is missing, short, refused by the loader, or not VOID. (The control's function
    of this name loops over O, A, B and also has a pairing rule this run does not.)"""
    folders = {}
    for fo in FOLDERS:
        spec = matched_spec(design, model, fo, RUN_TAG)
        try:
            folders[fo] = M.read_folder(root, spec, model, fo, domains)
        except S.SchemaError as e:
            raise Halt(f"--r2-models {model}: the first run cannot be read ({e}); the second "
                       f"run is read only after a VOID first run") from e
    for fo in FOLDERS:
        try:
            check_void(folders[fo])
        except Halt as e:
            return str(e)
    raise Halt(f"--r2-models {model}: no cell of the first run is VOID, so the second run "
               f"({R2_TAG}) is not read")


def resolve_tags(root: Path, design: Design, r2_arg: str,
                 domains: frozenset | None = None) -> tuple[dict, dict]:
    """The run tag of each model's two cells, and the VOID finding behind every r2 model."""
    r2 = {x for x in r2_arg.split(",") if x}
    if not r2 <= set(MODELS):
        raise Halt(f"--r2-models: unknown model tags {sorted(r2 - set(MODELS))}")
    found = {m: first_run_void(root, design, m, domains) for m in sorted(r2)}
    return {m: (R2_TAG if m in r2 else RUN_TAG) for m in MODEL_ORDER}, found


def arm_rows(folders: dict) -> dict:
    """{model: {arm: rows}}: N from the N folder, P and S from the tools folder by wording."""
    out = {}
    for m, fs in folders.items():
        out[m] = {arm: tuple(r for r in fs[ARM_FOLDER[arm]].rows
                             if r.variant in ARM_WORDINGS[arm]) for arm in ARMS}
    return out


def canon(key: tuple) -> tuple:
    """Section 4: the pairing key (task, domain, problem, plan label, wording), a steered
    wording mapped to its plain wording (v14 to v11, v15 to v12, v16 to v13)."""
    task, dom, prob, label, v = key
    if v in C.STEERED:
        v -= STEER_OFFSET
    if v not in C.PLAIN:
        raise Halt(f"wording v{key[4]} is in no arm")
    return (task, dom, prob, label, v)


def check_same_problems(m: str, arms: dict) -> None:
    """Section 7 item 5: the N and tools cells of a model hold the same problems (the
    same pairing keys in N, P and S, per task)."""
    for t in TASKS:
        ks = {a: {canon(r.trial_key) for r in arms[a] if r.task == t} for a in ARMS}
        if not (ks["N"] == ks["P"] == ks["S"]):
            raise Halt(f"{m}: the N and tools cells do not hold the same {t} problems "
                       f"({len(ks['N'] ^ ks['P'])} differ between N and P, "
                       f"{len(ks['P'] ^ ks['S'])} between P and S)")


def check_keys_equal_rerun(arms: dict, part_a: dict) -> None:
    """Section 7: the trial keys of each arm equal those of the rerun for that model and
    task (N and P against Part A's plain keys, S against its steered keys)."""
    for m in MODEL_ORDER:
        for arm in ARMS:
            ref = part_a[m]["steered" if arm == "S" else "plain"]
            for t in TASKS:
                ks = {r.trial_key for r in arms[m][arm] if r.task == t}
                want = set(ref[t])
                if ks != want:
                    raise Halt(f"arm {arm} of {m}: the {t} keys differ from the rerun's "
                               f"({len(ks - want)} not in the rerun, {len(want - ks)} missing)")


# ------------------------------------------------------------------ audit preconditions
# Arm N is audited by the control's own functions with cell "B" (`check_audit`,
# `check_settings`, `check_apparatus`). The tools cell needs its own: the control's
# functions require no tools, a swapped text and one request per trial.
def check_audit_tools(cell_dir: Path, model: str, rows) -> Counter:
    """Section 7 item 4 for a tools cell; returns the user-text sha256 counts (item 5).

    The audit log has one line per request, so a tool loop gives several lines per trial
    with the same system and first-user sha256. Every line: the system sha256 is the
    registered with-tools text of one of the two tasks; the stored text, where a line
    carries it, is that text byte for byte; mode "registered", not swapped, with tools,
    the model of the cell. So that the log covers every trial, each task has at least as
    many lines as rows and exactly as many different user texts as rows."""
    where = cell_dir.name
    by_sha = {TOOLS_SYSTEM_SHA256[t]: t for t in TASKS}
    users: Counter = Counter()
    per_task: Counter = Counter()
    distinct: dict[str, set] = {t: set() for t in TASKS}
    for i, o in enumerate(M.audit_lines(cell_dir / "system_prompt_audit.jsonl", where), 1):
        keys = set(o)
        if not (M.AUDIT_KEYS <= keys <= M.AUDIT_KEYS | {"system_text"}):
            raise AuditFailed(f"{where}: audit line {i} has keys {sorted(keys)}")
        sha = o["system_sha256"]
        if sha not in by_sha:
            raise AuditFailed(f"{where}: audit line {i}: system sha256 {str(sha)[:12]}... is "
                              f"not the with-tools text of Part A")
        task = by_sha[sha]
        if "system_text" in o:
            if not isinstance(o["system_text"], str) \
                    or o["system_text"] != tools_system_text(task) \
                    or M._text_sha(o["system_text"]) != sha:
                raise AuditFailed(f"{where}: audit line {i}: the stored system text is not "
                                  f"the with-tools {task} text byte for byte")
        if o["mode"] != TOOLS_AUDIT_MODE:
            raise AuditFailed(f"{where}: audit line {i}: mode {o['mode']!r}, a tools cell is "
                              f"{TOOLS_AUDIT_MODE!r}")
        if o["swapped"] is not False:
            raise AuditFailed(f"{where}: audit line {i}: swapped={o['swapped']!r}; a tools "
                              f"cell is not swapped")
        if o["has_tools"] is not True:
            raise AuditFailed(f"{where}: audit line {i}: a request of a tools cell without "
                              f"tools")
        if o["model"] != MODELS[model]:
            raise AuditFailed(f"{where}: audit line {i}: model {o['model']!r}")
        if not isinstance(o["user_sha256"], str) or not M._HEX64.match(o["user_sha256"]):
            raise AuditFailed(f"{where}: audit line {i}: user sha256 is not a sha256")
        users[o["user_sha256"]] += 1
        per_task[task] += 1
        distinct[task].add(o["user_sha256"])
    rows_per_task = Counter(r.task for r in rows)
    for t in TASKS:
        if per_task[t] < rows_per_task[t]:
            raise AuditFailed(f"{where}: {per_task[t]} audit lines for {t}, fewer than its "
                              f"{rows_per_task[t]} rows")
        if len(distinct[t]) != rows_per_task[t]:
            raise AuditFailed(f"{where}: {len(distinct[t])} different user texts for {t}, "
                              f"the cell has {rows_per_task[t]} rows of it")
    return users


def check_users(model: str, n_users: Counter, t_users: Counter) -> dict:
    """Section 7 item 5: the user messages of v11 to v13 are the same in N and in the
    tools cell. The audit names no wording, so the check is: every user text of N is
    also sent in the tools cell, and the tools cell holds exactly as many other texts
    (the steered ones). Returns the re-sent request lines of N, which are reported."""
    n, t = set(n_users), set(t_users)
    if not n <= t:
        raise AuditFailed(f"{model}: {len(n - t)} user messages of the N cell are not sent "
                          f"in the tools cell (v11 to v13 must be the same in both)")
    if len(t - n) != len(n):
        raise AuditFailed(f"{model}: the tools cell holds {len(t - n)} user messages that "
                          f"are not in N, expected {len(n)} (the steered wordings)")
    return {"n_resent_lines": sum(n_users.values()) - len(n), "shared_user_texts": len(n),
            "tools_only_user_texts": len(t - n), "tools_lines": sum(t_users.values())}


def check_settings_tools(cell_dir: Path, model: str) -> dict:
    """Section 7 item 6 for a tools cell: client_settings.json names the tools condition,
    the model and the cell's audit log, and no no-tools system text."""
    s = M.read_settings(cell_dir)
    want = {"no_tools_system": TOOLS_SETTINGS_SYSTEM, "cond": CELL_TOKENS["T"],
            "hf_model": MODELS[model]}
    for k, v in want.items():
        if k not in s or s[k] != v:
            raise AuditFailed(f"{cell_dir.name}: client_settings.json {k}={s.get(k)!r}, this "
                              f"cell is {v!r}")
    log = s.get("system_audit_log")
    if not isinstance(log, str) or not log.endswith(f"/{cell_dir.name}/system_prompt_audit.jsonl"):
        raise AuditFailed(f"{cell_dir.name}: client_settings.json system_audit_log {log!r} is "
                          f"not this cell's audit log")
    return s


def check_tool_row_caps(rows, where: str) -> None:
    """Section 2.3, the output cap in a tools row. `tokens.completion` is the sum over
    the turns of the tool loop and the cap applies to each turn, so the control's rule
    ("no answer longer than the cap") does not hold for these rows. Checked instead:
    the sum is at most the cap times the number of turns; a trial of one turn follows
    the control's rule; a trial that stopped at the cap with no clipped turn and no
    refused turn used at least the cap. The 3,600 solve and simulate rows of Part A
    pass this check (the dry run runs it on them)."""
    for r in rows:
        cap, t = OUTPUT_CAP[r.task], r.tokens
        if t.completion > cap * max(t.turns, 1):
            raise Halt(f"{where}: {t.completion} answer tokens in {t.turns} turns, cap {cap} "
                       f"per turn")
        full = r.done_reason == "length" and t.ctx_clipped_turns == 0 and not r.no_room
        if full and t.turns <= 1 and t.completion != cap:
            raise Halt(f"{where}: a one-turn answer stopped at the cap after {t.completion} "
                       f"tokens, registered cap {cap}")
        if full and t.completion < cap:
            raise Halt(f"{where}: an answer stopped at the cap after {t.completion} tokens "
                       f"in all, registered cap {cap} per turn")


def check_apparatus_tools(cell_dir: Path, f: M.Folder, settings: dict) -> dict:
    """Section 2.3 for a tools cell, where the files expose it: the 16,384-token window
    and thinking off in client_settings.json and in every summary file; temperature 0;
    all tools visible and the prompt style of Part A; the per-turn output cap."""
    where = cell_dir.name
    if settings.get("max_model_len") != CONTEXT_WINDOW:
        raise Halt(f"{where}: client_settings.json max_model_len "
                   f"{settings.get('max_model_len')!r}, registered {CONTEXT_WINDOW}")
    if settings.get("think_mode_token") != C.THINK:
        raise Halt(f"{where}: client_settings.json think_mode_token "
                   f"{settings.get('think_mode_token')!r}")
    summaries = sorted(cell_dir.glob("summary_*.json"))
    if not summaries:
        raise Halt(f"{where}: no summary_*.json")
    for p in summaries:
        try:
            meta = json.loads(p.read_text()).get("meta")
        except (ValueError, AttributeError) as e:
            raise Halt(f"{where}/{p.name}: not a summary object") from e
        if not isinstance(meta, dict):
            raise Halt(f"{where}/{p.name}: no meta")
        want = {"num_ctx": CONTEXT_WINDOW, "temperature": 0.0, "think": C.THINK,
                "conditions": "tools", "models": [MODELS[f.model]],
                "tool_filter": C.TOOL_FILTER, "prompt_style": C.STYLE_A}
        for k, v in want.items():
            if meta.get(k) != v:
                raise Halt(f"{where}/{p.name}: meta {k}={meta.get(k)!r}, registered {v!r}")
    check_tool_row_caps(f.rows, where)
    return {"summaries": len(summaries)}


def check_summary_run(cell_dir: Path) -> None:
    """Section 2.3, for an N and for a tools cell: every summary file names the two tasks
    of this run and no output cap of its own (`num_predict` null), so the caps are the
    harness's defaults, which `check_constants` ties to 8,192 and 6,144. (The control's
    `check_apparatus` does not read these two fields.)"""
    for p in sorted(cell_dir.glob("summary_*.json")):
        try:
            meta = json.loads(p.read_text()).get("meta")
        except (ValueError, AttributeError) as e:
            raise Halt(f"{cell_dir.name}/{p.name}: not a summary object") from e
        if not isinstance(meta, dict) or "num_predict" not in meta or "tasks" not in meta:
            raise Halt(f"{cell_dir.name}/{p.name}: meta has no num_predict or no tasks")
        if meta["num_predict"] is not None:
            raise Halt(f"{cell_dir.name}/{p.name}: meta num_predict={meta['num_predict']!r}, "
                       f"registered: none (the harness's caps)")
        if meta["tasks"] != list(TASKS):
            raise Halt(f"{cell_dir.name}/{p.name}: meta tasks={meta['tasks']!r}, registered "
                       f"{list(TASKS)!r}")


def compare_user_texts(n_dir: Path, control_dir: Path, model: str) -> list[dict]:
    """Section 2.3: the user texts of the N cell against those of the control's cell B,
    by sha256, per task (both cells send the same system text, so a line's task is read
    from its system sha256). Reported beside K1; a difference does not halt. It would
    mean a user prompt moved between the two runs, which for simulate is the plan placed
    in the prompt."""
    by_sha = {N_SYSTEM_SHA256[t]: t for t in TASKS}
    sets = []
    for d in (n_dir, control_dir):
        per = {t: set() for t in TASKS}
        for i, o in enumerate(M.audit_lines(d / "system_prompt_audit.jsonl", d.name), 1):
            sha, user = o.get("system_sha256"), o.get("user_sha256")
            if sha not in by_sha or not isinstance(user, str) or not M._HEX64.match(user):
                raise AuditFailed(f"{d.name}: audit line {i} is not a line of the "
                                  f"format-stated text with a user sha256")
            per[by_sha[sha]].add(user)
        sets.append(per)
    return [{"model": model, "task": t, "shared": len(sets[0][t] & sets[1][t]),
             "only_this_run": len(sets[0][t] - sets[1][t]),
             "only_control": len(sets[1][t] - sets[0][t])} for t in TASKS]


def need_notes(serve_logs: Path | None, version_note: str | None, repo_note: str | None) -> None:
    """Item 7 has two halves; each needs evidence or a note that it was checked by hand."""
    if serve_logs is None and not (version_note and version_note.strip()):
        raise AuditFailed("item 7 (vLLM 0.20.2 in every serve log) is not checked: pass "
                          "--serve-logs DIR or --version-checked-by-hand NOTE")
    if not (repo_note and repo_note.strip()):
        raise AuditFailed(f"item 7 (the cluster's tools repo at {TOOLS_REPO_COMMIT}) leaves no "
                          f"trace in a cell's files: pass --tools-repo-checked-by-hand NOTE")


def audit_matched(root: Path, folders: dict, serve_logs: Path | None,
                  version_note: str | None, repo_note: str | None) -> dict:
    """Items 4 to 7 as preconditions (section 7) and the apparatus checks, before any
    answer is graded."""
    need_notes(serve_logs, version_note, repo_note)
    out = {"serve_logs": {}, "settings": {}, "apparatus": {}, "users": {},
           "version_note": version_note, "tools_repo_note": repo_note}
    for m, fs in folders.items():
        users = {}
        for fo in FOLDERS:
            f = fs[fo]
            d = root / f.spec.name
            if fo == "N":
                users[fo] = M.check_audit(d, m, CONTROL_CELL, f.rows)
                s = M.check_settings(d, m, CONTROL_CELL)
                out["apparatus"][f.spec.name] = M.check_apparatus(d, f, s)
            else:
                users[fo] = check_audit_tools(d, m, f.rows)
                s = check_settings_tools(d, m)
                out["apparatus"][f.spec.name] = check_apparatus_tools(d, f, s)
            check_summary_run(d)
            out["settings"][f.spec.name] = {"slurm_job_id": s.get("slurm_job_id")}
            if serve_logs is not None:
                out["serve_logs"][f.spec.name] = M.check_serve_log(serve_logs, d, m, s)
        out["users"][m] = check_users(m, users["N"], users["T"])
        check_same_problems(m, arm_rows({m: fs})[m])
    return out


# ------------------------------------------------------------------ smoke check
def window_full(r: S.Row) -> bool:
    """Section 7 item 3: the final turn of a trial was refused or clipped for a full
    context window. The two rules of the rerun's category REFUSED_OR_CLIPPED_FINAL
    (`tools/delivered_rerun/e4.py`, `classify`): the row's `no_room` (a turn was never
    generated because the prompt filled the window), or a final turn that ran out of a
    clipped allowance (`tokens.ctx_clip_last_turn_max_tokens` set and `done_reason`
    "length"). `classify` itself takes only tool-verified rows that are graded wrong, so
    its two conditions are written out here on the typed row."""
    return r.no_room or (r.tokens.ctx_clip_last_turn_max_tokens is not None
                         and r.done_reason == "length")


def nonempty_enough(folder: str, rows) -> bool:
    """Section 7 item 3. N cell: at least 95% of the stored answers are non-empty. Tools
    cell: the same among the trials whose final turn was not `window_full`; the item
    cannot pass on nothing, so each task needs at least one such trial."""
    base = [r for r in rows if not (folder == "T" and window_full(r))]
    if folder == "T" and not all(any(r.task == t for r in base) for t in TASKS):
        return False
    nonempty = sum(bool(strip_leaked_channel_prefix(r.response).strip()) for r in base)
    return nonempty >= SMOKE_NONEMPTY * len(base)


def smoke_check(root: Path, serve_logs: Path | None, version_note: str | None,
                repo_note: str | None, out=print) -> int:
    """Section 7, the smoke: the seven checks and nothing else. Prints no success rate,
    no failure-reason count, no tool-call count and no answer text."""
    check_smoke_design()
    fails: dict[int, list[str]] = {i: [] for i in range(1, 8)}
    loaded: dict[tuple, M.Folder] = {}
    resent: dict[str, int] = {}
    for m in MODEL_ORDER:
        for fo in FOLDERS:
            spec = matched_spec(SMOKE, m, fo, SMOKE_TAG)
            try:
                f = M.read_folder(root, spec, m, fo)
            except S.IncompleteCell as e:
                fails[1].append(str(e))
                continue
            except (Halt, S.SchemaError) as e:
                fails[2].append(f"{spec.name}: the frozen loader refuses a row "
                                f"({type(e).__name__}: {e})")
                continue
            if f.storage_cut:
                fails[2].append(f"{spec.name}: a row cut by storage")
            if f.void_rule_rows:
                fails[2].append(f"{spec.name}: exception or infrastructure-failure rows")
            if f.torn_lines:
                fails[2].append(f"{spec.name}: a torn line the loader cannot read")
            if not nonempty_enough(fo, f.rows):
                fails[3].append(f"{spec.name}: fewer than {100 * SMOKE_NONEMPTY:.0f}% of the "
                                f"stored answers are non-empty"
                                + (" among the trials whose final turn was not refused or "
                                   "clipped for a full window, or a task has no such trial"
                                   if fo == "T" else ""))
            loaded[(m, fo)] = f
    for m in MODEL_ORDER:
        users = {}
        for fo in FOLDERS:
            d = root / folder_name(m, fo, SMOKE_TAG)
            rows = loaded[(m, fo)].rows if (m, fo) in loaded else ()
            try:
                users[fo] = (M.check_audit(d, m, CONTROL_CELL, rows) if fo == "N"
                             else check_audit_tools(d, m, rows))
            except AuditFailed as e:
                msg = str(e)
                # Whether a cell offered the tools is item 6; everything else is item 4.
                fails[6 if ("has tools" in msg or "without tools" in msg) else 4].append(msg)
            try:
                s = (M.check_settings(d, m, CONTROL_CELL) if fo == "N"
                     else check_settings_tools(d, m))
            except AuditFailed as e:
                fails[6].append(str(e))
                s = None
            if serve_logs is not None:
                try:
                    if s is None:
                        s = M.read_settings(d)
                    M.check_serve_log(serve_logs, d, m, s)
                except AuditFailed as e:
                    fails[7].append(str(e))
        if len(users) == 2:
            try:
                resent[folder_name(m, "N", SMOKE_TAG)] = check_users(
                    m, users["N"], users["T"])["n_resent_lines"]
            except AuditFailed as e:
                fails[5].append(str(e))
        else:
            fails[5].append(f"{m}: user messages not compared, an audit log failed")
        if (m, "N") in loaded and (m, "T") in loaded:
            try:
                check_same_problems(m, arm_rows({m: {fo: loaded[(m, fo)] for fo in FOLDERS}})[m])
            except Halt as e:
                fails[5].append(str(e))
        else:
            fails[5].append(f"{m}: problems not compared, a cell folder was not read")
    names = {1: f"every cell folder holds its rows ({SMOKE.n_folder} in each N folder, "
                f"{SMOKE.tools_folder} in each tools folder)",
             2: "the frozen loader reads every row; no exception or infrastructure-failure "
                "row; no row cut by storage; no half-written line",
             3: f"in every N cell at least {100 * SMOKE_NONEMPTY:.0f}% of the stored answers "
                f"are non-empty; in every tools cell the same among the trials whose final "
                f"turn was not refused or clipped for a full context window, with at least "
                f"one such trial per task",
             4: "audit log: in the N cells the registered sha256 and text, swapped; in the "
                "tools cells one system text per task, the with-tools text of Part A, not "
                "swapped; the cell's model; at least one line and one different user text "
                "per row of each task",
             5: "the N and tools cells of a model hold the same problems; every user message "
                "of the N cell is also sent in the tools cell",
             6: "every request of a tools cell is logged with tools present, and no request "
                "of an N cell is; client_settings.json names the cell's condition",
             7: f"the serve log of the last job that wrote each cell (the job its "
                f"client_settings.json names) shows vLLM {VLLM_VERSION} and no other version"}
    out(f"Smoke check (prereg section 7): {root}, run tag {SMOKE_TAG}, "
        f"{len(MODEL_ORDER) * len(FOLDERS)} cell folders")
    ok = True
    for i in range(1, 8):
        if i == 7 and serve_logs is None:
            if version_note and version_note.strip():
                out(f"item 7: vLLM version checked by hand, not by this script: "
                    f"{version_note.strip()}")
            else:
                out("item 7: NOT CHECKED (pass --serve-logs DIR, or "
                    "--version-checked-by-hand NOTE after reading the banners)")
                ok = False
        else:
            out(f"item {i}: {'PASS' if not fails[i] else 'FAIL'}: {names[i]}")
            for msg in fails[i]:
                out(f"    {msg}")
            ok = ok and not fails[i]
        if i == 5:
            for name, n in sorted(resent.items()):
                out(f"    extra user-message lines in the N cell (re-sent requests): {name}: {n}")
        if i == 7:
            if repo_note and repo_note.strip():
                out(f"item 7: tools repo at {TOOLS_REPO_COMMIT} checked by hand, not by this "
                    f"script: {repo_note.strip()}")
            else:
                out(f"item 7: tools repo at {TOOLS_REPO_COMMIT}: NOT CHECKED (it leaves no "
                    f"trace in the synced files; pass --tools-repo-checked-by-hand NOTE)")
                ok = False
    for (m, fo), f in sorted(loaded.items()):
        out(f"  rows: {f.spec.name}: {len(f.rows)}")
    out("item 1, job states: not visible in the synced files; read them with the "
        "cluster-ops status script and record them in section 10")
    out("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ------------------------------------------------------------------ the earlier runs (K1 to K3)
@dataclass
class Earlier:
    part_a: dict          # {model: {"plain" | "steered": {task: {key: (Row, Delivered)}}}}
    part_c: dict          # {model: {task: {key: (Row, Delivered)}}}; route check only
    control_b: dict       # {model: Folder}: cell B of the control, graded in analyse()
    stored: dict          # stored validator verdicts of the rerun's frozen readout
    readout: dict         # the rerun's filed readout (e1, e4)
    regrade: dict         # the filed layout re-grade (cells)
    control: dict         # the control's filed analysis output (rates)
    gt_cache: dict
    note: str


def _split(rows, grade_of) -> dict:
    out = {t: {} for t in TASKS}
    for r in rows:
        if r.task in TASKS:
            out[r.task][r.trial_key] = (r, grade_of(r))
    return out


def check_inputs(args) -> None:
    """Section 9: the four input files outside the package hash are the recorded ones."""
    for name, want in INPUT_SHA256.items():
        path = getattr(args, name)
        try:
            got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError as e:
            raise Halt(f"input file --{name.replace('_', '-')} {path}: cannot be read "
                       f"({type(e).__name__})") from e
        if got != want:
            raise Halt(f"input file --{name.replace('_', '-')} {path}: sha256 {got[:12]}... "
                       f"is not the recorded {want[:12]}... (prereg section 9)")


def load_earlier_live(args) -> Earlier:
    """Part A (and Part C, for the route check) through `rq1_metrics.load_rerun_cells`
    (the frozen package, the pinned ground truth, grades that reproduce the filed
    readout or halt), and the rows of the control's cell B through the control's reader."""
    if M.package_sha256() != CONTROL_PACKAGE:
        raise Halt("the control's frozen package changed (its hash is not 825dab63...)")
    check_inputs(args)
    cells, grades, gt_cache = R1.load_rerun_cells(args)

    def g(r):
        return grades[(r.cell, r.trial_key)]
    stored = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
              for e in json.loads(args.plan_verdicts.read_text())}
    part_a, part_c = {}, {}
    for m in MODEL_ORDER:
        rows = cells["rerun_a"][m].rows
        part_a[m] = {arm: _split([r for r in rows if r.arm == arm], g) for arm in C.ARMS}
        part_c[m] = _split(cells["rerun_c"][m].rows, g)
    control = json.loads(args.control_json.read_text())
    if control.get("package_sha256") != CONTROL_PACKAGE or control.get("mode") != "live":
        raise Halt(f"{args.control_json} is not the control's frozen live analysis output")
    tags = control.get("run_tags")
    if not isinstance(tags, dict) or set(tags) != set(MODELS):
        raise Halt(f"{args.control_json} names no run tag per model")
    control_root = args.control_root or args.results / M.RUN_TAG
    control_b = {}
    for m in MODEL_ORDER:
        if tags[m] not in (M.RUN_TAG, M.R2_TAG):
            raise Halt(f"{args.control_json}: run tag {tags[m]!r} for {m}")
        f = M.read_folder(control_root, M.control_spec(M.REGISTERED, m, CONTROL_CELL, tags[m]),
                          m, CONTROL_CELL)
        M.check_void(f)
        control_b[m] = f
    return Earlier(part_a=part_a, part_c=part_c, control_b=control_b, stored=stored,
                   readout=json.loads(args.readout_json.read_text()),
                   regrade=json.loads(args.regrade_json.read_text()), control=control,
                   gt_cache=gt_cache,
                   note=f"delivered rerun at {args.rerun_root}; control at {control_root}")


def load_earlier_fixture(root: Path, design: Design, domains: frozenset) -> Earlier:
    gt_cache = json.loads((root / "gt_cache.json").read_text())
    stored = RUN.fixture_verdicts(root)
    part_a, control_b = {}, {}
    for m in MODEL_ORDER:
        f = M.read_folder(root / "rerun", part_a_spec(design, m), m, "A", domains)
        M.check_void(f)
        graded = {r.trial_key: G.grade(r, gt_cache, stored) for r in f.rows}
        part_a[m] = {arm: _split([r for r in f.rows if r.arm == arm],
                                 lambda r: graded[r.trial_key]) for arm in C.ARMS}
        b = M.read_folder(root / "control",
                          M.control_spec(control_design(design), m, CONTROL_CELL, M.RUN_TAG),
                          m, CONTROL_CELL, domains)
        M.check_void(b)
        control_b[m] = b
    return Earlier(part_a=part_a, part_c={m: {t: {} for t in TASKS} for m in MODEL_ORDER},
                   control_b=control_b, stored=stored,
                   readout=json.loads((root / "filed_readout.json").read_text()),
                   regrade=json.loads((root / "filed_regrade.json").read_text()),
                   control=json.loads((root / "filed_control.json").read_text()),
                   gt_cache=gt_cache, note="synthetic fixture")


def check_filed_readout(er: Earlier) -> None:
    """Section 4: the frozen grades of the Part A rows reproduce the rerun's filed
    readout (E1 delivered counts of the plain and the steered arm)."""
    e1 = {(e["model"], e["task"], e["arm"]): e for e in er.readout["e1"]}
    bad = []
    for m in MODEL_ORDER:
        for t in TASKS:
            for arm in C.ARMS:
                a = [M.ok_of(g) for _, g in er.part_a[m][arm][t].values()]
                f1 = e1.get((m, t, arm))
                if f1 is None or (sum(a), len(a)) != (f1["delivered_k"], f1["n"]):
                    bad.append(f"E1 {m}/{t}/{arm}: {sum(a)}/{len(a)} vs "
                               f"{None if f1 is None else (f1['delivered_k'], f1['n'])}")
    if bad:
        raise Halt("the rerun's frozen grades do not reproduce the filed readout:\n  "
                   + "\n  ".join(bad))


def check_filed_regrade(er: Earlier, earlier_trials: dict) -> None:
    """Section 4: the Part A rows, graded again here, reproduce the filed layout re-grade
    (tools/reanalysis/out/rq1_layout_regrade.json: n, frozen_k, tolerant_k, folded_k),
    plain and steered. (The control's function checks the unaided and plain arms.)"""
    filed = {(c["tag"], c["task"], c["arm"]): c for c in er.regrade["cells"]}
    bad = []
    for m in MODEL_ORDER:
        for t in TASKS:
            for arm in C.ARMS:
                gs = list(earlier_trials[(m, arm, t)].values())
                got = (len(gs), sum(x.frozen for x in gs), sum(x.second for x in gs),
                       sum(x.folded for x in gs))
                f = filed.get((m, t, arm))
                want = None if f is None else (f["n"], f["frozen_k"], f["tolerant_k"],
                                               f["folded_k"])
                if got != want:
                    bad.append(f"{m}/{t}/{arm}: (n, frozen, second, folded) {got} vs filed {want}")
    if bad:
        raise Halt("the Part A rows do not reproduce the filed re-grade:\n  " + "\n  ".join(bad))


def check_filed_control(er: Earlier, earlier_trials: dict) -> None:
    """Section 4: the rows of the control's cell B, graded again here, reproduce the
    control's filed readout (frozen grade, second reading and case-folded counts)."""
    filed = {(r["model"], r["task"]): r for r in er.control["rates"] if r["cell"] == CONTROL_CELL}
    bad = []
    for m in MODEL_ORDER:
        for t in TASKS:
            gs = list(earlier_trials[(m, "B", t)].values())
            got = (len(gs), sum(x.frozen for x in gs), sum(x.second for x in gs),
                   sum(x.folded for x in gs))
            f = filed.get((m, t))
            want = None if f is None else (f["n"], f["frozen"]["right"], f["second"]["right"],
                                           f["folded"]["right"])
            if got != want:
                bad.append(f"{m}/{t}: (n, frozen, second, folded) {got} vs filed {want}")
    if bad:
        raise Halt("cell B of the control does not reproduce the control's filed readout:\n  "
                   + "\n  ".join(bad))


# ------------------------------------------------------------------ the grade (section 3)
@dataclass(frozen=True)
class Trial:
    key: tuple
    domain: str
    variant: int
    registered: bool        # section 3: the one registered grade
    frozen: bool            # descriptive: the rerun's frozen delivered grade
    second: bool            # descriptive: the registered grade without the lower-casing
    folded: bool            # the control's case-folded column (must reproduce the filed counts)
    reason: str             # the frozen grader's reason
    layout: str
    at_cap: bool            # stopped at the output cap: "length" and not window_full
    window_full: bool       # the final turn was refused or clipped for a full window
    completion: int
    is_exception: bool
    read: bool              # a reader of the registered grade found an answer to grade
    unread: bool            # the control's "unread final answer"
    invoked: bool           # the trial called a tool


def grade_trials(pairs, verdict: M.Verdicts, gt_cache: dict) -> dict:
    """{trial key: Trial} for a list of (Row, frozen Delivered).

    The registered grade (section 3). Solve: the delivered plan is the plan in the last
    closed code block when that block holds a plan (`block_plan`), otherwise the plan the
    frozen grader reads; it is sent to the validator in lower case, always. Simulate: the
    frozen grade, or a trace written one JSON object per line that equals the answer key
    (`line_reader_exact`, through the control's `second_reading`). An exception row (the
    harness raised on the trial) is wrong, whatever its stored answer, as under the
    rerun's grader. The descriptive columns `frozen`, `second` and `folded` are the
    control's `grade_rows`, unchanged: `second` and `folded` still read the stored answer
    of an exception row, which is the control's frozen behaviour."""
    pairs = list(pairs)
    graded = M.grade_rows(pairs, verdict, gt_cache)
    out = {}
    for r, g in pairs:
        x = graded[r.trial_key]
        if r.task == "solve":
            bp = RG.block_plan(r.response)
            plan = bp[0] if bp is not None else M.plan_of(g)
            registered = verdict(r.domain, r.problem, RG.lower(plan))
            read = x.readable or bp is not None
        else:
            registered = x.second
            read = x.readable or PILOT.line_reader_steps(r.response) is not None
        if r.is_exception:
            registered = False
        _check(isinstance(registered, bool), f"registered grade of {r.trial_key} is a bool")
        full = window_full(r)
        out[r.trial_key] = Trial(
            key=r.trial_key, domain=r.domain, variant=r.variant, registered=registered,
            frozen=x.frozen, second=x.second, folded=x.folded, reason=x.reason,
            layout=x.layout, at_cap=x.at_cap and not full, window_full=full,
            completion=x.completion,
            is_exception=x.is_exception, read=read, unread=x.unread, invoked=r.invoked)
    return out


# ------------------------------------------------------------------ labels and readings
def base_label(label: str) -> str:
    return label.replace(" (not after Holm)", "")


def m3_label(c: dict) -> str:
    """Section 4, M3: naming the tool helps (interval above 0), hurts (below 0), no
    difference shown otherwise. "(not after Holm)" as for every contrast."""
    if c["lo"] > 0:
        lab = "naming the tool helps"
    elif c["hi"] < 0:
        lab = "naming the tool hurts"
    else:
        return "no difference shown"
    return lab if c["p_holm"] < HOLM_ALPHA else lab + " (not after Holm)"


def label_of(name: str, c: dict) -> str:
    """Section 4: M1 and M2 by the control's C4 rule (tools ahead / no tools ahead / no
    difference shown), M3 by `m3_label`, K1 to K3 by the control's C1 to C3 rule
    (criterion met / a difference is shown / unresolved, margin 5 points)."""
    if name in ("M1", "M2"):
        return M.c4_label(c)
    if name == "M3":
        return m3_label(c)
    return M.contrast_label(c)


def q1_reading(m1: dict, m2: dict, m3: dict) -> dict:
    """Section 5, Q1: the label of M1 is the answer for "tools offered", the label of M2
    for "tools offered and named"; where the two differ both are stated and M3 says what
    naming the tool added. Two labels differ when they differ without the Holm words."""
    differ = base_label(m1["label"]) != base_label(m2["label"])
    s = (f"tools offered: {m1['label']} ({M.ci_text(m1)}); tools offered and named: "
         f"{m2['label']} ({M.ci_text(m2)})")
    if differ:
        s += f"; the two differ; naming the tool: {m3['label']} ({M.ci_text(m3)})"
    return {"tools_offered": m1["label"], "tools_offered_and_named": m2["label"],
            "differ": differ, "naming_the_tool": m3["label"] if differ else None, "sentence": s}


def q2_reading(name: str, c: dict, run_dates: str) -> dict:
    """Section 5, Q2: where a check meets the criterion, this run reproduces the earlier
    one for that model, task and arm; where it does not, the estimate is given. Printed
    with the dates of both runs."""
    met = M.met(c)
    arm = CONTINUITY[name][1]
    earlier = EARLIER_WORDS[CONTINUITY[name][0]]
    if met:
        s = (f"this run reproduces {earlier} for arm {arm} within the margin "
             f"({c['label']}, {M.ci_text(c)})")
    else:
        s = (f"this run does not meet the criterion against {earlier} for arm {arm} "
             f"({c['label']}, {M.ci_text(c)})")
    s += f"; earlier run: {EARLIER_DATES[name]}; this run: {run_dates}"
    return {"criterion_met": met, "label": c["label"], "sentence": s}


# ------------------------------------------------------------------ section 6, rules 3 and 4
def tracks_of(domains_dir: Path, live: bool) -> dict[str, str]:
    """Domain name -> "classical" | "numeric", as `bc_common.domain_track` reads it from
    the domains tree (that function reads the repository's own tree only; in live mode
    the two must agree)."""
    out = {}
    for track in ("classical", "numeric"):
        if (domains_dir / track).is_dir():
            for d in sorted((domains_dir / track).iterdir()):
                if d.is_dir():
                    out[d.name] = track
    if live and domains_dir.resolve() == (REPO / "domains").resolve():
        _check(out == domain_track(), "domain tracks equal bc_common.domain_track()")
    return out


def rq2_cells(arms: dict, track: dict) -> list[dict]:
    """Section 6 rule 3, which tool was called: `rq23_metrics.row2` and `rq23_metrics.rq2`
    on this run's tool rows (classes none / right only / right + other / other only),
    with the self-check of `rq23_metrics.rq2_rows` (the harness rule on the stored calls
    equals the stored `tool_selected`)."""
    rows = []
    for m in MODEL_ORDER:
        for arm in ("P", "S"):
            for r in arms[m][arm]:
                try:
                    rows.append(R23.row2("matched run", m, C.THINK, r.arm, r.task, r.domain,
                                         [c.name for c in r.tool_calls], r.tool_selected, track))
                except ValueError as e:
                    raise Halt(f"tool choice: {r.domain} has no track ({e})") from e
    bad = [x for x in rows if x["tool_selected"] is not None
           and bool(x["tool_selected"]) != x["harness_called"]]
    if bad:
        raise Halt(f"{len(bad)} tool rows where the harness rule on the stored calls differs "
                   f"from the stored tool_selected (first: {bad[0]['model']} {bad[0]['task']} "
                   f"{bad[0]['domain']})")
    cells = R23.rq2(rows)["cells"]
    _check(len(cells) == len(MODELS) * len(TASKS) * 2, "tool choice: 12 cells")
    return sorted(cells, key=lambda c: (MODEL_ORDER.index(c["model"]), TASKS.index(c["task"]),
                                        c["arm"]))


def rq3_cells(arms: dict, frozen: dict, trials: dict, gt_cache: dict) -> list[dict]:
    """Section 6 rule 3, tool right and final answer wrong: among the trials whose stored
    harness grade is right (the tool returned the right result, the definition of
    `rq23_metrics.rq3_rerun`), the share whose final answer is wrong under this run's
    registered grade. Beside it the frozen-grade version, which is that function's own
    measure, with the categories of the frozen `e4.classify` (the loop of the frozen
    `analysis.e4_cell`, written out so that a row the classifier refuses is counted as
    "not classified" and does not halt the registered tables). (`rq3_rerun` itself loops
    over the rerun's five tasks and checks the rerun's readout, so it cannot be called on
    this run.)"""
    out = []
    for m in MODEL_ORDER:
        rows = list(arms[m]["P"]) + list(arms[m]["S"])
        grades = {(r.cell, r.trial_key): frozen[(m, ARM_FOLDER["P"])][r.trial_key] for r in rows}
        for task in TASKS:
            for arm_name, arm in (("plain", "P"), ("steered", "S")):
                tv = [r for r in rows if r.task == task and r.arm == arm_name
                      and r.success is True]
                doms = [r.domain for r in tv]
                lost_frozen = [M.ok_of(grades[(r.cell, r.trial_key)]) is False for r in tv]
                why: Counter = Counter()
                not_classified = 0
                for r, gone in zip(tv, lost_frozen):
                    if not gone:
                        continue
                    try:
                        cat, _sub = E4.classify(r, grades[(r.cell, r.trial_key)], gt_cache)
                    except S.SchemaError:
                        not_classified += 1
                        continue
                    _check(cat in E4.CATS, f"a category of the rerun ({cat!r})")
                    why[cat] += 1
                lost = [trials[(m, arm, task)][r.trial_key].registered is False for r in tv]
                out.append({
                    "model": m, "task": task, "arm": arm,
                    "n_trials": sum(r.task == task and r.arm == arm_name for r in rows),
                    "n_tool_right": len(tv), "n_lost": sum(lost),
                    "lost": R1.boot(lost, doms),
                    "n_lost_frozen": sum(lost_frozen),
                    "lost_frozen": R1.boot(lost_frozen, doms),
                    "why_frozen": {c: why[c] for c in E4.CATS if why[c]},
                    "not_classified": not_classified})
    return out


def breakdowns(arms: dict, frozen: dict, trials: dict, gt_cache: dict,
               domains_dir: Path) -> dict:
    """Section 6 rule 4: solved by reference plan length, simulate by trace length and
    the lenient simulate score, with the bins and functions `rq1_control_metrics.py`
    uses (`rq1_metrics.problem_facts`, `metric3`, and `metric2` with
    `rq1_control_metrics.best_state_score_second` put in place for that call only, as
    that script does). A trial counts as right under this run's registered grade."""
    recs = []
    for m in MODEL_ORDER:
        for arm in ARMS:
            for r in arms[m][arm]:
                g = frozen[(m, ARM_FOLDER[arm])][r.trial_key]
                plan = None
                if r.task == "solve":
                    bp = RG.block_plan(r.response)
                    plan = bp[0] if bp is not None else g.plan
                recs.append(R1.rec(model_name(m), ARM_REC[arm], r.task, r.domain, r.problem,
                                   r.plan_label, r.variant,
                                   trials[(m, arm, r.task)][r.trial_key].registered, None, plan,
                                   r.response,
                                   [(c.name, c.arguments, c.result) for c in r.tool_calls]))
    facts = R1.problem_facts(recs, gt_cache, domains_dir)
    used = {(x["domain"], x["problem"]) for x in recs}
    missing = sorted(used - set(facts))
    if missing:
        raise Halt(f"by-length breakdowns: no reference plan in the ground-truth cache for "
                   f"{missing[:5]}")
    if any(f["objects"] is None for f in facts.values()):
        raise Halt("by-length breakdowns: a solvable problem has no readable (:objects ...) "
                   "block under the domains directory")
    frozen_best = R1.best_state_score
    R1.best_state_score = RC.best_state_score_second
    try:
        m2 = R1.metric2(recs, gt_cache, facts)
    finally:
        R1.best_state_score = frozen_best
    m3 = R1.metric3(recs, facts)
    return {"simulate_overall": m2["overall"], "simulate_by_trace_length": m2["cells"],
            "simulate_left_out": m2["skipped_problems"],
            "simulate_undetermined": m2["undetermined_problems"],
            "solve_by_reference_length": m3["by_length"], "solve_overall": m3["corr"]}


# ------------------------------------------------------------------ analysis
def analyse(design: Design, arms: dict, er: Earlier, verdict: M.Verdicts, mode: str,
            run_dates: str, audit: dict, audit_notes: dict, corpus: list,
            domains_dir: Path, plan_differs: tuple, halt_on_tripwires: bool = True) -> dict:
    k = design.k_domains
    gt = er.gt_cache
    # The earlier runs: frozen grades reproduce the filed readout; keys equal the rerun's.
    check_filed_readout(er)
    check_keys_equal_rerun(arms, er.part_a)
    for m in MODEL_ORDER:
        check_same_problems(m, arms[m])
    # The route returns the stored verdicts before any new plan is validated.
    checked = M.check_route(
        verdict, er.stored,
        [rg for m in MODEL_ORDER for src in (er.part_c[m], er.part_a[m]["plain"],
                                             er.part_a[m]["steered"])
         for rg in src["solve"].values()])
    # Grades. The frozen grade of every new row takes its solve verdicts from the route.
    frozen: dict = {}
    trials: dict = {}
    for m in MODEL_ORDER:
        for fo in FOLDERS:
            rows = [r for arm in ARMS if ARM_FOLDER[arm] == fo for r in arms[m][arm]]
            pairs = M.frozen_grades(rows, verdict, gt)
            frozen[(m, fo)] = {r.trial_key: g for r, g in pairs}
            graded = grade_trials(pairs, verdict, gt)
            for arm in ARMS:
                if ARM_FOLDER[arm] == fo:
                    for t in TASKS:
                        trials[(m, arm, t)] = {q: x for q, x in graded.items()
                                               if q[0] == t and q[4] in ARM_WORDINGS[arm]}
    earlier: dict = {}
    for m in MODEL_ORDER:
        b = grade_trials(M.frozen_grades(er.control_b[m].rows, verdict, gt), verdict, gt)
        for t in TASKS:
            earlier[(m, "B", t)] = {q: x for q, x in b.items() if q[0] == t}
            for arm in C.ARMS:
                earlier[(m, arm, t)] = grade_trials(er.part_a[m][arm][t].values(), verdict, gt)
    check_filed_regrade(er, earlier)
    check_filed_control(er, earlier)
    for key, gs in list(trials.items()) + list(earlier.items()):
        _check(len(gs) == design.per_task_arm, f"{key}: {design.per_task_arm} trials")

    # Rates: the registered grade, and the two descriptive grades beside it.
    rates = []
    for m in MODEL_ORDER:
        for t in TASKS:
            for cell, gs in [(a, trials[(m, a, t)]) for a in ARMS] + [
                    (EARLIER_WORDS[e], earlier[(m, e, t)]) for e in ("B", "plain", "steered")]:
                vals = list(gs.values())
                e = {"model": m, "task": t, "cell": cell, "n": len(vals),
                     "this_run": cell in ARMS,
                     "registered_differs_from_case_folded": sum(
                         x.registered != x.folded for x in vals)}
                for gr in GRADES:
                    e[gr] = M.rate(vals, gr, k, f"rate {m}/{t}/{cell}/{gr}")
                rates.append(e)
    by_rate = {(e["model"], e["task"], e["cell"]): e for e in rates}

    def by_canon(gs: dict) -> dict:
        out = {canon(q): x for q, x in gs.items()}
        _check(len(out) == len(gs), "pairing keys are unique within an arm")
        return out

    def family(name: str, x_of, y_of, grade: str) -> list[dict]:
        fam = []
        for m in MODEL_ORDER:
            for t in TASKS:
                c = M.paired(by_canon(x_of(m, t)), by_canon(y_of(m, t)), grade, k,
                             f"{name} {m}/{t}/{grade}")
                _check(c["n_pairs"] == design.per_task_arm and c["unpaired"] == 0,
                       f"{name} {m}/{t}: {design.per_task_arm} pairs, none unpaired")
                fam.append({"name": name, "grade": grade, "model": m, "task": t, **c})
        adj = ST.holm({(e["model"], e["task"]): e["p"] for e in fam}, HOLM_FAMILY)
        for e in fam:
            e["p_holm"] = adj[(e["model"], e["task"])]
            # A label is a registered reading; the descriptive grades carry none.
            e["label"] = label_of(name, e) if grade == REGISTERED_GRADE else None
        return fam

    contrasts, continuity = [], []
    for gr in GRADES:
        for name, (x, y) in CONTRASTS.items():
            contrasts += family(name, lambda m, t, x=x: trials[(m, x, t)],
                                lambda m, t, y=y: trials[(m, y, t)], gr)
        for name, (x, y) in CONTINUITY.items():
            continuity += family(name, lambda m, t, x=x: earlier[(m, x, t)],
                                 lambda m, t, y=y: trials[(m, y, t)], gr)
    _check(len(contrasts) == N_CONTRASTS * len(GRADES), "18 contrasts under each grade")
    _check(len(continuity) == N_CONTINUITY * len(GRADES), "18 continuity checks under each grade")
    by_c = {(e["name"], e["grade"], e["model"], e["task"]): e for e in contrasts + continuity}

    readings = []
    for m in MODEL_ORDER:
        for t in TASKS:
            reg = {n: by_c[(n, REGISTERED_GRADE, m, t)] for n in (*CONTRASTS, *CONTINUITY)}
            readings.append({"model": m, "task": t,
                             "Q1": q1_reading(reg["M1"], reg["M2"], reg["M3"]),
                             "Q2": {n: q2_reading(n, reg[n], run_dates) for n in CONTINUITY}})

    # Tripwires (section 8), on the registered grade.
    fired = {}
    for t in TASKS:
        ks = {by_rate[(m, t, a)][REGISTERED_GRADE]["right"] for m in MODEL_ORDER for a in ARMS}
        if len(ks) == 1:
            fired[f"T1:{t}"] = (f"the count of right answers on {t} is the same in all nine "
                                f"cells ({ks.pop()} of {design.per_task_arm})")
    for m in MODEL_ORDER:
        for t in TASKS:
            for arm in ARMS:
                if not any(x.read for x in trials[(m, arm, t)].values()):
                    fired[f"T2:{m}:{arm}:{t}"] = (f"arm {arm} of {m}: the grader reads no "
                                                  f"answer at all on {t}")
            for name in CONTINUITY:
                d = by_c[(name, REGISTERED_GRADE, m, t)]["est"]
                if abs(d) > TRIPWIRE_POINTS:
                    fired[f"T3:{name}:{m}:{t}"] = (
                        f"arm {CONTINUITY[name][1]} of {m}/{t} is {d:+.1f} points from "
                        f"{EARLIER_WORDS[CONTINUITY[name][0]]}")
            n_unread = sum(x.unread for x in trials[(m, "N", t)].values())
            limit = unread_limit(design, m, t)
            if n_unread > limit:
                fired[f"T5:{m}:{t}"] = (f"arm N of {m}, {t}: {n_unread} unread final answers "
                                        f"of {design.per_task_arm} (more than {limit:g})")
        for arm in ("P", "S"):
            for t in TASKS:
                if not any(x.invoked for x in trials[(m, arm, t)].values()):
                    fired[f"T4:{m}:{arm}:{t}"] = (f"tools arm {arm} of {m}, {t}: no trial "
                                                  f"called a tool")
    unaudited = {i: v for i, v in fired.items() if i not in audit_notes}
    if unaudited and halt_on_tripwires:
        raise Halt("readout tripwire(s) fired (section 8); audit before any readout "
                   "sentence:\n  " + "\n  ".join(f"{i}: {v}" for i, v in unaudited.items()))
    extra = set(audit_notes) - set(fired)
    if extra:
        raise Halt(f"audit notes for tripwires that did not fire: {sorted(extra)}")

    secondary = secondary_tables(trials)
    # Section 3, descriptive: the simulate trials on the problems whose prompt plan can
    # differ from the plan of the cached key, and how many of them are right.
    differs = {tuple(x) for x in plan_differs}
    key_plan = []
    for m in MODEL_ORDER:
        for arm in ARMS:
            hit = [x for q, x in trials[(m, arm, "simulate")].items() if (q[1], q[2]) in differs]
            if design is REGISTERED:
                _check(len(hit) == KEY_PLAN_DIFFERS_TRIALS,
                       f"{m}/{arm}: 18 simulate trials on the six problems")
            key_plan.append({"model": m, "arm": arm, "trials": len(hit),
                             "right": sum(x.registered for x in hit)})
    track = tracks_of(domains_dir, live=mode != "fixture")
    return {
        "mode": mode, "package_sha256": package_sha256(), "design": dataclasses.asdict(design),
        "run_dates": run_dates, "part_a_dates": PART_A_DATES, "control_dates": CONTROL_DATES,
        "earlier": er.note, "corpus": corpus, "audit": audit,
        "route_checked_plans": checked, "validated_plans": len(verdict.cache),
        "n_contrasts": N_CONTRASTS, "n_continuity": N_CONTINUITY,
        "rates": rates, "contrasts": contrasts, "continuity": continuity, "readings": readings,
        "secondary": secondary,
        "key_plan_differs": {"problems": sorted(f"{d}/{p}" for d, p in differs),
                             "cells": key_plan},
        "tool_choice": rq2_cells(arms, track),
        "tool_right_answer_wrong": rq3_cells(arms, frozen, trials, gt),
        "breakdowns": breakdowns(arms, frozen, trials, gt, domains_dir),
        "tripwires_audited": {i: {"fired": fired[i], "note": audit_notes[i]}
                              for i in fired if i in audit_notes},
        "tripwires_fired_not_halting": {i: v for i, v in unaudited.items()},
    }


def secondary_tables(trials: dict) -> list[dict]:
    """Section 8, descriptive, per model, task and arm."""
    out = []
    for (m, arm, t), gs in trials.items():
        vals = list(gs.values())
        ws = ARM_WORDINGS[arm]
        out.append({
            "model": m, "task": t, "arm": arm, "n": len(vals),
            "by_wording": {str(v): {gr: sum(getattr(x, gr) for x in vals if x.variant == v)
                                    for gr in GRADES} for v in ws},
            "per_wording_n": {str(v): sum(x.variant == v for x in vals) for v in ws},
            "layout": dict(sorted(Counter(x.layout for x in vals).items())),
            "at_output_cap": sum(x.at_cap for x in vals),
            "window_full": sum(x.window_full for x in vals),
            "mean_output_tokens": sum(x.completion for x in vals) / len(vals),
            "exception_rows": sum(x.is_exception for x in vals),
            "read": sum(x.read for x in vals),
            "failure_reasons": dict(sorted(Counter(
                x.reason for x in vals if x.registered is False).items())),
            "unread_final_answers": sum(x.unread for x in vals),
            "called_a_tool": sum(x.invoked for x in vals)})
    return out


# ------------------------------------------------------------------ markdown
def render(res: dict) -> str:
    def cell_rate(r: dict) -> str:
        return f"{r['right']}/{r['n']}, {r['est']:.1f} [{r['lo']:.1f}, {r['hi']:.1f}]"

    n = res["design"]["per_task_arm"]
    common = (f"n = {n} trials per model, task and arm (three wordings, "
              f"{res['design']['k_domains']} domains); {res['n_contrasts']} contrasts and "
              f"{res['n_continuity']} continuity checks")
    dry = res["mode"].startswith("dry run")
    L = []
    if dry:
        L += ["**DRY RUN ON EXISTING DATA. Not the matched run and not a result of it.** Arm N "
              "is filled with the rows of the control's cell B, arms P and S with the rows of "
              "Part A of the rerun. No row of the matched run was read.", ""]
    L += [f"*Generated by `tools/reanalysis/matched_run.py` ({res['mode']} mode, package hash "
          f"`{res['package_sha256'][:12]}...`). The registered analysis of "
          f"`development/reference/matched_run_prereg.md`. Three models, thinking off, solve "
          f"and simulate. Arm N: no tools, the format-stated system message. Arm P: tools "
          f"offered, plain wordings. Arm S: tools offered, steered wordings. Dates: this run "
          f"{res['run_dates']}; the control {res['control_dates']}; Part A of the rerun "
          f"{res['part_a_dates']}. The registered grade is delivered right: on solve the plan "
          f"in the last closed code block when that block holds a plan, otherwise the plan the "
          f"rerun's grader reads, sent to the validator in lower case; on simulate the trace "
          f"the rerun's grader reads, or a trace written one JSON object per line, equal to "
          f"the answer key. Intervals are 95% domain-cluster bootstrap. {common}. Solve plans "
          f"checked against the stored verdicts before any new plan was validated: "
          f"{res['route_checked_plans']}; plans validated in all: {res['validated_plans']}.*", ""]
    for title, key in (("Tripwires that fired and were audited", "tripwires_audited"),
                       ("Tripwires that fired (dry run, not halting)",
                        "tripwires_fired_not_halting")):
        if res[key]:
            L.append(f"**{title}:** " + "; ".join(
                f"{i}: {v['fired']} (audit: {v['note']})" if isinstance(v, dict) else f"{i}: {v}"
                for i, v in res[key].items()))
            L.append("")

    L += ["#### Matched run: delivered right per arm", "",
          f"The registered grade, and beside it the two descriptive grades (the rerun's frozen "
          f"grade; the registered grade without the lower-casing). No reading uses the "
          f"descriptive grades. {common}.", "",
          md_table(["model", "task", "arm", "trials", "registered grade",
                    "frozen grade (descriptive)", "not lower-cased (descriptive)",
                    "trials where the registered grade differs from the control's "
                    "case-folded column"],
                   [[model_name(r["model"]), r["task"], ARM_WORDS[r["cell"]], r["n"],
                     cell_rate(r["registered"]), cell_rate(r["frozen"]), cell_rate(r["second"]),
                     r["registered_differs_from_case_folded"]]
                    for r in res["rates"] if r["this_run"]]), ""]
    kp = res["key_plan_differs"]
    L += ["#### Matched run: simulate trials on the problems whose prompt plan can differ "
          "from the cached key (descriptive)", "",
          f"The answer key is the cached reference trace, as in every earlier readout. On "
          f"these problems the plan placed in the prompt can differ from the plan of the "
          f"cached key, so a correct simulation of the prompt's plan is graded wrong there: "
          f"{', '.join(kp['problems'])}. {common}.", "",
          md_table(["model", "arm", "trials on those problems", "right (registered grade)"],
                   [[model_name(c["model"]), c["arm"], c["trials"], c["right"]]
                    for c in kp["cells"]]), ""]
    L += ["#### Matched run: contrasts M1 to M3, registered grade", "",
          f"Points, paired on the trial (task, domain, problem, plan label, wording); a "
          f"steered wording is paired with its plain wording (v14 with v11, v15 with v12, v16 "
          f"with v13). {common}. The sign-flip p is exact over the 20 domains, Holm-adjusted "
          f"across the six contrasts of the same name.", "",
          md_table(["contrast", "model", "task", "pairs", "difference [95% interval]", "reading",
                    "sign-flip p", "Holm-adjusted p", "unpaired"],
                   [[f"{c['name']} ({CONTRAST_WORDS[c['name']]})", model_name(c["model"]),
                     c["task"], c["n_pairs"], M.ci_text(c), c["label"], f"{c['p']:.3g}",
                     f"{c['p_holm']:.3g}", c["unpaired"]]
                    for c in res["contrasts"] if c["grade"] == REGISTERED_GRADE]), ""]
    L += ["#### Matched run: registered readings (section 5, Q1)", "",
          f"Per model and task, never pooled. {common}.", "",
          md_table(["model", "task", "what the data say"],
                   [[model_name(e["model"]), e["task"], e["Q1"]["sentence"]]
                    for e in res["readings"]]), ""]
    L += ["#### Matched run: continuity checks K1 to K3 (across runs, descriptive, no gate)", "",
          f"Registered grade on both sides; the earlier rows are graded again with it. Margin "
          f"5 points, endpoints included. Dates: this run {res['run_dates']}; the control "
          f"{res['control_dates']}; Part A {res['part_a_dates']}. {common}.", "",
          md_table(["check", "model", "task", "pairs", "difference [95% interval]", "reading",
                    "sign-flip p", "Holm-adjusted p", "unpaired", "earlier run"],
                   [[f"{c['name']} ({CONTRAST_WORDS[c['name']]})", model_name(c["model"]),
                     c["task"], c["n_pairs"], M.ci_text(c), c["label"], f"{c['p']:.3g}",
                     f"{c['p_holm']:.3g}", c["unpaired"], EARLIER_DATES[c["name"]]]
                    for c in res["continuity"] if c["grade"] == REGISTERED_GRADE]), "",
          "Beside K1: the user texts of the N cell against those of the control's cell B, by "
          "sha256 (a difference does not halt; on simulate it would mean the plan placed in "
          "the prompt moved between the two runs).", "",
          md_table(["model", "task", "user texts in both", "only in this run",
                    "only in the control"],
                   [[model_name(u["model"]), u["task"], u["shared"], u["only_this_run"],
                     u["only_control"]] for u in res["audit"].get("user_texts_vs_control", [])]
                   or [["–", "–", "not compared in this mode", "–", "–"]]), "",
          md_table(["model", "task", "check", "reading (section 5, Q2)"],
                   [[model_name(e["model"]), e["task"], name, e["Q2"][name]["sentence"]]
                    for e in res["readings"] for name in CONTINUITY]), ""]
    for gr in DESCRIPTIVE_GRADES:
        L += [f"#### Matched run: contrasts under {GRADE_WORDS[gr]}", "",
              f"For the supplement only; no reading of section 5 uses this table. {common}.", "",
              md_table(["contrast", "model", "task", "pairs", "difference [95% interval]"],
                       [[f"{c['name']} ({CONTRAST_WORDS[c['name']]})", model_name(c["model"]),
                         c["task"], c["n_pairs"], M.ci_text(c)]
                        for c in res["contrasts"] + res["continuity"] if c["grade"] == gr]), ""]
    L += ["#### Matched run: the earlier runs, graded again (descriptive)", "",
          f"The rows of the control's cell B and of Part A under the three grades. Their "
          f"frozen grades reproduce the filed readouts (checked before any contrast). "
          f"{common}.", "",
          md_table(["model", "task", "rows", "trials", "registered grade",
                    "frozen grade (descriptive)", "not lower-cased (descriptive)",
                    "trials where the registered grade differs from the control's "
                    "case-folded column"],
                   [[model_name(r["model"]), r["task"], r["cell"], r["n"],
                     cell_rate(r["registered"]), cell_rate(r["frozen"]), cell_rate(r["second"]),
                     r["registered_differs_from_case_folded"]]
                    for r in res["rates"] if not r["this_run"]]), ""]
    L += ["#### Matched run: secondary, descriptive (section 8)", "",
          f"Right answers by wording under the registered grade; the layout of the answer; "
          f"answers that stopped at the output cap (the answer ended at the cap and its final "
          f"turn was not refused or clipped); trials whose final turn was refused or clipped "
          f"because the prompt and the tool output filled the window; mean output tokens (in a tools arm, summed "
          f"over the turns of a trial; the rows hold no per-turn count); the rerun's failure reason of each trial that "
          f"is wrong under the registered grade. {common}.", "",
          md_table(["model", "task", "arm", "right by wording", "layout",
                    "stopped at the output cap", "final turn refused or clipped (window full)",
                    "mean output tokens",
                    "exception rows", "unread final answers", "trials with a tool call",
                    "frozen reason of each wrong trial"],
                   [[model_name(s["model"]), s["task"], s["arm"],
                     "; ".join(f"v{v} {d['registered']}/{s['per_wording_n'][v]}"
                               for v, d in s["by_wording"].items()),
                     "; ".join(f"{k} {v}" for k, v in s["layout"].items()), s["at_output_cap"],
                     s["window_full"], f"{s['mean_output_tokens']:.0f}",
                     s["exception_rows"], s["unread_final_answers"], s["called_a_tool"],
                     "; ".join(f"{k} {v}" for k, v in s["failure_reasons"].items()) or "–"]
                    for s in res["secondary"]]), ""]
    L += ["#### Matched run: which tool was called (section 6 rule 3, supplement)", "",
          f"The classes of `tools/reanalysis/rq23_metrics.py`, on this run's tool rows. A "
          f"second sample on two tasks; it does not replace the rerun's figures. {common}.", "",
          md_table(["model", "task", "arm", "trials", "no call", "right only", "right + other",
                    "other only", "exactly the right tool [95% interval]"],
                   [[model_name(c["model"]), c["task"], c["arm"], c["n"], c["counts"]["none"],
                     c["counts"]["right_only"], c["counts"]["right_plus"],
                     c["counts"]["other_only"], R1.cell(c["exactly_right"])]
                    for c in res["tool_choice"]]), ""]
    L += ["#### Matched run: tool right and final answer wrong (section 6 rule 3, supplement)",
          "",
          f"Among the trials whose tool returned the right result, the trials whose final "
          f"answer is wrong under the registered grade. Beside it the same under the rerun's "
          f"frozen grade (the measure of `rq23_metrics.py`) with its categories. {common}.", "",
          md_table(["model", "task", "arm", "trials", "tool right",
                    "answer wrong (registered grade)", "share [95% interval]",
                    "answer wrong (frozen grade)", "why (frozen grade)",
                    "not classified by the rerun's rules"],
                   [[model_name(c["model"]), c["task"], c["arm"], c["n_trials"],
                     c["n_tool_right"], c["n_lost"], R1.cell(c["lost"]), c["n_lost_frozen"],
                     "; ".join(f"{k} {v}" for k, v in c["why_frozen"].items()) or "–",
                     c["not_classified"]]
                    for c in res["tool_right_answer_wrong"]]), ""]
    b = res["breakdowns"]
    L += ["#### Matched run: solved by reference plan length (section 6 rule 4, descriptive)",
          "", f"Registered grade; the bins of `rq1_metrics.py`. {common}.", "",
          md_table(["model", "arm", "bin", "trials", "solved"],
                   [[c["model"], R1.ARM_NAMES[c["arm"]], c["bin"], c["n"], R1.cell(c["solved"])]
                    for c in b["solve_by_reference_length"]]), "",
          "#### Matched run: simulate by trace length and the lenient score (section 6 rule 4, "
          "descriptive)", "",
          f"Registered grade for the exact trace; per-state scores as "
          f"`rq1_control_metrics.py` computes them. Problems left out, chosen by the rule "
          f"of that script from this run's rows (the plan most tool rows passed to the "
          f"simulate tool is not the reference plan): "
          f"{', '.join(b['simulate_left_out']) or 'none'}. {common}.", "",
          md_table(["model", "arm", "bin", "trials", "exact trace", "states, strict",
                    "states, lenient"],
                   [[c["model"], R1.ARM_NAMES[c["arm"]], c.get("bin", "all"), c["n"],
                     R1.cell(c["exact"]), R1.cell(c["states"]), R1.cell(c["states_salvaged"])]
                    for c in b["simulate_overall"] + b["simulate_by_trace_length"]]), ""]
    L += ["#### Matched run: corpus", "",
          f"Rows per cell folder as read by the frozen loader. {common}.", "",
          md_table(["cell folder", "rows", "exception rows (kept, graded as they are)",
                    "cut by storage (accepted: stopped at the output cap)", "torn lines"],
                   [[c["cell"], c["rows"], c["exception_rows"], c["storage_cut_accepted"],
                     c["torn_lines"]] for c in res["corpus"]]), ""]
    return "\n".join(L) + "\n"


def write_pair(out: Path, stem: str, js: str, md: str) -> None:
    """Both files, or neither (temporary names, then rename). The control's `write_pair`
    writes the control's file names."""
    final = [out / f"{stem}.json", out / f"{stem}.md"]
    tmp = [f.with_name(f.name + ".tmp") for f in final]
    placed: list[Path] = []
    try:
        out.mkdir(parents=True, exist_ok=True)
        for t, text in zip(tmp, (js, md)):
            t.write_text(text)
        for t, f in zip(tmp, final):
            t.replace(f)
            placed.append(f)
    except OSError as e:
        for f in tmp + placed:
            with contextlib.suppress(OSError):
                f.unlink(missing_ok=True)
        raise Halt(f"could not write to {out} ({e}); nothing kept") from e


# ------------------------------------------------------------------ main
def fixture_design(root: Path) -> Design:
    d = json.loads((root / "design.json").read_text())
    design = Design(name="fixture", per_task_arm=d["per_task_arm"], n_folder=d["n_folder"],
                    tools_folder=d["tools_folder"], per_wording=d["per_wording"],
                    per_task_wording=d["per_task_wording"], k_domains=d["k_domains"])
    if design.n_folder == REGISTERED.n_folder:
        raise Halt("fixture mode refuses a registered-size design")
    check_design(design, registered=False)
    return design


def corpus_table(folders: dict) -> list[dict]:
    return [{"cell": f.spec.name, "rows": len(f.rows), "torn_lines": f.torn_lines,
             "exception_rows": f.exception_rows, "infra_rows": f.infra_rows,
             "storage_cut_accepted": len(f.storage_cut)}
            for m in MODEL_ORDER for f in folders[m].values()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--print-package-hash", action="store_true")
    ap.add_argument("--fixture", type=Path, help="synthetic fixture root (tests only)")
    ap.add_argument("--smoke-check", type=Path, metavar="ROOT")
    ap.add_argument("--dry-run-existing", action="store_true",
                    help="fill the arms from the control's cell B and Part A of the rerun")
    ap.add_argument("--matched-root", type=Path)
    ap.add_argument("--control-root", type=Path)
    ap.add_argument("--r2-models", default="",
                    help=f"comma-separated model tags whose two cells were rerun under {R2_TAG}")
    ap.add_argument("--marketplace", type=Path,
                    help="the pddl-copilot checkout (required in live and dry-run mode)")
    here = Path(__file__).resolve().parent
    ap.add_argument("--regrade-json", type=Path, default=here / "out" / "rq1_layout_regrade.json")
    ap.add_argument("--control-json", type=Path, default=here / "out" / "control_prompt_fix.json")
    ap.add_argument("--serve-logs", type=Path,
                    help="folder holding the <job>-vllm-<model>.log serve logs")
    ap.add_argument("--version-checked-by-hand", metavar="NOTE",
                    help="item 7, vLLM version checked by hand: a note saying how")
    ap.add_argument("--tools-repo-checked-by-hand", metavar="NOTE",
                    help=f"item 7, the cluster's tools repo at {TOOLS_REPO_COMMIT}: a note "
                         f"saying how it was checked")
    ap.add_argument("--run-dates", help="the dates of the matched run (prereg section 9)")
    ap.add_argument("--i-have-frozen", metavar="SHA256")
    ap.add_argument("--audited-tripwires", default="")
    ap.add_argument("--audit-notes", type=Path)
    args = ap.parse_args(argv)

    if args.print_package_hash:
        for rel, digest in file_hashes():
            print(f"{digest}  {rel}")
        print(f"{package_sha256()}  (package hash for --i-have-frozen)")
        return 0
    if args.smoke_check is not None:
        return smoke_check(args.smoke_check, args.serve_logs, args.version_checked_by_hand,
                           args.tools_repo_checked_by_hand)
    stem = "matched_run"
    default_out = (here / "out").resolve()
    try:
        check_constants()
        audited = {x for x in args.audited_tripwires.split(",") if x}
        try:
            notes = RUN.load_audit_notes(args.audit_notes, audited)
        except RUN.Halt as e:
            raise Halt(str(e)) from e
        halt_on_tripwires = True
        if args.fixture is not None and args.dry_run_existing:
            raise Halt("--fixture and --dry-run-existing are different modes")
        if args.fixture is not None:
            root = args.fixture
            if not (root / FIXTURE_MARKER).exists():
                raise Halt(f"fixture mode: {root} has no {FIXTURE_MARKER} marker")
            if args.numbers:
                raise Halt("--numbers is for live mode only")
            if args.out.resolve() == default_out:
                raise Halt("fixture mode needs its own --out (not tools/reanalysis/out)")
            if not (args.run_dates and args.run_dates.strip()):
                raise Halt("--run-dates is required (the continuity checks state the dates of "
                           "both runs)")
            design = fixture_design(root)
            domains = M.fixture_domains(root)
            matched_root = root / "matched"
            tags, r2_found = resolve_tags(matched_root, design, args.r2_models, domains)
            folders = load_matched(matched_root, design, tags, domains)
            audit = audit_matched(matched_root, folders,
                                  None if args.version_checked_by_hand else root / "serve_logs",
                                  args.version_checked_by_hand, args.tools_repo_checked_by_hand)
            er = load_earlier_fixture(root, design, domains)
            audit["user_texts_vs_control"] = [
                u for m in MODEL_ORDER for u in compare_user_texts(
                    matched_root / folders[m]["N"].spec.name,
                    root / "control" / er.control_b[m].spec.name, m)]
            plan_differs = tuple(tuple(x) for x in json.loads(
                (root / "design.json").read_text())["key_plan_differs"])
            verdict = M.Verdicts(M.table_route(RUN.fixture_verdicts(root / "route")))
            env = {"validator": "fixture table"}
            mode, run_dates, domains_dir = "fixture", args.run_dates.strip(), root / "domains"
            arms, corpus = arm_rows(folders), corpus_table(folders)
        elif args.dry_run_existing:
            # Existing data only. No row of the matched run is read, so no frozen hash is
            # asked for; the output cannot go to tools/reanalysis/out or to NUMBERS.md.
            if args.numbers:
                raise Halt("--numbers is for live mode only")
            if args.out.resolve() == default_out:
                raise Halt("the dry run needs its own --out (not tools/reanalysis/out)")
            if args.marketplace is None:
                raise Halt("the dry run requires --marketplace (the pddl-copilot checkout)")
            if notes:
                raise Halt("the dry run takes no tripwire audit notes")
            R1.fill_data_args(args)
            design = REGISTERED
            check_design(design, registered=True)
            env = validator_env(args)
            er = load_earlier_live(args)
            control_root = args.control_root or args.results / M.RUN_TAG
            arms, folders_seen, apparatus = {}, {}, {}
            for m in MODEL_ORDER:
                b = er.control_b[m]
                d = control_root / b.spec.name
                apparatus[b.spec.name] = M.check_apparatus(d, b, M.read_settings(d))
                check_summary_run(d)
                arms[m] = {"N": b.rows}
                for arm, name in (("P", "plain"), ("S", "steered")):
                    arms[m][arm] = tuple(r for t in TASKS
                                         for r, _g in er.part_a[m][name][t].values())
                    check_tool_row_caps(arms[m][arm], f"Part A {name} of {m}")
                folders_seen[m] = {"N": b}
            audit = {"note": "dry run: the audit preconditions of section 7 are not run (Part "
                             "A has no audit log); the apparatus checks ran on the rows",
                     "apparatus": apparatus}
            verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
            mode = "dry run on existing data (not the matched run)"
            run_dates = "none: existing data"
            domains_dir, tags, r2_found = args.domains_dir, {}, {}
            corpus = corpus_table(folders_seen)
            plan_differs = KEY_PLAN_DIFFERS
            halt_on_tripwires = False
            stem = "matched_run_dryrun"
        else:
            if args.i_have_frozen != package_sha256():
                raise Halt("refusing to read the matched run: --i-have-frozen does not match "
                           "the package sha256 (freeze first, prereg sections 7 and 9)")
            if args.marketplace is None:
                raise Halt("live mode requires --marketplace (the pddl-copilot checkout)")
            if not (args.run_dates and args.run_dates.strip()):
                raise Halt("--run-dates is required (the continuity checks state the dates of "
                           "both runs)")
            R1.fill_data_args(args)
            design = REGISTERED
            check_design(design, registered=True)
            matched_root = args.matched_root or args.results / RUN_TAG
            tags, r2_found = resolve_tags(matched_root, design, args.r2_models)
            folders = load_matched(matched_root, design, tags)
            audit = audit_matched(matched_root, folders, args.serve_logs,
                                  args.version_checked_by_hand, args.tools_repo_checked_by_hand)
            env = validator_env(args)
            er = load_earlier_live(args)
            control_root = args.control_root or args.results / M.RUN_TAG
            audit["user_texts_vs_control"] = [
                u for m in MODEL_ORDER for u in compare_user_texts(
                    matched_root / folders[m]["N"].spec.name,
                    control_root / er.control_b[m].spec.name, m)]
            plan_differs = KEY_PLAN_DIFFERS
            verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
            mode, run_dates, domains_dir = "live", args.run_dates.strip(), args.domains_dir
            arms, corpus = arm_rows(folders), corpus_table(folders)
        res = analyse(design, arms, er, verdict, mode, run_dates, audit, notes, corpus,
                      domains_dir, plan_differs, halt_on_tripwires)
        res["environment"] = env
        res["run_tags"] = tags
        res["first_run_void"] = r2_found
        try:
            md = render(res)
            js = json.dumps(res, indent=1, sort_keys=True, default=list) + "\n"
        except Exception as e:  # noqa: BLE001 -- any render failure is a named HALT
            raise Halt(f"render failed ({type(e).__name__}: {e}); nothing written") from e
        write_pair(args.out, stem, js, md)
    except (Halt, R1.Halt, RUN.Halt, RC.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}/{stem}.{{json,md}}")
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", NUMBERS_TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


def validator_env(args) -> dict:
    """Section 3: pddl-pyvalidator 0.1.5 and the validator server file of the filed
    re-grade, or the analysis halts (the control's check)."""
    try:
        env = C27.environment(args.marketplace)
    except (OSError, subprocess.CalledProcessError) as e:
        raise Halt(f"--marketplace {args.marketplace}: cannot read the validator "
                   f"environment ({type(e).__name__})") from e
    M.check_validator_env(env, json.loads(args.regrade_json.read_text()).get("environment"))
    return env


if __name__ == "__main__":
    sys.exit(main())
