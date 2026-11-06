#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 — market_priority paliers + corners/cards holes. Zero reseau."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))

import combinator  # noqa: E402
import market_priority as prio  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _cfg():
    return prio.load_config(os.path.join(WORLD, "config", "market_priority.json"))


def test_config():
    cfg = _cfg()
    check("mp.min30", cfg.get("min_tickets_mesures") == 30, str(cfg.get("min_tickets_mesures")))
    check("mp.fermes", "corners" in cfg.get("fermes_sans_data") and "cards" in cfg.get("fermes_sans_data"))
    ids = [p["id"] for p in cfg["paliers"]]
    check("mp.paliers_012", ids == [0, 1, 2], str(ids))


def test_palier_gate():
    check("mp.p0_n0", prio.palier_ouvert(0, 0) is True)
    check("mp.p1_n29", prio.palier_ouvert(1, 29) is False)
    check("mp.p1_n30", prio.palier_ouvert(1, 30) is True)
    check("mp.p2_n30", prio.palier_ouvert(2, 30) is False)
    check("mp.p2_n60", prio.palier_ouvert(2, 60) is True)


def test_status_paliers():
    cfg = _cfg()
    s0 = prio.marche_status("1X2", n=0, cfg=cfg)
    check("mp.1x2_open0", s0.get("open") is True and s0.get("palier") == 0, str(s0))
    s1 = prio.marche_status("OU_1.5", n=29, cfg=cfg)
    check("mp.ou15_ferme29", s1.get("open") is False and "palier_ferme" in s1.get("holes"), str(s1))
    s1b = prio.marche_status("OU_1.5", n=30, cfg=cfg)
    check("mp.ou15_open30", s1b.get("open") is True and s1b.get("holes") == [], str(s1b))
    s2 = prio.marche_status("CS", n=30, cfg=cfg)
    check("mp.cs_ferme30", s2.get("open") is False, str(s2))
    s2b = prio.marche_status("CS", n=60, cfg=cfg)
    check("mp.cs_open60", s2b.get("open") is True, str(s2b))


def test_corners_cards_holes():
    cfg = _cfg()
    for name in ("corners", "cards", "CORNERS", "Cards"):
        st = prio.marche_status(name, n=999, cfg=cfg)
        check("mp.ferme_" + name.lower(), st.get("open") is False, str(st))
        check("mp.sans_data_" + name.lower(), "sans_data" in (st.get("holes") or []), str(st.get("holes")))
        check("mp.palier_none_" + name.lower(), st.get("palier") is None)


def test_n_mesures_zero_data():
    n = prio.n_tickets_mesures(lots_box={"lots": []})
    check("mp.n0_vide", n == 0)
    n2 = prio.n_tickets_mesures(lots_path="/no/such/lots.json")
    check("mp.n0_absent", n2 == 0)
    box = {"lots": [{"settle": {"tickets": [
        {"resultat": "G"}, {"resultat": "P"}, {"resultat": "EN_ATTENTE"},
    ]}}]}
    n3 = prio.n_tickets_mesures(lots_box=box)
    check("mp.n_gp_pas_attente", n3 == 2, str(n3))


def test_allocate_stamp_ferme():
    events = [
        {
            "id": "M1", "match": "A vs B", "score_commun": 9.0, "rang_global": 1,
            "bucket": "HAUTE", "no_bet_recommande": False,
            "top3": [{"marche": "corners", "selection": "over", "selection_label": "corners",
                      "cote": 1.8, "p_modele": 0.60, "ev": 0.08, "edge_net_devig": 0.04}],
        },
        {
            "id": "M2", "match": "C vs D", "score_commun": 8.0, "rang_global": 2,
            "bucket": "HAUTE", "no_bet_recommande": False,
            "top3": [{"marche": "1X2", "selection": "1", "selection_label": "1",
                      "cote": 1.7, "p_modele": 0.70, "ev": 0.19, "edge_net_devig": 0.03}],
        },
    ]
    res, _ = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        n_mesures=0)
    check("mp.alloc_existe", len(res["tickets"]) == 1)
    jambes = res["tickets"][0]["jambes"]
    corn = next(j for j in jambes if j["marche"] == "corners")
    check("mp.corn_holes", "sans_data" in (corn.get("holes") or []), str(corn.get("holes")))
    check("mp.corn_pas_drop", corn.get("match_id") == "M1")
    one = next(j for j in jambes if j["marche"] == "1X2")
    check("mp.1x2_open", one.get("priority_open") is True)


def main():
    print("=" * 70)
    print("TEST S5 — market_priority")
    print("=" * 70)
    test_config()
    test_palier_gate()
    test_status_paliers()
    test_corners_cards_holes()
    test_n_mesures_zero_data()
    test_allocate_stamp_ferme()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S5 market_priority : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
