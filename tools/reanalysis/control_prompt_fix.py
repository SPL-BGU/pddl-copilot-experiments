#!/usr/bin/env python3
"""Corrected-prompt control for the no-tools arm on solve and simulate: the registered analysis.

    python -m tools.reanalysis.control_prompt_fix --print-package-hash
    python -m tools.reanalysis.control_prompt_fix --fixture tests/fixtures/control_prompt_fix \\
        --out OUT --control-dates "..."
    python -m tools.reanalysis.control_prompt_fix --smoke-check results/control-promptfix-smoke \\
        [--serve-logs DIR | --version-checked-by-hand NOTE]
    python -m tools.reanalysis.control_prompt_fix --results /abs/results \\
        --marketplace /abs/pddl-copilot --control-dates "..." \\
        [--serve-logs DIR | --version-checked-by-hand NOTE] --i-have-frozen <package hash>

Spec: development/reference/control_prompt_fix_prereg.md (sections 2 to 8). The
clause-by-clause map from the spec to this file is
development/reference/control_prompt_fix_traceability.md.

Three cells per model, the system message the only difference: O (the
registered text of Part C), A (the reference to the schema removed), B (the
answer format stated). Every row is read through the frozen loader of the
delivered rerun (`tools.delivered_rerun.schema.parse_row`) and graded by the
frozen delivered grader (`tools.delivered_rerun.grade.grade`). Beside it, the
second reading of the filed layout re-grade (`rq1_layout_regrade.block_plan`
on solve, `rq3_context_pilot.line_reader_exact` on simulate). Every solve plan,
under both readings, is validated by one injected function: in live mode the
in-process route on pddl-pyvalidator 0.1.5, in fixture mode a table.

Modes:
  --print-package-hash   sha256 over this script and every repo file it imports.
  live (default)         reads the control only with --i-have-frozen <that hash>.
  --fixture DIR          the same pipeline on the synthetic fixture (small design,
                         injected validator verdicts, no results/ and no validator).
  --smoke-check ROOT     the seven checks of prereg section 7, nothing else.

Order (live and fixture): registered constants -> control cells through the
typed loader (completeness, duplicate keys, storage cuts, VOID) -> pairing of
the three cells -> audit preconditions (section 7 items 4 to 7) and apparatus
checks -> the rerun's Part C and Part A rows (must reproduce the filed readout)
-> keys equal to Part C -> validator route check -> grades, both readings (the
rerun's second reading must reproduce the filed re-grade) -> C1 to C4 -> R1 to
R4 and the rule-5 flag -> tripwires -> JSON and markdown. Any failure exits 2
and writes nothing.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pddl_eval import control_prompts as CP
from pddl_eval.domains import load_domains
from pddl_eval.prompts import WITHOUT_TOOLS_SYSTEM_BY_TASK
from pddl_eval.runner import DEFAULT_NUM_PREDICT
from pddl_eval.scoring import _safe_json_loads, _strip_md_fence, strip_leaked_channel_prefix
from tools.delivered_rerun import constants as C
from tools.delivered_rerun import grade as G
from tools.delivered_rerun import run as RUN
from tools.delivered_rerun import schema as S
from tools.delivered_rerun import stats as ST
from tools.e2e_regrade import _FENCED_BLOCK_RE, _TOLERANT_ACTION_RE, oracle_canon_for
from tools.gt_cache_gate import PREREG_PINNED_HASH, canonical_hash  # noqa: F401 (hashed dep)
from tools.reanalysis import iss027_common as C27
from tools.reanalysis import rq1_layout_regrade as RG
from tools.reanalysis import rq1_metrics as R1
from tools.reanalysis import rq3_context_pilot as PILOT
from tools.reanalysis.gen_common import md_table, model_name, write_numbers

REPO = Path(__file__).resolve().parents[2]
SCRIPT = "tools/reanalysis/control_prompt_fix.py"
NUMBERS_TAG = "CONTROL-PROMPT-FIX"
FIXTURE_MARKER = "SYNTHETIC_FIXTURE"

# Every repo file this script imports, directly or through the modules it
# imports (sorted). Part of the freeze: an edit to any of them changes the
# package hash, so --i-have-frozen refuses until the change is declared.
# tests/test_control_prompt_fix.py checks this list covers sys.modules.
DEPENDENCIES = (
    "pddl_eval/__init__.py", "pddl_eval/chat.py", "pddl_eval/control_prompts.py",
    "pddl_eval/domains.py", "pddl_eval/prompts.py", "pddl_eval/resume.py",
    "pddl_eval/runner.py", "pddl_eval/schemas.py", "pddl_eval/scoring.py",
    "pddl_eval/summary.py", "run_experiment.py", "tools/__init__.py",
    "tools/_run_manifest.py", "tools/delivered_rerun/__init__.py",
    "tools/delivered_rerun/analysis.py", "tools/delivered_rerun/constants.py",
    "tools/delivered_rerun/e4.py", "tools/delivered_rerun/grade.py",
    "tools/delivered_rerun/readout.py", "tools/delivered_rerun/run.py",
    "tools/delivered_rerun/schema.py", "tools/delivered_rerun/stats.py",
    "tools/delivered_rerun/tripwires.py", "tools/e2e_regrade.py", "tools/gt_cache_gate.py",
    "tools/reanalysis/gen_common.py", "tools/reanalysis/iss027_common.py",
    "tools/reanalysis/rq1_layout_regrade.py", "tools/reanalysis/rq1_metrics.py",
    "tools/reanalysis/rq3_context_pilot.py",
)


class Halt(Exception):
    """A registered stop: exits non-zero with the message, nothing written."""


class AuditFailed(Halt):
    """Section 7 items 4 to 7: an audit precondition does not hold."""


# ------------------------------------------------------------------ registered constants
# prereg section 2.1: cells, wrapper values, folder tokens, system-text sha256.
CELLS: tuple[str, ...] = ("O", "A", "B")
WRAPPER = {"O": "registered", "A": "no-pointer", "B": "format-stated"}
CELL_TOKENS = {"O": "no-tools", "A": "no-tools-syspointer-off", "B": "no-tools-sysformat"}
SYSTEM_SHA256 = {
    "O": {"solve": "dd835ea2f66c73f8f26cb80b11afae9030aac316f102fb54a433498b6e23de83",
          "simulate": "dfd6beadb3e815e769fd31bd88f99ed78c0cfb6c9b74001fe442cc0b2bbc5ccd"},
    "A": {"solve": "1cf4b9b6a7652fa90dc36cd41b98e3a312bebe6be3a427e3f16a62c4a7b2dfa8",
          "simulate": "c99db1124156372ea0e0a88b41779c4b9aa62167821a99272fa886f8b1774553"},
    "B": {"solve": "3dbc1baf9e2670b024a7fec73b2fe7031c5fa5a5c13b711a12b18debf0ad0588",
          "simulate": "7ccf5d9deccd98e72590f3649113929ea099ba855a72db1c571e91b6d1d47cf9"},
}
# section 2.2: models (folder tag -> model id), tasks, wordings.
MODELS = {
    "Qwen3_5_9B": "Qwen/Qwen3.5-9B",
    "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
    "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
}
MODEL_ORDER: tuple[str, ...] = ("Qwen3_5_9B", "gemma4_26b-a4b", "qwen3_6_35b")
TASKS: tuple[str, ...] = ("solve", "simulate")
WORDINGS: tuple[int, ...] = (11, 12, 13)
# section 2.3 and 2.4: apparatus and run tags.
CONTEXT_WINDOW = 16_384
OUTPUT_CAP = {"solve": 8_192, "simulate": 6_144}
STORAGE_CAP = 65_536
VLLM_VERSION = "0.20.2"
RUN_TAG = "control-promptfix"
SMOKE_TAG = "control-promptfix-smoke"
R2_TAG = "control-promptfix-r2"
# section 3: the validator release.
PYVALIDATOR = "0.1.5"
# section 4: statistics.
MARGIN = 5.0
LEVEL = 0.95
B_BOOT = 10_000
SEED = 20261002
HOLM_FAMILY = 6
HOLM_ALPHA = 0.05
N_CONTRASTS = 24
CONTRASTS: tuple[str, ...] = ("C1", "C2", "C3", "C4")
READINGS: tuple[str, ...] = ("frozen", "second")
# section 5 R4: the dates of Part A.
PART_A_DATES = "2026-10-03 to 2026-10-09"
# section 6 rule 5.
QUOTE_BOTH_POINTS = 5.0
# section 7: smoke and stop rules.
SMOKE_NONEMPTY = 0.95
VOID_FRAC = 0.01
PAIRING_MIN = 0.99
# section 8: tripwires.
TRIPWIRE_POINTS = 20.0
UNREAD_FRAC = 0.05            # cell B: more than 5% unread final answers (15 of 300)

READING_WORDS = {"frozen": "frozen grade (the registered measure)",
                 "second": "second reading (layout-tolerant)"}
CELL_WORDS = {"O": "O (registered text)", "A": "A (schema reference removed)",
              "B": "B (answer format stated)"}
CONTRAST_WORDS = {"C1": "A minus O", "C2": "B minus O", "C3": "O minus Part C",
                  "C4": "tools, plain wording (Part A) minus B"}
_BANNERS = (re.compile(r"Initializing a V1 LLM engine \(v([0-9][0-9A-Za-z.+-]*)\)"),
            re.compile(r"vLLM API server version ([0-9][0-9A-Za-z.+-]*)"))
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Design:
    """Size constants (live = REGISTERED; smoke = SMOKE; the fixture carries its own)."""
    name: str
    per_task_cell: int      # trials per model, task and cell
    per_folder: int         # rows per cell folder (one model, one system text, two tasks)
    per_wording: int        # rows per wording in a cell folder
    per_task_wording: int   # rows per task and wording in a cell folder
    k_domains: int          # domain clusters


REGISTERED = Design("registered", per_task_cell=300, per_folder=600, per_wording=200,
                    per_task_wording=100, k_domains=20)
SMOKE = Design("smoke", per_task_cell=60, per_folder=120, per_wording=40,
               per_task_wording=20, k_domains=20)


def _check(cond: bool, what: str) -> None:
    """A registered check that `python -O` cannot strip."""
    if cond is not True:
        raise C.RegisteredCheckFailed(f"registered check failed: {what}")


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def system_text(cell: str, task: str) -> str:
    """The system text a cell sends on a task (section 2.1)."""
    if cell == "O":
        return WITHOUT_TOOLS_SYSTEM_BY_TASK[task]
    return CP.NO_TOOLS_SYSTEM_CONTROL[WRAPPER[cell]][task]


def check_constants() -> None:
    """Gate 2: every quantity sections 2 to 8 name, as a raised check. Reads the
    module globals at call time, so a test can flip one and see it fire."""
    g = globals()
    _check(g["TASKS"] == ("solve", "simulate"), "tasks solve and simulate")
    _check(g["CELLS"] == ("O", "A", "B"), "cells O, A, B")
    _check(g["WRAPPER"] == {"O": "registered", "A": "no-pointer", "B": "format-stated"},
           "wrapper values")
    _check(g["CELL_TOKENS"] == {"O": "no-tools", "A": "no-tools-syspointer-off",
                                "B": "no-tools-sysformat"}, "cell tokens")
    _check(tuple(CP.NO_TOOLS_SYSTEM_MODES) == ("no-pointer", "format-stated"),
           "control_prompts modes")
    for cell in CELLS:
        for t in TASKS:
            want = g["SYSTEM_SHA256"][cell][t]
            _check(_HEX64.match(want) is not None, f"sha256 literal {cell}/{t}")
            _check(_text_sha(system_text(cell, t)) == want,
                   f"system text {cell}/{t} has the registered sha256")
            _check(CP.SYSTEM_TEXT_SHA256[WRAPPER[cell]][t] == want,
                   f"control_prompts.SYSTEM_TEXT_SHA256 {cell}/{t}")
    _check(len({g["SYSTEM_SHA256"][c][t] for c in CELLS for t in TASKS}) == 6,
           "six distinct system texts")
    _check(g["MODELS"] == {"Qwen3_5_9B": "Qwen/Qwen3.5-9B",
                           "gemma4_26b-a4b": "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
                           "qwen3_6_35b": "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"}, "model ids")
    _check(all(C.MODEL_IDS[m] == i for m, i in g["MODELS"].items()),
           "model ids are the rerun's")
    _check(set(g["MODEL_ORDER"]) == set(g["MODELS"]) == set(C.PART_A_MODELS),
           "three models, the rerun's")
    _check(g["WORDINGS"] == (11, 12, 13) == C.PLAIN, "wordings v11 to v13")
    _check(C.THINK == "off", "thinking off")
    _check(C.STYLE_A == "minimal", "prompt style of Part C")
    _check(g["CONTEXT_WINDOW"] == 16_384 == C.CONTEXT_WINDOW, "16,384-token window")
    _check(g["OUTPUT_CAP"] == {"solve": 8_192, "simulate": 6_144}, "output caps")
    _check(all(g["OUTPUT_CAP"][t] == DEFAULT_NUM_PREDICT[t] for t in g["TASKS"]),
           "output caps are the harness's DEFAULT_NUM_PREDICT")
    _check(g["STORAGE_CAP"] == 65_536 == C.STORAGE_CAP, "storage cap 65,536")
    _check(g["VLLM_VERSION"] == "0.20.2", "vLLM 0.20.2")
    _check(g["RUN_TAG"] == "control-promptfix", "run tag")
    _check(g["SMOKE_TAG"] == "control-promptfix-smoke", "smoke run tag")
    _check(g["R2_TAG"] == "control-promptfix-r2", "VOID rerun tag")
    _check(g["PYVALIDATOR"] == "0.1.5" == C27.PYVAL_EXPECTED, "pddl-pyvalidator 0.1.5")
    _check(g["MARGIN"] == 5.0 == C.MARGIN, "margin 5 points")
    _check(g["LEVEL"] == 0.95 == C.CI_ENDPOINT, "95% intervals")
    _check(g["B_BOOT"] == 10_000 == C.B_BOOT, "10,000 resamples")
    _check(g["SEED"] == 20261002 == C.SEED, "seed 20261002")
    _check(g["HOLM_FAMILY"] == 6 == len(g["MODELS"]) * len(g["TASKS"]), "Holm family 6")
    _check(g["HOLM_ALPHA"] == 0.05 == C.HOLM_ALPHA, "Holm alpha 0.05")
    _check(g["CONTRASTS"] == ("C1", "C2", "C3", "C4"), "contrasts C1 to C4")
    _check(g["N_CONTRASTS"] == 24 == len(g["CONTRASTS"]) * len(g["MODELS"]) * len(g["TASKS"]),
           "24 contrasts")
    _check(g["READINGS"] == ("frozen", "second"), "two readings")
    _check(g["PART_A_DATES"] == "2026-10-03 to 2026-10-09", "dates of Part A")
    _check(g["QUOTE_BOTH_POINTS"] == 5.0, "rule 5: more than 5 points")
    _check(g["SMOKE_NONEMPTY"] == 0.95, "smoke: 95% non-empty")
    _check(g["VOID_FRAC"] == 0.01 == C.EXCEPTION_VOID_FRAC, "VOID above 1%")
    _check(C.EXCEPTION_REASONS == frozenset({"exception", "ollama_parse_error"}),
           "exception reasons of the rerun")
    _check(g["PAIRING_MIN"] == 0.99, "pairing 99%")
    _check(g["TRIPWIRE_POINTS"] == 20.0, "tripwire 20 points")
    _check(g["UNREAD_FRAC"] == 0.05, "unread final answers: more than 5%")


def check_design(design: Design, registered: bool) -> None:
    """Size constants. Live mode passes REGISTERED and checks every field."""
    if registered:
        _check(design is REGISTERED, "live mode runs on the REGISTERED design")
        _check(design.per_task_cell == 300, "300 trials per model, task and cell")
        _check(design.per_folder == 600, "600 rows per cell folder")
        _check(design.per_wording == 200, "200 rows per wording")
        _check(design.per_task_wording == 100, "100 problems per task and wording")
        _check(design.k_domains == 20, "k = 20 domains")
        _check(design.per_folder * len(CELLS) * len(MODELS) == 5_400, "5,400 trials")
        _check(UNREAD_FRAC * design.per_task_cell == 15, "the fourth tripwire: more than 15 of 300")
    _check(design.per_folder == design.per_task_cell * len(TASKS), "rows per folder")
    _check(design.per_folder == design.per_wording * len(WORDINGS), "rows per wording")
    _check(design.per_task_cell == design.per_task_wording * len(WORDINGS),
           "rows per task and wording")


def check_smoke_design() -> None:
    _check(SMOKE.per_folder == 120, "smoke: 120 rows per cell folder")
    _check(SMOKE.k_domains == 20 and SMOKE.per_task_wording == 20,
           "smoke: the first problem of every domain")
    check_design(SMOKE, registered=False)


check_constants()


# ------------------------------------------------------------------ package hash
def frozen_files() -> list[tuple[str, Path]]:
    return [(rel, REPO / rel) for rel in sorted((SCRIPT,) + DEPENDENCIES)]


def file_hashes() -> list[tuple[str, str]]:
    return [(rel, hashlib.sha256(p.read_bytes()).hexdigest()) for rel, p in frozen_files()]


def package_sha256() -> str:
    """sha256 over (path, sha256(bytes)), the construction of run.package_sha256."""
    h = hashlib.sha256()
    for rel, digest in file_hashes():
        h.update(rel.encode() + b"\0" + digest.encode() + b"\n")
    return h.hexdigest()


# ------------------------------------------------------------------ names and specs
def folder_name(model: str, cell: str, tag: str) -> str:
    return f"slurm_vllm_{model}_{C.THINK}_{CELL_TOKENS[cell]}_{tag}"


def control_spec(design: Design, model: str, cell: str, tag: str) -> S.CellSpec:
    """The control's cell spec: Part C's spec with the control's folder and sizes."""
    return dataclasses.replace(
        S.spec_rerun_c(C.REGISTERED, model), name=folder_name(model, cell, tag), tasks=TASKS,
        variants=WORDINGS, n_rows=design.per_folder, per_variant=design.per_wording,
        per_task_variant={t: design.per_task_wording for t in TASKS},
        k_domains=design.k_domains)


def rerun_spec(design: Design, model: str, part: str) -> S.CellSpec:
    """Fixture only: a Part C or Part A cell holding solve and simulate, plain wordings."""
    base = (S.spec_rerun_c if part == "C" else S.spec_rerun_a)(C.REGISTERED, model)
    return dataclasses.replace(
        base, tasks=TASKS, variants=WORDINGS, n_rows=design.per_folder,
        per_variant=design.per_wording,
        per_task_variant={t: design.per_task_wording for t in TASKS},
        k_domains=design.k_domains)


# ------------------------------------------------------------------ typed load boundary
@dataclass(frozen=True)
class Folder:
    spec: S.CellSpec
    model: str
    cell: str
    rows: tuple[S.Row, ...]
    storage_cut: frozenset          # trial keys accepted under the storage-cut rule
    torn_lines: int
    exception_rows: int             # is_exception (failure_reason or empty-message shape)
    infra_rows: int
    void_rule_rows: int             # exception or infrastructure failure


def read_folder(root: Path, spec: S.CellSpec, model: str, cell: str,
                domains: frozenset | None = None) -> Folder:
    """One cell folder through the frozen `schema.parse_row`.

    A row cut by storage is refused by the frozen loader. Section 7: it is
    accepted here only when the answer also stopped at the output cap, read
    on its stored characters and counted; any other cut row halts. Duplicate
    trial keys halt. A torn line (a record half-written when a job was killed)
    is counted and skipped, as the frozen `load_cell` does; completeness then
    proves every key is present intact."""
    cell_dir = root / spec.name
    if not cell_dir.is_dir():
        raise S.IncompleteCell(f"cell folder not found: {cell_dir}")
    files = sorted(p.name for p in cell_dir.glob("trials*.jsonl"))
    if files != ["trials.jsonl"]:
        raise S.SchemaError(f"{cell_dir}: expected exactly trials.jsonl, found {files}")
    rows: list[S.Row] = []
    seen: set = set()
    cut: set = set()
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
            was_cut = False
            if isinstance(obj, dict) and isinstance(obj.get("result"), dict):
                res = obj["result"]
                if res.get("response_truncated_by_storage") is True:
                    if res.get("done_reason") != "length":
                        raise Halt(f"{where}: an answer cut by storage that did not stop at "
                                   f"the output cap (section 7)")
                    was_cut = True
                    obj = {**obj, "result": {**res, "response_truncated_by_storage": False}}
            row = S.parse_row(obj, spec, where)
            if domains is not None and row.domain not in domains:
                raise Halt(f"{where}: domain {row.domain!r} is not one of the fixture's own "
                           f"(fixture mode reads synthetic rows only)")
            if row.trial_key in seen:
                raise Halt(f"{where}: duplicate trial key {row.trial_key} (section 7)")
            seen.add(row.trial_key)
            rows.append(row)
            if was_cut:
                cut.add(row.trial_key)
    S._check_completeness(spec, rows)
    return Folder(spec=spec, model=model, cell=cell, rows=tuple(rows), storage_cut=frozenset(cut),
                  torn_lines=torn, exception_rows=sum(r.is_exception for r in rows),
                  infra_rows=sum(r.infra_failure for r in rows),
                  void_rule_rows=sum(r.is_exception or r.infra_failure for r in rows))


def check_void(f: Folder) -> None:
    """Section 7: VOID above 1% exception or infrastructure-failure rows."""
    if f.void_rule_rows > VOID_FRAC * len(f.rows):
        raise Halt(f"VOID (section 7): {f.spec.name} has {f.void_rule_rows} exception or "
                   f"infrastructure-failure rows of {len(f.rows)} (more than "
                   f"{100 * VOID_FRAC:.0f}%); all three cells of {f.model} are run again "
                   f"from scratch under the run tag {R2_TAG}, not analysed")


def load_control(root: Path, design: Design, tags: dict[str, str],
                 domains: frozenset | None = None) -> dict:
    """{model: {cell: Folder}} for the nine cells, with the section 7 load rules."""
    out = {}
    for m in MODEL_ORDER:
        out[m] = {}
        for cell in CELLS:
            f = read_folder(root, control_spec(design, m, cell, tags[m]), m, cell, domains)
            check_void(f)
            out[m][cell] = f
    return out


def first_run_void(root: Path, design: Design, model: str,
                   domains: frozenset | None = None) -> str:
    """Section 7: the second run of a model is read only after the analysis has found
    a cell of that model's first run VOID, by the exception rule or the pairing rule.
    Returns the VOID finding; halts when the first run is missing, short, refused by
    the loader for another reason, or not VOID."""
    folders = {}
    for cell in CELLS:
        spec = control_spec(design, model, cell, RUN_TAG)
        try:
            folders[cell] = read_folder(root, spec, model, cell, domains)
        except S.SchemaError as e:
            raise Halt(f"--r2-models {model}: the first run cannot be read ({e}); the second "
                       f"run is read only after a VOID first run") from e
    for cell in CELLS:
        try:
            check_void(folders[cell])
        except Halt as e:
            return str(e)
    try:
        check_pairing({model: folders}, design)
    except Halt as e:
        return str(e)
    raise Halt(f"--r2-models {model}: no cell of the first run is VOID, so the second run "
               f"({R2_TAG}) is not read")


def resolve_tags(root: Path, design: Design, r2_arg: str,
                 domains: frozenset | None = None) -> tuple[dict, dict]:
    """The run tag of each model's cells, and the VOID finding behind every r2 model."""
    r2 = {x for x in r2_arg.split(",") if x}
    if not r2 <= set(MODELS):
        raise Halt(f"--r2-models: unknown model tags {sorted(r2 - set(MODELS))}")
    found = {m: first_run_void(root, design, m, domains) for m in sorted(r2)}
    return {m: (R2_TAG if m in r2 else RUN_TAG) for m in MODEL_ORDER}, found


def check_pairing(control: dict, design: Design) -> dict:
    """Section 7: the three cells of a model hold the same keys; fewer than 99% shared
    is VOID. Returns the shared-key count per model."""
    shared = {}
    for m, cells in control.items():
        keys = [{r.trial_key for r in cells[c].rows} for c in CELLS]
        common = keys[0] & keys[1] & keys[2]
        if len(common) < PAIRING_MIN * design.per_folder:
            raise Halt(f"VOID (section 7): the cells of {m} share {len(common)} of "
                       f"{design.per_folder} trial keys (fewer than "
                       f"{100 * PAIRING_MIN:.0f}%)")
        shared[m] = len(common)
    return shared


def check_keys_equal_part_c(control: dict, part_c: dict) -> None:
    """Section 7: each task's keys of every cell equal the keys of Part C."""
    for m, cells in control.items():
        for cell in CELLS:
            for t in TASKS:
                ks = {r.trial_key for r in cells[cell].rows if r.task == t}
                pc = set(part_c[m][t])
                if ks != pc:
                    raise Halt(f"{cells[cell].spec.name}: the {t} keys differ from Part C's "
                               f"({len(ks - pc)} not in Part C, {len(pc - ks)} missing)")


# ------------------------------------------------------------------ audit preconditions
def audit_lines(path: Path, where: str) -> list[dict]:
    if not path.is_file():
        raise AuditFailed(f"{where}: no system_prompt_audit.jsonl")
    out = []
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError as e:
            raise AuditFailed(f"{where}: audit line {i} is not JSON") from e
        if not isinstance(o, dict):
            raise AuditFailed(f"{where}: audit line {i} is not an object")
        out.append(o)
    if not out:
        raise AuditFailed(f"{where}: the audit log is empty")
    return out


AUDIT_KEYS = frozenset({"mode", "swapped", "system_sha256", "user_sha256", "model", "has_tools"})


def check_audit(cell_dir: Path, model: str, cell: str, rows) -> Counter:
    """Section 7 item 4 for one cell; returns the user-text sha256 counts (item 5).

    The line shape is `pddl_eval/vllm_client.py` `_write_audit`. Every line: the
    system sha256 is the registered one of this cell for one of its two tasks;
    the stored text, where a line carries it, is that text byte for byte; mode
    names the cell's text; cell O not swapped, A and B swapped; no tools; the
    model id of the cell. So that the log covers every trial, each task has at least
    as many lines as rows and exactly as many different user texts as rows."""
    where = cell_dir.name
    by_sha = {SYSTEM_SHA256[cell][t]: t for t in TASKS}
    users: Counter = Counter()
    per_task: Counter = Counter()
    distinct: dict[str, set] = {t: set() for t in TASKS}
    for i, o in enumerate(audit_lines(cell_dir / "system_prompt_audit.jsonl", where), 1):
        keys = set(o)
        if not (AUDIT_KEYS <= keys <= AUDIT_KEYS | {"system_text"}):
            raise AuditFailed(f"{where}: audit line {i} has keys {sorted(keys)}")
        sha = o["system_sha256"]
        if sha not in by_sha:
            raise AuditFailed(f"{where}: audit line {i}: system sha256 {str(sha)[:12]}... is not "
                              f"the registered text of cell {cell}")
        task = by_sha[sha]
        if "system_text" in o:
            if not isinstance(o["system_text"], str) or o["system_text"] != system_text(cell, task) \
                    or _text_sha(o["system_text"]) != sha:
                raise AuditFailed(f"{where}: audit line {i}: the stored system text is not the "
                                  f"registered {cell}/{task} text byte for byte")
        if o["mode"] != WRAPPER[cell]:
            raise AuditFailed(f"{where}: audit line {i}: mode {o['mode']!r}, cell {cell} is "
                              f"{WRAPPER[cell]!r}")
        if o["swapped"] is not (cell != "O"):
            raise AuditFailed(f"{where}: audit line {i}: swapped={o['swapped']!r}; cell O is not "
                              f"swapped, A and B are")
        if o["has_tools"] is not False:
            raise AuditFailed(f"{where}: audit line {i} has tools")
        if o["model"] != MODELS[model]:
            raise AuditFailed(f"{where}: audit line {i}: model {o['model']!r}")
        if not isinstance(o["user_sha256"], str) or not _HEX64.match(o["user_sha256"]):
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
            raise AuditFailed(f"{where}: {len(distinct[t])} different user texts for {t}, the "
                              f"cell has {rows_per_task[t]} rows of it")
    return users


def check_users(model: str, users: dict[str, Counter]) -> dict[str, int]:
    """Section 7 item 5: the same set of user-text sha256 in O, A and B. A text that
    appears more often in one cell is allowed (a resumed job sends its unfinished
    requests again); returns, per cell, the lines above the smallest count of the
    three, which are reported."""
    sets = {c: set(users[c]) for c in CELLS}
    if not (sets["O"] == sets["A"] == sets["B"]):
        missing = len((sets["O"] | sets["A"] | sets["B"]) - (sets["O"] & sets["A"] & sets["B"]))
        raise AuditFailed(f"{model}: the user messages differ between the cells "
                          f"({missing} user texts are not in all three)")
    low = {s: min(users[c][s] for c in CELLS) for s in sets["O"]}
    return {c: sum(users[c][s] - low[s] for s in sets["O"]) for c in CELLS}


def read_settings(cell_dir: Path) -> dict:
    path = cell_dir / "client_settings.json"
    if not path.is_file():
        raise AuditFailed(f"{cell_dir.name}: no client_settings.json")
    try:
        s = json.loads(path.read_text())
    except ValueError as e:
        raise AuditFailed(f"{cell_dir.name}: client_settings.json is not JSON") from e
    if not isinstance(s, dict):
        raise AuditFailed(f"{cell_dir.name}: client_settings.json is not an object")
    return s


def check_settings(cell_dir: Path, model: str, cell: str) -> dict:
    """Section 7 item 6: client_settings.json (cluster-experimenting/reasoning_settings.py,
    written by the sbatch) names this cell's system text, condition, audit log and model."""
    s = read_settings(cell_dir)
    want = {"no_tools_system": WRAPPER[cell], "cond": CELL_TOKENS[cell],
            "hf_model": MODELS[model]}
    for k, v in want.items():
        if k not in s or s[k] != v:
            raise AuditFailed(f"{cell_dir.name}: client_settings.json {k}={s.get(k)!r}, this "
                              f"cell is {v!r}")
    log = s.get("system_audit_log")
    if not isinstance(log, str) or not log.endswith(f"/{cell_dir.name}/system_prompt_audit.jsonl"):
        raise AuditFailed(f"{cell_dir.name}: client_settings.json system_audit_log {log!r} is not "
                          f"this cell's audit log")
    return s


def serve_versions(text: str) -> list[str]:
    return [v for rx in _BANNERS for v in rx.findall(text)]


def check_serve_log(serve_logs: Path, cell_dir: Path, model: str, settings: dict) -> str:
    """Section 7 item 7: the serve log of the last job that wrote the cell (the job
    client_settings.json names) shows vLLM 0.20.2 and no other version.

    The sbatch keeps the log as cluster-experimenting/logs/<job id>-vllm-<model tag>.log
    on the cluster. Earlier jobs of a resumed cell are read on the cluster and recorded
    in section 9, not here."""
    job = settings.get("slurm_job_id")
    if not isinstance(job, str) or not job:
        raise AuditFailed(f"{cell_dir.name}: client_settings.json has no slurm_job_id")
    path = serve_logs / f"{job}-vllm-{model}.log"
    if not path.is_file():
        raise AuditFailed(f"{cell_dir.name}: serve log {path.name} not in {serve_logs}")
    vs = serve_versions(path.read_text(errors="replace"))
    if not vs:
        raise AuditFailed(f"{cell_dir.name}: {path.name} has no vLLM version banner")
    if set(vs) != {VLLM_VERSION}:
        raise AuditFailed(f"{cell_dir.name}: {path.name} shows vLLM {sorted(set(vs))}, "
                          f"registered {VLLM_VERSION}")
    return path.name


def check_apparatus(cell_dir: Path, f: Folder, settings: dict) -> dict:
    """Section 2.3 where the files expose it (live and fixture; not a smoke check):
    the 16,384-token window and thinking off in client_settings.json and in every
    summary file; temperature 0; the output cap of each task in the rows (no answer
    is longer, and an answer that stopped at the cap without a clipped turn used
    all of it)."""
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
                "conditions": "no-tools", "models": [MODELS[f.model]]}
        for k, v in want.items():
            if meta.get(k) != v:
                raise Halt(f"{where}/{p.name}: meta {k}={meta.get(k)!r}, registered {v!r}")
    for r in f.rows:
        cap = OUTPUT_CAP[r.task]
        if r.tokens.completion > cap:
            raise Halt(f"{where}: an answer of {r.tokens.completion} tokens, cap {cap}")
        if (r.done_reason == "length" and r.tokens.ctx_clipped_turns == 0
                and not r.no_room and r.tokens.completion != cap):
            raise Halt(f"{where}: an answer stopped at the cap after {r.tokens.completion} "
                       f"tokens, registered cap {cap}")
    return {"summaries": len(summaries)}


def audit_control(root: Path, control: dict, serve_logs: Path | None,
                  version_note: str | None, apparatus: bool = True) -> dict:
    """Items 4 to 7 as preconditions (section 7), before any answer is graded.
    Item 7 needs the serve logs, or a note that the version was checked by hand."""
    out = {"serve_logs": {}, "settings": {}, "apparatus": {}, "extra_user_lines": {},
           "version_note": version_note}
    if serve_logs is None and not (version_note and version_note.strip()):
        raise AuditFailed("item 7 (vLLM 0.20.2 in every serve log) is not checked: pass "
                          "--serve-logs DIR or --version-checked-by-hand NOTE")
    for m, cells in control.items():
        users = {}
        for cell in CELLS:
            f = cells[cell]
            d = root / f.spec.name
            users[cell] = check_audit(d, m, cell, f.rows)
            s = check_settings(d, m, cell)
            out["settings"][f.spec.name] = {"slurm_job_id": s.get("slurm_job_id")}
            if serve_logs is not None:
                out["serve_logs"][f.spec.name] = check_serve_log(serve_logs, d, m, s)
            if apparatus:
                out["apparatus"][f.spec.name] = check_apparatus(d, f, s)
        extra = check_users(m, users)
        for cell in CELLS:
            out["extra_user_lines"][cells[cell].spec.name] = extra[cell]
    return out


# ------------------------------------------------------------------ smoke check
def smoke_check(root: Path, serve_logs: Path | None, version_note: str | None,
                out=print) -> int:
    """Section 7, the smoke: the seven checks and nothing else. Prints no success
    rate, no failure-reason count and no answer text."""
    check_smoke_design()
    fails: dict[int, list[str]] = {i: [] for i in range(1, 8)}
    loaded: dict[tuple, Folder] = {}
    extra_lines: dict[str, int] = {}
    for m in MODEL_ORDER:
        for cell in CELLS:
            spec = control_spec(SMOKE, m, cell, SMOKE_TAG)
            try:
                f = read_folder(root, spec, m, cell)
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
            nonempty = sum(bool(strip_leaked_channel_prefix(r.response).strip()) for r in f.rows)
            if nonempty < SMOKE_NONEMPTY * len(f.rows):
                fails[3].append(f"{spec.name}: fewer than {100 * SMOKE_NONEMPTY:.0f}% of the "
                                f"stored answers are non-empty")
            loaded[(m, cell)] = f
    for m in MODEL_ORDER:
        users = {}
        for cell in CELLS:
            d = root / folder_name(m, cell, SMOKE_TAG)
            rows = loaded[(m, cell)].rows if (m, cell) in loaded else ()
            try:
                users[cell] = check_audit(d, m, cell, rows)
            except AuditFailed as e:
                fails[4].append(str(e))
            try:
                s = check_settings(d, m, cell)
            except AuditFailed as e:
                fails[6].append(str(e))
                s = None
            if serve_logs is not None:
                try:
                    if s is None:
                        s = read_settings(d)
                    check_serve_log(serve_logs, d, m, s)
                except AuditFailed as e:
                    fails[7].append(str(e))
        if len(users) == 3:
            try:
                extra = check_users(m, users)
                for cell in CELLS:
                    extra_lines[folder_name(m, cell, SMOKE_TAG)] = extra[cell]
            except AuditFailed as e:
                fails[5].append(str(e))
        else:
            fails[5].append(f"{m}: not checked, an audit log failed item 4")
    names = {1: "every cell folder holds its 120 rows",
             2: "the frozen loader reads every row; no exception or infrastructure-failure "
                "row; no row cut by storage; no half-written line",
             3: f"in every cell at least {100 * SMOKE_NONEMPTY:.0f}% of the stored answers "
                f"are non-empty",
             4: "audit log: registered system sha256 and text, swapped flag, no tools, the "
                "cell's model, at least one line and one different user text per row of each "
                "task",
             5: "the same set of user messages in the three cells of a model",
             6: "client_settings.json names the cell's system text",
             7: f"the serve log of the last job that wrote each cell (the job its "
                f"client_settings.json names) shows vLLM {VLLM_VERSION} and no other version; "
                f"earlier jobs of a resumed cell are read on the cluster (section 9)"}
    out(f"Smoke check (prereg section 7): {root}, run tag {SMOKE_TAG}, "
        f"{len(MODEL_ORDER) * len(CELLS)} cell folders")
    ok = True
    for i in range(1, 8):
        if i == 7 and serve_logs is None:
            if version_note and version_note.strip():
                out(f"item 7: checked by hand, not by this script: {version_note.strip()}")
            else:
                out("item 7: NOT CHECKED (pass --serve-logs DIR, or "
                    "--version-checked-by-hand NOTE after reading the banners)")
                ok = False
            continue
        out(f"item {i}: {'PASS' if not fails[i] else 'FAIL'}: {names[i]}")
        for msg in fails[i]:
            out(f"    {msg}")
        if i == 5:
            for name, n in sorted(extra_lines.items()):
                out(f"    extra user-message lines (re-sent requests): {name}: {n}")
        ok = ok and not fails[i]
    for (m, cell), f in sorted(loaded.items()):
        out(f"  rows: {f.spec.name}: {len(f.rows)}")
    out("item 1, job states: not visible in the synced files; read them with the "
        "cluster-ops status script and record them in section 10")
    out("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ------------------------------------------------------------------ grades
@dataclass(frozen=True)
class Graded:
    key: tuple
    domain: str
    variant: int
    frozen: bool
    second: bool
    folded: bool
    reason: str
    layout: str
    at_cap: bool
    completion: int
    is_exception: bool
    readable: bool
    unread: bool            # section 8: an unread final answer


UNREADABLE = frozenset({"no_plan_extracted", "format_parse_fail", "empty_stop",
                        "truncated_empty", "no_room", "exception"})
NO_PLAN_BLOCK = "no plan block"
ONE_OBJECT, PER_LINE, NEITHER = "one JSON object", "one object per line", "neither"


def _norm_action(line: str) -> str:
    """One action as `block_plan` normalises an action line: the parenthesised text
    from the first "(" to the first ")", white space collapsed, lower case."""
    inner = line[line.find("("):]
    inner = inner[: inner.find(")") + 1]
    return " ".join(inner.split()).lower()


def _closing_fence_aside(lines: list[str]) -> list[str]:
    """The non-empty lines of an answer with one final closing code fence left out."""
    return lines[:-1] if lines and lines[-1].strip() == "```" else lines


def unread_final(task: str, response: str, frozen: bool, second: bool, layout: str,
                 at_cap: bool, frozen_plan: tuple[str, ...], frozen_reason: str) -> bool:
    """Section 8, an unread final answer: wrong under both readings, did not stop at
    the output cap, and ends with what looks like its final answer in a place neither
    reader reads. Text read after the leaked-prefix strip.

    Solve, either of two shapes, both with no plan block (`block_plan` is None):
    (ii) the answer has at least one closed fenced block (`e2e_regrade._FENCED_BLOCK_RE`
    on the stripped text, as `block_plan` finds blocks) and the LAST one holds a
    parenthesised action somewhere (`rq1_layout_regrade._ACTION`, searched, not
    matched); counted whatever the frozen reader took.
    (i) the last non-empty line, a closing code fence aside, is one action line (the
    tolerant action pattern of the re-grade, `e2e_regrade._TOLERANT_ACTION_RE`); and
    the frozen reader's plan is not just the run of action lines the answer ends with.
    That run is the longest sequence of consecutive non-empty lines at the end
    (closing fence aside) that each match the pattern. Both the run and the frozen
    plan are normalised as `block_plan` normalises action lines (the parenthesised
    text, white space collapsed, lower case) before they are compared. No frozen plan
    at all counts as unread.
    Simulate: the frozen grader read no trace at all (its reason is
    "format_parse_fail"; a trace that was read and is wrong does not count), layout
    "neither", and the answer, a closing code fence aside and trailing white space
    removed, ends with } or ]."""
    if frozen or second or at_cap:
        return False
    text = strip_leaked_channel_prefix(response or "")
    lines = _closing_fence_aside([ln for ln in text.splitlines() if ln.strip()])
    if task == "solve":
        if RG.block_plan(response) is not None:
            return False
        blocks = _FENCED_BLOCK_RE.findall(text)
        if blocks and RG._ACTION.search(blocks[-1]) is not None:
            return True                                            # shape (ii)
        if not lines or _TOLERANT_ACTION_RE.match(lines[-1]) is None:
            return False
        run: list[str] = []
        for ln in reversed(lines):
            if _TOLERANT_ACTION_RE.match(ln) is None:
                break
            run.insert(0, _norm_action(ln))
        return tuple(_norm_action(a) for a in frozen_plan) != tuple(run)
    tail = "\n".join(lines).rstrip()
    return (frozen_reason == "format_parse_fail" and layout == NEITHER
            and tail.endswith(("}", "]")))


def ok_of(g: G.Delivered) -> bool:
    if not isinstance(g.ok, bool):
        raise Halt(f"a frozen grade is {g.ok!r}, not a bool")
    return g.ok


def plan_of(g: G.Delivered) -> tuple[str, ...]:
    return () if g.plan is None else tuple(g.plan)


def simulate_layout(response: str) -> str:
    """Section 8 descriptive: the whole answer one JSON object (after the registered
    prefix strip and one enclosing code fence), two or more lines that are each one
    JSON object, or neither."""
    text = strip_leaked_channel_prefix(response or "")
    if isinstance(_safe_json_loads(_strip_md_fence(text)), dict):
        return ONE_OBJECT
    n = 0
    for ln in text.splitlines():
        ln = ln.strip().rstrip(",")
        if ln.startswith("{") and ln.endswith("}"):
            try:
                n += isinstance(json.loads(ln), dict)
            except json.JSONDecodeError:
                pass
    return PER_LINE if n >= 2 else NEITHER


class Verdicts:
    """The single verdict(domain, problem, plan) -> bool every solve plan goes through.
    An empty plan is invalid, as the harness's `_validate_model_plan` returns."""

    def __init__(self, fn):
        self._fn = fn
        self.cache: dict = {}

    def __call__(self, d: str, p: str, plan) -> bool:
        plan = tuple(plan)
        if not plan:
            return False
        key = (d, p, plan)
        if key not in self.cache:
            v = self._fn(d, p, plan)
            if not isinstance(v, bool):
                raise Halt(f"validator verdict for {d}/{p} is {v!r}, not a bool")
            self.cache[key] = v
        return self.cache[key]


def live_route(marketplace: Path, domains_dir: Path):
    """The filed re-grade's route: the pddl-validator plugin server in process on
    pddl-pyvalidator 0.1.5, called the way the harness calls `validate_plan`."""
    domains = load_domains(domains_dir)
    vs = C27.load_validator(marketplace)
    loop = asyncio.new_event_loop()

    def fn(d: str, p: str, plan: tuple[str, ...]) -> bool:
        if d not in domains or p not in domains[d]["problems"]:
            raise Halt(f"plan validation: {d}/{p} is not in {domains_dir}")
        raw = loop.run_until_complete(C27.call_tool(vs, "validate_plan", {
            "domain": domains[d]["domain"], "problem": domains[d]["problems"][p],
            "plan": "\n".join(plan)}))
        return validator_verdict(raw, f"{d}/{p}")
    return fn


def validator_verdict(raw, where: str) -> bool:
    """The verdict of one validate_plan answer ({"valid": bool, "status", "report"}).
    Section 3: halts unless `valid` is a real true or false (no truthiness, no error
    answer). For a well-formed answer this is what `_parse_validation_verdict` returns."""
    data = _safe_json_loads(raw) if isinstance(raw, str) else None
    if not isinstance(data, dict) or data.get("error") is True or "valid" not in data:
        raise Halt(f"validator gave no verdict for {where}: {str(raw)[:200]}")
    if not isinstance(data["valid"], bool):
        raise Halt(f"validator verdict for {where} is {data['valid']!r}, not true or false")
    return data["valid"]


def check_validator_env(env: dict, filed_env: dict | None) -> None:
    """Section 3: release 0.1.5, the server file unedited, and the same server file (by
    sha256) as the filed re-grade used."""
    bad = list(C27.check_environment(env))
    if env.get("pyval") != PYVALIDATOR:
        bad.append(f"pddl-pyvalidator is {env.get('pyval')}, registered {PYVALIDATOR}")
    if not isinstance(filed_env, dict) or "validator_server_sha256" not in filed_env:
        bad.append("the filed re-grade records no validator_server_sha256")
    elif env.get("validator_server_sha256") != filed_env["validator_server_sha256"]:
        bad.append(f"validator_server.py sha256 {str(env.get('validator_server_sha256'))[:12]} "
                   f"differs from the filed re-grade's "
                   f"{str(filed_env['validator_server_sha256'])[:12]}")
    if bad:
        raise Halt("validator environment: " + "; ".join(bad))


def table_route(table: dict):
    def fn(d: str, p: str, plan: tuple[str, ...]) -> bool:
        key = (d, p, plan)
        if key not in table:
            raise Halt(f"fixture has no validator verdict for {d}/{p} {list(plan)}")
        return table[key]
    return fn


def check_route(verdict: Verdicts, stored: dict, graded_rows) -> int:
    """Section 3: before any new plan, the route returns the stored verdict for every
    plan the frozen grade used on the Part C solve rows (and on the Part A rows C4
    reads). Returns the number of distinct plans checked."""
    seen = set()
    for r, g in graded_rows:
        if r.task != "solve" or len(plan_of(g)) == 0:
            continue
        key = (r.domain, r.problem, plan_of(g))
        if key in seen:
            continue
        if key not in stored:
            raise Halt(f"no stored verdict for a plan of the frozen grade ({key[:2]})")
        if verdict(*key) != stored[key]:
            raise Halt(f"the validator route disagrees with the stored verdict for {key[:2]} "
                       f"({len(key[2])} actions)")
        seen.add(key)
    return len(seen)


def second_reading(r: S.Row, g: G.Delivered, verdict: Verdicts, gt_cache: dict
                   ) -> tuple[bool, bool, str]:
    """(second reading, case folded, layout) of one row, as the filed re-grade composes
    them (rq1_layout_regrade.main, re-implemented here because that logic is not a
    function there). Solve: when the last closed code block holds a plan
    (`block_plan`), that plan replaces the frozen reading either way; case folded
    sends the deciding plan in lower case when it has a capital. Simulate: a trace
    written one JSON object per line also counts when it equals the answer key."""
    frozen = ok_of(g)
    if r.task == "solve":
        bp = RG.block_plan(r.response)
        plan, second, layout = plan_of(g), frozen, NO_PLAN_BLOCK
        if bp is not None:
            plan, layout = bp
            second = verdict(r.domain, r.problem, plan)
        if len(plan) > 0 and C27.has_upper(list(plan)):
            folded = verdict(r.domain, r.problem, RG.lower(plan))
        else:
            folded = second
        return second, folded, layout
    oracle = oracle_canon_for(gt_cache, {"domain_name": r.domain, "problem_name": r.problem})
    second = frozen or PILOT.line_reader_exact(r.response, oracle)
    return second, second, simulate_layout(r.response)


def grade_rows(pairs, verdict: Verdicts, gt_cache: dict) -> dict:
    """{trial key: Graded} for a list of (Row, frozen Delivered)."""
    out = {}
    for r, g in pairs:
        second, folded, layout = second_reading(r, g, verdict, gt_cache)
        if g.reason not in G.REASONS:
            raise Halt(f"unknown frozen reason {g.reason!r}")
        out[r.trial_key] = Graded(
            key=r.trial_key, domain=r.domain, variant=r.variant, frozen=ok_of(g), second=second,
            folded=folded, reason=g.reason, layout=layout, at_cap=r.done_reason == "length",
            completion=r.tokens.completion, is_exception=r.is_exception,
            readable=g.reason not in UNREADABLE,
            unread=unread_final(r.task, r.response, ok_of(g), second, layout,
                                r.done_reason == "length", plan_of(g), g.reason))
    return out


def frozen_grades(rows, verdict: Verdicts, gt_cache: dict) -> list:
    """The frozen grade of every control row; its solve verdicts come from the route."""
    need = G.solve_plans_to_validate(rows)
    table = {k: verdict(*k) for k in sorted(need)}
    return [(r, G.grade(r, gt_cache, table)) for r in rows]


# ------------------------------------------------------------------ the rerun (C3, C4)
@dataclass
class Rerun:
    part_c: dict          # {model: {task: {key: (Row, Delivered)}}}
    part_a: dict          # plain arm only, same shape
    stored: dict          # stored validator verdicts of the frozen readout
    readout: dict         # the filed readout (e1, e2)
    regrade: dict         # the filed layout re-grade (cells)
    gt_cache: dict
    note: str


def _split(rows, grades_of) -> dict:
    out = {t: {} for t in TASKS}
    for r in rows:
        if r.task in TASKS:
            out[r.task][r.trial_key] = (r, grades_of(r))
    return out


def load_rerun_live(args) -> Rerun:
    """Part C and Part A through `rq1_metrics.load_rerun_cells`: the frozen package,
    the pinned ground truth, and grades that reproduce the filed readout or halt."""
    cells, grades, gt_cache = R1.load_rerun_cells(args)
    stored = {(e["domain"], e["problem"], tuple(e["plan"])): e["valid"]
              for e in json.loads(args.plan_verdicts.read_text())}
    part_c, part_a = {}, {}
    for m in MODEL_ORDER:
        part_c[m] = _split(cells["rerun_c"][m].rows, lambda r: grades[(r.cell, r.trial_key)])
        part_a[m] = _split([r for r in cells["rerun_a"][m].rows if r.arm == "plain"],
                           lambda r: grades[(r.cell, r.trial_key)])
    return Rerun(part_c=part_c, part_a=part_a, stored=stored,
                 readout=json.loads(args.readout_json.read_text()),
                 regrade=json.loads(args.regrade_json.read_text()), gt_cache=gt_cache,
                 note=f"delivered rerun at {args.rerun_root}")


def fixture_domains(root: Path) -> frozenset:
    """Fixture mode reads the fixture's own domains only (design.json), so real cell
    folders cannot be fed through it."""
    names = json.loads((root / "design.json").read_text()).get("domains")
    if not isinstance(names, list) or not names:
        raise Halt("fixture mode: design.json lists no domains")
    return frozenset(names)


def load_rerun_fixture(root: Path, design: Design, domains: frozenset) -> Rerun:
    gt_cache = json.loads((root / "gt_cache.json").read_text())
    stored = RUN.fixture_verdicts(root)
    part_c, part_a = {}, {}
    for m in MODEL_ORDER:
        for part, out in (("C", part_c), ("A", part_a)):
            spec = rerun_spec(design, m, part)
            f = read_folder(root / "rerun", spec, m, part, domains)
            check_void(f)
            graded = {r.trial_key: G.grade(r, gt_cache, stored) for r in f.rows}
            out[m] = _split(f.rows, lambda r: graded[r.trial_key])
    return Rerun(part_c=part_c, part_a=part_a, stored=stored,
                 readout=json.loads((root / "filed_readout.json").read_text()),
                 regrade=json.loads((root / "filed_regrade.json").read_text()),
                 gt_cache=gt_cache, note="synthetic fixture")


def check_filed_readout(rr: Rerun) -> None:
    """Section 4: the frozen grades of the rerun rows reproduce the filed readout
    (E1 delivered counts of the plain tool arm, E2 unaided rates)."""
    e1 = {(e["model"], e["task"], e["arm"]): e for e in rr.readout["e1"]}
    e2 = {(e["model"], e["task"]): e for e in rr.readout["e2"]}
    bad = []
    for m in MODEL_ORDER:
        for t in TASKS:
            c = [ok_of(g) for _, g in rr.part_c[m][t].values()]
            a = [ok_of(g) for _, g in rr.part_a[m][t].values()]
            f1 = e1[(m, t, "plain")]
            if (sum(a), len(a)) != (f1["delivered_k"], f1["n"]):
                bad.append(f"E1 {m}/{t}: {sum(a)}/{len(a)} vs {f1['delivered_k']}/{f1['n']}")
            if abs(100 * sum(c) / len(c) - e2[(m, t)]["a_pct"]) > 1e-9:
                bad.append(f"E2 unaided {m}/{t}: {100 * sum(c) / len(c):.4f} vs "
                           f"{e2[(m, t)]['a_pct']:.4f}")
    if bad:
        raise Halt("the rerun's frozen grades do not reproduce the filed readout:\n  "
                   + "\n  ".join(bad))


def check_filed_regrade(rr: Rerun, graded_c: dict, graded_a: dict) -> None:
    """Section 4: the second reading of the rerun rows reproduces the filed re-grade
    (tools/reanalysis/out/rq1_layout_regrade.json: frozen_k, tolerant_k, folded_k)."""
    filed = {(c["tag"], c["task"], c["arm"]): c for c in rr.regrade["cells"]}
    bad = []
    for m in MODEL_ORDER:
        for t in TASKS:
            for arm, src in (("unaided", graded_c), ("plain", graded_a)):
                gs = list(src[m][t].values())
                got = (len(gs), sum(x.frozen for x in gs), sum(x.second for x in gs),
                       sum(x.folded for x in gs))
                f = filed[(m, t, arm)]
                want = (f["n"], f["frozen_k"], f["tolerant_k"], f["folded_k"])
                if got != want:
                    bad.append(f"{m}/{t}/{arm}: (n, frozen, second, folded) {got} vs filed {want}")
    if bad:
        raise Halt("the second reading of the rerun rows does not reproduce the filed "
                   "re-grade:\n  " + "\n  ".join(bad))


# ------------------------------------------------------------------ statistics
def boot(values: list[float], doms: list[str], k: int, what: str) -> ST.Boot:
    """The frozen domain-cluster bootstrap at 95%, k asserted."""
    b = ST.cluster_bootstrap(values, doms, LEVEL, k, what)
    _check(b.k == k and b.level == LEVEL, f"{what}: k = {k} clusters at 95%")
    return b


def bdict(b: ST.Boot) -> dict:
    return dataclasses.asdict(b)


def rate(gs: list[Graded], reading: str, k: int, what: str) -> dict:
    vals = [getattr(x, reading) for x in gs]
    b = boot([float(v) for v in vals], [x.domain for x in gs], k, what)
    return {**bdict(b), "right": sum(vals), "n": len(vals)}


def paired(xs: dict, ys: dict, reading: str, k: int, what: str) -> dict:
    """y minus x over the shared trial keys, in points, with interval and sign-flip p."""
    keys = sorted(set(xs) & set(ys))
    unpaired = len(set(xs) ^ set(ys))
    diffs = [int(getattr(ys[q], reading)) - int(getattr(xs[q], reading)) for q in keys]
    doms = [xs[q].domain for q in keys]
    b = boot([float(v) for v in diffs], doms, k, what)
    p = ST.signflip_exact_p(ST.domain_sums(diffs, doms))
    return {**bdict(b), "n_pairs": len(keys), "unpaired": unpaired, "p": p,
            "gained": sum(d == 1 for d in diffs), "lost": sum(d == -1 for d in diffs)}


def contrast_label(c: dict) -> str:
    """Section 4, C1 to C3: criterion met (the whole interval in [-5, +5], endpoints
    included); a difference is shown (the interval excludes 0), "(not after Holm)"
    when the Holm-adjusted p is 0.05 or more; unresolved otherwise. Both labels can
    hold at once."""
    parts = []
    if c["lo"] >= -MARGIN and c["hi"] <= MARGIN:
        parts.append("criterion met")
    if c["lo"] > 0 or c["hi"] < 0:
        parts.append("a difference is shown" if c["p_holm"] < HOLM_ALPHA
                     else "a difference is shown (not after Holm)")
    return "; ".join(parts) if parts else "unresolved"


def c4_label(c: dict) -> str:
    """Section 4, C4: tools ahead (interval above 0), no tools ahead (below 0), no
    difference shown otherwise; no margin. "(not after Holm)" as for C1 to C3."""
    if c["lo"] > 0:
        lab = "tools ahead"
    elif c["hi"] < 0:
        lab = "no tools ahead"
    else:
        return "no difference shown"
    return lab if c["p_holm"] < HOLM_ALPHA else lab + " (not after Holm)"


def met(c: dict) -> bool:
    return c["lo"] >= -MARGIN and c["hi"] <= MARGIN


def rise(c: dict) -> bool:
    return c["lo"] > 0


def fall(c: dict) -> bool:
    return c["hi"] < 0


def ci_text(c: dict) -> str:
    return f"{c['est']:+.1f} [{c['lo']:+.1f}, {c['hi']:+.1f}]"


R_SENTENCES = {
    "C1": {
        "a": "removing the reference to the schema did not move the unaided baseline by "
             "more than 5 points",
        "b": "the wrong reference lowered the unaided baseline",
        "c": "the wrong reference changed how the answers were laid out, and the grader did "
             "not read that layout; what the models wrote did not change by more than the "
             "second reading shows",
        "d": "a fall, reported as it is: the reference, wrong as it was, did not cost the "
             "model anything on that task",
        "e": "unresolved",
    },
    "C2": {
        "a": "stating the answer format did not move the unaided baseline by more than 5 "
             "points",
        "b": "stating the answer format raises the unaided baseline, and not through layout "
             "alone",
        "c": "stating the answer format raises the frozen grade through layout: the answers "
             "come in a layout the grader reads; what the models wrote did not change by "
             "more than the second reading shows",
        "d": "a fall, reported as it is: stating the answer format lowered the unaided "
             "baseline on that task",
        "e": "unresolved",
    },
}
WITH_INTERVALS = ("b", "e")   # the cases the prereg gives "with both estimates and intervals"


def holm_notes(*cs: tuple[str, dict]) -> list[str]:
    """Section 4: the note beside a sentence that rests on a contrast whose interval
    excludes 0 but whose Holm-adjusted p is 0.05 or more."""
    return [f"{r} reading: {c['label']}" for r, c in cs if "(not after Holm)" in c["label"]]


def r12_reading(name: str, fz: dict, sc: dict) -> dict:
    """Section 5, "How R1 and R2 are read": the two labels always; a sentence for
    every case (a) to (d) whose condition holds, in the listed order; (e)
    "unresolved" only when none holds. "A rise" = the interval is above 0, "a fall"
    = below 0. R1 is C1, R2 is C2, each with its own sentences."""
    est = f"frozen {ci_text(fz)}, second reading {ci_text(sc)}"
    holds = {"a": met(fz) and met(sc), "b": rise(fz) and rise(sc),
             "c": rise(fz) and not rise(sc), "d": fall(fz)}
    cases = [k for k in "abcd" if holds[k]] or ["e"]
    sentences = [R_SENTENCES[name][k] + (f" ({est})" if k in WITH_INTERVALS else "")
                 for k in cases]
    return {"cases": cases, "sentences": sentences,
            "labels": {"frozen": f"{fz['label']} ({ci_text(fz)})",
                       "second": f"{sc['label']} ({ci_text(sc)})"},
            "holm_notes": holm_notes(("frozen", fz), ("second", sc))}


def r3_reading(fz: dict) -> dict:
    """Section 5, R3 (C3, frozen grade)."""
    if met(fz):
        return {"moved": False, "levels_beside_part_c": True,
                "sentence": "the setup is taken to reproduce Part C there"}
    return {"moved": True, "levels_beside_part_c": False,
            "sentence": f"the setup moved between Part C and the control for this model and "
                        f"task (frozen {ci_text(fz)}); the levels of the control are not set "
                        f"beside the levels of Part C here"}


def r4_reading(fz: dict, sc: dict, moved: bool, control_dates: str) -> dict:
    """Section 5, R4 (C4, both readings, with the dates of the two runs)."""
    s = (f"frozen grade: {fz['label']} ({ci_text(fz)}); second reading: {sc['label']} "
         f"({ci_text(sc)}); Part A: {PART_A_DATES}; the control: {control_dates}")
    if moved and "across a setup that moved" not in s:
        s += "; across a setup that moved"
    return {"sentence": s, "across_a_setup_that_moved": moved,
            "holm_notes": holm_notes(("frozen", fz), ("second", sc))}


# ------------------------------------------------------------------ analysis
def analyse(design: Design, control: dict, rr: Rerun, verdict: Verdicts, mode: str,
            control_dates: str, audit: dict, audit_notes: dict) -> dict:
    k = design.k_domains
    # Part C and Part A: frozen grades must reproduce the filed readout.
    check_filed_readout(rr)
    check_keys_equal_part_c(control, rr.part_c)
    # The route returns the stored verdicts before any new plan is validated.
    checked = check_route(verdict, rr.stored,
                          [rg for m in MODEL_ORDER for src in (rr.part_c, rr.part_a)
                           for rg in src[m]["solve"].values()])
    # Grades, both readings.
    g_ctrl: dict = {}
    for m in MODEL_ORDER:
        for cell in CELLS:
            graded = grade_rows(frozen_grades(control[m][cell].rows, verdict, rr.gt_cache),
                                verdict, rr.gt_cache)
            for t in TASKS:
                g_ctrl[(m, cell, t)] = {q: x for q, x in graded.items() if q[0] == t}
    g_c = {m: {t: grade_rows(rr.part_c[m][t].values(), verdict, rr.gt_cache) for t in TASKS}
           for m in MODEL_ORDER}
    g_a = {m: {t: grade_rows(rr.part_a[m][t].values(), verdict, rr.gt_cache) for t in TASKS}
           for m in MODEL_ORDER}
    check_filed_regrade(rr, g_c, g_a)
    for key, gs in g_ctrl.items():
        _check(len(gs) == design.per_task_cell, f"{key}: {design.per_task_cell} trials")

    # Rates.
    rates = []
    for m in MODEL_ORDER:
        for t in TASKS:
            for cell, gs in [(c, g_ctrl[(m, c, t)]) for c in CELLS] + [
                    ("Part C", g_c[m][t]), ("Part A", g_a[m][t])]:
                vals = list(gs.values())
                e = {"model": m, "task": t, "cell": cell, "n": len(vals)}
                for rd in READINGS + ("folded",):
                    e[rd] = rate(vals, rd, k, f"rate {m}/{t}/{cell}/{rd}")
                rates.append(e)
    by_rate = {(e["model"], e["task"], e["cell"]): e for e in rates}

    # Contrasts C1 to C4, both readings; Holm across the six of one name and reading.
    sides = {"C1": ("O", "A"), "C2": ("O", "B"), "C3": ("Part C", "O"), "C4": ("B", "Part A")}

    def src(m, t, cell):
        if cell == "Part C":
            return g_c[m][t]
        if cell == "Part A":
            return g_a[m][t]
        return g_ctrl[(m, cell, t)]

    contrasts = []
    for name in CONTRASTS:
        x, y = sides[name]
        for rd in READINGS:
            fam = []
            for m in MODEL_ORDER:
                for t in TASKS:
                    c = paired(src(m, t, x), src(m, t, y), rd, k, f"{name} {m}/{t}/{rd}")
                    _check(c["n_pairs"] == design.per_task_cell,
                           f"{name} {m}/{t}: {design.per_task_cell} pairs")
                    fam.append({"name": name, "reading": rd, "model": m, "task": t, **c})
            adj = ST.holm({(e["model"], e["task"]): e["p"] for e in fam}, HOLM_FAMILY)
            for e in fam:
                e["p_holm"] = adj[(e["model"], e["task"])]
                e["label"] = c4_label(e) if name == "C4" else contrast_label(e)
            contrasts.extend(fam)
    _check(len(contrasts) == N_CONTRASTS * len(READINGS), "24 contrasts under two readings")
    by_c = {(e["name"], e["reading"], e["model"], e["task"]): e for e in contrasts}

    # Registered readings and the rule-5 flag. Where R3 says the setup moved, the C4
    # labels themselves carry the words (R4).
    for m in MODEL_ORDER:
        for t in TASKS:
            if r3_reading(by_c[("C3", "frozen", m, t)])["moved"]:
                for rd in READINGS:
                    by_c[("C4", rd, m, t)]["label"] += "; across a setup that moved"
    readings = []
    for m in MODEL_ORDER:
        for t in TASKS:
            r3 = r3_reading(by_c[("C3", "frozen", m, t)])
            b = by_rate[(m, t, "B")]
            gap = b["frozen"]["est"] - b["second"]["est"]
            readings.append({
                "model": m, "task": t,
                "R1": r12_reading("C1", by_c[("C1", "frozen", m, t)], by_c[("C1", "second", m, t)]),
                "R2": r12_reading("C2", by_c[("C2", "frozen", m, t)], by_c[("C2", "second", m, t)]),
                "R3": r3,
                "R4": r4_reading(by_c[("C4", "frozen", m, t)], by_c[("C4", "second", m, t)],
                                 r3["moved"], control_dates),
                "rule5": {"b_frozen": b["frozen"]["est"], "b_second": b["second"]["est"],
                          "gap": gap, "quote_both": abs(gap) > QUOTE_BOTH_POINTS},
            })

    # Tripwires (section 8).
    fired = {}
    for t in TASKS:
        for rd in READINGS:
            ks = {by_rate[(m, t, c)][rd]["right"] for m in MODEL_ORDER for c in CELLS}
            if len(ks) == 1:
                fired[f"T1:{t}:{rd}"] = (f"the count of right answers on {t} is the same in "
                                         f"all nine cells under the {READINGS_SHORT[rd]} "
                                         f"reading ({ks.pop()} of {design.per_task_cell})")
    for m in MODEL_ORDER:
        for t in TASKS:
            d = by_rate[(m, t, "O")]["frozen"]["est"] - by_rate[(m, t, "Part C")]["frozen"]["est"]
            if abs(d) > TRIPWIRE_POINTS:
                fired[f"T2:{m}:{t}"] = (f"cell O of {m}/{t} is {d:+.1f} points from Part C "
                                        f"(frozen grade)")
        for cell in CELLS:
            for t in TASKS:
                if not any(x.readable for x in g_ctrl[(m, cell, t)].values()):
                    fired[f"T3:{m}:{cell}:{t}"] = (f"cell {cell} of {m}: the frozen grader can "
                                                   f"read no answer at all on {t}")
                # The fourth tripwire guards cell B only (the reported baseline);
                # for O and A the count is reported and never halts.
                n_unread = sum(x.unread for x in g_ctrl[(m, cell, t)].values())
                if cell == "B" and n_unread > UNREAD_FRAC * design.per_task_cell:
                    fired[f"T4:{m}:{cell}:{t}"] = (
                        f"cell {cell} of {m}, {t}: {n_unread} unread final answers of "
                        f"{design.per_task_cell} (more than {100 * UNREAD_FRAC:.0f}%)")
    unaudited = {i: v for i, v in fired.items() if i not in audit_notes}
    if unaudited:
        raise Halt("readout tripwire(s) fired (section 8); audit before any readout "
                   "sentence:\n  " + "\n  ".join(f"{i}: {v}" for i, v in unaudited.items()))
    extra = set(audit_notes) - set(fired)
    if extra:
        raise Halt(f"audit notes for tripwires that did not fire: {sorted(extra)}")

    secondary = secondary_tables(design, g_ctrl)
    unread_rerun = [{"model": m, "task": t, "part": part,
                     "unread": sum(x.unread for x in src[m][t].values())}
                    for m in MODEL_ORDER for t in TASKS
                    for part, src in (("Part C", g_c), ("Part A", g_a))]
    corpus = [{"cell": f.spec.name, "rows": len(f.rows), "torn_lines": f.torn_lines,
               "exception_rows": f.exception_rows, "infra_rows": f.infra_rows,
               "storage_cut_accepted": len(f.storage_cut)}
              for m in MODEL_ORDER for f in control[m].values()]
    return {
        "mode": mode, "package_sha256": package_sha256(), "design": dataclasses.asdict(design),
        "control_dates": control_dates, "part_a_dates": PART_A_DATES,
        "rerun": rr.note, "corpus": corpus, "audit": audit,
        "route_checked_plans": checked, "validated_plans": len(verdict.cache),
        "rates": rates, "contrasts": contrasts, "readings": readings,
        "secondary": secondary, "unread_rerun": unread_rerun, "tripwires_audited": {i: {"fired": fired[i],
                                                          "note": audit_notes[i]}
                                                      for i in fired},
    }


READINGS_SHORT = {"frozen": "frozen", "second": "second"}


def secondary_tables(design: Design, g_ctrl: dict) -> list[dict]:
    """Section 8, descriptive: by wording, layout, output cap, tokens, reasons,
    moves from O to A and O to B, the case-folded column."""
    out = []
    for (m, cell, t), gs in g_ctrl.items():
        vals = list(gs.values())
        e = {"model": m, "task": t, "cell": cell, "n": len(vals),
             "by_wording": {str(v): {rd: sum(getattr(x, rd) for x in vals if x.variant == v)
                                     for rd in READINGS}
                            for v in WORDINGS},
             "per_wording_n": {str(v): sum(x.variant == v for x in vals) for v in WORDINGS},
             "layout": dict(sorted(Counter(x.layout for x in vals).items())),
             "at_output_cap": sum(x.at_cap for x in vals),
             "mean_answer_tokens": sum(x.completion for x in vals) / len(vals),
             "exception_rows": sum(x.is_exception for x in vals),
             "readable": sum(x.readable for x in vals),
             "failure_reasons": dict(sorted(Counter(x.reason for x in vals
                                                    if x.frozen is False).items())),
             "folded_k": sum(x.folded for x in vals),
             "unread_final_answers": sum(x.unread for x in vals)}
        if cell != "O":
            o = g_ctrl[(m, "O", t)]
            e["moves_from_O"] = {f"{a} -> {b}": n for (a, b), n in sorted(
                Counter((o[q].reason, gs[q].reason) for q in sorted(gs)).items())}
        out.append(e)
    return out


# ------------------------------------------------------------------ markdown
def render(res: dict) -> str:
    def cell_rate(r: dict) -> str:
        return f"{r['right']}/{r['n']}, {r['est']:.1f} [{r['lo']:.1f}, {r['hi']:.1f}]"

    n = res["design"]["per_task_cell"]
    common = (f"n = {n} trials per model, task and cell (three wordings, "
              f"{res['design']['k_domains']} domains); 24 contrasts, each under two readings")
    L = [f"*Generated by `tools/reanalysis/control_prompt_fix.py` ({res['mode']} mode, package "
         f"hash `{res['package_sha256'][:12]}...`). The registered analysis of "
         f"`development/reference/control_prompt_fix_prereg.md`. Three models, thinking off, "
         f"no tools, solve and simulate. Cell O sends the registered system text of Part C, "
         f"cell A the same text with the reference to the schema removed, cell B the answer "
         f"format stated; nothing else differs. Dates: the control {res['control_dates']}; "
         f"Part A of the rerun {res['part_a_dates']}. \"Frozen grade\" is the registered "
         f"measure (the frozen delivered grader of the rerun). \"Second reading\" is the "
         f"layout-tolerant reading of the filed re-grade: on solve the plan in the last code "
         f"block decides when that block holds a plan; on simulate a trace written one JSON "
         f"object per line also counts when it equals the answer key. Intervals are 95% "
         f"domain-cluster bootstrap. {common}. Solve plans checked against the stored verdicts "
         f"before any new plan was validated: {res['route_checked_plans']}; plans validated "
         f"in all: {res['validated_plans']}.*", ""]
    if res["tripwires_audited"]:
        L.append("**Tripwires that fired and were audited:** " + "; ".join(
            f"{i}: {v['fired']} (audit: {v['note']})" for i, v in res["tripwires_audited"].items()))
        L.append("")

    # R3: where the setup moved, the control's levels are not set beside Part C's.
    moved = {(e["model"], e["task"]) for e in res["readings"] if e["R3"]["moved"]}
    L.append("#### Control prompt fix: delivered right per cell, both readings")
    L.append("")
    L.append(f"Reading: frozen grade and second reading side by side; case folded is "
             f"descriptive (no registered reading uses it). Cell B is the no-tools baseline the "
             f"paper reports on these two tasks; cell O is the anchor of C1 to C3 (section 6). "
             f"{common}."
             + (" Part C is left out of this table for " + ", ".join(
                 f"{model_name(m)} {t}" for m, t in sorted(moved))
                + ", where R3 says the setup moved." if moved else ""))
    L.append("")
    L.append(md_table(
        ["model", "task", "cell", "trials", "frozen grade", "second reading",
         "case folded (descriptive)"],
        [[model_name(r["model"]), r["task"], CELL_WORDS.get(r["cell"], r["cell"]), r["n"],
          cell_rate(r["frozen"]), cell_rate(r["second"]),
          cell_rate(r["folded"]) if r["task"] == "solve" else "–"] for r in res["rates"]
         if not (r["cell"] == "Part C" and (r["model"], r["task"]) in moved)]))
    L.append("")
    for rd in READINGS:
        L.append(f"#### Control prompt fix: contrasts C1 to C4, {READING_WORDS[rd]}")
        L.append("")
        L.append(f"Reading: {READING_WORDS[rd]}. Points, paired on the trial key; {common}. "
                 f"Margin 5 points for C1 to C3 (endpoints included); none for C4. The sign-flip "
                 f"p is exact over the 20 domains, Holm-adjusted across the six contrasts of the "
                 f"same name and reading.")
        L.append("")
        L.append(md_table(
            ["contrast", "model", "task", "pairs", "difference [95% interval]", "reading",
             "sign-flip p", "Holm-adjusted p", "unpaired"],
            [[f"{c['name']} ({CONTRAST_WORDS[c['name']]})", model_name(c["model"]), c["task"],
              c["n_pairs"], ci_text(c), c["label"], f"{c['p']:.3g}", f"{c['p_holm']:.3g}",
              c["unpaired"]]
             for c in res["contrasts"] if c["reading"] == rd]))
        L.append("")
    L.append("#### Control prompt fix: registered readings R1 to R4 and the reporting rule")
    L.append("")
    L.append(f"Readings as registered in section 5, per model and task, never pooled. R1 and R2 "
             f"give both labels, then a sentence for every case (a) to (d) that holds, in order; "
             f"(e) only when none holds. {common}.")
    L.append("")
    def with_notes(s: str, notes: list[str]) -> str:
        return s + (" [note: " + "; ".join(notes) + "]" if notes else "")

    rows = []
    for e in res["readings"]:
        for r in ("R1", "R2"):
            x = e[r]
            s = (f"labels: frozen grade {x['labels']['frozen']}; second reading "
                 f"{x['labels']['second']}. "
                 + " ".join(f"({k}) {txt}." for k, txt in zip(x["cases"], x["sentences"])))
            rows.append([model_name(e["model"]), e["task"], r, with_notes(s, x["holm_notes"])])
        rows.append([model_name(e["model"]), e["task"], "R3", e["R3"]["sentence"]])
        rows.append([model_name(e["model"]), e["task"], "R4",
                     with_notes(e["R4"]["sentence"], e["R4"]["holm_notes"])])
        f5 = e["rule5"]
        rows.append([model_name(e["model"]), e["task"], "section 6 rule 5",
                     f"cell B frozen {f5['b_frozen']:.1f}, second reading {f5['b_second']:.1f}: "
                     + ("the two differ by more than 5 points; the text gives both figures"
                        if f5["quote_both"] else "the text quotes the frozen grade")])
    L.append(md_table(["model", "task", "reading", "what the data say"], rows))
    L.append("")
    L.append("#### Control prompt fix: by wording (secondary, descriptive)")
    L.append("")
    L.append(f"Reading: both. The count of right answers by wording, "
             f"{res['secondary'][0]['per_wording_n']['11']} trials each; {common}.")
    L.append("")
    L.append(md_table(
        ["model", "task", "cell"] + [f"v{v}: count right, frozen / second" for v in WORDINGS],
        [[model_name(s["model"]), s["task"], CELL_WORDS[s["cell"]]]
         + [f"{s['by_wording'][str(v)]['frozen']} / {s['by_wording'][str(v)]['second']}"
            for v in WORDINGS] for s in res["secondary"]]))
    L.append("")
    L.append("#### Control prompt fix: answer layout, length and failure reasons "
             "(secondary, descriptive)")
    L.append("")
    L.append(f"Reading: frozen grade for the reasons; layout as the second reading sees it. "
             f"An unread final answer is wrong under both readings, did not stop at the "
             f"output cap, and ends with what looks like its final answer where neither reader "
             f"reads it (solve: no plan block, the last line, a closing fence aside, is an "
             f"action line, and the frozen reader's plan is not just the action lines the "
             f"answer ends with, or the last closed block is not a plan block but holds an "
             f"action; simulate: the frozen grader read no trace, layout neither, "
             f"the answer ends with a closing brace or bracket). The fourth tripwire applies to cell B only. The rerun's rows: "
             + "; ".join(f"{model_name(u['model'])} {u['task']} {u['part']} {u['unread']}"
                         for u in res["unread_rerun"]) + f". {common}.")
    L.append("")
    L.append(md_table(
        ["model", "task", "cell", "trials", "layout", "stopped at the output cap",
         "mean answer tokens", "exception rows", "unread final answers",
         "frozen reason of each failure"],
        [[model_name(s["model"]), s["task"], CELL_WORDS[s["cell"]], s["n"],
          "; ".join(f"{k} {v}" for k, v in s["layout"].items()), s["at_output_cap"],
          f"{s['mean_answer_tokens']:.0f}", s["exception_rows"], s["unread_final_answers"],
          "; ".join(f"{k} {v}" for k, v in s["failure_reasons"].items()) or "–"]
         for s in res["secondary"]]))
    L.append("")
    L.append("#### Control prompt fix: how each trial moved from O (secondary, descriptive)")
    L.append("")
    L.append(f"Reading: frozen grade reason in O, then in A or B, on the same trial; only trials "
             f"whose reason changed are listed (the JSON output has every pair). {common}.")
    L.append("")
    L.append(md_table(
        ["model", "task", "move", "frozen reason in O -> in the cell", "trials"],
        [[model_name(s["model"]), s["task"], f"O to {s['cell']}", k, v]
         for s in res["secondary"] if "moves_from_O" in s for k, v in s["moves_from_O"].items()
         if k.split(" -> ")[0] != k.split(" -> ")[1]] or [["–", "–", "–", "no trial moved", 0]]))
    L.append("")
    L.append("#### Control prompt fix: corpus")
    L.append("")
    L.append(f"Rows per cell folder as read by the frozen loader. {common}.")
    L.append("")
    L.append(md_table(
        ["cell folder", "rows", "exception rows (kept, graded as they are)",
         "cut by storage (accepted: stopped at the output cap)", "torn lines"],
        [[c["cell"], c["rows"], c["exception_rows"], c["storage_cut_accepted"], c["torn_lines"]]
         for c in res["corpus"]]))
    L.append("")
    return "\n".join(L) + "\n"


def write_pair(out: Path, js: str, md: str) -> None:
    """Both files, or neither (temporary names, then rename)."""
    final = [out / "control_prompt_fix.json", out / "control_prompt_fix.md"]
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
    design = Design(name="fixture", per_task_cell=d["per_task_cell"], per_folder=d["per_folder"],
                    per_wording=d["per_wording"], per_task_wording=d["per_task_wording"],
                    k_domains=d["k_domains"])
    if design.per_folder == REGISTERED.per_folder:
        raise Halt("fixture mode refuses a registered-size design")
    check_design(design, registered=False)
    return design


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    R1.add_data_args(ap)
    ap.add_argument("--print-package-hash", action="store_true")
    ap.add_argument("--fixture", type=Path, help="synthetic fixture root (tests only)")
    ap.add_argument("--smoke-check", type=Path, metavar="ROOT")
    ap.add_argument("--control-root", type=Path)
    ap.add_argument("--r2-models", default="",
                    help=f"comma-separated model tags whose cells were rerun under {R2_TAG}")
    ap.add_argument("--marketplace", type=Path,
                    help="the pddl-copilot checkout (required in live mode)")
    ap.add_argument("--regrade-json", type=Path,
                    default=Path(__file__).resolve().parent / "out" / "rq1_layout_regrade.json")
    ap.add_argument("--serve-logs", type=Path,
                    help="folder holding the <job>-vllm-<model>.log serve logs")
    ap.add_argument("--version-checked-by-hand", metavar="NOTE",
                    help="item 7 checked by hand: a note saying how (recorded in the output)")
    ap.add_argument("--control-dates", help="the dates of the control (prereg section 9)")
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
        return smoke_check(args.smoke_check, args.serve_logs, args.version_checked_by_hand)
    try:
        check_constants()
        audited = {x for x in args.audited_tripwires.split(",") if x}
        try:
            notes = RUN.load_audit_notes(args.audit_notes, audited)
        except RUN.Halt as e:
            raise Halt(str(e)) from e
        if not (args.control_dates and args.control_dates.strip()):
            raise Halt("--control-dates is required (R4 states the dates of both runs)")
        if args.fixture is not None:
            root = args.fixture
            if not (root / FIXTURE_MARKER).exists():
                raise Halt(f"fixture mode: {root} has no {FIXTURE_MARKER} marker")
            if args.numbers:
                raise Halt("--numbers is for live mode only")
            if args.out.resolve() == (Path(__file__).resolve().parent / "out").resolve():
                raise Halt("fixture mode needs its own --out (not tools/reanalysis/out)")
            design = fixture_design(root)
            domains = fixture_domains(root)
            control_root = root / "control"
            tags, r2_found = resolve_tags(control_root, design, args.r2_models, domains)
            control = load_control(control_root, design, tags, domains)
            shared = check_pairing(control, design)
            audit = audit_control(control_root, control,
                                  None if args.version_checked_by_hand else root / "serve_logs",
                                  args.version_checked_by_hand)
            rr = load_rerun_fixture(root, design, domains)
            verdict = Verdicts(table_route(RUN.fixture_verdicts(root / "route")))
            env = {"validator": "fixture table"}
            mode = "fixture"
        else:
            if args.i_have_frozen != package_sha256():
                raise Halt("refusing to read the control: --i-have-frozen does not match the "
                           "package sha256 (freeze first, prereg section 7 and 9)")
            if args.marketplace is None:
                raise Halt("live mode requires --marketplace (the pddl-copilot checkout)")
            R1.fill_data_args(args)
            design = REGISTERED
            check_design(design, registered=True)
            control_root = args.control_root or args.results / RUN_TAG
            tags, r2_found = resolve_tags(control_root, design, args.r2_models)
            control = load_control(control_root, design, tags)
            shared = check_pairing(control, design)
            audit = audit_control(control_root, control, args.serve_logs,
                                  args.version_checked_by_hand)
            try:
                env = C27.environment(args.marketplace)
            except (OSError, subprocess.CalledProcessError) as e:
                raise Halt(f"--marketplace {args.marketplace}: cannot read the validator "
                           f"environment ({type(e).__name__})") from e
            check_validator_env(env, json.loads(args.regrade_json.read_text()).get("environment"))
            rr = load_rerun_live(args)
            verdict = Verdicts(live_route(args.marketplace, args.domains_dir))
            mode = "live"
        res = analyse(design, control, rr, verdict, mode, args.control_dates.strip(),
                      audit, notes)
        res["shared_keys"] = shared
        res["environment"] = env
        res["run_tags"] = tags
        res["first_run_void"] = r2_found
        try:
            md = render(res)
            js = json.dumps(res, indent=1, sort_keys=True, default=list) + "\n"
        except Exception as e:  # noqa: BLE001 -- any render failure is a named HALT
            raise Halt(f"render failed ({type(e).__name__}: {e}); nothing written") from e
        write_pair(args.out, js, md)
    except (Halt, R1.Halt, RUN.Halt, S.SchemaError, C.RegisteredCheckFailed) as e:
        print(f"HALT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}/control_prompt_fix.{{json,md}}")
    if args.numbers:
        changed = write_numbers(REPO / "development" / "NUMBERS.md", NUMBERS_TAG, md)
        print("NUMBERS.md " + ("updated" if changed else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
