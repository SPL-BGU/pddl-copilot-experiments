"""Pure helpers of tools/reanalysis/c4_select_transcripts.py (no results needed).

Plain-Python test (no pytest dependency), run by tests/verify.sh:
    python3 tests/test_c4_select_transcripts.py
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _helpers import TestResults  # noqa: E402

_P = Path(__file__).resolve().parent.parent / "tools/reanalysis/c4_select_transcripts.py"
_spec = importlib.util.spec_from_file_location("c4_select_transcripts", _P)
c4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c4)


def test_fence(r):
    out = c4.fence("before\n```\n(a)\n```\nafter")
    r.check("fence outlasts inner backticks",
            out.startswith("````text\n") and out.endswith("\n````"))
    r.check("plain fence is three backticks", c4.fence("plain").startswith("```text\n"))


def test_abridge_lines(r):
    text = "\n".join(str(i) for i in range(20))
    r.check_eq("abridge marks the cut", c4.abridge_lines(text, 3, 2, "x").splitlines(),
               ["0", "1", "2", "[... 15 lines of x elided ...]", "18", "19"])
    r.check_eq("short text unchanged", c4.abridge_lines("a\nb\nc", 3, 2, "x"), "a\nb\nc")


def test_keep_windows(r):
    lines = [str(i) for i in range(10)]
    r.check_eq("every gap marked", c4.keep_windows(lines, [(0, 1), (5, 6)], "y").splitlines(),
               ["0", "1", "[... 3 lines of y elided ...]", "5", "6",
                "[... 3 lines of y elided ...]"])


def test_doubt_flag(r):
    r.check_eq("doubtful", c4.doubt_flag("", "Right verdict, doubtful reason."), "doubtful")
    r.check_eq("loose", c4.doubt_flag("Step numbering is loose", ""), "loose")
    r.check_eq("benign note", c4.doubt_flag("", "long numeric trace"), None)
    r.check_eq("missing note", c4.doubt_flag(None, ""), None)


def test_draw_order(r):
    ids = [f"id{i}" for i in range(50)]
    a = c4.draw_order(ids, 1)
    r.check_eq("input order does not matter", a, c4.draw_order(list(reversed(ids)), 1))
    r.check("pool number changes the order", a != c4.draw_order(ids, 2))
    r.check_eq("a permutation", sorted(a), sorted(ids))


def test_pick(r):
    got, skipped = c4.pick(["a", "b", "c"],
                           {"a": ("rejected", "why"), "b": ("confirmed", "ok")})
    r.check_eq("first not rejected", got, "b")
    r.check_eq("rejected listed", skipped, [("a", "why")])


def test_plan_actions(r):
    for plan in (["(pick a)", "(move a b)"], ["pick a", "move a b"],
                 '["pick a", "move a b"]', "(pick a)\n(move a b)\n", "(pick a)(move  A b)"):
        r.check_eq(f"plan form {plan!r}", c4.plan_actions(plan), ("pick a", "move a b"))


def test_same_text(r):
    r.check_eq("exact", c4.same_text("(a b)", "(a b)"), "exact")
    r.check_eq("whitespace", c4.same_text("(a  b)\n", "(a b)"), "whitespace")
    r.check_eq("comments", c4.same_text(";; note\n(a b)", "(a b)"), "comments")
    r.check_eq("different", c4.same_text("(a b)", "(a c)"), None)


def test_plan_shape(r):
    t = ("(a)", "(b)")
    r.check_eq("identical", c4.plan_shape(t, t), "identical")
    r.check_eq("appended", c4.plan_shape(t, t + ("(on x y)",)), "tool plan, then extra lines")
    r.check_eq("prepended", c4.plan_shape(t, ("(z)",) + t), "extra lines, then tool plan")
    r.check_eq("same length", c4.plan_shape(t, ("(a)", "(c)")),
               "same length, some actions differ")
    r.check_eq("other", c4.plan_shape(t, ("(c)",)), "other")


def test_run_diffs(r):
    tool = ("(d)",) * 3 + ("(r)",) + ("(u)",) * 2
    ans = ("(d)",) * 2 + ("(r)",) + ("(u)",) * 3
    r.check_eq("miscounted runs", c4.run_diffs(tool, ans),
               [{"tool": ("(d)", 3, 1), "answer": ("(d)", 2, 1)},
                {"tool": ("(u)", 2, 5), "answer": ("(u)", 3, 4)}])


def test_goal_text(r):
    g = c4.goal_text("(define (problem x) (:init (on a b)) (:goal (and (on b a))))")
    r.check("goal atom kept", "(on b a)" in g)
    r.check("init atom dropped", "(on a b)" not in g)


def test_wrong_facts_split(r):
    from collections import Counter
    shapes = Counter({"tool plan, then extra lines": 18, "other": 10,
                      "extra lines, then tool plan": 5, "same length, some actions differ": 5})
    total, goal, text = c4.wrong_facts_split(shapes, 17)
    r.check_eq("total and goal rows", (total, goal), (38, 17))
    r.check_eq("the other rows, by shape", text,
               "5 keep the tool plan's length with some actions changed (example 4's pool); "
               "5 have extra lines before the tool plan; 1 has the tool plan followed by "
               "extra lines that are not all goal facts; 10 have some other shape, not "
               "classified further")
    r.check("a shape with no rows left is not named",
            "followed by" not in c4.wrong_facts_split(Counter(
                {"tool plan, then extra lines": 2, "other": 1}), 2)[2])


def test_tokens_text(r):
    from types import SimpleNamespace as NS
    base = dict(prompt=25517, completion=5140, turns=3, ctx_no_room_turns=0)
    clipped = NS(**base, ctx_clipped_turns=2, ctx_clip_last_turn_max_tokens=4910,
                 ctx_clip_last_turn_prompt_tokens=11474)
    r.check_eq("clipped last turn shown", c4.tokens_text(clipped, "stop"),
               "prompt 25,517 (summed over turns), completion 5,140, turns 3, clipped turns 2 "
               "(last turn clipped to max_tokens 4,910, its prompt 11,474 tokens), no-room "
               "turns 0, done_reason `stop`")
    plain = NS(**base, ctx_clipped_turns=0, ctx_clip_last_turn_max_tokens=None,
               ctx_clip_last_turn_prompt_tokens=None)
    r.check("no clip: count only", "clipped turns 0, no-room" in c4.tokens_text(plain, "stop"))


if __name__ == "__main__":
    r = TestResults("test_c4_select_transcripts")
    for fn in (test_fence, test_abridge_lines, test_keep_windows, test_doubt_flag,
               test_draw_order, test_pick, test_plan_actions, test_same_text,
               test_plan_shape, test_run_diffs, test_goal_text, test_wrong_facts_split,
               test_tokens_text):
        fn(r)
    r.report_and_exit()
