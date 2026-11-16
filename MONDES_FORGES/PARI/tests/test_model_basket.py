#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2 — modeles de score basket (fonctions pures, seed reproductible)."""

import math
import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import model_basket as mb  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 2 — model_basket")
    print("=" * 70)

    check("mb.cdf_zero", abs(mb.norm_cdf(0.0) - 0.5) < 1e-12)
    refused = False
    try:
        mb.norm_cdf(0.0, sigma=0)
    except ValueError:
        refused = True
    check("mb.sigma_nul_refuse", refused)
    check("mb.margin", mb.expected_margin(2.0, -1.0, 2.5) == 5.5)
    mh, ma = mb.expected_totals(110.0, 2.0, -1.0, 1.0, -2.0)
    check("mb.totals", mh == 110.0 and ma == 110.0, f"{mh}/{ma}")
    check("mb.home_favori", mb.p_home_win(110.0, 100.0, 12.0) > 0.5)
    check("mb.over_ligne_haute", mb.p_total_over(110.0, 100.0, 12.0, 400.0) < 0.01)
    check("mb.spread", 0.0 < mb.p_spread_home(110.0, 100.0, 12.0, -1.5) < 1.0)

    m1, n1 = mb.simulate_matrix(110.0, 100.0, 12.0, sims=500, seed=42)
    m2, n2 = mb.simulate_matrix(110.0, 100.0, 12.0, sims=500, seed=42)
    check("mb.seed_reproductible", m1 == m2 and n1 == n2 == 500)
    check("mb.proba_somme_un", abs(sum(m1.values()) - 1.0) < 1e-9)

    st = mb.matrix_stats(m1, n1)
    check("mb.cles", set(st.keys()) == {"1", "2", "total_over", "total_under", "spread_home", "_n"},
          str(sorted(st.keys())))
    check("mb.pas_de_nul", "X" not in st)
    check("mb.over_under", abs(st["total_over"] + st["total_under"] - 1.0) < 1e-3)
    check("mb.n_trace", st["_n"] == 500)

    cfg = {"mc_sims": 400, "spread_line": -2.5}
    p = mb.probas_from(110.0, 100.0, 12.0, cfg=cfg, seed=7)
    check("mb.probas_from", p["_n"] == 400 and "spread_home" in p)
    check("mb.time_weight", mb.time_weight(0) == 1.0 and abs(mb.time_weight(45) - 0.5) < 1e-12)
    check("mb.half_life_invalide", mb.time_weight(10, half_life=0) == 1.0)

    refused = False
    try:
        mb.simulate_matrix(110, 100, 12, sims=0)
    except ValueError:
        refused = True
    check("mb.sims_nuls_refuses", refused)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 2 model : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
