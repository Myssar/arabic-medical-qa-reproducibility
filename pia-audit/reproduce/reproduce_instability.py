"""Reproduce the answer-change results (Tables 6-7 and the perturbation specificity ratio).

Usage: python reproduce/reproduce_instability.py
Uses only files in data/ (model outputs, permutation register), no benchmark text.
"""
from pathlib import Path

import pandas as pd

from pia import specificity_ratio, transition_decomposition

DATA = Path(__file__).resolve().parents[1] / "data"
p = pd.read_csv(DATA / "phase2_paired_outputs.csv")
p = p[p.valid_output.astype(str).str.lower() == "true"].rename(columns={
    "model_label": "model", "prompt_id": "prompt", "order_id": "order", "canonical_answer": "answer"})
P, O = ("P0_original", "P1_probability"), ("O0_original", "O1_permuted")
pd.set_option("display.width", 200)

rho = specificity_ratio(p, P, O, n_boot=5000, seed=20260924)
print("Perturbation specificity ratio (complete four-cell questions):")
print(rho[["model", "n", "order_change", "instruction_change", "rho", "rho_lo", "rho_hi"]].round(3).to_string(index=False))

dec = transition_decomposition(p, "order", P, O)
print("\nOrder-change decomposition (shares of questions):")
print(dec.round(3).to_string(index=False))

reg = pd.read_csv(DATA / "audit_register_article.csv")
r1 = set(reg.item_id[reg.r1_changed_reference])
p["R1"] = p.item_id.isin(r1)
t6 = (p.groupby(["model", "R1", "order"]).correct.mean().unstack() * 100).round(1)
print("\nAccuracy (%) by R1 flag and option order (Table 6):")
print(t6.to_string())
