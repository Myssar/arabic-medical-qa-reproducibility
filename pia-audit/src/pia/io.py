"""Readers for benchmark and permutation files."""
from __future__ import annotations

import json
from typing import Dict, List

import pandas as pd

from .rules import LABELS, Item


def read_benchmark(path: str, fmt: str = "generic") -> List[Item]:
    """generic: columns item_id, question, option_A ... option_F.
    medarabench: MedAraBench CSV (Question Number, Question, Option A ... Option F); ids become 'mab<number>'."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    items = []
    for _, r in df.iterrows():
        if fmt == "medarabench":
            iid, q = f"mab{int(float(r['Question Number']))}", r["Question"]
            col = lambda L: f"Option {L}"
        else:
            iid, q = r["item_id"], r["question"]
            col = lambda L: f"option_{L}"
        opts = {L: r[col(L)].strip() for L in LABELS if col(L) in df.columns and str(r[col(L)]).strip()}
        items.append(Item(iid, q, opts))
    return items


def read_permutations(path: str) -> Dict[str, Dict[str, str]]:
    """CSV with columns item_id, display_to_canonical (JSON object: displayed label -> canonical label)."""
    df = pd.read_csv(path, dtype=str)
    col = "display_to_canonical" if "display_to_canonical" in df.columns else "display_to_canonical_json"
    return {r.item_id: json.loads(getattr(r, col)) for r in df.itertuples()}


def write_permutations(perms: Dict[str, Dict[str, str]], path: str) -> None:
    pd.DataFrame([{"item_id": k, "display_to_canonical": json.dumps(v)} for k, v in perms.items()]).to_csv(path, index=False)
