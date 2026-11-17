"""Reproduce the expert-review results of the article (Sections 4.5 and 4.7, Tables 8 and 9).

Usage:  python score_expert_review.py            (reads ./data, writes ./results)
Requires pandas and numpy only.
"""
from __future__ import annotations
import itertools, json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "results"
OUT.mkdir(exist_ok=True)
read = lambda name: pd.read_csv(DATA / name, keep_default_na=False, na_values=[""])
NON_ANSWERS = ("CANNOT_JUDGE", "MULTIPLE", "NONE")


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h), 1), round(100 * (c + h), 1)


def fleiss(M):
    M = np.asarray(M).astype(str); cats = sorted(set(M.ravel())); n = M.shape[1]
    cnt = np.array([[(row == c).sum() for c in cats] for row in M])
    P = (cnt * (cnt - 1)).sum(1) / (n * (n - 1)); pj = cnt.sum(0) / cnt.sum()
    return round(float((P.mean() - (pj ** 2).sum()) / (1 - (pj ** 2).sum())), 3)


def cohen(a, b):
    a, b = np.asarray(a).astype(str), np.asarray(b).astype(str)
    po = (a == b).mean(); pe = sum((a == c).mean() * (b == c).mean() for c in set(a) | set(b))
    return round(float((po - pe) / (1 - pe)), 3), round(float(po), 3)


res = {}
# ---------------------------------------------------------------- Part A: pharmacists
A = read("pharmacist_ratings.csv")
P = ["pharmacist_1", "pharmacist_2", "pharmacist_3"]
C = A[P].eq("CHANGED")                       # uncertain counted as not changed
nonR1 = A.stratum != "R1"
res["partA"] = {
    "fleiss_all": fleiss(C.astype(int).values),
    "fleiss_excluding_R1": fleiss(C[nonR1].astype(int).values),
    "cohen_p1_p2_all": cohen(C.pharmacist_1, C.pharmacist_2),
    "cohen_p1_p2_excluding_R1": cohen(C[nonR1].pharmacist_1, C[nonR1].pharmacist_2),
}
A["majority_changed"] = C.sum(axis=1) >= 2
table8 = []
for s in ["R1", "R2_only", "R3", "Unflagged"]:
    g = A[A.stratum == s]; k = int(g.majority_changed.sum()); n = len(g)
    table8.append({"stratum": s, "sampled": n, "population": int(g.population_in_stratum.iloc[0]),
                   **{p: int(C.loc[g.index, p].sum()) for p in P},
                   "majority_changed": k, "pct": round(100 * k / n, 1), "wilson_95": wilson(k, n)})
pd.DataFrame(table8).to_csv(OUT / "table8_pharmacists.csv", index=False)
res["partA"]["table8"] = table8

# weighted share of changed items captured by R1 and by the R1-R3 screen (R1 treated as changed)
pop = {"R2_only": 86, "Unflagged": 373, "R3": 5}
grp = {s: A[A.stratum == s].majority_changed.values.astype(int) for s in pop}
def shares(g):
    ch = {s: g[s].mean() * pop[s] for s in pop}; tot = 36 + sum(ch.values())
    return 36 / tot, (36 + ch["R2_only"] + ch["R3"]) / tot, ch["R2_only"], ch["Unflagged"]
rng = np.random.default_rng(20260925)
boot = np.array([shares({s: rng.choice(v, len(v)) for s, v in grp.items()}) for _ in range(5000)])
pt = shares(grp)
res["partA"]["weighted"] = {
    "R2_only_changed_est": round(pt[2], 1), "unflagged_changed_est": round(pt[3], 1),
    "R1_share": round(pt[0], 3), "R1_share_95": np.percentile(boot[:, 0], [2.5, 97.5]).round(3).tolist(),
    "screen_share": round(pt[1], 3), "screen_share_95": np.percentile(boot[:, 1], [2.5, 97.5]).round(3).tolist()}

# ---------------------------------------------------------------- Part B: physicians (blinded)
B = read("physician_blinded_answers.csv")
D = [f"physician_{i}" for i in range(1, 6)]
def cat(v, r):
    if v in NON_ANSWERS: return v
    return "key" if v == r.benchmark_key else ("model" if v == r.model_answer else "other")
def majority(r, raters, need):
    v, n = Counter(r[d] for d in raters).most_common(1)[0]
    return v if n >= need else "NO_MAJORITY"
B["majority"] = B.apply(lambda r: majority(r, D, 3), axis=1)
B["majority_class"] = [cat(v, r) if v != "NO_MAJORITY" else "no majority" for v, r in zip(B.majority, B.itertuples())]
res["partB"] = {"fleiss_all_categories": fleiss(B[D].values),
                "cannot_judge_rate": {d: round(float((B[d] == "CANNOT_JUDGE").mean()), 3) for d in D},
                "multiple_rate": {d: round(float((B[d] == "MULTIPLE").mean()), 3) for d in D}}
table9 = {}
for s, g in B.groupby("source"):
    vc = g.majority_class.value_counts().to_dict(); n = len(g)
    table9[s] = {"n": n, **{k: int(v) for k, v in vc.items()},
                 "model_wilson_95": wilson(vc.get("model", 0), n), "key_wilson_95": wilson(vc.get("key", 0), n)}
res["partB"]["table9"] = table9
pd.DataFrame(table9).T.to_csv(OUT / "table9_physicians.csv")
U = B[B.source == "UNANIMOUS_DISAGREEMENT"]
res["partB"]["unanimous_endorsements"] = {
    "model": int(sum((U[d] == U.model_answer).sum() for d in D)),
    "key": int(sum((U[d] == U.benchmark_key).sum() for d in D)), "of": 5 * len(U)}
res["partB"]["model_majority_specialties"] = U[U.majority_class == "model"].umbrella_specialty.value_counts().to_dict()
loo = {}
for excl in itertools.chain(itertools.combinations(D, 1), itertools.combinations(D, 2)):
    keep = [d for d in D if d not in excl]; need = len(keep) // 2 + 1
    m = U.apply(lambda r: majority(r, keep, need), axis=1)
    loo["+".join(excl)] = {"model": int((m == U.model_answer).sum()), "key": int((m == U.benchmark_key).sum())}
res["partB"]["exclusion_robustness"] = loo

# ---------------------------------------------------------------- Part B: unblinded stage (two physicians)
UB = read("physician_unblinded_ratings.csv")
w = UB.pivot(index="survey_id", columns="rater", values="key_validity")
sv = UB.pivot(index="survey_id", columns="rater", values="severity")
raters = list(w.columns)
res["unblinded"] = {"raters": raters, "cohen_key_validity": cohen(w[raters[0]], w[raters[1]])}
Bi = B.set_index("survey_id")
J = Bi[["source", "majority_class"]].join(w.add_suffix("_kv"))
for src, g in J.groupby("source"):
    res["unblinded"][src] = {r: g[r + "_kv"].value_counts().to_dict() for r in raters}
    res["unblinded"][src]["both_incorrect"] = int(g[[r + "_kv" for r in raters]].eq("KEY_INCORRECT").all(axis=1).sum())
mm = J[(J.source == "UNANIMOUS_DISAGREEMENT") & (J.majority_class == "model")]
res["unblinded"]["model_majority_items"] = {r: mm[r + "_kv"].value_counts().to_dict() for r in raters}
res["unblinded"]["severity_when_key_correct"] = {r: sv[r][w[r] == "KEY_CORRECT"].value_counts().to_dict() for r in raters}
cons = {}
for r in raters:
    bl, kv, key = Bi[r], w[r], Bi.benchmark_key
    ok = ((bl == key) & (kv == "KEY_CORRECT")) | (~bl.isin(NON_ANSWERS) & (bl != key) & (kv == "KEY_INCORRECT")) | \
         ((bl == "CANNOT_JUDGE") & (kv == "CANNOT_JUDGE")) | ((bl == "MULTIPLE") & (kv == "MULTIPLE"))
    cons[r] = int(ok.sum())
res["unblinded"]["consistent_with_own_blinded_answer"] = cons

(OUT / "expert_review_results.json").write_text(json.dumps(res, indent=2, default=str))
print(json.dumps(res, indent=2, default=str))
