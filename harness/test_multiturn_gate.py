"""Offline tests for harness/multiturn_gate.py."""
import json
import tempfile
import unittest
from pathlib import Path

from harness import multiturn_gate as g

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "data" / "examples" / "multiturn_synthetic.jsonl"


class CountingBackend(g.MockGateBackend):
    def __init__(self):
        self.calls = []

    def complete(self, messages, repeat):
        self.calls.append(messages[0]["content"].split(".")[0])
        return super().complete(messages, repeat)


class GateTests(unittest.TestCase):
    def test_example_file(self):
        convs = g.read_conversations(EX)
        self.assertEqual(len(convs), 5)
        text = EX.read_text(encoding="utf-8")
        text.encode("ascii")
        self.assertNotIn(chr(0x2014), text)
        recs = {r["id"]: r for r in (g.evaluate(g.MockGateBackend(), c) for c in convs)}
        self.assertEqual({k: v["verdict"] for k, v in recs.items()},
                         {"mt-01": "SCORED", "mt-02": "SCORED", "mt-03": "INSUFFICIENT",
                          "mt-04": "INSUFFICIENT", "mt-05": "SCORED"})

    def test_score_not_requested_when_gate_fails(self):
        b = CountingBackend()
        conv = [c for c in g.read_conversations(EX) if c["id"] == "mt-04"][0]
        rec = g.evaluate(b, conv)
        self.assertEqual(rec["verdict"], "INSUFFICIENT")
        self.assertIsNone(rec["score"])
        self.assertEqual(b.calls, ["Gate"])

    def test_missing_fact_fails_gate_even_if_committed(self):
        rec = g.evaluate(g.MockGateBackend(), [c for c in g.read_conversations(EX) if c["id"] == "mt-04"][0])
        self.assertTrue(rec["gate"]["commits"])
        self.assertFalse(rec["gate"]["passed"])

    def test_parse_gate(self):
        ok = json.dumps({"commits": True, "facts": {"a": "STATED"}})
        self.assertEqual(g.parse_gate(ok, ["a"]), (True, {"a": "STATED"}))
        self.assertEqual(g.parse_gate(ok, ["a", "b"])[1]["b"], "MISSING")
        self.assertIsNone(g.parse_gate("nope", ["a"]))
        self.assertIsNone(g.parse_gate(json.dumps({"commits": "yes", "facts": {}}), []))
        self.assertIsNone(g.parse_gate(json.dumps({"commits": True, "facts": {"a": "MAYBE"}}), ["a"]))

    def test_parse_score(self):
        self.assertEqual(g.parse_score('{"answer": 7}'), 7)
        for bad in ("x", '{"answer": 11}', '{"answer": true}', "{}"):
            self.assertIsNone(g.parse_score(bad))

    def test_input_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.jsonl"
            p.write_text(json.dumps({"id": "x", "turns": [{"role": "user", "content": "hi"}],
                                     "reference_facts": ["f"]}) + "\n")
            with self.assertRaises(ValueError):
                g.read_conversations(p)


class CliTests(unittest.TestCase):
    def test_live_refused(self):
        for extra in (["--live"], ["--live", "--allow-live"]):
            with self.assertRaises(SystemExit) as cm:
                g.main(["--input", str(EX)] + extra)
            self.assertEqual(cm.exception.code, 2)

    def test_output_guards(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in (Path(d) / "out.jsonl", ROOT / "harness" / "results_x_mock" / "o.jsonl"):
                with self.assertRaises(SystemExit):
                    g.main(["--input", str(EX), "--out", str(bad)])
            good = Path(d) / "mock_out.jsonl"
            g.main(["--input", str(EX), "--out", str(good)])
            self.assertEqual(len(good.read_text().splitlines()), 5)
            with self.assertRaises(SystemExit):
                g.main(["--input", str(EX), "--out", str(good)])


if __name__ == "__main__":
    unittest.main()
