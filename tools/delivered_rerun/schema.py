"""Typed load boundary (freeze gate 1).

Every row of every corpus this analysis reads goes through `load_cell()`,
which parses each `trials.jsonl` line into a frozen `Row` and raises
`SchemaError` on:

* an unknown enum value (task, failure_reason, done_reason, think,
  tool_filter, prompt_style, plan_label, variant);
* a missing key, an extra key, or a value of the wrong type;
* a key read from the wrong layer: a `tokens.ctx_*` field at the result top
  level, a field that only the rerun schema has (`response_truncated_by_storage`)
  in a canonical row or vice versa, or a resume key that disagrees with the
  result it indexes;
* a row whose model / condition / prompt_style does not belong to the cell
  directory it was read from;
* a duplicate trial key.

Rows that the prereg says must be *refused* raise `RefusedRow` (a SchemaError):
a row cut by storage (§2 delta 1, registered expectation zero), and a
no-room or clipped row whose recorded sizes break the 16,384-token window.

Estimator code downstream reads only `Row` attributes; there is no dict access
on a grade field after this module.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from pddl_eval.runner import TaskResult
from pddl_eval import scoring

from . import constants as C


class SchemaError(Exception):
    """A row or corpus does not match the registered schema. Never caught."""


class RefusedRow(SchemaError):
    """A row the prereg says may not enter the analysis."""


# ------------------------------------------------------------------ enums
TASKS = frozenset(C.TASKS)
FAILURE_REASONS = frozenset(
    v for k, v in vars(scoring).items() if k.startswith("FR_") and isinstance(v, str))
assert "ok" in FAILURE_REASONS and "exception" in FAILURE_REASONS
assert C.EXCEPTION_REASONS <= FAILURE_REASONS
# "abort" is never on disk (runner drops infra rows); "content_filter" never
# observed. Anything outside this set is a schema surprise.
DONE_REASONS = frozenset({"stop", "length", "tool_calls", ""})
PLAN_LABELS = frozenset({f"v{i}" for i in range(1, 6)} | {f"b{i}" for i in range(1, 6)})
_PROBLEM_RE = re.compile(r"^(p\d\d|n\d\d|domain_neg)$")

# ------------------------------------------------------------------ key sets
# Result keys written by the harness at the rerun commit: asdict(TaskResult).
RERUN_RESULT_KEYS = frozenset({
    "model", "task", "domain_name", "problem_name", "prompt_variant",
    "with_tools", "success", "tool_selected", "format_compliant", "response",
    "response_truncated_by_storage", "thinking", "tool_calls", "tokens",
    "duration_s", "error", "tool_filter", "prompt_style", "failure_reason",
    "truncated", "done_reason", "think_truncated", "plan_label", "infra_failure",
})
assert RERUN_RESULT_KEYS == frozenset(f.name for f in fields(TaskResult)), (
    "pddl_eval.runner.TaskResult changed shape; the loader no longer matches "
    "the harness commit the prereg pins")
# Canonical sweep5v2-live rows (written 2026-05/06) predate three fields.
CANONICAL_RESULT_KEYS = RERUN_RESULT_KEYS - {
    "format_compliant", "response_truncated_by_storage", "think_truncated"}
TOKEN_BASE_KEYS = frozenset({"prompt", "completion", "turns",
                             "total_duration_ns", "eval_duration_ns"})
TOKEN_CTX_KEYS = frozenset({"ctx_clipped_turns", "ctx_clip_last_turn_max_tokens",
                            "ctx_clip_last_turn_prompt_tokens", "ctx_no_room_turns"})
TOOL_CALL_KEYS = frozenset({"name", "arguments", "result"})
KEY_LEN = 10

RERUN = "rerun"
CANONICAL = "canonical"


@dataclass(frozen=True)
class Tokens:
    prompt: int
    completion: int
    turns: int
    ctx_clipped_turns: int                    # 0 when the key is absent
    ctx_clip_last_turn_max_tokens: int | None
    ctx_clip_last_turn_prompt_tokens: int | None
    ctx_no_room_turns: int                    # 0 when the key is absent


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Any
    result: str


@dataclass(frozen=True)
class Row:
    layer: str                 # RERUN | CANONICAL
    cell: str                  # directory name the row was read from
    model_tag: str
    task: str
    domain: str
    problem: str
    plan_label: str
    variant: int
    with_tools: bool
    prompt_style: str
    success: bool              # stored harness grade (tool-verified when with_tools)
    tool_selected: bool | None
    response: str
    response_truncated_by_storage: bool | None   # None only on CANONICAL rows
    tool_calls: tuple[ToolCall, ...]
    tokens: Tokens
    error: str
    failure_reason: str
    truncated: bool
    done_reason: str
    infra_failure: bool

    @property
    def fixture_key(self) -> tuple[str, str, str, str]:
        """(task, domain, problem, plan_label): the fixture, wording excluded."""
        return (self.task, self.domain, self.problem, self.plan_label)

    @property
    def trial_key(self) -> tuple[str, str, str, str, int]:
        """§3 pairing key (domain, problem, variant, plan label), within task."""
        return (self.task, self.domain, self.problem, self.plan_label, self.variant)

    @property
    def arm(self) -> str:
        if self.variant in C.PLAIN:
            return "plain"
        if self.variant in C.STEERED:
            return "steered"
        raise SchemaError(f"variant {self.variant} is in no arm")

    @property
    def invoked(self) -> bool:
        """§5 R5 'share of trials with a tool call'."""
        return len(self.tool_calls) > 0

    @property
    def no_room(self) -> bool:
        """§8a: a turn was never generated because the prompt filled the window."""
        return self.tokens.ctx_no_room_turns > 0

    @property
    def is_exception(self) -> bool:
        """§7: the harness raised (client call or scoring) on this row."""
        return self.failure_reason in C.EXCEPTION_REASONS

    @property
    def clipped_before_tool_call(self) -> bool:
        """§3: a turn ran with a clipped allowance and a tool call followed it.

        A turn is followed by another turn only when it emitted tool calls
        (pddl_eval/chat.py chat_with_tools), so every clipped turn other than
        the last one preceded a tool call. `ctx_clip_last_turn_max_tokens` is
        present iff the LAST turn was clipped (chat._record_ctx_clip). The last
        turn also preceded a tool call when the loop ran out (loop_exhausted).
        """
        clipped = self.tokens.ctx_clipped_turns
        last_clipped = self.tokens.ctx_clip_last_turn_max_tokens is not None
        if clipped - (1 if last_clipped else 0) > 0:
            return True
        return last_clipped and self.failure_reason == "loop_exhausted"


@dataclass(frozen=True)
class CellSpec:
    """What one cell directory must contain."""
    name: str
    layer: str
    model_tag: str
    with_tools: bool
    prompt_style: str
    tasks: tuple[str, ...]
    variants: tuple[int, ...]
    n_rows: int
    per_variant: int
    per_task_variant: dict[str, int]
    k_domains: int


# ------------------------------------------------------------------ typed getters
def _need(d: dict, k: str, where: str):
    if k not in d:
        raise SchemaError(f"{where}: missing key {k!r}")
    return d[k]


def _bool(d: dict, k: str, where: str) -> bool:
    v = _need(d, k, where)
    if not isinstance(v, bool):
        raise SchemaError(f"{where}: {k} must be a bool, got {v!r}")
    return v


def _opt_bool(d: dict, k: str, where: str) -> bool | None:
    v = _need(d, k, where)
    if v is not None and not isinstance(v, bool):
        raise SchemaError(f"{where}: {k} must be a bool or null, got {v!r}")
    return v


def _int(d: dict, k: str, where: str) -> int:
    v = _need(d, k, where)
    if isinstance(v, bool) or not isinstance(v, int):
        raise SchemaError(f"{where}: {k} must be an int, got {v!r}")
    return v


def _str(d: dict, k: str, where: str) -> str:
    v = _need(d, k, where)
    if not isinstance(v, str):
        raise SchemaError(f"{where}: {k} must be a string, got {type(v).__name__}")
    return v


def _exact_keys(d: dict, expected: frozenset, where: str) -> None:
    got = set(d)
    missing = expected - got
    extra = got - expected
    if missing:
        raise SchemaError(f"{where}: missing key(s) {sorted(missing)}")
    if extra:
        wrong_layer = extra & TOKEN_CTX_KEYS
        if wrong_layer:
            raise SchemaError(f"{where}: {sorted(wrong_layer)} belong under "
                              "`tokens`, not at the result top level (wrong layer)")
        raise SchemaError(f"{where}: unexpected key(s) {sorted(extra)}")


def _parse_tokens(t: Any, layer: str, where: str) -> Tokens:
    if not isinstance(t, dict):
        raise SchemaError(f"{where}: tokens must be an object")
    missing = TOKEN_BASE_KEYS - set(t)
    if missing:
        raise SchemaError(f"{where}: tokens missing {sorted(missing)}")
    extra = set(t) - TOKEN_BASE_KEYS - TOKEN_CTX_KEYS
    if extra:
        raise SchemaError(f"{where}: tokens has unexpected key(s) {sorted(extra)}")
    ctx = set(t) & TOKEN_CTX_KEYS
    if layer == CANONICAL and ctx:
        raise SchemaError(f"{where}: canonical row carries {sorted(ctx)}, which "
                          "only exist since 2026-10-02 (wrong corpus layer)")
    for k in t:
        _int(t, k, f"{where}.tokens")
    clipped = t["ctx_clipped_turns"] if "ctx_clipped_turns" in t else 0
    last_max = t["ctx_clip_last_turn_max_tokens"] if "ctx_clip_last_turn_max_tokens" in t else None
    last_prompt = (t["ctx_clip_last_turn_prompt_tokens"]
                   if "ctx_clip_last_turn_prompt_tokens" in t else None)
    no_room = t["ctx_no_room_turns"] if "ctx_no_room_turns" in t else 0
    if "ctx_clipped_turns" in t and clipped < 1:
        raise SchemaError(f"{where}: ctx_clipped_turns present but {clipped}")
    if last_max is not None and clipped < 1:
        raise SchemaError(f"{where}: last-turn clip size without a clipped turn")
    if last_prompt is not None and last_max is None:
        raise SchemaError(f"{where}: last-turn prompt size without a clip size")
    if "ctx_no_room_turns" in t and no_room < 1:
        raise SchemaError(f"{where}: ctx_no_room_turns present but {no_room}")
    if last_max is not None and last_prompt is not None:
        # §2 delta 2 / §8a: prompt plus clipped allowance never exceeds the window.
        if last_prompt + last_max > C.CONTEXT_WINDOW:
            raise RefusedRow(f"{where}: measured prompt {last_prompt} + clipped "
                             f"allowance {last_max} exceeds {C.CONTEXT_WINDOW}")
    return Tokens(prompt=t["prompt"], completion=t["completion"], turns=t["turns"],
                  ctx_clipped_turns=clipped,
                  ctx_clip_last_turn_max_tokens=last_max,
                  ctx_clip_last_turn_prompt_tokens=last_prompt,
                  ctx_no_room_turns=no_room)


def _parse_tool_calls(v: Any, where: str) -> tuple[ToolCall, ...]:
    if not isinstance(v, list):
        raise SchemaError(f"{where}: tool_calls must be a list")
    out = []
    for i, tc in enumerate(v):
        w = f"{where}.tool_calls[{i}]"
        if not isinstance(tc, dict):
            raise SchemaError(f"{w}: not an object")
        _exact_keys(tc, TOOL_CALL_KEYS, w)
        out.append(ToolCall(name=_str(tc, "name", w), arguments=tc["arguments"],
                            result=_str(tc, "result", w)))
    return tuple(out)


def parse_row(obj: Any, spec: CellSpec, where: str) -> Row:
    """One trials.jsonl record -> Row, or SchemaError/RefusedRow."""
    if not isinstance(obj, dict):
        raise SchemaError(f"{where}: record is not an object")
    _exact_keys(obj, frozenset({"key", "result"}), where)
    key, r = obj["key"], obj["result"]
    if not isinstance(key, list) or len(key) != KEY_LEN:
        raise SchemaError(f"{where}: key must be a {KEY_LEN}-list, got {key!r}")
    if not isinstance(r, dict):
        raise SchemaError(f"{where}: result is not an object")
    _exact_keys(r, RERUN_RESULT_KEYS if spec.layer == RERUN else CANONICAL_RESULT_KEYS,
                where)

    model = _str(r, "model", where)
    task = _str(r, "task", where)
    domain = _str(r, "domain_name", where)
    problem = _str(r, "problem_name", where)
    plan_label = _str(r, "plan_label", where)
    variant = _int(r, "prompt_variant", where)
    with_tools = _bool(r, "with_tools", where)
    tool_filter = _str(r, "tool_filter", where)
    prompt_style = _str(r, "prompt_style", where)
    success = _bool(r, "success", where)
    tool_selected = _opt_bool(r, "tool_selected", where)
    response = _str(r, "response", where)
    _str(r, "thinking", where)
    error = _str(r, "error", where)
    failure_reason = _str(r, "failure_reason", where)
    truncated = _bool(r, "truncated", where)
    done_reason = _str(r, "done_reason", where)
    infra_failure = _bool(r, "infra_failure", where)
    dur = _need(r, "duration_s", where)
    if isinstance(dur, bool) or not isinstance(dur, (int, float)):
        raise SchemaError(f"{where}: duration_s must be a number")

    # --- enums
    if task not in TASKS:
        raise SchemaError(f"{where}: unknown task {task!r}")
    if failure_reason not in FAILURE_REASONS:
        raise SchemaError(f"{where}: unknown failure_reason {failure_reason!r}")
    if done_reason not in DONE_REASONS:
        raise SchemaError(f"{where}: unknown done_reason {done_reason!r}")
    if tool_filter != C.TOOL_FILTER:
        raise SchemaError(f"{where}: tool_filter {tool_filter!r} != {C.TOOL_FILTER!r}")
    if prompt_style not in (C.STYLE_A, C.STYLE_B):
        raise SchemaError(f"{where}: unknown prompt_style {prompt_style!r}")
    if not _PROBLEM_RE.match(problem):
        raise SchemaError(f"{where}: unknown problem name {problem!r}")
    if task == "validate_plan":
        if plan_label not in PLAN_LABELS:
            raise SchemaError(f"{where}: unknown plan_label {plan_label!r}")
    elif plan_label != "":
        raise SchemaError(f"{where}: plan_label {plan_label!r} on task {task}")
    if success != (failure_reason == "ok"):
        raise SchemaError(f"{where}: success={success} but failure_reason="
                          f"{failure_reason!r} (harness writes 'ok' iff success)")
    if truncated != (done_reason == "length"):
        raise SchemaError(f"{where}: truncated={truncated} but done_reason={done_reason!r}")

    # --- key <-> result (a key read from the wrong place)
    expect_key = [model, task, domain, problem, plan_label, variant, with_tools,
                  C.THINK, tool_filter, prompt_style]
    if key != expect_key:
        raise SchemaError(f"{where}: resume key {key!r} disagrees with its result "
                          f"{expect_key!r} (think must be {C.THINK!r})")

    # --- the row belongs to this cell
    if model != C.MODEL_IDS[spec.model_tag]:
        raise SchemaError(f"{where}: model {model!r} in cell of {spec.model_tag}")
    if with_tools != spec.with_tools:
        raise SchemaError(f"{where}: with_tools={with_tools} in cell {spec.name}")
    if prompt_style != spec.prompt_style:
        raise RefusedRow(f"{where}: prompt_style {prompt_style!r} in a "
                         f"{spec.prompt_style!r} cell ({spec.name})")
    if task not in spec.tasks:
        raise SchemaError(f"{where}: task {task} not registered for {spec.name}")
    if variant not in spec.variants:
        raise SchemaError(f"{where}: variant {variant} not registered for {spec.name}")

    tool_calls = _parse_tool_calls(_need(r, "tool_calls", where), where)
    if with_tools:
        if tool_selected is None:
            raise SchemaError(f"{where}: with-tools row has tool_selected=null")
    else:
        if tool_selected is not None or tool_calls:
            raise SchemaError(f"{where}: no-tools row carries tool fields")
    tokens = _parse_tokens(_need(r, "tokens", where), spec.layer, where)

    # --- layer-specific fields
    if spec.layer == RERUN:
        cut = _need(r, "response_truncated_by_storage", where)
        if not isinstance(cut, bool):
            raise SchemaError(f"{where}: response_truncated_by_storage must be a "
                              f"bool on a rerun row, got {cut!r}")
        if cut:
            raise RefusedRow(f"{where}: response cut by storage (registered "
                             f"expectation: {C.REGISTERED_STORAGE_CUTS} rows)")
        if len(response) > C.STORAGE_CAP:
            raise RefusedRow(f"{where}: stored response {len(response)} chars > "
                             f"{C.STORAGE_CAP}")
        fc = _need(r, "format_compliant", where)
        if with_tools or task != "simulate":
            if fc is not None:
                raise SchemaError(f"{where}: format_compliant set outside no-tools simulate")
        elif fc is not None and not isinstance(fc, bool):
            raise SchemaError(f"{where}: format_compliant must be a bool or null")
        if _need(r, "think_truncated", where) is not None:
            raise SchemaError(f"{where}: think_truncated set (decoupled row)")
    else:
        cut = None

    if tokens.ctx_no_room_turns:
        # chat.py: a no-room turn returns an empty, tool-call-free message with
        # done_reason "length", which ends the loop; so at most one per trial.
        if tokens.ctx_no_room_turns != 1 or response != "" or done_reason != "length":
            raise RefusedRow(f"{where}: no-room row is not an empty length-stop "
                             f"(turns={tokens.ctx_no_room_turns}, "
                             f"done_reason={done_reason!r}, {len(response)} chars)")

    return Row(layer=spec.layer, cell=spec.name, model_tag=spec.model_tag, task=task,
               domain=domain, problem=problem, plan_label=plan_label, variant=variant,
               with_tools=with_tools, prompt_style=prompt_style, success=success,
               tool_selected=tool_selected, response=response,
               response_truncated_by_storage=cut, tool_calls=tool_calls,
               tokens=tokens, error=error, failure_reason=failure_reason,
               truncated=truncated, done_reason=done_reason,
               infra_failure=infra_failure)


@dataclass(frozen=True)
class LoadedCell:
    spec: CellSpec
    rows: tuple[Row, ...]
    torn_lines: int
    exception_rows: int
    infra_rows: int


def load_cell(root: Path, spec: CellSpec) -> LoadedCell:
    """Load and check one cell directory. The only row reader of this package."""
    cell_dir = root / spec.name
    if "smoke" in spec.name:
        raise SchemaError(f"{spec.name}: smoke cells are never pooled (§7)")
    if not cell_dir.is_dir():
        raise SchemaError(f"cell directory not found: {cell_dir}")
    files = sorted(p.name for p in cell_dir.glob("trials*.jsonl"))
    if files != ["trials.jsonl"]:
        raise SchemaError(f"{cell_dir}: expected exactly trials.jsonl, found {files}")
    rows: list[Row] = []
    seen: set[tuple] = set()
    torn = 0
    with (cell_dir / "trials.jsonl").open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            where = f"{spec.name}/trials.jsonl:{lineno}"
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # A record half-written when a job was killed; the runner's
                # resume drops it and re-runs the key. Counted and reported;
                # completeness below proves every key is present intact.
                torn += 1
                continue
            row = parse_row(obj, spec, where)
            if row.trial_key in seen:
                raise SchemaError(f"{where}: duplicate trial key {row.trial_key}")
            seen.add(row.trial_key)
            rows.append(row)
    _check_completeness(spec, rows)
    return LoadedCell(spec=spec, rows=tuple(rows), torn_lines=torn,
                      exception_rows=sum(r.is_exception for r in rows),
                      infra_rows=sum(r.infra_failure for r in rows))


class IncompleteCell(SchemaError):
    """§7: 'A short cell is resumed, not analysed.'"""


def _check_completeness(spec: CellSpec, rows: list[Row]) -> None:
    if len(rows) != spec.n_rows:
        raise IncompleteCell(f"{spec.name}: {len(rows)} rows, registered {spec.n_rows}")
    per_v: dict[int, int] = {}
    per_tv: dict[tuple[str, int], int] = {}
    domains: set[str] = set()
    for r in rows:
        per_v[r.variant] = per_v.get(r.variant, 0) + 1
        per_tv[(r.task, r.variant)] = per_tv.get((r.task, r.variant), 0) + 1
        domains.add(r.domain)
    for v in spec.variants:
        if per_v.get(v, 0) != spec.per_variant:
            raise IncompleteCell(f"{spec.name}: variant {v} has {per_v.get(v, 0)} "
                                 f"rows, registered {spec.per_variant}")
        for t in spec.tasks:
            want = spec.per_task_variant[t]
            if per_tv.get((t, v), 0) != want:
                raise IncompleteCell(f"{spec.name}: {t} v{v} has "
                                     f"{per_tv.get((t, v), 0)} rows, expected {want}")
    if len(domains) != spec.k_domains:
        raise IncompleteCell(f"{spec.name}: {len(domains)} domains, registered "
                             f"{spec.k_domains}")


# ------------------------------------------------------------------ cell names
def rerun_a_name(model_tag: str) -> str:
    return f"slurm_vllm_{model_tag}_{C.THINK}_tools_all_{C.STYLE_A}_{C.RUN_TAG_A}"


def rerun_b_name() -> str:
    return f"slurm_vllm_{C.PART_B_MODEL}_{C.THINK}_tools_all_{C.STYLE_B}_{C.RUN_TAG_B}"


def rerun_c_name(model_tag: str) -> str:
    return f"slurm_vllm_{model_tag}_{C.THINK}_no-tools_{C.RUN_TAG_C}"


def canonical_tools_name(model_tag: str) -> str:
    return f"slurm_vllm_{model_tag}_{C.THINK}_tools_all_{C.STYLE_A}"


def canonical_no_tools_name(model_tag: str) -> str:
    return f"slurm_vllm_{model_tag}_{C.THINK}_no-tools"


def spec_rerun_a(design: C.Design, model_tag: str) -> CellSpec:
    return CellSpec(name=rerun_a_name(model_tag), layer=RERUN, model_tag=model_tag,
                    with_tools=True, prompt_style=C.STYLE_A, tasks=C.TASKS,
                    variants=C.VARIANTS, n_rows=design.n_part_a_cell,
                    per_variant=design.per_variant_a,
                    per_task_variant=design.per_task_variant,
                    k_domains=design.k_domains)


def spec_rerun_b(design: C.Design) -> CellSpec:
    return CellSpec(name=rerun_b_name(), layer=RERUN, model_tag=C.PART_B_MODEL,
                    with_tools=True, prompt_style=C.STYLE_B, tasks=(C.PART_B_TASK,),
                    variants=C.VARIANTS, n_rows=design.n_part_b,
                    per_variant=design.per_variant_b,
                    per_task_variant={C.PART_B_TASK: design.per_variant_b},
                    k_domains=design.k_domains)


def spec_rerun_c(design: C.Design, model_tag: str) -> CellSpec:
    """§2 Part C: no tools, v11-13, all five tasks, 4,560 rows, full storage."""
    return CellSpec(name=rerun_c_name(model_tag), layer=RERUN, model_tag=model_tag,
                    with_tools=False, prompt_style=C.STYLE_A, tasks=C.TASKS,
                    variants=C.PLAIN, n_rows=design.n_no_tools_cell,
                    per_variant=design.per_variant_a,
                    per_task_variant=design.per_task_variant,
                    k_domains=design.k_domains)


def spec_canonical_tools(design: C.Design, model_tag: str) -> CellSpec:
    return CellSpec(name=canonical_tools_name(model_tag), layer=CANONICAL,
                    model_tag=model_tag, with_tools=True, prompt_style=C.STYLE_A,
                    tasks=C.TASKS, variants=C.VARIANTS, n_rows=design.n_part_a_cell,
                    per_variant=design.per_variant_a,
                    per_task_variant=design.per_task_variant,
                    k_domains=design.k_domains)


def spec_canonical_no_tools(design: C.Design, model_tag: str) -> CellSpec:
    return CellSpec(name=canonical_no_tools_name(model_tag), layer=CANONICAL,
                    model_tag=model_tag, with_tools=False, prompt_style=C.STYLE_A,
                    tasks=C.TASKS, variants=C.PLAIN, n_rows=design.n_no_tools_cell,
                    per_variant=design.per_variant_a,
                    per_task_variant=design.per_task_variant,
                    k_domains=design.k_domains)
