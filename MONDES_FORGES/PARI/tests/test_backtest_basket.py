#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 — backtest basket OOS. Split strict, portes uniques, jamais de GO invente."""

import json
import os
import sys
import tempfile
from datetime import date

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("F00_RADAR", "F02_BREACHER"):
    sys.path.insert(0, os.path.join(WORLD, d, "CODEBASE"))

import backtest_basket as bt  # noqa: E402
import fit_basket as fb  # noqa: E402
import market_basket as mkb  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "basket_ok")
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 3 — backtest_basket")
    print("=" * 70)

    check("bt.cutoff_parse", bt.parse_cutoff("2025-01-01") == date(2025, 1, 1))
    check("bt.cutoff_vide", bt.parse_cutoff("") is None)

    rows, holes = mkb.load_dir(FIX)
    train, test = bt.split_cutoff(rows, bt.parse_cutoff("2025-01-01"))
    check("bt.split_train", len(train) == 8, str(len(train)))
    check("bt.split_test", len(test) == 4, str(len(test)))
    ids_train = {r["game_id"] for r in train}
    ids_test = {r["game_id"] for r in test}
    check("bt.split_strict", not (ids_train & ids_test))
    check("bt.sans_cutoff", len(bt.split_cutoff(rows, None)[1]) == 0)

    mk = bt.implied_2way(2.0, 3.0)
    check("bt.devig_somme", mk is not None and abs(mk[0] + mk[1] - 1.0) < 1e-12)
    check("bt.cote_invalide", bt.implied_2way(1.0, 3.0) is None)
    check("bt.cote_texte", bt.implied_2way("x", "3.0") is None)
    check("bt.brier_parfait", bt.brier(1.0, True) == 0.0)
    check("bt.brier_echec", bt.brier(0.0, True) == 1.0)

    gates = bt.moteur_flag.gates(bt.moteur_sport_cfg()) or {}
    check("bt.gates_min_300", int(gates.get("min_matches_oos") or 0) == 300)
    check("bt.gates_ece", float(gates.get("ece_max") or 9) == 0.03)
    bg = gates.get("brier_gap_max")
    check("bt.gates_brier", bg is not None and float(bg) == 0.0, str(bg))

    tmp = tempfile.mkdtemp(prefix="pari-bt-")
    out_path = os.path.join(tmp, "calibration_basket.json")
    params_path = os.path.join(tmp, "basket_params.json")
    old_out, old_params = bt.DEFAULT_OUT, fb.DEFAULT_OUT
    try:
        bt.DEFAULT_OUT, fb.DEFAULT_OUT = out_path, params_path
        rec = bt.run("2025-01-01", FIX)
        check("bt.contrat", rec["contract"] == "pari.calibration_basket.v1")
        check("bt.n_oos", rec["n_oos"] == 4, str(rec["n_oos"]))
        check("bt.fichier_ecrit", os.path.isfile(out_path))
        check("bt.brier_modele", isinstance(rec["brier_modele"], float))
        check("bt.brier_gap_none", rec["brier_gap"] is None, str(rec["brier_gap"]))
        check("bt.marche_absent", any("marche_absent" in h for h in rec["holes"]),
              str(rec["holes"][:3]))
        check("bt.verdict_pas_go", rec["verdict"] is None or rec["verdict"] == "NO-GO",
              str(rec["verdict"]))
        saved = json.load(open(out_path, encoding="utf-8"))
        check("bt.contenu_fichier", saved["n_oos"] == 4 and saved["contract"] == rec["contract"])

        rec2 = bt.run(None, FIX)
        check("bt.test_vide", "test_vide" in rec2["holes"] and rec2["n_oos"] == 0,
              str(rec2["holes"][:3]))

        rec3 = bt.run("2025-01-01", os.path.join(tmp, "dir-absent"))
        check("bt.dossier_absent", any("dossier_absent" in h for h in rec3["holes"]))
        check("bt.verdict_sans_donnee", rec3["verdict"] is None, str(rec3["verdict"]))

        FIX_O = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "basket_odds")
        reco = bt.run("2025-01-01", FIX_O)
        check("bt.brier_gap_calcule", isinstance(reco["brier_gap"], float), str(reco["brier_gap"]))
        check("bt.brier_marche_calcule", isinstance(reco["brier_marche"], float))
        check("bt.pas_marche_absent", not any("marche_absent" in h for h in reco["holes"]),
              str(reco["holes"][:3]))
        check("bt.pas_trou_logloss", "logloss" not in reco["holes"], str(reco["holes"][:3]))
        check("bt.verdict_n_insuffisant", reco["verdict"] is None and any("n_oos" in h for h in reco["holes"]),
              str(reco["verdict"]))

        go = bt.backtest_market.apply_gates(300, -0.01, 0.02, -0.01, gates=gates)
        check("bt.go_atteignable", go["verdict"] == "GO", str(go))
        nog = bt.backtest_market.apply_gates(300, 0.01, 0.02, 0.01, gates=gates)
        check("bt.nogo_si_gap_positif", nog["verdict"] == "NO-GO", str(nog["verdict"]))
    finally:
        bt.DEFAULT_OUT, fb.DEFAULT_OUT = old_out, old_params

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 3 backtest : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
