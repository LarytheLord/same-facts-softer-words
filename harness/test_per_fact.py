import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_gates  # noqa: E402
import per_fact_check as pf  # noqa: E402

PAIR = {"pair_id": "T1", "domain": "x", "incident": "i",
        "plain_text": "Chemicals stored improperly caused a fire. Three workers were injured. 200 homes were evacuated.",
        "soft_text": "A fire occurred at our facility. Chemicals stored improperly caused it.",
        "contrast_text": "c", "source_soft": "s", "source_plain": "p"}


class Fixed:
    def __init__(self, extract, verdicts):
        self.extract, self.verdicts = extract, list(verdicts)

    def complete(self, messages, repeat):
        if messages[0]["content"] == pf.SYSTEM_EXTRACT:
            return {"text": self.extract}
        return {"text": self.verdicts.pop(0)}


def V(x):
    return json.dumps({"verdict": x})


class PerFact(unittest.TestCase):
    def test_parse_facts(self):
        self.assertEqual(pf.parse_facts('```json\n[{"fact":"a","kind":"harm"},"b"]\n```'),
                         [{"fact": "a", "kind": "harm"}, {"fact": "b", "kind": "other"}])
        self.assertIsNone(pf.parse_facts("[]"))
        self.assertIsNone(pf.parse_facts("nope"))

    def test_gate_insufficient_on_missing_harm(self):
        ex = json.dumps([{"fact": "cause", "kind": "responsible"}, {"fact": "injured", "kind": "harm"}])
        r = pf.check_pair(Fixed(ex, [V("STATED"), V("MISSING")]), PAIR)
        self.assertEqual((r["n_facts"], r["n_missing"], r["coverage"], r["gate"]), (2, 1, 0.5, "INSUFFICIENT"))

    def test_missing_other_fact_does_not_trip_gate(self):
        ex = json.dumps([{"fact": "cause", "kind": "responsible"}, {"fact": "injured", "kind": "harm"}])
        r = pf.check_pair(Fixed(ex, [V("MISSING"), V("STATED")]), PAIR)
        self.assertEqual((r["n_missing"], r["gate"]), (1, "SUFFICIENT"))

    def test_invalid_outputs(self):
        self.assertEqual(pf.check_pair(Fixed("junk", []), PAIR)["status"], "INVALID")
        ex = json.dumps([{"fact": "a", "kind": "harm"}])
        self.assertEqual(pf.check_pair(Fixed(ex, ["junk"]), PAIR)["error"], "step2_unparseable")

    def test_mock_backend_end_to_end(self):
        r = pf.check_pair(pf.MockBackend(), PAIR)
        self.assertEqual(r["status"], "VALID")
        self.assertEqual(r["n_facts"], 3)
        self.assertEqual(r["gate"], "INSUFFICIENT")

    def test_refuses_protected_dirs_and_live(self):
        for bad in (pf.ROOT / "data" / "mock_x", pf.ROOT / "harness" / "results_omission" / "mock",
                    pf.ROOT / "harness" / "results_new"):
            with self.assertRaises(ValueError):
                pf.check_out_dir(bad)
        with self.assertRaises(SystemExit):
            pf.main(["--model", "some-model"])  # non-mock without --live
        with self.assertRaises(SystemExit):
            pf.main(["--out-dir", str(pf.ROOT / "data" / "mock_x")])

    def test_main_writes_mock_output(self):
        with tempfile.TemporaryDirectory() as t:
            pairs = Path(t) / "pairs.jsonl"
            pairs.write_text(json.dumps(PAIR) + "\n")
            out = Path(t) / "out_mock"
            pf.main(["--pairs", str(pairs), "--out-dir", str(out)])
            row = json.loads((out / "per_fact_mock.jsonl").read_text())
            self.assertEqual(row["pair_id"], "T1")
            with self.assertRaises(SystemExit):
                pf.main(["--pairs", str(pairs), "--out-dir", str(out)])


class Compare(unittest.TestCase):
    def test_compare(self):
        om = [{"pair_id": p, "condition": "soft", "repeat": i,
               "answer": {"responsible": "STATED", "harmed": h, "extent": e}}
              for p, h, e in (("A", "STATED", "STATED"), ("A", "STATED", "STATED"),
                              ("B", "MISSING", "STATED"), ("B", "MISSING", "STATED"),
                              ("C", "STATED", "STATED"), ("C", "STATED", "STATED"))
              for i in (0,)] + [{"pair_id": "B", "condition": "plain", "answer": None}]
        one = compare_gates.one_question_gates(om)
        self.assertEqual(one, {"A": "SUFFICIENT", "B": "INSUFFICIENT", "C": "SUFFICIENT"})
        per = compare_gates.per_fact_gates([
            {"pair_id": "A", "status": "VALID", "gate": "INSUFFICIENT"},
            {"pair_id": "B", "status": "VALID", "gate": "INSUFFICIENT"},
            {"pair_id": "D", "status": "VALID", "gate": "SUFFICIENT"},
            {"pair_id": "C", "status": "INVALID", "gate": None}])
        res = compare_gates.compare(one, per)
        self.assertEqual((res["n"], res["agree"]), (2, 1))
        self.assertEqual(res["only_one"], ["C"])
        self.assertEqual(res["only_per"], ["D"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            om, pfp = Path(t) / "o.jsonl", Path(t) / "p.jsonl"
            om.write_text(json.dumps({"pair_id": "A", "condition": "soft",
                                      "answer": {"responsible": "STATED", "harmed": "STATED", "extent": "STATED"}}) + "\n")
            pfp.write_text(json.dumps({"pair_id": "A", "status": "VALID", "gate": "SUFFICIENT"}) + "\n")
            compare_gates.main(["--per-fact", str(pfp), "--omission", str(om)])


if __name__ == "__main__":
    unittest.main()
