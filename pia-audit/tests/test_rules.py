import random

from pia import Item, audit, safe_permutation, free_permutation, is_identity

VIT = Item("v1", "أي مما يلي من الفيتامينات الذائبة في الدهون؟",
           {"A": "فيتامين د", "B": "فيتامين ك", "C": "فيتامين ج", "D": "A+B"})
ALL = Item("t1", "من أعراض قصور الغدة الدرقية:",
           {"A": "زيادة الوزن", "B": "عدم تحمّل البرد", "C": "الإمساك", "D": "كل ما سبق"})
PLAIN = Item("p1", "أي مما يلي هرمون تفرزه الغدة النخامية الأمامية؟",
             {"A": "الإنسولين", "B": "هرمون النمو", "C": "الغلوكاغون", "D": "الألدوستيرون"})
DUP = Item("d1", "سؤال", {"A": "نعم", "B": "لا", "C": "نعم "})


def flags(item, d2c, **kw):
    return audit([item], {item.item_id: d2c}, **kw)[0]


def test_r1_changed_reference():
    # displayed A,B,C,D show canonical C,A,B,D: "A+B" now points to C and A
    r = flags(VIT, {"A": "C", "B": "A", "C": "B", "D": "D"})
    assert r.r1_changed_reference and not r.r2_changed_positional_scope


def test_r1_preserved_when_referents_swap_among_themselves():
    r = flags(VIT, {"A": "B", "B": "A", "C": "C", "D": "D"})
    assert not r.r1_changed_reference


def test_r1_new_self_reference():
    # the "A+B" option itself is displayed as A
    r = flags(VIT, {"A": "D", "B": "C", "C": "A", "D": "B"})
    assert r.r1_changed_reference and r.r1_new_self_reference


def test_r2_positional_scope():
    r = flags(ALL, {"A": "D", "B": "C", "C": "A", "D": "B"})
    assert r.r2_changed_positional_scope
    assert not flags(ALL, {"A": "B", "B": "C", "C": "A", "D": "D"}).r2_changed_positional_scope


def test_r3_and_plain():
    assert flags(DUP, {"A": "A", "B": "B", "C": "C"}).r3_identical_option_text
    assert not flags(PLAIN, {"A": "D", "B": "A", "C": "B", "D": "C"}).flagged


def test_r4_overlap():
    twin = Item("x9", PLAIN.question, dict(PLAIN.options))
    r = audit([PLAIN], {}, reference=[twin])[0]
    assert r.r4_cross_sample_overlap


def test_extended_vocab():
    it = Item("e1", "q", {"A": "a", "B": "b", "C": "c", "D": "كل ما ذكر صحيح"})
    d2c = {"A": "D", "B": "A", "C": "B", "D": "C"}
    assert not flags(it, d2c).r2_changed_positional_scope
    assert flags(it, d2c, vocab="extended").r2_changed_positional_scope


def test_safe_permutation_never_flags():
    rng = random.Random(1)
    for it in (VIT, ALL, PLAIN):
        for _ in range(200):
            r = flags(it, safe_permutation(it, rng))
            assert not (r.r1_changed_reference or r.r2_changed_positional_scope)
    assert not is_identity(safe_permutation(PLAIN, rng))


def test_free_permutation_not_identity():
    rng = random.Random(2)
    assert all(not is_identity(free_permutation(PLAIN, rng)) for _ in range(50))
