"""Offline synthetic arm contracts."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness import synth, synth_to_pairs, run


SOURCE = "The company dumped 12 barrels of waste on 2026-11-01. Two workers were injured."


class SynthTests(unittest.TestCase):
    def make(self, move="euphemism"):
        return synth.generate({"pair_id": "p01", "text": SOURCE}, move,
                              synth.MockBackend(), synth.MockBackend())

    def test_each_arm_has_only_requested_moves(self):
        rewrites = set()
        for move in synth.MOVES:
            row = self.make(move)
            self.assertTrue(row["kept"], row["checker"])
            self.assertEqual(set(row["checker"]["applied_moves"]),
                             set(synth.move_components(move)))
            rewrites.add(row["rewrite_text"])
        self.assertEqual(len(rewrites), 4)
        self.assertIn("The company", self.make("euphemism")["rewrite_text"])
        self.assertNotIn("The company", self.make("agent_deletion")["rewrite_text"])

    def test_fact_loss_and_addition_rejected(self):
        row = self.make()
        for status in ("LOST", "ADDED"):
            check = copy.deepcopy(row["checker"])
            check["facts"][0]["status"] = status
            self.assertFalse(synth.assess(SOURCE, row["rewrite_text"], "euphemism", check)[0])

    def test_actor_loss_is_only_exception(self):
        row = self.make("agent_deletion")
        self.assertTrue(any(f.get("expected") for f in row["checker"]["facts"]))
        self.assertFalse(synth.assess(SOURCE, row["rewrite_text"], "euphemism", row["checker"])[0])
        check = copy.deepcopy(row["checker"])
        check["facts"].append({"field": "outcome", "source": "injury", "rewrite": None,
                               "status": "LOST", "expected": True})
        self.assertFalse(synth.assess(SOURCE, row["rewrite_text"], "agent_deletion", check)[0])

    def test_numbers_override_checker_approval(self):
        row = self.make()
        for old, new in (("12", "13"), ("2026-11-01", "2026-01-11"), ("Two", "Three")):
            changed = row["rewrite_text"].replace(old, new)
            self.assertFalse(synth.assess(SOURCE, changed, "euphemism", row["checker"])[0])

    def test_reasoning_and_list_scaffolding_are_rejected(self):
        row = self.make()
        for prefix in ("Wait, ", "Output: ", "- ", "**Rewrite:** ", "<think>reason</think>"):
            self.assertFalse(synth.assess(SOURCE, prefix + row["rewrite_text"],
                                         "euphemism", row["checker"])[0])

    def test_fail_closed_on_empty_incomplete_or_multiple_moves(self):
        row = self.make()
        for check in ({}, {"facts": []}, {**row["checker"], "facts": []},
                      {**row["checker"], "applied_moves": ["euphemism", "nominalization"]}):
            self.assertFalse(synth.assess(SOURCE, row["rewrite_text"], "euphemism", check)[0])
        self.assertFalse(synth.assess(SOURCE, SOURCE, "euphemism", row["checker"])[0])

    def test_malformed_checker_never_crashes_or_passes(self):
        row = self.make()
        for update in ({"applied_moves": [{}]}, {"facts": None}, {"facts": "KEPT"},
                       {"facts": [{"field": []}]}, {"source_facts": []}):
            with self.subTest(update=update):
                self.assertFalse(synth.assess(SOURCE, row["rewrite_text"], "euphemism",
                                              {**row["checker"], **update})[0])

    def test_generation_and_check_are_separate_calls(self):
        generator, checker = synth.MockBackend(), synth.MockBackend()
        with patch.object(generator, "complete", wraps=generator.complete) as gen_call, \
             patch.object(checker, "complete", wraps=checker.complete) as check_call:
            row = synth.generate({"pair_id": "p01", "text": SOURCE}, "euphemism", generator, checker)
        self.assertTrue(row["kept"])
        self.assertEqual(gen_call.call_count, 1)
        self.assertEqual(check_call.call_count, 1)
        check_input = json.loads(check_call.call_args.args[0][-1]["content"])
        self.assertEqual(check_input, {"source_text": SOURCE, "rewrite_text": row["rewrite_text"]})

    def test_failed_or_truncated_calls_are_rejected(self):
        for result in ({"text": "{}", "finish_reason": "length"},
                       {"text": "{}", "refusal": True}, {"text": "not json"},
                       {"text": '{"facts":[],"facts":[]}'}):
            with patch.object(synth.MockBackend, "complete", return_value=result):
                self.assertFalse(self.make()["kept"])

    def test_source_precedence(self):
        self.assertEqual(synth.source_text({"plain_neutral": "neutral", "plain_text": "plain", "text": "text"}), "neutral")
        self.assertEqual(synth.source_text({"plain_text": "plain"}), "plain")
        self.assertEqual(synth.source_text({"text": "text"}), "text")

    def test_unsupported_mock_is_rejected(self):
        row = synth.generate({"pair_id": "x", "text": "A bird sang."}, "euphemism",
                             synth.MockBackend(), synth.MockBackend())
        self.assertFalse(row["kept"])

    def test_cli_offline_default_and_explicit_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            pairs = path / "pairs.jsonl"
            pairs.write_text(json.dumps({"pair_id": "p01", "text": SOURCE}) + "\n")
            with patch.object(run.LiveBackend, "__init__", side_effect=AssertionError("network enabled")), \
                 patch("socket.socket", side_effect=AssertionError("network attempted")):
                for mode in ([], ["--dry-run"]):
                    output = path / ("dry.jsonl" if mode else "default.jsonl")
                    self.assertEqual(synth.main(["--pairs", str(pairs), "--output", str(output)] + mode), 0)
                    rows = [json.loads(line) for line in output.read_text().splitlines()]
                    self.assertEqual({r["move"] for r in rows}, set(synth.MOVES))
                    self.assertTrue(all(r["backend"] == "mock" for r in rows))

    def test_live_uses_distinct_checker_model_and_redacts_evidence(self):
        models = []
        def post(url, headers, json, timeout):
            models.append(json["model"])
            result = synth.MockBackend().complete(json["messages"], 0)
            body = {"choices": [{"message": {"content": result["text"]}, "finish_reason": "stop"}],
                    "test_marker": "test-credential-value"}
            return SimpleNamespace(status_code=200, json=lambda: body)
        fake_requests = SimpleNamespace(post=post, RequestException=ConnectionError)
        with tempfile.TemporaryDirectory() as tmp:
            pairs, output = Path(tmp) / "pairs.jsonl", Path(tmp) / "synthetic.jsonl"
            pairs.write_text(json.dumps({"pair_id": "p01", "text": SOURCE}) + "\n")
            with patch.dict(os.environ, {"BASE_URL": "https://example.invalid/v1",
                                         "API_KEY": "test-credential-value", "MODEL": "generator",
                                         "MIN_INTERVAL": "0"}), \
                 patch.dict("sys.modules", {"requests": fake_requests}), \
                 patch("socket.socket", side_effect=AssertionError("network attempted")):
                synth.main(["--live", "--pairs", str(pairs), "--output", str(output),
                            "--move", "euphemism", "--checker-model", "checker"])
            record = json.loads(output.read_text())
            self.assertTrue(record["kept"])
            self.assertEqual(models, ["generator", "checker"])
            self.assertEqual(record["checker_model"], "checker")
            self.assertNotIn("test-credential-value", output.read_text())

    def test_generation_keeps_malformed_checker_for_inspection(self):
        checker = synth.MockBackend()
        with patch.object(checker, "complete", return_value={"text": '{"facts":null}'}):
            row = synth.generate({"pair_id": "p01", "text": SOURCE}, "euphemism",
                                 synth.MockBackend(), checker)
        self.assertFalse(row["kept"])
        self.assertEqual(row["checker"]["call"]["raw_text"], '{"facts":null}')

    def test_converter_filters_and_matches_runner_schema(self):
        original = run.read_pairs(Path(__file__).resolve().parents[1] / "data/pairs_example.jsonl")[0]
        rows = [synth.generate(original, move, synth.MockBackend(), synth.MockBackend())
                for move in synth.MOVES]
        rows[1]["kept"] = False
        converted = synth_to_pairs.convert(rows, [original])
        self.assertEqual(len(converted), 3)
        for pair in converted:
            self.assertEqual(pair["contrast_text"], original["contrast_text"])
            self.assertEqual(pair["plain_text"], original["plain_text"])
            self.assertTrue(pair["pair_id"].startswith(original["pair_id"] + "__"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pairs.jsonl"
            path.write_text("".join(json.dumps(p) + "\n" for p in converted))
            self.assertEqual(run.read_pairs(path), converted)

    def test_converter_does_not_invent_contrast_or_accept_stale_sources(self):
        row = self.make()
        with self.assertRaisesRegex(ValueError, "contrast_text"):
            synth_to_pairs.convert([row], [{"pair_id": "p01", "text": SOURCE}])
        with self.assertRaisesRegex(ValueError, "does not match"):
            synth_to_pairs.convert([row], [{"pair_id": "p01", "text": "Different incident"}])


if __name__ == "__main__":
    unittest.main()
