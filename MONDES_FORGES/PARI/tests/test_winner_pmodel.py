#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_pmodel — p_modele depuis fit_dc, EV vs cotes Winner, zero ticket."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F03_FORGEWARD", "F02_BREACHER", "F00_RADAR", "F01_SENTINEL"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import winner_pmodel as wp  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


TEAMS = {
    "Getafe": {"att": 0.0, "def": 0.0, "n": 30},
    "Ath Madrid": {"att": 0.2, "def": -0.1, "n": 30},
}
BLOB = {"leagues": {"SP1": {"params": "fitted", "mu": 0.2, "home_adv": 0.15,
                            "rho": -0.13, "teams": TEAMS}}}
MATCH = {"match_key": "getafe_ath", "home": "Getafe CF", "away": "Atletico Madrid",
         "odds": {"home": 6.50, "draw": 3.90, "away": 1.55}}


def run_checks():
    PASS.clear()
    N[0] = 0
    check("alias Atletico -> Ath Madrid", wp.resolve("Atletico Madrid", BLOB) ==
          ("SP1", "Ath Madrid"))
    check("alias suffixe CF", wp.resolve("Getafe CF", BLOB) == ("SP1", "Getafe"))
    check("equipe Celta B bloquee", wp.resolve("RC Celta Fortuna", BLOB)[1] is None)
    r = wp.analyse(MATCH, BLOB)
    check("p_modele present", r["p_modele"] is not None and sum(r["p_modele"].values()) > 0.99)
    check("EV = p*cote - 1", abs(r["ev"]["home"] -
          (r["p_modele"]["home"] * 6.50 - 1)) < 1e-5, str(r["ev"]))
    check("edge_net calcule", r["edge_net"]["home"] is not None)
    check("aucun ticket", r["ticket"] is False)
    missing = wp.analyse({**MATCH, "away": "Sparta Praga"}, BLOB)
    check("equipe absente = trou + pas de p",
          missing["p_modele"] is None and missing["holes"], str(missing["holes"]))
    nocols = wp.analyse({**MATCH, "odds": {"home": None}}, BLOB)
    check("cote absente = trou", nocols["p_modele"] is None)

    src = Path(wp.__file__).read_text(encoding="utf-8")
    ast.parse(src)
    check("pas_set_tickets", "set_tickets" not in src)
    check("stdlib", "import numpy" not in src and "import scipy" not in src)
    check("hors_hsh", "hsh_" not in src)

    print(f"winner_pmodel : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_pmodel():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
