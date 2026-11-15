# Apart submission form: field values (fill on the sprint page "Submit project")

Deadline: Sun 15 Nov 2026 23:59 AoE = Mon 16 Nov 17:29 IST. Resubmit with the SAME title to update.

| Field | Value | Status |
|---|---|---|
| Project title | Softer Words or Missing Facts? How LLM Judges Score Company Statements Against Regulator Records | ready |
| Project summary | abstract below (250 words) | ready, Abid to reword in own voice |
| PDF report | report/report.pdf (build: report/build_pdf.sh report.pdf), <= 25 MB | build after final edits |
| Interested in publishing | Abid decides | OPEN |
| Track(s) | Track 1 (Model Epistemics and Decision-Making Evals); optionally Track 2 (Trust Infrastructure) | Abid confirms |
| Team name | Abid decides (solo) | OPEN |
| Location | India | confirm |
| Team member | Abid Khan, email: Abid chooses which address | OPEN |
| Optional: project code | public GitHub repo of sprint-epistemics-2026-11-public, only if Abid approves publishing | OPEN |
| Optional: Discord username | larylawliet | confirm |
| Author affiliation (in PDF) | [Abid to confirm] | OPEN |
| Navya credit (in PDF) | name as she wants it | waiting on Navya |

## Summary text
LLMs increasingly summarize and triage institutional reports, often deciding what a human reviewer sees. We collected 11 real incidents with both the company's public statement and the regulator's record (OSHA, CSB, CPSC, FTC, SEC, FDA, EPA), anonymized and with verdict language removed. Five open-weight judges and one frontier model (Claude Opus 5.5) rate the company's account 4.4 to 6.0 points less wrong on a 0-10 scale, as much as changing one morally relevant fact, and a plain-language rewrite defense does not close the gap on any of them. Company statements contain only 10 to 40% of the regulator's core facts. In a synthetic arm where facts are held fixed, euphemism, nominalization and agent deletion produce no systematic shift on either of two judges (pooled gaps -0.10 and 0.53 points, 95% intervals including zero), while one changed fact moves the same judges by 3 to 4 points. The real-world gap is therefore consistent with omitted facts rather than word choice. Judges detect the omission when asked directly and mostly answer UNCLEAR on fact-checks. On a scale whose zero means "no wrongdoing established", though, an incomplete statement correctly scores near zero, and a pipeline that reads that score as low wrongdoing turns missing information into exoneration. An explicit insufficient-information option separates the two clearly on one of four judges and partly on the frontier model. We provide the corpus and a one-command check that reports, for any judge, its company-versus-regulator gap, its sensitivity to one changed fact, and whether it abstains selectively.
