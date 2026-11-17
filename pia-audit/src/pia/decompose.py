"""Paired answer-change analysis for a 2 x 2 instruction-by-order design.

Input: one row per (item, model, prompt, order) with the canonical answer and correctness.
Only items with a valid answer in all four cells are used (complete cases), as in the article.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def _complete(df: pd.DataFrame, prompts: Tuple[str, str], orders: Tuple[str, str]) -> pd.DataFrame:
    d = df.dropna(subset=["answer"]).copy()
    d["cell"] = d["prompt"].astype(str) + "|" + d["order"].astype(str)
    cells = [f"{p}|{o}" for p in prompts for o in orders]
    ans = d.pivot_table(index=["model", "item_id"], columns="cell", values="answer", aggfunc="first")
    cor = d.pivot_table(index=["model", "item_id"], columns="cell", values="correct", aggfunc="first")
    ans, cor = ans.reindex(columns=cells), cor.reindex(columns=cells)
    keep = ans.notna().all(axis=1)
    return pd.concat({"ans": ans[keep], "cor": cor[keep]}, axis=1)


def change_rates(df, prompts=("P0", "P1"), orders=("O0", "O1")) -> pd.DataFrame:
    """Answer-change rates under each perturbation holding the other factor fixed."""
    w = _complete(df, prompts, orders)
    (p0, p1), (o0, o1) = prompts, orders
    a = w["ans"]
    out = pd.DataFrame({
        f"order_change_{p0}": (a[f"{p0}|{o0}"] != a[f"{p0}|{o1}"]),
        f"order_change_{p1}": (a[f"{p1}|{o0}"] != a[f"{p1}|{o1}"]),
        f"instruction_change_{o0}": (a[f"{p0}|{o0}"] != a[f"{p1}|{o0}"]),
        f"instruction_change_{o1}": (a[f"{p0}|{o1}"] != a[f"{p1}|{o1}"]),
    })
    return out


def transition_decomposition(df, contrast="order", prompts=("P0", "P1"), orders=("O0", "O1")) -> pd.DataFrame:
    """Shares of correct->incorrect (l), incorrect->correct (g) and incorrect->different incorrect (w)
    for each model and level of the fixed factor, with F = g + l + w and net change g - l."""
    w = _complete(df, prompts, orders)
    rows = []
    fixed = prompts if contrast == "order" else orders
    for lev in fixed:
        if contrast == "order":
            c0, c1 = f"{lev}|{orders[0]}", f"{lev}|{orders[1]}"
        else:
            c0, c1 = f"{prompts[0]}|{lev}", f"{prompts[1]}|{lev}"
        for model, g in w.groupby(level="model"):
            a0, a1 = g["ans"][c0], g["ans"][c1]
            k0, k1 = g["cor"][c0].astype(int), g["cor"][c1].astype(int)
            n = len(g)
            loss = ((k0 == 1) & (k1 == 0)).mean()
            gain = ((k0 == 0) & (k1 == 1)).mean()
            wrong = ((k0 == 0) & (k1 == 0) & (a0 != a1)).mean()
            rows.append({"model": model, "fixed_level": lev, "n": n, "correct_to_incorrect": loss,
                         "incorrect_to_correct": gain, "different_incorrect": wrong,
                         "answer_change_rate": loss + gain + wrong, "net_accuracy_change": gain - loss})
    return pd.DataFrame(rows)


def specificity_ratio(df, prompts=("P0", "P1"), orders=("O0", "O1"), n_boot=5000, seed=20260924) -> pd.DataFrame:
    """rho = mean order-change rate / mean instruction-change rate, with question-level paired bootstrap CIs."""
    rates = change_rates(df, prompts, orders)
    rng = np.random.default_rng(seed)
    rows = []
    for model, g in rates.groupby(level="model"):
        X = g.to_numpy(dtype=float)
        n = len(X)

        def rho(M):
            o, i = M[:, :2].mean(), M[:, 2:].mean()
            return (o / i if i > 0 else np.nan), o - i
        r, d = rho(X)
        bs = np.array([rho(X[rng.integers(0, n, n)]) for _ in range(n_boot)])
        rows.append({"model": model, "n": n,
                     "order_change": X[:, :2].mean(), "instruction_change": X[:, 2:].mean(),
                     "rho": r, "rho_lo": np.nanpercentile(bs[:, 0], 2.5), "rho_hi": np.nanpercentile(bs[:, 0], 97.5),
                     "excess_pp": 100 * d, "excess_lo": 100 * np.percentile(bs[:, 1], 2.5),
                     "excess_hi": 100 * np.percentile(bs[:, 1], 97.5)})
    return pd.DataFrame(rows)
