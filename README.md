# Arabic medical QA: offline reproducibility core

Repository preparation: 23 September 2026. Remote publication pending.

This package checks and reconstructs selected analyses from retained, derived study exports. It requires no API keys, network calls during analysis, or new model generations. It is not the complete manuscript submission package or an independent validation of the source data.

## Quick verification

Use Python 3.12 (archived version 3.12.14):

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows instead: .venv\Scripts\activate
python -m pip install -r requirements.txt
python check_integrity.py
python verify_step2.py
```

Verification checks 105 confidence intervals against stored bootstrap draws, seven weighted-versus-duplicated refit comparisons, within-fold separation, and supplementary count accounting. It does not rerun all 2,000 refits per model or independently audit raw API responses.

## Reconstruct selected outputs

Run in a disposable checkout; these commands overwrite the corresponding results:

```bash
python reconstruct_supplements.py
python reconstruct_transitions.py
python verify_step2.py
```

These rebuild Tables S1–S9, S17, S18 and transition assignments/totals. S6 is copied from supplied transport output, not refitted. Other tables are retained exports; see ARCHIVED_STEP2_NOTES.md for their origins, historical rounding and interval differences.

For the slower complete stored-fold refit bootstrap:

```bash
python refit_analysis.py
python verify_step2.py
```

## Scientific boundaries

Inputs contain item identifiers, labels, correctness and confidence summaries, not original question text or patient records. Primary confidence is mean verbalized confidence over eligible returns, attached to the aggregated answer; it is not a posterior probability of that answer. Accuracy measures benchmark-key agreement.

The transition reconstruction uses the original complete-case population. It does **not** reproduce the later 36/42/132-item defect-exclusion sensitivity analyses. Its GPT-OSS-20B original-order comparison is 41.0%, not the later 40.4% after 42 exclusions. Do not substitute it for the final manuscript sensitivity result.

The final numbered supplementary evidence, later audit code, complete raw traces, manuscript and figures are outside this core. No clinician review, external validation or identical-prompt repeat control is supplied. Transition accounting is an algebraic identity, not a demonstrated novel theorem. Stored-fold separation does not establish that benchmark content has no semantic duplicates.

## Access and reuse

Begin with a private repository. Redistribution rights for benchmark-derived data and author agreement on a code license remain to be confirmed. No open-source or third-party data license is granted by this package. Complete the checks in SUBMISSION_CHECKS.md before public release or journal submission.

Checksums document this preparation, not prospective preregistration or independent provenance. A passing local check does not prove GitHub reviewer access or journal acceptance.
