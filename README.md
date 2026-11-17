# Arabic medical QA: reproducibility package

Code, derived data and verification scripts for the article:

> Al-Battbootti M, Alkadhmawee AA, Aledan H, Jasim ZM, Marin I. *Permutation integrity auditing for reliability evaluation of large language models: confidence, calibration and answer stability in Arabic medical question answering.* Submitted to *Artificial Intelligence in Medicine*.

No benchmark question text is included anywhere in this repository. Files contain MedAraBench item identifiers, answer labels, model outputs reduced to labels and confidence, and derived results. Obtain MedAraBench itself from its authors.

## What is where

| Folder | Reproduces | Article sections |
|---|---|---|
| repository root (`inputs/`, `results/`, `supplements/`, `*.py`) | Confidence reliability, calibration, recalibration, selective risk and transition analyses from retained exports | 3.4–3.6, 3.8, 4.1–4.4, 4.6; Tables S1–S35 |
| `pia-audit/` | The permutation integrity audit (rules R1–R4), safe permutations, answer-change decomposition and the perturbation specificity ratio ρ | 3.7, 4.5, Table 6 |
| `expert_review/` | Pharmacist validation of the audit and physician review of answer-key disagreements | 3.7, 3.9, 4.5, 4.7; Tables 8–9 |

## Quick start

Python 3.12 is recommended (archived version 3.12.14).

```bash
git clone https://github.com/Myssar/arabic-medical-qa-reproducibility.git
cd arabic-medical-qa-reproducibility
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

# 1. Confidence reliability core
python check_integrity.py
python verify_step2.py

# 2. Permutation integrity audit
cd pia-audit && pip install -e ".[test]" && pytest && cd ..
python pia-audit/reproduce/reproduce_instability.py
# the full R1–R4 register needs the MedAraBench test split:
# python pia-audit/reproduce/reproduce_audit.py --benchmark medarabench-test_split.csv

# 3. Expert review (Tables 8 and 9)
python expert_review/score_expert_review.py
```

## 1. Confidence reliability core (repository root)

`verify_step2.py` checks 105 confidence intervals against stored bootstrap draws, seven weighted-versus-duplicated refit comparisons, within-fold separation and supplementary count accounting. It does not rerun all 2,000 refits per model or audit raw API responses.

To rebuild selected outputs, run these in a disposable checkout (they overwrite results):

```bash
python reconstruct_supplements.py    # Tables S1–S9, S17, S18
python reconstruct_transitions.py    # transition assignments and totals
python refit_analysis.py             # slower stored-fold refit bootstrap
python verify_step2.py
```

S6 is copied from the supplied transport output, not refitted. Other tables are retained exports; `ARCHIVED_STEP2_NOTES.md` documents their origins and historical rounding.

Primary confidence is the mean verbalized confidence over eligible returns, attached to the aggregated answer. It is not a posterior probability of that answer. Accuracy measures agreement with the benchmark key.

The transition reconstruction uses the original complete-case population. Its GPT-OSS-20B original-order rate is 41.0%. The audit-based exclusion analyses (36, 42 and 132 items) are reproduced by `pia-audit/`, not by this core.

## 2. Permutation integrity audit (`pia-audit/`)

This is an installable Python package with a command-line interface, tests and reproduction scripts; see `pia-audit/README.md`. `pia-audit/data/` holds the audit register of the article, item identifiers, permutation maps and the 10,000 model outputs of the presentation experiment. The reproduction scripts check their output against the published values (bootstrap seed 20260924).

## 3. Expert review (`expert_review/`)

This folder holds anonymized ratings from three pharmacists (150 permutations) and five physicians (101 questions; blinded answers, plus unblinded key-validity ratings from two physicians), together with a script that reproduces every expert-review number in the article. See `expert_review/README.md`. The web application used to collect the ratings is in `pia-audit/tools/review-webapp/`. Its question files are built locally from MedAraBench and are not committed.

## Scientific boundaries

- Correctness means agreement with the benchmark key. The physician review indicates that the key is wrong for part of the questions on which all models disagreed with it (Section 4.7).
- The audit and expert reviews are post hoc. There was no identical-prompt repeat control.
- Checksums (`checksums.json`) document this package; they are not preregistration.

## Use of AI assistants

The authors used AI assistants during this work, as declared in the article (Section 3.11 and the declaration of generative AI use):

- OpenAI ChatGPT and Anthropic Claude assisted with code review, computational auditing and exploratory reanalysis of archived outputs. This covers the perturbation specificity intervals, the displayed-letter analysis, Table 6 and the scoring of expert ratings. They also assisted with preparing documentation in this repository.
- Anthropic Claude drafted the English reading aid shown to physicians in the expert review (`expert_review/`). The Arabic question text remained authoritative.
- OpenAI ChatGPT and Anthropic Claude were used for language editing of the manuscript, and Consensus and SciSpace for literature discovery.

All computations were reproduced from the archived files, and the authors verified and approved all code, analyses and interpretations. The large language models listed in the data files (for example `openai/gpt-oss-120b` or Claude Sonnet) are the systems evaluated in the study, not tools used to produce it.

## License

Code is released under the MIT License (`LICENSE`). Derived data and results files are released for research use with citation of the article. MedAraBench content remains under its own license and is not redistributed here.

## Citation

See `CITATION.cff`.
