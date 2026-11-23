#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_pmodel_basket — EV ML, devig, garde anti-EV délirant."""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F02_BREACHER", "F03_FORGEWARD", "F00_RADAR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import winner_pmodel_basket as wb  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


BLOB = {"base": 100.0, "home_adv": 2.0, "sigma": 12.0,
        "teams": {"Team A": {"off": 5.0, "rtg": 5.0},
                  "Team B": {"off": -5.0, "rtg": -5.0}}}
MATCH = {"match_key": "a_b", "home": "Team A", "away": "Team B",
         "odds": {"ml_1": 2.10, "ml_2": 1.80}}


def run_checks():
    PASS.clear()
    N[0] = 0
    r = wb.analyse(MATCH, BLOB)
    check("p_modele basket", r["p_modele"] is not None and 0 < r["p_modele"]["home"] < 1)
    check("EV = p*cote - 1", abs(r["ev"]["home"] -
          (r["p_modele"]["home"] * 2.10 - 1)) < 1e-5, str(r["ev"]))
    check("somme probabilites", abs(r["p_modele"]["home"] + r["p_modele"]["away"] - 1) < 1e-9)
    check("total diagnostic", r["total"]["diagnostic_only"] is True
          and r["total"]["p_over"] is None)
    check("pas de ticket", r["ticket"] is False)
    ko = wb.analyse({**MATCH, "home": "Inconnu"}, BLOB)
    check("equipe inconnue = trou", ko["p_modele"] is None and ko["holes"] != [])
    nocols = wb.analyse({**MATCH, "odds": {"ml_1": None}}, BLOB)
    check("cote absente = trou", nocols["p_modele"] is None)

    src = Path(wb.__file__).read_text(encoding="utf-8")
    ast.parse(src)
    check("garde discrimination", "discrimination_faible" in src
          and "ratio_dispersion" in src)
    check("stdlib", "import numpy" not in src and "import scipy" not in src)

    print(f"winner_pmodel_basket : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_pmodel_basket():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
