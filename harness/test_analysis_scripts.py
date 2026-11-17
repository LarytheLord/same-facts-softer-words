"""Offline tests for the analysis scripts. No API calls, no network, no keys.

Fixtures live in harness/tests_fixtures/. Saved results under harness/results_*/ are only read.
"""
import re
from pathlib import Path

import pytest

from harness import clearance, judge_check, omission_arm, rescore_probes, two_step

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "harness" / "tests_fixtures"


def table_rows(text):
    """Data rows of a markdown table (header and separator lines dropped)."""
    rows = []
    for line in text.splitlines():
        if line.startswith("| ") and not line.startswith("| ---") and not line.startswith("| Model") \
                and not line.startswith("| Judge"):
            rows.append(line.strip())
    return rows


# ---- two_step -------------------------------------------------------------------------------

@pytest.fixture
def two_step_dirs(monkeypatch):
    monkeypatch.setattr(two_step, "SCORE_DIRS", [str(FIX / "scores")])
    monkeypatch.setattr(two_step, "PROBE_DIRS", [str(FIX / "probe")])


def test_two_step_norm_strips_provider_prefix():
    assert two_step.norm("adaption:m1") == "m1"
    assert two_step.norm("anthropic:claude-x") == "claude-x"
    assert two_step.norm("openai/gpt") == "openai/gpt"


def test_two_step_gate_default_threshold(two_step_dirs, capsys):
    two_step.main([])
    out = capsys.readouterr().out
    # Pairs S1..S8; S8 has scores but no probe so it is excluded -> 7 pairs.
    # One-step closes S1,S3,S4,S5,S6 (mean <= 2) = 5.
    # Two-step: S1,S6 closed; S3 (majority harmed MISSING), S4 (exactly half, not a majority)
    # and S5 (extent MISSING) insufficient; S2 (mean 8) and S7 (mean 2.5) escalated.
    assert "| m1 | company statement | 5 of 7 | 2 / 3 / 2 |" in out
    # The fixture has only the soft condition; the other two are empty.
    assert "| m1 | regulator record | 0 of 0 | 0 / 0 / 0 |" in out
    assert "| m1 | one-fact contrast | 0 of 0 | 0 / 0 / 0 |" in out


def test_two_step_threshold_is_inclusive_and_configurable(two_step_dirs, capsys):
    two_step.main(["--thresh", "3"])
    out = capsys.readouterr().out
    # S7 (mean 2.5) now closes: one-step 6, two-step closed S1,S6,S7 = 3, insufficient 3, escalated S2.
    assert "| m1 | company statement | 6 of 7 | 3 / 3 / 1 |" in out
    two_step.main(["--thresh", "1"])
    out = capsys.readouterr().out
    # mean 1 is closed (<=), mean 2 (S6) is not.
    assert "| m1 | company statement | 4 of 7 | 1 / 3 / 3 |" in out


def test_two_step_ignores_invalid_rows(two_step_dirs):
    scores = two_step.load_scores()["m1"]
    assert scores[("S2", "soft")] == [8, 8]  # INVALID, wrong-stage and wrong-task rows dropped


def test_two_step_probe_needs_both_facts_stated(two_step_dirs):
    probe = two_step.load_probe()["m1"]
    assert probe[("S5", "soft")] == [False, False]
    assert probe[("S1", "soft")] == [True, True, False]


# ---- clearance ------------------------------------------------------------------------------

def test_clearance_counts_closed_at_threshold(capsys):
    clearance.main(["--dirs", str(FIX / "clearance")])
    out = capsys.readouterr().out
    # soft: C1 mean 1.5 closed, C2 mean 2.5 open, C3 exactly 2 closed -> 2 of 3.
    # plain: C1 score 9 -> 0 of 1. contrast: no rows -> 0 of 0.
    assert "| m | 2 of 3 | 0 of 1 | 0 of 0 |" in out


def test_clearance_threshold_option(capsys):
    clearance.main(["--dirs", str(FIX / "clearance"), "--thresh", "1"])
    assert "| m | 0 of 3 | 0 of 1 | 0 of 0 |" in capsys.readouterr().out
    clearance.main(["--dirs", str(FIX / "clearance"), "--thresh", "3"])
    assert "| m | 3 of 3 | 0 of 1 | 0 of 0 |" in capsys.readouterr().out


# ---- omission_arm ---------------------------------------------------------------------------

def test_tokens_lowercases_and_keeps_apostrophes():
    assert omission_arm.tokens("Two workers DIED; it's 12.5 km.") == ["two", "workers", "died", "it's", "12", "5", "km"]


SOURCE = "A fire broke out at the plant. Three workers were injured and one died. The company shut the site."


def test_deletions_pass():
    src = omission_arm.tokens(SOURCE)
    for kept in ("A fire broke out at the plant. The company shut the site.",
                 "fire plant company site",
                 SOURCE):
        assert omission_arm.is_subsequence(omission_arm.tokens(kept), src)
    assert omission_arm.is_subsequence([], src)


def test_rewording_and_reordering_fail():
    src = omission_arm.tokens(SOURCE)
    reworded = "A blaze broke out at the plant."
    reordered = "The plant broke out at a fire."
    added = "A fire broke out at the large plant."
    for bad in (reworded, reordered, added):
        assert not omission_arm.is_subsequence(omission_arm.tokens(bad), src)


def test_subsequence_respects_repeat_counts():
    assert not omission_arm.is_subsequence(["a", "a"], ["a", "b"])
    assert omission_arm.is_subsequence(["a", "a"], ["a", "b", "a"])


def test_parse_extracts_omitted_text():
    assert omission_arm.parse('x {"omitted_text": "hello"} y') == "hello"
    assert omission_arm.parse('{"omitted_text": "  "}') is None
    assert omission_arm.parse("no json") is None
    assert omission_arm.parse(None) is None


def test_omission_arm_refuses_without_live(tmp_path):
    out = tmp_path / "o.jsonl"
    with pytest.raises(SystemExit) as e:
        omission_arm.main(["--out", str(out), "--pairs-out", str(tmp_path / "p.jsonl")])
    assert e.value.code == 2
    assert not out.exists()


def test_omission_arm_refuses_to_overwrite(tmp_path):
    out = tmp_path / "o.jsonl"
    out.write_text("keep me\n")
    with pytest.raises(SystemExit) as e:
        omission_arm.main(["--live", "--out", str(out), "--pairs-out", str(tmp_path / "p.jsonl")])
    assert e.value.code == 2
    assert out.read_text() == "keep me\n"
    assert not (tmp_path / "p.jsonl").exists()


# ---- judge_check ----------------------------------------------------------------------------

def test_judge_check_refuses_mock_into_non_mock_folder(tmp_path):
    target = tmp_path / "real_results"
    with pytest.raises(SystemExit) as e:
        judge_check.main(["--out-dir", str(target)])
    assert e.value.code == 2
    assert not target.exists()


def test_judge_check_refuses_folder_with_existing_raw(tmp_path):
    target = tmp_path / "x_mock"
    target.mkdir()
    existing = target / "raw_something.jsonl"
    existing.write_text("evidence\n")
    with pytest.raises(SystemExit) as e:
        judge_check.main(["--out-dir", str(target)])
    assert e.value.code == 2
    assert existing.read_text() == "evidence\n"
    assert [p.name for p in target.iterdir()] == ["raw_something.jsonl"]


# ---- rescore_probes -------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["results_scale", "results_scale_glm", "results_scale_claude"])
def test_rescore_scale_matches_committed_summary(name):
    d = ROOT / "harness" / name
    rebuilt = rescore_probes.scale_rows(d)
    committed = table_rows((d / "summary.md").read_text(encoding="utf-8"))
    assert rebuilt and rebuilt == committed


# The committed omission summaries list models in the order the live run finished; the rebuild
# lists them in raw file name order. The row contents must match exactly, so compare as sets of
# exact rows plus equal counts.
@pytest.mark.parametrize("name", ["results_omission", "results_omission_claude",
                                  "results_omission_groq", "results_omission_glm"])
def test_rescore_omission_matches_committed_summary(name):
    """Rebuilt rows must equal the committed summary rows exactly.

    The comparison sorts the rows first: the committed results_omission_groq summary lists
    models in live-run order, while rescore_probes.py lists them in raw file name order.
    Row contents are compared exactly; only the order of rows is ignored.
    """
    d = ROOT / "harness" / name
    rebuilt = rescore_probes.omission_rows(d)
    committed = table_rows((d / "summary.md").read_text(encoding="utf-8"))
    assert rebuilt and sorted(rebuilt) == sorted(committed)
