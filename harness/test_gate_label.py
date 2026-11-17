"""Offline tests for the gate label sheet and agreement scripts."""
import csv
import json
import shutil
from pathlib import Path

import pytest

from harness import build_gate_label_sheet as B
from harness import gate_label_agreement as G

FIX = Path(__file__).resolve().parent / "tests_fixtures"


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_pairs():
    with open(FIX / "pairs_tiny.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def build(tmp_path):
    B.main(["--pairs", str(FIX / "pairs_tiny.jsonl"), "--out-dir", str(tmp_path / "sheet"),
            "--key-dir", str(tmp_path / "key")])
    return tmp_path / "sheet", tmp_path / "key"


def test_sheet_blinded_and_complete(tmp_path):
    sd, kd = build(tmp_path)
    assert not (sd / "gate_label_key.csv").exists()
    assert not list(kd.glob("*sheet*"))
    sheet = read(sd / "gate_label_sheet.csv")
    key = read(kd / "gate_label_key.csv")
    assert list(sheet[0].keys()) == B.SHEET_COLS
    assert len(sheet) == 9 and len(key) == 9
    assert len({r["item_id"] for r in sheet}) == 9
    for r in sheet:
        assert r["harmed_stated"] == r["extent_stated"] == r["responsible_stated"] == ""
    with open(sd / "gate_label_sheet.csv", encoding="utf-8") as f:
        blob = f.read()
    assert "T01" not in blob and "contrast" not in blob.split("\n", 1)[1]
    assert {(k["pair_id"], k["condition"]) for k in key} == {
        (p, c) for p in ("T01", "T02", "T03") for c in ("soft", "plain", "contrast")}
    texts = {r["pair_id"]: r for r in load_pairs()}
    by_id = {r["item_id"]: r["text"] for r in sheet}
    for k in key:
        assert by_id[k["item_id"]] == texts[k["pair_id"]][k["condition"] + "_text"]


def test_sheet_deterministic_and_shuffled(tmp_path):
    pairs = load_pairs()
    a, ka = B.build_rows(pairs, 1)
    b, kb = B.build_rows(pairs, 1)
    assert a == b and ka == kb
    assert [k["condition"] for k in ka] != ["soft", "plain", "contrast"] * 3


def test_xlsx_optional(tmp_path):
    sd, _ = build(tmp_path)
    try:
        import openpyxl
    except ImportError:
        assert not (sd / "gate_label_sheet.xlsx").exists()
        return
    ws = openpyxl.load_workbook(sd / "gate_label_sheet.xlsx").active
    assert [c.value for c in ws[1]] == B.SHEET_COLS
    assert ws.max_row == 10


def test_kappa_values():
    assert G.kappa([("STATED", "STATED"), ("MISSING", "MISSING")]) == 1.0
    assert G.kappa([("STATED", "MISSING"), ("MISSING", "STATED")]) == -1.0
    assert G.kappa([("STATED", "STATED")] * 3) is None
    assert G.kappa([]) is None


def test_kappa_one_side_constant_is_zero_not_na():
    one_side = [("STATED", "STATED"), ("STATED", "MISSING"), ("STATED", "STATED")]
    assert G.kappa(one_side) == 0.0
    assert G.kappa([(b, a) for a, b in one_side]) == 0.0
    # both constant but different labels: also 0.0; both constant and equal: undefined
    assert G.kappa([("STATED", "MISSING")] * 2) == 0.0
    assert G.kappa([("MISSING", "MISSING")] * 2) is None


def test_bootstrap_reports_dropped_draws():
    # two incidents; resampling can pick one incident twice, giving both-constant-equal samples
    groups = {"A": [("STATED", "STATED")], "B": [("MISSING", "MISSING")]}
    k, lo, hi, dropped = G.boot_kappa(groups, draws=200)
    assert k == 1.0
    assert 0 < dropped < 200


def test_missing_key_ids_warn(tmp_path, capsys):
    sd, kd = build(tmp_path)
    sheet = read(sd / "gate_label_sheet.csv")
    sheet[0]["item_id"] = "G999"
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=B.SHEET_COLS)
        w.writeheader()
        w.writerows(sheet)
    labels = G.load_labels(tmp_path / "r.csv", kd / "gate_label_key.csv")
    assert len(labels) == 8
    assert "G999" in capsys.readouterr().err


def make_inputs(tmp_path, human):
    sd, kd = build(tmp_path)
    key = read(kd / "gate_label_key.csv")
    sheet = read(sd / "gate_label_sheet.csv")
    kmap = {r["item_id"]: (r["pair_id"], r["condition"]) for r in key}
    for r in sheet:
        lab = human(*kmap[r["item_id"]])
        r["harmed_stated"], r["extent_stated"], r["responsible_stated"] = lab
    with open(tmp_path / "returned.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=B.SHEET_COLS)
        w.writeheader()
        w.writerows(sheet)
    res = tmp_path / "res"
    res.mkdir()
    shutil.copy(FIX / "omission_tiny.jsonl", res / "raw_m1.jsonl")
    return tmp_path / "returned.csv", kd / "gate_label_key.csv", res


def test_agreement_perfect_and_invalid_skipped(tmp_path):
    def human(pid, cond):
        return ("STATED",) * 3 if cond != "soft" else ("MISSING",) * 3
    lab, key, res = make_inputs(tmp_path, human)
    probe = G.load_probe(res)
    assert len(probe["m1"]) == 5  # INVALID row dropped
    labels = G.load_labels(lab, key)
    g = G.by_incident(labels, probe["m1"], "harmed")
    assert sum(len(v) for v in g.values()) == 5
    k, lo, hi, dropped = G.boot_kappa(g, draws=200)
    assert k == 1.0
    lines = G.main(["--labels", str(lab), "--key", str(key), "--results-dir", str(res), "--draws", "200"])
    assert len(lines) == 2 + 3
    assert "| m1 | harmed | 5 | 1.00 |" in lines[2]
    assert " of 200 |" in lines[2]


def test_agreement_disagreement_and_blanks(tmp_path):
    def human(pid, cond):
        return ("MISSING",) * 3 if cond != "soft" else ("STATED",) * 3
    lab, key, res = make_inputs(tmp_path, human)
    labels = G.load_labels(lab, key)
    g = G.by_incident(labels, G.load_probe(res)["m1"], "extent")
    assert G.kappa([p for v in g.values() for p in v]) < 0
    labels[("T01", "soft")] = {}
    g = G.by_incident(labels, G.load_probe(res)["m1"], "extent")
    assert sum(len(v) for v in g.values()) == 4
