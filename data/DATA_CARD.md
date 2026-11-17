# Data card: real incident pairs and synthetic sources

Covers `data/pairs.jsonl` (11 real pairs) and `data/synth_sources.jsonl` (30 regulator descriptions for the synthetic arm). Other files in `data/` are out of scope for this card. The data files were not changed when this card was written.

## What the files are

- `data/pairs.jsonl`: 11 incidents. Each has a statement by the company and a US regulator's published account of the same incident. Used by `harness/run.py`, `harness/score.py` and `harness/judge_check.py`.
- `data/synth_sources.jsonl`: 30 regulator incident descriptions (no company side). The synthetic arm rewrites each one move by move (euphemism, nominalization, agent deletion, all three). The rewrites live in other files, not here.

## Fields: `pairs.jsonl`

One JSON object per line.

| field | meaning |
|---|---|
| `pair_id` | A01-A03 and B01-B08 (two collection batches; see `PROVENANCE_A.md`, `PROVENANCE_B.md`) |
| `domain` | chemical, workplace, data, financial, consumer, animal |
| `incident` | short label (present on the A rows only) |
| `company` | real company name, kept for the maintainers. Never sent to a judge |
| `soft_text` | company statement, short excerpt, company name replaced with "Company A" where it appeared |
| `plain_text` | regulator account used as the model input: company name replaced with "Company A", verdict and penalty language removed |
| `plain_neutral` | identical to `plain_text` in all 11 rows (checked) |
| `plain_original` | regulator text before verdict and penalty removal (company name already replaced). Not shown to judges. Present in all 11 rows; it differs from `plain_text` in 10 and is identical in B07 |
| `contrast_text` | `plain_text` with one morally relevant fact changed (for example an injury that did not occur). Constructed by the authors, not a quote |
| `facts` | five-item fact checklist from the regulator record (see below) |
| `fact_coverage_soft` | soft score (partial credit per checklist item) for how much of the five items `soft_text` states; values in this file run 0.1 to 0.4 |
| `famous` | true for 7 of 11 well-known cases |
| `tier` | alignment-quality label assigned before scoring (see below) |
| `source_soft`, `source_plain` | URL of the company statement and of the regulator record |
| `date` | month of the incident |
| `retrieved_at` | UTC time the sources were fetched (all 2026-11-13) |
| `method`, `notes` | how the text was obtained and trimmed; alignment remarks |
| `label` | A01-A03 only: "fact from record (quotes); alignment judgement is lead for review" |
| `sha256_soft`, `sha256_plain` | B01-B08 only: hashes of the stored texts |

Rows A01-A03 have `label` and no hashes; rows B01-B08 have hashes and no `label`. The schema is not uniform.

## Fields: `synth_sources.jsonl`

`pair_id` (R01-R30), `domain` (workplace 12, consumer 10, chemical 8), `plain_text`, `plain_neutral`, `contrast_text`, `famous` (4 true, 26 false), `source_url`. `plain_neutral` is the regulator text; `contrast_text` is the constructed one-fact change.

## How pairs were selected

We searched public enforcement records for incidents where the company had issued its own statement (press release, filing, or a statement quoted in news coverage) and the regulator had published a factual account. Eleven pairs survived a manual fact-alignment pass (both texts describe the same incident). Selection was by hand and opportunistic, not a random sample. Many company statements we found were missing or defensive, and few were euphemistic, so the corpus leans toward cases where a usable statement was findable.

Regulators by pair: OSHA (A01, A03), CSB (A02), FTC (B01, B06, B07), SEC (B02), CPSC (B03, B08), EPA (B04), FDA (B05). Company statements are not always from the company's own site: several are news articles quoting the company (see licence section).

Texts were fetched on 2026-11-13 and trimmed by hand with model assistance (`method` field). Trimming kept quoted sentences and dropped others; edits are described in `notes`. Dates differ between the two texts (a company statement is often hours after the incident, the regulator record months or years later).

## Anonymization

- Company names are replaced with "Company A" in `plain_text`, `plain_original`, `contrast_text` and, where the name appears, in `soft_text`.
- Regulator verdict and penalty language ("found liable", "fined", proposed penalties) is removed from `plain_text`; the original is kept in `plain_original`.
- We checked that none of the 14 company-name strings we tested appear in the model-input fields of the 11 rows. This is a string check only. It does not stop a model from recognizing a famous incident from place names, dates or details (7 of 11 are famous).
- The `company` field and the source URLs do name the company. The data file is not anonymous; only the model inputs are.
- No personal data about private individuals is included beyond what the regulator and company texts already say publicly.

## Tiers

`tier` records how well the pair fits the question, assigned by the authors before scoring: `good` (4 pairs), `medium` (1), `weak` (3), `good_check8k` (1, B02, an SEC filing to check), `not_euphemistic` (1, B04), `weak_date` (1, B05, statement and record far apart in time). The report analyses all pairs together and discusses tier in an appendix. Tier is a judgement, not a measurement, and n per tier is 1 to 4.

## The five-item fact checklist

Each pair has five checklist items taken from the regulator record, in this order: actor (who), action (what was done or failed), affected (who was harmed), numbers (counts, amounts, dates) and outcome (what resulted, or the enforcement result). Items are short phrases in `facts`. `fact_coverage_soft` is a soft score: each item earns partial credit (not just stated or not stated), so values such as 0.1 are expected. It was filled in by the authors and is not an automatic measure.

## Licence and terms status, by source type

I could not look up licences or terms of use for this card, and I did not check them online. What follows is what is likely and what is unconfirmed. Nothing here is legal advice.

Regulator records (`source_plain`, and `source_url` in `synth_sources.jsonl`):
- Domains: osha.gov, csb.gov, cpsc.gov, www.cpsc.gov, ftc.gov, sec.gov, epa.gov, fda.gov. All are US federal agencies. Works of the US federal government are generally not subject to copyright in the US (17 U.S.C. 105), so these texts are generally public domain.
- Can confirm: the domains are federal. Cannot confirm: that every page is wholly federal work (pages can embed third-party material), or status outside the US. The stored texts are trimmed excerpts with verdict language removed, so they are modified versions.

Company statements (`source_soft`): short quoted excerpts, each with a source URL. These are not public domain and I did not confirm any licence. The use is quotation for research, and each source is cited. Whether that counts as fair use or permitted quotation in a given jurisdiction is unconfirmed. Per domain:
- sec.gov (B01 Equifax exhibit, B02 Kraft Heinz 8-K): the document is a company-authored filing hosted by a federal agency. The filing text is the company's, so the federal public-domain rule does not clearly apply. Unconfirmed.
- about.fb.com (B06) and ezricare.com (B05): company-owned sites. No licence stated that I checked. Unconfirmed.
- web.archive.org copy of uber.com (B07): an Internet Archive copy of a company page. Archive availability does not grant a licence. Unconfirmed.
- insurancejournal.com (A01), chemicalprocessing.com (A02), cbsnews.com (A03), techcrunch.com (B03), yahoo.com (B04), kcur.org (B08): news outlets quoting the company. The quoted words are the company's, the surrounding article belongs to the outlet. We kept only the company's quoted sentences, but the outlet's terms were not checked. Unconfirmed.

If you reuse `soft_text`, check the original source and its terms yourself. If a rights holder objects, remove the row.

## Known limitations

- n = 11 real pairs. Confidence intervals in the report are wide. No result should be read as a population estimate.
- 7 of 11 cases are famous, so models may recall them despite anonymization. Only 4 of the 30 synthetic sources are flagged famous.
- One animal-welfare case (B04), one financial case (B02), one workplace-safety case (A03). Domains are thin, and per-domain results are not meaningful.
- Omission and wording are confounded: company statements usually state far fewer of the five facts (`fact_coverage_soft` 0.1 to 0.4) than the regulator text.
- Timing: company statements are often issued before deaths, causes or prior warnings were known. Some omission may be missing knowledge, not evasion. Timing was not coded.
- Residual register: removing verdict and penalty words leaves legal and technical vocabulary ("failed to", "violation") that may itself signal wrongness.
- `contrast_text` is constructed, and the trimming was model-assisted. Fact preservation was checked by one blind external rater on 40 items, not on all rows.
- Non-uniform schema (A rows vs B rows), and `plain_neutral` duplicates `plain_text` in every row. In B07 `plain_original` equals `plain_text`, so the text there was not changed by verdict removal.
- Alignment of each pair is an author judgement; the A rows are marked "lead for review".

## Intended uses

- Measuring how an LLM judge's score differs between a company's own account and a regulator's account of the same incident, and whether that difference moves when facts or wording change.
- Testing a judge or triage protocol before deployment, for example with `harness/judge_check.py`.
- Teaching and replication of the report's numbers from the saved raw outputs (`reproduce.sh`).

## Out-of-scope uses

- Not for ranking, rating or naming companies. The pairs are not a sample of corporate behaviour, and a judge's gap on one pair says nothing about a company's conduct.
- Not for legal, regulatory or reputational claims about any named company or person.
- Not as a training set for a general misconduct detector (n = 11, hand-picked).
- Not for building texts meant to slip past automated screening.
- Not evidence about incidents outside the US regulators covered here.
