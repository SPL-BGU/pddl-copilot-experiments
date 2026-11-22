"""Unit tests for tools/d5a_pilot.py (D5a thinking pilot, 2026-11-09).

Pure-Python: no MCP, no Anthropic API. Covers the seeded key pick, the
outcome-blind parse check (harness extractor and the Corrêa <plan> tags),
the percentile/stat helpers, the per-arm report from a synthetic arm dir,
and the full-set cost re-estimate arithmetic.

Run standalone: `python3 tests/test_d5a_pilot.py`
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402
import tools.d5a_pilot as dp  # noqa: E402


def _keys():
    keys = []
    for d in ("bw", "gripper", "rovers", "tpp"):
        for p in ("p01", "p02", "p03"):
            for v in (11, 12, 13):
                keys.append(["claude-sonnet-4-6", "solve", d, p, "", v, False,
                             "off", "all", "minimal"])
                keys.append(["claude-sonnet-4-6", "validate_plan", d, p, "v1", v,
                             False, "off", "all", "minimal"])
    return keys


def test_pick_keys(r: TestResults) -> None:
    keys = _keys()
    a = dp.pick_keys(keys, 8, 20261109)
    b = dp.pick_keys(list(reversed(keys)), 8, 20261109)
    r.check("pick is independent of input order", a == b)
    r.check_eq("n picked", len(a), 8)
    r.check("solve only", all(k["task"] == "solve" for k in a))
    r.check("distinct problems",
            len({(k["domain_name"], k["problem_name"]) for k in a}) == 8)
    r.check("different seed, different pick", dp.pick_keys(keys, 8, 1) != a)
    try:
        dp.pick_keys(keys, 13, 1)
        r.check("too many refused", False, "no exception")
    except ValueError:
        r.check("too many refused", True)
    with tempfile.TemporaryDirectory() as tmp:
        trials = Path(tmp) / "trials.jsonl"
        trials.write_text("".join(json.dumps({"key": k, "result": {"success": True}}) + "\n"
                                  for k in keys))
        out = Path(tmp) / "keys"
        dp.cmd_keys(type("A", (), {"trials": trials, "n": 8, "seed": 20261109, "out": out})())
        son = [json.loads(l) for l in (out / "sonnet_keys.jsonl").read_text().splitlines()]
        hai = [json.loads(l) for l in (out / "haiku_v11_keys.jsonl").read_text().splitlines()]
        cor = [json.loads(l) for l in (out / "correa_keys.jsonl").read_text().splitlines()]
        r.check_eq("sonnet keys = pick", son, a)
        r.check("haiku keys: same problems, v11",
                [(k["domain_name"], k["problem_name"]) for k in hai]
                == [(k["domain_name"], k["problem_name"]) for k in son]
                and all(k["prompt_variant"] == 11 for k in hai))
        r.check("correa keys drop gripper",
                all(k["domain_name"] != "gripper" for k in cor)
                and len(cor) == sum(1 for k in son if k["domain_name"] != "gripper"))


def test_answer_parses(r: TestResults) -> None:
    p = dp.answer_parses('{"plan": ["(pick a)", "(drop a)"]}', "harness")
    r.check_eq("json plan parses", (p["parses"], p["path"], p["n_actions"]), (True, "json", 2))
    p = dp.answer_parses("Here:\n(pick a)\n(drop a)\n", "harness")
    r.check_eq("free text fallback", (p["parses"], p["path"]), (True, "free_text"))
    p = dp.answer_parses('{"plan": []}', "harness")
    r.check("empty json plan does not parse", not p["parses"])
    p = dp.answer_parses("no plan here", "harness")
    r.check_eq("nothing", (p["parses"], p["path"]), (False, "none"))
    p = dp.answer_parses("text\n<plan>\n(pick a)\n(drop a)\n</plan>", "correa")
    r.check_eq("correa tags parse", (p["parses"], p["path"], p["n_actions"]), (True, "plan_tags", 2))
    p = dp.answer_parses("(pick a)\n(drop a)", "correa")
    r.check("correa without tags does not parse", not p["parses"])
    p = dp.answer_parses("<plan></plan>", "correa")
    r.check("correa empty tags do not parse", not p["parses"])


def test_stats(r: TestResults) -> None:
    vals = list(range(1, 21))
    s = dp._stats(vals + [None])
    r.check_eq("median", s["median"], 10.5)
    r.check_eq("p90 nearest rank", s["p90"], 18)
    r.check_eq("max", s["max"], 20)
    r.check_eq("n skips None", s["n"], 20)
    r.check_eq("p90 of 10 values", dp._q(list(range(1, 11)), 0.9), 9)
    r.check("empty stats", dp._stats([None])["median"] is None)


def _row(cid, out_tok, think_tok, stop="end_turn", answer='{"plan": ["(a)"]}'):
    return {"custom_id": cid, "type": "succeeded", "sdk_version": "0.109.2",
            "model_id": "claude-sonnet-4-6", "stop_reason": stop, "answer": answer,
            "thinking_text": "t" if think_tok else "", "n_thinking_blocks": 1 if think_tok else 0,
            "usage": {"input_tokens": 1000, "output_tokens": out_tok},
            "input_tokens": 1000, "output_tokens": out_tok, "thinking_tokens": think_tok,
            "visible_output_tokens": out_tok - think_tok if think_tok is not None else None,
            "request_settings": {"max_tokens": 64000}}


def test_arm_report_and_estimate(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "a"
        d.mkdir()
        rows = [_row("t0", 5000, 4700), _row("t1", 64000, 63900, stop="max_tokens", answer=""),
                _row("t2", 3000, 2800)]
        (d / "results_full.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
        (d / "batch_info.json").write_text(json.dumps({"wall_seconds": 600}))
        (d / "request_settings.json").write_text(json.dumps({"model": "claude-sonnet-4-6"}))
        rep = dp.arm_report(d, "harness")
        r.check_eq("thinking median", rep["thinking_tokens"]["median"], 4700)
        r.check_eq("visible median", rep["visible_output_tokens"]["median"], 200)
        r.check_eq("stop reasons", rep["stop_reasons"], {"end_turn": 2, "max_tokens": 1})
        r.check_eq("share at max_tokens", round(rep["share_at_max_tokens"], 4), round(1 / 3, 4))
        r.check_eq("parse rate", round(rep["parse_rate"], 4), round(2 / 3, 4))
        want = (3000 * 3 + 72000 * 15) / 1e6
        r.check_eq("list cost from usage", round(rep["cost_list_usd"], 6), round(want, 6))
        r.check_eq("batch cost = list / 2", round(rep["cost_batch_usd"], 6), round(want / 2, 6))
        est = {e["line"]: e for e in dp.full_set_estimate({"a": rep})}
        a_line = est["Sonnet 4.6 thinking on, 300 keys x3"]
        r.check_eq("full-set line from arm mean", a_line["batch_usd"],
                   round(900 * (1000 * 1.5e-6 + 24000 * 7.5e-6), 2))
        r.check("missing arm reported, not guessed",
                est["Haiku 4.5 thinking on, 100 keys x3"]["batch_usd"] is None)
        ctrl = est["Sonnet 4.6 thinking off, T=1, x3"]
        r.check_eq("T=1 control from existing cell means", ctrl["batch_usd"],
                   round(900 * (1457 * 1.5e-6 + 261 * 7.5e-6), 2))
        # No thinking count in usage and no thinking block: all output visible.
        d2 = Path(tmp) / "e"
        d2.mkdir()
        (d2 / "results_full.jsonl").write_text(json.dumps(
            _row("t0", 300, None, answer="<plan>\n(a)\n</plan>")) + "\n")
        (d2 / "batch_info.json").write_text(json.dumps({"wall_seconds": 60}))
        (d2 / "request_settings.json").write_text(json.dumps({"model": "claude-sonnet-4-6"}))
        rep2 = dp.arm_report(d2, "correa")
        r.check_eq("thinking off: visible = output", rep2["visible_output_tokens"]["median"], 300)
        r.check_eq("correa parse", rep2["parse_rate"], 1.0)


def main() -> None:
    r = TestResults("test_d5a_pilot")
    test_pick_keys(r)
    test_answer_parses(r)
    test_stats(r)
    test_arm_report_and_estimate(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
