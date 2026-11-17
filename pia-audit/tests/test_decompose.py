import pandas as pd

from pia import change_rates, specificity_ratio, transition_decomposition


def toy():
    rows = []
    # item 1: stable correct; item 2: flips with order only; item 3: flips with instruction only
    spec = {1: {"P0|O0": "A", "P0|O1": "A", "P1|O0": "A", "P1|O1": "A"},
            2: {"P0|O0": "A", "P0|O1": "B", "P1|O0": "A", "P1|O1": "B"},
            3: {"P0|O0": "A", "P0|O1": "A", "P1|O0": "C", "P1|O1": "C"}}
    for i, cells in spec.items():
        for cell, ans in cells.items():
            p, o = cell.split("|")
            rows.append({"item_id": i, "model": "m", "prompt": p, "order": o, "answer": ans, "correct": int(ans == "A")})
    return pd.DataFrame(rows)


def test_change_rates_and_rho():
    r = change_rates(toy()).mean()
    assert abs(r["order_change_P0"] - 1 / 3) < 1e-9 and abs(r["instruction_change_O0"] - 1 / 3) < 1e-9
    rho = specificity_ratio(toy(), n_boot=50).iloc[0]
    assert abs(rho.rho - 1.0) < 1e-9


def test_decomposition_identity():
    d = transition_decomposition(toy(), "order")
    row = d[d.fixed_level == "P0"].iloc[0]
    assert abs(row.answer_change_rate - (row.correct_to_incorrect + row.incorrect_to_correct + row.different_incorrect)) < 1e-12
    assert abs(row.correct_to_incorrect - 1 / 3) < 1e-9
