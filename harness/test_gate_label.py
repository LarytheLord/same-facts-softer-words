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
    return list(csv.DictReader(open(p, encoding="utf-8", newline="")))


def test_sheet_blinded_and_complete(tmp_path):
    B.main(["--pairs", str(FIX / "pairs_tiny.jsonl"), "--out-dir", str(tmp_path)])
    sheet = read(tmp_path / "gate_label_sheet.csv")
    key = read(tmp_path / "gate_label_key.csv")
    assert list(sheet[0].keys()) == B.SHEET_COLS
    assert len(sheet) == 9 and len(key) == 9
    assert len({r["item_id"] for r in sheet}) == 9
    for r in sheet:
        assert r["harmed_stated"] == r["extent_stated"] == r["responsible_stated"] == ""
    blob = open(tmp_path / "gate_label_sheet.csv", encoding="utf-8").read()
    assert "T01" not in blob and "contrast" not in blob.split("\n", 1)[1]
    assert {(k["pair_id"], k["condition"]) for k in key} == {
        (p, c) for p in ("T01", "T02", "T03") for c in ("soft", "plain", "contrast")}
    texts = {json.loads(l)["pair_id"]: json.loads(l) for l in open(FIX / "pairs_tiny.jsonl")}
    by_id = {r["item_id"]: r["text"] for r in sheet}
    for k in key:
        assert by_id[k["item_id"]] == texts[k["pair_id"]][k["condition"] + "_text"]


def test_sheet_deterministic_and_shuffled(tmp_path):
    pairs = [json.loads(l) for l in open(FIX / "pairs_tiny.jsonl")]
    a, ka = B.build_rows(pairs, 1)
    b, kb = B.build_rows(pairs, 1)
    assert a == b and ka == kb
    assert [k["condition"] for k in ka] != ["soft", "plain", "contrast"] * 3


def test_xlsx_optional(tmp_path):
    B.main(["--pairs", str(FIX / "pairs_tiny.jsonl"), "--out-dir", str(tmp_path)])
    try:
        import openpyxl
    except ImportError:
        assert not (tmp_path / "gate_label_sheet.xlsx").exists()
        return
    ws = openpyxl.load_workbook(tmp_path / "gate_label_sheet.xlsx").active
    assert [c.value for c in ws[1]] == B.SHEET_COLS
    assert ws.max_row == 10


def test_kappa_values():
    assert G.kappa([("STATED", "STATED"), ("MISSING", "MISSING")]) == 1.0
    assert G.kappa([("STATED", "MISSING"), ("MISSING", "STATED")]) == -1.0
    assert G.kappa([("STATED", "STATED")] * 3) is None
    assert G.kappa([]) is None


def make_inputs(tmp_path, human):
    pairs = [json.loads(l) for l in open(FIX / "pairs_tiny.jsonl")]
    B.main(["--pairs", str(FIX / "pairs_tiny.jsonl"), "--out-dir", str(tmp_path)])
    key = read(tmp_path / "gate_label_key.csv")
    sheet = read(tmp_path / "gate_label_sheet.csv")
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
    return tmp_path / "returned.csv", tmp_path / "gate_label_key.csv", res


def test_agreement_perfect_and_invalid_skipped(tmp_path):
    def human(pid, cond):
        return ("STATED",) * 3 if cond != "soft" else ("MISSING",) * 3
    lab, key, res = make_inputs(tmp_path, human)
    probe = G.load_probe(res)
    assert len(probe["m1"]) == 5  # INVALID row dropped
    labels = G.load_labels(lab, key)
    g = G.by_incident(labels, probe["m1"], "harmed")
    assert sum(len(v) for v in g.values()) == 5
    k, lo, hi = G.boot_kappa(g, draws=200)
    assert k == 1.0
    lines = G.main(["--labels", str(lab), "--key", str(key), "--results-dir", str(res), "--draws", "200"])
    assert len(lines) == 2 + 3
    assert "| m1 | harmed | 5 | 1.00 |" in lines[2]


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
