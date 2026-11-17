# pia-audit – permutation integrity auditing for multiple-choice LLM benchmarks

Reordering answer options is a standard robustness test for large language models. It assumes the reordered
question means the same thing. That assumption fails when options refer to other options: after reordering,
"A+B" or "كل ما سبق" (all of the above) can point to different content, and an apparent *order effect* is really a
defect in the test.

`pia-audit` checks every permuted item before order effects are interpreted, generates permutations that keep
meaning intact, and quantifies how much answer instability is specific to option order.

This repository accompanies the article *Permutation integrity auditing for reliability evaluation of large language
models: confidence, calibration and answer stability in Arabic medical question answering* (Al-Battbootti,
Alkadhmawee, Aledan, Jasim, Marin; submitted to *Artificial Intelligence in Medicine*).

## Install
```bash
pip install "git+https://github.com/Myssar/arabic-medical-qa-reproducibility.git#subdirectory=pia-audit"
# or, after cloning: cd pia-audit && pip install -e .
```
Python ≥3.9; depends only on pandas and numpy.

## The four rules
| Rule | Flags an item when… |
|---|---|
| **R1** explicit reference | an option names other options by letter (“A+B”, “C و D”) and the permutation changes which options those letters denote; also records options that come to refer to their own new label |
| **R2** positional scope | an option uses positional wording (“كل ما سبق”, “all of the above”) and the options displayed before it change |
| **R3** distinctness | two options are identical after Unicode NFC and whitespace normalization |
| **R4** cross-sample overlap | the normalized stem and labelled options duplicate an item in a reference sample |

R1 directly establishes a change in meaning; R2 and R3 are conservative screens; R4 concerns sample integrity.
Two positional vocabularies are provided: `paper` (reproduces the article exactly) and `extended` (adds phrases such
as “كل ما ذكر” and “جميع الإجابات”).

## Command line
```bash
# 1. audit an existing permutation
pia audit --benchmark bench.csv --permutations perms.csv --reference-ids other_sample_ids.csv -o register.csv

# 2. generate integrity-preserving ("safe") permutations; referential options stay in place
pia permute --benchmark bench.csv --mode safe --seed 1 -o safe_perms.csv

# 3. decompose answer changes and compute the perturbation specificity ratio (2 x 2 design)
pia decompose --paired outputs.csv --prompts P0 P1 --orders O0 O1 --output-prefix results
```
`bench.csv` needs `item_id, question, option_A … option_F` (or use `--format medarabench`). A permutation file has
`item_id, display_to_canonical` where the JSON object maps each displayed label to its original label.

**Perturbation specificity ratio.** ρ = mean answer-change rate under option reordering ÷ mean answer-change rate
under instruction rewording, with question-level paired bootstrap intervals. ρ ≈ 1 means a model changes its answers
about as often under an unrelated perturbation, so instability is not specific to option order.

## Python API
```python
from pia import Item, audit, safe_permutation
item = Item("q1", "أي مما يلي من الفيتامينات الذائبة في الدهون؟",
            {"A": "فيتامين د", "B": "فيتامين ك", "C": "فيتامين ج", "D": "A+B"})
print(audit([item], {"q1": {"A": "C", "B": "A", "C": "B", "D": "D"}})[0].details)
```

## Reproducing the article
`data/` holds item IDs, permutation maps, the article's audit register and the 10,000 model outputs of the
presentation experiment. It contains **no benchmark question text**; obtain MedAraBench from its authors.
```bash
python reproduce/reproduce_audit.py --benchmark medarabench-test_split.csv   # R1-R4 register: 36 / 17 / 90 / 5 / 6
python reproduce/reproduce_instability.py                                     # answer-change rates, rho, Table 6
```
Both scripts check their output against the published values. Bootstrap intervals use seed 20260924.

## Human review web app
`tools/review-webapp/` contains the Google Apps Script web app used for blinded validation by pharmacists
(Part A) and doctors (Part B). The anonymized ratings and the script that reproduces the article's expert-review
results are in `../expert_review/`.

## Tests
```bash
pip install -e ".[test]" && pytest
```

## Citation
See `CITATION.cff`. Please cite the article when using the tool.

## License
Code: MIT. The data files contain identifiers and derived results only; MedAraBench content remains under its own license.

---

### بالعربية
أداة `pia-audit` تفحص أسئلة الاختيار من متعدد قبل تغيير ترتيب خياراتها، وتكشف الحالات التي يتغيّر فيها معنى السؤال
(مثل خيار «A+B» أو «كل ما سبق»). كما تُنشئ ترتيبات آمنة تحافظ على المعنى، وتحسب نسبة تغيّر الإجابات الناتجة عن
الترتيب مقارنةً بتغيير صياغة التعليمات. المستودع يرافق البحث المقدَّم إلى مجلة *Artificial Intelligence in Medicine*.
