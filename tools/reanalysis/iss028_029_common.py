"""Shared helpers of the ISS-028 and ISS-029 checks (`iss028_goal_trailers.py`,
`iss029_simulate_plan.py`).

Both checks read the delivered rerun through the frozen package
`tools/delivered_rerun` (package hash `822aace...`), imported read-only and never
edited. They are post hoc and descriptive: the frozen readout
(`development/reference/delivered_rerun_readout.json`) stays the record, and every
figure they print sits beside the frozen one, labelled post hoc.

Everything above the `# --- data` line is pure (no results, no validator), so that
tests/test_iss028_iss029.py can check it on small synthetic inputs.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# The frozen corpora were graded with this pyval release. 0.1.6 folds case
# (ISS-027), so a re-grade under it would not reproduce the frozen grades.
PYVAL_EXPECTED = "0.1.5"

# Logical and numeric heads that are never a goal atom.
_OPERATORS = frozenset({"and", "or", "not", "imply", "forall", "exists", "when",
                        ">=", "<=", ">", "<", "=", "+", "-", "*", "/",
                        "increase", "decrease", "assign"})


class Halt(Exception):
    """A failed self-check: the script exits non-zero and writes nothing."""


def norm_action(a: str) -> str:
    """Whitespace collapsed, lower case (the frozen E4 `_norm_action`)."""
    return " ".join(str(a).split()).lower()


def row_id(r) -> str:
    """The trial id C4 uses: model|task|arm|domain|problem|plan label|v<variant>."""
    return (f"{r.model_tag}|{r.task}|{r.arm}|{r.domain}|{r.problem}|{r.plan_label}"
            f"|v{r.variant}")


def goal_section(problem_pddl: str) -> str:
    """The text of the problem's `(:goal ...)` section, comments removed, or ''."""
    text = re.sub(r";[^\n]*", "", problem_pddl)
    m = re.search(r"\(\s*:goal\b", text, re.IGNORECASE)
    if not m:
        return ""
    i, depth = m.end(), 1
    while depth and i < len(text):
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _sexp(text: str) -> list:
    """The parenthesised groups of `text` as nested lists of lower-case symbols."""
    stack: list[list] = [[]]
    for tok in re.findall(r"\(|\)|[^\s()]+", text.lower()):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            if len(stack) > 1:
                done = stack.pop()
                stack[-1].append(done)
        else:
            stack[-1].append(tok)
    return stack[0]


def goal_atoms(problem_pddl: str) -> frozenset[str]:
    """The positive atoms of the goal, each as `(pred arg ...)`, lower case,
    whitespace collapsed. The goal is walked from the top: `and`, `or`, `imply`,
    `forall`, `exists` are entered; anything under `not` or a numeric comparison
    is left out (a negated fact or a fluent is not a fact the plan makes true); a
    group of plain symbols is an atom."""
    out = set()

    def walk(node):
        if not isinstance(node, list) or not node:
            return
        head = node[0]
        if isinstance(head, list):
            for x in node:
                walk(x)
            return
        if head in ("and", "or", "imply", "forall", "exists"):
            for x in node[(2 if head in ("forall", "exists") else 1):]:
                walk(x)
            return
        if head in _OPERATORS:
            return
        if all(isinstance(x, str) for x in node):
            out.add("(" + " ".join(node) + ")")
    for top in _sexp(goal_section(problem_pddl)):
        walk(top)
    return frozenset(out)


def as_atom(line: str) -> str:
    """A plan line in the form `goal_atoms` uses: `(a b c)`, lower case."""
    s = norm_action(line)
    if s.startswith("(") and s.endswith(")"):
        s = norm_action(s[1:-1])
    return f"({s})"


def plan_shape(tool: tuple, answer: tuple) -> str:
    """How a delivered plan differs from the tool's plan (the C4 shapes, PR #128)."""
    if answer == tool:
        return "identical"
    if len(answer) > len(tool) and answer[:len(tool)] == tool:
        return "tool plan, then extra lines"
    if len(answer) > len(tool) and answer[-len(tool):] == tool:
        return "extra lines, then tool plan"
    if len(answer) == len(tool):
        return "same length, some actions differ"
    return "other"


GOAL_TRAILER = "goal_trailer"      # (a)
COPY_ERROR = "copy_error"          # (b)
OTHER = "other"                    # (c)
CLASSES = (GOAL_TRAILER, COPY_ERROR, OTHER)


def classify_wrong_facts(tool: tuple, answer: tuple, goals: frozenset) -> tuple[str, str]:
    """(class, shape) of one solve row the frozen E4 labels WRONG_FACTS.

    Rule (first match wins; `tool` and `answer` are normalised action tuples):
      (a) goal_trailer: the answer is the tool's plan, action for action, followed
          by one or more lines, and every one of those lines is a positive atom of
          the problem's goal (`goal_atoms`, compared as `as_atom`).
      (b) copy_error: the answer has exactly as many actions as the tool's plan
          and differs from it in at least one (a copying error by construction).
      (c) other: anything else (extra lines before the plan, a trailer that is not
          all goal facts, a different length, ...); its C4 shape is kept.
    """
    shape = plan_shape(tool, answer)
    if shape == "tool plan, then extra lines" and all(
            as_atom(x) in goals for x in answer[len(tool):]):
        return GOAL_TRAILER, shape
    if shape == "same length, some actions differ":
        return COPY_ERROR, shape
    return OTHER, shape


def strip_goal_trailer(plan: tuple, goals: frozenset) -> tuple | None:
    """The plan with its trailing run of goal atoms removed, or None when the last
    line is not a goal atom or nothing would be left. Post hoc extractor rule: it
    never touches a line before the last non-goal line."""
    i = len(plan)
    while i > 0 and as_atom(plan[i - 1]) in goals:
        i -= 1
    if i == len(plan) or i == 0:
        return None
    return tuple(plan[:i])


def c4_goal_rule(tool: tuple, answer: tuple, problem_pddl: str) -> bool:
    """The C4 rule (PR #128, `pools()` pool 4) as written there: every extra line
    is a substring of the goal text. Kept only to compare with rule (a)."""
    low = problem_pddl.lower()
    i = low.find("(:goal")
    gtxt = " ".join(low[i:].split()) if i >= 0 else ""
    return (plan_shape(tool, answer) == "tool plan, then extra lines"
            and all(norm_action(x) in gtxt for x in answer[len(tool):]))


def md_cell(text: str) -> str:
    """Text safe inside a markdown table cell (trial ids hold `|`)."""
    return text.replace("|", "\\|")


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}"


# --- data (touches results, the sibling repo or installed packages; read-only)
def load_frozen(results: Path, domains_dir: Path):
    """The frozen loader, after the package-hash and domains-manifest gates."""
    from tools.delivered_rerun import constants as C
    from tools.delivered_rerun import run as RUN
    from tools.delivered_rerun_secondary import FROZEN_SHA
    if RUN.package_sha256() != FROZEN_SHA:
        raise Halt("the frozen package tools/delivered_rerun changed (hash is not 822aace...)")
    RUN.check_domains(domains_dir)
    C.assert_registered(C.REGISTERED)
    return RUN.load_all(C.REGISTERED, results / "delivered-rerun", results / "sweep5v2-live")


def load_readout(path: Path) -> dict:
    from tools.delivered_rerun_secondary import FROZEN_SHA
    ro = json.loads(path.read_text())
    if ro.get("package_sha256") != FROZEN_SHA or ro.get("mode") != "live":
        raise Halt(f"{path} is not the frozen live readout")
    return ro


def environment(marketplace: Path) -> dict:
    """Versions the validator path depends on, for the outputs."""
    server = marketplace / "plugins" / "pddl-validator" / "server" / "validator_server.py"

    def git(*a):
        return subprocess.run(["git", "-C", str(marketplace), *a], capture_output=True,
                              text=True, check=True).stdout.strip()
    return {"pyval": importlib.metadata.version("pddl-pyvalidator"),
            "unified_planning": importlib.metadata.version("unified-planning"),
            "mcp": importlib.metadata.version("mcp"),
            "marketplace_head": git("rev-parse", "HEAD"),
            "validator_server_modified": bool(git("status", "--porcelain", "--", str(server))),
            "validator_server_sha256": hashlib.sha256(server.read_bytes()).hexdigest()}


class InProcessValidator:
    """The pddl-validator plugin server imported in process, called the way the
    harness calls it (`pddl_eval.chat.MCPPlanner.call_tool`: `verbose` pinned to
    False, the text of the first content block). Plans are graded by the frozen
    `pddl_eval.scoring._validate_model_plan`, unchanged."""

    def __init__(self, marketplace: Path):
        os.environ.setdefault("PDDL_TEMP_DIR", tempfile.mkdtemp(prefix="iss028_"))
        sys.path.insert(0, str(marketplace / "plugins" / "pddl-validator" / "server"))
        import validator_server  # noqa: E402
        self.vs = validator_server

    async def call_tool(self, name: str, arguments: dict) -> str:
        from pddl_eval.chat import MCPPlanner
        if name in MCPPlanner._PINNED_VERBOSE_FALSE:
            arguments = {**(arguments or {}), "verbose": False}
        res = await self.vs.mcp.call_tool(name, arguments)
        if isinstance(res, tuple):
            res = res[0]
        if hasattr(res, "content"):
            res = res.content
        return res[0].text if res else ""


def plan_verdicts(need: set, table_path: Path | None, marketplace: Path | None,
                  domains: dict) -> tuple[dict, dict]:
    """{(domain, problem, plan): bool} for every plan in `need`, and where they came
    from. A cached table (`delivered-rerun-secondary/plan_verdicts.json`) is read
    first; the rest is validated in process (pyval must be 0.1.5)."""
    import asyncio
    from pddl_eval.scoring import _validate_model_plan
    out: dict = {}
    src = {"table": str(table_path) if table_path else None, "from_table": 0, "live": 0,
           "env": None}
    if table_path is not None:
        for e in json.loads(table_path.read_text()):
            k = (e["domain"], e["problem"], tuple(e["plan"]))
            if k in need:
                out[k] = e["valid"]
        src["from_table"] = len(out)
    rest = sorted(need - set(out))
    if rest:
        if marketplace is None:
            raise Halt(f"{len(rest)} plans have no cached verdict and no --marketplace "
                       "was given for the in-process validator")
        env = environment(marketplace)
        src["env"] = env
        if env["pyval"] != PYVAL_EXPECTED:
            raise Halt(f"pddl-pyvalidator is {env['pyval']}; the frozen grades used "
                       f"{PYVAL_EXPECTED} (0.1.6 folds case, ISS-027)")
        if env["validator_server_modified"]:
            raise Halt("validator_server.py has uncommitted changes in the sibling repo")
        val = InProcessValidator(marketplace)

        async def run():
            for d, p, plan in rest:
                v = await _validate_model_plan(val, domains[d]["domain"],
                                               domains[d]["problems"][p], list(plan))
                if not isinstance(v, bool):
                    raise Halt(f"validator transport error on {d}/{p}")
                out[(d, p, plan)] = v
        asyncio.run(run())
        src["live"] = len(rest)
    return out, src


def counter_dict(c: Counter) -> dict:
    return {k: c[k] for k in sorted(c)}
