# Arabic medical QA strengthening step 2

Completed 16 September 2026. This is a strengthened manuscript version for author review, not a certification of submission readiness or acceptance. No new model generations or physician assessments were performed.

## What changed

- Added 2,000-replicate, question-identity bootstrap uncertainty that refits base-rate, logistic and isotonic predictors within the original five-fold allocation. All copies of a question remain in one fold, avoiding training/evaluation identity leakage.
- Added Table S35 and corresponding Methods, Results and Limitations text. Existing main and appendix numerical tables and all 12 figures are preserved.
- Supplied standalone CSVs for Tables S1–S35 with an explicit provenance inventory. Some are reconstructed analyses, others archived outputs or rounded appendix exports; these are not interchangeable evidence types.
- Added a reproducible verification script: 105 interval rows recomputed from stored draws; seven weighted-refit calculations checked against explicit duplicate-row fits; fold isolation and supplementary count identities checked.

## Main findings

Isotonic Brier score and log loss remain lower than cross-fitted base-rate predictions for six configurations. Llama-3.1-8B remains unresolved (Brier difference -0.000982, interval -0.003681 to +0.002540; log loss +0.004026, interval -0.003638 to +0.034562). These six include Claude and differ from the six that improved over native confidence.

Claude isotonic versus native confidence remains unresolved for Brier score, log loss and ECE. Its ECE interval is -0.039996 to +0.000351. The initial 1,000-replicate upper endpoint was -0.000225. We increased the count to 2,000 to assess numerical stability after observing this boundary result; this was a post hoc amendment, not a prespecified decision. The initial summaries and analysis plan are retained. Neither a tiny threshold crossing nor this amendment establishes improvement.

Intervals are descriptive, unadjusted for multiple comparisons and conditional on the original folds and retained outputs. Resampling does not address source-cluster dependence, future model generations, model updates or external transport. Pooled ECE can exhibit bias and cancellation; percentile intervals need not contain the original point estimate. Proper scoring rules are the main basis of the base-rate comparison.

## Supplement reconciliation

S1: matched McNemar tests, 19/21 Bonferroni-adjusted comparisons below .05. S2: 69,703 retained outputs, 315 invalid returned outputs, 469 valid answers without numeric confidence. S3–S5: subgroup and reliability-bin reconstruction. S6: original transport-stratum CSV copied. S7: first valid answer-plus-confidence and ensemble estimates. S8: new exact uniform-random tie expectation and explicitly seeded 500-repetition simulation; historical finite Monte Carlo averages in S29 remain unchanged. S9: reconstructed 2,000-resample selective-risk intervals and historical rounded-rank coverage rule; Step1 used fractional coverage in its separate comparator analysis. S17: retrospective approximate precision, not prospective power. S18: 100 transition-class rows, with gains/losses and additive loss-accounting identities checked. Reconstructed interval endpoints can differ from historical outputs because row order and random streams differ; original displayed intervals are preserved. S19–S20 and S22–S33 are rounded appendix exports. S34 contains Step1 fixed-prediction contrasts. S35 contains full-precision Step2 refitting contrasts.

Complete numbered-table coverage does not establish completeness of separately cited supplementary File S1–S15, raw traces, dataset licenses or a public release. Those require an author-level archive check before submission.

## Reproduce

Dependencies: Python with numpy, pandas, scipy, scikit-learn and python-docx; versions are recorded in environment.json. Run refit_analysis.py, reconstruct_supplements.py, reconstruct_transitions.py and verify_step2.py from this directory. The refitting run is computationally substantial. Scripts resolve their inputs relative to their own paths; no API keys or new model calls are required. Document update code uses the Step1 DOCX files supplied in source_docs. Inputs contain archived item-level measurements and labels, not a newly validated clinical reference standard.

## Remaining work before submission

1. The most useful next experimental strengthening is a held-out external dataset evaluation with frozen calibration and prespecified loss/selective-risk comparisons. This has not been run.
2. An identical-prompt/order repeated-call control is needed to separate stochastic generation changes from presentation sensitivity. Existing factorial outputs cannot supply this missing control.
3. Physician review is unavailable. Keep all outcomes explicitly benchmark-key agreement; do not claim clinical safety, diagnostic quality or deployment readiness. Corrected-key and overlap sensitivity findings remain central limitations.
4. Complete author details, ethics/data/license statements, funding and conflicts, repository/DOI release, all supplementary-file references and target-journal formatting. Verify current journal scope and requirements at submission.

The contribution is an auditable evaluation of confidence, selective prediction and presentation sensitivity in Arabic medical QA, strengthened by a base-rate comparator and refitting uncertainty. It does not introduce a new calibration algorithm or establish clinical utility. Q1 acceptance cannot be guaranteed.
