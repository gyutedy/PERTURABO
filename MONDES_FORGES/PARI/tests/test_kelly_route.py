#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S10 — Kelly 1/8 defaut, 1/4 gate ECE. n<50 jamais 1/4. Zero reseau."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))

import combinator  # noqa: E402
import journal  # noqa: E402
import kelly_route  # noqa: E402
import ledger  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_config():
    cfg = kelly_route.load_config()
    check("k.cfg_defaut", abs(float(cfg["fraction_default"]) - 0.125) < 1e-12, str(cfg["fraction_default"]))
    check("k.cfg_plafond", abs(float(cfg["fraction_plafond"]) - 0.25) < 1e-12, str(cfg["fraction_plafond"]))
    check("k.cfg_pev", abs(float(cfg["p_ev_positif"]) - 0.55) < 1e-12, str(cfg["p_ev_positif"]))
    check("k.cfg_ece", abs(float(cfg["ece"]) - 0.03) < 1e-12, str(cfg["ece"]))
    check("k.cfg_nlock", int(cfg["n_lock"]) == 50)


def test_gate_1_4():
    rec = kelly_route.decide(ece=0.02, p_ev=0.60, n=50)
    check("k.hi_frac", rec["fraction"] == 0.25, str(rec["fraction"]))
    check("k.hi_label", rec["label"] == "1/4")
    check("k.hi_cal", rec["calibration_validee"] is True)
    check("k.hi_gate", rec["gate_1_4"] is True)
    check("k.hi_holes", rec["holes"] == [])
    rec_eq = kelly_route.decide(ece=0.03, p_ev=0.55, n=50)
    check("k.eq_1_4", rec_eq["fraction"] == 0.25 and rec_eq["gate_1_4"] is True, str(rec_eq))


def test_reste_1_8():
    rec_ece = kelly_route.decide(ece=0.04, p_ev=0.60, n=50)
    check("k.ece_haute", rec_ece["fraction"] == 0.125 and rec_ece["label"] == "1/8")
    check("k.ece_haute_cal", rec_ece["calibration_validee"] is False)
    rec_p = kelly_route.decide(ece=0.02, p_ev=0.50, n=50)
    check("k.pev_basse", rec_p["fraction"] == 0.125 and rec_p["gate_1_4"] is False)
    rec_n = kelly_route.decide(ece=0.02, p_ev=0.60, n=49)
    check("k.n49", rec_n["fraction"] == 0.125, str(rec_n["fraction"]))
    check("k.n49_jamais_1_4", rec_n["label"] != "1/4" and rec_n["gate_1_4"] is False)
    check("k.n49_hole", "n<50" in (rec_n.get("holes") or []), str(rec_n.get("holes")))
    rec_0 = kelly_route.decide(ece=0.02, p_ev=0.60, n=0)
    check("k.n0", rec_0["fraction"] == 0.125 and "n<50" in (rec_0.get("holes") or []))


def test_absents_holes():
    rec_p = kelly_route.decide(ece=0.02, p_ev=None, n=50)
    check("k.p_absent_frac", rec_p["fraction"] == 0.125)
    check("k.p_absent_hole", "p_ev" in (rec_p.get("holes") or []), str(rec_p.get("holes")))
    check("k.p_absent_pas_1_4", rec_p["gate_1_4"] is False)
    rec_e = kelly_route.decide(ece=None, p_ev=0.60, n=50)
    check("k.ece_absent_frac", rec_e["fraction"] == 0.125)
    check("k.ece_absent_hole", "ece" in (rec_e.get("holes") or []), str(rec_e.get("holes")))
    rec_n = kelly_route.decide(ece=0.02, p_ev=0.60, n=None)
    check("k.n_absent", rec_n["fraction"] == 0.125 and "n" in (rec_n.get("holes") or []))
    rec_all = kelly_route.decide(ece=None, p_ev=None, n=None)
    holes = rec_all.get("holes") or []
    check("k.tous_absents", rec_all["fraction"] == 0.125)
    check("k.tous_holes", "ece" in holes and "p_ev" in holes and "n" in holes, str(holes))


def test_conjoint():
    jambes = [
        {"p_modele": 0.70, "cote": 1.70},
        {"p_modele": 0.62, "cote": 1.90},
    ]
    p1, h1 = kelly_route.p_ev_conjoint(jambes, draws=400, seed=42)
    p2, h2 = kelly_route.p_ev_conjoint(jambes, draws=400, seed=42)
    p3, _ = kelly_route.p_ev_conjoint(jambes, draws=400, seed=7)
    check("k.mc_ok", p1 is not None and not h1, str((p1, h1)))
    check("k.mc_seede", p1 == p2, str((p1, p2)))
    check("k.mc_seed_change", p3 is not None and p3 != p1, str((p1, p3)))
    check("k.mc_range", 0.0 <= p1 <= 1.0)
    rec = kelly_route.route_ticket(jambes=jambes, ece=0.02, n=50)
    check("k.combo_conjoint", rec.get("conjoint") is True)
    check("k.combo_pev", rec.get("p_ev") is not None, str(rec.get("p_ev")))
    rec_hi = kelly_route.route_ticket(
        jambes=jambes, ece=0.02, n=50, p_ev=0.80)
    check("k.combo_gate_si_ok", rec_hi["fraction"] == 0.25, str(rec_hi))
    rec_trou = kelly_route.p_ev_conjoint(
        [{"p_modele": None, "cote": 1.7}, {"p_modele": 0.6, "cote": 1.9}])
    check("k.combo_trou_p", rec_trou[0] is None and "p_modele" in rec_trou[1], str(rec_trou))


def test_stamp_budget_intact():
    tix = {
        "rang_ticket": 1,
        "mise_fc": 800,
        "jambes": [{"p_modele": 0.70, "cote": 1.70}],
    }
    kelly_route.stamp_ticket(tix, ece=0.02, p_ev=0.60, n=50)
    check("k.stamp_frac", tix.get("kelly_fraction") == 0.25, str(tix.get("kelly_fraction")))
    check("k.stamp_label", tix.get("kelly_label") == "1/4")
    check("k.stamp_mise", tix.get("mise_fc") == 800, str(tix.get("mise_fc")))
    check("k.stamp_cal", tix.get("kelly_calibration_validee") is True)
    tix2 = {
        "rang_ticket": 2,
        "mise_fc": 2200,
        "jambes": [
            {"p_modele": 0.55, "cote": 1.90},
            {"p_modele": 0.52, "cote": 2.10},
        ],
    }
    kelly_route.stamp_ticket(tix2, ece=None, n=10)
    check("k.stamp2_frac", tix2.get("kelly_fraction") == 0.125)
    check("k.stamp2_mise", tix2.get("mise_fc") == 2200)
    check("k.stamp2_holes", "ece" in (tix2.get("kelly_holes") or []), str(tix2.get("kelly_holes")))


def test_allocate_stamp_pas_budget():
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
    res, _wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        n_mesures=0)
    t = res["tickets"][0]
    check("k.alloc_mise", t.get("mise_fc") == 800, str(t.get("mise_fc")))
    check("k.alloc_frac", t.get("kelly_fraction") == 0.125, str(t.get("kelly_fraction")))
    check("k.alloc_label", t.get("kelly_label") == "1/8")
    check("k.alloc_jamais_1_4", t.get("kelly_fraction") != 0.25)


def test_journal_procedure():
    extra = kelly_route.procedure_extra(ece=0.02, p_ev=0.60, n=50)
    check("k.extra_frac", extra["kelly"]["fraction"] == 0.25)
    check("k.extra_pas_hole", "kelly" not in (extra.get("holes") or []))
    tix = {
        "tickets": [{
            "rang_ticket": 1, "mise_fc": 100, "cote_totale": 1.7,
            "kelly_fraction": 0.125, "kelly_label": "1/8",
            "kelly_holes": ["n<50"], "kelly_ece": None, "kelly_p_ev": None,
            "kelly_calibration_validee": False,
            "jambes": [{"match_id": "M1", "marche": "1X2", "selection": "1",
                        "selection_label": "1", "cote": 1.7, "p_modele": 0.62}],
        }],
        "budget": {"budget_fc": 300, "alloue_fc": 100, "reste_fc": 200},
        "warnings": [],
        "regles": {"seuil_ev": 0.03},
    }
    extra_t = kelly_route.procedure_extra_from_tickets(tix)
    check("k.extra_tix_frac", extra_t["kelly"]["fraction"] == 0.125)
    check("k.extra_tix_src", extra_t["kelly"].get("source") == "tickets")
    lot = ledger.freeze_lot(
        "L-KEL", "PARI-TEST", "C-KEL", tix,
        ledger.legs_from_tickets(tix["tickets"]), 300, 100)
    proc = (lot.get("journal") or {}).get("procedure") or {}
    kel = proc.get("kelly") or {}
    check("k.freeze_kelly", kel.get("fraction") == 0.125, str(kel))
    check("k.freeze_pas_hole_kelly", "kelly" not in (proc.get("holes") or []), str(proc.get("holes")))
    frozen = str(proc)
    check("k.freeze_7args", lot.get("token") == "L-KEL")
    check("k.proc_present", bool(proc.get("checks")))
    check("k.proc_immu", frozen == str((lot.get("journal") or {}).get("procedure")))


def test_build_procedure_tickets():
    tix = {"tickets": [{"kelly_fraction": 0.125, "mise_fc": 800, "jambes": []}]}
    proc = journal.build_procedure(tix)
    check("k.jnl_from_tix", (proc.get("kelly") or {}).get("source") == "tickets")
    check("k.jnl_fracs", (proc.get("kelly") or {}).get("fractions") == [0.125])


def main():
    print("=" * 70)
    print("TEST S10 — kelly_route")
    print("=" * 70)
    test_config()
    test_gate_1_4()
    test_reste_1_8()
    test_absents_holes()
    test_conjoint()
    test_stamp_budget_intact()
    test_allocate_stamp_pas_budget()
    test_journal_procedure()
    test_build_procedure_tickets()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S10 kelly : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
