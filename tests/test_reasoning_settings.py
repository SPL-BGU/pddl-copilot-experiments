"""Tests for cluster-experimenting/reasoning_settings.py (2026-11-09).

The Harmony check reads the `Reasoning:` line of the system message vLLM
renders for gpt-oss. The rendered prompt below is the openai-harmony system
message layout; the server calls are replaced by a fake `post`.
Runs under pytest and as a plain script.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "reasoning_settings", REPO_ROOT / "cluster-experimenting" / "reasoning_settings.py")
RS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RS)


def _prompt(level: str) -> str:
    return ("<|start|>system<|message|>You are ChatGPT, a large language model "
            "trained by OpenAI.\nKnowledge cutoff: 2024-06\nCurrent date: "
            f"2026-11-09\n\nReasoning: {level}\n\n# Valid channels: analysis, "
            "commentary, final. Channel must be included for every message."
            "<|end|><|start|>developer<|message|># Instructions\n\nReasoning: "
            "high is not a system line<|end|><|start|>user<|message|>ping<|end|>"
            "<|start|>assistant")


def _fake_post(level_for_effort: dict, seen: list):
    def post(url, body, timeout):
        seen.append((url, body))
        if url.endswith("/v1/chat/completions/render"):
            return {"token_ids": [1, 2, 3], "effort": body.get("reasoning_effort")}
        if url.endswith("/detokenize"):
            effort = seen[-2][1].get("reasoning_effort")
            return {"prompt": _prompt(level_for_effort[effort])}
        raise AssertionError(url)
    return post


def test_system_line_reads_the_system_message_only():
    assert RS.effort_in(RS.system_segment(_prompt("low"))) == "low"
    assert RS.effort_in(RS.system_segment(_prompt("medium"))) == "medium"
    # the developer message's "Reasoning:" text is not the system line
    assert RS.system_segment(_prompt("low")).count("Reasoning:") == 1
    # markers dropped: the first Reasoning line of the prompt is still found
    bare = _prompt("low").replace("<|start|>", "").replace("<|message|>", "").replace("<|end|>", "")
    assert RS.system_segment(bare) == "" and RS.effort_in(bare) == "low"
    assert RS.effort_in("no such line") == ""


def test_system_line_checks_the_expected_level():
    honest = {None: "medium", "low": "low", "medium": "medium", "high": "high"}
    for effort in (None, "low", "medium", "high"):
        seen: list = []
        rc, line = RS.system_line("http://h:1/", "openai/gpt-oss-20b", effort,
                                  post=_fake_post(honest, seen))
        assert rc == 0, line
        assert line == (f"harmony system line: Reasoning: {honest[effort]} "
                        f"(expected {effort or 'medium'})")
        assert seen[0][0] == "http://h:1/v1/chat/completions/render"
        assert ("reasoning_effort" in seen[0][1]) == (effort is not None)
        assert seen[1] == ("http://h:1/detokenize",
                           {"model": "openai/gpt-oss-20b", "tokens": [1, 2, 3]})
    # a server that ignores the field: the low cell must fail the check
    ignoring = {None: "medium", "low": "medium"}
    rc, line = RS.system_line("http://h:1", "m", "low", post=_fake_post(ignoring, []))
    assert rc == 1 and "Reasoning: medium (expected low)" in line


def test_system_line_server_error_is_exit_2():
    def post(url, body, timeout):
        raise OSError("connection refused")
    rc, line = RS.system_line("http://h:1", "m", "low", post=post)
    assert rc == 2 and "could not render" in line

    def post_bad(url, body, timeout):
        return {"error": "no token_ids"}
    assert RS.system_line("http://h:1", "m", None, post=post_bad)[0] == 2


def test_write_settings_record():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "client_settings.json"
        rc = RS.main(["write-settings", str(path), "think_mode_token=effort-low",
                      "reasoning_effort=low", "store_reasoning=1", "max_model_len=16384",
                      "harmony_system_line=harmony system line: Reasoning: low (expected low)",
                      "hf_revision="])
        assert rc == 0
        rec = json.loads(path.read_text())
    assert rec == {
        "think_mode_token": "effort-low", "reasoning_effort": "low",
        "store_reasoning": True, "max_model_len": 16384,
        "harmony_system_line": "harmony system line: Reasoning: low (expected low)",
        "hf_revision": None, "reasoning_effort_sent": True,
    }
    rec2 = RS.settings_record(["think_mode_token=default", "reasoning_effort=",
                               "store_reasoning=0"])
    assert rec2["reasoning_effort"] is None and rec2["reasoning_effort_sent"] is False
    assert rec2["store_reasoning"] is False
    try:
        RS.settings_record(["novalue"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def _write_cell(root: Path, think: str, cond: str, completions: list[int],
                thinking: str, line: str | None) -> None:
    cell = root / f"slurm_vllm_gpt-oss_20b_{think}_{cond}_effort-smoke"
    cell.mkdir(parents=True)
    with (cell / "trials.jsonl").open("w") as f:
        for i, c in enumerate(completions):
            f.write(json.dumps({"key": [], "result": {
                "task": "solve", "domain_name": "d", "problem_name": f"p{i}",
                "plan_label": "", "prompt_variant": 11, "done_reason": "stop",
                "thinking": thinking, "tokens": {"completion": c}}}) + "\n")
        f.write('{"torn line\n')
    if line is not None:
        (cell / "client_settings.json").write_text(json.dumps({"harmony_system_line": line}))


def test_effort_smoke_check():
    _spec2 = importlib.util.spec_from_file_location(
        "effort_smoke_check", REPO_ROOT / "tools" / "effort_smoke_check.py")
    ESC = importlib.util.module_from_spec(_spec2)
    _spec2.loader.exec_module(ESC)
    ok_low = "harmony system line: Reasoning: low (expected low)"
    ok_def = "harmony system line: Reasoning: medium (expected medium)"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for cond in ESC.CONDS:
            _write_cell(root, "effort-low", cond, [100, 200, 300], "t", ok_low)
            _write_cell(root, "default", cond, [400, 500, 600], "t", ok_def)
        assert ESC.main([str(root)]) == 0
    # each criterion failing on its own fails the smoke
    for bad in ("tokens", "line", "trace"):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for cond in ESC.CONDS:
                _write_cell(root, "effort-low", cond,
                            [900, 900, 900] if bad == "tokens" else [100, 200, 300],
                            "" if bad == "trace" else "t",
                            ok_def if bad == "line" else ok_low)
                _write_cell(root, "default", cond, [400, 500, 600], "t", ok_def)
            assert ESC.main([str(root)]) == 1, bad


if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
        except Exception as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {_name}: {type(exc).__name__}: {exc}")
    print(f"\ntest_reasoning_settings: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
