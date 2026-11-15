# Same facts, softer words

An offline-first evaluation harness for wording sensitivity. It judges each passage
independently on wrongness (0-10), a fixed serious-harm claim
(TRUE/FALSE/UNCLEAR), and severity (1-5). It also tests structured plain-language
rewrites and a factual sensitivity control.

All commands below run from the sprint folder. Outputs live in `harness/results/`,
so every generated file stays within `harness/` or `data/`.

## Run the toy check

Python 3 is sufficient for the offline path. No packages or credentials are needed.

```sh
python3 harness/run.py --dry-run --pairs data/pairs_example.jsonl
python3 harness/score.py
python3 -m pytest harness -q
```

If pytest is unavailable, run the original contract and synthetic tests with the
standard library. The resume tests require pytest:

```sh
python3 -m unittest harness.test_harness harness.test_synth -q
```

The three example pairs are explicitly fictional toys. Their `.invalid` source URLs
are placeholders, not evidence. The mock is a deterministic text heuristic with
small deterministic numeric variation between repeats. Its results demonstrate
pipeline behavior only, including a deliberately simulated wording effect. They
are not measurements of any real model or incident.

The default is offline even if API credentials are present. `--dry-run` and
`--live` are mutually exclusive. Existing raw files are protected. To rerun:

```sh
python3 harness/run.py --dry-run --pairs data/pairs_example.jsonl --overwrite
python3 harness/score.py --seed 42 --bootstrap 2000
```

To continue an interrupted run, repeat its command with `--resume`:

```sh
python3 harness/run.py --dry-run --pairs data/pairs_example.jsonl --resume
python3 harness/score.py
```

Resume appends missing queries to the same `raw_<model>.jsonl` file and preserves
the original run ID. A query is identified by `(pair_id, condition, repeat, task,
stage)`. Stored VALID records are skipped. Stored INVALID records are also kept
unless you pass both `--resume --retry-invalid`. VALID rewrite answers are rendered
with `render_rewrite` and reused for the remaining judge tasks. An INVALID rewrite
still produces `invalid_rewrite` judge records unless its retry succeeds.

Use the same pairs file contents, model IDs, `--n`, and results directory. Resume
checks the input hash, model, backend, prompt version, repeat count and pair count
before changing any files. Filenames do not include a new timestamp or run ID, so
the same model and pairs hash keep the same target. Different datasets need separate
results directories. `--resume` also works when the target file does not yet exist;
it cannot be combined with `--overwrite`. `--retry-invalid` requires `--resume`.
Live resumes still require an explicit `--live`.

Retried records replace the older record for that key. Each replacement writes a
temporary file in the same directory, flushes it to disk, then uses `os.replace`.
Existing duplicate keys are reduced to their newest record on resume. A truncated
final JSON line without a newline is discarded and its query runs again; malformed
complete lines are rejected. The previous file survives a failed atomic replacement.
Free enough disk space for the raw file and its temporary replacement before retrying.

With the default conditions, finishing a resume produces the full grid required by
the scorer, including INVALID records. If you used `--conditions` to run a subset,
resume without that option to fill the remaining conditions before scoring.

## Real data and explicit live mode

Someone else supplies `data/pairs.jsonl`. The harness never creates or modifies it.
Each nonblank line must contain nonempty string fields:

```json
{"pair_id":"unique-id","domain":"domain","incident":"incident description","soft_text":"institutional wording","plain_text":"plain wording of the SAME facts","contrast_text":"plain wording with ONE morally relevant fact changed","source_soft":"source URL","source_plain":"source URL"}
```

Duplicate pair IDs are rejected. Source URLs and incident descriptions are stored
as provenance but are not shown to the judge. Only the passage is judged. The
harness validates input structure; it does not establish that a real pair has the
same facts, a contrast changes exactly one fact, or a source supports its passage.
Review these properties before using the data for research.

For live calls, install `requests` in your Python environment. Set `BASE_URL`,
`API_KEY`, and `MODEL` in the environment without putting credentials in command
history or source files. `BASE_URL` is an API base URL such as
`https://your-provider.example/v1`, or a full chat completions endpoint.
No live request is made by the toy checks or test suite.

```sh
python3 harness/run.py --live --pairs data/pairs.jsonl --n 3 --results-dir harness/results_live
python3 harness/score.py --results-dir harness/results_live
```

`--models model-a model-b` runs multiple model IDs against the configured endpoint.
Without it, live mode uses `MODEL`; dry runs use `mock`. Custom dry-run labels get a
`mock:` prefix so they cannot be mistaken for actual model measurements. Filenames
escape model IDs and add a hash when needed. Use separate results directories for
separate experiments. The scorer rejects mixed runs for a model and incomplete
query grids. It scores all `raw_*.jsonl` files in the selected directory.

Calls start with temperature 0 and an output budget of 8192 tokens. On a server
error explicitly rejecting temperature, the backend retries without that parameter.
If the server requests `max_completion_tokens`, it switches from `max_tokens`.
You can select this explicitly with `--token-param max_completion_tokens`.
`--max-tokens` must be at least 2048; raise it for models that exhaust their reasoning
budget. A 200 response with empty content, a refusal, malformed content, a length
stop, or a content-filter stop is INVALID. Hidden reasoning is never used as an
answer. A parseable fragment from a truncated response is still INVALID.

Transient transport errors and HTTP 408/409/429/5xx responses get up to `--retries 3`
retries, with exponential delays of 1, 2, and 4 seconds. Capability negotiation is
separate and bounded. Other HTTP failures are recorded immediately. `--timeout 120`
sets the per-request timeout in seconds. Error logs retain response evidence but
redact exact API key matches; headers and keys are never printed or persisted.

## Conditions and records

Every pair, model, and repeat has six judge conditions:

- `soft`, `plain`, `contrast`: input passages.
- `soft_deeuph`, `plain_deeuph`: independently rewritten soft and plain passages.
- `contrast_deeuph`: independently rewritten contrast, needed to check whether the
  defense retains sensitivity to a real factual change.

There are three rewrite calls and eighteen judge calls per pair per repeat.
The default three-pair, three-repeat toy run writes 189 records: 27 rewrite and
162 judge records. A rewrite is reused across the three judge tasks within that
pair and repeat, but regenerated for each repeat. Each call has fresh messages;
no chat history or other passages are shared with the judge.

`raw_<model>.jsonl` records include run ID, timestamp, input hash, full pair
provenance, prompt version, messages, repeat index, raw response, attempts, parsed
answer, finish reason, and VALID/INVALID status. Failed rewrite dependencies produce
explicit INVALID judge records with `invalid_rewrite`; no judge API call is made
for those slots. Writes flush after each record. Interrupted files remain available
for inspection; scoring rejects their incomplete grid until `--resume` fills it.

## Read the scores

`summary.json` contains per-model task metrics, denominators, per-condition invalid
counts, numeric repeat standard deviations, and categorical verdict counts.
`summary.md` presents estimates, 95% intervals, and valid pair counts.

Numeric gaps are `mean(plain - soft)` and `mean(plain - contrast)`. Each difference
uses valid repeat indices common to both conditions within a `pair_id`. Differences
are averaged within the pair first, then equally across pairs. Thus repeated
calls are not treated as additional independent incidents. Condition means are
reported separately using all valid observations; with missing outputs their
difference can differ from the matched gap.

Fact-check flip rates are the fraction of matched repeat indices whose verdicts
differ, averaged equally across pairs. UNCLEAR is a valid category. This is a
categorical disagreement measure, not factual accuracy. No ground-truth verdicts
are inferred from the passages.

Defense comparisons use the same pairs AND repeat indices across all four relevant
conditions. The reduction is `(plain - soft) - (plain_deeuph - soft_deeuph)` for
numeric tasks, or original minus defended flip rate for fact checking. Positive
reduction means a smaller signed wording gap. Original and defended sensitivity
comparisons similarly share a common cohort. Both unrestricted pairwise estimates
and common-cohort comparisons are in JSON; the table uses common-cohort estimates.

Intervals use a seeded percentile bootstrap, resampling entire pairs with
replacement (default 2000 draws, seed 42). Estimates without valid pairs are null
in JSON and NA in the table. INVALID responses are counted, never converted to
zero or UNCLEAR. Judge invalid rate includes failed rewrite dependencies; rewrite
invalid rate is reported separately. Valid-pair estimates may still be biased by
nonrandom missingness, so inspect the invalid counts alongside each effect.

A positive sensitivity gap is expected only if the factual change was designed to
reduce wrongdoing. The schema supplies no direction labels or acceptance threshold,
so the harness reports signed gaps and their intervals without declaring that a
judge passed. Inspect whether defended sensitivity survives; a defense that makes
all passages equivalent has failed this control even if its wording gap is zero.

No live model was evaluated by the offline checks. Structural rewrite validation
cannot establish that all facts survived. Human review is needed for rewrite
fidelity. The same configured model rewrites and judges, which may introduce
correlated errors. Three toy pairs and deterministic repeats cannot establish
statistical power or generalization. Bootstrap intervals reflect sampling over the
supplied pairs, not uncertainty from pair selection or factual annotation.

## Synthetic per-move arms

Generate one arm per move, with a separate fact-checking call for each rewrite:

```sh
python3 harness/synth.py --dry-run --pairs data/pairs_example.jsonl
python3 harness/synth_to_pairs.py --pairs data/pairs_example.jsonl
python3 -m pytest harness/test_synth.py -q
python3 harness/run.py --dry-run --pairs data/synthetic_pairs.jsonl --results-dir harness/results_synthetic
python3 harness/score.py --results-dir harness/results_synthetic
```

The generator defaults to `data/pairs.jsonl`, reads `plain_neutral` before
`plain_text` before `text`, and requires unique `pair_id` values. A minimal source
is `{"pair_id":"p01","text":"The company dumped waste."}`. Conversion also needs
`contrast_text` in the source; it never invents a factual control. Other runner
metadata is retained, with local provenance labels where metadata is absent.

`--move euphemism`, `--move nominalization`, and `--move agent_deletion` generate
single-move arms. `--move all_three` generates the combined arm. `--move all`
(the default) generates all four arms separately. Euphemism retains an explicit
actor and verbal action; nominalization retains the actor and harm meaning;
agent deletion hides the acting agent alone. The combined arm applies all three.

`data/synthetic.jsonl` records source and rewrite text, move, acceptance (`kept`),
model IDs, generation response, and checker output including extracted facts,
comparisons, observed moves, and raw response evidence. Rejected candidates remain
in this file for inspection and never become runner pairs. The checker inventories
cover actor, action, affected parties, numbers, and outcomes, including qualifiers,
negations, consent and uncertainty. Every atom must be accounted for. Any ADDED or
LOST fact rejects the candidate except an actor loss when agent deletion is
requested and no actor remains. These losses get `expected: true`. Numeric tokens,
number words and month names also undergo an independent ordered equality check.
Malformed, refused, truncated, unchanged, or unintended-move outputs are rejected.

The converter rechecks accepted rows and preserves each original `contrast_text`.
IDs become `p01__euphemism`, for example. The original source text is the same
`plain_text` across all arms, and synthetic text becomes `soft_text`. The runner
and scorer need no changes. For separate move estimates, select suffixes before
running the existing harness, for example:

```sh
python3 -c 'import json; from pathlib import Path; rows=[json.loads(s) for s in Path("data/synthetic_pairs.jsonl").read_text().splitlines() if s.strip()]; Path("data/synthetic_euphemism.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows if r["pair_id"].endswith("__euphemism")))'
python3 harness/run.py --dry-run --pairs data/synthetic_euphemism.jsonl --results-dir harness/results_euphemism
python3 harness/score.py --results-dir harness/results_euphemism
```

Do not pool arms as independent incidents for inference: they share source facts.
The scorer does not automatically group suffixes or model that dependence.

Both commands protect existing outputs; use `--overwrite` or a different
`--output` for reruns. The default backend is offline regardless of credentials.
The toy mock supports a small set of company/employer action templates, including
the example pairs, and rejects unsupported input. It is a pipeline fixture, not a
fact checker or evidence of a wording effect.

Live generation requires `requests` and the same `BASE_URL`, `API_KEY`, and `MODEL`
environment settings as the runner. Use a different checker model when available:

```sh
python3 harness/synth.py --live --pairs data/pairs.jsonl --checker-model another-model --output data/synthetic_live.jsonl
python3 harness/synth_to_pairs.py --pairs data/pairs.jsonl --synthetic data/synthetic_live.jsonl --output data/synthetic_live_pairs.jsonl
```

Each arm uses one generation call and a separate checker call with fresh messages.
Without `--checker-model`, the checker uses `MODEL` in a separate call. Both models
use the same configured API endpoint. Responses and request attempts are retained;
API key values are redacted. No live call is made by the commands marked dry-run
or by the tests. Model fact extraction and move classification can be wrong even
when the numeric check passes. Human review is needed before attributing a judge
shift to a single move. These checks do not establish causal isolation by themselves.
