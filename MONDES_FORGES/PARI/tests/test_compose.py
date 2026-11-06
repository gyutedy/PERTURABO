#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 — EV compose net = produit (1+edge_net)-1. Zero reseau."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))

import combinator  # noqa: E402
import compose  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_produit_815():
    val, flags, holes = compose.ev_compose_net([0.03, 0.05])
    expected = 1.03 * 1.05 - 1
    check("cp.815", abs(val - expected) < 1e-15, str(val))
    check("cp.815_exact", abs(val - 0.0815) < 1e-12, str(val))
    check("cp.815_pas_round", val == expected)
    check("cp.815_flags", flags == [])
    check("cp.815_holes", holes == [])


def test_negatif_info_pas_rejet():
    val, flags, holes = compose.ev_compose_net([0.03, -0.02])
    expected = 1.03 * 0.98 - 1
    check("cp.neg_val", abs(val - expected) < 1e-15, str(val))
    check("cp.neg_flag", "jambe_edge_net_negatif" in flags, str(flags))
    check("cp.neg_pas_drop", val is not None)


def test_trou_pas_ev():
    val, flags, holes = compose.ev_compose_net([0.03, None, 0.05])
    expected = 1.03 * 1.05 - 1
    check("cp.trou_produit", abs(val - expected) < 1e-15, str(val))
    check("cp.trou_hole", "edge_net" in holes, str(holes))
    check("cp.trou_pas_zero", 0 not in (holes or []))


def test_vide():
    val, flags, holes = compose.ev_compose_net([])
    check("cp.vide_none", val is None)
    check("cp.vide_hole", "compose_vide" in holes, str(holes))
    val2, _, holes2 = compose.ev_compose_net([None])
    check("cp.none_only", val2 is None and "edge_net" in holes2)


def test_compose_ticket_stamp():
    jambes = [
        {"edge_net_devig": 0.03, "ev": 0.10},
        {"edge_net_devig": -0.01, "ev": 0.04},
    ]
    rec = compose.compose_ticket(jambes)
    check("cp.ticket_val", abs(rec["ev_compose_net"] - (1.03 * 0.99 - 1)) < 1e-15)
    check("cp.ticket_flag", "jambe_edge_net_negatif" in rec["compose_flags"])
    check("cp.stamp", jambes[1].get("jambe_edge_net_negatif") is True)
    check("cp.stamp_pos", "jambe_edge_net_negatif" not in jambes[0])


def test_allocate_compose_pas_rejet():
    events = [
        {
            "id": "M1", "match": "A vs B", "score_commun": 9.0, "rang_global": 1,
            "bucket": "HAUTE", "no_bet_recommande": False,
            "top3": [{"marche": "1X2", "selection": "1", "selection_label": "1",
                      "cote": 1.7, "p_modele": 0.70, "ev": 0.19, "edge_net_devig": 0.03}],
        },
        {
            "id": "M2", "match": "C vs D", "score_commun": 8.5, "rang_global": 2,
            "bucket": "HAUTE", "no_bet_recommande": False,
            "top3": [{"marche": "OU_2.5", "selection": "o2.5", "selection_label": "O2.5",
                      "cote": 1.9, "p_modele": 0.55, "ev": 0.045, "edge_net_devig": -0.02}],
        },
    ]
    res, wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        n_mesures=0)
    check("cp.alloc_tickets", len(res["tickets"]) == 1, str(len(res["tickets"])))
    t = res["tickets"][0]
    check("cp.alloc_2jambes", t["nb_jambes"] == 2, str(t["nb_jambes"]))
    expected = 1.03 * 0.98 - 1
    check("cp.alloc_compose", abs((t.get("ev_compose_net") or 0) - expected) < 1e-15,
          str(t.get("ev_compose_net")))
    check("cp.alloc_flag", "jambe_edge_net_negatif" in (t.get("compose_flags") or []))
    check("cp.alloc_pas_drop", all(j.get("match_id") for j in t["jambes"]))
    check("cp.ev_brute_inchangee",
          abs(t["jambes"][0]["ev"] - 0.19) < 1e-12 and abs(t["jambes"][1]["ev"] - 0.045) < 1e-12)


def main():
    print("=" * 70)
    print("TEST S5 — compose")
    print("=" * 70)
    test_produit_815()
    test_negatif_info_pas_rejet()
    test_trou_pas_ev()
    test_vide()
    test_compose_ticket_stamp()
    test_allocate_compose_pas_rejet()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S5 compose : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
