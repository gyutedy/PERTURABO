#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cahier B — ticket systeme 2/3. 3 jambes exactement, jamais de cote estimee."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))

import combinator as c  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def jambes():
    return [("M1", "1X2", "1", 2.0, 0.55),
            ("M2", "MT_PROLIFIQUE", "total_over", 1.8, 0.60),
            ("M3", "1X2", "2", 3.0, 0.40)]


def main():
    print("=" * 70)
    print("TEST Cahier B — build_system23")
    print("=" * 70)

    out = c.build_system23(jambes(), 100.0)
    check("s23.type", out["type"] == "systeme_2_3")
    check("s23.trois_doubles", len(out["doubles"]) == 3)
    paires = [(d["jambes"][0][0], d["jambes"][1][0]) for d in out["doubles"]]
    check("s23.paires", paires == [("M1", "M2"), ("M1", "M3"), ("M2", "M3")], str(paires))
    check("s23.cotes", [d["cote"] for d in out["doubles"]] == [3.6, 6.0, 5.4],
          str([d["cote"] for d in out["doubles"]]))
    check("s23.mise_totale", out["mise_totale"] == 300.0)
    check("s23.p_conjointe", out["p_conjointe"] == 0.132, str(out["p_conjointe"]))
    check("s23.gain_3_3", out["gain_si_3_3"] == 1500.0, str(out["gain_si_3_3"]))
    check("s23.gains_2_3", len(out["gain_si_2_3_par_paire"]) == 3)
    check("s23.perte", out["perte_si_1_3"] == 300.0)

    dec = c.build_system23(jambes(), 100.0, corr_decote=0.9)
    check("s23.decote", dec["p_conjointe"] == 0.1188, str(dec["p_conjointe"]))

    def refuse(label, js):
        raised = False
        try:
            c.build_system23(js, 100.0)
        except ValueError:
            raised = True
        check(label, raised)

    refuse("s23.refus_2_jambes", jambes()[:2])
    refuse("s23.refus_4_jambes", jambes() + [("M4", "1X2", "1", 2.0, 0.5)])
    js = jambes(); js[0] = ("M1", "1X2", "1", None, 0.55)
    refuse("s23.refus_cote_absente", js)
    js = jambes(); js[0] = ("M1", "1X2", "1", 1.0, 0.55)
    refuse("s23.refus_cote_1", js)
    js = jambes(); js[1] = ("M2", "MT", "o2.5", 1.8, None)
    refuse("s23.refus_p_absente", js)
    js = jambes(); js[2] = ("M3", "1X2", "2", 3.0, 1.0)
    refuse("s23.refus_p_1", js)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Cahier B systeme 2/3 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
