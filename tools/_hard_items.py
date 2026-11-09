"""Pure-text PDDL helpers for the D1b new item kinds (action plan D1b).

Used by `tools/build_hard_fixtures.py`. No MCP, no planner, no I/O: every
function takes text and returns text plus a record of what changed, so the
mutations are unit-testable (`tests/test_hard_items.py`). Whether a
mutation is really invalid is decided by the oracle (pyval through the
pddl-validator plugin) and by VAL in the build script, never here.

What is here

* A small S-expression reader that keeps the character offset of every
  token and list, so a mutation is one local edit of the original text and
  everything else (layout, comments) stays byte-identical.
* `read_domain` / `read_problem`: the type hierarchy, predicate and function
  signatures, constants, action parameters, and every predicate or function
  occurrence (with the variables in scope and their types).
* Domain mutators (one real error each, inside the define form):
  undeclared predicate, wrong arity, type mismatch, undeclared type,
  undeclared function.
* Problem mutators: undefined object, wrong arity, type mismatch,
  undeclared predicate, undeclared type, undeclared function.
* Plan mutators: delete a step, swap two adjacent steps, replace a step
  (by a sibling grounding of the same action, or by another action on the
  same objects when the types fit).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# S-expression reader with offsets
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r";[^\n]*|[()]|[^\s()]+")


@dataclass
class Tok:
    text: str
    start: int
    end: int

    @property
    def low(self) -> str:
        return self.text.lower()


@dataclass
class SList:
    items: list
    start: int          # offset of "("
    end: int            # offset just after ")"

    def head(self) -> str | None:
        if self.items and isinstance(self.items[0], Tok):
            return self.items[0].low
        return None


def parse_sexp(text: str) -> list:
    """Top-level forms of `text` (comments skipped). Raises ValueError on
    unbalanced parentheses."""
    stack: list[list] = [[]]
    starts: list[int] = []
    for m in _TOKEN_RE.finditer(text):
        t = m.group(0)
        if t.startswith(";"):
            continue
        if t == "(":
            stack.append([])
            starts.append(m.start())
        elif t == ")":
            if len(stack) == 1:
                raise ValueError(f"unbalanced ')' at offset {m.start()}")
            items = stack.pop()
            stack[-1].append(SList(items, starts.pop(), m.end()))
        else:
            stack[-1].append(Tok(t, m.start(), m.end()))
    if len(stack) != 1:
        raise ValueError("unbalanced '(': missing ')'")
    return stack[0]


def _define(text: str) -> SList:
    for form in parse_sexp(text):
        if isinstance(form, SList) and form.head() == "define":
            return form
    raise ValueError("no (define ...) form")


def _section(define: SList, key: str) -> SList | None:
    for it in define.items:
        if isinstance(it, SList) and it.head() == key:
            return it
    return None


def typed_list(items: list) -> list[tuple[Tok, str | None, Tok | None]]:
    """`a b - t c` -> [(a, t, tok_t), (b, t, tok_t), (c, 'object', None)].
    An `(either ...)` type gives type None (unknown for mismatch checks)."""
    out: list[tuple[Tok, str | None, Tok | None]] = []
    pending: list[Tok] = []
    i = 0
    while i < len(items):
        it = items[i]
        if isinstance(it, Tok) and it.text == "-" and i + 1 < len(items):
            t = items[i + 1]
            tname, ttok = (None, None) if isinstance(t, SList) else (t.low, t)
            out += [(p, tname, ttok) for p in pending]
            pending = []
            i += 2
            continue
        if isinstance(it, Tok):
            pending.append(it)
        i += 1
    out += [(p, "object", None) for p in pending]
    return out


# ---------------------------------------------------------------------------
# Domain / problem models
# ---------------------------------------------------------------------------

LOGIC = {"and", "or", "not", "imply", "when"}
QUANT = {"forall", "exists"}
NUM_EFFECT = {"increase", "decrease", "assign", "scale-up", "scale-down"}
COMPARE = {"=", "<", ">", "<=", ">="}
ARITH = {"+", "-", "*", "/"}
KEYWORDS = LOGIC | QUANT | NUM_EFFECT | COMPARE | ARITH | {
    "define", "domain", "problem", "either", "object", "number", "at", "over",
    "total-cost", "minimize", "maximize", "total-time"}


@dataclass
class Occ:
    """One predicate or function occurrence: `(head arg ...)`."""
    kind: str                     # "pred" | "func"
    node: SList
    section: str                  # precondition / effect / init / goal
    action: str | None            # action name (domain occurrences)
    scope: dict[str, str | None]  # variable -> type (domain occurrences)

    @property
    def head(self) -> Tok:
        return self.node.items[0]

    @property
    def args(self) -> list:
        return self.node.items[1:]


@dataclass
class Action:
    name: str
    node: SList
    params: list[tuple[Tok, str | None, Tok | None]]


@dataclass
class DomainModel:
    text: str
    types: dict[str, str | None]            # type -> parent ("object" is the root)
    type_tokens: list[Tok]
    predicates: dict[str, list[str | None]]
    functions: dict[str, list[str | None]]
    constants: dict[str, str | None]
    actions: list[Action]
    occs: list[Occ] = field(default_factory=list)

    def names(self) -> set[str]:
        """Every declared name (for picking a name that is NOT declared)."""
        return (set(self.types) | set(self.predicates) | set(self.functions)
                | set(self.constants) | {a.name for a in self.actions} | KEYWORDS)

    def ancestors(self, t: str | None) -> set[str]:
        out: set[str] = set()
        seen = 0
        while t is not None and t not in out and seen < 64:
            out.add(t)
            t = self.types.get(t, "object" if t != "object" else None)
            seen += 1
        return out

    def incomparable(self, a: str | None, b: str | None) -> bool:
        """True when neither type is a subtype of the other (a clear type
        mismatch). Unknown (`either`) types are never called incomparable."""
        if a is None or b is None or a == b:
            return False
        if a not in self.types or b not in self.types:
            return False
        return a not in self.ancestors(b) and b not in self.ancestors(a)


def _walk(node, model: DomainModel, scope: dict, section: str, action: str | None,
          out: list[Occ]) -> None:
    if not isinstance(node, SList) or not node.items:
        return
    h = node.head()
    if h is None:
        return
    if h in QUANT and len(node.items) >= 3 and isinstance(node.items[1], SList):
        inner = dict(scope)
        for v, t, _ in typed_list(node.items[1].items):
            inner[v.low] = t
        for c in node.items[2:]:
            _walk(c, model, inner, section, action, out)
    elif h in LOGIC or h in NUM_EFFECT or h in COMPARE or h in ARITH:
        for c in node.items[1:]:
            _walk(c, model, scope, section, action, out)
    elif h in model.predicates:
        out.append(Occ("pred", node, section, action, scope))
    elif h in model.functions:
        out.append(Occ("func", node, section, action, scope))
        for c in node.items[1:]:
            _walk(c, model, scope, section, action, out)


def read_domain(text: str) -> DomainModel:
    d = _define(text)
    types: dict[str, str | None] = {"object": None}
    type_tokens: list[Tok] = []
    sec = _section(d, ":types")
    if sec:
        for name, parent, _ in typed_list(sec.items[1:]):
            types[name.low] = parent
            type_tokens.append(name)
    preds: dict[str, list[str | None]] = {}
    sec = _section(d, ":predicates")
    if sec:
        for p in sec.items[1:]:
            if isinstance(p, SList) and p.head():
                preds[p.head()] = [t for _, t, _ in typed_list(p.items[1:])]
    funcs: dict[str, list[str | None]] = {}
    sec = _section(d, ":functions")
    if sec:
        for f in sec.items[1:]:
            if isinstance(f, SList) and f.head():
                funcs[f.head()] = [t for _, t, _ in typed_list(f.items[1:])]
    consts: dict[str, str | None] = {}
    sec = _section(d, ":constants")
    if sec:
        for c, t, _ in typed_list(sec.items[1:]):
            consts[c.low] = t
    actions: list[Action] = []
    model = DomainModel(text, types, type_tokens, preds, funcs, consts, actions)
    for it in d.items:
        if not (isinstance(it, SList) and it.head() == ":action"):
            continue
        name = it.items[1].low
        params: list = []
        parts: dict[str, object] = {}
        j = 2
        while j < len(it.items) - 1:
            k = it.items[j]
            if isinstance(k, Tok) and k.text.startswith(":"):
                parts[k.low] = it.items[j + 1]
                j += 2
            else:
                j += 1
        if isinstance(parts.get(":parameters"), SList):
            params = typed_list(parts[":parameters"].items)
        act = Action(name, it, params)
        actions.append(act)
        scope = {v.low: t for v, t, _ in params}
        for key, section in ((":precondition", "precondition"), (":effect", "effect")):
            if isinstance(parts.get(key), SList):
                _walk(parts[key], model, scope, section, name, model.occs)
    return model


@dataclass
class ProblemModel:
    text: str
    objects: list[tuple[Tok, str | None, Tok | None]]
    occs: list[Occ]

    def object_types(self, dom: DomainModel) -> dict[str, str | None]:
        out = dict(dom.constants)
        out.update({o.low: t for o, t, _ in self.objects})
        return out


def read_problem(text: str, dom: DomainModel) -> ProblemModel:
    d = _define(text)
    objs: list = []
    sec = _section(d, ":objects")
    if sec:
        objs = typed_list(sec.items[1:])
    occs: list[Occ] = []
    init = _section(d, ":init")
    if init:
        for it in init.items[1:]:
            _walk(it, dom, {}, "init", None, occs)
    goal = _section(d, ":goal")
    if goal:
        for it in goal.items[1:]:
            _walk(it, dom, {}, "goal", None, occs)
    return ProblemModel(text, objs, occs)


# ---------------------------------------------------------------------------
# Names that are not declared
# ---------------------------------------------------------------------------


def _norm(name: str) -> str:
    return name.lower().replace("-", "_")


def near_miss(name: str, taken: set[str], rng: random.Random) -> str | None:
    """A one-letter typo of `name` that is not a declared name. Names of five
    or more letters lose one inner letter (not next to a `-` or `_`, so no
    one-letter word part vanishes) or gain a plural `s`; shorter names only
    gain the `s`. None when nothing qualifies."""
    n = name                       # keep the file's own letter case
    taken_n = {_norm(t) for t in taken}
    cands: set[str] = set()
    if len(n) >= 5:
        for i in range(1, len(n) - 1):
            if n[i].isalpha() and n[i - 1] not in "-_" and n[i + 1] not in "-_":
                cands.add(n[:i] + n[i + 1:])
    if not n.lower().endswith("s"):
        cands.add(n + ("S" if n.isupper() else "s"))
    ok = sorted(c for c in cands if len(c) >= 3 and c.lower() != n.lower()
                and _norm(c) not in taken_n and c[0].isalpha())
    return rng.choice(ok) if ok else None


def next_object_name(name: str, declared: set[str]) -> str:
    """A plausible object name that is not declared: `b6` -> `b7` (one past
    the largest number with the same prefix), `rover` -> `rover2`."""
    low = {d.lower() for d in declared}
    m = re.match(r"^(.*?)(\d+)$", name)
    if m:
        prefix, num = m.group(1), m.group(2)
        used = [int(mm.group(2)) for o in low
                if (mm := re.match(r"^(.*?)(\d+)$", o)) and mm.group(1) == prefix.lower()]
        k = max(used + [int(num)]) + 1
        while True:
            cand = prefix + (str(k).zfill(len(num)) if num.startswith("0") else str(k))
            if cand.lower() not in low:
                return cand
            k += 1
    k = 2
    while f"{name}{k}".lower() in low:
        k += 1
    return f"{name}{k}"


# ---------------------------------------------------------------------------
# Edits
# ---------------------------------------------------------------------------


@dataclass
class Mutation:
    text: str
    kind: str
    detail: dict


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _apply(text: str, start: int, end: int, new: str) -> str:
    return text[:start] + new + text[end:]


def _record(text: str, new_text: str, node: SList, start: int, end: int, new: str,
            kind: str, **extra) -> Mutation:
    before = text[node.start:node.end]
    delta = len(new) - (end - start)
    after = new_text[node.start:node.end + delta]
    return Mutation(new_text, kind, {"line": _line_of(text, node.start),
                                     "before": " ".join(before.split()),
                                     "after": " ".join(after.split()), **extra})


def _rename_head(text: str, occ: Occ, new: str, kind: str, **extra) -> Mutation:
    h = occ.head
    nt = _apply(text, h.start, h.end, new)
    return _record(text, nt, occ.node, h.start, h.end, new, kind, section=occ.section,
                   action=occ.action, **extra)


def _drop_last_arg(text: str, occ: Occ, kind: str, **extra) -> Mutation:
    items = occ.node.items
    last, prev = items[-1], items[-2]
    nt = _apply(text, prev.end, last.end, "")
    return _record(text, nt, occ.node, prev.end, last.end, "", kind, section=occ.section,
                   action=occ.action, **extra)


def _add_arg(text: str, occ: Occ, arg: str, kind: str, **extra) -> Mutation:
    last = occ.node.items[-1]
    nt = _apply(text, last.end, last.end, " " + arg)
    return _record(text, nt, occ.node, last.end, last.end, " " + arg, kind,
                   section=occ.section, action=occ.action, **extra)


def _replace_arg(text: str, occ: Occ, tok: Tok, new: str, kind: str, **extra) -> Mutation:
    nt = _apply(text, tok.start, tok.end, new)
    return _record(text, nt, occ.node, tok.start, tok.end, new, kind, section=occ.section,
                   action=occ.action, **extra)


def _pick(rng: random.Random, xs: list):
    return rng.choice(xs) if xs else None


# ---------------------------------------------------------------------------
# Domain mutators
# ---------------------------------------------------------------------------


def dom_undeclared_predicate(dom: DomainModel, rng: random.Random) -> Mutation | None:
    occs = [o for o in dom.occs if o.kind == "pred" and len(o.head.text) >= 3]
    rng.shuffle(occs)
    for o in occs:
        new = near_miss(o.head.text, dom.names(), rng)
        if new:
            return _rename_head(dom.text, o, new, "undeclared_predicate",
                                declared=o.head.low, used=new)
    return None


def dom_undeclared_function(dom: DomainModel, rng: random.Random) -> Mutation | None:
    occs = [o for o in dom.occs if o.kind == "func" and len(o.head.text) >= 3
            and o.head.low != "total-cost"]
    rng.shuffle(occs)
    for o in occs:
        new = near_miss(o.head.text, dom.names(), rng)
        if new:
            return _rename_head(dom.text, o, new, "undeclared_function",
                                declared=o.head.low, used=new)
    return None


def _sig(dom: DomainModel, o: Occ) -> list[str | None]:
    return (dom.predicates if o.kind == "pred" else dom.functions)[o.head.low]


def _arity_order(occs: list[Occ]) -> list[Occ]:
    """Predicates first (the usual reading of "wrong arity"); functions only
    for domains whose actions use no predicate."""
    return [o for o in occs if o.kind == "pred"] + [o for o in occs if o.kind == "func"]


def dom_wrong_arity(dom: DomainModel, rng: random.Random) -> Mutation | None:
    """Drop the last argument of a 2+-ary atom, or add a second argument
    (another variable in scope) to a 0- or 1-ary atom. Predicates first,
    then function terms (numeric domains without predicates)."""
    occs = [o for o in dom.occs if all(isinstance(a, Tok) for a in o.args)
            and o.head.low != "total-cost"]
    rng.shuffle(occs)
    for o in _arity_order(occs):
        sig = _sig(dom, o)
        if len(o.args) != len(sig):
            continue
        if len(o.args) >= 2:
            return _drop_last_arg(dom.text, o, "wrong_arity", symbol=o.head.low,
                                  symbol_kind=o.kind, declared_arity=len(sig),
                                  used_arity=len(sig) - 1)
        used = {a.low for a in o.args}
        extra = sorted(v for v in o.scope if v not in used)
        if extra:
            return _add_arg(dom.text, o, rng.choice(extra), "wrong_arity",
                            symbol=o.head.low, symbol_kind=o.kind,
                            declared_arity=len(sig), used_arity=len(sig) + 1)
    return None


def dom_type_mismatch(dom: DomainModel, rng: random.Random) -> Mutation | None:
    """Replace a variable in an atom (or function term) by another variable
    in scope whose type is incomparable with the type declared at that
    place."""
    cands = []
    for o in dom.occs:
        sig = _sig(dom, o)
        if len(o.args) != len(sig):
            continue
        for j, a in enumerate(o.args):
            if not (isinstance(a, Tok) and a.low.startswith("?")):
                continue
            want = sig[j]
            for v, vt in o.scope.items():
                if v != a.low and v not in {x.low for x in o.args if isinstance(x, Tok)} \
                        and dom.incomparable(vt, want):
                    cands.append((o, a, v, want, vt))
    c = _pick(rng, cands)
    if c is None:
        return None
    o, a, v, want, vt = c
    return _replace_arg(dom.text, o, a, v, "type_mismatch", symbol=o.head.low,
                        symbol_kind=o.kind, declared_type=want, used_variable=v,
                        used_type=vt)


def dom_undeclared_type(dom: DomainModel, rng: random.Random) -> Mutation | None:
    """Change one parameter type of one action to a typo of a declared type."""
    cands = [(a, v, t, tt) for a in dom.actions for v, t, tt in a.params
             if tt is not None and t != "object" and len(tt.text) >= 3]
    rng.shuffle(cands)
    for a, v, t, tt in cands:
        new = near_miss(tt.text, dom.names(), rng)
        if new:
            nt = _apply(dom.text, tt.start, tt.end, new)
            node = next(it for it in a.node.items if isinstance(it, SList)
                        and it.start <= tt.start < it.end)   # the :parameters list
            return _record(dom.text, nt, node, tt.start, tt.end, new, "undeclared_type",
                           section="parameters", action=a.name, declared=t, used=new,
                           variable=v.low)
    return None


DOMAIN_MUTATORS = {
    "undeclared_predicate": dom_undeclared_predicate,
    "wrong_arity": dom_wrong_arity,
    "type_mismatch": dom_type_mismatch,
    "undeclared_type": dom_undeclared_type,
    "undeclared_function": dom_undeclared_function,
}


# ---------------------------------------------------------------------------
# Problem mutators
# ---------------------------------------------------------------------------


def _object_args(o: Occ, objtypes: dict) -> list[tuple[int, Tok]]:
    return [(j, a) for j, a in enumerate(o.args)
            if isinstance(a, Tok) and a.low in objtypes]


def prob_undefined_object(dom: DomainModel, prob: ProblemModel,
                          rng: random.Random) -> Mutation | None:
    objtypes = prob.object_types(dom)
    cands = [(o, j, a) for o in prob.occs for j, a in _object_args(o, objtypes)
             if a.low not in dom.constants]
    c = _pick(rng, cands)
    if c is None:
        return None
    o, j, a = c
    new = next_object_name(a.text, set(objtypes) | dom.names())
    return _replace_arg(prob.text, o, a, new, "undefined_object", replaced=a.low, used=new)


def prob_wrong_arity(dom: DomainModel, prob: ProblemModel,
                     rng: random.Random) -> Mutation | None:
    objtypes = prob.object_types(dom)
    occs = [o for o in prob.occs if all(isinstance(a, Tok) for a in o.args)
            and o.head.low != "total-cost"]
    rng.shuffle(occs)
    for o in _arity_order(occs):
        sig = _sig(dom, o)
        if len(o.args) != len(sig):
            continue
        if len(o.args) >= 2:
            return _drop_last_arg(prob.text, o, "wrong_arity", symbol=o.head.low,
                                  symbol_kind=o.kind, declared_arity=len(sig),
                                  used_arity=len(sig) - 1)
        used = {a.low for a in o.args}
        extra = sorted(x for x in objtypes if x not in used)
        if extra:
            return _add_arg(prob.text, o, rng.choice(extra), "wrong_arity",
                            symbol=o.head.low, symbol_kind=o.kind,
                            declared_arity=len(sig), used_arity=len(sig) + 1)
    return None


def prob_type_mismatch(dom: DomainModel, prob: ProblemModel,
                       rng: random.Random) -> Mutation | None:
    objtypes = prob.object_types(dom)
    cands = []
    for o in prob.occs:
        sig = _sig(dom, o)
        if len(o.args) != len(sig):
            continue
        for j, a in _object_args(o, objtypes):
            want = sig[j]
            for x, xt in sorted(objtypes.items()):
                if x != a.low and dom.incomparable(xt, want):
                    cands.append((o, a, x, want, xt))
    c = _pick(rng, cands)
    if c is None:
        return None
    o, a, x, want, xt = c
    return _replace_arg(prob.text, o, a, x, "type_mismatch", symbol=o.head.low,
                        symbol_kind=o.kind, declared_type=want, used_object=x,
                        used_type=xt)


def prob_undeclared_predicate(dom: DomainModel, prob: ProblemModel,
                              rng: random.Random) -> Mutation | None:
    occs = [o for o in prob.occs if o.kind == "pred" and len(o.head.text) >= 3]
    rng.shuffle(occs)
    taken = dom.names() | set(prob.object_types(dom))
    for o in occs:
        new = near_miss(o.head.text, taken, rng)
        if new:
            return _rename_head(prob.text, o, new, "undeclared_predicate",
                                declared=o.head.low, used=new)
    return None


def prob_undeclared_function(dom: DomainModel, prob: ProblemModel,
                             rng: random.Random) -> Mutation | None:
    occs = [o for o in prob.occs if o.kind == "func" and len(o.head.text) >= 3
            and o.head.low != "total-cost"]
    rng.shuffle(occs)
    taken = dom.names() | set(prob.object_types(dom))
    for o in occs:
        new = near_miss(o.head.text, taken, rng)
        if new:
            return _rename_head(prob.text, o, new, "undeclared_function",
                                declared=o.head.low, used=new)
    return None


def prob_undeclared_type(dom: DomainModel, prob: ProblemModel,
                         rng: random.Random) -> Mutation | None:
    cands = [(o, t, tt) for o, t, tt in prob.objects
             if tt is not None and t != "object" and len(tt.text) >= 3]
    rng.shuffle(cands)
    taken = dom.names() | set(prob.object_types(dom))
    for o, t, tt in cands:
        new = near_miss(tt.text, taken, rng)
        if new:
            nt = _apply(prob.text, tt.start, tt.end, new)
            d = _define(prob.text)
            node = _section(d, ":objects")
            mut = _record(prob.text, nt, node, tt.start, tt.end, new, "undeclared_type",
                          section="objects", declared=t, used=new, object=o.low)
            # The whole :objects block is long; keep only the edited line.
            ln = mut.detail["line"] = _line_of(prob.text, tt.start)
            mut.detail["before"] = prob.text.splitlines()[ln - 1].strip()
            mut.detail["after"] = nt.splitlines()[ln - 1].strip()
            return mut
    return None


PROBLEM_MUTATORS = {
    "undefined_object": prob_undefined_object,
    "wrong_arity": prob_wrong_arity,
    "type_mismatch": prob_type_mismatch,
    "undeclared_predicate": prob_undeclared_predicate,
    "undeclared_type": prob_undeclared_type,
    "undeclared_function": prob_undeclared_function,
}


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------


def plan_steps(plan_text: str) -> list[str]:
    """Non-empty action lines, whitespace-normalised and lowercased."""
    return [" ".join(ln.strip().lower().split()) for ln in plan_text.splitlines()
            if ln.strip() and not ln.strip().startswith(";")]


def plan_text(steps: list[str]) -> str:
    return "\n".join(steps) + "\n"


def _step_parts(step: str) -> list[str]:
    return step.strip("()").split()


def plan_delete(steps: list[str], k: int) -> tuple[list[str], dict] | None:
    """Delete step k (1-based)."""
    if not 1 <= k <= len(steps):
        return None
    return steps[:k - 1] + steps[k:], {"op": "delete", "step": k, "removed": steps[k - 1]}


def plan_swap(steps: list[str], k: int) -> tuple[list[str], dict] | None:
    """Swap steps k and k+1 (1-based)."""
    if not 1 <= k < len(steps) or steps[k - 1] == steps[k]:
        return None
    out = list(steps)
    out[k - 1], out[k] = out[k], out[k - 1]
    return out, {"op": "swap", "steps": [k, k + 1], "first": steps[k - 1], "second": steps[k]}


def plan_replacements(steps: list[str], k: int, dom: DomainModel | None = None,
                      objtypes: dict[str, str | None] | None = None
                      ) -> list[tuple[list[str], dict]]:
    """Every one-step replacement of step k (1-based), all well-typed:

    * a sibling grounding: one argument takes a value that the same action
      has at the same position elsewhere in the plan;
    * (with `dom` and `objtypes`) another action of the domain applied to
      the same objects, when each object's type fits the other action's
      parameter type.
    """
    if not 1 <= k <= len(steps):
        return []
    parts = _step_parts(steps[k - 1])
    name, args = parts[0], parts[1:]
    seen: dict[int, set[str]] = {}
    for s in steps:
        p = _step_parts(s)
        if p[0] == name and len(p) == len(parts):
            for j, v in enumerate(p[1:]):
                seen.setdefault(j, set()).add(v)
    news: list[tuple[str, str]] = []
    for j in range(len(args)):
        for v in sorted(seen.get(j, ())):
            if v != args[j]:
                new_args = list(args)
                new_args[j] = v
                news.append(("sibling_grounding", "(" + " ".join([name] + new_args) + ")"))
    if dom is not None and objtypes is not None:
        for act in dom.actions:
            if act.name == name or len(act.params) != len(args):
                continue
            if all(objtypes.get(a) is not None and t is not None
                   and t in dom.ancestors(objtypes[a])
                   for a, (_, t, _) in zip(args, act.params)):
                news.append(("other_action", "(" + " ".join([act.name] + args) + ")"))
    out = []
    for how, new in news:
        s2 = list(steps)
        s2[k - 1] = new
        out.append((s2, {"op": "replace", "how": how, "step": k,
                         "before": steps[k - 1], "after": new}))
    return out
