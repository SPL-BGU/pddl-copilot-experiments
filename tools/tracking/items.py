"""Render and check the tracking file, development/items.yaml (Design A).

items.yaml holds every open item, the steps done since 2026-10-10, and every
decision. This script does two jobs:

  render  rewrites the blocks between marker comments in development/STATUS.md:
              <!-- items:begin NAME -->
              ... generated text ...
              <!-- items:end NAME -->
          NAME is one of: lines, workstreams, waiting, start, prs, decisions.
  check   prints one plain line per problem and exits 1 if there is any:
          bad or duplicate ids, unknown fields or enum values, a waits_on that
          names a missing id or forms a loop, a missing evidence path, a done
          item without evidence or PR, a decision without its dated
          paper_notes entry, a STATUS block that differs from `render`.
          With network it also asks git and GitHub: a branch that is not on
          origin, a PR listed as open that is merged. `--offline` skips those.

Usage (from the repo root):
  python3 tools/tracking/items.py render
  python3 tools/tracking/items.py check [--offline]

Only the standard library and PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ITEMS = "development/items.yaml"
STATUS = "development/STATUS.md"
PAPER_NOTES = "development/paper_notes_discussions.md"
OPEN_ISSUES = "development/OPEN_ISSUES.md"

STATES = ("todo", "doing", "blocked", "review", "done", "dropped")
CLOSED = ("done", "dropped")
OWNERS = ("agent", "omer")
NEEDS = ("none", "decide", "read", "go-ahead", "merge")

ITEM_KEYS = {"id", "title", "state", "owner", "waits_on", "needs_omer", "branch", "pr",
             "commit", "evidence", "plan", "issue", "was", "hold", "note", "updated"}
DECISION_KEYS = {"id", "question", "answer", "decided", "affects", "logged", "note"}
LINE_KEYS = {"id", "name", "state", "items", "evidence"}

ITEM_ID = re.compile(r"^(?:[A-WYZ]\d+[a-z]?|X-\d{2})$")
DEC_ID = re.compile(r"^DEC-\d{8}-\d{2}$")
LINE_ID = re.compile(r"^[a-z][a-z0-9-]*$")
ISS_ID = re.compile(r"^ISS-\d{3}$")
BLOCK = re.compile(r"(<!-- items:begin (\S+) -->\n)(.*?)(<!-- items:end \2 -->)", re.S)


# ---------------------------------------------------------------- loading

def load(root: Path) -> dict:
    data = yaml.safe_load((root / ITEMS).read_text()) or {}
    data.setdefault("workstreams", {})
    for key in ("items", "decisions", "lines"):
        data[key] = data.get(key) or []
    return data


def as_list(value) -> list:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def is_open(item: dict) -> bool:
    return item.get("state") not in CLOSED


def resolved_ids(data: dict) -> set:
    """Ids that no longer hold anything up: closed items and answered decisions."""
    done = {i["id"] for i in data["items"] if i.get("state") in CLOSED}
    return done | {d["id"] for d in data["decisions"] if d.get("answer")}


def unresolved_waits(item: dict, resolved: set) -> list:
    return [w for w in as_list(item.get("waits_on")) if w not in resolved]


def workstream_of(item_id: str) -> str:
    return "X" if item_id.startswith("X-") else item_id[0]


# ---------------------------------------------------------------- render

def cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|") if text not in (None, "") else "-"


def pr_text(item: dict) -> str:
    prs = ", ".join(f"#{n}" for n in as_list(item.get("pr")))
    if prs:
        return prs
    if item.get("branch"):
        return f"`{item['branch']}`"
    if item.get("commit"):
        return f"`{item['commit']}` (record-only)"
    return "-"


def state_text(item: dict) -> str:
    needs = item.get("needs_omer", "none")
    state = item.get("state")
    return state if needs == "none" or not is_open(item) else f"{state} (Omer: {needs})"


def can_start(data: dict) -> list:
    """Open agent items, todo or doing, needing nothing from Omer, all waits resolved."""
    resolved = resolved_ids(data)
    return [i for i in data["items"]
            if i.get("state") in ("todo", "doing") and i.get("owner") == "agent"
            and i.get("needs_omer", "none") == "none" and not unresolved_waits(i, resolved)]


def waiting_for_omer(data: dict) -> tuple[list, list]:
    """(open decisions, open items Omer can act on now: they need him or he owns them,
    and nothing they wait on is still open)."""
    resolved = resolved_ids(data)
    decisions = [d for d in data["decisions"] if not d.get("answer")]
    items = [i for i in data["items"] if is_open(i) and not unresolved_waits(i, resolved)
             and (i.get("needs_omer", "none") != "none" or i.get("owner") == "omer")]
    return decisions, items


def with_note(text: str, note) -> str:
    return f"{text} {' '.join(str(note).split())}" if note else text


def render_lines(data: dict) -> str:
    by_id = {i["id"]: i for i in data["items"]}
    out = ["| line | state | open items |", "|---|---|---|"]
    for line in data["lines"]:
        open_ids = [f"{i} ({by_id[i].get('state')})" for i in as_list(line.get("items"))
                    if i in by_id and is_open(by_id[i])]
        out.append(f"| {cell(line.get('name'))} | {cell(line.get('state'))} | "
                   f"{cell(', '.join(open_ids) or 'none')} |")
    return "\n".join(out)


def render_workstreams(data: dict) -> str:
    resolved = resolved_ids(data)
    out = []
    for ws, name in data["workstreams"].items():
        items = [i for i in data["items"] if workstream_of(i["id"]) == ws]
        if not items:
            continue
        n_open = sum(is_open(i) for i in items)
        out += [f"**{ws}. {name}** ({n_open} open, {len(items) - n_open} closed)", "",
                "| id | what | state | waits on | PR or branch |", "|---|---|---|---|---|"]
        for i in items:
            waits = ", ".join(unresolved_waits(i, resolved)) if is_open(i) else ""
            out.append(f"| {i['id']} | {cell(i.get('title'))} | {cell(state_text(i))} | "
                       f"{cell(waits)} | {cell(pr_text(i))} |")
        out.append("")
    return "\n".join(out).rstrip()


def render_waiting(data: dict) -> str:
    decisions, items = waiting_for_omer(data)
    out = [with_note(f"- **{d['id']}** (open decision): {' '.join(str(d.get('question', '?')).split())}",
                     d.get("note")) for d in decisions]
    for i in items:
        what = i.get("needs_omer", "none")
        what = "your task" if what == "none" else what
        out.append(with_note(f"- **{i['id']}** ({what}; {i.get('state')}): {i.get('title', '?')}.",
                             i.get("hold") or i.get("note")))
    return "\n".join(out) or "- nothing"


def render_start(data: dict) -> str:
    out = [f"- **{i['id']}**: {i.get('title', '?')}." for i in can_start(data)]
    return "\n".join(out) or "- nothing"


def render_prs(data: dict) -> str:
    out = []
    for i in data["items"]:
        if is_open(i) and (i.get("pr") or i.get("branch")) and i["state"] in ("doing", "review"):
            needs = i.get("needs_omer", "none")
            who = "" if needs == "none" else f"; Omer: {needs}"
            out.append(with_note(f"- **{i['id']}** ({pr_text(i)}; {i.get('state')}{who}): "
                                 f"{i.get('title', '?')}.", i.get("note")))
    return "\n".join(out) or "- none"


def render_decisions(data: dict) -> str:
    out = []
    for d in data["decisions"]:
        if not d.get("answer"):
            continue
        affects = ", ".join(as_list(d.get("affects"))) or "-"
        text = (f"- **{d['id']}** ({d.get('decided')}) {' '.join(str(d.get('question', '?')).split())} "
                f"**Answer:** {' '.join(str(d['answer']).split())}")
        out.append(with_note(text, d.get("note")) + f" *Affects {affects}; logged in "
                   f"paper_notes \"{d.get('logged') or d.get('decided')}\".*")
    return "\n".join(out) or "- none"


RENDERERS = {"lines": render_lines, "workstreams": render_workstreams,
             "waiting": render_waiting, "start": render_start, "prs": render_prs,
             "decisions": render_decisions}


def render_status(text: str, data: dict) -> tuple[str, list]:
    """Return STATUS text with every block re-rendered, and the problems found."""
    problems = []

    def repl(m):
        name = m.group(2)
        if name not in RENDERERS:
            problems.append(f"STATUS.md: unknown block '{name}' (known: {', '.join(RENDERERS)})")
            return m.group(0)
        return f"{m.group(1)}{RENDERERS[name](data)}\n{m.group(4)}"

    new = BLOCK.sub(repl, text)
    begins = re.findall(r"<!-- items:begin (\S+) -->", text)
    ends = re.findall(r"<!-- items:end (\S+) -->", text)
    if not begins:
        problems.append("STATUS.md: no <!-- items:begin NAME --> blocks found")
    if sorted(begins) != sorted(ends) or len(BLOCK.findall(text)) != len(begins):
        problems.append("STATUS.md: a begin marker has no matching end marker (or the reverse)")
    return new, problems


# ---------------------------------------------------------------- check

def check_fields(kind: str, obj: dict, allowed: set, required: tuple) -> list:
    oid = obj.get("id", "?")
    problems = [f"{kind} {oid}: unknown field '{k}'" for k in obj if k not in allowed]
    problems += [f"{kind} {oid}: missing field '{k}'" for k in required if not obj.get(k)]
    return problems


def find_cycles(data: dict) -> list:
    """Each loop in the waits_on graph, as a list of ids, found once."""
    graph = {i["id"]: as_list(i.get("waits_on")) for i in data["items"]}
    color, cycles, stack = {}, [], []

    def visit(node):
        color[node] = "grey"
        stack.append(node)
        for nxt in graph.get(node, []):
            if color.get(nxt) == "grey":
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif nxt in graph and nxt not in color:
                visit(nxt)
        stack.pop()
        color[node] = "black"

    for node in graph:
        if node not in color:
            visit(node)
    return cycles


def heading_found(notes: str, dec: dict) -> bool:
    """A dated '## ' heading in paper_notes for this decision, or its id anywhere."""
    if dec["id"] in notes:
        return True
    decided, logged = str(dec.get("decided") or ""), dec.get("logged")
    for line in notes.splitlines():
        if not line.startswith("## "):
            continue
        head = line[3:]
        if (head.startswith(str(logged)) if logged else head.startswith(decided)) and decided in head:
            return True
    return False


def check_data(data: dict, root: Path) -> list:
    """Every offline check except the STATUS comparison."""
    problems = []
    items, decisions, lines = data["items"], data["decisions"], data["lines"]
    workstreams = data["workstreams"]
    notes_path, issues_path = root / PAPER_NOTES, root / OPEN_ISSUES
    notes = notes_path.read_text() if notes_path.exists() else ""
    issues_text = issues_path.read_text() if issues_path.exists() else ""
    known_issues = set(re.findall(r"^### (?:~~)?(ISS-\d{3})", issues_text, re.M))

    seen = {}
    for kind, objs, pattern in (("item", items, ITEM_ID), ("decision", decisions, DEC_ID),
                                ("line", lines, LINE_ID)):
        for o in objs:
            oid = o.get("id")
            if not isinstance(oid, str) or not pattern.match(oid):
                problems.append(f"{kind} {oid!r}: bad id (see the schema note in items.yaml)")
            if oid in seen:
                problems.append(f"{kind} {oid}: duplicate id (also a {seen[oid]})")
            seen[oid] = kind
    item_ids = {i.get("id") for i in items}
    wait_ids = item_ids | {d.get("id") for d in decisions}

    def paths_exist(owner: str, paths) -> None:
        for p in as_list(paths):
            if not (root / str(p).split("#")[0]).exists():
                problems.append(f"{owner}: evidence path '{p}' does not exist")

    resolved = resolved_ids(data)
    for i in items:
        iid = i.get("id", "?")
        problems += check_fields("item", i, ITEM_KEYS, ("id", "title", "state", "owner"))
        if isinstance(iid, str) and ITEM_ID.match(iid) and workstream_of(iid) not in workstreams:
            problems.append(f"item {iid}: workstream '{workstream_of(iid)}' is not listed")
        for key, allowed in (("state", STATES), ("owner", OWNERS), ("needs_omer", NEEDS)):
            value = i.get(key, "none" if key == "needs_omer" else None)
            if value not in allowed:
                problems.append(f"item {iid}: {key} '{value}' is not one of {', '.join(allowed)}")
        for w in as_list(i.get("waits_on")):
            if w not in wait_ids:
                problems.append(f"item {iid}: waits_on '{w}' is not a known item or decision")
        for n in as_list(i.get("pr")):
            if not isinstance(n, int) or isinstance(n, bool):
                problems.append(f"item {iid}: pr '{n}' is not a number")
        for iss in as_list(i.get("issue")):
            if not ISS_ID.match(str(iss)):
                problems.append(f"item {iid}: issue '{iss}' is not of the form ISS-###")
            elif iss not in known_issues:
                problems.append(f"item {iid}: issue {iss} has no entry in OPEN_ISSUES.md")
        paths_exist(f"item {iid}", i.get("evidence"))
        state = i.get("state")
        if state == "done":
            if not as_list(i.get("evidence")):
                problems.append(f"item {iid}: done but cites no evidence")
            if not as_list(i.get("pr")) and not i.get("commit"):
                problems.append(f"item {iid}: done but names no PR (or commit, for a record-only step)")
        if state == "review" and not (as_list(i.get("pr")) or i.get("branch")):
            problems.append(f"item {iid}: in review but names no PR or branch")
        if state == "blocked" and not unresolved_waits(i, resolved) and not i.get("hold"):
            problems.append(f"item {iid}: blocked, but everything it waits on is resolved "
                            f"and it gives no 'hold' reason")
    for cycle in find_cycles(data):
        problems.append(f"waits_on loop: {' -> '.join(cycle)}")

    for d in decisions:
        did = d.get("id", "?")
        problems += check_fields("decision", d, DECISION_KEYS, ("id", "question"))
        for a in as_list(d.get("affects")):
            if a not in item_ids:
                problems.append(f"decision {did}: affects '{a}' is not a known item")
        if d.get("answer") and not d.get("decided"):
            problems.append(f"decision {did}: has an answer but no 'decided' date")
        if d.get("decided") and not d.get("answer"):
            problems.append(f"decision {did}: has a 'decided' date but no answer")
        if d.get("answer") and d.get("decided") and not heading_found(notes, d):
            where = f"'## {d.get('logged')}'" if d.get("logged") else f"a '## {d.get('decided')}' heading"
            problems.append(f"decision {did}: no paper_notes entry found ({where}, or the id); "
                            f"append the dated entry")

    for line in lines:
        lid = line.get("id", "?")
        problems += check_fields("line", line, LINE_KEYS, ("id", "name", "state"))
        for i in as_list(line.get("items")):
            if i not in item_ids:
                problems.append(f"line {lid}: item '{i}' is not a known item")
        paths_exist(f"line {lid}", line.get("evidence"))
    return problems


def check_status(data: dict, root: Path) -> list:
    path = root / STATUS
    if not path.exists():
        return [f"{STATUS} does not exist"]
    text = path.read_text()
    new, problems = render_status(text, data)
    if new != text:
        stale = [m.group(2) for m, n in zip(BLOCK.finditer(text), BLOCK.finditer(new))
                 if m.group(0) != n.group(0)]
        problems.append(f"STATUS.md blocks out of date ({', '.join(stale)}): run "
                        f"`python3 tools/tracking/items.py render`")
    return problems


# ---------------------------------------------------------------- GitHub

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          timeout=60, check=True).stdout


def remote_branches(root: Path):
    """Branch names on origin, or None when git cannot reach it."""
    try:
        out = git(root, "ls-remote", "--heads", "origin")
    except (subprocess.SubprocessError, OSError):
        return None
    return {ln.split("refs/heads/", 1)[1] for ln in out.splitlines() if "refs/heads/" in ln}


def repo_slug(root: Path):
    try:
        url = git(root, "remote", "get-url", "origin").strip()
    except (subprocess.SubprocessError, OSError):
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def pr_fetcher(slug: str):
    """A function PR number -> {'state', 'merged'}; uses GITHUB_TOKEN, else `gh`."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def via_api(n):
        req = urllib.request.Request(f"https://api.github.com/repos/{slug}/pulls/{n}",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)

    def via_gh(n):
        out = subprocess.run(["gh", "api", f"repos/{slug}/pulls/{n}"], capture_output=True,
                             text=True, timeout=30, check=True).stdout
        return json.loads(out)

    fetch = via_api if token else via_gh

    def get(n):
        d = fetch(n)
        return {"state": d["state"], "merged": bool(d.get("merged_at")), "draft": d.get("draft")}
    return get


def check_github(data: dict, branches, get_pr) -> tuple[list, list]:
    """(problems, notes). `branches` is a set or None; `get_pr` a function or None."""
    problems, notes = [], []
    if branches is None:
        notes.append("note: branch check skipped (git ls-remote origin failed)")
    if get_pr is None:
        notes.append("note: PR check skipped (no GitHub access)")
    for i in data["items"]:
        iid, branch = i["id"], i.get("branch")
        if branches is not None and branch and is_open(i) and branch not in branches:
            problems.append(f"item {iid}: branch '{branch}' is not on origin (push it)")
        if get_pr is None:
            continue
        for n in as_list(i.get("pr")):
            try:
                pr = get_pr(n)
            except Exception as exc:  # network or auth: skip the rest, say so
                notes.append(f"note: PR check stopped at #{n} ({exc.__class__.__name__}: {exc})")
                get_pr = None
                break
            if i.get("state") == "done" and not pr["merged"]:
                problems.append(f"item {iid}: marked done but PR #{n} is not merged")
            elif is_open(i) and pr["merged"]:
                problems.append(f"item {iid}: PR #{n} is merged on GitHub; mark the item done")
            elif is_open(i) and pr["state"] == "closed":
                problems.append(f"item {iid}: PR #{n} was closed without merging")
    return problems, notes


# ---------------------------------------------------------------- CLI

def run_check(root: Path, offline: bool) -> int:
    data = load(root)
    problems = check_data(data, root) + check_status(data, root)
    notes = ["note: GitHub checks skipped (--offline)"] if offline else []
    if not offline:
        slug = repo_slug(root)
        more, notes = check_github(data, remote_branches(root), pr_fetcher(slug) if slug else None)
        problems += more
    for n in notes:
        print(n)
    for p in problems:
        print(f"problem: {p}")
    if problems:
        print(f"{len(problems)} problem(s) in {ITEMS}")
        return 1
    print(f"OK: {len(data['items'])} items, {len(data['decisions'])} decisions, "
          f"{len(data['lines'])} lines; STATUS.md is up to date")
    return 0


def run_render(root: Path) -> int:
    data = load(root)
    path = root / STATUS
    new, problems = render_status(path.read_text(), data)
    for p in problems:
        print(f"problem: {p}")
    if problems:
        return 1
    path.write_text(new)
    print(f"rendered {len(BLOCK.findall(new))} block(s) into {STATUS}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=("render", "check"))
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                    help="repo root (default: the repo this script sits in)")
    ap.add_argument("--offline", action="store_true", help="skip the git and GitHub checks")
    args = ap.parse_args(argv)
    if args.command == "render":
        return run_render(args.root)
    return run_check(args.root, args.offline)


if __name__ == "__main__":
    sys.exit(main())
