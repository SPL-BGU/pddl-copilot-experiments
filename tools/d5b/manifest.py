"""sha256 manifest of the D5b domain files and generated problems.

Standard library only. The manifest (tools/d5b/manifest.json) is the committed
record of the ground-truth corpus: the IPC 2023 commit, the generator spec, and
one sha256 per domain file and per generated problem. The PDDL itself stays
untracked (no licence on the source repo).

    python -m tools.d5b.manifest --clone external/ipc2023-learning \
        --work external/d5b-work --write      # (re)write manifest.json
    python -m tools.d5b.manifest --clone ... --work ... --check  # exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from tools.d5b import ladder

MANIFEST_PATH = Path(__file__).with_name("manifest.json")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def problem_relpath(domain: str, tier: str, name: str) -> str:
    return f"problems/{domain}/{tier}/{name}"


def build(clone: Path, work: Path, specs=None) -> dict:
    """Manifest dict for the clone's domain files and the generated problems.

    Raises FileNotFoundError if any expected file is missing, so a partial
    generation can never be written as the record."""
    specs = ladder.ladder() if specs is None else specs
    domains = sorted({s.domain for s in specs})
    dom = {d: sha256_file(clone / d / "domain.pddl") for d in domains}
    probs = {}
    for s in specs:
        rel = problem_relpath(s.domain, s.tier, s.problem_name)
        probs[rel] = {
            "sha256": sha256_file(work / rel),
            "domain": s.domain,
            "tier": s.tier,
            "instance_id": s.instance_id,
            "seed": s.seed,
            "params": s.params,
            "command": s.shell_command(s.tier),
        }
    return {"spec": ladder.spec_record(), "domain_files": dom, "problems": probs}


def diff(expected: dict, actual: dict) -> list[str]:
    """Human-readable list of differences (empty = identical)."""
    out = []
    if expected.get("spec") != actual.get("spec"):
        out.append("spec differs")
    for key in ("domain_files", "problems"):
        e, a = expected.get(key, {}), actual.get(key, {})
        for k in sorted(set(e) | set(a)):
            ev = e.get(k)
            av = a.get(k)
            if isinstance(ev, dict):
                ev = ev.get("sha256")
            if isinstance(av, dict):
                av = av.get("sha256")
            if ev != av:
                out.append(f"{key}/{k}: expected {ev} got {av}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clone", type=Path, default=Path(__file__).resolve().parents[2] / "external" / "ipc2023-learning")
    ap.add_argument("--work", type=Path, default=Path(__file__).resolve().parents[2] / "external" / "d5b-work")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    actual = build(a.clone, a.work)
    if a.write:
        MANIFEST_PATH.write_text(json.dumps(actual, indent=1, sort_keys=True) + "\n")
        print(f"wrote {MANIFEST_PATH} ({len(actual['problems'])} problems, "
              f"{len(actual['domain_files'])} domain files)")
        return 0
    expected = json.loads(MANIFEST_PATH.read_text())
    d = diff(expected, actual)
    for line in d:
        print(line)
    print("manifest check:", "OK" if not d else f"FAILED ({len(d)} differences)")
    return 0 if not d else 1


if __name__ == "__main__":
    sys.exit(main())
