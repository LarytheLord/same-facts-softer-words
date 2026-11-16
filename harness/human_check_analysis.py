"""Score the blind human fact-preservation check (no API calls).

Joins the returned sheet (human_check/returned/*.xlsx, column 'Same facts? (yes/no)') with the
hidden key (human_check/key.csv). Reports same-facts rates by item type, agreement between the
automatic synthetic checker and the human, and writes human_check/returned/human_same_facts.csv
for `analyze_synth.py --human`.
"""
import csv
import glob
from collections import Counter

from openpyxl import load_workbook


def main():
    path = sorted(glob.glob("human_check/returned/*.xlsx"))[0]
    ws = load_workbook(path, data_only=True)["Items"]
    ans = {r[0]: ((str(r[3]).strip().lower() if r[3] else ""), r[4] or "") for r in list(ws.iter_rows(values_only=True))[1:]}
    key = {r["item"]: r for r in csv.DictReader(open("human_check/key.csv"))}
    print("rater file:", path, "| answers:", dict(Counter(a for a, _ in ans.values())))
    for src in ("defense", "synthetic"):
        xs = [ans[q][0] for q, k in key.items() if k["source"] == src]
        print(f"{src}: same facts {xs.count('yes')} of {len(xs)}")
    syn = [(key[q]["auto_checker"], ans[q][0]) for q in key if key[q]["source"] == "synthetic"]
    print("checker vs human agreement:", sum((c == "kept") == (a == "yes") for c, a in syn), "of", len(syn))
    print("synthetic same-facts by move:", dict(Counter((key[q]["condition"], ans[q][0]) for q in key if key[q]["source"] == "synthetic")))
    with open("human_check/returned/human_same_facts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "same_facts", "item", "source"])
        for q, k in key.items():
            if k["source"] == "synthetic":
                w.writerow([k["pair_id"] + "_" + k["condition"], ans[q][0], q, "synthetic"])


if __name__ == "__main__":
    main()
