"""Build a blinded label sheet for the omission gate.

Reads data/pairs.jsonl and writes one row per text (soft, plain, contrast) in
random order. The rater sees only item_id, text and three STATED/MISSING
columns to fill in. A separate key file maps item_id to pair_id and condition.
Writes CSV always, and XLSX when openpyxl is installed. Offline, no API calls.
"""
import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = (("soft", "soft_text"), ("plain", "plain_text"), ("contrast", "contrast_text"))
SHEET_COLS = ["item_id", "text", "harmed_stated", "extent_stated", "responsible_stated", "rater_notes"]
KEY_COLS = ["item_id", "pair_id", "condition"]


def build_rows(pairs, seed=20261117):
    items = []
    for p in pairs:
        for cond, field in CONDITIONS:
            text = p.get(field)
            if isinstance(text, str) and text.strip():
                items.append((p["pair_id"], cond, text.strip()))
    rng = random.Random(seed)
    rng.shuffle(items)
    sheet, key = [], []
    for i, (pid, cond, text) in enumerate(items, 1):
        iid = "G%03d" % i
        sheet.append({"item_id": iid, "text": text, "harmed_stated": "", "extent_stated": "",
                      "responsible_stated": "", "rater_notes": ""})
        key.append({"item_id": iid, "pair_id": pid, "condition": cond})
    return sheet, key


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_xlsx(path, rows):
    try:
        from openpyxl import Workbook
        from openpyxl.worksheet.datavalidation import DataValidation
        from openpyxl.styles import Alignment
    except ImportError:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "labels"
    ws.append(SHEET_COLS)
    for r in rows:
        ws.append([r[c] for c in SHEET_COLS])
    dv = DataValidation(type="list", formula1='"STATED,MISSING"', allow_blank=True)
    ws.add_data_validation(dv)
    if rows:
        dv.add("C2:E%d" % (len(rows) + 1))
    ws.column_dimensions["B"].width = 100
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", type=Path, default=ROOT / "data/pairs.jsonl")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "human_check/gate_labels")
    ap.add_argument("--seed", type=int, default=20261117)
    a = ap.parse_args(argv)
    pairs = [json.loads(l) for l in open(a.pairs, encoding="utf-8") if l.strip()]
    sheet, key = build_rows(pairs, a.seed)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(a.out_dir / "gate_label_sheet.csv", SHEET_COLS, sheet)
    write_csv(a.out_dir / "gate_label_key.csv", KEY_COLS, key)
    xlsx = write_xlsx(a.out_dir / "gate_label_sheet.xlsx", sheet)
    print("wrote %d items to %s%s" % (len(sheet), a.out_dir, "" if xlsx else " (openpyxl missing, CSV only)"))


if __name__ == "__main__":
    main()
