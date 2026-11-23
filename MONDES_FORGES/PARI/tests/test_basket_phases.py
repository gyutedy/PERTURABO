#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase 1/5 : fenetre fit, prior marche desactive, paper basket bloque."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F02_BREACHER", "F06_TRACKER", "F00_RADAR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import fit_basket  # noqa: E402
import basket_prior  # noqa: E402
import paper_trader  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


ROWS = [
    {"date": "2023-01-01", "home": "A", "away": "B", "pts_home": 100, "pts_away": 90,
     "odds_home": 1.5, "odds_away": 2.6},
    {"date": "2024-01-01", "home": "A", "away": "B", "pts_home": 105, "pts_away": 99,
     "odds_home": 1.6, "odds_away": 2.4},
]


def run_checks():
    PASS.clear()
    N[0] = 0
    cfg = fit_basket._cfg()
    check("fenetre par defaut", cfg["window_days"] == 540.0)
    obs = fit_basket.prepare(ROWS)
    b = fit_basket.fit(obs)
    check("metadata fit", b["n_matches"] == 2 and b["n_raw"] == 2)
    check("convergence visible", "n_iter" in b and "grad_final" in b and "converged" in b)
    src = Path(fit_basket.__file__).read_text(encoding="utf-8")
    check("fenetre dans le code", "window_days" in src and "wmin" in src)

    pblob = basket_prior.fit(ROWS, lambda r: [1.0, 0.0, 0.0, 0.0, 0.0], cutoff="2024-06-01")
    check("prior desactive", pblob["enabled"] is False and pblob["verdict"] in ("GO", "NO-GO"))
    check("prior jamais producteur", "producteur de p" in Path(basket_prior.__file__).read_text(encoding="utf-8"))

    rec = paper_trader.record_basket(source=str(WORLD / "inexistant.json"))
    check("paper basket bloque", rec["skipped"] == "modele_non_valide" and rec["ajoutes"] == [])
    ast.parse(src)

    print(f"basket_phases : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_basket_phases():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
