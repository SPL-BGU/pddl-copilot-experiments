"""D1e wiring of the PlanBench tools arm: submit_planbench.sh --prompt and the
per-model serve flags of run_planbench_tools_rtx.sbatch.

The sbatch's model-resolution block (from "### Prompt arm" to "### Workspace")
is cut out and run under bash with the real lib/defaults.sh, once per
verified model, so the test sees the exact flags the job would pass: the same
per-model extras run_condition_vllm_rtx.sbatch passes since PR #122 (chat
template, extra serve args, pinned revision, weights to job scratch, the
client's tool-call id style) and PR #126 (reasoning effort). Nothing is
submitted; submit_planbench.sh runs with --dry-run only.

Standalone: `python3 tests/test_planbench_submit.py`; also under pytest.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CE = REPO / "cluster-experimenting"
SBATCH = CE / "run_planbench_tools_rtx.sbatch"
SUBMIT = CE / "submit_planbench.sh"
DEFAULTS = CE / "lib" / "defaults.sh"

_PRINT = (
    'echo "ENGINE_BACKEND=$ENGINE_BACKEND"\n'
    'echo "TOOL_CALL_PARSER=$TOOL_CALL_PARSER"\n'
    'echo "REASONING_PARSER_FLAG=$REASONING_PARSER_FLAG"\n'
    'echo "MAX_NUM_BATCHED_TOKENS_FLAG=$MAX_NUM_BATCHED_TOKENS_FLAG"\n'
    'echo "CHAT_TEMPLATE_FLAG=$CHAT_TEMPLATE_FLAG"\n'
    'echo "EXTRA_SERVE_FLAGS=$EXTRA_SERVE_FLAGS"\n'
    'echo "APPTAINER_ENV=${APPTAINER_ENV[*]}"\n'
    'echo "TOOL_CALL_ID_STYLE=${TOOL_CALL_ID_STYLE:-}"\n'
    'echo "EFFORT=$EFFORT"\n'
    'echo "ENGINE_THINK=$ENGINE_THINK"\n'
)


def _block() -> str:
    text = SBATCH.read_text()
    a = text.index("### Prompt arm")
    b = text.index("### Workspace on /scratch")
    return text[a:b]


def _resolve(model: str, think: str = "off", arm: str = "legacy",
             tasks: str = "t1") -> tuple[int, dict, str]:
    script = (
        "set -eo pipefail\n"
        f'source "{DEFAULTS}"\n'
        f'MODEL="{model}"; THINK="{think}"; PROMPT_ARM="{arm}"\n'
        f'PLANBENCH_TASKS="{tasks}"; EXPT_ROOT="{REPO}"\n'
        "unset TOOL_CALL_ID_STYLE HF_REVISION\n"
        + _block() + _PRINT
    )
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    out = {}
    for line in p.stdout.splitlines():
        k, _, v = line.partition("=")
        out[k] = v.strip()
    return p.returncode, out, p.stderr


def _verified_models() -> list[str]:
    p = subprocess.run(
        ["bash", "-c", f'source "{DEFAULTS}"; printf "%s\\n" "${{PDDL_VLLM_VERIFIED_MODELS[@]}}"'],
        capture_output=True, text=True, check=True,
    )
    return p.stdout.split()


def _lookup(model: str) -> dict:
    keys = ("TOOL_CALL_PARSER", "REASONING_PARSER", "CHAT_TEMPLATE",
            "EXTRA_SERVE_ARGS", "HF_REVISION", "HF_CACHE_IN_JOB",
            "TOOL_CALL_ID_STYLE", "MAX_NUM_BATCHED_TOKENS")
    echo = "".join(f'echo "{k}=${{{k}:-}}"\n' for k in keys)
    p = subprocess.run(
        ["bash", "-c", f'source "{DEFAULTS}"; vllm_lookup "{model}"\n{echo}'],
        capture_output=True, text=True, check=True,
    )
    return dict(l.split("=", 1) for l in p.stdout.splitlines())


def _think_for(model: str) -> str:
    return "default" if _lookup(model)["TOOL_CALL_ID_STYLE"] == "mistral9" else "off"


def test_per_model_flags_match_lib_defaults():
    for model in _verified_models():
        lk = _lookup(model)
        rc, out, err = _resolve(model, think=_think_for(model))
        assert rc == 0, (model, err)
        assert out["TOOL_CALL_PARSER"] == lk["TOOL_CALL_PARSER"], model
        rp = lk["REASONING_PARSER"] or "qwen3"
        want_rp = "" if rp == "none" else f"--reasoning-parser {rp}"
        assert out["REASONING_PARSER_FLAG"] == want_rp, model
        want_tmpl = f"--chat-template {REPO}/{lk['CHAT_TEMPLATE']}" if lk["CHAT_TEMPLATE"] else ""
        assert out["CHAT_TEMPLATE_FLAG"] == want_tmpl, model
        extra = lk["EXTRA_SERVE_ARGS"]
        if lk["HF_REVISION"]:
            extra += f" --revision {lk['HF_REVISION']} --tokenizer-revision {lk['HF_REVISION']}"
        assert out["EXTRA_SERVE_FLAGS"] == extra.strip(), model
        want_env = "APPTAINERENV_HF_HOME=/root/.cache/huggingface" if lk["HF_CACHE_IN_JOB"] == "1" else ""
        assert out["APPTAINER_ENV"] == want_env, model
        assert out["TOOL_CALL_ID_STYLE"] == lk["TOOL_CALL_ID_STYLE"], model
        mnbt = lk["MAX_NUM_BATCHED_TOKENS"]
        assert out["MAX_NUM_BATCHED_TOKENS_FLAG"] == (f"--max-num-batched-tokens {mnbt}" if mnbt else ""), model


def test_old_models_keep_their_serve_command():
    """The models verified before 2026-10-27 get no new flag."""
    for model in ("Qwen3.5:0.8B", "Qwen3.5:4B", "Qwen3.5:9B", "qwen3.6:35b", "gemma4:26b-a4b"):
        rc, out, err = _resolve(model)
        assert rc == 0, err
        for k in ("CHAT_TEMPLATE_FLAG", "EXTRA_SERVE_FLAGS", "APPTAINER_ENV",
                  "TOOL_CALL_ID_STYLE", "EFFORT"):
            assert out[k] == "", (model, k, out[k])


def test_serve_command_splices_the_new_flags():
    text = SBATCH.read_text()
    serve = text[text.index('env "${APPTAINER_ENV[@]}" apptainer exec'):text.index('> "$SERVE_LOG"')]
    for piece in ("$CHAT_TEMPLATE_FLAG", "$EXTRA_SERVE_FLAGS", "$MAX_NUM_BATCHED_TOKENS_FLAG",
                  '--tool-call-parser "$TOOL_CALL_PARSER"', "$REASONING_PARSER_FLAG",
                  "--enable-prefix-caching", '--served-model-name "$MODEL"'):
        assert piece in serve, piece
    assert 'export PDDL_TOOL_CALL_ID_STYLE="$TOOL_CALL_ID_STYLE"' in text
    assert 'export PDDL_REASONING_EFFORT="$EFFORT"' in text
    assert 'export PDDL_COPILOT_THINK="$ENGINE_THINK"' in text


def test_prompt_arm_sets_the_engine_backend():
    for arm, backend in (("legacy", "vllm-tools"), ("plain", "vllm-tools-plain"),
                         ("steered", "vllm-tools-steered")):
        rc, out, err = _resolve("Qwen3.5:4B", arm=arm)
        assert rc == 0, err
        assert out["ENGINE_BACKEND"] == backend
    assert 'ENGINE="pddl_copilot__${ENGINE_BACKEND}__${MODEL}"' in SBATCH.read_text()


def test_guards():
    rc, _, err = _resolve("Qwen3.5:4B", arm="steered", tasks="t1 t3")
    assert rc != 0 and "t1-only" in err
    rc, _, err = _resolve("Qwen3.5:4B", arm="bogus")
    assert rc != 0
    rc, _, err = _resolve("Qwen3.5:4B", think="effort-low")
    assert rc != 0 and "reasoning_effort" in err
    rc, _, err = _resolve("ministral3:14b", think="off")
    assert rc != 0 and "THINK=default" in err


def test_effort_maps_to_default_think_plus_effort():
    rc, out, err = _resolve("gpt-oss:20b", think="effort-low")
    assert rc == 0, err
    assert out["EFFORT"] == "low" and out["ENGINE_THINK"] == "default"


def _submit(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SUBMIT), *args, "--dry-run"],
                          capture_output=True, text=True)


def test_submit_prompt_arm():
    p = _submit("--tools", "--prompt", "steered", "--smoke", "--models", "Qwen3.5:4B",
                "--num-predict", "8192")
    assert p.returncode == 0, p.stderr
    sb = [l for l in p.stdout.splitlines() if l.strip().startswith("sbatch ")]
    assert len(sb) == 1
    assert "PROMPT_ARM=steered" in sb[0] and "PLANBENCH_TASKS=t1," in sb[0]
    assert "run_planbench_tools_rtx.sbatch" in sb[0]
    assert "--job-name=pddl_planbench_tools_steered_Qwen3_5_4B" in sb[0]


def test_submit_roster_default_keeps_the_4b():
    p = _submit("--tools", "--prompt", "plain")
    assert p.returncode == 0, p.stderr
    models = re.findall(r"MODEL=([^,]+),", p.stdout)
    assert models == ["Qwen3.5:4B", "Qwen3.5:9B", "qwen3.6:35b"]
    p = _submit("--tools", "--prompt", "plain", "--smoke")
    assert re.findall(r"MODEL=([^,]+),", p.stdout) == ["Qwen3.5:4B"]


def test_submit_refusals_and_legacy():
    assert _submit("--prompt", "steered").returncode != 0
    assert _submit("--tools", "--prompt", "plain", "--tasks", "t3").returncode != 0
    assert _submit("--tools", "--prompt", "other").returncode != 0
    p = _submit("--tools", "--smoke")
    assert p.returncode == 0 and "PROMPT_ARM" not in p.stdout
    assert "--job-name=pddl_planbench_tools_Qwen3_5_0_8B" in p.stdout


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
    print(f"\ntest_planbench_submit: {len(_tests) - _failed}/{len(_tests)} passed")
    sys.exit(1 if _failed else 0)
