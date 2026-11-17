"""Reproduce the article's audit register (R1-R4) from the MedAraBench test split.

Usage: python reproduce/reproduce_audit.py --benchmark path/to/medarabench-test_split.csv
The benchmark file is not redistributed here; obtain it from the MedAraBench authors.
"""
import argparse
import random
from pathlib import Path

import pandas as pd

from pia import audit, safe_permutation, is_identity
from pia.io import read_benchmark, read_permutations

DATA = Path(__file__).resolve().parents[1] / "data"
COLS = ["r1_changed_reference", "r1_new_self_reference", "r2_changed_positional_scope",
        "r3_identical_option_text", "r4_cross_sample_overlap"]

ap = argparse.ArgumentParser()
ap.add_argument("--benchmark", required=True)
a = ap.parse_args()

bench = {i.item_id: i for i in read_benchmark(a.benchmark, "medarabench")}
p2 = pd.read_csv(DATA / "phase2_confirmatory_ids.csv").item_id
p1 = pd.read_csv(DATA / "phase1_item_ids.csv").item_id
items = [bench[i] for i in p2]
ref = [bench[i] for i in p1]
perms = read_permutations(DATA / "phase2_permutations.csv")

res = pd.DataFrame([r.as_dict() for r in audit(items, perms, ref, "paper")]).set_index("item_id")
art = pd.read_csv(DATA / "audit_register_article.csv").set_index("item_id").loc[res.index]
print("Rule                              article  reproduced  identical items")
ok = True
for c in COLS:
    same = bool((res[c] == art[c]).all()); ok &= same
    print(f"{c:33s} {int(art[c].sum()):7d}  {int(res[c].sum()):10d}  {same}")
r13 = res[["r1_changed_reference", "r2_changed_positional_scope", "r3_identical_option_text"]].any(axis=1)
print(f"Expanded screen R1-R3: {int(r13.sum())} items; with R4: {int((r13 | res.r4_cross_sample_overlap).sum())}")
print("ALL RULES REPRODUCED EXACTLY" if ok else "MISMATCH – see above")

ext = pd.DataFrame([r.as_dict() for r in audit(items, perms, ref, "extended")]).set_index("item_id")
extra = ext.index[ext.r2_changed_positional_scope & ~res.r2_changed_positional_scope]
print(f"\nExtended positional vocabulary flags {len(extra)} additional item(s): {', '.join(extra)}")

rng = random.Random(20260925)
safe = {i.item_id: safe_permutation(i, rng) for i in items}
sres = audit(items, safe)
print(f"Safe permutations: R1 flags {sum(r.r1_changed_reference for r in sres)}, "
      f"R2 flags {sum(r.r2_changed_positional_scope for r in sres)}, "
      f"not permutable {sum(is_identity(v) for v in safe.values())} of {len(items)}")
