"""Run manifest — the apparatus settings of one results directory, persisted
BEFORE the first API call and checked on every resume.

Why this exists (frontier budget probe, development/frontier_budget_probe_prereg.md
§2.3 item 5, gate-5 review 2026-09-10): the frontier runners are resumable by
re-running the same command against the same `--out`, and nothing used to stop a
resume from continuing an interrupted run under different settings — a 6,144-token
budget run could be topped up at 64,000, or a 16,384-char snapshot run at 262,144,
and the mixed corpus would carry no trace of it. The manifest makes the settings a
property of the DIRECTORY, not of the command line that happened to be typed:

  * `ensure_manifest` is called after job selection and before any request. On a
    fresh directory it writes `run_manifest.json`; on a directory that already has
    one it compares every registered setting and refuses to continue on any
    difference; on a directory that has trials but no manifest it refuses outright
    (the existing rows have no verifiable settings — use a fresh `--out`).
  * Downstream readers use it as provenance: `tools/e2e_regrade.py` takes the
    snapshot length from it instead of inferring the cap from the response-length
    histogram (legacy corpora without a manifest keep the inference), and
    `tools/budget_probe_analysis.py` asserts every prereg-registered setting
    against it before reading a single probe row.

Fields are plain JSON scalars/lists so equality is exact. `created_at` and
`sdk_version` are recorded but NOT compared (a resume after a patch-level SDK
upgrade is reported as a warning by the caller, not refused).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

MANIFEST_NAME = "run_manifest.json"
MANIFEST_VERSION = 1

# Recorded but exempt from the resume comparison.
UNCOMPARED_FIELDS = ("created_at", "sdk_version")


class ManifestError(ValueError):
    """A results directory cannot be (re)used under the requested settings."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ground_truth_sha256(ground_truth: dict) -> str:
    """Content hash of a ground-truth dict (cached or freshly generated), so two
    runs can be compared on WHAT they graded against regardless of where the
    dict came from. Canonical JSON: sorted keys, compact separators."""
    payload = json.dumps(ground_truth, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    backend: str,
    model: str,
    with_tools: bool,
    tasks: list[str],
    corpus: str,
    domains_dir: str,
    prompt_variants: list[int],
    num_predict: int | None,
    snapshot_len: int | None,
    max_iterations: int,
    stream: bool,
    temperature: int | float,
    think: str,
    ground_truth_source: str,
    ground_truth_sha256: str,
    gt_cache_sha256: str | None,
    gt_cache_path: str | None,
    sdk_version: str | None,
    keys_files: list[str] | None = None,
    limit: int | None = None,
    extra: dict | None = None,
) -> dict:
    """Assemble the manifest dict. Every argument is a registered setting; the
    keyword-only signature makes a caller that forgets one fail at import
    time rather than write a manifest with a silently missing field."""
    m = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "backend": backend,
        "sdk_version": sdk_version,
        "model": model,
        "with_tools": bool(with_tools),
        "conditions": "tools" if with_tools else "no-tools",
        "tasks": sorted(tasks),
        "corpus": corpus,
        "domains_dir": domains_dir,
        "prompt_variants": sorted(int(v) for v in prompt_variants),
        "num_predict": num_predict,
        "snapshot_len": snapshot_len,
        "max_iterations": int(max_iterations),
        "stream": bool(stream),
        "temperature": temperature,
        "think": think,
        "ground_truth": ground_truth_source,
        "ground_truth_sha256": ground_truth_sha256,
        "gt_cache_sha256": gt_cache_sha256,
        "gt_cache_path": gt_cache_path,
        "keys_files": list(keys_files) if keys_files else None,
        "limit": limit,
    }
    if extra:
        m.update(extra)
    return m


def read_manifest(out_dir: Path) -> dict | None:
    path = Path(out_dir) / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        m = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{path}: unreadable manifest ({exc})") from exc
    if not isinstance(m, dict) or m.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestError(f"{path}: unknown manifest version "
                            f"{m.get('manifest_version') if isinstance(m, dict) else m!r}")
    return m


def write_manifest(out_dir: Path, manifest: dict) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / MANIFEST_NAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
    return path


def manifest_diffs(existing: dict, requested: dict) -> list[tuple[str, object, object]]:
    """(field, existing, requested) for every compared field that differs. A
    field present on one side only counts as a difference."""
    diffs = []
    for k in sorted(set(existing) | set(requested)):
        if k in UNCOMPARED_FIELDS:
            continue
        a, b = existing.get(k, "<absent>"), requested.get(k, "<absent>")
        if a != b:
            diffs.append((k, a, b))
    return diffs


def has_trials(out_dir: Path) -> bool:
    return any(Path(out_dir).glob("trials*.jsonl"))


def ensure_manifest(out_dir: Path, requested: dict) -> dict:
    """Make `out_dir` safe to write under `requested`.

    Returns the manifest in force (the existing one on a compatible resume,
    else the freshly written one). Raises ManifestError when:
      * trials exist but no manifest does — the rows carry no verifiable
        settings, so a resume cannot prove it is continuing the same run;
      * a manifest exists and any compared field differs.
    Must be called BEFORE restoring/compacting trials and before the first
    API call, so a refused resume touches nothing.
    """
    out_dir = Path(out_dir)
    existing = read_manifest(out_dir)
    if existing is None:
        if has_trials(out_dir):
            raise ManifestError(
                f"{out_dir} holds trials but no {MANIFEST_NAME}: the existing rows "
                "have no verifiable settings. Use a fresh --out (or move the old "
                "rows aside) — a resume cannot prove it continues the same run.")
        write_manifest(out_dir, requested)
        return requested
    diffs = manifest_diffs(existing, requested)
    if diffs:
        lines = "\n".join(f"  {k}: existing={a!r} requested={b!r}" for k, a, b in diffs)
        raise ManifestError(
            f"{out_dir / MANIFEST_NAME} was written under different settings; "
            f"refusing to resume into it:\n{lines}\nUse a fresh --out.")
    return existing
