# Held-out candidate selection rule

Written and committed before any candidate was collected. It is not to be edited after collection starts, except by a dated amendment at the bottom.

## Purpose

Build a held-out pool of 25 candidate incidents, separate from the 11 cases in data/pairs.jsonl, so that later tests of the soft-versus-plain wording effect are not fit to the cases used to develop the method.

## Sources (regulator side)

OSHA, CSB, CPSC, FTC, SEC, FDA, EPA, UK HSE. Only public pages on the agency's own domain (osha.gov, csb.gov, cpsc.gov, ftc.gov, sec.gov, fda.gov, epa.gov, hse.gov.uk).

## Inclusion rule (fixed in advance)

A candidate is included only if all of these hold:

1. The incident date is between 2015-01-01 and 2026-12-31.
2. There is a public regulator record about the incident (press release, citation, order, report, recall notice, warning letter, or similar) at a URL I opened.
3. There is a public company statement about the same incident (press release, web statement, filing, or social post) at a URL I opened.
4. At least one harm is stated in either document (injury, death, illness, exposure, financial loss, data exposed, environmental release). The harm_stated column records yes or no for whether a harm is stated in the regulator record; the harm must still be stated somewhere to qualify.
5. It is not one of the 11 cases in data/pairs.jsonl (A01-A03, B01-B08), judged by company and incident.

Anything failing a test is dropped, not repaired. A URL I could not open is marked UNVERIFIED in its column, and a row with an UNVERIFIED URL does not count toward the 25.

## Avoiding regulator text that is harsher by construction

The risk: enforcement documents are adversarial by design, so a pool built from them will always look harsher than company text. Controls:

1. Selection uses only metadata (agency, date, existence of both documents, harm stated). I do not read the two texts for tone before deciding to include a case, and I do not pick a case because the company text looks vague or the regulator text looks severe.
2. I do not search with words like "evasive", "downplay", "minimize", or "euphemism".
3. Regulator records are taken as they come in each agency's listing, in reverse date order, from the first qualifying entries found. I do not skip a qualifying entry once seen, except for the five inclusion tests.
4. Spread across agencies: at most 5 candidates per agency, so no single agency's house style dominates.
5. Include neutral and cooperative cases: recalls announced jointly with the company, voluntary disclosures, and cases where the company text is detailed. These are not excluded for being plain.
6. Both documents are recorded as found, with only short quotes in notes. No text is copied at length.
7. The notes column records anything that makes the regulator record unusually harsh by genre (for example a criminal plea or a warning letter) so analysis can stratify on it.

## Output

data/heldout_candidates.csv with columns: id, agency, incident_date, company_anonymized_label, regulator_url, company_statement_url, harm_stated, notes. Company labels are anonymized (Company A, B, ...).

## Collection status

Not started at the time of writing this rule.
