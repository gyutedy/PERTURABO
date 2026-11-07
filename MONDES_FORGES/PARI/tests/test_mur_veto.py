#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 — mur veto: NO_BET / scorer KO hors tickets. Pas de recycle EV."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))

import combinator  # noqa: E402
import marches  # noqa: E402
import top3 as top3mod  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _sel(selection, ev, verdict, eligible, p=0.5, cote=2.0, marche="1X2"):
    return {
        "marche": marche, "selection": selection, "selection_label": selection,
        "cote": cote, "p_modele": p, "ev": ev, "verdict": verdict,
        "scorer_eligible": eligible, "scorer_refuse": [] if eligible else ["A3"],
        "scorer_score": 0.7 if eligible else 0.4, "scorer_seuil": 0.55,
        "pieges": [],
    }


def _event(mid, match, tops, score=8.0, bucket="HAUTE", verdict_modele="GO"):
    return {
        "id": mid, "match": match, "score_commun": score, "rang_global": 1,
        "bucket": bucket, "no_bet_recommande": False,
        "verdict_modele": verdict_modele, "top3": tops,
    }


def _top(selection, ev, verdict="VALUE", eligible=True, cote=1.87, p=0.73):
    return {
        "marche": "1X2", "selection": selection, "selection_label": selection,
        "cote": cote, "p_modele": p, "ev": ev, "verdict": verdict,
        "scorer_eligible": eligible,
    }


def test_top3_pas_de_recycle():
    p = {
        "id": "M1", "match": "Arsenal FC vs Hull City", "verdict": "NO_BET",
        "selections": [
            _sel("1", -0.17, "NO_BET", False, p=0.72, cote=1.15),
            _sel("X", 0.625, "NO_BET", False, p=0.21, cote=7.7),
            _sel("2", 0.13, "NO_BET", False, p=0.07, cote=17.0),
        ],
    }
    rows, score, bucket = top3mod.compute_match(p, "basse")
    check("v.top3_vide_nobet", rows == [], str(rows))
    check("v.top3_pas_x", not any(r.get("selection") == "X" for r in rows))
    check("v.vide_score0", score == 0.0, str(score))
    check("v.vide_faible", bucket == "FAIBLE", str(bucket))
    _, score_h, bucket_h = top3mod.compute_match(p, "haute")
    check("v.vide_haute_pas_fake", score_h == 0.0 and bucket_h == "FAIBLE",
          str((score_h, bucket_h)))


def test_top3_value_seulement():
    p = {
        "id": "M12", "match": "VfB Stuttgart vs Werder Bremen", "verdict": "GO",
        "selections": [
            _sel("1", 0.367, "VALUE", True, p=0.73, cote=1.87),
            _sel("X", -0.22, "NO_BET", False, p=0.19, cote=4.1),
            _sel("2", -0.72, "NO_BET", False, p=0.08, cote=3.55),
        ],
    }
    rows, _, _ = top3mod.compute_match(p, "haute")
    check("v.top3_un", len(rows) == 1, str(rows))
    check("v.top3_1", rows and rows[0]["selection"] == "1")
    check("v.top3_verdict", rows and rows[0].get("verdict") == "VALUE")
    check("v.top3_elig", rows and rows[0].get("scorer_eligible") is True)


def test_score_sur_jambe():
    p = {
        "id": "M1", "match": "A vs B", "verdict": "GO",
        "selections": [
            _sel("1", 0.10, "VALUE", True, p=0.72, cote=1.50),
            _sel("X", 0.625, "VALUE", True, p=0.21, cote=7.7),
        ],
    }
    rows, score, bucket = top3mod.compute_match(p, "basse")
    check("v.score_jambe_x", rows and rows[0]["selection"] == "X", str(rows))
    expected = round(10 * (0.30 * 0.45 + 0.40 * (0.21 / 0.65) + 0.30 * 1.0), 1)
    check("v.score_sur_jambe", score == expected, f"{score} vs {expected}")
    score_pmax = round(10 * (0.30 * 0.45 + 0.40 * min(1.0, 0.72 / 0.65) + 0.30 * 1.0), 1)
    check("v.score_pas_pmax", score != score_pmax, f"{score} vs pmax {score_pmax}")
    check("v.score_pfav", rows and rows[0].get("p_fav") == 0.72, str(rows[0] if rows else None))
    check("v.score_vest_legacy", rows and rows[0].get("vestiaire_ok") is True)


def test_combinator_jette_arsenal_gala():
    events = [
        _event("M1", "Arsenal FC vs Hull City", [
            _top("X", 0.625, verdict="NO_BET", eligible=False, cote=7.7, p=0.21),
        ], score=8.3, verdict_modele="NO_BET"),
        _event("M8", "Galatasaray Istanbul vs Amed", [
            _top("1", 0.1089, verdict="NO_BET", eligible=False, cote=1.37, p=0.81),
        ], score=8.3, verdict_modele="NO_BET"),
        _event("M12", "VfB Stuttgart vs Werder Bremen", [
            _top("1", 0.367, verdict="VALUE", eligible=True, cote=1.87, p=0.73),
        ], score=10.0),
        _event("M3", "Birmingham City vs Swansea City", [
            _top("1", 0.1828, verdict="VALUE", eligible=True, cote=1.84, p=0.64),
        ], score=10.0),
        _event("M2", "Fulham FC vs Newcastle United", [
            _top("1", 0.1118, verdict="VALUE", eligible=True, cote=2.0, p=0.56),
        ], score=9.4),
    ]
    res, wrn = combinator.allocate(
        events, tickets=3, jambes_by_ticket=[3, 2, 2],
        surticket_fc=400, budget_fc=1000, mises_free=None, n_mesures=0)
    ids = [j["match_id"] for t in res["tickets"] for j in t["jambes"]]
    check("v.pas_arsenal", "M1" not in ids, str(ids))
    check("v.pas_gala", "M8" not in ids, str(ids))
    check("v.stuttgart", "M12" in ids, str(ids))
    check("v.birm", "M3" in ids, str(ids))
    check("v.fulham", "M2" in ids, str(ids))


def test_scorer_ko_meme_si_label_value():
    events = [
        _event("M1", "Poison vs Label", [
            _top("X", 0.50, verdict="VALUE", eligible=False, cote=7.7, p=0.21),
        ]),
        _event("M2", "Clean vs Side", [
            _top("1", 0.20, verdict="VALUE", eligible=True, cote=1.9, p=0.65),
        ]),
    ]
    res, _ = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=400, budget_fc=1000, mises_free=None, n_mesures=0)
    ids = [j["match_id"] for t in res["tickets"] for j in t["jambes"]]
    check("v.ko_label", "M1" not in ids, str(ids))
    check("v.ko_clean", "M2" in ids, str(ids))


def test_zero_value_zero_ticket():
    events = [
        _event("M1", "A vs B", [
            _top("X", 0.62, verdict="NO_BET", eligible=False, cote=7.7, p=0.21),
        ], verdict_modele="NO_BET"),
    ]
    res, wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[1],
        surticket_fc=400, budget_fc=1000, mises_free=None, n_mesures=0)
    check("v.zero_tickets", res["tickets"] == [], str(res["tickets"]))
    check("v.zero_budget", res["budget"]["alloue_fc"] == 0)
    check("v.zero_msg", any("0 match" in w or "eligible" in w.lower() or "NO BET" in w for w in wrn), str(wrn))


def test_marches_filtre():
    events = [
        _event("M1", "Arsenal FC vs Hull City", [
            _top("X", 0.62, verdict="NO_BET", eligible=False, cote=7.7, p=0.21),
        ]),
        _event("M12", "VfB Stuttgart vs Werder Bremen", [
            _top("1", 0.36, verdict="VALUE", eligible=True, cote=1.87, p=0.73),
        ]),
    ]
    out = marches.filter_events(events, ["1X2"], ev_floor=0.03)
    ids = [e["id"] for e in out]
    check("v.filt_pas_arsenal", "M1" not in ids, str(ids))
    check("v.filt_stuttgart", "M12" in ids, str(ids))
    check("v.jouable_nobet", marches.jambe_jouable(_top("X", 0.62, "NO_BET", False)) is False)
    check("v.jouable_ko", marches.jambe_jouable(_top("1", 0.10, "VALUE", False)) is False)
    check("v.jouable_ok", marches.jambe_jouable(_top("1", 0.36, "VALUE", True)) is True)
    check("v.jouable_legacy", marches.jambe_jouable({"marche": "1X2", "ev": 0.12, "selection": "1"}) is True)


def test_tank_x_veto():
    tank_x = _top("X", 0.625, verdict="VALUE", eligible=True, cote=7.7, p=0.21)
    tank_x["p_fav"] = 0.72
    tank_x["vestiaire_ok"] = False
    check("v.tank_x_bloque", marches.jambe_jouable(tank_x) is False)

    tank_x_ok = dict(tank_x)
    tank_x_ok["vestiaire_ok"] = True
    check("v.tank_x_vestiaire", marches.jambe_jouable(tank_x_ok) is True)

    gala_1 = _top("1", 0.1089, verdict="VALUE", eligible=True, cote=1.37, p=0.81)
    gala_1["p_fav"] = 0.81
    gala_1["vestiaire_ok"] = False
    check("v.tank_1_ok", marches.jambe_jouable(gala_1) is True)

    x_pas_tank = _top("X", 0.20, verdict="VALUE", eligible=True, cote=3.5, p=0.40)
    x_pas_tank["p_fav"] = 0.40
    x_pas_tank["vestiaire_ok"] = False
    check("v.x_pas_tank", marches.jambe_jouable(x_pas_tank) is True)

    x_legacy = _top("X", 0.20, verdict="VALUE", eligible=True, cote=3.5, p=0.40)
    check("v.x_legacy_sans_pfav", marches.jambe_jouable(x_legacy) is True)

    ou = {"marche": "OU_2.5", "selection": "u2.5", "selection_label": "u2.5",
          "cote": 2.1, "p_modele": 0.55, "ev": 0.15, "verdict": "VALUE",
          "scorer_eligible": True, "p_fav": 0.72, "vestiaire_ok": False}
    check("v.tank_pas_jeter_ou", marches.jambe_jouable(ou) is True)

    events = [
        _event("M1", "Arsenal FC vs Hull City", [tank_x], score=8.3),
        _event("M8", "Galatasaray Istanbul vs Amed", [gala_1], score=8.3),
        _event("M12", "VfB Stuttgart vs Werder Bremen", [
            _top("1", 0.367, verdict="VALUE", eligible=True, cote=1.87, p=0.73),
        ], score=10.0),
        _event("M4", "Tank vs Side", [tank_x, ou], score=9.0),
    ]
    res, _ = combinator.allocate(
        events, tickets=2, jambes_by_ticket=[3, 2],
        surticket_fc=400, budget_fc=1000, mises_free=None, n_mesures=0)
    ids = [j["match_id"] for t in res["tickets"] for j in t["jambes"]]
    sels = {j["match_id"]: j["selection"] for t in res["tickets"] for j in t["jambes"]}
    check("v.tank_pas_arsenal_x", "M1" not in ids, str(ids))
    check("v.tank_gala_1", "M8" in ids and sels.get("M8") == "1", str(sels))
    check("v.tank_stuttgart", "M12" in ids, str(ids))
    check("v.tank_autre_marche", "M4" in ids and sels.get("M4") == "u2.5", str(sels))


def test_vestiaire_et_pfav():
    check("v.vest_legacy", top3mod.vestiaire_ok(None) is True)
    check("v.vest_applique", top3mod.vestiaire_ok({
        "state_factors": {"applied": True, "holes": []}, "holes": [],
    }) is True)
    check("v.vest_pas_applique", top3mod.vestiaire_ok({
        "state_factors": {"applied": False, "holes": ["effectifs"]},
        "holes": ["effectifs"],
    }) is False)
    check("v.vest_trou", top3mod.vestiaire_ok({
        "state_factors": {"applied": True, "holes": ["effectifs"]},
        "holes": ["effectifs"],
    }) is False)
    p = {"selections": [
        _sel("1", -0.17, "NO_BET", False, p=0.72),
        _sel("X", 0.625, "VALUE", True, p=0.21),
        _sel("2", 0.13, "NO_BET", False, p=0.07),
    ]}
    check("v.pfav_1", top3mod.p_fav_of(p) == 0.72, str(top3mod.p_fav_of(p)))
    an = {"state_factors": {"applied": False, "holes": ["effectifs"]},
          "holes": ["effectifs"]}
    rows, _, _ = top3mod.compute_match(
        {"id": "M1", "selections": [
            _sel("1", -0.17, "NO_BET", False, p=0.72, cote=1.15),
            _sel("X", 0.625, "VALUE", True, p=0.21, cote=7.7),
        ]}, "basse", an)
    check("v.stamp_pfav", rows and rows[0].get("p_fav") == 0.72)
    check("v.stamp_vest_ko", rows and rows[0].get("vestiaire_ok") is False)
    check("v.stamp_x_bloque", rows and marches.jambe_jouable(rows[0]) is False)


def test_thin_hors_combo():
    events = [
        _event("M11", "Nottingham Forest vs Manchester City", [
            _top("X", 0.0421, verdict="THIN", eligible=True, cote=3.9, p=0.267),
        ], score=8.5, verdict_modele="THIN"),
        _event("M12", "VfB Stuttgart vs Werder Bremen", [
            _top("1", 0.367, verdict="VALUE", eligible=True, cote=1.87, p=0.73),
        ], score=10.0),
    ]
    res, _ = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=400, budget_fc=1000, mises_free=None, n_mesures=0)
    ids = [j["match_id"] for t in res["tickets"] for j in t["jambes"]]
    check("v.pas_forest_thin", "M11" not in ids, str(ids))
    check("v.stuttgart_value", "M12" in ids, str(ids))
    check("v.jouable_thin", marches.jambe_jouable(_top("X", 0.0421, "THIN", True)) is False)
    out = marches.filter_events(events, ["1X2"], ev_floor=0.03)
    check("v.filt_pas_thin", [e["id"] for e in out] == ["M12"], str([e["id"] for e in out]))
    txt = marches.format_coverage({"matchs": events}, markets=["1X2"])
    check("v.cov_value", "VALUE" in txt, txt[:80])
    check("v.cov_pas_ev3", "EV>=3%" not in txt, txt[:80])


def main():
    print("=" * 70)
    print("TEST MUR VETO — phase 1")
    print("=" * 70)
    test_top3_pas_de_recycle()
    test_top3_value_seulement()
    test_score_sur_jambe()
    test_combinator_jette_arsenal_gala()
    test_scorer_ko_meme_si_label_value()
    test_zero_value_zero_ticket()
    test_marches_filtre()
    test_tank_x_veto()
    test_vestiaire_et_pfav()
    test_thin_hors_combo()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"mur veto : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
