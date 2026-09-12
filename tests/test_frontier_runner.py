"""Unit tests for tools/frontier_runner.py + tools/_run_manifest.py (frontier
budget probe apparatus, gate-5 review fixes of 2026-09-10).

Pure-Python: no MCP, no Anthropic API. Covers
  * final-turn output tokens recorded separately from the aggregate
    (`run_one` -> `grade` -> tokens.completion_final);
  * the run manifest: written on a fresh dir, refused on a resume with
    changed settings, refused on a dir that holds trials without provenance.

Run standalone: `python3 tests/test_frontier_runner.py`
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402
import tools.frontier_runner as fr  # noqa: E402
from tools import _run_manifest as rm  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes for the SDK tool runner
# ---------------------------------------------------------------------------
def _msg(out_tok: int, stop_reason: str, text: str = "") -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=100, output_tokens=out_tok,
                            cache_creation_input_tokens=0, cache_read_input_tokens=50)
    content = [SimpleNamespace(type="text", text=text)] if text else []
    return SimpleNamespace(usage=usage, stop_reason=stop_reason, content=content)


class _Stream:
    def __init__(self, msg):
        self._msg = msg

    async def get_final_message(self):
        return self._msg


class _Runner:
    def __init__(self, msgs, stream: bool):
        self._items = [_Stream(m) if stream else m for m in msgs]

    def __aiter__(self):
        self._i = iter(self._items)
        return self

    async def __anext__(self):
        try:
            return next(self._i)
        except StopIteration:
            raise StopAsyncIteration


class _Client:
    def __init__(self, msgs):
        self.msgs = msgs
        self.kwargs = None

    @property
    def beta(self):
        return SimpleNamespace(messages=SimpleNamespace(tool_runner=self._tool_runner))

    def _tool_runner(self, **kwargs):
        self.kwargs = kwargs
        return _Runner(self.msgs, stream=kwargs["stream"])


class _MCP:
    tools: list = []

    async def call_tool(self, name, args):
        return "{}"


def _job():
    # (model, task, dname, dpddl, pname, ppddl, pv, with_tools, gt, np, plan_label)
    return ("claude-sonnet-4-6", "simulate", "blocksworld", "(define (domain bw))",
            "p01", "(define (problem p01))", 11, True, {"trace": "[]"}, 64000, "")


# ---------------------------------------------------------------------------
# 1. Final-turn tokens
# ---------------------------------------------------------------------------
def test_run_one_records_final_turn_tokens(r: TestResults) -> None:
    # Three turns: tool call, tool call, final answer. Aggregate 70,000 output
    # tokens exceeds the 64,000 budget; no single turn did. The final turn
    # (10,000) is what a truncation tripwire must read.
    msgs = [_msg(30000, "tool_use"), _msg(30000, "tool_use"),
            _msg(10000, "end_turn", text="final answer")]
    for stream in (False, True):
        client = _Client(msgs)
        out = asyncio.run(fr.run_one(client, _MCP(), "claude-sonnet-4-6", _job(),
                                     stream=stream))
        tag = "stream" if stream else "non-stream"
        r.check_eq(f"{tag}: aggregate out_tok", out["out_tok"], 70000)
        r.check_eq(f"{tag}: final-turn out_tok_final", out["out_tok_final"], 10000)
        r.check_eq(f"{tag}: turns", out["turns"], 3)
        r.check_eq(f"{tag}: stop_reason from last turn", out["stop_reason"], "end_turn")
        r.check_eq(f"{tag}: text from last turn", out["text"], "final answer")
        r.check_eq(f"{tag}: max_tokens passed per call", client.kwargs["max_tokens"], 64000)
        r.check_eq(f"{tag}: stream flag passed", client.kwargs["stream"], stream)

    # Truncated final turn exactly at the budget.
    msgs = [_msg(3000, "tool_use"), _msg(64000, "max_tokens", text="cut off")]
    out = asyncio.run(fr.run_one(_Client(msgs), _MCP(), "claude-sonnet-4-6", _job()))
    r.check_eq("truncated: final == budget", out["out_tok_final"], 64000)
    r.check_eq("truncated: aggregate above budget", out["out_tok"], 67000)
    r.check_eq("truncated: stop_reason", out["stop_reason"], "max_tokens")


def test_run_one_context_overflow_final_is_zero(r: TestResults) -> None:
    class _Overflow(_Runner):
        async def __anext__(self):
            item = await super().__anext__()
            if getattr(item, "stop_reason", None) == "tool_use":
                return item
            raise RuntimeError("400 prompt is too long: 498K tokens > 200K")

    class _OverflowClient(_Client):
        def _tool_runner(self, **kwargs):
            self.kwargs = kwargs
            return _Overflow(self.msgs, stream=kwargs["stream"])

    msgs = [_msg(5000, "tool_use"), _msg(1, "end_turn")]
    out = asyncio.run(fr.run_one(_OverflowClient(msgs), _MCP(), "claude-sonnet-4-6", _job()))
    r.check_eq("overflow: aggregate keeps completed turns", out["out_tok"], 5000)
    r.check_eq("overflow: final-turn count is 0", out["out_tok_final"], 0)
    r.check_eq("overflow: recorded as max_tokens", out["stop_reason"], "max_tokens")
    r.check("overflow: error kept", "prompt is too long" in out["error"], out["error"])


def test_grade_and_failed_result_carry_completion_final(r: TestResults) -> None:
    outcome = {"text": "", "tool_calls": [], "stop_reason": "refusal", "in_tok": 10,
               "out_tok": 70000, "out_tok_final": 10000, "cache_write": 0,
               "cache_read": 0, "turns": 3, "loop_exhausted": False}
    # refusal path skips check_success, so no MCP/GT needed.
    res = asyncio.run(fr.grade(_job(), outcome, None, "claude-sonnet-4-6"))
    r.check_eq("grade: completion aggregate", res.tokens["completion"], 70000)
    r.check_eq("grade: completion_final", res.tokens["completion_final"], 10000)
    failed = fr.failed_result(_job(), "boom", "claude-sonnet-4-6")
    r.check_eq("failed_result: completion_final present", failed.tokens["completion_final"], 0)


# ---------------------------------------------------------------------------
# 2. Run manifest
# ---------------------------------------------------------------------------
def _args(**over):
    base = dict(tasks=["simulate"], corpus="canonical", num_predict=64000,
                snapshot_len=262144, stream=True, use_cached_gt=True,
                gt_cache="results/derived/gt_cache.json", keys_file=None,
                limit=None, variant=11)
    base.update(over)
    return SimpleNamespace(**base)


def _manifest(**over):
    return fr.build_run_manifest(_args(**over), model="claude-sonnet-4-6",
                                 selected=[_job()], ground_truth={"blocksworld": {"p01": {}}},
                                 gt_cache_sha="ab" * 32)


def test_build_run_manifest_fields(r: TestResults) -> None:
    m = _manifest()
    for k, v in {"backend": "anthropic-tool-runner", "model": "claude-sonnet-4-6",
                 "with_tools": True, "tasks": ["simulate"], "corpus": "canonical",
                 "domains_dir": "domains", "prompt_variants": [11], "num_predict": 64000,
                 "snapshot_len": 262144, "max_iterations": 10, "stream": True,
                 "temperature": 0, "think": "off", "ground_truth": "cached",
                 "gt_cache_sha256": "ab" * 32, "keys_files": None, "limit": None}.items():
        r.check_eq(f"manifest.{k}", m[k], v)
    r.check_eq("ground-truth content hash is deterministic",
               m["ground_truth_sha256"],
               rm.ground_truth_sha256({"blocksworld": {"p01": {}}}))
    r.check("loop limit is the harness constant", m["max_iterations"] == fr.MAX_TOOL_LOOPS, "")


def test_ensure_manifest_fresh_then_compatible_resume(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "run"
        m1 = rm.ensure_manifest(out, _manifest())
        r.check("manifest written on fresh dir", (out / rm.MANIFEST_NAME).exists(), "")
        r.check_eq("returns the requested manifest", m1["num_predict"], 64000)
        (out / "trials.jsonl").write_text('{"key": [], "result": {}}\n')
        # Same settings, later invocation (different created_at, SDK bumped):
        # compatible, returns the EXISTING manifest.
        m2 = rm.ensure_manifest(out, dict(_manifest(), created_at="later", sdk_version="9.9.9"))
        r.check_eq("compatible resume keeps original created_at", m2["created_at"], m1["created_at"])
        r.check_eq("compatible resume keeps original sdk_version", m2["sdk_version"], m1["sdk_version"])


def test_ensure_manifest_refuses_changed_settings(r: TestResults) -> None:
    changes = {
        "budget": dict(num_predict=6144),
        "snapshot": dict(snapshot_len=16384),
        "stream": dict(stream=False),
        "corpus": dict(corpus="anon"),
        "variant": dict(variant=12),
        "keys file": dict(keys_file=["subset.jsonl"]),
        "limit": dict(limit=10),
        "tasks": dict(tasks=["solve"]),
    }
    for label, over in changes.items():
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            rm.ensure_manifest(out, _manifest())
            (out / "trials.jsonl").write_text("{}\n")
            requested = _manifest(**over)
            if label == "variant":
                requested["prompt_variants"] = [12]     # selection differs
            try:
                rm.ensure_manifest(out, requested)
                r.check(f"resume refused: {label}", False, "no exception")
            except rm.ManifestError as exc:
                r.check(f"resume refused: {label}", "different settings" in str(exc), str(exc))
    # Ground-truth hash and loop limit are compared too.
    for label, key, val in [("gt hash", "gt_cache_sha256", "cd" * 32),
                            ("gt content", "ground_truth_sha256", "0" * 64),
                            ("loop limit", "max_iterations", 5),
                            ("model", "model", "claude-haiku-4-5")]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            rm.ensure_manifest(out, _manifest())
            requested = dict(_manifest(), **{key: val})
            try:
                rm.ensure_manifest(out, requested)
                r.check(f"resume refused: {label}", False, "no exception")
            except rm.ManifestError as exc:
                r.check(f"resume refused: {label}", key in str(exc), str(exc))


def test_ensure_manifest_refuses_trials_without_provenance(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "run"
        out.mkdir()
        (out / "trials.jsonl").write_text('{"key": [], "result": {}}\n')
        try:
            rm.ensure_manifest(out, _manifest())
            r.check("trials without manifest refused", False, "no exception")
        except rm.ManifestError as exc:
            r.check("trials without manifest refused", "fresh --out" in str(exc), str(exc))
        r.check("nothing written on refusal", not (out / rm.MANIFEST_NAME).exists(), "")
    # A suffixed trials file (trials_rest52.jsonl) counts as trials too.
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "run"
        out.mkdir()
        (out / "trials_rest52.jsonl").write_text("{}\n")
        try:
            rm.ensure_manifest(out, _manifest())
            r.check("suffixed trials without manifest refused", False, "no exception")
        except rm.ManifestError:
            r.check("suffixed trials without manifest refused", True, "")


def test_read_manifest_rejects_garbage(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        r.check("no manifest -> None", rm.read_manifest(out) is None, "")
        (out / rm.MANIFEST_NAME).write_text("not json")
        try:
            rm.read_manifest(out)
            r.check("unreadable manifest refused", False, "no exception")
        except rm.ManifestError:
            r.check("unreadable manifest refused", True, "")
        (out / rm.MANIFEST_NAME).write_text(json.dumps({"manifest_version": 99}))
        try:
            rm.read_manifest(out)
            r.check("unknown manifest version refused", False, "no exception")
        except rm.ManifestError:
            r.check("unknown manifest version refused", True, "")


def main() -> None:
    r = TestResults("test_frontier_runner")
    test_run_one_records_final_turn_tokens(r)
    test_run_one_context_overflow_final_is_zero(r)
    test_grade_and_failed_result_carry_completion_final(r)
    test_build_run_manifest_fields(r)
    test_ensure_manifest_fresh_then_compatible_resume(r)
    test_ensure_manifest_refuses_changed_settings(r)
    test_ensure_manifest_refuses_trials_without_provenance(r)
    test_read_manifest_rejects_garbage(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
