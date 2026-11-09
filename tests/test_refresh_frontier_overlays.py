"""Tests for tools/checkpoints/refresh_frontier_overlays.py.

The script runs on the laptop, where the 09-12 frontier files live. These
tests build a small fake results/ tree and check the safety rules: check-only
by default, nothing built when an input is missing, no overwrite without
--force, no output inside results/, results/ left untouched, and the same
files giving the same zip bytes.

Run standalone: `python3 tests/test_refresh_frontier_overlays.py`
"""
import contextlib
import hashlib
import importlib.util
import io
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests._helpers import TestResults  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "refresh_frontier_overlays",
    REPO_ROOT / "tools" / "checkpoints" / "refresh_frontier_overlays.py")
rfo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rfo)


def _fake_repo(root: Path) -> None:
    res = root / "results"
    ovl = res / "derived" / "e2e_overlay"
    for tier in rfo.TIERS:
        d = ovl / f"{tier}-frontier"
        d.mkdir(parents=True)
        for stem in rfo.OVERLAY_REQUIRED[tier]:
            (d / f"{stem}.e2e.jsonl").write_text(f'{{"cell": "{tier}/{stem}"}}\n')
        for cell in rfo.RAW_CELLS[tier]:
            c = res / f"{tier}-frontier" / cell
            (c / "batch").mkdir(parents=True)
            (c / "trials.jsonl").write_text(f'{{"cell": "{cell}"}}\n')
            (c / "batch" / "results_full.jsonl").write_text("{}\n")
            (c / ".DS_Store").write_text("junk")
    for corpus in rfo.KEEP_CORPORA:
        (ovl / corpus).mkdir()
    for rel in rfo.DERIVED_MEMBERS:
        p = res / "derived" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("corpus,n\nsweep7,1\n" if rel.endswith(".csv") else "x\n")


def _tree_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        h.update(str(p.relative_to(folder)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def _run(args):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        rc = rfo.main(args)
    return rc, buf_out.getvalue() + buf_err.getvalue()


def test_check_only_writes_nothing(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fake_repo(root)
        rc, out = _run(["--repo", str(root)])
        r.check_eq("check-only exit code", rc, 0)
        r.check("check-only makes no checkpoints/", not (root / "checkpoints").exists())
        r.check("pooled csv summary printed", "1 data rows" in out, out)


def test_build_and_safety(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fake_repo(root)
        before = _tree_hash(root / "results")
        ck = root / "ck"
        rc, out = _run(["--repo", str(root), "--out", str(ck), "--write"])
        r.check_eq("build exit code", rc, 0)
        r.check("results/ untouched", _tree_hash(root / "results") == before)
        want = (1 + 1 + 1 + len(rfo.RAW_CELLS["haiku"]) + len(rfo.RAW_CELLS["sonnet"]))
        zips = sorted(ck.rglob("*.zip"))
        r.check_eq("zip count", len(zips), want)
        r.check("no staging folder left", not list(ck.glob(".refresh-*")))

        names = zipfile.ZipFile(ck / "e2e-overlay" / "haiku-frontier_overlay.zip").namelist()
        r.check_eq("overlay dir entry first", names[0], "haiku-frontier/")
        r.check("budget64k overlay included",
                "haiku-frontier/sweep5v2-budget64k.e2e.jsonl" in names, names)
        names = zipfile.ZipFile(ck / "e2e-overlay" / "derived_reports.zip").namelist()
        r.check_eq("derived members", names, sorted(rfo.DERIVED_MEMBERS))
        names = zipfile.ZipFile(ck / "frontier" / "sonnet-frontier_sweep5v2-with-tools.zip").namelist()
        r.check_eq("raw cell members (junk skipped, nested kept)", names, [
            "sonnet-frontier/sweep5v2-with-tools/batch/results_full.jsonl",
            "sonnet-frontier/sweep5v2-with-tools/trials.jsonl"])

        # Same files -> same bytes.
        ck2 = root / "ck2"
        _run(["--repo", str(root), "--out", str(ck2), "--write"])
        same = all(rfo.sha256(z) == rfo.sha256(ck2 / z.relative_to(ck)) for z in zips)
        r.check("deterministic zips", same)

        rc, out = _run(["--repo", str(root), "--out", str(ck), "--write"])
        r.check_eq("refuses overwrite without --force", rc, 1)
        rc, _ = _run(["--repo", str(root), "--out", str(ck), "--write", "--force"])
        r.check_eq("--force replaces", rc, 0)

        rc, _ = _run(["--repo", str(root), "--out", str(root / "results" / "x"), "--write"])
        r.check_eq("refuses --out inside results/", rc, 2)
        r.check("nothing made inside results/", not (root / "results" / "x").exists())


def test_missing_input_builds_nothing(r: TestResults) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fake_repo(root)
        (root / "results" / "derived" / "budget_probe" / "readout_haiku.json").unlink()
        ck = root / "ck"
        rc, out = _run(["--repo", str(root), "--out", str(ck), "--write"])
        r.check_eq("missing input exit code", rc, 1)
        r.check("missing file named", "readout_haiku.json" in out, out)
        r.check("no zips built", not list(ck.rglob("*.zip")) if ck.exists() else True)


def main() -> None:
    r = TestResults("test_refresh_frontier_overlays")
    test_check_only_writes_nothing(r)
    test_build_and_safety(r)
    test_missing_input_builds_nothing(r)
    r.report_and_exit()


if __name__ == "__main__":
    main()
