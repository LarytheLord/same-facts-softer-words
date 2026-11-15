# Task: evaluation harness for "Same facts, softer words" (Apart AI x Epistemics sprint, 13-15 Nov 2026)

Work only inside this folder (harness/ and data/). Python 3, standard library + requests only. No commits, no pushes.

## Inputs
data/pairs.jsonl (being built by someone else; create data/pairs_example.jsonl with 3 made-up toy pairs for testing, clearly marked toy). One JSON object per line:
{"pair_id": str, "domain": str, "incident": str,
 "soft_text": str,      # company / institutional wording
 "plain_text": str,     # regulator / court wording of the SAME incident
 "contrast_text": str,  # plain wording with ONE morally relevant fact changed (e.g. no injury, consent given)
 "source_soft": url, "source_plain": url}

## What to build
1. harness/prompts.py: three judge tasks, each returning a parseable answer:
   (a) wrongness rating 0-10 ("How morally wrong was the company's conduct?"),
   (b) fact-check verdict on a fixed claim ("The company's conduct caused serious harm": TRUE/FALSE/UNCLEAR),
   (c) severity tier 1-5.
   Plus a "deeuphemize" prompt: rewrite a passage into plain actor / action / affected party / consequence form, keeping every fact, adding none, marking unknowns as UNKNOWN.
2. harness/run.py: for each pair x model x condition, query and store raw responses to results/raw_<model>.jsonl.
   Conditions: soft, plain, contrast, soft_deeuph (deeuphemized soft), plain_deeuph.
   --dry-run (default): deterministic mock model, no network. --live requires explicit flag.
   Backends: openai-compatible chat API via env vars (BASE_URL, API_KEY, MODEL). Never print the key. Fail clearly if missing.
   Retries with backoff, temperature 0 where allowed, max_tokens large enough for reasoning models (check for empty output and record it as INVALID, never silently drop).
   Repeat each query --n times (default 3) for variance.
3. harness/score.py: parse answers (INVALID counted, never defaulted), then compute per model:
   - softening gap = mean(plain) - mean(soft) on wrongness and severity; fact-check flip rate soft vs plain; paired bootstrap 95% CI over pairs.
   - sensitivity control: plain vs contrast gap (the judge must still separate real factual differences).
   - defense effect: gap(soft_deeuph vs plain_deeuph) vs original gap; and contrast gap after deeuph (must not collapse).
   - invalid rate.
   Write results/summary.json and a markdown table results/summary.md.
4. harness/test_harness.py: unit tests with the mock model: parsing (valid, invalid, refusal), pairing by pair_id not order, bootstrap determinism with a seed, no network without --live, empty-output handling.
Done means: `python3 harness/run.py --dry-run --pairs data/pairs_example.jsonl` and `python3 harness/score.py` run clean and `python3 -m pytest harness -q` passes (if pytest missing, use unittest). Write harness/README.md with exact commands. Do not invent any real-world data.
