# Expert review data and scoring

This folder reproduces Sections 4.5 and 4.7 and Tables 8 and 9 of the article.

```bash
python score_expert_review.py      # reads data/, writes results/
```

The script requires only pandas and numpy. It prints every reported statistic and writes `results/expert_review_results.json`, `results/table8_pharmacists.csv` and `results/table9_physicians.csv`.

## Data

Reviewers are identified only by anonymous codes. No names, free-text comments or benchmark question text are included.

### `data/pharmacist_ratings.csv` (Part A)

There is one row per sampled permutation (150 rows).

- **Sample:** a stratified random sample with seed 20260925 (R1 36/36, R3 5/5, R2-only 30/86, unflagged 79/373), with columns `population_in_stratum`, `sampled_in_stratum` and `weight`.
- **Ratings:** `pharmacist_1`–`pharmacist_3` hold each pharmacist's judgment (`PRESERVED`, `CHANGED` or `UNCERTAIN`). Pharmacists are numbered in order of completion; two further invited pharmacists did not complete the task.

### `data/physician_blinded_answers.csv` (Part B, blinded stage)

There is one row per question (101 rows): the 59 questions on which all seven configurations agreed against the key, and 42 high-confidence errors (six per configuration, confidence ≥0.90).

- **Item columns:** `model_answer` and `benchmark_key` (answer letters), plus specialty metadata.
- **Answers:** `physician_1`–`physician_5` hold each physician's answer, given before the key or any model output was shown. Besides an answer letter, the possible values are `MULTIPLE` (more than one defensible answer), `NONE` (no correct option) and `CANNOT_JUDGE`.

### `data/physician_unblinded_ratings.csv` (Part B, unblinded stage)

These are key-validity and severity ratings from the two physicians who completed this stage.

- **Key validity:** `KEY_CORRECT`, `KEY_INCORRECT`, `MULTIPLE`, `FLAWED` or `CANNOT_JUDGE`.
- **Severity of relying on the model answer:** `ACCEPTABLE`, `MINOR`, `MODERATE`, `HARMFUL` or `NA`. `NA` was used when the physician could not judge the key.

Read the CSVs with `keep_default_na=False`, so that the literal value `NA` is not treated as missing.

## Methods summary

- Ratings were collected with the web application in `../pia-audit/tools/review-webapp/`. Each reviewer had a personal link, saw the items in their own seeded random order and had answers saved automatically. The last saved value of each item is analyzed.
- **Part A:** "changed" versus "not changed", with uncertain counted as not changed. The script reports the majority of three, Fleiss' and Cohen's κ, Wilson 95% intervals, and inverse-probability-weighted shares of changed items with 5,000 stratified bootstrap resamples. R1 items serve as a positive control.
- **Part B:** the majority is the same response from at least three of five physicians. Robustness is checked by excluding each physician (majority three of four) and each pair (majority two of three).
- **Disclosure:** two of the five physician reviewers are co-authors. They rated under the same blinded procedure and joined the author team after submitting their ratings. The script reports the results with every pair excluded, including theirs.
- **Questions were displayed in Arabic.** From 30 October 2026, an English reading aid prepared with AI assistance was shown beneath the Arabic text. The Arabic text remained authoritative.
