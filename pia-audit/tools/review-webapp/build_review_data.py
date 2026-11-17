"""Build dataA.gs and dataB.gs for the review web app from the MedAraBench file.

The repository stores only item IDs and option maps; question text and answer keys are read from your local
copy of the benchmark. Usage:
    python build_review_data.py --benchmark medarabench-test_split.csv
Also writes partB_key.csv (with the benchmark key) for scoring. Keep dataB.gs and partB_key.csv private.
"""
import argparse, json
from pathlib import Path

import pandas as pd

H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--benchmark", required=True); a = ap.parse_args()
t = pd.read_csv(a.benchmark, dtype=str, keep_default_na=False)
t["item_id"] = "mab" + t["Question Number"].astype(float).astype(int).astype(str)
T = t.set_index("item_id")


def opts(iid):
    r = T.loc[iid]
    return {L: r[f"Option {L}"].strip() for L in "ABCDEF" if f"Option {L}" in r and str(r[f"Option {L}"]).strip()}


A = pd.read_csv(H / "partA_sample.csv")
partA = []
for r in A.itertuples():
    o = opts(r.item_id)
    show = lambda m: "\n".join(f"{d}. {o[c]}" for d, c in sorted(json.loads(m).items()))
    partA.append({"id": r.review_id, "q": T.loc[r.item_id, "Question"].strip(), "x": show(r.X_to_canonical), "y": show(r.Y_to_canonical)})

B = pd.read_csv(H / "partB_items.csv")
partB, keys = [], []
for r in B.itertuples():
    o = opts(r.item_id); key = T.loc[r.item_id, "Correct Answer"].strip().upper()
    partB.append({"id": r.survey_id, "q": T.loc[r.item_id, "Question"].strip(), "opts": [[k, v] for k, v in o.items()], "key": key, "model": r.model_answer})
    keys.append(key)
B.assign(benchmark_key=keys).to_csv(H / "partB_key.csv", index=False)
(H / "dataA.gs").write_text("const PART_A = " + json.dumps(partA, ensure_ascii=False, indent=0) + ";\n", encoding="utf-8")
(H / "dataB.gs").write_text("// Contains the answer key: keep private.\nconst PART_B = " + json.dumps(partB, ensure_ascii=False, indent=0) + ";\n", encoding="utf-8")
print(f"dataA.gs: {len(partA)} items; dataB.gs: {len(partB)} items; partB_key.csv written")
