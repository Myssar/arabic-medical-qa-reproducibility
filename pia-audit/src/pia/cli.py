"""Command-line interface: pia audit | permute | decompose."""
from __future__ import annotations

import argparse
import random
import sys

import pandas as pd

from .decompose import specificity_ratio, transition_decomposition
from .io import read_benchmark, read_permutations, write_permutations
from .permute import free_permutation, is_identity, safe_permutation
from .rules import audit


def cmd_audit(a):
    items = read_benchmark(a.benchmark, a.format)
    if a.ids:
        keep = set(pd.read_csv(a.ids, dtype=str).item_id)
        items = [i for i in items if i.item_id in keep]
    perms = read_permutations(a.permutations) if a.permutations else {}
    ref = None
    if a.reference_ids:
        rids = set(pd.read_csv(a.reference_ids, dtype=str).item_id)
        ref = [i for i in read_benchmark(a.benchmark, a.format) if i.item_id in rids]
    res = pd.DataFrame([r.as_dict() for r in audit(items, perms, ref, a.vocab)])
    res.to_csv(a.output, index=False)
    s = res.drop(columns=["item_id", "details"]).sum()
    print(f"Audited {len(res)} items -> {a.output}")
    for k, v in s.items():
        print(f"  {k:30s} {int(v)}")


def cmd_permute(a):
    items = read_benchmark(a.benchmark, a.format)
    if a.ids:
        keep = set(pd.read_csv(a.ids, dtype=str).item_id)
        items = [i for i in items if i.item_id in keep]
    rng = random.Random(a.seed)
    perms, fixed = {}, 0
    for it in items:
        d2c = safe_permutation(it, rng, a.vocab) if a.mode == "safe" else free_permutation(it, rng)
        fixed += is_identity(d2c)
        perms[it.item_id] = d2c
    write_permutations(perms, a.output)
    res = audit(items, perms, vocab=a.vocab)
    r1 = sum(r.r1_changed_reference for r in res); r2 = sum(r.r2_changed_positional_scope for r in res)
    print(f"{a.mode} permutations for {len(items)} items -> {a.output}")
    print(f"  not permutable (identity): {fixed}; R1 flags: {r1}; R2 flags: {r2}")


def cmd_decompose(a):
    df = pd.read_csv(a.paired)
    ren = {a.item_col: "item_id", a.model_col: "model", a.prompt_col: "prompt", a.order_col: "order",
           a.answer_col: "answer", a.correct_col: "correct"}
    df = df.rename(columns=ren)
    if a.valid_col:
        df = df[df[a.valid_col].astype(str).str.lower().isin(["true", "1"])]
    prompts, orders = tuple(a.prompts), tuple(a.orders)
    dec = transition_decomposition(df, "order", prompts, orders)
    rho = specificity_ratio(df, prompts, orders, n_boot=a.n_boot, seed=a.seed)
    dec.to_csv(a.output_prefix + "_order_decomposition.csv", index=False)
    rho.to_csv(a.output_prefix + "_specificity_ratio.csv", index=False)
    pd.set_option("display.width", 160)
    print(dec.round(4).to_string(index=False)); print(); print(rho.round(3).to_string(index=False))


def main(argv=None):
    p = argparse.ArgumentParser(prog="pia", description="Permutation integrity audit for multiple-choice benchmarks")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "permute"):
        s = sp.add_parser(name)
        s.add_argument("--benchmark", required=True)
        s.add_argument("--format", choices=["generic", "medarabench"], default="generic")
        s.add_argument("--ids", help="CSV with an item_id column restricting the items")
        s.add_argument("--vocab", choices=["paper", "extended"], default="paper")
        s.add_argument("-o", "--output", required=True)
    s = sp.choices["audit"]
    s.add_argument("--permutations", help="CSV: item_id, display_to_canonical (JSON)")
    s.add_argument("--reference-ids", help="CSV with item_id of a reference sample for R4")
    s = sp.choices["permute"]
    s.add_argument("--mode", choices=["safe", "free"], default="safe")
    s.add_argument("--seed", type=int, default=20260925)
    s = sp.add_parser("decompose")
    s.add_argument("--paired", required=True)
    for c, d in [("item", "item_id"), ("model", "model_label"), ("prompt", "prompt_id"), ("order", "order_id"),
                 ("answer", "canonical_answer"), ("correct", "correct")]:
        s.add_argument(f"--{c}-col", default=d)
    s.add_argument("--valid-col", default=None)
    s.add_argument("--prompts", nargs=2, required=True)
    s.add_argument("--orders", nargs=2, required=True)
    s.add_argument("--n-boot", type=int, default=5000)
    s.add_argument("--seed", type=int, default=20260924)
    s.add_argument("--output-prefix", default="pia")
    a = p.parse_args(argv)
    {"audit": cmd_audit, "permute": cmd_permute, "decompose": cmd_decompose}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
