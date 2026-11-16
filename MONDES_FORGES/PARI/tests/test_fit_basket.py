#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2 — fit basket MLE ridge. Centre verifie. Aucun parametre invente."""

import os
import sys
import tempfile
from datetime import datetime

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("F00_RADAR", "F02_BREACHER"):
    sys.path.insert(0, os.path.join(WORLD, d, "CODEBASE"))

import market_basket as mkb  # noqa: E402
import fit_basket as fb  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "basket_ok")
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 2 — fit_basket")
    print("=" * 70)

    rows, holes = mkb.load_dir(FIX)
    check("fit.fixtures_propres", len(rows) == 12 and holes == [])
    obs = fb.prepare(rows, as_of=datetime(2025, 6, 1))
    check("fit.observations", len(obs) == 12)
    check("fit.poids_temporel", 0.0 < obs[0]["weight"] <= 1.0)
    check("fit.marge_calculee", obs[0]["margin"] == 5)
    check("fit.poids_decroissant", obs[0]["weight"] < obs[-1]["weight"])

    blob = fb.fit(obs)
    check("fit.centre_residual", blob["center_residual"] <= 1e-6, str(blob["center_residual"]))
    check("fit.n_matches", blob["n_matches"] == 12)
    check("fit.sigma_positif", blob["sigma"] > 0, str(blob["sigma"]))
    check("fit.base", blob["base"] > 0, str(blob["base"]))
    check("fit.home_adv", blob["home_adv"] > 0, str(blob["home_adv"]))
    check("fit.4_equipes", len(blob["teams"]) == 4, str(sorted(blob["teams"])))
    check("fit.sans_trou", blob["holes"] == [], str(blob["holes"]))
    check("fit.contrat", blob["contract"] == "pari.basket_params.v1")

    pauvre = fb.prepare(rows + [{
        "game_id": "G999", "date": "2025-03-01", "home": "Nouveau",
        "away": "Lakers", "pts_home": 90, "pts_away": 100}], as_of=datetime(2025, 6, 1))
    bp = fb.fit(pauvre)
    check("fit.equipe_pauvre_trou", any(h.startswith("equipe_pauvre:Nouveau") for h in bp["holes"]),
          str(bp["holes"]))
    check("fit.equipe_pauvre_zero", bp["teams"]["Nouveau"]["rtg"] == 0.0)

    empty = fb.fit([])
    check("fit.aucun_match", empty["holes"] == ["aucun_match"] and empty["base"] is None)

    tmp = os.path.join(tempfile.mkdtemp(prefix="pari-fit-"), "params.json")
    out = fb.save_params(blob, tmp)
    check("fit.save", out == tmp and os.path.isfile(tmp))
    back = fb.load_params(tmp)
    check("fit.load_contrat", back is not None and back["base"] == blob["base"])
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('{"contract": "faux"}')
    check("fit.load_mauvais_contrat", fb.load_params(tmp) is None)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 2 fit : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
