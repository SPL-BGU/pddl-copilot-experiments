"""tools/tracking/items.py: render and check on small temp fixtures.

Plain-Python test (no pytest dependency), run by tests/verify.sh:
    python3 tests/test_tracking.py
"""
import contextlib
import copy
import importlib.util
import io
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _helpers import TestResults  # noqa: E402

_P = Path(__file__).resolve().parent.parent / "tools/tracking/items.py"
_spec = importlib.util.spec_from_file_location("tracking_items", _P)
items = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(items)

BASE = {
    "workstreams": {"A": "Records", "D": "Experiments", "X": "Unsorted"},
    "lines": [{"id": "ext", "name": "Extension", "state": "under way", "items": ["D1", "D2"],
               "evidence": ["docs/readout.md"]}],
    "items": [
        {"id": "A1", "title": "Old record", "state": "done", "owner": "agent",
         "commit": "abc1234", "evidence": ["docs/readout.md"]},
        {"id": "D1", "title": "Build it", "state": "done", "owner": "agent", "pr": 7,
         "evidence": ["docs/readout.md#part"], "issue": ["ISS-001"]},
        {"id": "D2", "title": "Run it", "state": "todo", "owner": "agent",
         "waits_on": ["D1", "DEC-20260101-01"], "evidence": []},
        {"id": "D3", "title": "Read it", "state": "todo", "owner": "agent",
         "waits_on": ["D2"], "evidence": []},
        {"id": "D4", "title": "Go ahead", "state": "todo", "owner": "agent",
         "needs_omer": "go-ahead", "evidence": []},
        {"id": "X-01", "title": "In review", "state": "review", "owner": "agent",
         "branch": "feat/x", "pr": 9, "evidence": []},
    ],
    "decisions": [
        {"id": "DEC-20260101-01", "question": "Which?", "answer": "This one.",
         "decided": "2026-01-01", "affects": ["D2"], "logged": "2026-01-01 (later)"},
        {"id": "DEC-20260101-02", "question": "Open one?", "affects": ["D3"]},
    ],
}
NOTES = "# notes\n\n## 2026-01-01 (later) — a decision\n\n- text\n"
ISSUES = "# issues\n\n### ISS-001 · a gap\n\n### ~~ISS-002~~ · closed\n"
STATUS = ("# STATUS\n\nhand text\n\n<!-- items:begin lines -->\nold\n<!-- items:end lines -->\n\n"
          "<!-- items:begin start -->\n<!-- items:end start -->\n\n"
          "<!-- items:begin waiting -->\n<!-- items:end waiting -->\n\n"
          "<!-- items:begin workstreams -->\n<!-- items:end workstreams -->\n\n"
          "<!-- items:begin prs -->\n<!-- items:end prs -->\n\n"
          "<!-- items:begin decisions -->\n<!-- items:end decisions -->\n\nmore hand text\n")


def make_repo(data=None, status=STATUS, notes=NOTES):
    root = Path(tempfile.mkdtemp())
    (root / "development").mkdir()
    (root / "docs").mkdir()
    (root / "docs/readout.md").write_text("x\n")
    (root / items.ITEMS).write_text(yaml.safe_dump(data or BASE, sort_keys=False))
    (root / items.STATUS).write_text(status)
    (root / items.PAPER_NOTES).write_text(notes)
    (root / items.OPEN_ISSUES).write_text(ISSUES)
    return root


def render(root):
    with contextlib.redirect_stdout(io.StringIO()):
        items.run_render(root)


def problems_for(data, render_first=True, **kw):
    root = make_repo(data, **kw)
    if render_first:
        render(root)
    loaded = items.load(root)
    return items.check_data(loaded, root) + items.check_status(loaded, root)


def changed(edit):
    data = copy.deepcopy(BASE)
    edit(data)
    return data


def by_id(data, iid):
    return next(i for i in data["items"] if i["id"] == iid)


def has(problems, text):
    return any(text in p for p in problems)


def test_clean_fixture_passes(r):
    r.check_eq("no problems on the clean fixture", problems_for(BASE), [])


def test_render_idempotent(r):
    root = make_repo()
    render(root)
    once = (root / items.STATUS).read_text()
    render(root)
    r.check_eq("second render changes nothing", (root / items.STATUS).read_text(), once)
    r.check("hand text kept", once.startswith("# STATUS\n\nhand text\n")
            and once.endswith("more hand text\n"))
    r.check("old block text replaced", "\nold\n" not in once)


def test_status_stale(r):
    p = problems_for(BASE, render_first=False)
    r.check("unrendered STATUS is out of date", has(p, "STATUS.md blocks out of date"), p)
    p = problems_for(BASE, render_first=False, status="# STATUS\n\nno blocks\n")
    r.check("STATUS without blocks", has(p, "no <!-- items:begin"), p)
    p = problems_for(BASE, render_first=False,
                     status="<!-- items:begin bogus -->\n<!-- items:end bogus -->\n")
    r.check("unknown block name", has(p, "unknown block 'bogus'"), p)


def test_can_start_now(r):
    data = items.load(make_repo())
    r.check_eq("D2 can start (D1 done, decision answered); D3 waits; D4 needs Omer",
               [i["id"] for i in items.can_start(data)], ["D2"])
    d = changed(lambda x: x["decisions"][0].pop("answer") or x["decisions"][0].pop("decided"))
    r.check_eq("unanswered decision holds D2 back", [i["id"] for i in items.can_start(d)], [])
    d = changed(lambda x: by_id(x, "D2").update(state="done", pr=8, evidence=["docs/readout.md"]))
    r.check_eq("D3 can start once D2 is done", [i["id"] for i in items.can_start(d)], ["D3"])
    d = changed(lambda x: by_id(x, "D1").update(state="dropped"))
    r.check_eq("dropped counts as resolved", [i["id"] for i in items.can_start(d)], ["D2"])


def test_waiting_for_omer(r):
    decisions, its = items.waiting_for_omer(items.load(make_repo()))
    r.check_eq("open decision listed", [d["id"] for d in decisions], ["DEC-20260101-02"])
    r.check_eq("items needing Omer, waits resolved", [i["id"] for i in its], ["D4"])


def test_unknown_and_duplicate_ids(r):
    p = problems_for(changed(lambda x: by_id(x, "D3").update(waits_on=["D9"])))
    r.check("waits_on a missing id", has(p, "waits_on 'D9' is not a known"), p)
    p = problems_for(changed(lambda x: x["items"].append(dict(by_id(x, "D4")))))
    r.check("duplicate id", has(p, "D4: duplicate id"), p)
    p = problems_for(changed(lambda x: by_id(x, "D4").update(id="NEW-1")))
    r.check("bad id format", has(p, "'NEW-1': bad id"), p)
    p = problems_for(changed(lambda x: x["decisions"][1].update(id="DEC-2026-1")))
    r.check("bad decision id", has(p, "'DEC-2026-1': bad id"), p)
    p = problems_for(changed(lambda x: x["decisions"][1].update(affects=["Q1"])))
    r.check("affects a missing item", has(p, "affects 'Q1'"), p)
    p = problems_for(changed(lambda x: x["lines"][0].update(items=["Z9"])))
    r.check("line names a missing item", has(p, "item 'Z9' is not a known item"), p)
    p = problems_for(changed(lambda x: by_id(x, "D4").update(id="Q1")))
    r.check("workstream not listed", has(p, "workstream 'Q' is not listed"), p)


def test_cycle(r):
    def loop(x):
        by_id(x, "D2").update(waits_on=["D3"])
        by_id(x, "D3").update(waits_on=["D4"])
        by_id(x, "D4").update(waits_on=["D2"])
    p = problems_for(changed(loop))
    r.check("three-step loop found", has(p, "waits_on loop: D2 -> D3 -> D4 -> D2"), p)
    r.check_eq("found once", sum("loop" in x for x in p), 1)
    p = problems_for(changed(lambda x: by_id(x, "D4").update(waits_on=["D4"])))
    r.check("self loop found", has(p, "waits_on loop: D4 -> D4"), p)


def test_evidence_and_done(r):
    p = problems_for(changed(lambda x: by_id(x, "D2").update(evidence=["docs/missing.md"])))
    r.check("missing evidence path", has(p, "'docs/missing.md' does not exist"), p)
    p = problems_for(changed(lambda x: by_id(x, "D1").update(evidence=[])))
    r.check("done without evidence", has(p, "D1: done but cites no evidence"), p)
    p = problems_for(changed(lambda x: by_id(x, "D1").pop("pr")))
    r.check("done without PR or commit", has(p, "D1: done but names no PR"), p)
    p = problems_for(changed(lambda x: by_id(x, "X-01").pop("pr") and by_id(x, "X-01").pop("branch")))
    r.check("review without PR or branch", has(p, "X-01: in review but names no PR"), p)
    p = problems_for(changed(lambda x: by_id(x, "D4").update(state="blocked")))
    r.check("blocked on nothing, no hold", has(p, "D4: blocked, but"), p)
    p = problems_for(changed(lambda x: by_id(x, "D4").update(state="blocked", hold="R7")))
    r.check("blocked with a hold reason is fine", not has(p, "D4: blocked"), p)
    p = problems_for(changed(lambda x: by_id(x, "D1").update(pr="seven")))
    r.check("pr not a number", has(p, "pr 'seven' is not a number"), p)


def test_enums_and_fields(r):
    p = problems_for(changed(lambda x: by_id(x, "D2").update(state="waiting")))
    r.check("bad state", has(p, "state 'waiting' is not one of"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").update(owner="bob")))
    r.check("bad owner", has(p, "owner 'bob'"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").update(needs_omer="maybe")))
    r.check("bad needs_omer", has(p, "needs_omer 'maybe'"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").update(staet="todo")))
    r.check("unknown field", has(p, "unknown field 'staet'"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").pop("title")))
    r.check("missing title", has(p, "missing field 'title'"), p)


def test_issues(r):
    p = problems_for(changed(lambda x: by_id(x, "D2").update(issue=["ISS-002"])))
    r.check("closed (struck) issue still found", not has(p, "ISS-002"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").update(issue="ISS-099")))
    r.check("issue not in OPEN_ISSUES", has(p, "ISS-099 has no entry"), p)
    p = problems_for(changed(lambda x: by_id(x, "D2").update(issue=["iss27"])))
    r.check("issue bad form", has(p, "'iss27' is not of the form"), p)


def test_decision_log(r):
    p = problems_for(BASE, notes="# notes\n\n## 2026-01-02 — other\n")
    r.check("answered decision without its entry", has(p, "DEC-20260101-01: no paper_notes"), p)
    p = problems_for(BASE, notes="# notes\n\n## 2026-01-01 — a different heading\n")
    r.check("logged names a heading that is not there", has(p, "DEC-20260101-01: no paper_notes"), p)
    p = problems_for(BASE, notes="# notes\n\n- see DEC-20260101-01\n")
    r.check("the id anywhere is enough", not has(p, "paper_notes"), p)
    d = changed(lambda x: x["decisions"][0].pop("logged"))
    p = problems_for(d, notes="# notes\n\n## 2026-01-01 — any\n")
    r.check("without 'logged', the date heading is enough", not has(p, "paper_notes"), p)
    p = problems_for(changed(lambda x: x["decisions"][0].pop("decided")))
    r.check("answer without a date", has(p, "has an answer but no 'decided'"), p)
    p = problems_for(changed(lambda x: x["decisions"][1].update(decided="2026-01-01")))
    r.check("date without an answer", has(p, "'decided' date but no answer"), p)


def test_github_checks(r):
    data = items.load(make_repo())
    merged = {7: {"state": "closed", "merged": True}, 9: {"state": "closed", "merged": True}}
    p, notes = items.check_github(data, {"main"}, merged.get)
    r.check("open item whose PR merged", has(p, "X-01: PR #9 is merged"), p)
    r.check("branch not on origin", has(p, "branch 'feat/x' is not on origin"), p)
    r.check_eq("no notes when both checks ran", notes, [])
    p, _ = items.check_github(data, {"feat/x"}, {7: {"state": "open", "merged": False},
                                                9: {"state": "open", "merged": False}}.get)
    r.check("done item whose PR is not merged", has(p, "D1: marked done but PR #7"), p)
    r.check("open review PR is fine", not has(p, "X-01"), p)
    p, notes = items.check_github(data, None, None)
    r.check_eq("nothing checked offline", p, [])
    r.check("both skips noted", len(notes) == 2 and all("skipped" in n for n in notes), notes)

    def boom(n):
        raise OSError("no network")
    p, notes = items.check_github(data, {"feat/x"}, boom)
    r.check("network error is a note, not a problem", p == [] and has(notes, "no network"),
            (p, notes))


def test_repo_items_file(r):
    """The real development/items.yaml passes the offline checks."""
    root = Path(__file__).resolve().parent.parent
    data = items.load(root)
    p = items.check_data(data, root) + items.check_status(data, root)
    r.check_eq("development/items.yaml and STATUS.md agree", p, [])


ALL = (test_clean_fixture_passes, test_render_idempotent, test_status_stale,
       test_can_start_now, test_waiting_for_omer, test_unknown_and_duplicate_ids, test_cycle,
       test_evidence_and_done, test_enums_and_fields, test_issues, test_decision_log,
       test_github_checks, test_repo_items_file)

if __name__ == "__main__":
    r = TestResults("test_tracking")
    for fn in ALL:
        fn(r)
    r.report_and_exit()
