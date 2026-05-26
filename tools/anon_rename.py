"""Deterministic PDDL symbol rewriter for the contamination-probe pilot.

Implements the rename pipeline spec'd in `development/contamination_probe_plan.md`
(§3.1, §3.2, §6). Reads canonical PDDL fixtures under `--source-dir`, applies a
per-domain YAML rename table from `--maps-dir`, and writes a renamed corpus to
`--output-dir`. Safety invariants enforced at startup: source tree is opened
read-only, output dir cannot resolve inside the source tree, and every per-file
write is staged under a sibling `.tmp/` directory and atomically promoted only
after all domains complete. Validation gates (bijective, keyword guard, reserved
collision, source coverage, completeness) fail closed before any output is
written. Stdlib + PyYAML only.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable

import yaml


def _make_bool_safe_loader() -> type:
    """Build a SafeLoader subclass with the implicit `bool` resolver stripped.

    PyYAML's default SafeLoader resolves YAML 1.1 truthy/falsy literals
    (`on/off/yes/no/y/n/true/false`) to Python booleans. PDDL predicate /
    action names like `on`, `at`, `in` are common; if a YAML author writes
    `predicates: { on: stowed_on }` (no quotes), PyYAML loads the key as
    `True`, the downstream source-coverage gate then fails with a confusing
    "key 'true' not found" error. Stripping the bool resolver makes those
    tokens load as plain strings — which is what we want for every map.

    Numeric / null / timestamp resolvers are untouched: those token classes
    don't appear as PDDL identifier names (identifiers must start with a
    letter per the spec), so leaving them in place can't cause the same
    collision.
    """
    class _BoolSafeLoader(yaml.SafeLoader):
        pass

    # `yaml_implicit_resolvers` is a class dict keyed by first-character.
    # We rebuild it without any resolver tagged `tag:yaml.org,2002:bool`.
    new_resolvers: dict = {}
    for first_char, resolvers in _BoolSafeLoader.yaml_implicit_resolvers.items():
        kept = [(tag, regexp) for tag, regexp in resolvers
                if tag != "tag:yaml.org,2002:bool"]
        if kept:
            new_resolvers[first_char] = kept
    _BoolSafeLoader.yaml_implicit_resolvers = new_resolvers
    return _BoolSafeLoader


_YAML_LOADER = _make_bool_safe_loader()


# PDDL reserved keywords — case-insensitive. A rename target equal to any of
# these would alias a parser keyword and silently break the renamed corpus.
# List is exhaustive per the spec brief; covers STRIPS, ADL, fluents, metric.
PDDL_RESERVED_KEYWORDS: frozenset[str] = frozenset(
    s.lower() for s in (
        "define", "domain", "requirements", "types", "predicates", "functions",
        "constants", "action", "parameters", "precondition", "effect",
        "and", "or", "not", "forall", "exists", "when", "imply",
        "object", "either",
        "init", "goal",
        "assign", "increase", "decrease", "scale-up", "scale-down",
        "total-cost", "metric", "minimize", "maximize",
        "=", "<", ">", "<=", ">=", "+", "-", "*", "/",
    )
)

# Section names in the YAML rename block. `functions` is treated as a peer
# section (the spec brief lists :functions in the completeness check but the
# YAML example in §3.1 only shows types/predicates/actions/object_prefixes;
# we accept and require functions for numeric domains that declare them).
#
# `domain_name` is included in RENAME_SECTIONS so it picks up the same
# keyword-guard / bijective / reserved-name / completeness loops for free.
# In the YAML it's a scalar (`domain_name: <new-id>`); load_map normalises
# it to a single-pair dict {canonical_domain_token: target} once the
# canonical token is known (see _attach_domain_name_pair).
#
# `constants` (Phase-B extension) renames bare exact-token names — both
# entries from `(:constants ...)` domain blocks (e.g. pogo_stick's
# `crafting_table`) and compound / unprefixed object names that can't be
# captured by the `<prefix>(\d+|[a-z])$` object-prefix pattern (e.g. rovers'
# `rover0store`, drone's `x0y0z0`). Substituted before the object_prefix
# pass so a `rover` prefix-rename doesn't see `rover0store`.
RENAME_SECTIONS: tuple[str, ...] = (
    "domain_name", "constants", "types", "predicates", "functions", "actions",
)
ALL_SECTIONS: tuple[str, ...] = RENAME_SECTIONS + ("object_prefixes",)

# Identifier rules: PDDL identifiers start with a letter, may contain letters,
# digits, hyphens and underscores. Variable refs (?x) and keyword refs (:xxx)
# are not renamable.
_IDENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")
_LINE_COMMENT_RE = re.compile(r";[^\n]*")

# Object-prefix pass: the full token must be <prefix>(\d+|[a-z]). One or more
# trailing digits OR a single trailing lowercase letter. Letter-suffix support
# rescues corpora like delivery (`rooma`, `roomb`, …). Compiled per map.
# NOTE: this regex is used at SUBSTITUTION time against DECLARED prefixes in
# the YAML. `extract_object_prefixes` is intentionally narrower (digit-only)
# to avoid spurious extraction from singleton tokens like `general` (which
# would otherwise parse as `genera` + `l`). Letter-suffix coverage at the
# completeness gate is object-centric: every problem object must be covered
# by some declared prefix OR by `constants:` (see validate_map gate 7).


# ---------- YAML loading ----------------------------------------------------


def load_map(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=_YAML_LOADER)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML must be a mapping")
    if "domain" not in data or "rename" not in data:
        raise ValueError(f"{path}: missing required keys 'domain' and 'rename'")
    rename = data["rename"]
    if not isinstance(rename, dict):
        raise ValueError(f"{path}: 'rename' must be a mapping")

    # `domain_name` is the only scalar entry in `rename`. Pull it out before
    # the generic mapping-normalisation loop so we don't try to .items() it.
    # It stays as a string for now; load_map's caller attaches it to a
    # single-pair dict via _attach_domain_name_pair once the canonical token
    # is known (read from domain.pddl). Until then, callers see
    # rename["domain_name"] as a raw string sentinel.
    if "domain_name" not in rename:
        raise ValueError(
            f"{path}: missing required key 'rename.domain_name' "
            f"(see development/contamination_probe_plan.md fix 3)"
        )
    dn_target = rename["domain_name"]
    if not isinstance(dn_target, str) or not dn_target.strip():
        raise ValueError(
            f"{path}: rename.domain_name must be a non-empty string identifier, "
            f"got {dn_target!r}"
        )
    rename["domain_name"] = dn_target.strip().lower()

    for section in ALL_SECTIONS:
        if section == "domain_name":
            continue  # scalar, handled above
        section_map = rename.get(section, {}) or {}
        if not isinstance(section_map, dict):
            raise ValueError(f"{path}: rename.{section} must be a mapping")
        rename[section] = {str(k).lower(): str(v).lower() for k, v in section_map.items()}
    data["rename"] = rename
    return data


def _attach_domain_name_pair(map_data: dict, canonical_domain_token: str) -> None:
    """Promote `rename.domain_name` from scalar target -> {src: tgt} pair.

    Called by the driver right after `discover_canonical` parses the
    `(define (domain X))` token from the canonical `domain.pddl`. Once
    promoted, `rename.domain_name` looks like every other section and can be
    fed through the generic validate_map / rewrite_text loops.
    """
    target = map_data["rename"]["domain_name"]
    if isinstance(target, dict):
        return  # already promoted (e.g. self-test re-entry)
    map_data["rename"]["domain_name"] = {canonical_domain_token.lower(): target.lower()}


# ---------- Canonical symbol extraction ------------------------------------


def _strip_comments(text: str) -> str:
    return _LINE_COMMENT_RE.sub("", text)


def _find_section(text: str, header: str) -> str | None:
    """Return the paren-balanced body of `(:<header> ...)`, or None if absent."""
    needle = f"(:{header}"
    lower = text.lower()
    idx = 0
    while True:
        hit = lower.find(needle, idx)
        if hit < 0:
            return None
        # Ensure the next char after header is whitespace or a paren — guards
        # against false matches like `(:predicates-foo`.
        end_of_header = hit + len(needle)
        if end_of_header < len(text) and text[end_of_header] not in " \t\n\r(":
            idx = end_of_header
            continue
        # Walk parens from the opening `(` at `hit`.
        depth = 0
        i = hit
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[hit + 1 : i]  # body without outer parens
            i += 1
        return None


def _tokenise_typed_list(body: str) -> list[str]:
    """Return identifier tokens and dash separators from a `:types` / `:objects`
    body, preserving order. Skips `?vars`, `:keywords`, parens, comments.
    """
    raw = _strip_comments(body)
    out: list[str] = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c.isspace() or c in "()":
            i += 1
        elif c == "-" and (i + 1 >= len(raw) or raw[i + 1].isspace() or raw[i + 1] == "("):
            out.append("-")
            i += 1
        elif c in "?:":  # variable or keyword ref — consume and drop
            j = i + 1
            while j < len(raw) and (raw[j].isalnum() or raw[j] in "_-"):
                j += 1
            i = j
        else:
            m = _IDENT_RE.match(raw, i)
            if m:
                out.append(m.group(0).lower())
                i = m.end()
            else:
                i += 1
    return out


def _extract_idents_from_typed_list(body: str) -> list[str]:
    """Bare names from a typed list — drops the parent type that follows `-`."""
    toks = _tokenise_typed_list(body)
    names: list[str] = []
    skip_next = False
    for tok in toks:
        if tok == "-":
            skip_next = True
        elif skip_next:
            skip_next = False  # this token is a parent type, not a name
        else:
            names.append(tok)
    return names


def _extract_parent_types(body: str) -> list[str]:
    """Identifiers appearing immediately after a `-` in a typed list."""
    toks = _tokenise_typed_list(body)
    parents: list[str] = []
    after_dash = False
    for tok in toks:
        if tok == "-":
            after_dash = True
        elif after_dash:
            parents.append(tok)
            after_dash = False
    return parents


def _extract_predicate_or_function_names(body: str) -> list[str]:
    """For `(:predicates ...)` / `(:functions ...)`, the head of each inner
    paren group is the predicate/function name.
    """
    names: list[str] = []
    text = _strip_comments(body)
    depth = 0
    i = 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
            # Skip whitespace, then read the head identifier.
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and depth == 1:
                # We only care about depth-1 groups directly under :predicates.
                m = _IDENT_RE.match(text, j)
                if m:
                    names.append(m.group(0).lower())
            i = j
            continue
        if c == ")":
            depth -= 1
        i += 1
    # Dedup, preserve order.
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _extract_action_names(text: str) -> list[str]:
    """Find every `(:action <name>` head in the domain body."""
    out: list[str] = []
    pattern = re.compile(r"\(\s*:action\s+([A-Za-z][A-Za-z0-9_\-]*)", re.IGNORECASE)
    for m in pattern.finditer(_strip_comments(text)):
        out.append(m.group(1).lower())
    return out


_DOMAIN_DEF_RE = re.compile(
    r"\(\s*define\s*\(\s*domain\s+([A-Za-z][A-Za-z0-9_\-]*)\s*\)",
    re.IGNORECASE,
)


def extract_domain_name(domain_text: str) -> str:
    """Return the identifier X from `(define (domain X))`. Case-normalised
    to lowercase to match the rest of the canonical-symbol pipeline.
    """
    stripped = _strip_comments(domain_text)
    m = _DOMAIN_DEF_RE.search(stripped)
    if not m:
        raise ValueError("could not locate `(define (domain X))` in domain text")
    return m.group(1).lower()


def extract_canonical_symbols(domain_text: str) -> dict[str, list[str]]:
    """Return canonical {domain_name, constants, types, predicates, functions,
    actions} from a domain. Every value is a list of lowercased identifiers
    in declaration / sorted order.
    """
    types_body = _find_section(domain_text, "types")
    types: list[str] = []
    parents: list[str] = []
    if types_body is not None:
        types = _extract_idents_from_typed_list(types_body)
        parents = _extract_parent_types(types_body)
    # Parents include user-declared supertypes too (e.g. `place` in depots) —
    # those should be in `types` already; we union to be safe.
    type_set = set(types) | set(parents)
    types_sorted = sorted(type_set)

    preds_body = _find_section(domain_text, "predicates")
    predicates = _extract_predicate_or_function_names(preds_body) if preds_body else []

    fns_body = _find_section(domain_text, "functions")
    functions = _extract_predicate_or_function_names(fns_body) if fns_body else []

    actions = _extract_action_names(domain_text)
    domain_name = extract_domain_name(domain_text)
    constants = extract_canonical_constants(domain_text)
    return {
        "domain_name": [domain_name],
        "constants": constants,
        "types": types_sorted,
        "predicates": predicates,
        "functions": functions,
        "actions": actions,
    }


def extract_object_prefixes(problem_text: str) -> set[str]:
    """Return the set of canonical object prefixes used in `:objects`.

    A prefix is the leading `[A-Za-z][A-Za-z0-9_\\-]*?` of any object name that
    ends in one or more digits; e.g. `truck1` → `truck`, `lgripper1` → `lgripper`.
    Objects without a trailing-digit suffix are ignored (no prefix to extract).

    DESIGN: This intentionally extracts ONLY digit-suffix prefixes — broadening
    to single-letter suffix would over-extract spurious prefixes from singleton
    tokens (e.g. `general` → `genera`, `colour` → `colou`). Letter-suffix
    objects like delivery's `rooma..d` are handled at the substitution layer
    (`_build_object_prefix_re` accepts `(\\d+|[a-z])`) against the declared
    YAML prefixes; the completeness gate is object-centric, not prefix-centric.
    """
    body = _find_section(problem_text, "objects")
    if body is None:
        return set()
    names = _extract_idents_from_typed_list(body)
    prefixes: set[str] = set()
    suffix_re = re.compile(r"^([A-Za-z][A-Za-z0-9_\-]*?)(\d+)$")
    for n in names:
        m = suffix_re.match(n)
        if m:
            prefixes.add(m.group(1).lower())
    return prefixes


def extract_object_names(problem_text: str) -> list[str]:
    """Return ALL object names from `:objects`, in declaration order, lowered."""
    body = _find_section(problem_text, "objects")
    if body is None:
        return []
    return list(_extract_idents_from_typed_list(body))


def extract_canonical_constants(domain_text: str) -> list[str]:
    """Return bare-token names declared in the domain's `(:constants ...)`
    block, lowered, in declaration order.

    The `:constants` block has the same typed-list shape as `:objects` so we
    reuse `_extract_idents_from_typed_list`. Returns [] when the domain has
    no `:constants` block (the common case) or when the block is empty.

    Defensive note: a `(:constants foo bar)` block WITHOUT a `- supertype`
    annotation is technically legal PDDL (defaults to type `object`). Without
    a dash, `_extract_idents_from_typed_list` returns every token as a name
    — which is the correct behaviour here. The only failure mode is a
    malformed dash-only token or an unterminated paren block; both surface
    as parse errors in downstream parser gates rather than silently swallow.
    """
    body = _find_section(domain_text, "constants")
    if body is None:
        return []
    return list(_extract_idents_from_typed_list(body))


def _make_declared_prefix_match_re(prefixes: Iterable[str]) -> re.Pattern[str] | None:
    """Build the SUBSTITUTION-time matcher for declared YAML prefixes.

    Matches `<prefix>(\\d+|[a-z])$` — same regex used by
    `_build_object_prefix_re` for the rewriter. Returned re may be `None`
    when no prefixes are declared.
    """
    keys = sorted(prefixes, key=len, reverse=True)
    if not keys:
        return None
    alternation = "|".join(re.escape(k) for k in keys)
    return re.compile(rf"^({alternation})(\d+|[a-z])$", re.IGNORECASE)


def extract_unprefixed_objects_from_names(
    names: Iterable[str],
    declared_prefixes: Iterable[str],
) -> list[str]:
    """Name-level twin of `extract_unprefixed_objects`. Given a pre-extracted
    list of object names, return those not matched by any declared YAML
    `object_prefix` key under the relaxed `<prefix>(\\d+|[a-z])$` pattern.
    Used by `validate_map` where `problem_objects` already holds the parsed
    name lists per problem file.
    """
    matcher = _make_declared_prefix_match_re(declared_prefixes)
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if matcher is not None and matcher.match(n):
            continue
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def extract_unprefixed_objects(
    problem_text: str,
    declared_prefixes: Iterable[str],
) -> list[str]:
    """Return object names from `:objects` that are NOT matched by any of the
    declared YAML object_prefix keys under the relaxed `<prefix>(\\d+|[a-z])$`
    pattern. Order-preserving, lowered, deduplicated.

    Objects in the returned list MUST appear as keys in the YAML's `constants`
    section — otherwise they would leak unchanged into the renamed corpus.
    Helper used by the source-coverage gate (constants validation) and the
    object-centric completeness gate.
    """
    return extract_unprefixed_objects_from_names(
        extract_object_names(problem_text),
        declared_prefixes,
    )


# ---------- Map validation -------------------------------------------------


def _valid_target_token(token: str) -> tuple[bool, str]:
    if not token:
        return False, "empty target"
    if any(c.isspace() for c in token):
        return False, f"contains whitespace: {token!r}"
    if "(" in token or ")" in token:
        return False, f"contains parens: {token!r}"
    if token[0].isdigit():
        return False, f"starts with digit: {token!r}"
    if token.lower() in PDDL_RESERVED_KEYWORDS:
        return False, f"equals PDDL reserved keyword: {token!r}"
    return True, ""


def validate_map(
    map_data: dict,
    canonical: dict[str, list[str]],
    canonical_object_prefixes: set[str],
    problem_objects: dict[str, list[str]] | None = None,
) -> dict:
    """Run all gate checks against a single domain's rename map.

    Returns a checks-result dict (serialisable). Raises ValueError on any gate
    failure with a message identifying the violation.

    ``problem_objects`` (Phase-B extension) is ``{filename: [object_names]}``
    from every ``p0N`` / ``n0N`` PDDL. Required to validate the new
    ``constants`` section: every object not matched by any YAML-declared
    ``object_prefix`` under the relaxed pattern MUST appear as a constants
    key (else it would leak unchanged). Pre-extension callers may pass
    ``None`` (treated as an empty dict).
    """
    domain = map_data["domain"]
    rename = map_data["rename"]
    if problem_objects is None:
        problem_objects = {}
    results: dict = {"domain": domain, "gates": {}}

    # Gate 1: keyword guard + target token shape, per section.
    for section in ALL_SECTIONS:
        for src, tgt in rename[section].items():
            ok, why = _valid_target_token(tgt)
            if not ok:
                raise ValueError(f"[{domain}] rename.{section}: {src!r} -> invalid target ({why})")
    results["gates"]["keyword_guard"] = "pass"

    # Gate 2: bijective within each section.
    for section in ALL_SECTIONS:
        seen: dict[str, str] = {}
        for src, tgt in rename[section].items():
            if tgt in seen:
                raise ValueError(
                    f"[{domain}] rename.{section}: target {tgt!r} reused by "
                    f"both {seen[tgt]!r} and {src!r}"
                )
            seen[tgt] = src
    results["gates"]["bijective_per_section"] = "pass"

    # Gate 3: bijective across the merged identifier-token table
    # (types ∪ predicates ∪ functions ∪ actions ∪ constants). object_prefixes
    # deliberately excluded — they apply via a separate regex and use a
    # disjoint token shape that can't collide with bare identifiers in the
    # rewriter's char-walk. The brief is explicit that `constants` joins the
    # merged-bijection check so a constant rename target can't collide with
    # a type/predicate/function/action target, and vice-versa.
    merged: dict[str, tuple[str, str]] = {}
    for section in RENAME_SECTIONS:
        for src, tgt in rename[section].items():
            if tgt in merged:
                prev_section, prev_src = merged[tgt]
                raise ValueError(
                    f"[{domain}] cross-section collision on target {tgt!r}: "
                    f"{prev_section}.{prev_src} and {section}.{src}"
                )
            merged[tgt] = (section, src)
    results["gates"]["bijective_merged"] = "pass"

    # Cross-section key collision: a YAML key may appear in at most one
    # section unless the canonical genuinely reuses the name across
    # namespaces (rare). Surface a clear error so the YAML author can split
    # the entries explicitly. domain_name is single-entry by construction;
    # exclude it from the loop.
    key_locations: dict[str, list[str]] = {}
    for section in RENAME_SECTIONS:
        if section == "domain_name":
            continue
        for src in rename[section]:
            key_locations.setdefault(src, []).append(section)
    for src, locs in key_locations.items():
        if len(locs) > 1:
            raise ValueError(
                f"[{domain}] key {src!r} appears in multiple rename sections "
                f"{locs!r}; split into distinct keys or remove the duplicate"
            )

    # Gate 4: source-coverage — every YAML key must be a real canonical symbol.
    for section in RENAME_SECTIONS:
        if section == "constants":
            continue  # constants has dual provenance — handled below
        canon_set = set(canonical[section])
        for src in rename[section]:
            if src not in canon_set:
                raise ValueError(
                    f"[{domain}] rename.{section}: key {src!r} not found in canonical "
                    f"{section}; known canonical {section} = {sorted(canon_set)}"
                )
    # Constants source-coverage: every YAML constants key must appear EITHER
    # in the domain's `(:constants ...)` block OR as a problem-level object
    # that is NOT matched by any declared YAML object_prefix under the
    # relaxed `<prefix>(\d+|[a-z])$` pattern (object-centric: a constant key
    # rewrites tokens the prefix machinery can't reach).
    declared_op_keys = list(rename["object_prefixes"].keys())
    canon_constants = set(canonical.get("constants", []))
    legal_constants_sources: set[str] = set(canon_constants)
    for fname, names in problem_objects.items():
        for n in extract_unprefixed_objects_from_names(names, declared_op_keys):
            legal_constants_sources.add(n)
    for src in rename["constants"]:
        if src not in legal_constants_sources:
            raise ValueError(
                f"[{domain}] rename.constants: key {src!r} not found in canonical "
                f"`(:constants …)` (= {sorted(canon_constants)}) nor among the "
                f"unprefixed object names of any p0N/n0N.pddl. Either add the "
                f"object to the corpus or remove the constants entry."
            )
    # object_prefixes source-coverage: a YAML key is valid if there exists
    # at least one canonical object name matching `^<key>(\d+|[a-z])$` across
    # all p0N/n0N problems. Accepts both digit-suffix families (depots `truck`)
    # and letter-suffix-only families (delivery `rooma..d`).
    for src in rename["object_prefixes"]:
        match_re = re.compile(rf"^{re.escape(src)}(\d+|[a-z])$", re.IGNORECASE)
        matched = any(
            match_re.match(name)
            for names in problem_objects.values()
            for name in names
        )
        if not matched:
            raise ValueError(
                f"[{domain}] rename.object_prefixes: prefix {src!r} matches no "
                f"object in any p0N/n0N.pddl under `<prefix>(\\d+|[a-z])$`. "
                f"Known digit-suffix prefixes = {sorted(canonical_object_prefixes)}; "
                f"letter-suffix families are accepted but must match at least one object."
            )
    results["gates"]["source_coverage"] = "pass"

    # Gate 5: completeness — every canonical non-keyword symbol must be a key.
    # For domain_name/types/predicates/functions/actions: every canonical
    # symbol must be renamed (object/either supertypes excepted).
    for section in RENAME_SECTIONS:
        if section == "constants":
            continue  # constants completeness handled below (dual source)
        keys = set(rename[section])
        for sym in canonical[section]:
            if sym in PDDL_RESERVED_KEYWORDS:
                continue  # built-in supertype like `object` — skip
            if sym not in keys:
                raise ValueError(
                    f"[{domain}] rename.{section} is missing canonical symbol "
                    f"{sym!r}; every canonical {section[:-1]} must be renamed"
                )
    # Constants completeness (two halves):
    #   (a) every canonical `(:constants ...)` symbol must be a constants key.
    #   (b) every unprefixed problem object (not matched by any declared
    #       object_prefix under the relaxed regex) must be a constants key.
    #       Without (b), the rewriter would leak the canonical token to the
    #       renamed corpus unchanged — observable contamination signal.
    constants_keys = set(rename["constants"])
    for sym in canon_constants:
        if sym in PDDL_RESERVED_KEYWORDS:
            continue
        if sym not in constants_keys:
            raise ValueError(
                f"[{domain}] rename.constants is missing canonical `(:constants …)` "
                f"symbol {sym!r}; every domain-level constant must be renamed"
            )
    for fname, names in problem_objects.items():
        leaked: list[str] = []
        for n in extract_unprefixed_objects_from_names(names, declared_op_keys):
            if n not in constants_keys:
                leaked.append(n)
        if leaked:
            raise ValueError(
                f"[{domain}] {fname}: object name(s) {sorted(set(leaked))!r} are "
                f"not covered by any rename.object_prefixes key (relaxed pattern: "
                f"`<prefix>(\\d+|[a-z])$`) NOR by rename.constants. They would "
                f"leak unchanged to the renamed corpus. Add them under "
                f"rename.constants: (or expand object_prefixes if they share a "
                f"family with a declared prefix)."
            )
    # Object-prefix completeness intentionally removed: the object-centric
    # gate above already ensures every canonical object is covered by EITHER
    # an object_prefix match OR a constants entry. A redundant prefix-centric
    # check would falsely reject domains (e.g. drone) where ALL objects in a
    # prefix family are exact-enumerated under constants instead.
    results["gates"]["completeness"] = "pass"

    # Gate 6: reserved-name collision — a rename target must not equal an
    # unrenamed canonical symbol in the same domain (would create transient
    # parser ambiguity during the rewrite or in downstream re-parsing).
    # Includes constants (a constants target colliding with an unrenamed
    # type or predicate would still create the same ambiguity).
    unrenamed: set[str] = set()
    for section in RENAME_SECTIONS:
        keys = set(rename[section])
        for sym in canonical.get(section, []):
            if sym not in keys and sym not in PDDL_RESERVED_KEYWORDS:
                unrenamed.add(sym)
    for section in RENAME_SECTIONS:
        for src, tgt in rename[section].items():
            if tgt in unrenamed:
                raise ValueError(
                    f"[{domain}] rename.{section}: target {tgt!r} (from {src!r}) "
                    f"collides with unrenamed canonical symbol of same domain"
                )
    results["gates"]["reserved_name_collision"] = "pass"

    return results


# ---------- Rewriter --------------------------------------------------------


def _build_object_prefix_re(prefixes: Iterable[str]) -> re.Pattern[str] | None:
    """Compile the substitution regex `^(<prefix>)(\\d+|[a-z])$`.

    `(\\d+|[a-z])` accepts EITHER one-or-more trailing digits (the original
    behaviour: `truck0`, `lgripper1`) OR a SINGLE trailing lowercase letter
    (rescues `rooma`, `roomb`, … in the delivery corpus). The substitution
    handler reattaches the captured suffix verbatim so `rooma` -> `hamleta`,
    `room0` -> `hamlet0` regardless of which alternative fired.

    Compound suffixes like `rover0store` and composite tokens like `x0y0z0`
    deliberately do NOT match; they are routed through the new `constants:`
    section so the prefix-pass never sees them.
    """
    keys = sorted(prefixes, key=len, reverse=True)  # longest-first to avoid greedy issues
    if not keys:
        return None
    alternation = "|".join(re.escape(k) for k in keys)
    return re.compile(rf"^({alternation})(\d+|[a-z])$", re.IGNORECASE)


_DOMAIN_NAME_HEADER_RE_TEMPLATE = (
    r"(\(\s*define\s*\(\s*domain\s+){token}(\s*\))"
)
_DOMAIN_NAME_REF_RE_TEMPLATE = (
    # `(?![A-Za-z0-9_\-])` is a tighter end-of-token guard than `\b`. Python
    # `\b` treats `-` as a non-word boundary, so `(:domain depots-extra)`
    # would (incorrectly) rewrite the prefix; the lookahead refuses any
    # trailing identifier-continuation character.
    r"(\(\s*:domain\s+){token}(?![A-Za-z0-9_\-])"
)

# `(define (problem X))` header — wholesale renamed via
# `_apply_problem_name_pass`. Three capture groups so the original
# whitespace between `define` / `problem` / closing-paren is preserved.
# `re.IGNORECASE` here is for the IDENTIFIER (group 2): canonical problem
# names like `ZTRAVEL-2-1` or `BW-rand-3` carry uppercase letters. The
# `define`/`problem` keywords themselves are lowercase by PDDL convention.
_PROBLEM_NAME_HEADER_RE = re.compile(
    r"(\(\s*define\s*\(\s*problem\s+)([A-Za-z][A-Za-z0-9_\-]*)(\s*\))",
    re.IGNORECASE,
)


def _apply_problem_name_pass(
    text: str,
    file_stem: str,
    target_domain_token: str,
) -> str:
    """Wholesale rewrite of `(define (problem X))` headers.

    Replaces the problem identifier with the deterministic synthetic name
    `<target_domain_token>-<file_stem>` (e.g. `apiary-p01`). Run as a
    POST-pass — after the identifier char-walk and the object-prefix
    regex — so the synthetic name is opaque to both. Returns the rewritten
    text unchanged when no `(define (problem ...))` header is present
    (domain.pddl, domain_neg.pddl, .plan files).

    The canonical problem name (for audit logging and round-trip restore)
    is the caller's responsibility — extract it from the pre-rewrite source
    via `_extract_canonical_problem_name` so the audit log reflects the
    true canonical, never a post-walk form.

    Closes the lexical-leak weak spot where canonical (or canonical-substring)
    tokens survived in the problem identifier — see
    `development/contamination_probe_plan.md` §3.2.
    """
    new_name = f"{target_domain_token}-{file_stem}".lower()

    def _sub(m: re.Match[str]) -> str:
        return f"{m.group(1)}{new_name}{m.group(3)}"

    rewritten, _ = _PROBLEM_NAME_HEADER_RE.subn(_sub, text, count=1)
    return rewritten


def _apply_problem_name_pass_inverse(
    text: str,
    canonical_problem_name: str,
) -> str:
    """Restore the canonical `(define (problem X))` from the synthetic name.

    Used by `round_trip_check` to re-establish strict byte-equality after
    inverse rewrite. The forward pass is one-way (file_stem -> synthetic
    name) so inverse needs the canonical name from the source file rather
    than deriving it from the synthetic form.
    """
    def _sub(m: re.Match[str]) -> str:
        return f"{m.group(1)}{canonical_problem_name}{m.group(3)}"

    rewritten, _ = _PROBLEM_NAME_HEADER_RE.subn(_sub, text, count=1)
    return rewritten


_PROBLEM_FILE_RE = re.compile(r"^[pn]\d{2}$")

# Audit invariant: every renamed problem file's header must match this
# pattern after `_apply_problem_name_pass`. Pin via `_audit_problem_headers`
# at the end of `rewrite_corpus` so a regression aborts the rewrite
# atomically (before the tmp dir is promoted to `domains-anon/`).
_PROBLEM_HEADER_SYNTH_RE = re.compile(
    r"\(\s*define\s*\(\s*problem\s+[a-z][a-z0-9_\-]*-[pn]\d{2}\s*\)",
)


def _extract_canonical_problem_name(text: str) -> str | None:
    """Pull the `X` from `(define (problem X))`, lowercased, or None."""
    m = _PROBLEM_NAME_HEADER_RE.search(text)
    if m is None:
        return None
    return m.group(2).lower()


def _audit_problem_headers(corpus_root: Path) -> list[str]:
    """Walk every `[pn]\\d{2}.pddl` under `corpus_root` and assert each
    `(define (problem X))` header matches the synthetic
    `<renamed_domain_token>-[pn]\\d{2}` pattern. Returns a list of
    violation messages (empty when the corpus is clean).

    Called from `rewrite_corpus` after all files are staged in the tmp dir
    but before atomic-promote. A non-empty list aborts the rewrite — the
    previous `domains-anon/` is preserved untouched. Defence-in-depth
    against future regressions in `_apply_problem_name_pass`.
    """
    violations: list[str] = []
    for family in ("classical", "numeric"):
        family_root = corpus_root / family
        if not family_root.is_dir():
            continue
        for dir_path in sorted(family_root.iterdir()):
            if not dir_path.is_dir():
                continue
            for entry in sorted(os.listdir(dir_path)):
                stem = entry[:-5] if entry.endswith(".pddl") else entry
                if not _PROBLEM_FILE_RE.fullmatch(stem):
                    continue
                fpath = dir_path / entry
                with fpath.open("r", encoding="utf-8") as fh:
                    text = fh.read()
                if _PROBLEM_HEADER_SYNTH_RE.search(text) is None:
                    m = _PROBLEM_NAME_HEADER_RE.search(text)
                    actual = m.group(0) if m else "<no problem header found>"
                    violations.append(f"{fpath}: header does not match synthetic pattern; got {actual!r}")
    return violations


def _apply_domain_name_pass(
    text: str,
    rename_domain_name: dict[str, str],
) -> tuple[str, int]:
    """Context-bound rewrite of the canonical domain identifier.

    Substitutes ONLY in two contexts:
      1. The second symbol of `(define (domain X))` — domain.pddl + domain_neg.pddl.
      2. The single argument of `(:domain X)` — every p0N.pddl / n0N.pddl.

    Free-string replace is deliberately avoided so a domain whose canonical
    name happens to coincide with an object prefix (or any other token) is
    not over-substituted. Returns (rewritten_text, count_of_substitutions).
    """
    if not rename_domain_name:
        return text, 0
    # The dict is single-pair {canonical_token: target_token} per
    # _attach_domain_name_pair; pull both out.
    (src_tok, tgt_tok), = rename_domain_name.items()
    token_pattern = re.escape(src_tok)

    header_re = re.compile(
        _DOMAIN_NAME_HEADER_RE_TEMPLATE.format(token=token_pattern),
        re.IGNORECASE,
    )
    ref_re = re.compile(
        _DOMAIN_NAME_REF_RE_TEMPLATE.format(token=token_pattern),
        re.IGNORECASE,
    )
    count = 0

    def _sub_header(m: re.Match[str]) -> str:
        # Two capture groups: prefix `(define (domain `, suffix `)`.
        nonlocal count
        count += 1
        return f"{m.group(1)}{tgt_tok}{m.group(2)}"

    def _sub_ref(m: re.Match[str]) -> str:
        # One capture group: prefix `(:domain `; trailing boundary is a
        # zero-width lookahead, so the token is replaced in place.
        nonlocal count
        count += 1
        return f"{m.group(1)}{tgt_tok}"

    text = header_re.sub(_sub_header, text)
    text = ref_re.sub(_sub_ref, text)
    return text, count


def rewrite_text(
    text: str,
    rename: dict[str, dict[str, str]],
) -> tuple[str, dict[str, int]]:
    """Apply the multi-pass rename to `text`. Returns (rewritten, counts-per-section).

    Passes:
      A. Identifier-token pass over types / predicates / functions / actions
         (case-insensitive exact match, comment- and ?var- aware).
      B. Object-prefix pass over `<prefix><digits>` object names.
      C. Context-bound domain-name pass (only `(define (domain X))` and
         `(:domain X)`). Run as a separate post-pass — see fix 3 of the
         spec extension — to avoid corrupting fixtures if a domain's
         canonical name coincides with another identifier elsewhere.

    Idempotency note: pass C searches for the ORIGINAL canonical token, so
    a second run over already-rewritten text matches zero times.
    """
    identifier_table: dict[str, tuple[str, str]] = {}
    for section in RENAME_SECTIONS:
        if section == "domain_name":
            continue  # handled by the context-bound PRE-pass below
        for src, tgt in rename[section].items():
            identifier_table[src.lower()] = (section, tgt)

    op_re = _build_object_prefix_re(rename["object_prefixes"].keys())
    op_table = {k.lower(): v for k, v in rename["object_prefixes"].items()}

    counts: dict[str, int] = {s: 0 for s in ALL_SECTIONS}

    # PRE-pass: domain-name context-bound rewrite must run BEFORE the
    # char-walk. The relaxed object-prefix regex `<prefix>(\d+|[a-z])$`
    # would otherwise match the canonical domain identifier as a prefix +
    # letter pair (e.g. `depots` → prefix `depot` + suffix `s` → `docks`).
    # Running domain-name first replaces `depots` with the target (e.g.
    # `seaport`), leaving nothing for the prefix pass to wrongly match.
    text, dn_count = _apply_domain_name_pass(text, rename["domain_name"])
    counts["domain_name"] = dn_count

    # We walk the text character-by-character so comments and variable/keyword
    # refs are preserved verbatim. Identifier tokens are matched with _IDENT_RE.
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == ";":  # comment — copy through to end-of-line.
            j = text.find("\n", i)
            if j < 0:
                out.append(text[i:])
                i = n
            else:
                out.append(text[i:j])
                i = j
            continue
        if c == "?" or c == ":":  # variable ref or keyword ref — copy through.
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "_-"):
                j += 1
            out.append(text[i:j])
            i = j
            continue
        m = _IDENT_RE.match(text, i)
        if m:
            tok = m.group(0)
            key = tok.lower()
            # Pass 1: identifier exact match.
            if key in identifier_table:
                section, tgt = identifier_table[key]
                out.append(tgt)
                counts[section] += 1
                i = m.end()
                continue
            # Pass 2: object-prefix + digits.
            if op_re is not None:
                pm = op_re.match(key)
                if pm:
                    prefix = pm.group(1).lower()
                    digits = pm.group(2)
                    out.append(f"{op_table[prefix]}{digits}")
                    counts["object_prefixes"] += 1
                    i = m.end()
                    continue
            # No rename — copy verbatim.
            out.append(tok)
            i = m.end()
            continue
        out.append(c)
        i += 1
    rewritten = "".join(out)
    return rewritten, counts


def rewrite_text_inverse(
    text: str,
    rename: dict[str, dict[str, str]],
) -> str:
    """Apply the inverse rename — for the round-trip check."""
    inverse = {
        section: {v: k for k, v in rename[section].items()}
        for section in ALL_SECTIONS
    }
    rewritten, _ = rewrite_text(text, inverse)
    return rewritten


def lowercase_identifiers(text: str) -> str:
    """Lowercase every identifier token (skipping `?vars`, `:keywords`,
    comments). PDDL is case-insensitive on identifiers; this normalises the
    canonical corpus for byte-comparison against round-trip output (which
    always emits lowercase per spec).
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == ";":
            j = text.find("\n", i)
            if j < 0:
                out.append(text[i:]); i = n
            else:
                out.append(text[i:j]); i = j
            continue
        if c in "?:":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "_-"):
                j += 1
            out.append(text[i:j])
            i = j
            continue
        m = _IDENT_RE.match(text, i)
        if m:
            out.append(m.group(0).lower())
            i = m.end()
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------- File-tree walk -------------------------------------------------


def find_domain_root(source_dir: Path, dir_stem: str) -> Path:
    """Locate `<source-dir>/classical/<dir_stem>/` or `<source-dir>/numeric/<dir_stem>/`.

    `dir_stem` is the YAML filename stem (e.g. `depots`, `gripper`,
    `counters`), NOT the canonical PDDL domain identifier. The two differ
    when the canonical identifier carries a suffix like `gripper-strips`
    or `fo-counters-rnd`; the on-disk directory uses the short stem.
    """
    for family in ("classical", "numeric"):
        candidate = source_dir / family / dir_stem
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"domain directory {dir_stem!r} not found under "
        f"{source_dir / 'classical'} or {source_dir / 'numeric'}"
    )


def domain_family(source_dir: Path, dir_stem: str) -> str:
    for family in ("classical", "numeric"):
        if (source_dir / family / dir_stem).is_dir():
            return family
    raise FileNotFoundError(dir_stem)


def discover_canonical(
    source_dir: Path,
    dir_stem: str,
    yaml_domain: str | None = None,
) -> tuple[dict[str, list[str]], set[str], dict[str, list[str]]]:
    """Parse the canonical `domain.pddl` under `<source-dir>/<family>/<dir_stem>/`
    and (optionally) cross-check the YAML `domain:` field against the parsed
    `(define (domain X))` identifier.

    Cross-check rationale: source-coverage for `domain_name` is degenerate
    (one source token, one target token), so the gate IS this equality
    check — there's no list-comparison to do. If `yaml_domain` is provided
    and doesn't match the parsed token, fail fast with a clear message.

    Returns a triple ``(canonical, object_prefixes, problem_objects)``:
      * ``canonical`` -- dict from `extract_canonical_symbols`, including the
        new `constants` key.
      * ``object_prefixes`` -- set of digit-suffix prefixes extracted from
        every ``p0N.pddl`` / ``n0N.pddl``. Letter-suffix objects are NOT
        contributed here (see `extract_object_prefixes` design note); they
        are surfaced through `problem_objects` instead.
      * ``problem_objects`` -- ``{filename: [object_names_in_decl_order]}``
        across every ``p0N.pddl`` / ``n0N.pddl``. Used by the constants
        validation gates to compute "unprefixed objects" relative to the
        YAML's declared prefixes (object-centric completeness).
    """
    root = find_domain_root(source_dir, dir_stem)
    with (root / "domain.pddl").open("r", encoding="utf-8") as fh:
        domain_text = fh.read()
    canonical = extract_canonical_symbols(domain_text)
    parsed_token = canonical["domain_name"][0]
    if yaml_domain is not None and parsed_token != yaml_domain.lower():
        raise ValueError(
            f"YAML domain: {yaml_domain!r} does not match canonical "
            f"`(define (domain {parsed_token}))` in {root / 'domain.pddl'}"
        )
    prefixes: set[str] = set()
    problem_objects: dict[str, list[str]] = {}
    for fname in sorted(os.listdir(root)):
        if re.fullmatch(r"[pn]\d{2}\.pddl", fname):
            with (root / fname).open("r", encoding="utf-8") as fh:
                ptext = fh.read()
            prefixes |= extract_object_prefixes(ptext)
            problem_objects[fname] = extract_object_names(ptext)
    return canonical, prefixes, problem_objects


def iter_domain_files(source_dir: Path, dir_stem: str) -> Iterable[Path]:
    root = find_domain_root(source_dir, dir_stem)
    for entry in sorted(os.listdir(root)):
        p = root / entry
        if p.is_file() and (entry.endswith(".pddl") or entry.endswith(".plan")):
            yield p


# ---------- Driver ---------------------------------------------------------


def _ensure_output_not_inside_source(source_dir: Path, output_dir: Path) -> None:
    src = source_dir.resolve()
    out = output_dir.resolve()
    if out == src:
        raise SystemExit(f"FATAL: --output-dir ({out}) equals --source-dir ({src})")
    try:
        out.relative_to(src)
    except ValueError:
        return  # not inside source — OK
    raise SystemExit(f"FATAL: --output-dir ({out}) is inside --source-dir ({src})")


def _discover_maps(maps_dir: Path, requested: list[str]) -> list[Path]:
    if not maps_dir.is_dir():
        raise SystemExit(f"FATAL: --maps-dir {maps_dir} does not exist")
    all_yamls = sorted(p for p in maps_dir.glob("*.yaml"))
    if not requested:
        return all_yamls
    by_stem = {p.stem: p for p in all_yamls}
    out: list[Path] = []
    for d in requested:
        if d not in by_stem:
            raise SystemExit(f"FATAL: requested domain {d!r} has no map at {maps_dir}/{d}.yaml")
        out.append(by_stem[d])
    return out


def _self_test_bool_resolver() -> None:
    """Unit-style assertion: a YAML literal with bare `on:` must load as a
    string key, not Python True. Guards the loader fix from regressing."""
    literal = "predicates:\n  on: foo\n"
    parsed = yaml.load(literal, Loader=_YAML_LOADER)
    assert isinstance(parsed, dict), "expected mapping"
    preds = parsed["predicates"]
    assert "on" in preds and preds["on"] == "foo", (
        f"bool-resolver strip regression: expected string key 'on', "
        f"got keys {list(preds.keys())!r}"
    )
    assert True not in preds, (
        "bool-resolver strip regression: True still appears as a key "
        "(YAML 1.1 implicit bool not fully stripped)"
    )


def _self_test_domain_name_substitution(
    source_dir: Path,
    maps_dir: Path,
    map_paths: list[Path],
) -> None:
    """Bonus fix-5 check: for depots/domain.pddl, the rewritten output must
    contain the renamed `domain_name` token EXACTLY once after
    `(define (domain `. Skips silently if depots isn't in the requested set.
    """
    depots_path: Path | None = None
    for mp in map_paths:
        if mp.stem == "depots":
            depots_path = mp
            break
    if depots_path is None:
        print("  (skipped fix-5 depots integration spot-check — depots not in --domain set)")
        return
    data = load_map(depots_path)
    canonical, prefixes, problem_objects = discover_canonical(source_dir, depots_path.stem, data["domain"])
    _attach_domain_name_pair(data, canonical["domain_name"][0])
    validate_map(data, canonical, prefixes, problem_objects)
    domain_pddl = source_dir / "classical" / "depots" / "domain.pddl"
    with domain_pddl.open("r", encoding="utf-8") as fh:
        rewritten, counts = rewrite_text(fh.read(), data["rename"])
    assert counts["domain_name"] == 1, (
        f"fix-5: depots/domain.pddl expected 1 domain_name substitution, "
        f"got {counts['domain_name']}"
    )
    target = next(iter(data["rename"]["domain_name"].values()))
    # The renamed token must appear once after `(define (domain ` and the
    # canonical `depots` token (in that header position) must be gone.
    header_re = re.compile(
        r"\(\s*define\s*\(\s*domain\s+([A-Za-z][A-Za-z0-9_\-]*)\s*\)",
        re.IGNORECASE,
    )
    headers = header_re.findall(rewritten)
    assert len(headers) == 1, (
        f"fix-5: expected exactly one `(define (domain X))` in rewritten "
        f"depots/domain.pddl, found {len(headers)}: {headers!r}"
    )
    assert headers[0].lower() == target, (
        f"fix-5: rewritten header has {headers[0]!r}, expected {target!r}"
    )
    print(f"  fix-5 depots integration spot-check: 1 hit, header now ({target})")


def self_test(maps_dir: Path, source_dir: Path, requested: list[str]) -> int:
    # Standalone unit-style assertions that don't depend on real YAMLs.
    _self_test_bool_resolver()
    print("OK  bool-resolver strip (synthetic `on: foo` -> string key)")

    map_paths = _discover_maps(maps_dir, requested)
    failures: list[str] = []
    for mp in map_paths:
        try:
            data = load_map(mp)
            yaml_domain = data["domain"]
            dir_stem = mp.stem
            canonical, prefixes, problem_objects = discover_canonical(source_dir, dir_stem, yaml_domain)
            _attach_domain_name_pair(data, canonical["domain_name"][0])
            # Extra fix-4 check (2): rename.domain_name target must be a
            # non-empty identifier — load_map enforces non-empty; here we
            # confirm the promoted single-pair dict has exactly one entry.
            dn_pair = data["rename"]["domain_name"]
            assert isinstance(dn_pair, dict) and len(dn_pair) == 1 and \
                all(v for v in dn_pair.values()), (
                    f"rename.domain_name promoted to malformed dict: {dn_pair!r}"
                )
            validate_map(data, canonical, prefixes, problem_objects)
            print(f"OK  {mp.name}  (yaml domain={yaml_domain}, dir={dir_stem}, "
                  f"canonical_token={canonical['domain_name'][0]} -> "
                  f"{dn_pair[canonical['domain_name'][0]]})")
        except Exception as exc:  # noqa: BLE001 — surface every error to the user
            failures.append(f"{mp.name}: {exc}")
            print(f"FAIL  {mp.name}  {exc}")
    # Fix-5 bonus: depots integration spot-check. Best-effort; only run if no
    # validation failures so far (otherwise the rewrite path may be unsafe).
    if not failures:
        try:
            _self_test_domain_name_substitution(source_dir, maps_dir, map_paths)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"depots/domain.pddl (fix-5 spot-check): {exc}")
            print(f"FAIL  fix-5 spot-check  {exc}")
    if failures:
        print(f"\n{len(failures)} of {len(map_paths)} maps failed validation", file=sys.stderr)
        return 1
    print(f"\nAll {len(map_paths)} maps passed validation.")
    return 0


def round_trip_check(
    source_dir: Path,
    output_dir: Path,
    maps_dir: Path,
    requested: list[str],
) -> int:
    map_paths = _discover_maps(maps_dir, requested)
    mismatches: list[str] = []
    for mp in map_paths:
        data = load_map(mp)
        yaml_domain = data["domain"]
        dir_stem = mp.stem
        # Promote rename.domain_name from scalar to {src: tgt} dict so the
        # inverse rewriter can build a coherent inverse table.
        canonical, _, _ = discover_canonical(source_dir, dir_stem, yaml_domain)
        _attach_domain_name_pair(data, canonical["domain_name"][0])
        rename = data["rename"]
        family = domain_family(source_dir, dir_stem)
        canon_root = source_dir / family / dir_stem
        anon_root = output_dir / family / dir_stem
        if not anon_root.is_dir():
            mismatches.append(f"{dir_stem}: missing output dir {anon_root}")
            continue
        for entry in sorted(os.listdir(canon_root)):
            canon_path = canon_root / entry
            anon_path = anon_root / entry
            if not canon_path.is_file():
                continue
            if not anon_path.is_file():
                mismatches.append(f"{dir_stem}/{entry}: missing in output")
                continue
            with canon_path.open("r", encoding="utf-8") as fh:
                canonical_text = fh.read()
            with anon_path.open("r", encoding="utf-8") as fh:
                anon_text = fh.read()
            restored = rewrite_text_inverse(anon_text, rename)
            # Problem-name pass is one-way (synthetic `<target>-<file_stem>`
            # carries no record of the canonical X). For problem files,
            # extract X from the canonical source and rewrite the synthetic
            # header back to it before byte-compare. Non-problem files
            # (domain.pddl, plans) skip this step — they have no problem
            # header to restore.
            if _PROBLEM_FILE_RE.fullmatch(Path(entry).stem):
                canonical_problem_name = _extract_canonical_problem_name(canonical_text)
                if canonical_problem_name is None:
                    mismatches.append(
                        f"{dir_stem}/{entry}: canonical file has no "
                        f"`(define (problem X))` header — cannot round-trip"
                    )
                    continue
                restored = _apply_problem_name_pass_inverse(restored, canonical_problem_name)
            # Renamed tokens are always emitted lowercase (spec). Tokens the
            # inverse pass doesn't substitute (e.g. problem identifiers like
            # `BW-rand-3`) keep their original casing — so case-normalise
            # BOTH sides for the byte-compare. Comments stay case-as-is on
            # both sides (lowercase_identifiers skips comment regions).
            canon_norm = lowercase_identifiers(canonical_text)
            restored_norm = lowercase_identifiers(restored)
            if restored_norm != canon_norm:
                diff = "".join(difflib.unified_diff(
                    canon_norm.splitlines(keepends=True),
                    restored_norm.splitlines(keepends=True),
                    fromfile=f"{canon_path} (case-normalised)",
                    tofile=f"inverse({anon_path}) (case-normalised)",
                ))
                mismatches.append(f"{dir_stem}/{entry}:\n{diff}")
    # Fix-5 bonus: depots/domain.pddl must contain the renamed domain_name
    # token exactly once after `(define (domain `. Cheap insurance against
    # silent fail-open on the new context-bound pass.
    try:
        _self_test_domain_name_substitution(source_dir, maps_dir, map_paths)
    except Exception as exc:  # noqa: BLE001
        mismatches.append(f"depots/domain.pddl (fix-5 spot-check): {exc}")
    if mismatches:
        for m in mismatches:
            print(m)
        print(f"\n{len(mismatches)} files failed round-trip", file=sys.stderr)
        return 1
    print(f"Round-trip OK across {len(map_paths)} domains.")
    return 0


def rewrite_corpus(
    source_dir: Path,
    output_dir: Path,
    maps_dir: Path,
    requested: list[str],
    verbose: bool,
) -> int:
    map_paths = _discover_maps(maps_dir, requested)
    tmp_dir = output_dir.with_name(output_dir.name + ".tmp")
    bak_dir = output_dir.with_name(output_dir.name + ".bak")

    # Clean stale staging.
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    log_lines: list[str] = []
    maps_out = tmp_dir / "_maps"
    maps_out.mkdir(parents=True)

    for mp in map_paths:
        data = load_map(mp)
        yaml_domain = data["domain"]
        dir_stem = mp.stem
        family = domain_family(source_dir, dir_stem)
        canonical, prefixes, problem_objects = discover_canonical(source_dir, dir_stem, yaml_domain)
        _attach_domain_name_pair(data, canonical["domain_name"][0])
        rename = data["rename"]
        checks = validate_map(data, canonical, prefixes, problem_objects)
        # Surface the three identifiers in the checks artefact so a future
        # debugger doesn't have to re-derive them.
        checks["dir_stem"] = dir_stem
        checks["yaml_domain"] = yaml_domain
        checks["canonical_domain_token"] = canonical["domain_name"][0]

        # Copy YAML verbatim into output (source of truth alongside the corpus).
        shutil.copyfile(mp, maps_out / mp.name)

        # Write per-domain checks.json. Key by dir_stem to keep filenames
        # consistent with the on-disk layout (was previously the YAML
        # `domain:` field which can carry a suffix like `gripper-strips`).
        with (maps_out / f"{dir_stem}.checks.json").open("w", encoding="utf-8") as fh:
            json.dump(checks, fh, indent=2, sort_keys=True)
            fh.write("\n")

        out_root = tmp_dir / family / dir_stem
        out_root.mkdir(parents=True, exist_ok=True)

        # Pull the renamed domain token once per domain — used to build the
        # synthetic problem identifier `<target>-<file_stem>`. Reading from
        # rename["domain_name"].values() (not yaml_domain) keeps the source
        # of truth aligned with the actual rewrite target, which may differ
        # from the YAML `domain:` field when the canonical token carries a
        # suffix (e.g. `gripper-strips`).
        target_domain_token = next(iter(rename["domain_name"].values()))

        for src_path in iter_domain_files(source_dir, dir_stem):
            with src_path.open("r", encoding="utf-8") as fh:
                text = fh.read()
            # Extract the canonical problem name from the SOURCE text before
            # `rewrite_text` runs, so the audit log records the true canonical
            # even if a future YAML accidentally puts a problem identifier
            # into the identifier_table. None for non-problem files.
            original_problem_name: str | None = None
            if _PROBLEM_FILE_RE.fullmatch(src_path.stem):
                original_problem_name = _extract_canonical_problem_name(text)
            rewritten, counts = rewrite_text(text, rename)
            if _PROBLEM_FILE_RE.fullmatch(src_path.stem):
                rewritten = _apply_problem_name_pass(
                    rewritten, src_path.stem, target_domain_token,
                )
            dst_path = out_root / src_path.name
            with dst_path.open("w", encoding="utf-8") as fh:
                fh.write(rewritten)
            digest = hashlib.sha256(rewritten.encode("utf-8")).hexdigest()
            # `domain_name` appears as its own key in `counts` (a separate
            # audit-log section, per fix 3) so reviewers can verify
            # domain.pddl had exactly 1 hit, problem files 1 hit each,
            # plan files 0 hits. `original_problem_name` is logged outside
            # `substitutions` because the problem-name pass is one-way
            # (synthetic name not derived from canonical-token rename).
            log_lines.append(json.dumps({
                "dir_stem": dir_stem,
                "domain": yaml_domain,
                "canonical_domain_token": canonical["domain_name"][0],
                "family": family,
                "file": src_path.name,
                "substitutions": counts,
                "original_problem_name": original_problem_name,
                "sha256": digest,
            }, sort_keys=True))
            if verbose:
                print(f"  {family}/{dir_stem}/{src_path.name}: {counts}"
                      f" problem_name={original_problem_name!r}")

    with (tmp_dir / "_rename.log").open("w", encoding="utf-8") as fh:
        for line in log_lines:
            fh.write(line + "\n")

    # Defence-in-depth: assert every problem header in the staged corpus
    # matches the synthetic `<target>-[pn]NN` pattern. A regression in
    # `_apply_problem_name_pass` would surface here BEFORE the existing
    # `domains-anon/` is replaced; we abort and the previous corpus stays
    # untouched. Today this is invariant by construction (the pass fires
    # on every p0N/n0N file), but the audit guards against silent breakage
    # in future refactors.
    audit_violations = _audit_problem_headers(tmp_dir)
    if audit_violations:
        for v in audit_violations:
            print(v, file=sys.stderr)
        raise SystemExit(
            f"FATAL: {len(audit_violations)} problem-header audit "
            f"violation(s) in staged corpus; refusing to promote {tmp_dir} "
            f"to {output_dir}"
        )

    # Atomic-ish promotion: bak swap then tmp -> output.
    if output_dir.exists():
        if bak_dir.exists():
            shutil.rmtree(bak_dir)
        os.replace(output_dir, bak_dir)
    os.replace(tmp_dir, output_dir)
    if bak_dir.exists():
        shutil.rmtree(bak_dir)

    print(f"Wrote {len(log_lines)} files across {len(map_paths)} domains to {output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, default=Path("domains"))
    ap.add_argument("--output-dir", type=Path, default=Path("domains-anon"))
    ap.add_argument("--maps-dir", type=Path, default=Path("domains-anon/_maps"))
    ap.add_argument("--domain", action="append", default=[],
                    help="Domain to process (repeatable); default = all maps under --maps-dir")
    ap.add_argument("--self-test", action="store_true",
                    help="Validate every map under --maps-dir and exit without writing output")
    ap.add_argument("--round-trip-check", action="store_true",
                    help="Invert rename on --output-dir and byte-compare to --source-dir")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test and args.round_trip_check:
        raise SystemExit("FATAL: --self-test and --round-trip-check are mutually exclusive")

    if not args.source_dir.is_dir():
        raise SystemExit(f"FATAL: --source-dir {args.source_dir} does not exist")

    # Defence-in-depth: every entry path must satisfy the source/output invariant.
    _ensure_output_not_inside_source(args.source_dir, args.output_dir)

    if args.self_test:
        return self_test(args.maps_dir, args.source_dir, args.domain)
    if args.round_trip_check:
        return round_trip_check(args.source_dir, args.output_dir, args.maps_dir, args.domain)
    return rewrite_corpus(
        args.source_dir, args.output_dir, args.maps_dir, args.domain, args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
