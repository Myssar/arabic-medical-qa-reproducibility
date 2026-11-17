"""Permutation generators: the conventional free shuffle and the integrity-preserving 'safe' shuffle."""
from __future__ import annotations

import random
from typing import Dict, List

from .rules import Item, explicit_referents, has_positional


def free_permutation(item: Item, rng: random.Random) -> Dict[str, str]:
    """Shuffle all options; never returns the identity when two or more options exist."""
    labels = item.labels()
    canon = labels[:]
    for _ in range(100):
        rng.shuffle(canon)
        if canon != labels or len(labels) < 2:
            break
    else:
        canon = labels[1:] + labels[:1]
    return dict(zip(labels, canon))


def pinned_labels(item: Item, vocab: str = "paper") -> set:
    """Options that must keep their position: explicit-reference options, the options they name,
    and options with positional wording."""
    pins = set()
    for label, text in item.options.items():
        refs = [r for r in explicit_referents(text) if r in item.options]
        if refs:
            pins.add(label)
            pins.update(refs)
        if has_positional(text, vocab):
            pins.add(label)
    return pins


def safe_permutation(item: Item, rng: random.Random, vocab: str = "paper") -> Dict[str, str]:
    """Shuffle only options that can move without changing meaning.

    Pinned options stay in place, and movable options are shuffled only within the segment between
    pinned positions, so every positional option keeps the same preceding set. Returns the identity
    map when nothing can move (report such items as 'not permutable')."""
    labels = item.labels()
    pins = pinned_labels(item, vocab)
    result = labels[:]
    segment: List[int] = []

    def flush():
        if len(segment) > 1:
            vals = [labels[i] for i in segment]
            for _ in range(100):
                rng.shuffle(vals)
                if vals != [labels[i] for i in segment]:
                    break
            for i, v in zip(segment, vals):
                result[i] = v
        segment.clear()

    for i, lab in enumerate(labels):
        if lab in pins:
            flush()
        else:
            segment.append(i)
    flush()
    return dict(zip(labels, result))


def is_identity(d2c: Dict[str, str]) -> bool:
    return all(k == v for k, v in d2c.items())
