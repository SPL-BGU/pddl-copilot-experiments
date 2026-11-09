"""Unit tests for tools/extension_copy_reused.py (temp dirs only, no real data).

Runs under pytest (`pytest -q tests/test_extension_copy_reused.py`) and
standalone (`python3 tests/test_extension_copy_reused.py`).
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pddl_eval.resume import load_progress  # noqa: E402
from tools import extension_copy_reused as X  # noqa: E402

MODEL = "org/Model-A"
STAMP = "2026-11-09T12:00:00Z"


def _result(model, task, dname, pname, pv, with_tools):
    """A record shaped like pddl_eval.runner.TaskResult (all fields)."""
    from dataclasses import fields
    from pddl_eval.runner import TaskResult
    vals = {f.name: None for f in fields(TaskResult)}
    vals.update(model=model, task=task, domain_name=dname, problem_name=pname,
                prompt_variant=pv, with_tools=with_tools, success=True)
    return TaskResult(**vals).__dict__


def _row(model, task, pname, pv, with_tools, label=""):
    key = [model, task, "blocksworld", pname, label, pv, with_tools, "off",
           "all" if with_tools else "", "minimal" if with_tools else ""]
    return json.dumps({"key": key, "result": _result(model, task, "blocksworld", pname,
                                                     pv, with_tools)})


def _source(root: Path, lines: list[str], name="delivered-rerun", cell="cellA") -> Path:
    d = root / "results" / name / cell
    d.mkdir(parents=True)
    p = d / "trials.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def _lines():
    return [
        _row(MODEL, "solve", "p01", 11, True),
        _row(MODEL, "solve", "p02", 11, True),
        _row(MODEL, "solve", "p01", 12, True),
        _row(MODEL, "solve", "p01", 11, False),          # other arm
        _row(MODEL, "validate_plan", "p01", 11, True, "v1"),  # other task
        _row("org/Model-B", "solve", "p01", 11, True),   # other model
    ]


def _copy(src, dest, **kw):
    args = dict(source=src, source_job="21982370", model=MODEL, tasks=["solve"], arm="tools",
                variants=[11], dest=dest, copied_at=STAMP)
    args.update(kw)
    return X.copy_reused(**args)


def _refused(fn) -> str:
    try:
        fn()
    except SystemExit as e:
        return str(e)
    raise AssertionError("expected a refusal")


def test_copies_filtered_rows_with_provenance():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines())
        before = src.read_bytes()
        dest = root / "results" / "extension-live" / "cellA"
        rec = _copy(src, dest)
        assert src.read_bytes() == before, "source changed"
        out = (dest / "trials.jsonl").read_text().splitlines()
        assert len(out) == 2 and rec["copied_rows"] == 2 and rec["source_rows"] == 6
        src_lines = before.decode().splitlines()
        sha = hashlib.sha256(before).hexdigest()
        for o, s in zip(out, [src_lines[0], src_lines[1]]):
            assert o.startswith(s[:-1]), "copied row is not the source line plus fields"
            got = json.loads(o)
            assert got["reused_from_job"] == "21982370"
            assert got["reused_from_sha256"] == sha
            assert got["copied_at"] == STAMP
            assert got["reused_from_folder"].endswith("delivered-rerun/cellA")
            stripped = {k: v for k, v in got.items() if k not in X.PROVENANCE_FIELDS}
            assert stripped == json.loads(s)
        side = json.loads((dest / X.SIDECAR).read_text())
        assert side["dest_trials_sha256"] == hashlib.sha256(
            (dest / "trials.jsonl").read_bytes()).hexdigest()
        assert side["filter"] == {"model": MODEL, "tasks": ["solve"], "arm": "tools",
                                  "variants": [11]}


def test_resume_loader_reads_copied_rows():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines())
        dest = root / "results" / "extension-live" / "cellA"
        _copy(src, dest, variants=[11, 12])
        restored = load_progress(dest / "trials.jsonl")
        assert len(restored) == 3
        assert all(k[0] == MODEL and k[1] == "solve" and k[6] is True for k in restored)


def test_no_tools_arm_and_duplicates():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        lines = _lines()
        src = _source(root, lines + [lines[3]])            # duplicate no-tools row
        dest = root / "results" / "extension-live" / "cellB"
        rec = _copy(src, dest, arm="no-tools")
        assert rec["copied_rows"] == 1 and rec["duplicate_keys_skipped"] == 1


def test_refuses_frozen_destinations():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines())
        for bad in (root / "results" / "delivered-rerun" / "new",
                    root / "results" / "sweep5v2-live" / "x",
                    root / "results" / "sweep6-live" / "x",
                    root / "results" / "foo_sweep6" / "x"):
            msg = _refused(lambda: _copy(src, bad))
            assert "frozen corpus" in msg, msg
            assert not bad.exists()


def test_refuses_source_folder_and_overwrite():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines(), name="other-run")
        assert "source folder" in _refused(lambda: _copy(src, src.parent))
        assert "source folder" in _refused(lambda: _copy(src, src.parent / "sub"))
        dest = root / "results" / "extension-live" / "cellA"
        _copy(src, dest)
        first = (dest / "trials.jsonl").read_bytes()
        assert "never overwrites" in _refused(lambda: _copy(src, dest))
        assert (dest / "trials.jsonl").read_bytes() == first
        dest2 = root / "results" / "extension-live" / "cellC"
        dest2.mkdir(parents=True)
        (dest2 / X.SIDECAR).write_text("{}")
        assert "never overwrites" in _refused(lambda: _copy(src, dest2))
        assert not (dest2 / "trials.jsonl").exists()


def test_refuses_bad_inputs():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        dest = root / "results" / "extension-live" / "c"
        torn = _source(root, _lines() + ['{"key": ["x"'], name="r1")
        assert "not a complete trial record" in _refused(lambda: _copy(torn, dest))
        short = _source(root, [json.dumps({"key": [MODEL, "solve"], "result": {}})], name="r2")
        assert "wrong shape" in _refused(lambda: _copy(short, dest))
        again = _source(root, [_lines()[0][:-1] + ', "copied_at": "x"}'], name="r3")
        assert "already carries" in _refused(lambda: _copy(again, dest))
        src = _source(root, _lines(), name="r4")
        assert "keeps no row" in _refused(lambda: _copy(src, dest, model="nope"))
        assert "ISO 8601" in _refused(lambda: _copy(src, dest, copied_at="yesterday"))
        assert "empty" in _refused(lambda: _copy(src, dest, source_job=" "))
        assert "trials.jsonl" in _refused(lambda: _copy(src.parent / "x.jsonl", dest))
        assert not dest.exists()


def test_job_id_must_match_summary_meta_when_recorded():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines(), name="r5")
        (src.parent / "summary_20261004_000000.json").write_text(
            json.dumps({"single_task": [], "meta": {"slurm_job_id": 111}}))
        dest = root / "results" / "extension-live" / "c"
        assert "differs" in _refused(lambda: _copy(src, dest, source_job="222"))
        _copy(src, dest, source_job="111")
        # no job id in meta (today's corpora): any given id is accepted
        src2 = _source(root, _lines(), name="r6")
        (src2.parent / "summary_20261004_000000.json").write_text(
            json.dumps({"single_task": [], "meta": {"think": "off"}}))
        _copy(src2, root / "results" / "extension-live" / "d", source_job="999")


def test_cli():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = _source(root, _lines(), name="r7")
        dest = root / "results" / "extension-live" / "cli"
        X.main(["--source", str(src), "--source-job", "21982370", "--model", MODEL,
                "--task", "solve", "--arm", "tools", "--variant", "11", "12",
                "--dest", str(dest), "--copied-at", STAMP])
        assert len((dest / "trials.jsonl").read_text().splitlines()) == 3


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"test_extension_copy_reused: {len(tests)}/{len(tests)} passed")
