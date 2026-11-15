"""Resume persisted mock runs without losing responses or repeating valid calls."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from harness import run, score
from harness.prompts import render_rewrite

PAIRS = Path(__file__).resolve().parents[1] / "data/pairs_example.jsonl"


def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def key(record):
    return tuple(record[k] for k in ("pair_id", "condition", "repeat", "task", "stage"))


@pytest.fixture
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network without --live")
    monkeypatch.setattr(run, "LiveBackend", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)


@pytest.mark.parametrize("n,stop_after", [(1, 1), (1, 3), (1, 5), (1, 19), (1, 62), (3, 25), (3, 188)])
def test_resume_interrupted_run(tmp_path, offline, n, stop_after):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", str(n)]
    original = run.MockBackend.complete
    calls = 0

    def interrupt(backend, messages, repeat):
        nonlocal calls
        if calls == stop_after:
            raise KeyboardInterrupt
        calls += 1
        return original(backend, messages, repeat)

    with patch.object(run.MockBackend, "complete", interrupt), pytest.raises(KeyboardInterrupt):
        run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    prefix = path.read_bytes()
    saved = read_records(path)
    assert len(saved) == stop_after
    with patch.object(run.MockBackend, "complete", autospec=True, side_effect=original) as complete:
        assert run.main(args + ["--resume"]) == 0
        assert complete.call_count == 63 * n - stop_after
    records = read_records(path)
    assert path.read_bytes().startswith(prefix)
    assert len(records) == len({key(r) for r in records}) == 63 * n
    assert len(list(tmp_path.glob("raw_*.jsonl"))) == 1
    report = score.summarize(records, draws=10)["mock"]
    assert report["total_judge_records"] == 54 * n
    assert report["rewrite_records"] == 9 * n
    rewrites = {key(r)[:3]: r for r in records if r["stage"] == "rewrite"}
    for record in records:
        if record["stage"] == "judge" and record["condition"].endswith("_deeuph"):
            expected = render_rewrite(rewrites[key(record)[:3]]["answer"])
            assert record["evaluated_text"] == expected
            assert json.loads(record["messages"][-1]["content"])["passage"] == expected
    unchanged = path.read_bytes()
    with patch.object(run.MockBackend, "complete", side_effect=AssertionError("repeated valid query")):
        assert run.main(args + ["--resume", "--retry-invalid"]) == 0
    assert path.read_bytes() == unchanged


def test_resume_invalid_requires_retry_and_keeps_newest(tmp_path, offline):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    with patch.object(run.MockBackend, "complete", return_value={"text": "", "response": {}}):
        run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    old = read_records(path)
    unchanged = path.read_bytes()
    with patch.object(run.MockBackend, "complete", side_effect=AssertionError("retried invalid query")):
        run.main(args + ["--resume"])
    assert path.read_bytes() == unchanged
    real_replace = run.os.replace
    with patch.object(run.os, "replace", wraps=real_replace) as replace:
        run.main(args + ["--resume", "--retry-invalid"])
    assert replace.called
    records = read_records(path)
    assert len(records) == len({key(r) for r in records}) == 63
    assert all(r["status"] == "VALID" for r in records)
    assert {r["run_id"] for r in records} == {old[0]["run_id"]}
    assert score.summarize(records, draws=10)["mock"]["invalid_count"] == 0


def test_resume_missing_file(tmp_path, offline):
    assert run.main(["--pairs", str(PAIRS), "--results-dir", str(tmp_path),
                     "--n", "1", "--resume"]) == 0
    assert score.summarize(read_records(tmp_path / "raw_mock.jsonl"), draws=10)["mock"]["rewrite_records"] == 9


@pytest.mark.parametrize("change", ["n", "pairs_sha256", "model", "prompt_version"])
def test_resume_rejects_mismatched_metadata(tmp_path, offline, change, capsys):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    records = read_records(path)
    records[0][change] = 2 if change == "n" else "different"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    before = path.read_bytes()
    with pytest.raises(SystemExit), patch.object(run.MockBackend, "complete", side_effect=AssertionError("query")):
        run.main(args + ["--resume"])
    assert "Cannot resume" in capsys.readouterr().err
    assert path.read_bytes() == before


def test_retry_replace_failure_preserves_file(tmp_path, offline):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    with patch.object(run.MockBackend, "complete", return_value={"text": "", "response": {}}):
        run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    before = path.read_bytes()
    with patch.object(run.os, "replace", side_effect=OSError("disk full")), pytest.raises(OSError):
        run.main(args + ["--resume", "--retry-invalid"])
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_resume_recovers_truncated_tail_and_newest_duplicate(tmp_path, offline):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    records = read_records(path)
    newest = dict(records[0], recovery_marker="newest")
    with path.open("a") as output:
        output.write(json.dumps(newest) + '\n{"pair_id":')
    with patch.object(run.MockBackend, "complete", side_effect=AssertionError("query")):
        run.main(args + ["--resume"])
    records = read_records(path)
    assert len(records) == 63
    assert records[0]["recovery_marker"] == "newest"
    score.summarize(records, draws=10)


def test_retry_invalid_preserves_valid_records_and_can_resume_again(tmp_path, offline):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    run.main(args)
    path = tmp_path / "raw_mock.jsonl"
    records = read_records(path)
    invalid_keys = {key(records[i]) for i in (3, 4, 5)}
    for record in records:
        if key(record) in invalid_keys:
            record.update(status="INVALID", answer=None, raw_text="", error="empty_output")
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    valid_records = {key(r): r for r in records if r["status"] == "VALID"}
    original = run.MockBackend.complete
    calls = 0

    def interrupt(backend, messages, repeat):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return original(backend, messages, repeat)

    with patch.object(run.MockBackend, "complete", interrupt), pytest.raises(KeyboardInterrupt):
        run.main(args + ["--resume", "--retry-invalid"])
    midway = read_records(path)
    assert len(midway) == 63
    assert sum(r["status"] == "INVALID" for r in midway) == 2
    with patch.object(run.MockBackend, "complete", autospec=True, side_effect=original) as complete:
        run.main(args + ["--resume", "--retry-invalid"])
        assert complete.call_count == 2
    result = read_records(path)
    assert all(r == valid_records[key(r)] for r in result if key(r) in valid_records)
    assert score.summarize(result, draws=10)["mock"]["invalid_count"] == 0


def test_resume_fills_unselected_conditions(tmp_path, offline):
    args = ["--pairs", str(PAIRS), "--results-dir", str(tmp_path), "--n", "1"]
    run.main(args + ["--conditions", "soft", "soft_deeuph"])
    run.main(args + ["--resume"])
    assert score.summarize(read_records(tmp_path / "raw_mock.jsonl"), draws=10)["mock"]["total_judge_records"] == 54


@pytest.mark.parametrize("options", [["--resume", "--overwrite"], ["--retry-invalid"]])
def test_resume_flag_conflicts(tmp_path, offline, options):
    with pytest.raises(SystemExit):
        run.main(["--pairs", str(PAIRS), "--results-dir", str(tmp_path)] + options)
    assert not list(tmp_path.iterdir())
