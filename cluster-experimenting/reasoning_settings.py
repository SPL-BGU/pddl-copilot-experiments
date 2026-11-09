#!/usr/bin/env python3
"""Two small jobs for the gpt-oss reasoning-effort cells, run by the sbatch.

system-line: print the `Reasoning: <level>` line of the Harmony system
  message that the running vLLM server builds for gpt-oss, and check it. The
  sbatch runs this once per gpt-oss cell, right after the server is up, so
  the job log shows which effort the served model really gets. It asks the
  server to render a one-message chat (POST /v1/chat/completions/render, no
  generation), decodes the prompt tokens (POST /detokenize), and reads the
  line. In vLLM 0.20.2 the line comes from the request's top-level
  `reasoning_effort` field (vllm/entrypoints/serve/render/serving.py,
  _make_request_with_harmony); with no field, openai-harmony writes its
  default, `medium`.

      reasoning_settings.py system-line --base-url URL --model HF_ID [--effort LEVEL]

  Prints `harmony system line: Reasoning: <level> (expected <e>)`. Exit 0
  when the level matches (--effort, or `medium` without it), 1 when it differs
  or is missing, 2 when the server cannot be asked.

write-settings: write OUT_DIR/client_settings.json, the record of the
  request settings that run_experiment.py's summary does not hold (that file
  is hashed into the frozen delivered-rerun package, so it is not edited).

      reasoning_settings.py write-settings PATH key=value [key=value ...]

  Empty values become null; store_reasoning is a boolean; max_model_len an
  integer. Standard library only.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

HARMONY_DEFAULT_EFFORT = "medium"
_SYSTEM_RE = re.compile(r"<\|start\|>system<\|message\|>(.*?)<\|end\|>", re.DOTALL)
_EFFORT_RE = re.compile(r"^Reasoning:\s*(\w+)\s*$", re.MULTILINE)


def system_segment(prompt: str) -> str:
    """Body of the first Harmony system message in a rendered prompt, or ""."""
    m = _SYSTEM_RE.search(prompt)
    return m.group(1) if m else ""


def effort_in(text: str) -> str:
    """The level on the first `Reasoning:` line of `text`, or ""."""
    m = _EFFORT_RE.search(text)
    return m.group(1) if m else ""


def render_request(model: str, effort: str | None) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
    if effort is not None:
        body["reasoning_effort"] = effort
    return body


def _post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def system_line(base_url: str, model: str, effort: str | None,
                timeout: float = 60.0, post=_post) -> tuple[int, str]:
    """(exit code, printed line). `post` is injectable for tests."""
    base = base_url.rstrip("/")
    expected = effort or HARMONY_DEFAULT_EFFORT
    try:
        rendered = post(f"{base}/v1/chat/completions/render",
                        render_request(model, effort), timeout)
        prompt = post(f"{base}/detokenize",
                      {"model": model, "tokens": rendered["token_ids"]}, timeout)["prompt"]
    except (urllib.error.URLError, OSError, KeyError, TypeError, ValueError) as exc:
        return 2, f"harmony system line: could not render ({type(exc).__name__}: {exc})"
    # vLLM's decode keeps special tokens, so the <|start|>system… markers are
    # there; if they were dropped, the first `Reasoning:` line of the whole
    # prompt is still the system message's (it comes first).
    level = effort_in(system_segment(prompt) or prompt)
    line = f"harmony system line: Reasoning: {level or '(missing)'} (expected {expected})"
    return (0 if level == expected else 1), line


def settings_record(pairs: list[str]) -> dict:
    out: dict = {}
    for pair in pairs:
        key, sep, val = pair.partition("=")
        if not sep or not key:
            raise ValueError(f"expected key=value, got {pair!r}")
        out[key] = val if val != "" else None
    if "store_reasoning" in out:
        out["store_reasoning"] = out["store_reasoning"] == "1"
    if out.get("max_model_len") is not None:
        out["max_model_len"] = int(out["max_model_len"])
    out["reasoning_effort_sent"] = out.get("reasoning_effort") is not None
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="gpt-oss reasoning-effort helpers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("system-line")
    s1.add_argument("--base-url", required=True)
    s1.add_argument("--model", required=True)
    s1.add_argument("--effort", choices=("low", "medium", "high"), default=None)
    s1.add_argument("--timeout", type=float, default=60.0)
    s2 = sub.add_parser("write-settings")
    s2.add_argument("path")
    s2.add_argument("pairs", nargs="*")
    args = ap.parse_args(argv)
    if args.cmd == "system-line":
        rc, line = system_line(args.base_url, args.model, args.effort, args.timeout)
        print(line)
        return rc
    with open(args.path, "w") as f:
        json.dump(settings_record(args.pairs), f, indent=1)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
