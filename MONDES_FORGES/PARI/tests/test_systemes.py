#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F05 — systemes S2/S3/S4 + regression S1. Variance faconnee, marge intacte."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("F05_PACKAGER", "F02_BREACHER", "ORCHESTRATOR"):
    sys.path.insert(0, os.path.join(WORLD, d, "CODEBASE"))

import systemes as sy  # noqa: E402
import combinator as co  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok)))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST F05 — systemes S1-S4")
    print("=" * 70)

    legs = [
        ("M1", "1X2", "1", 2.42, 0.52),
        ("M2", "1X2", "2", 2.16, 0.51),
        ("M3", "1X2", "1", 1.84, 0.60),
    ]

    s1 = co.build_system23(legs[:3], mise_par_double=100)
    check("sys.s1_type", s1["type"] == "systeme_2_3")
    check("sys.s1_doubles", len(s1["doubles"]) == 3)
    check("sys.s1_mise", s1["mise_totale"] == 300)

    s2 = sy.build_dutching2(legs[:2], 3000)
    check("sys.s2_type", s2["type"] == "dutching_2")
    check("sys.s2_retour", abs(s2["retour_si_une_gagne"] - 3424.0) < 0.1,
          str(s2["retour_si_une_gagne"]))
    check("sys.s2_gain", abs(s2["gain_si_une"] - 424.0) < 0.2
          and abs(s2["gain_si_deux"] - 3848.0) < 0.2)
    check("sys.s2_break_even", abs(s2["p_break_even_par_jambe"] - 0.4381) < 0.001,
          str(s2["p_break_even_par_jambe"]))
    check("sys.s2_perte", s2["perte_si_aucune"] == 3000.0)
    refused = False
    try:
        sy.build_dutching2([legs[0], ("M1", "1X2", "2", 1.55, 0.6)], 1000)
    except ValueError:
        refused = True
    check("sys.s2_meme_match_refuse", refused)

    over = ("M4", "total_over", 214.5, 1.83, 0.27)
    under = ("M4", "total_under", 220.5, 1.84, 0.63)
    s3 = sy.build_corridor(over, under, 1500, 0.10)
    check("sys.s3_type", s3["type"] == "corridor")
    check("sys.s3_gain_both", s3["gain_si_les_deux"] == 2505.0,
          str(s3["gain_si_les_deux"]))
    check("sys.s3_pire_cas", s3["perte_si_un_seul"] == -255.0,
          str(s3["perte_si_un_seul"]))
    refused = False
    try:
        sy.build_corridor(over, ("M4", "total_under", 210.5, 1.84, 0.6), 100, 0.1)
    except ValueError:
        refused = True
    check("sys.s3_ligne_vide_refusee", refused)
    refused = False
    try:
        sy.build_corridor(over, under, 100, None)
    except ValueError:
        refused = True
    check("sys.s3_p_corridor_requise", refused)

    s4 = sy.build_tri_lettre(legs[2], legs[:2], 100)
    check("sys.s4_type", s4["type"] == "pivot_couvert")
    check("sys.s4_mise", s4["mise_totale"] == 400.0)
    check("sys.s4_perte_plafonnee", abs(s4["perte_si_pivot_seul"] + 32.0) < 0.01,
          str(s4["perte_si_pivot_seul"]))

    for name, fn in (("s2", lambda: sy.build_dutching2(
                         [("M1", "1X2", "1", None, 0.5), legs[1]], 100)),
                     ("s3", lambda: sy.build_corridor(
                         ("M4", "total_over", 214.5, 1.0, 0.5), under, 100, 0.1)),
                     ("s4", lambda: sy.build_tri_lettre(
                         legs[2], [legs[0], legs[0]], 100))):
        refused = False
        try:
            fn()
        except ValueError:
            refused = True
        check("sys." + name + "_zero_data_refuse", refused)

    import workflow
    check("sys.commande_enregistree", "systeme" in workflow.CMDS)
    check("sys.workflow_importe_systemes", os.path.isfile(
        os.path.join(WORLD, "F05_PACKAGER", "CODEBASE", "systemes.py")))

    ok = all(v for _, v in CHECKS)
    print("=" * 70)
    print(f"RESULTAT: {sum(v for _, v in CHECKS)}/{len(CHECKS)} " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
