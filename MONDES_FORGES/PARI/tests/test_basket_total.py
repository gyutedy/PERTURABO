#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""basket_total — total des DEUX equipes, sigma OOS, zero data."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F02_BREACHER", "F00_RADAR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import basket_total as bt  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


ROWS = [
    {"date": "2026-01-01", "home": "A", "away": "B", "pts_home": 110, "pts_away": 100},
    {"date": "2026-01-03", "home": "B", "away": "A", "pts_home": 105, "pts_away": 112},
    {"date": "2026-01-05", "home": "A", "away": "B", "pts_home": 118, "pts_away": 108},
]


def run_checks():
    PASS.clear()
    N[0] = 0
    st = bt.state_at(ROWS, "2026-01-04")
    check("state sans fuite", "A" in st and st["A"]["last"] == "2026-01-03")
    f = bt.features("A", "B", "2026-01-04", st, 210.0)
    check("features", f is not None and len(f) == 3 and f[0] == 1.0)
    old_train, old_test = bt.CUTOFF_TRAIN, bt.CUTOFF_TEST
    bt.CUTOFF_TRAIN, bt.CUTOFF_TEST = "2026-01-05", "2026-01-07"
    try:
        b = bt.fit(ROWS)
    finally:
        bt.CUTOFF_TRAIN, bt.CUTOFF_TEST = old_train, old_test
    check("sigma OOS", b["sigma_total"] is not None and b["sigma_total"] > 0, str(b))
    check("intercept non penalise", b["weights"][0] > 200, str(b["weights"]))
    check("pas de ticket", b["tickets_enabled"] is False)
    po = bt.p_over(b, "A", "B", "2026-01-06", st, 220.5)
    check("p_over", po is not None and 0 < po < 1, str(po))
    src = Path(bt.__file__).read_text(encoding="utf-8")
    ast.parse(src)
    check("stdlib", "import numpy" not in src and "import scipy" not in src)

    print(f"basket_total : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_basket_total():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
