"""Offline contract tests; runnable with pytest or unittest."""
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import run, score
from harness.prompts import parse_answer

ROOT = Path(__file__).resolve().parents[1]


def row(pair, condition, value, repeat=0, task="wrongness"):
    return {"pair_id": pair, "model": "mock", "condition": condition,
            "repeat": repeat, "task": task, "stage": "judge",
            "status": "VALID", "raw_text": json.dumps({"answer": value})}


class ParsingTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_answer("wrongness", '{"answer": 7.5}'), 7.5)
        self.assertEqual(parse_answer("severity", '```json\n{"answer": 4}\n```'), 4)
        self.assertEqual(parse_answer("fact_check", '{"answer": "UNCLEAR"}'), "UNCLEAR")
        self.assertEqual(parse_answer("wrongness", "8"), 8)

    def test_invalid_and_refusal(self):
        for text in ("", "I cannot judge this.", '{"answer": true}',
                     '{"answer": 11}', '{"answer": NaN}',
                     '{"answer": 4, "refusal": "cannot answer"}',
                     'First 3 then 8', '{"answer": 2, "answer": 7}'):
            with self.subTest(text=text):
                self.assertIsNone(parse_answer("wrongness", text))
        self.assertIsNone(parse_answer("severity", '{"answer": 2.5}'))
        self.assertIsNone(parse_answer("fact_check", '{"answer": "probably"}'))

    def test_reasoning_is_not_answer(self):
        self.assertIsNone(parse_answer("wrongness", "<think>8</think>"))
        self.assertEqual(parse_answer("wrongness", '<think>2</think> {"answer":8}'), 8)


class ScoringTests(unittest.TestCase):
    def test_pair_id_not_order(self):
        rows = [row("b", "soft", 1), row("a", "plain", 8),
                row("a", "soft", 2), row("b", "plain", 5)]
        a = score.summarize(rows, seed=3, draws=100)
        random.Random(10).shuffle(rows)
        self.assertEqual(a, score.summarize(rows, seed=3, draws=100))
        m = a["mock"]["tasks"]["wrongness"]["softening_gap"]
        self.assertEqual(m["estimate"], 5)
        self.assertEqual(m["n_pairs"], 2)

    def test_bootstrap_determinism(self):
        self.assertEqual(score.bootstrap([1, 3, 9], seed=8, draws=200),
                         score.bootstrap([1, 3, 9], seed=8, draws=200))
        self.assertEqual(score.bootstrap([], seed=8)["estimate"], None)
        self.assertEqual(score.bootstrap([4], seed=8)["ci95"], [4, 4])

    def test_invalid_counted_not_zero(self):
        bad = row("a", "soft", 5)
        bad["raw_text"] = "refused"
        report = score.summarize([bad, row("a", "plain", 8)])['mock']
        self.assertEqual(report["invalid_rate"], 0.5)
        self.assertIsNone(report["tasks"]["wrongness"]["softening_gap"]["estimate"])

    def test_repeats_are_not_independent_pairs(self):
        rows = [row("a", c, v, r) for c, v in (("plain", 8), ("soft", 3))
                for r in range(3)]
        m = score.summarize(rows)["mock"]["tasks"]["wrongness"]["softening_gap"]
        self.assertEqual(m["n_pairs"], 1)
        self.assertEqual(m["estimate"], 5)

    def test_repeat_matched_flip_rate(self):
        rows = [row("a", "soft", "TRUE", 0, "fact_check"),
                row("a", "plain", "FALSE", 0, "fact_check"),
                row("a", "soft", "FALSE", 1, "fact_check"),
                row("a", "plain", "FALSE", 1, "fact_check")]
        m = score.summarize(rows)["mock"]["tasks"]["fact_check"]["soft_plain_flip_rate"]
        self.assertEqual(m["estimate"], 0.5)

    def test_duplicate_query_rejected(self):
        with self.assertRaises(ValueError):
            score.summarize([row("a", "soft", 2)] * 2)


class RunnerTests(unittest.TestCase):
    def test_no_network_without_live_and_complete_matrix(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "harness") as temp:
            with patch.object(run, "LiveBackend", side_effect=AssertionError("network")), \
                    patch("socket.socket", side_effect=AssertionError("network")):
                self.assertEqual(run.main(["--pairs", str(ROOT / "data/pairs_example.jsonl"),
                                           "--results-dir", temp]), 0)
            records = [json.loads(line) for line in
                       (Path(temp) / "raw_mock.jsonl").read_text().splitlines()]
            self.assertEqual(len(records), 189)
            self.assertTrue(all(r["status"] == "VALID" for r in records))
            self.assertEqual(len({r["run_id"] for r in records}), 1)
            self.assertIn("contrast_deeuph", {r["condition"] for r in records})

    def test_empty_output_recorded(self):
        class Empty:
            def complete(self, messages, repeat):
                return {"text": "", "response": {"choices": []}}
        result = run.query(Empty(), [], "wrongness", 0)
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["error"], "empty_output")
        self.assertEqual(result["raw_text"], "")

    def test_missing_live_config(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "BASE_URL.*API_KEY.*MODEL"):
                run.LiveBackend(None)

    def test_invalid_rewrite_propagates(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "harness") as temp:
            with patch.object(run.MockBackend, "complete", return_value={"text": "", "response": {}}):
                run.main(["--pairs", str(ROOT / "data/pairs_example.jsonl"),
                          "--results-dir", temp, "--n", "1"])
            records = [json.loads(s) for s in (Path(temp) / "raw_mock.jsonl").read_text().splitlines()]
            blocked = [r for r in records if r.get("error") == "invalid_rewrite"]
            self.assertEqual(len(blocked), 27)
            self.assertTrue(all(r['status'] == 'INVALID' for r in records))


class BackendTests(unittest.TestCase):
    def response(self, status, body):
        from types import SimpleNamespace
        return SimpleNamespace(status_code=status, json=lambda: body, text=json.dumps(body))

    def backend(self, **kwargs):
        with patch.dict("os.environ", {"BASE_URL": "https://example.invalid/v1",
                                       "API_KEY": "test-secret-only", "MODEL": "test-model"}):
            return run.LiveBackend(None, **kwargs)

    def requests_module(self, post):
        from types import SimpleNamespace
        return SimpleNamespace(post=post, RequestException=ConnectionError)

    def test_capability_negotiation(self):
        from unittest.mock import Mock
        post = Mock(side_effect=[
            self.response(400, {"error": "temperature unsupported; only default allowed"}),
            self.response(400, {"error": "use max_completion_tokens instead of max_tokens"}),
            self.response(200, {"choices": [{"message": {"content": '{"answer": 8}'},
                                             "finish_reason": "stop"}]})])
        with patch.dict("sys.modules", {"requests": self.requests_module(post)}):
            result = run.query(self.backend(), [], "wrongness", 0)
        self.assertEqual(result["status"], "VALID")
        payload = post.call_args.kwargs["json"]
        self.assertNotIn("temperature", payload)
        self.assertEqual(payload["max_completion_tokens"], 8192)
        self.assertEqual(len(result["attempts"]), 3)

    def test_retries_with_backoff_and_redaction(self):
        from unittest.mock import Mock
        post = Mock(return_value=self.response(429, {"error": "test-secret-only"}))
        with patch.dict("sys.modules", {"requests": self.requests_module(post)}):
            with patch.object(run.time, "sleep") as sleep:
                result = run.query(self.backend(retries=2), [], "wrongness", 0)
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(post.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])
        self.assertNotIn("test-secret-only", json.dumps(result))

    def test_empty_truncated_refusal_and_malformed_responses(self):
        from unittest.mock import Mock
        cases = [({"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}, "empty_output"),
                 ({"choices": [{"message": {"content": '{"answer": 8}'}, "finish_reason": "length"}]}, "finish_length"),
                 ({"choices": [{"message": {"content": '{"answer": 8}', "refusal": "no"}}]}, "refusal"),
                 ({"choices": []}, "malformed_api_response")]
        for body, error in cases:
            with self.subTest(error=error):
                post = Mock(return_value=self.response(200, body))
                with patch.dict("sys.modules", {"requests": self.requests_module(post)}):
                    result = run.query(self.backend(), [], "wrongness", 0)
                self.assertEqual(result["status"], "INVALID")
                self.assertEqual(result["error"], error)


class DefenseTests(unittest.TestCase):
    def test_defense_cohort_and_sensitivity(self):
        rows = [row("a", c, v) for c, v in (("plain", 8), ("soft", 4),
                ("plain_deeuph", 8), ("soft_deeuph", 8),
                ("contrast", 2), ("contrast_deeuph", 2))]
        rows += [row("b", "plain", 9), row("b", "soft", 1)]
        r = score.summarize(rows)["mock"]["tasks"]["wrongness"]
        self.assertEqual(r["softening_gap"]["estimate"], 6)
        comparison = r["defense_comparison"]
        self.assertEqual(comparison["original_common_cohort"]["estimate"], 4)
        self.assertEqual(comparison["reduction"]["estimate"], 4)
        self.assertEqual(comparison["reduction"]["n_pairs"], 1)
        self.assertEqual(r["defended_sensitivity_gap"]["estimate"], 6)

    def test_numeric_repeat_alignment(self):
        rows = [row("a", "plain", 10, 0), row("a", "plain", 6, 1),
                row("a", "soft", 4, 1)]
        gap = score.summarize(rows)["mock"]["tasks"]["wrongness"]["softening_gap"]
        self.assertEqual(gap["estimate"], 2)
        self.assertEqual(gap["n_matched_repeats"], 1)

    def test_all_invalid_has_null_estimates(self):
        bad = row("a", "soft", 8)
        bad.update(status="INVALID", error="empty_output", raw_text="")
        report = score.summarize([bad])["mock"]
        self.assertEqual(report["invalid_rate"], 1)
        self.assertIsNone(report["tasks"]["wrongness"]["softening_gap"]["ci95"])

    def test_partial_manifest_rejected(self):
        one = row("a", "soft", 3)
        one.update(n=1, pair_count=1)
        with self.assertRaisesRegex(ValueError, "Incomplete raw run"):
            score.summarize([one])

    def test_invalid_status_cannot_be_reparsed_into_success(self):
        bad = row("a", "soft", 8)
        bad.update(status="INVALID", error="finish_length")
        report = score.summarize([bad])["mock"]
        self.assertEqual(report["invalid_count"], 1)


if __name__ == "__main__":
    unittest.main()
