#!/usr/bin/env python3
"""The Claude run (Haiku 5.5 and Sonnet 5.5, tools against no tools, five tasks): the registered analysis.

    python -m tools.reanalysis.frontier55 --print-package-hash
    python -m tools.reanalysis.frontier55 --fixture tests/fixtures/frontier55 --out OUT
    python -m tools.reanalysis.frontier55 --root /abs/results/frontier55 \\
        --gt-cache /abs/results/derived/gt_cache.json \\
        --plan-verdicts /abs/results/delivered-rerun-secondary/plan_verdicts.json \\
        --marketplace /abs/pddl-copilot --out OUT --i-have-frozen <package hash>

Spec: development/reference/frontier55_prereg.md (sections 2.5, 2.6, 3, 4, 5, 6, 7, 8). The
clause-by-clause map from the spec to this file is
development/reference/frontier55_traceability.md.

Two models, two arms per model (no tools; tools offered), five tasks, wordings v11 to v13.
One folder per model and arm, `<model>_<arm>`, holding `trials.jsonl` (the harness's row
shape) and `trial_meta.jsonl` (the sidecar: one line per trial).

This file imports the frozen code and edits none of it. Every row is read through the
frozen loader of the delivered rerun (`tools.delivered_rerun.schema.parse_row`) with the
model name swapped for an open model's, as section 2.6 says. Solve and simulate are graded
by the matched run's registered grade (`matched_run.grade_trials`, called unchanged); the
three validation tasks by the rerun's frozen grade (`tools.delivered_rerun.grade.grade`).
The sidecar is read by one typed reader of this file (`parse_meta`), which halts on a
missing key, an extra key or an unknown value. The runner (`tools/frontier55/`) is not
imported: its row and sidecar shapes are restated here and tests/test_frontier55_analysis.py
checks them against rows the runner's own functions build.

Modes:
  --print-package-hash   sha256 over this script and every repo file it imports.
  live (default)         reads the run only with --i-have-frozen <that hash>.
  --fixture DIR          the same pipeline on the synthetic fixture (small design,
                         injected validator verdicts, no results/ and no validator).

Order (live and fixture): registered constants -> the frozen-hash gate -> pinned inputs
and the validator environment -> the four folders through the typed loaders (run manifest,
sidecar, rows, row against sidecar, completeness, duplicate keys, storage cuts, the batch
record) -> the same trials in both arms (live: the harness's own trial list) -> validator
route check -> per model, the three rules that send both arms back to be run again (VOID,
failed batch items, the later-date share) -> grades -> RQ1 rates and contrasts -> verdict
errors -> RQ2 and RQ3 -> descriptive counts -> tripwires -> JSON and markdown. A fault
exits 2 and writes nothing. A model that one of the three rules sends back is printed as
"not analysed: <rule>" and is in no table; the other model's readout goes on. A model
whose two arms were run again in new folders is read from them (--rerun-root MODEL=PATH,
--rerun-suffix MODEL=SUFFIX); its first attempt is counted and not graded.

Nothing is pooled over models or tasks, and no number of an open model is read into the
output or compared with these rows.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pddl_eval import control_prompts as CP
from pddl_eval.chat import MAX_TOOL_LOOPS
from pddl_eval.domains import load_domains
from pddl_eval.prompts import ACTIVE_PROMPT_VARIANTS
from pddl_eval.runner import DEFAULT_NUM_PREDICT, RESPONSE_SNAPSHOT_LEN, build_jobs, build_messages
from pddl_eval.scoring import strip_leaked_channel_prefix
from tools import _run_manifest as RM
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.delivered_rerun import stats as ST
from tools.e2e_regrade import truth_for
from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash
from tools.reanalysis import control_prompt_fix as M
from tools.reanalysis import iss027_common as C27
from tools.reanalysis import matched_run as MR
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq23_metrics as R23
from tools.reanalysis.gen_common import begin_marker, end_marker, md_table, write_numbers

REPO = Path(__file__).resolve().parents[2]
SCRIPT = "tools/reanalysis/frontier55.py"
REGISTRATION = "development/reference/frontier55_prereg.md"
NUMBERS_TAG = "FRONTIER55"
FIXTURE_MARKER = "SYNTHETIC_FIXTURE"
STEM = "frontier55"

# Every repo file this script imports, directly or through the modules it imports
# (sorted). Part of the freeze: an edit to any of them changes the package hash, so
# --i-have-frozen refuses until the change is declared. tests/test_frontier55_analysis.py
# checks this list covers sys.modules. It is the matched run's list and the matched run's
# script; this file imports nothing else from the repo.
DEPENDENCIES = tuple(sorted(MR.DEPENDENCIES + (MR.SCRIPT,)))

Halt = M.Halt
_check = M._check            # raises RegisteredCheckFailed; `python -O` cannot strip it


class SidecarError(S.SchemaError):
    """A sidecar line does not have the shape the runner writes."""


class NotAnalysed(Exception):
    """A registered rule says both arms of one model are run again together. That model is
    not analysed and appears in no table; the readout of the other model goes on."""

    def __init__(self, model: str, rule: str, detail: str):
        super().__init__(f"{model}: not analysed: {rule}: {detail}")
        self.model, self.rule, self.detail = model, rule, detail


# ------------------------------------------------------------------ registered constants
# prereg section 2.1: models, tasks, arms, size.
RUN_NAME = "frontier55"
MODELS: tuple[str, ...] = ("claude-haiku-5-5", "claude-sonnet-5-5")
ARMS: tuple[str, ...] = ("no-tools", "tools")
TASKS: tuple[str, ...] = ("solve", "validate_domain", "validate_problem", "validate_plan",
                          "simulate")
WORDINGS: tuple[int, ...] = (11, 12, 13)
PER_TASK = {"solve": 300, "validate_domain": 360, "validate_problem": 600,
            "validate_plan": 3_000, "simulate": 300}
N_FOLDER = 4_560
TOTAL_TRIALS = 18_240
K_DOMAINS = 20
# section 2.2: sha256 (utf-8) of the ten system texts.
SYSTEM_SHA256 = {
    "no-tools": {
        "solve": "3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588",
        "simulate": "7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9",
        "validate_domain": "ab1ffd2abc5e6deab5f37668366b09be3e78d9060646e1aac8ec944fd64d0c36",
        "validate_problem": "f8bea04b4d9e1aac588db14775254f8ef1f77465d1b1f7ec3705441488b9f201",
        "validate_plan": "dcbd1189e28a7f5ace9bcdba92236e6945bd71c9b8b9feed349ceeec09c5c538",
    },
    "tools": {
        "solve": "9b179ca12c2cd2220b46c5478bc637f6dd47356a2f81a4795d3541ecdf6dbb2c",
        "simulate": "ebf8e7fe9d55ab56b9d2d4ba02be4f2b7770fe1b9fdd4d77bba790a68a0d0ac6",
        "validate_domain": "2351f7b2257621ca0155af5206a4304ba7bef79caf974712ac2563101dda839d",
        "validate_problem": "fa18dc28613de2ae12a75efca36bd2aaeb3950fd6f6b6cf7d176295a6a88c54e",
        "validate_plan": "dae2e397c4fc933163608debcab8a6004c170db9f1242ea53b1953909a616f0f",
    },
}
GT_CACHE_SHA256 = "77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e"
# section 2.3: request settings, tools, output caps, round trips.
SETTINGS = {
    "claude-haiku-5-5": {"thinking": {"type": "disabled"}, "effort": "medium"},
    "claude-sonnet-5-5": {"thinking": {"type": "between_tools"}, "effort": "high"},
}
MAY_THINK: tuple[tuple[str, str], ...] = (("claude-sonnet-5-5", "tools"),)   # section 3 item 2
OUTPUT_CAP = {"solve": 8_192, "validate_domain": 6_144, "validate_problem": 6_144,
              "validate_plan": 6_144, "simulate": 6_144}
MAX_ROUND_TRIPS = 10
TOOLS_COMMIT = "5e4f9c0"
TOOLS_SHA256 = "dd14507890d38a8a3c581971a699037b39a3a0bd9374d5801072fb58b9b14400"   # the tool list
PYVALIDATOR = "0.1.5"
API_HOST = "api.anthropic.com"
# section 2.4: the two routes.
TRANSPORT = {"no-tools": "batch", "tools": "live"}
# section 2.6: storage; the loader's model-name swap.
STORAGE_CAP = 65_536
LOADER_TAG = "gemma4_26b-a4b"       # the open model whose name a row carries through the loader
# section 4: which registered grade a task gets.
MATCHED_GRADE_TASKS: tuple[str, ...] = ("solve", "simulate")
RERUN_GRADE_TASKS: tuple[str, ...] = ("validate_domain", "validate_problem", "validate_plan")
# section 5: contrasts and statistics.
N_CONTRASTS = 10
LEVEL = 0.95
B_BOOT = 10_000
SEED = 20261002
HOLM_FAMILY = 5
HOLM_ALPHA = 0.05
LABELS: tuple[str, ...] = ("tools ahead", "no tools ahead", "no difference shown")
NOT_AFTER_HOLM = " (not after Holm)"
RQ2_CLASSES: tuple[str, ...] = ("none", "right_only", "right_plus", "other_only")
# section 6: the same-day rule and the failed batch items. section 7: VOID.
LATER_FRAC = 0.05
BATCH_RETRY_FRAC = 0.01
BATCH_COUNT_KEYS: tuple[str, ...] = ("processing", "succeeded", "errored", "canceled", "expired")
VOID_FRAC = 0.01
# readout-time tripwires (freeze protocol; not registration clauses).
UNREAD_FRAC = 0.05
REFUSAL_TRIPWIRE_FRAC = 0.10

# The sidecar, as tools/frontier55/runner.py writes it (make_meta, turn_record,
# call_messages, batch_grade). Restated here; the tests compare with the runner's output.
OUTCOMES: tuple[str, ...] = ("answer", "loop_exhausted", "overflow", "refusal", "pause_turn",
                             "unknown_stop")
ERROR_OUTCOMES: tuple[str, ...] = ("refusal", "pause_turn", "unknown_stop")
STOP_END, STOP_MAX, STOP_TOOL = "end_turn", "max_tokens", "tool_use"
STOP_REFUSAL, STOP_PAUSE, STOP_SEQ = "refusal", "pause_turn", "stop_sequence"
STOP_WINDOW = "model_context_window_exceeded"
KNOWN_STOPS = frozenset({STOP_END, STOP_MAX, STOP_TOOL, STOP_REFUSAL, STOP_PAUSE, STOP_SEQ,
                         STOP_WINDOW})
DONE_OF_STOP = {STOP_END: "stop", STOP_SEQ: "stop", STOP_MAX: "length"}
META_KEYS = frozenset({
    "key", "custom_id", "run", "arm", "transport", "model_requested", "model_ids_returned",
    "anthropic_version_sent", "sdk_version", "settings", "batch_id", "request_ids", "n_turns",
    "outcome", "stop_reason", "stop_details", "overflow_error", "storage_cut", "answer_chars",
    "full_answer_if_cut", "tool_results", "turns", "written_at_utc"})
META_BATCH_KEYS = META_KEYS | {"batch_created_at", "batch_ended_at"}
TURN_KEYS = frozenset({
    "turn", "request", "requested_at_utc", "received_at_utc", "request_id",
    "anthropic_version_sent", "message_id", "model", "stop_reason", "stop_details", "usage",
    "content"})
TURN_LIVE_KEYS = TURN_KEYS | {"request_body_sha256", "request_host",
                              "thinking_blocks_in_previous_response",
                              "thinking_blocks_passed_back"}
TOOL_RESULT_KEYS = frozenset({"turn", "tool_use_id", "name", "is_error"})
SETTINGS_KEYS = frozenset({"thinking", "effort", "max_tokens", "system_sha256"})
TOOL_ERROR_PREFIX = "Tool error:"

# Error rows (section 3 item 6, section 7), by the row's error text.
REFUSAL, PAUSE, UNKNOWN_STOP, SCORING_ERROR = "refusal", "pause", "unknown stop", "scoring error"
ERROR_KINDS: tuple[str, ...] = (REFUSAL, PAUSE, UNKNOWN_STOP, SCORING_ERROR)
# The error rows section 3 item 6 names: they hold no tool calls and no tokens.
NAMED_ERROR_KINDS: tuple[str, ...] = (REFUSAL, PAUSE, UNKNOWN_STOP)
# Kinds that can count toward VOID (never a refusal). A scoring-error row counts only where
# the rerun's `is_exception` holds: `counts_toward_void`.
VOID_KINDS: tuple[str, ...] = (PAUSE, UNKNOWN_STOP, SCORING_ERROR)
OUTCOME_OF_KIND = {REFUSAL: "refusal", PAUSE: "pause_turn", UNKNOWN_STOP: "unknown_stop"}
THINK_OVERFLOW = "think_overflow"     # section 3 item 4: a label the open rows never carry
# How a trial ended (section 5, descriptive). `E_CAP_EMPTY` is the label of section 3
# item 4: a row the harness labelled `think_overflow` is counted here and nowhere else.
E_ANSWER, E_EMPTY = "answer", "empty answer"
E_CAP, E_CAP_EMPTY = "stopped at the cap with an answer", "stopped at the cap with no answer"
E_LOOP, E_NO_ROOM = "loop exhausted", "refused for length (no room)"
E_REFUSAL, E_ERROR = "refusal", "other error row"
ENDINGS: tuple[str, ...] = (E_ANSWER, E_EMPTY, E_CAP, E_CAP_EMPTY, E_LOOP, E_NO_ROOM, E_REFUSAL,
                            E_ERROR)

ARM_WORDS = {"no-tools": "no tools", "tools": "tools"}
WRONG_READINGS: tuple[str, ...] = (
    "\"the unaided model is as good as the tools\" from an interval that includes 0",
    "any ranking of a Claude model against an open model",
    "a pooled figure over the two models",
    "a comparison of this run's rates with the old Claude runs as if they were the same "
    "experiment")


@dataclass(frozen=True)
class Design:
    """Size constants (live = REGISTERED; the fixture carries its own)."""
    name: str
    per_task: dict          # rows per task in a folder
    n_folder: int           # rows per folder (one model, one arm)
    per_wording: int        # rows per wording in a folder
    k_domains: int          # domain clusters


REGISTERED = Design("registered", per_task=dict(PER_TASK), n_folder=N_FOLDER, per_wording=1_520,
                    k_domains=K_DOMAINS)


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def system_text(arm: str, task: str, wording: int = 11) -> str:
    """The system text a folder sends on a task (section 2.2), from the harness: the
    with-tools text of Part A; the registered no-tools text on the validation tasks; the
    format-stated text of the control's cell B on no-tools solve and simulate."""
    msgs = build_messages(task, "(d)", "(p)", wording, arm == "tools", {"plan": ["(a)"]},
                          prompt_style=C.STYLE_A)
    if arm == "no-tools" and task in CP.CONTROL_TASKS:
        msgs, _ = CP.swap_system(msgs, "format-stated")
    _check(msgs[0]["role"] == "system", "build_messages puts the system text first")
    return msgs[0]["content"]


def check_constants() -> None:
    """Gate 2: every quantity the registration names, as a raised check. Reads the module
    globals at call time, so a test can flip one and see it fire."""
    g = globals()
    MR.check_constants()
    _check(g["RUN_NAME"] == "frontier55", "run name")
    _check(g["MODELS"] == ("claude-haiku-5-5", "claude-sonnet-5-5"), "the two models")
    _check(len(g["MODELS"]) == 2, "2 models")
    _check(g["ARMS"] == ("no-tools", "tools") and len(g["ARMS"]) == 2, "2 arms")
    _check(g["TASKS"] == ("solve", "validate_domain", "validate_problem", "validate_plan",
                          "simulate") == C.TASKS == R23.TASKS, "the five tasks")
    _check(g["WORDINGS"] == (11, 12, 13) == C.PLAIN == tuple(ACTIVE_PROMPT_VARIANTS[:3]),
           "wordings v11 to v13, the plain wordings")
    _check(g["PER_TASK"] == {"solve": 300, "validate_domain": 360, "validate_problem": 600,
                             "validate_plan": 3_000, "simulate": 300}, "trials per task")
    _check(g["N_FOLDER"] == 4_560 == sum(g["PER_TASK"].values()) == C.REGISTERED.n_no_tools_cell,
           "4,560 trials per model and arm")
    _check(g["TOTAL_TRIALS"] == 18_240 == len(g["MODELS"]) * len(g["ARMS"]) * g["N_FOLDER"],
           "18,240 trials")
    _check(g["K_DOMAINS"] == 20 == C.REGISTERED.k_domains, "20 domains")
    _check(set(g["SYSTEM_SHA256"]) == set(g["ARMS"]), "system texts of both arms")
    for arm in ARMS:
        _check(set(g["SYSTEM_SHA256"][arm]) == set(TASKS), f"system texts of {arm}, five tasks")
        for t in TASKS:
            want = g["SYSTEM_SHA256"][arm][t]
            _check(M._HEX64.match(want) is not None, f"sha256 literal {arm}/{t}")
            for v in g["WORDINGS"]:
                _check(_text_sha(system_text(arm, t, v)) == want,
                       f"the harness sends the registered system text on {arm}/{t} v{v}")
    _check(len({d for arm in ARMS for d in g["SYSTEM_SHA256"][arm].values()}) == 10,
           "ten distinct system texts")
    for t in MR.TASKS:
        _check(g["SYSTEM_SHA256"]["no-tools"][t] == MR.N_SYSTEM_SHA256[t]
               == CP.SYSTEM_TEXT_SHA256["format-stated"][t],
               f"no-tools {t}: the format-stated text of the control's cell B")
        _check(g["SYSTEM_SHA256"]["tools"][t] == MR.TOOLS_SYSTEM_SHA256[t],
               f"tools {t}: the with-tools text of the matched run")
    _check(g["GT_CACHE_SHA256"]
           == "77d4184ed872dd4bd7a22747c2e716eb74b86edc94420e47c92daf1684d04c7e",
           "sha256 of the pinned ground-truth cache")
    _check(g["SETTINGS"] == {
        "claude-haiku-5-5": {"thinking": {"type": "disabled"}, "effort": "medium"},
        "claude-sonnet-5-5": {"thinking": {"type": "between_tools"}, "effort": "high"}},
        "thinking and effort of each model")
    _check(set(g["SETTINGS"]) == set(g["MODELS"]), "settings for both models")
    _check(g["MAY_THINK"] == (("claude-sonnet-5-5", "tools"),),
           "only Sonnet's tool arm may carry notes")
    _check(g["OUTPUT_CAP"] == {"solve": 8_192, "validate_domain": 6_144,
                               "validate_problem": 6_144, "validate_plan": 6_144,
                               "simulate": 6_144}, "output caps")
    _check(all(g["OUTPUT_CAP"][t] == DEFAULT_NUM_PREDICT[t] for t in TASKS),
           "output caps are the harness's DEFAULT_NUM_PREDICT")
    _check(all(g["OUTPUT_CAP"][t] == MR.OUTPUT_CAP[t] for t in MR.TASKS),
           "output caps of solve and simulate are the matched run's")
    _check(g["MAX_ROUND_TRIPS"] == 10 == MAX_TOOL_LOOPS, "at most 10 tool round trips")
    _check(g["TOOLS_COMMIT"] == "5e4f9c0" == C.MARKETPLACE_PIN == MR.TOOLS_REPO_COMMIT,
           "tools repo at 5e4f9c0")
    _check(g["TOOLS_SHA256"]
           == "dd14507890d38a8a3c581971a699037b39a3a0bd9374d5801072fb58b9b14400",
           "sha256 of the tool list")
    _check(g["PYVALIDATOR"] == "0.1.5" == C27.PYVAL_EXPECTED == MR.PYVALIDATOR == M.PYVALIDATOR,
           "pddl-pyvalidator 0.1.5")
    _check(g["API_HOST"] == "api.anthropic.com", "the provider's address")
    _check(g["TRANSPORT"] == {"no-tools": "batch", "tools": "live"},
           "no tools through the Batch API, tools through live calls")
    _check(g["STORAGE_CAP"] == 65_536 == C.STORAGE_CAP == RESPONSE_SNAPSHOT_LEN == MR.STORAGE_CAP,
           "storage cap 65,536")
    _check(g["LOADER_TAG"] in C.MODEL_IDS, "the loader's model name is an open model's")
    _check(C.THINK == "off" and C.TOOL_FILTER == "all" and C.STYLE_A == "minimal",
           "key tags: thinking off, all tools, the minimal prompt style")
    _check(g["MATCHED_GRADE_TASKS"] == ("solve", "simulate") == MR.TASKS,
           "solve and simulate: the matched run's registered grade")
    _check(g["RERUN_GRADE_TASKS"] == ("validate_domain", "validate_problem", "validate_plan")
           == G.VALIDATE_TASKS, "validation tasks: the rerun's frozen grade")
    _check(set(g["MATCHED_GRADE_TASKS"]) | set(g["RERUN_GRADE_TASKS"]) == set(g["TASKS"])
           and not set(g["MATCHED_GRADE_TASKS"]) & set(g["RERUN_GRADE_TASKS"]),
           "every task has exactly one registered grade")
    _check(MR.REGISTERED_GRADE == "registered", "the matched run's registered grade")
    _check(MR.RERUN_PACKAGE.startswith("822aace9") and MR.RERUN_PACKAGE == R1.FROZEN_SHA,
           "the rerun's frozen package 822aace9")
    _check(g["N_CONTRASTS"] == 10 == len(g["MODELS"]) * len(g["TASKS"]), "10 contrasts")
    _check(g["LEVEL"] == 0.95 == C.CI_ENDPOINT == M.LEVEL, "95% intervals")
    _check(g["B_BOOT"] == 10_000 == C.B_BOOT, "10,000 resamples")
    _check(g["SEED"] == 20261002 == C.SEED, "seed 20261002")
    _check(g["HOLM_FAMILY"] == 5 == len(g["TASKS"]), "Holm across the five tasks of a model")
    _check(g["HOLM_ALPHA"] == 0.05 == C.HOLM_ALPHA == M.HOLM_ALPHA, "Holm alpha 0.05")
    _check(g["LABELS"] == ("tools ahead", "no tools ahead", "no difference shown"),
           "the three labels")
    _check(g["NOT_AFTER_HOLM"] == " (not after Holm)", "the words (not after Holm)")
    for lo, hi, p, want in ((1.0, 2.0, 0.01, "tools ahead"), (-2.0, -1.0, 0.01, "no tools ahead"),
                            (-1.0, 1.0, 0.01, "no difference shown"),
                            (0.0, 2.0, 0.01, "no difference shown"),
                            (1.0, 2.0, 0.05, "tools ahead (not after Holm)"),
                            (-2.0, -1.0, 0.5, "no tools ahead (not after Holm)")):
        _check(M.c4_label({"lo": lo, "hi": hi, "p_holm": p}) == want,
               f"the frozen label rule gives {want!r}")
    _check(g["RQ2_CLASSES"] == ("none", "right_only", "right_plus", "other_only") == R23.CLASSES,
           "the four tool-choice classes of rq23_metrics")
    _check(g["LATER_FRAC"] == 0.05, "later-date rule: more than 5%")
    _check(g["BATCH_RETRY_FRAC"] == 0.01, "failed batch items: more than 1% after the retry batch")
    _check(g["BATCH_COUNT_KEYS"] == ("processing", "succeeded", "errored", "canceled", "expired"),
           "the request counts of a batch")
    _check(g["VOID_FRAC"] == 0.01 == C.EXCEPTION_VOID_FRAC, "VOID above 1%")
    _check(C.EXCEPTION_REASONS == frozenset({"exception", "ollama_parse_error"}),
           "exception reasons of the rerun")
    _check(g["UNREAD_FRAC"] == 0.05 == M.UNREAD_FRAC, "unread final answers: more than 5%")
    _check(g["REFUSAL_TRIPWIRE_FRAC"] == 0.10, "refusal tripwire: more than 10%")
    _check(g["OUTCOMES"] == ("answer", "loop_exhausted", "overflow", "refusal", "pause_turn",
                             "unknown_stop"), "the runner's outcome labels")
    _check(g["ERROR_OUTCOMES"] == ("refusal", "pause_turn", "unknown_stop"),
           "the outcomes stored as error rows")
    _check(g["ERROR_KINDS"] == ("refusal", "pause", "unknown stop", "scoring error")
           and g["VOID_KINDS"] == ("pause", "unknown stop", "scoring error")
           and g["REFUSAL"] == "refusal" and g["REFUSAL"] not in g["VOID_KINDS"],
           "error rows; a refusal does not count toward VOID")
    _check(g["NAMED_ERROR_KINDS"] == ("refusal", "pause", "unknown stop")
           and set(g["NAMED_ERROR_KINDS"]) == set(g["OUTCOME_OF_KIND"]),
           "the error rows of section 3 item 6: a refusal, a pause, an unknown stop")
    _check(g["THINK_OVERFLOW"] == "think_overflow" and "think_overflow" in S.FAILURE_REASONS,
           "the harness's think_overflow label")
    _check(g["E_CAP_EMPTY"] == "stopped at the cap with no answer" and len(set(ENDINGS)) == 8,
           "the endings; think_overflow maps to stopped at the cap with no answer")


def check_design(design: Design, registered: bool) -> None:
    """Size constants. Live mode passes REGISTERED and checks every field."""
    if registered:
        _check(design is REGISTERED, "live mode runs on the REGISTERED design")
        _check(design.per_task == {"solve": 300, "validate_domain": 360, "validate_problem": 600,
                                   "validate_plan": 3_000, "simulate": 300},
               "300 / 360 / 600 / 3,000 / 300 rows per task")
        _check(design.n_folder == 4_560, "4,560 rows per folder")
        _check(design.per_wording == 1_520 == C.REGISTERED.per_variant_a, "1,520 rows per wording")
        _check(design.k_domains == 20, "k = 20 domains")
        _check(design.n_folder * len(MODELS) * len(ARMS) == TOTAL_TRIALS, "18,240 trials")
        _check({t: n // len(WORDINGS) for t, n in design.per_task.items()}
               == C.PER_TASK_VARIANT_REGISTERED, "rows per task and wording are the rerun's")
    _check(set(design.per_task) == set(TASKS), "rows for each of the five tasks")
    _check(sum(design.per_task.values()) == design.n_folder, "rows per folder")
    _check(design.n_folder == design.per_wording * len(WORDINGS), "rows per wording")
    _check(all(n % len(WORDINGS) == 0 and n > 0 for n in design.per_task.values()),
           "every task has the same rows on each wording")


check_constants()


# ------------------------------------------------------------------ package hash
# The construction of `matched_run.package_sha256`, over this script's own file list.
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
def folder_name(model: str, arm: str) -> str:
    return f"{model}_{arm}"


def per_task_wording(design: Design) -> dict[str, int]:
    return {t: design.per_task[t] // len(WORDINGS) for t in TASKS}


def cell_spec(design: Design, model: str, arm: str) -> S.CellSpec:
    """The cell spec of one folder: the rerun's Part C spec (five tasks, v11 to v13) with
    this run's folder and sizes, and `with_tools` set for the tool arm. The loader knows
    only the open models' names, so the spec names one of them (section 2.6)."""
    return dataclasses.replace(
        S.spec_rerun_c(C.REGISTERED, LOADER_TAG), name=folder_name(model, arm),
        with_tools=arm == "tools", tasks=TASKS, variants=WORDINGS, n_rows=design.n_folder,
        per_variant=design.per_wording, per_task_variant=per_task_wording(design),
        k_domains=design.k_domains)


# ------------------------------------------------------------------ typed sidecar reader
@dataclass(frozen=True)
class Turn:
    n: int
    model: str                    # the model id the provider returned
    stop_reason: str | None       # the provider's own word; None only on an unknown stop
    requested: datetime           # UTC
    received: datetime | None     # UTC
    input_tokens: int             # uncached + cache-written + cache-read
    output_tokens: int
    cache_tokens: int
    thinking_tokens: int
    thinking_blocks: int
    other_blocks: tuple[str, ...]     # block types other than text, thinking and tool_use
    tool_uses: tuple[str, ...]        # names of the tools this response asked for
    text: str                         # the text blocks, joined
    version: str | None               # the API version header that was sent
    host: str | None                  # live requests only
    think_seen: int                   # thinking blocks of the previous response
    think_back: int                   # of them, found byte-equal in this request


@dataclass(frozen=True)
class Meta:
    key: tuple                    # the 10-field trial key of the row
    task: str
    outcome: str
    stop_reason: str | None
    turns: tuple[Turn, ...]
    model_ids: tuple[str, ...]
    versions: tuple[str, ...]
    sdk_version: str | None
    batch_id: str | None
    batch_created: datetime | None
    batch_ended: datetime | None
    overflow_error: str
    storage_cut: bool
    answer_chars: int
    full_answer: str | None
    tool_results: tuple[tuple[str, bool], ...]    # (tool name, flagged as an error)


def _need(d: dict, k: str, where: str):
    if k not in d:
        raise SidecarError(f"{where}: missing key {k!r}")
    return d[k]


def _typed(d: dict, k: str, kind, where: str, none_ok: bool = False):
    v = _need(d, k, where)
    if v is None and none_ok:
        return None
    if isinstance(v, bool) != (kind is bool) or not isinstance(v, kind):
        raise SidecarError(f"{where}: {k} must be {kind.__name__}"
                           f"{' or null' if none_ok else ''}, got {type(v).__name__}")
    return v


def _exact(d, expected: frozenset, where: str) -> None:
    if not isinstance(d, dict):
        raise SidecarError(f"{where}: not an object")
    missing, extra = expected - set(d), set(d) - expected
    if missing:
        raise SidecarError(f"{where}: missing key(s) {sorted(missing)}")
    if extra:
        raise SidecarError(f"{where}: unexpected key(s) {sorted(extra)}")


def parse_time(v, where: str) -> datetime:
    """A time of the sidecar as an aware UTC datetime. The runner writes
    `%Y-%m-%dT%H:%M:%S.%fZ`; the times of a batch are the SDK's ISO strings."""
    if not isinstance(v, str):
        raise SidecarError(f"{where}: a time must be a string, got {type(v).__name__}")
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        t = datetime.fromisoformat(v)
    except ValueError as e:
        raise SidecarError(f"{where}: unreadable time {v!r}") from e
    if t.tzinfo is None:
        raise SidecarError(f"{where}: time {v!r} carries no zone")
    return t.astimezone(timezone.utc)


def _sum_keys(obj, words: tuple[str, ...]) -> int:
    """Every integer of a usage block whose field name holds one of `words`, at any depth:
    the runner's rule for thinking and cache token counts (`anthropic_requests._sum_keys`)."""
    total = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                total += _sum_keys(v, words)
            elif isinstance(v, int) and not isinstance(v, bool) and any(w in k for w in words):
                total += v
    elif isinstance(obj, list):
        for v in obj:
            total += _sum_keys(v, words)
    return total


def registered_request(model: str, task: str, arm: str, n_messages: int) -> dict:
    """What the sidecar keeps of a registered request (section 2.3): every field of the
    request except the texts and the tool list, and the list of field names."""
    keys = ["max_tokens", "messages", "model", "output_config", "system", "thinking"]
    if arm == "tools":
        keys.append("tools")
    return {"model": model, "max_tokens": OUTPUT_CAP[task],
            "thinking": dict(SETTINGS[model]["thinking"]),
            "output_config": {"effort": SETTINGS[model]["effort"]}, "param_keys": sorted(keys),
            "has_tools": arm == "tools", "n_messages": n_messages}


def parse_turn(t, n: int, model: str, arm: str, task: str, where: str) -> Turn:
    w = f"{where} turn {n}"
    _exact(t, TURN_LIVE_KEYS if arm == "tools" else TURN_KEYS, w)
    if _typed(t, "turn", int, w) != n:
        raise SidecarError(f"{w}: numbered {t['turn']}")
    # Section 2.3: the request holds the registered settings and nothing else. A turn's
    # request carries the first user message and one assistant and one user message per
    # earlier turn.
    if t["request"] != registered_request(model, task, arm, 2 * n - 1):
        raise SidecarError(f"{w}: the request's settings are not the registered ones "
                           f"(section 2.3): {t['request']!r}")
    returned = _typed(t, "model", str, w)
    if not returned.startswith(model):
        raise SidecarError(f"{w}: the provider returned model id {returned!r}, asked {model!r}")
    stop = _typed(t, "stop_reason", str, w, none_ok=True)
    usage = _need(t, "usage", w)
    if not isinstance(usage, dict):
        raise SidecarError(f"{w}: usage is not an object")
    inp, out = _typed(usage, "input_tokens", int, w), _typed(usage, "output_tokens", int, w)
    for k in ("cache_creation_input_tokens", "cache_read_input_tokens"):
        if k in usage:
            inp += _typed(usage, k, int, w, none_ok=True) or 0
    content = _need(t, "content", w)
    if not isinstance(content, list):
        raise SidecarError(f"{w}: content is not a list")
    text, tool_uses, other, thinking = [], [], [], 0
    for i, b in enumerate(content):
        wb = f"{w} block {i}"
        if not isinstance(b, dict):
            raise SidecarError(f"{wb}: not an object")
        kind = _typed(b, "type", str, wb)
        if kind == "text":
            text.append(_typed(b, "text", str, wb))
        elif kind == "tool_use":
            tool_uses.append(_typed(b, "name", str, wb))
        elif "thinking" in kind:
            thinking += 1
        else:
            other.append(kind)
    version = _typed(t, "anthropic_version_sent", str, w, none_ok=True)
    if arm == "tools":
        host = _typed(t, "request_host", str, w)
        if host != API_HOST:
            raise SidecarError(f"{w}: the request went to {host!r}, registered {API_HOST!r}")
        seen = _typed(t, "thinking_blocks_in_previous_response", int, w)
        back = _typed(t, "thinking_blocks_passed_back", int, w)
        received = parse_time(_need(t, "received_at_utc", w), w)
    else:
        host, seen, back = None, 0, 0
        raw = _need(t, "received_at_utc", w)
        received = None if raw is None else parse_time(raw, w)
    return Turn(n=n, model=returned, stop_reason=stop,
                requested=parse_time(_need(t, "requested_at_utc", w), w), received=received,
                input_tokens=inp, output_tokens=out, cache_tokens=_sum_keys(usage, ("cache",)),
                thinking_tokens=_sum_keys(usage, ("thinking", "reasoning")),
                thinking_blocks=thinking, other_blocks=tuple(other), tool_uses=tuple(tool_uses),
                text="".join(text), version=version, host=host, think_seen=seen, think_back=back)


def parse_meta(obj, model: str, arm: str, where: str) -> Meta:
    """One sidecar line -> Meta, or SidecarError: a missing or extra key, a value of the
    wrong type, an unknown outcome, settings that are not the registered ones, or a
    conversation whose shape section 2.5 does not allow."""
    _exact(obj, META_BATCH_KEYS if arm == "no-tools" else META_KEYS, where)
    key = obj["key"]
    if not isinstance(key, list) or len(key) != S.KEY_LEN \
            or not all(isinstance(x, (str, int)) for x in key):
        raise SidecarError(f"{where}: key must be a {S.KEY_LEN}-list of names")
    task = key[1]
    if task not in TASKS:
        raise SidecarError(f"{where}: unknown task {task!r}")
    if key[0] != model or key[6] is not (arm == "tools") \
            or key[7:] != [C.THINK, C.TOOL_FILTER, C.STYLE_A]:
        raise SidecarError(f"{where}: key {key!r} is not a trial of {model} {arm}")
    for k, want in (("run", RUN_NAME), ("arm", arm), ("transport", TRANSPORT[arm]),
                    ("model_requested", model)):
        if _need(obj, k, where) != want:
            raise SidecarError(f"{where}: {k}={obj[k]!r}, registered {want!r}")
    settings = obj["settings"]
    _exact(settings, SETTINGS_KEYS, f"{where} settings")
    want = {"thinking": SETTINGS[model]["thinking"], "effort": SETTINGS[model]["effort"],
            "max_tokens": OUTPUT_CAP[task], "system_sha256": SYSTEM_SHA256[arm][task]}
    if settings != want:
        raise SidecarError(f"{where}: settings {settings!r} are not the registered {want!r}")
    outcome = _typed(obj, "outcome", str, where)
    if outcome not in OUTCOMES:
        raise SidecarError(f"{where}: unknown outcome {outcome!r}")
    raw_turns = obj["turns"]
    if not isinstance(raw_turns, list) or not raw_turns:
        raise SidecarError(f"{where}: no turn")
    turns = tuple(parse_turn(t, i, model, arm, task, where) for i, t in enumerate(raw_turns, 1))
    if _typed(obj, "n_turns", int, where) != len(turns):
        raise SidecarError(f"{where}: n_turns {obj['n_turns']} with {len(turns)} turns")
    ids = tuple(sorted({t.model for t in turns}))
    if obj["model_ids_returned"] != list(ids):
        raise SidecarError(f"{where}: model_ids_returned {obj['model_ids_returned']!r} is not "
                           f"the ids of its turns {list(ids)!r}")
    versions = tuple(sorted({t.version for t in turns if t.version is not None}))
    if obj["anthropic_version_sent"] != list(versions):
        raise SidecarError(f"{where}: anthropic_version_sent is not that of its turns")
    request_ids = obj["request_ids"]
    if not isinstance(request_ids, list) or len(request_ids) != len(turns):
        raise SidecarError(f"{where}: request_ids does not have one entry per turn")
    stop = _typed(obj, "stop_reason", str, where, none_ok=True)
    tool_results = obj["tool_results"]
    if not isinstance(tool_results, list):
        raise SidecarError(f"{where}: tool_results is not a list")
    results = []
    for i, tr in enumerate(tool_results):
        wt = f"{where} tool_results[{i}]"
        _exact(tr, TOOL_RESULT_KEYS, wt)
        results.append((_typed(tr, "name", str, wt), _typed(tr, "is_error", bool, wt)))
    batch_id = _typed(obj, "batch_id", str, where, none_ok=arm == "tools")
    if arm == "tools" and batch_id is not None:
        raise SidecarError(f"{where}: a live trial with a batch id")
    created = ended = None
    if arm == "no-tools":
        if obj["batch_created_at"] is not None:
            created = parse_time(obj["batch_created_at"], where)
        if obj["batch_ended_at"] is not None:
            ended = parse_time(obj["batch_ended_at"], where)
    parse_time(obj["written_at_utc"], where)
    answer_chars = _typed(obj, "answer_chars", int, where)
    meta = Meta(key=tuple(key), task=task, outcome=outcome, stop_reason=stop, turns=turns,
                model_ids=ids, versions=versions,
                sdk_version=_typed(obj, "sdk_version", str, where, none_ok=True),
                batch_id=batch_id, batch_created=created, batch_ended=ended,
                overflow_error=_typed(obj, "overflow_error", str, where),
                storage_cut=_typed(obj, "storage_cut", bool, where), answer_chars=answer_chars,
                full_answer=_typed(obj, "full_answer_if_cut", str, where, none_ok=True),
                tool_results=tuple(results))
    check_conversation(meta, arm, where)
    return meta


def check_conversation(m: Meta, arm: str, where: str) -> None:
    """Section 2.5: the shape of the conversation behind an outcome."""
    def bad(what: str):
        raise SidecarError(f"{where}: outcome {m.outcome!r}: {what} (section 2.5)")
    last = m.turns[-1]
    if m.stop_reason != last.stop_reason:
        bad(f"stop_reason {m.stop_reason!r} is not the last turn's {last.stop_reason!r}")
    if len(m.turns) > MAX_ROUND_TRIPS:
        bad(f"{len(m.turns)} round trips, at most {MAX_ROUND_TRIPS}")
    if arm == "no-tools" and len(m.turns) != 1:
        bad(f"{len(m.turns)} requests in the no-tools arm")
    if any(t.stop_reason != STOP_TOOL for t in m.turns[:-1]):
        bad("a turn before the last did not ask for a tool")
    if m.overflow_error and m.outcome != "overflow":
        bad("an over-length error text on another outcome")
    if m.outcome == "answer":
        if last.stop_reason not in DONE_OF_STOP:
            bad(f"the last turn stopped with {last.stop_reason!r}")
    elif m.outcome == "refusal":
        if last.stop_reason != STOP_REFUSAL:
            bad(f"the last turn stopped with {last.stop_reason!r}")
    elif m.outcome == "pause_turn":
        if last.stop_reason != STOP_PAUSE:
            bad(f"the last turn stopped with {last.stop_reason!r}")
    elif m.outcome == "loop_exhausted":
        if arm != "tools" or len(m.turns) != MAX_ROUND_TRIPS or last.stop_reason != STOP_TOOL:
            bad(f"not {MAX_ROUND_TRIPS} round trips that all asked for a tool")
    elif m.outcome == "overflow":
        # Only after a tool result, never on the first request (section 2.5).
        by_stop = last.stop_reason == STOP_WINDOW and len(m.turns) >= 2 and not m.overflow_error
        by_error = last.stop_reason == STOP_TOOL and bool(m.overflow_error)
        if arm != "tools" or not (by_stop or by_error):
            bad("not a tool conversation that ran out of the window after a tool result")
    else:  # unknown_stop
        unknown = last.stop_reason not in KNOWN_STOPS
        if not (unknown or (arm == "no-tools" and last.stop_reason == STOP_TOOL)):
            bad(f"the last turn stopped with the known reason {last.stop_reason!r}")
    # Every tool the model asked for was run and its result kept, in order.
    asked = [n for t in m.turns if t.stop_reason == STOP_TOOL for n in t.tool_uses] \
        if arm == "tools" else []
    if [n for n, _ in m.tool_results] != asked:
        bad("the tool results are not those of the tools the model asked for")
    if (m.answer_chars > STORAGE_CAP) is not m.storage_cut \
            or (m.full_answer is not None) is not m.storage_cut:
        bad("storage_cut, answer_chars and full_answer_if_cut disagree")


def read_sidecar(path: Path, model: str, arm: str, name: str) -> tuple[dict, dict]:
    """({trial key: Meta}, counts). A trial that was abandoned after its sidecar line and
    before its row is run again and gets a second line: the last line of a key is the one
    its row belongs to (the runner's own counters read it the same way)."""
    # OPEN: a key with more than one sidecar line. Implemented: the last line is taken,
    # the earlier ones are counted, and the line taken must agree with the row (answer,
    # token and turn counts, tool calls). The other option is to halt on any repeated key.
    metas: dict = {}
    lines = torn = superseded = 0
    with path.open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            lines += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            m = parse_meta(obj, model, arm, f"{name}/trial_meta.jsonl:{lineno}")
            superseded += m.key in metas
            metas[m.key] = m
    return metas, {"lines": lines, "torn": torn, "superseded": superseded}


# ------------------------------------------------------------------ typed row reader
@dataclass(frozen=True)
class Cell:
    model: str
    arm: str
    spec: S.CellSpec
    rows: tuple[S.Row, ...]         # a row cut by storage carries the full answer of the sidecar
    meta: dict                      # {5-field trial key: Meta}
    kinds: dict                     # {5-field trial key: error kind or None}
    storage_cut: tuple              # trial keys cut by storage, graded from the sidecar
    torn_lines: int
    sidecar: dict                   # lines, torn, superseded
    manifest: dict                  # what `check_manifest` returns
    path: str                       # where the folder was read from
    batches: tuple                  # no-tools folder: its batches, in the order they were sent


@dataclass(frozen=True)
class Batch:
    n: int                          # 1 for the first batch of the folder, 2 for the retry, ...
    batch_id: str
    n_requests: int
    counts: dict                    # the provider's request counts when the batch ended


def read_batches(cell_dir: Path, name: str) -> tuple[Batch, ...]:
    """The batches of a no-tools folder, from the `batches.json` the runner keeps: one
    entry per batch in the order sent, with the number of requests and, once the batch has
    ended and its results are stored, the provider's request counts. Halts on a missing
    key, on a batch that was not fetched, and on entries that are not numbered 1, 2, ..."""
    path = cell_dir / "batches.json"
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise Halt(f"{path}: no readable batch record ({type(e).__name__})") from e
    if not isinstance(raw, list) or not raw:
        raise Halt(f"{path}: the batch record lists no batch")
    out = []
    for i, e in enumerate(raw, 1):
        w = f"{name}/batches.json entry {i}"
        if not isinstance(e, dict):
            raise SidecarError(f"{w}: not an object")
        if _typed(e, "n", int, w) != i:
            raise SidecarError(f"{w}: numbered {e['n']}")
        if _typed(e, "fetched", bool, w) is not True:
            raise Halt(f"{w}: a batch whose results were not fetched; the folder is not complete")
        counts = _need(e, "request_counts", w)
        _exact(counts, frozenset(BATCH_COUNT_KEYS), f"{w} request_counts")
        counts = {k: _typed(counts, k, int, w) for k in BATCH_COUNT_KEYS}
        n_requests = _typed(e, "n_requests", int, w)
        if sum(counts.values()) != n_requests or counts["processing"] != 0:
            raise SidecarError(f"{w}: request counts {counts} of an ended batch of "
                               f"{n_requests} requests")
        out.append(Batch(n=i, batch_id=_typed(e, "batch_id", str, w), n_requests=n_requests,
                         counts=counts))
    if len({b.batch_id for b in out}) != len(out):
        raise SidecarError(f"{name}/batches.json: a batch id twice")
    return tuple(out)


def check_manifest(cell_dir: Path, model: str, arm: str, gt_cache: dict) -> dict:
    """Sections 2.1 to 2.3 and 2.6: the settings a folder was collected under, from the
    run_manifest.json the runner wrote before its first request and refuses to resume
    against. Every registered setting it records must have its registered value; a key
    that is missing halts. Returns what the freeze record and the readout quote."""
    path = cell_dir / RM.MANIFEST_NAME
    try:
        m = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise Halt(f"{path}: no readable run manifest ({type(e).__name__})") from e
    if not isinstance(m, dict):
        raise Halt(f"{path}: the run manifest is not an object")
    tools = arm == "tools"
    want = {
        "manifest_version": RM.MANIFEST_VERSION, "run": RUN_NAME, "pilot": False,
        "model": model, "with_tools": tools, "conditions": arm, "tasks": sorted(TASKS),
        "prompt_variants": list(WORDINGS), "snapshot_len": STORAGE_CAP,
        "max_iterations": MAX_ROUND_TRIPS if tools else 1,
        "think": SETTINGS[model]["thinking"]["type"], "effort": SETTINGS[model]["effort"],
        "output_caps": OUTPUT_CAP, "system_sha256": SYSTEM_SHA256[arm],
        "ground_truth": "cached", "ground_truth_sha256": RM.ground_truth_sha256(gt_cache),
        "base_url": f"https://{API_HOST}",
        "tools_pyvalidator": PYVALIDATOR if tools else None,
        "tools_sha256": TOOLS_SHA256 if tools else None,
    }
    for k in (*want, "gt_cache_sha256", "tools_commit", "sdk_version", "runner_sha256"):
        if k not in m:
            raise Halt(f"{path}: the run manifest has no {k!r}")
    for k, v in want.items():
        if m[k] != v:
            raise Halt(f"{path}: {k}={m[k]!r}, registered {v!r}")
    commit = m["tools_commit"]
    if tools and not (isinstance(commit, str) and commit.startswith(TOOLS_COMMIT)):
        raise Halt(f"{path}: tools_commit={commit!r}, registered {TOOLS_COMMIT}")
    if not tools and commit is not None:
        raise Halt(f"{path}: a no-tools folder records a tools commit")
    return {"gt_cache_sha256": m["gt_cache_sha256"], "tools_commit": commit,
            "tools_pyvalidator": m["tools_pyvalidator"], "tools_sha256": m["tools_sha256"],
            "sdk_version": m["sdk_version"], "runner_sha256": m["runner_sha256"]}


def _raw(obj, where: str) -> tuple[str, list, bool]:
    """The three fields read before the frozen loader: the model name (swapped for the
    loader), the key (to find the sidecar line) and the storage flag."""
    if not isinstance(obj, dict) or set(obj) != {"key", "result"}:
        raise S.SchemaError(f"{where}: record is not a {{key, result}} object")
    key, res = obj["key"], obj["result"]
    if not isinstance(key, list) or len(key) != S.KEY_LEN or not isinstance(res, dict) \
            or not all(isinstance(x, (str, int)) for x in key):
        raise S.SchemaError(f"{where}: key must be a {S.KEY_LEN}-list of names and result an "
                            f"object")
    for k in ("model", "response_truncated_by_storage"):
        if k not in res:
            raise S.SchemaError(f"{where}: missing key {k!r}")
    if not isinstance(res["model"], str) or not isinstance(res["response_truncated_by_storage"],
                                                           bool):
        raise S.SchemaError(f"{where}: model must be a string and "
                            f"response_truncated_by_storage a bool")
    return res["model"], key, res["response_truncated_by_storage"]


def error_kind(r: S.Row, where: str) -> str | None:
    """Section 7: an error row is told from a refusal by its error text."""
    if r.infra_failure or r.empty_message_exception:
        raise S.SchemaError(f"{where}: a row shape the runner of this run never writes "
                            f"(infrastructure failure or an exception without a message)")
    if r.scoring_error:
        # OPEN: the harness's online grader raised on this trial (error "scoring error:
        # ..."); the answer and the tool calls are stored. The registration lists a
        # refusal, a pause and an unknown stop as error rows and is silent on this one.
        # Implemented, the reading that follows the open models' rules: wrong under the
        # grade; counted toward VOID only where the rerun's `is_exception` holds (so not a
        # row the harness labelled `loop_exhausted`); classed in RQ2 by its stored tool
        # calls like any other row; never in RQ3's "tool right" set, because its stored
        # grade is wrong. The other reading: an error row like the three named ones
        # (counted toward VOID whatever its label; left out of RQ2 and counted beside).
        return SCORING_ERROR
    if not r.is_exception:
        return None
    if r.error == "stop_reason=refusal":
        return REFUSAL
    if r.error == "stop_reason=pause_turn":
        return PAUSE
    if r.error.startswith("stop_reason="):
        return UNKNOWN_STOP
    raise Halt(f"{where}: an exception row whose error text is neither a stop reason nor a "
               f"scoring error: {r.error[:80]!r}")


def check_row_meta(r: S.Row, m: Meta, raw_cut: bool, where: str) -> tuple[str | None, str | None]:
    """(error kind, the full answer when the row was cut by storage). Halts when the row
    and its sidecar line do not describe the same trial."""
    def bad(what: str):
        raise Halt(f"{where}: the row and its sidecar line disagree: {what}")
    kind = error_kind(r, where)
    t = r.tokens
    if t.ctx_clipped_turns != 0 or t.ctx_clip_last_turn_max_tokens is not None:
        bad("a clipped turn; a request of this run either fits or is rejected (section 2.5)")
    if kind in OUTCOME_OF_KIND:
        if m.outcome != OUTCOME_OF_KIND[kind]:
            bad(f"error text {r.error!r} with sidecar outcome {m.outcome!r}")
        if r.error != f"stop_reason={m.stop_reason}":
            bad(f"error text {r.error!r} with sidecar stop reason {m.stop_reason!r}")
        if raw_cut or m.storage_cut or m.answer_chars != 0:
            bad("an error row with a stored answer")
        return kind, None
    if m.outcome in ERROR_OUTCOMES:
        bad(f"sidecar outcome {m.outcome!r} on a row that is not its error row")
    sums = (len(m.turns), sum(x.input_tokens for x in m.turns),
            sum(x.output_tokens for x in m.turns))
    if (t.turns, t.prompt, t.completion) != sums:
        bad(f"turns and tokens {(t.turns, t.prompt, t.completion)} against the sidecar's {sums}")
    if r.no_room is not (m.outcome == "overflow"):
        bad("the no-room flag and the sidecar's over-length outcome")
    if (r.done_reason == "tool_calls") is not (m.outcome == "loop_exhausted"):
        bad("the loop-exhausted ending")
    if m.outcome == "answer" and r.done_reason != DONE_OF_STOP[m.turns[-1].stop_reason]:
        bad(f"done_reason {r.done_reason!r} against stop reason {m.turns[-1].stop_reason!r}")
    if [c.name for c in r.tool_calls] != [n for n, _ in m.tool_results]:
        bad("the stored tool calls and the sidecar's tool results")
    full = m.turns[-1].text if m.outcome == "answer" else ""
    if m.answer_chars != len(full):
        bad(f"answer_chars {m.answer_chars} against {len(full)} characters of answer text")
    # Section 2.6 and 7, a row cut by storage: the row's flag, the sidecar's flag and the
    # length of the answer the sidecar holds must all say so, and the stored characters
    # must be the first 65,536 of that answer.
    # OPEN: how a row cut by storage is told. Implemented: all three signs must agree
    # (the row's `response_truncated_by_storage`, the sidecar's `storage_cut`, and an
    # answer text in the sidecar's last turn longer than 65,536 characters), and any
    # disagreement halts. The other option is to go by the row's flag alone.
    cut = len(full) > STORAGE_CAP
    if raw_cut is not cut or m.storage_cut is not cut:
        bad("whether the answer was cut by storage")
    if cut and m.full_answer != full:
        bad("full_answer_if_cut is not the answer text of the last turn")
    if r.response != full[:STORAGE_CAP]:
        bad("the stored answer is not the answer text of the sidecar's last turn")
    return kind, (full if cut else None)


def load_row(obj, by_key: dict, spec: S.CellSpec, model: str,
             where: str) -> tuple[S.Row, Meta, str | None, bool]:
    """One trials.jsonl record -> (typed row, its sidecar line, error kind, cut by storage).

    Section 2.6: the row goes through the frozen `schema.parse_row` with the model name
    swapped for an open model's; every other rule of the loader applies unchanged. The
    frozen loader refuses a row cut by storage, so such a row is read with its stored
    65,536 characters and the flag off, checked against its sidecar line, and then given
    the full answer the sidecar holds."""
    row_model, key, raw_cut = _raw(obj, where)
    if row_model != model or key[0] != model:
        raise S.SchemaError(f"{where}: model {row_model!r} (key {key[0]!r}) in the folder "
                            f"of {model}")
    if tuple(key) not in by_key:
        raise Halt(f"{where}: the row has no sidecar line (section 2.6)")
    m = by_key[tuple(key)]
    tag_id = C.MODEL_IDS[LOADER_TAG]
    swapped = {"key": [tag_id] + key[1:],
               "result": {**obj["result"], "model": tag_id,
                          "response_truncated_by_storage": False}}
    row = S.parse_row(swapped, spec, where)
    kind, full = check_row_meta(row, m, raw_cut, where)
    if full is not None:
        row = dataclasses.replace(row, response=full)
    return row, m, kind, full is not None


def read_cell(root: Path, design: Design, model: str, arm: str, gt_cache: dict,
              gt_cache_sha256: str, domains: frozenset | None = None,
              suffix: str = "") -> Cell:
    """One folder: its run manifest, the sidecar through `parse_meta`, every row through the frozen
    `schema.parse_row` (model name swapped, section 2.6), each row against its sidecar
    line, the frozen completeness check and the per-task counts of section 2.1.

    A row cut by storage is refused by the frozen loader. It is read with its stored
    65,536 characters and the flag off, and then carries the full answer of the sidecar,
    from which it is graded (sections 2.6, 4 and 7). Duplicate trial keys halt. A
    half-written line is counted and skipped, as the frozen `load_cell` does; completeness
    then proves every key is present intact."""
    spec = cell_spec(design, model, arm)
    spec = dataclasses.replace(spec, name=spec.name + suffix)
    cell_dir = root / spec.name
    if not cell_dir.is_dir():
        raise S.IncompleteCell(f"folder not found: {cell_dir}")
    files = sorted(p.name for p in cell_dir.glob("trials*.jsonl"))
    if files != ["trials.jsonl"]:
        raise S.SchemaError(f"{cell_dir}: expected exactly trials.jsonl, found {files}")
    if not (cell_dir / "trial_meta.jsonl").is_file():
        raise SidecarError(f"{cell_dir}: no trial_meta.jsonl")
    manifest = check_manifest(cell_dir, model, arm, gt_cache)
    if manifest["gt_cache_sha256"] != gt_cache_sha256:
        raise Halt(f"{cell_dir}: the run used the ground-truth cache "
                   f"{str(manifest['gt_cache_sha256'])[:12]}..., the analysis reads "
                   f"{gt_cache_sha256[:12]}...")
    by_key, counts = read_sidecar(cell_dir / "trial_meta.jsonl", model, arm, spec.name)
    rows: list[S.Row] = []
    meta, kinds, cut_keys = {}, {}, []
    seen: set = set()
    torn = 0
    with (cell_dir / "trials.jsonl").open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            where = f"{spec.name}/trials.jsonl:{lineno}"
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            row, m, kind, was_cut = load_row(obj, by_key, spec, model, where)
            if domains is not None and row.domain not in domains:
                raise Halt(f"{where}: domain {row.domain!r} is not one of the fixture's own "
                           f"(fixture mode reads synthetic rows only)")
            if m.key in seen:
                raise Halt(f"{where}: duplicate trial key {row.trial_key}")
            seen.add(m.key)
            if was_cut:
                cut_keys.append(row.trial_key)
            rows.append(row)
            meta[row.trial_key] = m
            kinds[row.trial_key] = kind
    S._check_completeness(spec, rows)
    per_task = Counter(r.task for r in rows)
    if dict(per_task) != design.per_task:
        raise S.IncompleteCell(f"{spec.name}: rows per task {dict(per_task)}, registered "
                               f"{design.per_task}")
    orphans = set(by_key) - seen
    if orphans:
        raise Halt(f"{spec.name}: {len(orphans)} sidecar line(s) of trials that have no row")
    ids = {i for m in meta.values() for i in m.model_ids}
    if len(ids) != 1:
        raise Halt(f"{spec.name}: the model id the provider returned changes within the "
                   f"folder: {sorted(ids)} (section 6)")
    return Cell(model=model, arm=arm, spec=spec, rows=tuple(rows), meta=meta, kinds=kinds,
                storage_cut=tuple(cut_keys), torn_lines=torn, sidecar=counts,
                manifest=manifest, path=str(cell_dir),
                batches=read_batches(cell_dir, spec.name) if arm == "no-tools" else ())


def counts_toward_void(r: S.Row, kind: str | None) -> bool:
    """Section 7: an error row that is not a refusal. A pause and an unknown stop always;
    a trial on which the harness's grader raised only where the rerun's `is_exception`
    holds (the open models' rule; see the OPEN note in `error_kind`)."""
    return kind in (PAUSE, UNKNOWN_STOP) or (kind == SCORING_ERROR and r.is_exception)


def void_rows(cell: Cell) -> int:
    """Section 7: error rows that are not refusals."""
    return sum(counts_toward_void(r, cell.kinds[r.trial_key]) for r in cell.rows)


def is_void(cell: Cell) -> bool:
    return void_rows(cell) > VOID_FRAC * len(cell.rows)


def void_rule(model: str, cells: dict) -> None:
    """Section 7: a folder is VOID above 1% error rows that are not refusals; both arms of
    that model are then run again together, not analysed."""
    void = [c for c in cells.values() if is_void(c)]
    if void:
        raise NotAnalysed(model, "VOID (section 7)", "; ".join(
            f"{c.spec.name} has {void_rows(c)} error rows that are not refusals of "
            f"{len(c.rows)} (more than {100 * VOID_FRAC:.0f}%)" for c in void)
            + ". Both arms are run again together, in new folders")


def failed_batch_rule(model: str, cell: Cell) -> dict:
    """Section 6, failed batch items: (1) items that come back failed, canceled or expired
    are sent again once, in a second batch; (2) if after that more than 1% of the arm's
    trials are still without a row, or if the first batch expired as a whole, both arms of
    the model are run again. A folder is complete when it is read, so the trials that had
    no row after the second batch are the rows that came from a third or later batch."""
    by_id = {b.batch_id: b for b in cell.batches}
    rows = Counter(m.batch_id for m in cell.meta.values())
    unknown = sorted(set(rows) - set(by_id))
    if unknown:
        raise Halt(f"{cell.spec.name}: rows of batch(es) {unknown} that batches.json does not list")
    for b in cell.batches:
        if rows[b.batch_id] > b.counts["succeeded"]:
            raise Halt(f"{cell.spec.name}: {rows[b.batch_id]} rows of batch {b.batch_id}, which "
                       f"reports {b.counts['succeeded']} succeeded requests")
    first = cell.batches[0]
    late = sum(rows[b.batch_id] for b in cell.batches if b.n >= 3)
    limit = BATCH_RETRY_FRAC * len(cell.rows)
    out = {"model": model, "folder": cell.spec.name,
           "batches": [{"n": b.n, "batch_id": b.batch_id, "requests": b.n_requests,
                        "request_counts": b.counts, "rows": rows[b.batch_id]}
                       for b in cell.batches],
           "rows_from_a_third_or_later_batch": late, "limit": limit,
           "first_batch_expired_as_a_whole": first.counts["expired"] == first.n_requests}
    if out["first_batch_expired_as_a_whole"]:
        raise NotAnalysed(model, "failed batch items (section 6)",
                          f"the first batch of {cell.spec.name} ({first.batch_id}, "
                          f"{first.n_requests} requests) expired as a whole. Both arms are run "
                          f"again together, in new folders")
    if late > limit:
        raise NotAnalysed(model, "failed batch items (section 6)",
                          f"{late} of the {len(cell.rows)} rows of {cell.spec.name} come from a "
                          f"third or later batch, so more than {100 * BATCH_RETRY_FRAC:.0f}% of "
                          f"the arm's trials were without a row after the one retry batch. Both "
                          f"arms are run again together, in new folders")
    return out


def model_rules(model: str, cells: dict) -> dict:
    """The three rules that send both arms of a model back to be run again (VOID, failed
    batch items, the later-date share). Raises NotAnalysed on the first that holds."""
    void_rule(model, cells)
    batches = failed_batch_rule(model, cells["no-tools"])
    return {"batches": batches, "same_day": same_day(model, cells)}


def screen(cells: dict) -> tuple[dict, dict, list[dict]]:
    """(the models that are analysed, their rule records, the models that are not).
    A model a rule sends back is left out of every table; the other model's readout goes
    on. All folders VOID is a guard firing everywhere: a fault to trace, not a result."""
    every = [c for m in cells for c in cells[m].values()]
    if len(every) == len(MODELS) * len(ARMS) and all(is_void(c) for c in every):
        raise Halt("every folder is VOID (section 7). A guard that fires everywhere is a "
                   "fault to trace before any rerun or readout:\n  " + "\n  ".join(
                       f"{c.spec.name} has {void_rows(c)} error rows that are not refusals of "
                       f"{len(c.rows)}" for c in every))
    kept, rules, blocked = {}, {}, []
    for m in cells:
        try:
            rules[m] = model_rules(m, cells[m])
            kept[m] = cells[m]
        except NotAnalysed as e:
            blocked.append({"model": e.model, "rule": e.rule, "detail": e.detail})
    if not kept:
        raise Halt("no model can be analysed:\n  " + "\n  ".join(
            f"{b['model']}: not analysed: {b['rule']}: {b['detail']}" for b in blocked))
    return kept, rules, blocked


def load_run(root: Path, design: Design, gt_cache: dict, gt_cache_sha256: str,
             domains: frozenset | None = None, reruns: dict | None = None) -> dict:
    """{model: {arm: Cell}} for the four folders. `gt_cache_sha256` is the sha256 of the
    ground-truth file the analysis reads; every folder's manifest must name the same.
    `reruns` gives, for a model whose two arms were run again in new folders, the root and
    the folder suffix of those folders; they are read in place of the first attempt's."""
    cells = {}
    for m in MODELS:
        at, suffix = (reruns or {}).get(m, (root, ""))
        cells[m] = {arm: read_cell(at, design, m, arm, gt_cache, gt_cache_sha256, domains,
                                   suffix) for arm in ARMS}
    return cells


def parse_reruns(roots: list[str], suffixes: list[str], root: Path) -> dict:
    """{model: (root, folder suffix)} from --rerun-root MODEL=PATH and --rerun-suffix
    MODEL=SUFFIX: the new folders of a model whose two arms were run again (sections 6
    and 7). A rerun must name other folders than the first attempt's."""
    given: dict = {}
    for what, items in (("root", roots), ("suffix", suffixes)):
        for item in items:
            model, sep, value = item.partition("=")
            if not sep or model not in MODELS or not value:
                raise Halt(f"--rerun-{what} {item!r}: expected MODEL=VALUE with MODEL one of "
                           f"{list(MODELS)}")
            if what in given.setdefault(model, {}):
                raise Halt(f"--rerun-{what} given twice for {model}")
            given[model][what] = value
    out = {}
    for model, g in given.items():
        at = Path(g["root"]) if "root" in g else root
        suffix = g["suffix"] if "suffix" in g else ""
        if at.resolve() == root.resolve() and not suffix:
            raise Halt(f"the rerun of {model} names the folders of its first attempt")
        if "pilot" in at.resolve().name or "pilot" in suffix:
            raise Halt(f"the rerun of {model} names a pilot folder; the pilot is never analysed")
        out[model] = (at, suffix)
    return out


def first_attempt(root: Path, model: str) -> list[dict]:
    """Section 6: "the first attempt is kept and reported". The folders a rerun replaces
    are counted (rows, rows per task, sidecar lines) and nothing in them is graded."""
    out = []
    for arm in ARMS:
        d = root / folder_name(model, arm)
        rec = {"folder": d.name, "found": d.is_dir(), "rows": 0, "half_written_lines": 0,
               "rows_per_task": {}, "sidecar_lines": 0}
        if rec["found"] and (d / "trials.jsonl").is_file():
            per_task: Counter = Counter()
            with (d / "trials.jsonl").open() as fh:
                for lineno, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        rec["half_written_lines"] += 1
                        continue
                    _model, key, _cut = _raw(obj, f"{d.name}/trials.jsonl:{lineno}")
                    per_task[str(key[1])] += 1
            rec["rows"] = sum(per_task.values())
            rec["rows_per_task"] = dict(sorted(per_task.items()))
        if rec["found"] and (d / "trial_meta.jsonl").is_file():
            with (d / "trial_meta.jsonl").open() as fh:
                rec["sidecar_lines"] = sum(1 for line in fh if line.strip())
        out.append(rec)
    return out


def check_same_trials(cells: dict) -> None:
    """Sections 2.1 and 6: the two arms of a model hold the same trials."""
    for m in cells:
        n = {r.trial_key for r in cells[m]["no-tools"].rows}
        t = {r.trial_key for r in cells[m]["tools"].rows}
        if n != t:
            raise Halt(f"{m}: the two arms do not hold the same trials ({len(n - t)} only in "
                       f"the no-tools folder, {len(t - n)} only in the tools folder)")


def registered_grid(domains_dir: Path, gt_cache: dict) -> frozenset:
    """Section 2.1: the trial list of an arm, from the harness's own enumerator
    (`pddl_eval.runner.build_jobs`, called as the runner calls it), wordings v11 to v13.
    Live mode only: it needs the repository's domains and the pinned ground truth."""
    domains = load_domains(domains_dir)
    grids = []
    for arm in ARMS:
        jobs, _ = build_jobs(models=[MODELS[0]], tasks=list(TASKS), domains=domains,
                             ground_truth=gt_cache, num_variants=len(ACTIVE_PROMPT_VARIANTS),
                             conditions=arm, tool_filter=C.TOOL_FILTER, prompt_style=C.STYLE_A,
                             think_tag=C.THINK)
        keys = [(j[1], j[2], j[4], j[10], j[6]) for j in jobs if j[6] in WORDINGS]
        _check(len(keys) == len(set(keys)) == N_FOLDER, f"the {arm} trial list has 4,560 trials")
        _check(dict(Counter(k[0] for k in keys)) == PER_TASK, f"trials per task, {arm}")
        _check(len({k[1] for k in keys}) == K_DOMAINS, f"20 domains, {arm}")
        grids.append(frozenset(keys))
    _check(grids[0] == grids[1], "the harness lists the same trials for both arms")
    return grids[0]


def check_grid(cells: dict, grid: frozenset) -> None:
    for m in cells:
        for arm in ARMS:
            keys = {r.trial_key for r in cells[m][arm].rows}
            if keys != grid:
                raise Halt(f"{cells[m][arm].spec.name}: its trials are not the registered list "
                           f"({len(keys - grid)} not in the list, {len(grid - keys)} missing)")


# ------------------------------------------------------------------ apparatus and the same-day rule
def _dates(times) -> dict[str, int]:
    return dict(sorted(Counter(t.date().isoformat() for t in times).items()))


def same_day(model: str, cells: dict) -> dict:
    """Section 6, the same-day rule: both arms of a model count as the same day when the
    batch was sent and every tool trial was requested on one UTC date. Reported: the date
    the batch was sent and the date it ended, and the tool trials requested on a later
    date. More than 5% of them: both arms of the model are run again together, so the
    model is not analysed. `cells` is {arm: Cell} of one model."""
    # OPEN: how a tool trial is dated. Implemented: the reference date is the earliest date
    # a batch of the no-tools folder was sent, and a tool trial counts as "on a later date"
    # when ANY of its requests has a later UTC date (the larger count). The other option
    # is to date a trial by its first request only.
    n, t = cells["no-tools"], cells["tools"]
    sent = [m.turns[0].requested for m in n.meta.values()]
    ref = min(x.date() for x in sent)
    early = [m for m in t.meta.values() if any(x.requested.date() < ref for x in m.turns)]
    if early:
        # The registration has the batch sent first and the tool arm started after it. A
        # tool request dated before the batch was sent is another fault, not a late trial.
        raise Halt(f"{model}: {len(early)} tool trial(s) hold a request dated before "
                   f"{ref.isoformat()}, the date the batch was sent (section 6 has the batch "
                   f"sent first); this is not the later-date case and is not analysed as one")
    later = [m for m in t.meta.values() if any(x.requested.date() > ref for x in m.turns)]
    share = len(later) / len(t.meta)
    batches = {}
    for m in n.meta.values():
        b = batches.setdefault(m.batch_id, {"trials": 0, "sent": set(), "ended": set()})
        b["trials"] += 1
        b["sent"].add(m.turns[0].requested.date().isoformat())
        b["ended"].add("not recorded" if m.batch_ended is None
                       else m.batch_ended.date().isoformat())
    out = {
        "model": model, "reference_date": ref.isoformat(),
        "batch_sent_dates": _dates(sent),
        "batch_ended_dates": dict(sorted(Counter(
            "not recorded" if m.batch_ended is None else m.batch_ended.date().isoformat()
            for m in n.meta.values()).items())),
        "batches": [{"batch_id": b, "trials": v["trials"], "sent": sorted(v["sent"]),
                     "ended": sorted(v["ended"])} for b, v in sorted(batches.items())],
        "no_tools_trials_sent_on_a_later_date": sum(x.date() > ref for x in sent),
        "tool_trial_first_request_dates": _dates(m.turns[0].requested for m in t.meta.values()),
        "tool_trials": len(t.meta), "tool_trials_on_a_later_date": len(later),
        "share_on_a_later_date": share,
        "same_day": len({x.date() for x in sent}) == 1 and not later,
    }
    if share > LATER_FRAC:
        raise NotAnalysed(model, "the later-date share (section 6)",
                          f"{len(later)} of {len(t.meta)} tool trials were requested on a date "
                          f"later than {ref.isoformat()}, the date the batch was sent (more "
                          f"than {100 * LATER_FRAC:.0f}%). Both arms are run again together")
    return out


def apparatus(cell: Cell) -> dict:
    """What the sidecar shows of how a folder was collected (sections 2.3, 2.5, 3 item 5)."""
    metas = list(cell.meta.values())
    turns = [t for m in metas for t in m.turns]
    seen, back = sum(t.think_seen for t in turns), sum(t.think_back for t in turns)
    if seen != back:
        # Section 2.5: the model's content goes back exactly as it came.
        raise Halt(f"{cell.spec.name}: {seen} notes between tool calls were returned and "
                   f"{back} were found unchanged in the next request (section 2.5)")
    return {
        "folder": cell.spec.name, "path": cell.path, "model": cell.model, "arm": cell.arm,
        "manifest": cell.manifest, "requests": len(turns),
        "model_ids_returned": sorted({i for m in metas for i in m.model_ids}),
        "request_dates_utc": _dates(t.requested for t in turns),
        "api_versions_sent": sorted({v for m in metas for v in m.versions}),
        "sdk_versions": sorted({str(m.sdk_version) for m in metas}),
        "hosts": sorted({t.host for t in turns if t.host is not None}),
        "cache_tokens": sum(t.cache_tokens for t in turns),
        "notes_returned_before_a_next_request": seen, "notes_passed_back_unchanged": back,
        "other_content_blocks": dict(sorted(Counter(
            b for t in turns for b in t.other_blocks).items())),
        "responses_over_the_output_cap": sum(
            t.output_tokens > OUTPUT_CAP[m.task] for m in metas for t in m.turns),
    }


# ------------------------------------------------------------------ the grade (section 4)
@dataclass(frozen=True)
class Trial:
    key: tuple
    task: str
    domain: str
    variant: int
    registered: bool            # section 4: right under the registered grade
    reason: str                 # the frozen grader's reason
    stated: bool | None         # validation tasks: the stated verdict
    truth: bool | None          # validation tasks: the truth
    ending: str                 # one of ENDINGS
    error_kind: str | None      # one of ERROR_KINDS
    read: bool                  # a reader of the registered grade found an answer to grade
    unread: bool                # an answer that ended on its own and no reader read
    invoked: bool               # the trial called a tool
    tool_right: bool            # tool arm, not a named error row: the stored harness grade is right
    storage_cut: bool
    think_overflow: bool        # the harness's label on the row
    scoring_error: bool


def ending_of(r: S.Row, kind: str | None) -> str:
    """How a trial ended. A row the harness labelled `think_overflow` (stopped for
    length, a note present, no answer text) falls under "stopped at the cap with no
    answer" by this rule, the label the same event gets for the open models (section 3
    item 4); `grade_cell` checks it. "Other error row" is a row that counts toward VOID."""
    if kind == REFUSAL:
        return E_REFUSAL
    if counts_toward_void(r, kind):
        return E_ERROR
    if r.no_room:
        return E_NO_ROOM
    if r.done_reason == "tool_calls":
        return E_LOOP
    empty = not strip_leaked_channel_prefix(r.response).strip()
    if r.done_reason == "length":
        return E_CAP_EMPTY if empty else E_CAP
    return E_EMPTY if empty else E_ANSWER


def grade_cell(cell: Cell, verdict: M.Verdicts, gt_cache: dict) -> dict:
    """{trial key: Trial} for one folder.

    Section 4. Solve and simulate: the matched run's registered grade, by calling
    `matched_run.grade_trials` unchanged on the frozen grades of `control_prompt_fix.
    frozen_grades`. The three validation tasks: the rerun's frozen grade (`grade.grade`).
    An error row is wrong whatever it stored. A row cut by storage was given the full
    answer of the sidecar by `read_cell`, so it is graded from that text."""
    pairs = M.frozen_grades(cell.rows, verdict, gt_cache)
    matched = MR.grade_trials([(r, g) for r, g in pairs if r.task in MATCHED_GRADE_TASKS],
                              verdict, gt_cache)
    cut = set(cell.storage_cut)
    out = {}
    for r, g in pairs:
        kind = cell.kinds[r.trial_key]
        ending = ending_of(r, kind)
        if r.task in MATCHED_GRADE_TASKS:
            x = matched[r.trial_key]
            registered, reason, read, unread = x.registered, x.reason, x.read, x.unread
            stated = truth = None
            if ending not in (E_REFUSAL, E_ERROR):
                _check(x.at_cap is (ending in (E_CAP, E_CAP_EMPTY))
                       and x.window_full is r.no_room,
                       f"{r.trial_key}: the ending agrees with the matched run's")
        else:
            _check(r.task in RERUN_GRADE_TASKS, f"{r.task} has a registered grade")
            registered, reason, stated = M.ok_of(g), g.reason, g.verdict
            truth = truth_for({"task": r.task, "problem_name": r.problem,
                               "plan_label": r.plan_label})
            _check(isinstance(truth, bool), f"{r.trial_key}: a true or false ground truth")
            _check(stated is None or isinstance(stated, bool),
                   f"{r.trial_key}: the stated verdict is true, false or absent")
            _check(registered is (stated is not None and stated is truth),
                   f"{r.trial_key}: right exactly when the stated verdict equals the truth")
            read = stated is not None
            unread = reason == "no_verdict_stated" and ending == E_ANSWER
        if kind is not None:
            registered = False            # section 4: error rows are wrong, whatever they stored
        _check(isinstance(registered, bool), f"registered grade of {r.trial_key} is a bool")
        think_overflow = r.failure_reason == THINK_OVERFLOW
        if think_overflow:
            _check(ending == E_CAP_EMPTY and reason == "truncated_empty" and registered is False,
                   f"{r.trial_key}: a think_overflow row is \"stopped at the cap with no "
                   f"answer\" (section 3 item 4)")
        if kind in OUTCOME_OF_KIND:
            _check(reason == "exception", f"{r.trial_key}: the frozen grade of an error row")
        out[r.trial_key] = Trial(
            key=r.trial_key, task=r.task, domain=r.domain, variant=r.variant,
            registered=registered, reason=reason, stated=stated, truth=truth, ending=ending,
            error_kind=kind, read=read, unread=unread, invoked=r.invoked,
            tool_right=(cell.arm == "tools" and kind not in NAMED_ERROR_KINDS
                        and r.success is True),
            storage_cut=r.trial_key in cut, think_overflow=think_overflow,
            scoring_error=r.scoring_error)
    return out


# ------------------------------------------------------------------ validator route and inputs
def check_route_table(verdict: M.Verdicts, stored: dict) -> int:
    """The matched run's section 3, which this run's grade follows word for word: before
    any new plan is validated, the route returns the stored verdict for the rerun's
    plans. Checked on every plan of the stored table (the file the rerun's frozen readout
    used, pinned by sha256); no row of an open model is read."""
    # OPEN: the matched run halts "when the route does not return the stored verdict for
    # the rerun's plans". Implemented: the same halt, on all plans of the stored table
    # (a superset of the plans the matched run checks). The other option is to drop the
    # check, since this registration does not repeat that sentence.
    for (d, p, plan), want in sorted(stored.items()):
        if not isinstance(want, bool):
            raise Halt(f"stored verdict for {d}/{p} is {want!r}, not true or false")
        if verdict(d, p, plan) is not want:
            raise Halt(f"the validator route disagrees with the stored verdict for {d}/{p} "
                       f"({len(plan)} actions)")
    return len(stored)


def file_sha256(path: Path, what: str) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as e:
        raise Halt(f"{what} {path}: cannot be read ({type(e).__name__})") from e


def load_gt_cache(path: Path) -> dict:
    """Section 2.2: the pinned ground-truth cache, or a halt."""
    got = file_sha256(path, "ground-truth cache")
    if got != GT_CACHE_SHA256:
        raise Halt(f"ground-truth cache {path}: sha256 {got[:12]}... is not the pinned "
                   f"{GT_CACHE_SHA256[:12]}...")
    gt = json.loads(Path(path).read_text())
    if canonical_hash(gt) != PREREG_PINNED_HASH:
        raise Halt("ground-truth cache does not match the rerun's pinned canonical hash")
    return gt


def validator_env(args) -> dict:
    """Section 4: pddl-pyvalidator 0.1.5 and the validator server file of the filed
    re-grade, or the analysis halts (the control's check, as in the matched run)."""
    got = file_sha256(args.regrade_json, "--regrade-json")
    if got != MR.INPUT_SHA256["regrade_json"]:
        raise Halt(f"--regrade-json {args.regrade_json}: sha256 {got[:12]}... is not the "
                   f"recorded {MR.INPUT_SHA256['regrade_json'][:12]}...")
    try:
        env = C27.environment(args.marketplace)
    except (OSError, subprocess.CalledProcessError) as e:
        raise Halt(f"--marketplace {args.marketplace}: cannot read the validator "
                   f"environment ({type(e).__name__})") from e
    M.check_validator_env(env, json.loads(args.regrade_json.read_text()).get("environment"))
    return env


def stored_verdicts(path: Path) -> dict:
    got = file_sha256(path, "--plan-verdicts")
    if got != MR.INPUT_SHA256["plan_verdicts"]:
        raise Halt(f"--plan-verdicts {path}: sha256 {got[:12]}... is not the recorded "
                   f"{MR.INPUT_SHA256['plan_verdicts'][:12]}...")
    return {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
            for e in json.loads(Path(path).read_text())}


# ------------------------------------------------------------------ measures (section 5)
def models_of(trials: dict) -> list[str]:
    """The models that are analysed, in the registered order."""
    return [m for m in MODELS if (m, "tools") in trials]


def share(values: list, doms: list, k: int, what: str) -> dict:
    """A share of a subset of trials (RQ2, RQ3), in points. Its 95% interval is the frozen
    domain-cluster bootstrap over the registered k domains, asserted. A subset that does
    not reach every domain gets its share and no interval: an interval over fewer
    clusters is never computed."""
    n, present = len(values), len(set(doms))
    out = {"est": None, "lo": None, "hi": None, "k": present, "n": n, "k_registered": k}
    if n and present == k:
        b = M.boot([float(v) for v in values], list(doms), k, what)
        _check(b.k == k and b.n == n, f"{what}: {k} domains")
        out.update(est=b.est, lo=b.lo, hi=b.hi)
    elif n:
        out["est"] = 100 * sum(bool(v) for v in values) / n
    return out


def share_cell(b: dict) -> str:
    if b["est"] is None:
        return "–"
    if b["lo"] is None:
        return (f"{b['est']:.1f} (no interval: the trials reach {b['k']} of "
                f"{b['k_registered']} domains)")
    return f"{b['est']:.1f} [{b['lo']:.1f}, {b['hi']:.1f}]"


def rq1(design: Design, trials: dict) -> tuple[list[dict], list[dict]]:
    """Section 5, RQ1: the rate right in each arm, and tools minus no tools paired on the
    trial, per model and task; 95% domain-cluster intervals; exact sign-flip p over the
    domains, Holm-adjusted across the five tasks of a model; the three labels."""
    k = design.k_domains
    rates, contrasts = [], []
    models = models_of(trials)
    for m in models:
        fam = []
        for t in TASKS:
            for arm in ARMS:
                vals = list(trials[(m, arm)][t].values())
                rates.append({"model": m, "task": t, "arm": arm,
                              **M.rate(vals, MR.REGISTERED_GRADE, k, f"rate {m}/{t}/{arm}")})
            c = M.paired(trials[(m, "no-tools")][t], trials[(m, "tools")][t],
                         MR.REGISTERED_GRADE, k, f"tools minus no tools {m}/{t}")
            _check(c["n_pairs"] == design.per_task[t] and c["unpaired"] == 0,
                   f"{m}/{t}: {design.per_task[t]} pairs, none unpaired")
            fam.append({"model": m, "task": t, **c})
        adj = ST.holm({e["task"]: e["p"] for e in fam}, HOLM_FAMILY)
        for e in fam:
            e["p_holm"] = adj[e["task"]]
            e["label"] = M.c4_label(e)
            _check(e["label"].replace(NOT_AFTER_HOLM, "") in LABELS,
                   f"{m}/{e['task']}: one of the three labels")
        contrasts += fam
    _check(len(contrasts) == len(TASKS) * len(models)
           and len(rates) == len(contrasts) * len(ARMS), "five contrasts and ten rates per model")
    if len(models) == len(MODELS):
        _check(len(contrasts) == N_CONTRASTS, "10 contrasts")
    return rates, contrasts


def verdict_errors(trials: dict) -> list[dict]:
    """Section 5: on the three validation tasks, in each arm, valid inputs called invalid
    and invalid inputs called valid, with counts (`rq1_metrics.confusion`)."""
    out = []
    for m in models_of(trials):
        for t in RERUN_GRADE_TASKS:
            for arm in ARMS:
                vals = list(trials[(m, arm)][t].values())
                c = R1.confusion([x.truth for x in vals], [x.stated for x in vals])
                _check(c["n_valid"] + c["n_broken"] == len(vals), f"{m}/{t}/{arm}: every trial")
                out.append({
                    "model": m, "task": t, "arm": arm, "n": len(vals),
                    "valid_inputs": c["n_valid"], "valid_called_invalid": c["fn"],
                    "valid_no_verdict": c["valid_none"],
                    "valid_error_rows": sum(x.truth is True and x.ending in (E_REFUSAL, E_ERROR)
                                            for x in vals),
                    "invalid_inputs": c["n_broken"], "invalid_called_valid": c["fp"],
                    "invalid_no_verdict": c["broken_none"],
                    "invalid_error_rows": sum(
                        x.truth is False and x.ending in (E_REFUSAL, E_ERROR) for x in vals)})
    return out


def rq2(design: Design, cells: dict, track: dict) -> list[dict]:
    """Section 5, RQ2: tool choice in the tool arm, the four classes of
    `rq23_metrics.classify`, with counts. The error rows section 3 item 6 names (a
    refusal, a pause, an unknown stop) hold no tool calls: they are left out of the
    classes and counted beside them. Every other row is classed by its stored tool calls.
    The self-check of `rq23_metrics.rq2_rows`: the harness rule on the stored calls equals
    the stored `tool_selected`, where the row stores one (a row on which the harness's
    grader raised stores none, as in the matched run's `rq2_cells`)."""
    out = []
    for m in cells:
        cell = cells[m]["tools"]
        for t in TASKS:
            rows = [r for r in cell.rows if r.task == t]
            left_out = Counter(cell.kinds[r.trial_key] for r in rows
                               if cell.kinds[r.trial_key] in NAMED_ERROR_KINDS)
            classed = []
            for r in rows:
                if cell.kinds[r.trial_key] in NAMED_ERROR_KINDS:
                    continue
                try:
                    c = R23.row2(RUN_NAME, m, C.THINK, "plain", r.task, r.domain,
                                 [x.name for x in r.tool_calls], r.tool_selected, track)
                except ValueError as e:
                    raise Halt(f"tool choice: {r.domain} has no track ({e})") from e
                _check(c["cls"] in RQ2_CLASSES, f"a class of rq23_metrics ({c['cls']!r})")
                if r.tool_selected is not None and r.tool_selected is not c["harness_called"]:
                    raise Halt(f"{cell.spec.name} {r.trial_key}: the harness rule on the stored "
                               f"calls differs from the stored tool_selected")
                classed.append(c)
            n = Counter(c["cls"] for c in classed)
            doms = [c["domain"] for c in classed]
            k = design.k_domains
            _check(len(classed) + sum(left_out.values()) == len(rows), f"{m}/{t}: every trial")
            out.append({
                "model": m, "task": t, "n_trials": len(rows), "n_classed": len(classed),
                "counts": {c: n[c] for c in RQ2_CLASSES},
                "error_rows_left_out": sum(left_out.values()),
                "error_rows_by_kind": {x: left_out[x] for x in NAMED_ERROR_KINDS if left_out[x]},
                "exactly_right": share([c["cls"] == "right_only" for c in classed], doms, k,
                                       f"exactly the right tool {m}/{t}"),
                "right_called": share([c["cls"] in ("right_only", "right_plus")
                                       for c in classed], doms, k, f"the right tool {m}/{t}"),
                "other_planner": sum(c["other_planner"] for c in classed),
                "plan_check_only": sum(c["plan_check_only"] for c in classed)})
    return out


def rq3(design: Design, trials: dict) -> list[dict]:
    """Section 5, RQ3: of the trials where the right tool returned the right result, the
    share whose final answer is wrong under the registered grade. "Tool right" is the
    definition of `rq23_metrics.rq3_rerun`: the stored harness grade of a with-tools row
    is right. The error rows section 3 item 6 names are left out of the "tool right" set
    and counted beside it."""
    # OPEN: section 4 says no reading uses the harness's online grade, and section 4 also
    # gives RQ3 the definitions of rq23_metrics.py, whose "tool right" IS that stored
    # grade on a with-tools row. Implemented: the stored grade (`success is True`), for
    # RQ3's denominator only. The other option is to work out "tool right" again from
    # the stored tool results.
    out = []
    for m in models_of(trials):
        for t in TASKS:
            vals = list(trials[(m, "tools")][t].values())
            tv = [x for x in vals if x.tool_right]
            lost = [x.registered is False for x in tv]
            out.append({
                "model": m, "task": t, "n_trials": len(vals), "n_tool_right": len(tv),
                "n_answer_wrong": sum(lost),
                "answer_wrong": share(lost, [x.domain for x in tv], design.k_domains,
                                      f"tool right, answer wrong {m}/{t}"),
                "why": dict(sorted(Counter(x.ending if x.ending != E_ANSWER else x.reason
                                           for x in tv if x.registered is False).items())),
                "error_rows_left_out": sum(x.error_kind in NAMED_ERROR_KINDS for x in vals)})
        _check(all(x.tool_right is False for t in TASKS
                   for x in trials[(m, "no-tools")][t].values()),
               f"{m}: no no-tools row is in the tool-right set")
    return out


def descriptive(cells: dict, trials: dict) -> list[dict]:
    """Section 5, descriptive, with counts, per model, arm and task."""
    out = []
    for m in cells:
        for arm in ARMS:
            cell = cells[m][arm]
            for t in TASKS:
                vals = list(trials[(m, arm)][t].values())
                metas = [cell.meta[x.key] for x in vals]
                ends = Counter(x.ending for x in vals)
                kinds = Counter(x.error_kind for x in vals if x.ending in (E_REFUSAL, E_ERROR))
                turns = [len(mm.turns) for mm in metas]
                tin = [sum(u.input_tokens for u in mm.turns) for mm in metas]
                tout = [sum(u.output_tokens for u in mm.turns) for mm in metas]
                notes = [sum(u.thinking_blocks for u in mm.turns) for mm in metas]
                think = sum(u.thinking_tokens for mm in metas for u in mm.turns)
                calls = [(name, flagged) for mm in metas for name, flagged in mm.tool_results]
                rows = [r for r in cell.rows if r.task == t]
                out.append({
                    "model": m, "arm": arm, "task": t, "n": len(vals),
                    "right_by_wording": {str(v): {
                        "right": sum(x.registered for x in vals if x.variant == v),
                        "n": sum(x.variant == v for x in vals)} for v in WORDINGS},
                    "endings": {e: ends[e] for e in ENDINGS},
                    "stopped_at_the_output_cap": ends[E_CAP] + ends[E_CAP_EMPTY],
                    "stopped_at_the_cap_with_no_answer": ends[E_CAP_EMPTY],
                    "labelled_think_overflow_by_the_harness": sum(x.think_overflow for x in vals),
                    "loop_exhausted": ends[E_LOOP],
                    "refused_for_length": ends[E_NO_ROOM],
                    "refusals": kinds[REFUSAL],
                    "other_error_rows": {k: kinds[k] for k in VOID_KINDS},
                    "scoring_error_rows": sum(x.scoring_error for x in vals),
                    "cut_by_storage": sum(x.storage_cut for x in vals),
                    "turns_mean": sum(turns) / len(turns), "turns_max": max(turns),
                    "turns_histogram": {str(k): v for k, v in sorted(Counter(turns).items())},
                    "input_tokens_mean": sum(tin) / len(tin), "input_tokens_total": sum(tin),
                    "output_tokens_mean": sum(tout) / len(tout), "output_tokens_total": sum(tout),
                    "thinking_tokens_total": think,
                    "thinking_blocks": sum(notes), "trials_with_a_note": sum(n > 0 for n in notes),
                    "tool_calls": len(calls),
                    "tool_calls_flagged_as_errors": sum(flagged for _n, flagged in calls),
                    "tool_results_that_are_the_error_text": sum(
                        c.result.startswith(TOOL_ERROR_PREFIX) for r in rows for c in r.tool_calls),
                    "trials_with_a_tool_call": sum(bool(mm.tool_results) for mm in metas),
                    "rows_with_a_stored_tool_call": sum(x.invoked for x in vals),
                    "unread_final_answers": sum(x.unread for x in vals),
                    "read": sum(x.read for x in vals),
                    "wrong_by_reason": dict(sorted(Counter(
                        x.reason for x in vals if x.registered is False).items()))})
    return out


def refusal_table(desc: list[dict]) -> list[dict]:
    """Section 3 item 6 and section 7: refusals per model, arm and task."""
    return [{"model": d["model"], "arm": d["arm"], "task": d["task"], "n": d["n"],
             "refusals": d["refusals"]} for d in desc]


def storage_table(cells: dict, trials: dict) -> list[dict]:
    """Sections 4 and 7, the storage rule: every row cut by storage, reported."""
    out = []
    for m in cells:
        for arm in ARMS:
            cell = cells[m][arm]
            for key in cell.storage_cut:
                x = trials[(m, arm)][key[0]][key]
                out.append({"model": m, "arm": arm, "task": key[0], "domain": key[1],
                            "problem": key[2], "plan_label": key[3], "wording": key[4],
                            "answer_chars": cell.meta[key].answer_chars,
                            "graded_from": "the full answer in the sidecar",
                            "right": x.registered})
    return out


# ------------------------------------------------------------------ tripwires
def tripwires(design: Design, rates: list, desc: list, cells_app: list) -> dict:
    """Readout-time tripwires (freeze protocol): degenerate outputs halt the readout
    until each is audited and the audit is written down."""
    # OPEN: the registration names no tripwire; these nine are this analysis's own, in
    # the spirit of the matched run's. Implemented: T1 the same count of right answers in
    # all four folders on a task (not evaluated when one model is not analysed: two arms
    # of one model with the same count is no sign of a fault); T2 a cell where the grader
    # reads no answer; T3 a tool-arm cell where no trial called a tool; T4 more than 5% of a
    # cell's final answers
    # that no reader read (both arms, all five tasks); T5 more than 10% refusals in a cell;
    # T6 thinking where the registration has none; T7 a response over its output cap; T8
    # notes with no thinking-token count; T9 the two arms of a model answered by different
    # model ids. The options are other thresholds or fewer wires.
    fired = {}
    by_rate = {(e["model"], e["task"], e["arm"]): e for e in rates}
    models = [m for m in MODELS if any(e["model"] == m for e in rates)]
    for t in TASKS if len(models) == len(MODELS) else ():
        ks = {by_rate[(m, t, arm)]["right"] for m in models for arm in ARMS}
        if len(ks) == 1:
            fired[f"T1:{t}"] = (f"the count of right answers on {t} is the same in all four "
                                f"folders ({ks.pop()} of {design.per_task[t]})")
    for d in desc:
        m, arm, t, n = d["model"], d["arm"], d["task"], d["n"]
        if d["read"] == 0:
            fired[f"T2:{m}:{arm}:{t}"] = f"{m} {arm}: the grader reads no answer at all on {t}"
        if arm == "tools" and d["trials_with_a_tool_call"] == 0:
            fired[f"T3:{m}:{t}"] = f"{m}, tools arm, {t}: no trial called a tool"
        if d["unread_final_answers"] > UNREAD_FRAC * n:
            fired[f"T4:{m}:{arm}:{t}"] = (
                f"{m} {arm}, {t}: {d['unread_final_answers']} final answers of {n} that no "
                f"reader read (more than {UNREAD_FRAC * n:g})")
        if d["refusals"] > REFUSAL_TRIPWIRE_FRAC * n:
            fired[f"T5:{m}:{arm}:{t}"] = (f"{m} {arm}, {t}: {d['refusals']} refusals of {n} "
                                          f"(more than {REFUSAL_TRIPWIRE_FRAC * n:g})")
    for m in models:
        for arm in ARMS:
            ds = [d for d in desc if (d["model"], d["arm"]) == (m, arm)]
            tokens = sum(d["thinking_tokens_total"] for d in ds)
            blocks = sum(d["thinking_blocks"] for d in ds)
            if (m, arm) not in MAY_THINK and (tokens or blocks):
                fired[f"T6:{m}:{arm}"] = (f"{m} {arm}: {blocks} thinking blocks and {tokens} "
                                          f"thinking tokens where the registration has none")
            if (m, arm) in MAY_THINK and blocks and not tokens:
                fired[f"T8:{m}:{arm}"] = (
                    f"{m} {arm}: {blocks} notes between tool calls were returned and no usage "
                    f"block reports a thinking-token count. If the provider does not report "
                    f"thinking tokens separately, this fires by design. The audit must "
                    f"establish three things from the sidecar: that the notes are present, "
                    f"that no usage field of any turn counts them apart, and so that the "
                    f"notes' tokens are inside the output tokens. The count of section 5 is "
                    f"then reported as \"not separable\", with the number of notes")
        ids = {a["arm"]: a["model_ids_returned"] for a in cells_app if a["model"] == m}
        if len(ids) == len(ARMS) and all(len(v) == 1 for v in ids.values()) \
                and len({v[0] for v in ids.values()}) > 1:
            fired[f"T9:{m}"] = (f"{m}: the two arms were answered by different model ids ("
                                + ", ".join(f"{arm}: {ids[arm][0]}" for arm in ARMS)
                                + "); the contrast of this model would compare two models")
    for a in cells_app:
        if a["responses_over_the_output_cap"]:
            fired[f"T7:{a['model']}:{a['arm']}"] = (
                f"{a['folder']}: {a['responses_over_the_output_cap']} responses report more "
                f"output tokens than the cap of their request")
    return fired


# ------------------------------------------------------------------ analysis
def analyse(design: Design, cells: dict, verdict: M.Verdicts, gt_cache: dict, mode: str,
            route_checked: int, track: dict, audit_notes: dict,
            reruns: list[dict] | None = None) -> dict:
    """`cells` is every model's folders as loaded. The same-trials check runs on all of
    them; then `screen` leaves out a model that a registered rule sends back to be run
    again, and the measures are computed for the models that remain."""
    check_same_trials(cells)
    cells, rules, blocked = screen(cells)
    models = list(cells)
    app = [apparatus(cells[m][arm]) for m in models for arm in ARMS]
    trials: dict = {}
    for m in models:
        for arm in ARMS:
            graded = grade_cell(cells[m][arm], verdict, gt_cache)
            trials[(m, arm)] = {t: {q: x for q, x in graded.items() if x.task == t}
                                for t in TASKS}
            for t in TASKS:
                _check(len(trials[(m, arm)][t]) == design.per_task[t],
                       f"{m}/{arm}/{t}: {design.per_task[t]} trials")
    rates, contrasts = rq1(design, trials)
    desc = descriptive(cells, trials)
    fired = tripwires(design, rates, desc, app)
    unaudited = {i: v for i, v in fired.items() if i not in audit_notes}
    if unaudited:
        raise Halt("readout tripwire(s) fired; audit before any readout sentence:\n  "
                   + "\n  ".join(f"{i}: {v}" for i, v in unaudited.items()))
    extra = set(audit_notes) - set(fired)
    if extra:
        raise Halt(f"audit notes for tripwires that did not fire: {sorted(extra)}")
    corpus = []
    for m in models:
        for c in cells[m].values():
            void_kinds = Counter(c.kinds[r.trial_key] for r in c.rows
                                 if counts_toward_void(r, c.kinds[r.trial_key]))
            corpus.append({
                "folder": c.spec.name, "path": c.path, "model": c.model, "arm": c.arm,
                "rows": len(c.rows), "torn_lines": c.torn_lines,
                "sidecar_lines": c.sidecar["lines"], "sidecar_torn_lines": c.sidecar["torn"],
                "sidecar_lines_of_abandoned_tries": c.sidecar["superseded"],
                "refusals": sum(k == REFUSAL for k in c.kinds.values()),
                "error_rows_not_refusals": void_rows(c),
                "error_rows_by_kind": {k: void_kinds[k] for k in VOID_KINDS},
                "void_above": VOID_FRAC * len(c.rows), "void": is_void(c),
                "cut_by_storage": len(c.storage_cut)})
    return {
        "mode": mode, "package_sha256": package_sha256(), "registration": REGISTRATION,
        "design": dataclasses.asdict(design), "models": models, "arms": list(ARMS),
        "tasks": list(TASKS), "n_contrasts": len(contrasts),
        "not_analysed": blocked, "reruns": reruns or [],
        "corpus": corpus, "apparatus": app,
        "same_day": [rules[m]["same_day"] for m in models],
        "failed_batch_items": [rules[m]["batches"] for m in models],
        "route_checked_plans": route_checked, "validated_plans": len(verdict.cache),
        "rates": rates, "contrasts": contrasts,
        "verdict_errors": verdict_errors(trials),
        "tool_choice": rq2(design, cells, track),
        "tool_right_answer_wrong": rq3(design, trials),
        "descriptive": desc, "refusals": refusal_table(desc),
        "storage_cut_rows": storage_table(cells, trials),
        "wrong_readings_named_in_advance": list(WRONG_READINGS),
        "tripwires_audited": {i: {"fired": fired[i], "note": audit_notes[i]} for i in fired},
    }


# ------------------------------------------------------------------ markdown
def render(res: dict) -> str:
    def rate_cell(r: dict) -> str:
        return f"{r['right']}/{r['n']}, {r['est']:.1f} [{r['lo']:.1f}, {r['hi']:.1f}]"

    def counts(d: dict) -> str:
        return "; ".join(f"{k} {v}" for k, v in d.items() if v) or "–"

    per = ", ".join(f"{t} {res['design']['per_task'][t]}" for t in res["tasks"])
    common = (f"Per model and task, never pooled over models or tasks. Trials per model and "
              f"arm: {per} (three wordings, {res['design']['k_domains']} domains)")
    L = [f"*Generated by `tools/reanalysis/frontier55.py` ({res['mode']} mode, package hash "
         f"`{res['package_sha256'][:12]}...`). The registered analysis of "
         f"`{res['registration']}`. Two hosted models, Claude Haiku 5.5 and Claude Sonnet 5.5; "
         f"two arms, no tools and tools offered; five tasks. A separate corpus: these rows are "
         f"not pooled with, ranked against or tested against any other run. The grade is the "
         f"final answer as the model wrote it: on solve and simulate the matched run's "
         f"registered grade, on the three validation tasks the rerun's frozen grade. Error "
         f"rows and refusals are wrong and stay in the denominator. Intervals are 95% "
         f"domain-cluster bootstrap. The conditions that differ from the open models "
         f"(section 3 of the registration) are stated wherever these rows are shown. Solve "
         f"plans of the stored table checked on the validator route before any new plan: "
         f"{res['route_checked_plans']}; plans validated in all: {res['validated_plans']}.*", ""]
    for b in res["not_analysed"]:
        L += [f"**{b['model']}: not analysed: {b['rule']}.** {b['detail']}. This model is in "
              f"no table below.", ""]
    for x in res["reruns"]:
        L += [f"**{x['model']}: read from the folders of its rerun** ({', '.join(x['folders'])})"
              f". The first attempt is kept and only counted: " + "; ".join(
                  f"{f['folder']}: " + (f"{f['rows']} rows ({counts(f['rows_per_task'])}), "
                                        f"{f['sidecar_lines']} sidecar lines"
                                        if f["found"] else "not found")
                  for f in x["first_attempt"]) + ".", ""]
    if res["tripwires_audited"]:
        L += ["**Tripwires that fired and were audited:** " + "; ".join(
            f"{i}: {v['fired']} (audit: {v['note']})"
            for i, v in res["tripwires_audited"].items()), ""]
    L += ["**Readings that would be wrong, named in advance (section 5):** "
          + "; ".join(res["wrong_readings_named_in_advance"]) + ".", ""]

    L += ["#### Claude run: RQ1, right answers per arm", "", f"{common}.", "",
          md_table(["model", "task", "arm", "right / trials, rate [95% interval]"],
                   [[r["model"], r["task"], ARM_WORDS[r["arm"]], rate_cell(r)]
                    for r in res["rates"]]), ""]
    L += ["#### Claude run: RQ1, tools minus no tools", "",
          f"Points, paired on the trial (task, domain, problem, plan label, wording). The "
          f"sign-flip p is exact over the {res['design']['k_domains']} domains, Holm-adjusted "
          f"across the five tasks of a model. {res['n_contrasts']} contrasts. {common}.", "",
          md_table(["model", "task", "pairs", "difference [95% interval]", "reading",
                    "sign-flip p", "Holm-adjusted p", "no tools wrong, tools right",
                    "no tools right, tools wrong"],
                   [[c["model"], c["task"], c["n_pairs"], M.ci_text(c), c["label"],
                     f"{c['p']:.3g}", f"{c['p_holm']:.3g}", c["gained"], c["lost"]]
                    for c in res["contrasts"]]), ""]
    L += ["#### Claude run: verdict errors on the validation tasks", "", f"{common}.", "",
          md_table(["model", "task", "arm", "valid inputs", "called invalid", "no verdict",
                    "of which error rows", "invalid inputs", "called valid", "no verdict",
                    "of which error rows"],
                   [[v["model"], v["task"], ARM_WORDS[v["arm"]], v["valid_inputs"],
                     v["valid_called_invalid"], v["valid_no_verdict"], v["valid_error_rows"],
                     v["invalid_inputs"], v["invalid_called_valid"], v["invalid_no_verdict"],
                     v["invalid_error_rows"]] for v in res["verdict_errors"]]), ""]
    L += ["#### Claude run: RQ2, which tool was called (tool arm)", "",
          f"The classes of `tools/reanalysis/rq23_metrics.py`. A refusal, a pause and an "
          f"unknown stop hold no tool calls; such a row is left out of the classes and counted "
          f"beside them. {common}.", "",
          md_table(["model", "task", "trials", "no call", "right only", "right + other",
                    "other only", "error rows left out",
                    "exactly the right tool, share of the classed trials [95% interval]",
                    "solve: called the other planner", "solve: right planner + a plan check only"],
                   [[c["model"], c["task"], c["n_trials"], c["counts"]["none"],
                     c["counts"]["right_only"], c["counts"]["right_plus"],
                     c["counts"]["other_only"],
                     f"{c['error_rows_left_out']} ({counts(c['error_rows_by_kind'])})",
                     share_cell(c["exactly_right"]), c["other_planner"], c["plan_check_only"]]
                    for c in res["tool_choice"]]), ""]
    L += ["#### Claude run: RQ3, tool right and final answer wrong (tool arm)", "",
          f"Of the trials where the right tool returned the right result (the stored harness "
          f"grade of the tool row, as for the open models), the trials whose final answer is "
          f"wrong under the registered grade. A refusal, a pause and an unknown stop are left "
          f"out of the set and counted beside it. \"Tool right\" is the run-time check of the "
          f"open models' definition, which credits a trial when any call returned the right "
          f"result, including a call to a tool other than the task's own. {common}.", "",
          md_table(["model", "task", "trials", "tool right", "answer wrong",
                    "share [95% interval]", "how the wrong answers ended",
                    "error rows left out"],
                   [[c["model"], c["task"], c["n_trials"], c["n_tool_right"],
                     c["n_answer_wrong"], share_cell(c["answer_wrong"]), counts(c["why"]),
                     c["error_rows_left_out"]] for c in res["tool_right_answer_wrong"]]), ""]
    L += ["#### Claude run: how the trials ended (descriptive)", "",
          f"A final turn that reached the output cap holding a note and no answer text is "
          f"counted under \"stopped at the cap with no answer\", the label the same event "
          f"gets for the open models. {common}.", "",
          md_table(["model", "arm", "task", "right by wording", "stopped at the output cap",
                    "of which with no answer", "of which the harness labelled think_overflow",
                    "loop exhausted", "refused for length", "refusals", "other error rows",
                    "cut by storage", "final answers no reader read"],
                   [[d["model"], ARM_WORDS[d["arm"]], d["task"],
                     "; ".join(f"v{v} {x['right']}/{x['n']}"
                               for v, x in d["right_by_wording"].items()),
                     d["stopped_at_the_output_cap"], d["stopped_at_the_cap_with_no_answer"],
                     d["labelled_think_overflow_by_the_harness"], d["loop_exhausted"],
                     d["refused_for_length"], d["refusals"],
                     f"{sum(d['other_error_rows'].values())} ({counts(d['other_error_rows'])})",
                     d["cut_by_storage"], d["unread_final_answers"]]
                    for d in res["descriptive"]]), ""]
    L += ["#### Claude run: turns and tokens per trial (descriptive)", "",
          f"From the sidecar, every trial counted, the error rows included. Input and output "
          f"tokens are summed over the turns of a trial; the output tokens include Sonnet's "
          f"notes between tool calls. {common}.", "",
          md_table(["model", "arm", "task", "turns, mean (max)", "input tokens, mean",
                    "output tokens, mean", "thinking tokens between tool calls, total",
                    "notes (thinking blocks)", "trials with a note", "tool calls",
                    "tool calls flagged as errors", "trials with a tool call"],
                   [[d["model"], ARM_WORDS[d["arm"]], d["task"],
                     f"{d['turns_mean']:.2f} ({d['turns_max']})", f"{d['input_tokens_mean']:.0f}",
                     f"{d['output_tokens_mean']:.0f}", d["thinking_tokens_total"],
                     d["thinking_blocks"], d["trials_with_a_note"], d["tool_calls"],
                     d["tool_calls_flagged_as_errors"], d["trials_with_a_tool_call"]]
                    for d in res["descriptive"]]), ""]
    L += ["#### Claude run: rows cut by storage (registered expectation: none)", "",
          md_table(["model", "arm", "task", "domain", "problem", "plan label", "wording",
                    "characters", "graded from", "right"],
                   [[s["model"], ARM_WORDS[s["arm"]], s["task"], s["domain"], s["problem"],
                     s["plan_label"] or "–", f"v{s['wording']}", s["answer_chars"],
                     s["graded_from"], "yes" if s["right"] else "no"]
                    for s in res["storage_cut_rows"]]
                   or [["–", "–", "–", "–", "–", "–", "–", "–", "none", "–"]]), ""]
    L += ["#### Claude run: the same-day rule (section 6)", "",
          "Both arms of a model count as the same day when the batch was sent and every tool "
          "trial was requested on one UTC date.", "",
          md_table(["model", "batch sent (UTC date: trials)", "batch ended (UTC date: trials)",
                    "tool trials", "tool trials requested on a later date", "share",
                    "same day"],
                   [[s["model"], counts(s["batch_sent_dates"]), counts(s["batch_ended_dates"]),
                     s["tool_trials"], s["tool_trials_on_a_later_date"],
                     f"{100 * s['share_on_a_later_date']:.1f}%",
                     "yes" if s["same_day"] else "no"] for s in res["same_day"]]), ""]
    L += ["#### Claude run: failed batch items (section 6)", "",
          "The batches of each no-tools folder in the order sent. Items that failed are sent "
          "again once, in a second batch; a model is run again when more than 1% of the arm's "
          "rows come from a third or later batch, or when the first batch expired as a whole.",
          "",
          md_table(["model", "batch", "requests", "succeeded", "errored", "canceled", "expired",
                    "rows in the folder"],
                   [[f["model"], f"{b['n']} ({b['batch_id']})", b["requests"],
                     b["request_counts"]["succeeded"], b["request_counts"]["errored"],
                     b["request_counts"]["canceled"], b["request_counts"]["expired"], b["rows"]]
                    for f in res["failed_batch_items"] for b in f["batches"]]), "",
          md_table(["model", "rows from a third or later batch", "run again above"],
                   [[f["model"], f["rows_from_a_third_or_later_batch"], f"{f['limit']:g}"]
                    for f in res["failed_batch_items"]]), ""]
    L += ["#### Claude run: corpus and apparatus", "",
          "Rows per folder as read by the rerun's frozen loader, and what the sidecar shows of "
          "how each folder was collected. A folder is VOID above 1% error rows that are not "
          "refusals. The two per-folder counts of refusals and of error rows are bookkeeping "
          "for the VOID rule; the reported counts are the ones per model, arm and task in the "
          "table of how the trials ended.", "",
          md_table(["folder", "read from", "rows", "refusals (bookkeeping for the VOID rule)",
                    "error rows that are not refusals (bookkeeping for the VOID rule)",
                    "VOID above", "cut by storage", "half-written lines (rows, sidecar)",
                    "sidecar lines of abandoned tries"],
                   [[c["folder"], c["path"], c["rows"], c["refusals"],
                     f"{c['error_rows_not_refusals']} ({counts(c['error_rows_by_kind'])})",
                     f"{c['void_above']:g}", c["cut_by_storage"],
                     f"{c['torn_lines']}, {c['sidecar_torn_lines']}",
                     c["sidecar_lines_of_abandoned_tries"]] for c in res["corpus"]]), "",
          md_table(["folder", "model ids returned", "request dates (UTC date: requests)",
                    "requests", "API version sent", "SDK", "hosts", "cache tokens",
                    "notes returned / passed back unchanged", "other content blocks",
                    "tools commit, validator, tool-list sha256 (run manifest)"],
                   [[a["folder"], ", ".join(a["model_ids_returned"]),
                     counts(a["request_dates_utc"]), a["requests"],
                     ", ".join(a["api_versions_sent"]) or "–", ", ".join(a["sdk_versions"]),
                     ", ".join(a["hosts"]) or "–", a["cache_tokens"],
                     f"{a['notes_returned_before_a_next_request']} / "
                     f"{a['notes_passed_back_unchanged']}",
                     counts(a["other_content_blocks"]),
                     "–" if a["manifest"]["tools_commit"] is None else
                     f"{a['manifest']['tools_commit'][:7]}, {a['manifest']['tools_pyvalidator']}, "
                     f"{a['manifest']['tools_sha256'][:12]}..."] for a in res["apparatus"]]), ""]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main
def fixture_design(root: Path) -> Design:
    d = json.loads((root / "design.json").read_text())
    design = Design(name="fixture", per_task=dict(d["per_task"]), n_folder=d["n_folder"],
                    per_wording=d["per_wording"], k_domains=d["k_domains"])
    if design.n_folder == REGISTERED.n_folder:
        raise Halt("fixture mode refuses a registered-size design")
    check_design(design, registered=False)
    return design


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parent
    ap.add_argument("--print-package-hash", action="store_true")
    ap.add_argument("--fixture", type=Path, help="synthetic fixture root (tests only)")
    ap.add_argument("--root", type=Path, default=REPO / "results" / RUN_NAME,
                    help="the folder that holds the four <model>_<arm> folders")
    ap.add_argument("--rerun-root", action="append", default=[], metavar="MODEL=PATH",
                    help="a model whose two arms were run again in new folders (sections 6 "
                         "and 7): the folder that holds its two new <model>_<arm> folders")
    ap.add_argument("--rerun-suffix", action="append", default=[], metavar="MODEL=SUFFIX",
                    help="the same, when the new folders are <model>_<arm><SUFFIX>")
    ap.add_argument("--gt-cache", type=Path, default=REPO / "results" / "derived" / "gt_cache.json")
    ap.add_argument("--plan-verdicts", type=Path,
                    default=REPO / "results" / "delivered-rerun-secondary" / "plan_verdicts.json",
                    help="the stored verdicts of the rerun's plans (validator route check)")
    ap.add_argument("--regrade-json", type=Path, default=here / "out" / "rq1_layout_regrade.json")
    ap.add_argument("--domains-dir", type=Path, default=REPO / "domains")
    ap.add_argument("--marketplace", type=Path,
                    help="the pddl-copilot checkout (required in live mode)")
    ap.add_argument("--out", type=Path, default=here / "out")
    ap.add_argument("--numbers", action="store_true",
                    help="splice the tables into development/NUMBERS.md (live mode)")
    ap.add_argument("--i-have-frozen", metavar="SHA256")
    ap.add_argument("--audited-tripwires", default="")
    ap.add_argument("--audit-notes", type=Path)
    args = ap.parse_args(argv)

    if args.print_package_hash:
        for rel, digest in file_hashes():
            print(f"{digest}  {rel}")
        print(f"{package_sha256()}  (package hash for --i-have-frozen)")
        return 0
    default_out = (here / "out").resolve()
    numbers = REPO / "development" / "NUMBERS.md"
    try:
        check_constants()
        audited = {x for x in args.audited_tripwires.split(",") if x}
        try:
            notes = RUN.load_audit_notes(args.audit_notes, audited)
        except RUN.Halt as e:
            raise Halt(str(e)) from e
        if args.fixture is not None:
            root = args.fixture
            if not (root / FIXTURE_MARKER).exists():
                raise Halt(f"fixture mode: {root} has no {FIXTURE_MARKER} marker")
            if args.numbers:
                raise Halt("--numbers is for live mode only")
            if args.out.resolve() == default_out:
                raise Halt("fixture mode needs its own --out (not tools/reanalysis/out)")
            design = fixture_design(root)
            domains = M.fixture_domains(root)
            gt_cache = json.loads((root / "gt_cache.json").read_text())
            run_root = root / RUN_NAME
            reruns = parse_reruns(args.rerun_root, args.rerun_suffix, run_root)
            cells = load_run(run_root, design, gt_cache,
                             file_sha256(root / "gt_cache.json", "ground-truth cache"), domains,
                             reruns)
            verdict = M.Verdicts(M.table_route(RUN.fixture_verdicts(root / "route")))
            checked = check_route_table(verdict, RUN.fixture_verdicts(root))
            env = {"validator": "fixture table"}
            mode, track = "fixture", MR.tracks_of(root / "domains", live=False)
        else:
            if args.i_have_frozen != package_sha256():
                raise Halt("refusing to read the Claude run: --i-have-frozen does not match "
                           "the package sha256 (freeze first, prereg sections 4 and 10)")
            if "pilot" in args.root.resolve().name:
                raise Halt(f"{args.root} is a pilot folder; the pilot is never analysed or "
                           f"pooled (prereg sections 2.1 and 6)")
            if args.marketplace is None:
                raise Halt("live mode requires --marketplace (the pddl-copilot checkout)")
            if args.numbers:
                text = numbers.read_text()
                if text.count(begin_marker(NUMBERS_TAG)) != 1 \
                        or text.count(end_marker(NUMBERS_TAG)) != 1:
                    raise Halt(f"--numbers: {numbers} has no one pair of {NUMBERS_TAG} markers")
            design = REGISTERED
            check_design(design, registered=True)
            run_root = args.root
            reruns = parse_reruns(args.rerun_root, args.rerun_suffix, run_root)
            gt_cache = load_gt_cache(args.gt_cache)
            try:
                RUN.check_domains(args.domains_dir)
            except RUN.Halt as e:
                raise Halt(str(e)) from e
            stored = stored_verdicts(args.plan_verdicts)
            env = validator_env(args)
            grid = registered_grid(args.domains_dir, gt_cache)
            cells = load_run(run_root, design, gt_cache, GT_CACHE_SHA256, None, reruns)
            check_grid(cells, grid)
            verdict = M.Verdicts(M.live_route(args.marketplace, args.domains_dir))
            checked = check_route_table(verdict, stored)
            mode, track = "live", MR.tracks_of(args.domains_dir, live=True)
        rerun_records = [{"model": m, "root": str(at), "suffix": suffix,
                          "folders": [cells[m][arm].path for arm in ARMS],
                          "first_attempt": first_attempt(run_root, m)}
                         for m, (at, suffix) in sorted(reruns.items())]
        res = analyse(design, cells, verdict, gt_cache, mode, checked, track, notes,
                      rerun_records)
        res["environment"] = env
        try:
            md = render(res)
            js = json.dumps(res, indent=1, sort_keys=True, default=list) + "\n"
        except Exception as e:  # noqa: BLE001 -- any render failure is a named HALT
            raise Halt(f"render failed ({type(e).__name__}: {e}); nothing written") from e
        MR.write_pair(args.out, STEM, js, md)
    except (Halt, R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for b in res["not_analysed"]:
        print(f"{b['model']}: not analysed: {b['rule']}: {b['detail']}")
    print(f"wrote {args.out}/{STEM}.{{json,md}}")
    if args.numbers:
        changed = write_numbers(numbers, NUMBERS_TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
