"""Permutation integrity audit (PIA): rules R1-R4.

Terminology
-----------
canonical label : the option's label in the benchmark's original order (A, B, C, ...).
displayed label : the label the option carries after permutation.
permutation map : dict displayed label -> canonical label (``d2c``).

R1  explicit reference   An option names other options by letter ("A+B", "C و D") and the permutation
                         changes the set of options those letters point to.
R2  positional scope     An option uses positional wording ("كل ما سبق", "all of the above") and the set of
                         options displayed before it changes.
R3  distinctness         Two options are identical after normalization.
R4  cross-sample overlap The item's normalized stem and labelled options duplicate an item in a reference sample.

The default ``paper`` vocabulary reproduces the register reported in the accompanying article exactly.
``extended`` adds further Arabic and English positional phrases (e.g. "كل ما ذكر", "جميع الإجابات").
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional

LABELS = "ABCDEF"

# Two explicit Latin A-F references joined by a conjunction or separator (as in the original audit).
EXPLICIT_REFERENCE = re.compile(r"(?<![A-Za-z])([A-F])\s*(?:[+&,/،]|و)\s*([A-F])(?![A-Za-z])", re.I)

POSITIONAL_VOCAB: Dict[str, str] = {
    "paper": r"سبق|السابق|above|previous",
    "extended": r"سبق|السابق|ما\s*ذُ?كر|المذكور|أعلاه|(?:كل|جميع|كافة)\s+(?:ال)?[إاأ]جابات|all of the|none of the|above|previous",
}


def normalize(text: str) -> str:
    """Unicode NFC and whitespace normalization (used by R3 and R4)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(text))).strip()


@dataclass
class Item:
    item_id: str
    question: str
    options: Dict[str, str]  # canonical label -> text, in canonical order

    def labels(self) -> List[str]:
        return list(self.options.keys())


@dataclass
class ItemAudit:
    item_id: str
    r1_changed_reference: bool = False
    r1_new_self_reference: bool = False
    r2_changed_positional_scope: bool = False
    r3_identical_option_text: bool = False
    r4_cross_sample_overlap: bool = False
    details: List[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return (self.r1_changed_reference or self.r2_changed_positional_scope
                or self.r3_identical_option_text or self.r4_cross_sample_overlap)

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "r1_changed_reference": self.r1_changed_reference,
            "r1_new_self_reference": self.r1_new_self_reference,
            "r2_changed_positional_scope": self.r2_changed_positional_scope,
            "r3_identical_option_text": self.r3_identical_option_text,
            "r4_cross_sample_overlap": self.r4_cross_sample_overlap,
            "any_flag": self.flagged,
            "details": " | ".join(self.details),
        }


def explicit_referents(text: str) -> List[str]:
    return sorted({x.upper() for m in EXPLICIT_REFERENCE.finditer(str(text)) for x in m.groups()})


def has_positional(text: str, vocab: str = "paper") -> bool:
    return re.search(POSITIONAL_VOCAB[vocab], str(text), re.I) is not None


def check_r1(item: Item, d2c: Mapping[str, str]) -> tuple[bool, bool, List[str]]:
    c2d = {c: d for d, c in d2c.items()}
    changed, self_ref, notes = False, False, []
    for label, text in item.options.items():
        refs = explicit_referents(text)
        if not refs:
            continue
        if {c2d.get(r, r) for r in refs} != set(refs):
            changed = True
            notes.append(f"R1: option {label} ('{text}') refers to {'+'.join(refs)}, which now point to other options")
        if label not in refs and c2d[label] in refs:
            self_ref = True
            notes.append(f"R1: option {label} now carries label {c2d[label]} and refers to itself")
    return changed, self_ref, notes


def check_r2(item: Item, d2c: Mapping[str, str], vocab: str = "paper") -> tuple[bool, List[str]]:
    labels = item.labels()
    c2d = {c: d for d, c in d2c.items()}
    shown = sorted(d2c)  # displayed labels in display order
    notes, changed = [], False
    for label, text in item.options.items():
        if not has_positional(text, vocab):
            continue
        before = set(labels[: labels.index(label)])
        after = {d2c[d] for d in shown[: shown.index(c2d[label])]}
        if before != after:
            changed = True
            notes.append(f"R2: option {label} ('{text}') is preceded by different options after permutation")
    return changed, notes


def check_r3(item: Item) -> tuple[bool, List[str]]:
    texts = [normalize(t) for t in item.options.values()]
    dup = len(set(texts)) < len(texts)
    return dup, (["R3: two or more options are identical after normalization"] if dup else [])


def signature(item: Item) -> tuple:
    return (normalize(item.question), tuple((k, normalize(v)) for k, v in item.options.items()))


def audit(items: Iterable[Item], permutations: Mapping[str, Mapping[str, str]],
          reference: Optional[Iterable[Item]] = None, vocab: str = "paper") -> List[ItemAudit]:
    """Audit every item against its permutation map; optionally check overlap with a reference sample."""
    if vocab not in POSITIONAL_VOCAB:
        raise ValueError(f"vocab must be one of {sorted(POSITIONAL_VOCAB)}")
    ref_sigs = {signature(r): r.item_id for r in reference} if reference is not None else {}
    out = []
    for it in items:
        a = ItemAudit(it.item_id)
        d2c = permutations.get(it.item_id)
        if d2c is not None:
            if sorted(d2c.values()) != sorted(it.labels()) or sorted(d2c) != sorted(it.labels()):
                raise ValueError(f"{it.item_id}: permutation labels do not match the item's options")
            a.r1_changed_reference, a.r1_new_self_reference, n1 = check_r1(it, d2c)
            a.r2_changed_positional_scope, n2 = check_r2(it, d2c, vocab)
            a.details += n1 + n2
        a.r3_identical_option_text, n3 = check_r3(it)
        a.details += n3
        other = ref_sigs.get(signature(it))
        if other is not None and other != it.item_id:
            a.r4_cross_sample_overlap = True
            a.details.append(f"R4: same content as reference item {other}")
        out.append(a)
    return out
