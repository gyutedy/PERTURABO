#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""basket_calib — features repos/forme, ridge, verdict backtest."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F02_BREACHER", "F00_RADAR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import basket_calib as bc  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


ROWS = [
    {"date": "2024-01-01", "home": "A", "away": "B", "pts_home": 100, "pts_away": 90,
     "odds_home": 1.5, "odds_away": 2.6},
    {"date": "2024-01-03", "home": "B", "away": "A", "pts_home": 95, "pts_away": 110,
     "odds_home": 2.2, "odds_away": 1.7},
    {"date": "2024-01-05", "home": "A", "away": "B", "pts_home": 105, "pts_away": 99,
     "odds_home": 1.6, "odds_away": 2.4},
]


def run_checks():
    PASS.clear()
    N[0] = 0
    last, diffs = bc.state_at(ROWS, "2024-01-04")
    check("state sans fuite", "2024-01-03" in last.values() and "2024-01-05" not in last.values())
    f = bc.features("A", "B", "2024-01-04", last, diffs, {"A": {"rtg": 1.0}, "B": {"rtg": -1.0}})
    check("5 features", len(f) == 5 and f[0] == 1.0 and f[1] == 2.0, str(f))
    check("tokens", abs(f[4] - 1.0) < 1e-9)
    blob = bc.fit(ROWS, {"A": {"rtg": 1.0}, "B": {"rtg": -1.0}}, cutoff="2024-01-05")
    check("poids", len(blob["weights"]) == 5)
    check("verdict present", blob["verdict"] in ("GO", "NO-GO"))
    check("aucun ticket", blob["tickets_enabled"] is False)
    m, holes = bc.predict_margin(blob, "A", "B", "2024-01-06", last, diffs,
                                 {"A": {"rtg": 1.0}, "B": {"rtg": -1.0}})
    check("marge predite", m is not None and isinstance(m, float))
    src = Path(bc.__file__).read_text(encoding="utf-8")
    ast.parse(src)
    check("stdlib", "import numpy" not in src and "import scipy" not in src)

    print(f"basket_calib : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_basket_calib():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
