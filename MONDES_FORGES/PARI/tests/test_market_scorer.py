#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S12 — scorer eligibilite F03. Portes A1-A4 hors score. Poisson inchange."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import forgeward  # noqa: E402
import market_scorer as scorer  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _ov(*cotes):
    return sum(1.0 / c for c in cotes) - 1.0


def test_profiles():
    p = scorer.load_profiles()
    d = p["default"]["poids"]
    check("s.cfg_b1", abs(d["B1"] - 0.30) < 1e-12, str(d["B1"]))
    check("s.cfg_b2", abs(d["B2"] - 0.20) < 1e-12, str(d["B2"]))
    check("s.cfg_b3", abs(d["B3"] - 0.20) < 1e-12, str(d["B3"]))
    check("s.cfg_b4", abs(d["B4"] - 0.15) < 1e-12, str(d["B4"]))
    check("s.cfg_b5", abs(d["B5"] - 0.10) < 1e-12, str(d["B5"]))
    check("s.cfg_b6", abs(d["B6"] - 0.05) < 1e-12, str(d["B6"]))
    check("s.cfg_ovmax", abs(p["overround_max"] - 0.20) < 1e-12)
    check("s.cfg_cotemin", abs(p["cote_min"] - 1.10) < 1e-12)
    mt = scorer.profile_for("MT_PROLIFIQUE", p)
    check("s.mt_b1", abs(mt["poids"]["B1"] - 0.25) < 1e-12, str(mt["poids"]["B1"]))
    check("s.mt_b2", abs(mt["poids"]["B2"] - 0.25) < 1e-12, str(mt["poids"]["B2"]))
    check("s.mt_seuil", abs(mt["seuil"] - 0.55) < 1e-12, str(mt["seuil"]))
    ou = scorer.profile_for("OU_2.5", p)
    check("s.ou_b1", abs(ou["poids"]["B1"] - 0.30) < 1e-12)
    check("s.ou_seuil", abs(ou["seuil"] - 0.50) < 1e-12)
    cs = scorer.profile_for("CS", p)
    check("s.cs_seuil", abs(cs["seuil"] - 0.60) < 1e-12)


def test_overround_math():
    ov_mt_refuse = _ov(2.10, 3.40, 2.10)
    check("s.ov_mt_246", abs(ov_mt_refuse - 0.2464986) < 1e-4, str(ov_mt_refuse))
    check("s.ov_mt_gt20", ov_mt_refuse > 0.20)
    ov_mt_ok = _ov(2.20, 3.60, 2.20)
    check("s.ov_mt_ok", ov_mt_ok < 0.20, str(ov_mt_ok))
    check("s.ov_mt_187", abs(ov_mt_ok - 0.1868687) < 1e-4, str(ov_mt_ok))
    ov_1x2 = _ov(2.10, 3.40, 3.50)
    check("s.ov_1x2_56", abs(ov_1x2 - 0.0560224) < 1e-4, str(ov_1x2))
    check("s.ov_1x2_lt20", ov_1x2 < 0.20)


def test_a1_groupe():
    ok, miss = scorer.gate_a1("MT_PROLIFIQUE", {"mt1": 2.20, "mt2": 2.20})
    check("s.a1_mt_incomplet", ok is False)
    check("s.a1_mt_mte", "mte" in miss, str(miss))
    ok2, miss2 = scorer.gate_a1("MT_PROLIFIQUE", {"mt1": 2.20, "mte": 3.60, "mt2": 2.20})
    check("s.a1_mt_complet", ok2 is True and miss2 == [])
    ok3, _ = scorer.gate_a1("1X2", {"1": 2.10, "X": 3.40, "2": 3.50})
    check("s.a1_1x2", ok3 is True)
    ok4, miss4 = scorer.gate_a1("1X2", {"1": 2.10, "X": 3.40})
    check("s.a1_1x2_manque", ok4 is False and "2" in miss4, str(miss4))
    rec = scorer.score("mt1", 2.20, "MT_PROLIFIQUE", {"mt1": 2.20, "mt2": 2.20},
                       analysis={"data_quality": {"niveau": "haute", "flags": []}},
                       extra={"p_modele": 0.48, "ev": 0.056, "cote": 2.20, "cote_t2h": 2.10,
                              "double_confirmation": True})
    check("s.a1_refuse", rec["eligible"] is False and "A1" in rec["refuse"], str(rec["refuse"]))
    check("s.a1_hors_score", rec["score"] is not None)


def test_a2_praticable():
    check("s.a2_105", scorer.gate_a2(1.05) is False)
    check("s.a2_110", scorer.gate_a2(1.10) is True)
    check("s.a2_none", scorer.gate_a2(None) is False)
    rec = scorer.score("1", 1.05, "1X2", {"1": 1.05, "X": 8.0, "2": 12.0},
                       analysis={"data_quality": {"niveau": "haute", "flags": []}},
                       extra={"p_modele": 0.92, "ev": 0.0, "cote": 1.05, "cote_t2h": 1.08,
                              "double_confirmation": True})
    check("s.a2_refuse", rec["eligible"] is False and "A2" in rec["refuse"], str(rec["refuse"]))


def test_a3_historique():
    check("s.a3_haute", scorer.gate_a3({"data_quality": {"niveau": "haute", "flags": []}}) is True)
    check("s.a3_moyenne", scorer.gate_a3({"data_quality": {"niveau": "moyenne", "flags": ["mt_split_estimate"]}}) is True)
    check("s.a3_basse", scorer.gate_a3({"data_quality": {"niveau": "basse", "flags": []}}) is False)
    check("s.a3_mj", scorer.gate_a3({"data_quality": {"niveau": "haute", "flags": ["mj_insuffisant"]}}) is False)
    rec = scorer.score("o2.5", 1.90, "OU_2.5", {"o2.5": 1.90, "u2.5": 2.00},
                       analysis={"data_quality": {"niveau": "basse", "flags": ["mj_insuffisant"]}},
                       extra={"p_modele": 0.58, "ev": 0.102, "cote": 1.90, "cote_t2h": 1.85,
                              "double_confirmation": True})
    check("s.a3_refuse", rec["eligible"] is False and "A3" in rec["refuse"], str(rec["refuse"]))


def test_a4_vitrine():
    mt_bad = {"mt1": 2.10, "mte": 3.40, "mt2": 2.10}
    ok, ov = scorer.gate_a4(mt_bad)
    check("s.a4_mt_refus", ok is False)
    check("s.a4_mt_ov", ov is not None and ov > 0.20, str(ov))
    rec = scorer.score("mt2", 2.10, "MT_PROLIFIQUE", mt_bad,
                       analysis={"data_quality": {"niveau": "haute", "flags": []}},
                       extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.05,
                              "double_confirmation": True})
    check("s.a4_eligible_false", rec["eligible"] is False)
    check("s.a4_in_refuse", "A4" in rec["refuse"], str(rec["refuse"]))
    mt_ok = {"mt1": 2.20, "mte": 3.60, "mt2": 2.20}
    ok2, ov2 = scorer.gate_a4(mt_ok)
    check("s.a4_mt_passe", ok2 is True, str(ov2))
    rec2 = scorer.score("mt2", 2.20, "MT_PROLIFIQUE", mt_ok,
                        analysis={"data_quality": {"niveau": "haute", "flags": []}},
                        extra={"p_modele": 0.52, "ev": 0.144, "cote": 2.20, "cote_t2h": 2.10,
                               "double_confirmation": True})
    check("s.a4_mt_ok_gate", rec2["gates"]["A4"] is True)
    g1x2 = {"1": 2.10, "X": 3.40, "2": 3.50}
    ok3, ov3 = scorer.gate_a4(g1x2)
    check("s.a4_1x2_passe", ok3 is True, str(ov3))


def test_b_contrib():
    rec = scorer.score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.00,
               "double_confirmation": True},
    )
    c = rec["contrib"]
    check("s.b1_plein", abs(c["B1"]["raw"] - 1.0) < 1e-12, str(c["B1"]))
    check("s.b2_plein", abs(c["B2"]["raw"] - 1.0) < 1e-12, str(c["B2"]))
    check("s.b3_plein", abs(c["B3"]["raw"] - 1.0) < 1e-12, str(c["B3"]))
    check("s.b4_plein", abs(c["B4"]["raw"] - 1.0) < 1e-12, str(c["B4"]))
    check("s.b5_plein", abs(c["B5"]["raw"] - 1.0) < 1e-12, str(c["B5"]))
    check("s.b6_plein", abs(c["B6"]["raw"] - 1.0) < 1e-12, str(c["B6"]))
    expected = 0.30 + 0.20 + 0.20 + 0.15 + 0.10 + 0.05
    check("s.score_1", abs(rec["score"] - expected) < 1e-9, str(rec["score"]))
    check("s.eligible_plein", rec["eligible"] is True)
    check("s.refuse_vide", rec["refuse"] == [])
    ssum = sum(c[k]["contrib"] for k in scorer.KEYS)
    check("s.contrib_sum", abs(ssum - rec["score"]) < 1e-9, str(ssum))


def test_b_trous():
    rec = scorer.score(
        "o2.5", 1.90, "OU_2.5", {"o2.5": 1.90, "u2.5": 2.00},
        analysis={"data_quality": {"niveau": "moyenne", "flags": ["mt_split_estimate"]}},
        extra={"p_modele": 0.55, "ev": 0.045, "cote": 1.90},
    )
    check("s.b3_hole", "b3_asymetrie" in rec["holes"], str(rec["holes"]))
    check("s.b3_zero", rec["contrib"]["B3"]["raw"] == 0.0)
    check("s.b6_hole", "b6_confirmation" in rec["holes"], str(rec["holes"]))
    check("s.b4_moy", rec["contrib"]["B4"]["raw"] == 0.5)
    check("s.trou_reduit", rec["score"] < 1.0)
    rec_thin = scorer.score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.49, "ev": 0.029, "cote": 2.10, "cote_t2h": 2.00,
               "double_confirmation": False},
    )
    check("s.b1_thin", rec_thin["contrib"]["B1"]["raw"] == 0.5, str(rec_thin["contrib"]["B1"]))
    rec_neg = scorer.score(
        "2", 3.50, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.20, "ev": -0.30, "cote": 3.50, "cote_t2h": 3.40,
               "double_confirmation": False},
    )
    check("s.b1_neg", rec_neg["contrib"]["B1"]["raw"] == 0.0)


def test_b2_bande():
    rec_mid = scorer.score(
        "1", 2.50, "1X2", {"1": 2.50, "X": 3.20, "2": 2.90},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.45, "ev": 0.125, "cote": 2.50, "cote_t2h": 2.40,
               "double_confirmation": True},
    )
    check("s.b2_bande", rec_mid["contrib"]["B2"]["raw"] == 1.0)
    rec_lo = scorer.score(
        "1", 1.25, "1X2", {"1": 1.25, "X": 5.50, "2": 11.0},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.84, "ev": 0.05, "cote": 1.25, "cote_t2h": 1.22,
               "double_confirmation": True},
    )
    check("s.b2_125", rec_lo["contrib"]["B2"]["raw"] == 0.5, str(rec_lo["contrib"]["B2"]))
    rec_hi = scorer.score(
        "2", 4.20, "1X2", {"1": 1.70, "X": 3.80, "2": 4.20},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.28, "ev": 0.176, "cote": 4.20, "cote_t2h": 4.00,
               "double_confirmation": True},
    )
    check("s.b2_420", rec_hi["contrib"]["B2"]["raw"] == 0.5)


def test_mt_poids():
    rec = scorer.score(
        "mt2", 2.20, "MT_PROLIFIQUE", {"mt1": 2.20, "mte": 3.60, "mt2": 2.20},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.52, "ev": 0.144, "cote": 2.20, "cote_t2h": 2.10,
               "double_confirmation": True},
    )
    check("s.mt_poids_b1", abs(rec["contrib"]["B1"]["poids"] - 0.25) < 1e-12)
    check("s.mt_poids_b2", abs(rec["contrib"]["B2"]["poids"] - 0.25) < 1e-12)
    check("s.mt_b5_reduit", rec["contrib"]["B5"]["raw"] == 0.2, str(rec["contrib"]["B5"]))
    expected = 0.25 + 0.25 + 0.20 + 0.15 + 0.10 * 0.2 + 0.05
    check("s.mt_score", abs(rec["score"] - expected) < 1e-9, str(rec["score"]))
    check("s.mt_eligible", rec["eligible"] is True)
    rec_tight = scorer.score(
        "mt2", 2.60, "MT_PROLIFIQUE", {"mt1": 2.60, "mte": 3.50, "mt2": 2.60},
        analysis={"data_quality": {"niveau": "haute", "flags": []}},
        extra={"p_modele": 0.50, "ev": 0.30, "cote": 2.60, "cote_t2h": 2.50,
               "double_confirmation": True},
    )
    check("s.mt_tight_b5", rec_tight["contrib"]["B5"]["raw"] == 1.0, str(rec_tight["contrib"]["B5"]))
    check("s.mt_tight_1", abs(rec_tight["score"] - 1.0) < 1e-9, str(rec_tight["score"]))


def test_forgeward_veto_ev_inchange():
    analysis = {
        "probas": {"1": 0.50, "X": 0.25, "2": 0.25, "mt1": 0.33, "mte": 0.30, "mt2": 0.37},
        "cs": {},
        "data_quality": {"niveau": "haute", "flags": []},
    }
    m = {
        "id": "M1", "dom": "A", "ext": "B",
        "cotes": {"1": 2.10, "X": 3.40, "2": 3.50, "mt1": 2.10, "mte": 3.40, "mt2": 2.10},
        "odds_t2h": {"1": 2.00, "X": 3.30, "2": 3.40, "mt1": 2.00, "mte": 3.30, "mt2": 2.00},
    }
    pool = {
        "seuil_ev_top5": 0.03, "seuil_ev_exotique": 0.08,
        "kelly_fraction": 0.25, "mise_max_pct_bankroll": 0.05, "mise_max_pct_exotique": 0.03,
    }
    out = forgeward.predict_match(m, analysis, pool, "top5")
    one = next(s for s in out["selections"] if s["selection"] == "1")
    mt2 = next(s for s in out["selections"] if s["selection"] == "mt2")
    check("s.fw_ev_1", abs(one["ev"] - round(0.50 * 2.10 - 1, 4)) < 1e-12, str(one["ev"]))
    check("s.fw_ev_mt", abs(mt2["ev"] - round(0.37 * 2.10 - 1, 4)) < 1e-12, str(mt2["ev"]))
    check("s.fw_p_inchange", one["p_modele"] == 0.50)
    check("s.fw_1x2_ok", one.get("scorer_eligible") is True, str(one.get("scorer_refuse")))
    check("s.fw_mt_a4", mt2.get("scorer_eligible") is False and "A4" in (mt2.get("scorer_refuse") or []))
    check("s.fw_mt_nobet", mt2["verdict"] == "NO_BET")
    check("s.fw_mt_mise_null", mt2["mise_units"] is None)
    check("s.fw_pas_producteur", one["p_modele"] == analysis["probas"]["1"])


def test_pas_poisson():
    import breacher
    src = open(os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE", "market_scorer.py"), encoding="utf-8").read()
    check("s.pas_score_matrix", "score_matrix" not in src)
    check("s.pas_lambda", "lambda_dom" not in src)
    m = breacher.score_matrix(1.4, 1.1)
    st = breacher.matrix_stats(m)
    check("s.poisson_intact", "o2.5" in st and st["o2.5"] > 0)


def main():
    print("=" * 70)
    print("TEST S12 — market scorer")
    print("=" * 70)
    test_profiles()
    test_overround_math()
    test_a1_groupe()
    test_a2_praticable()
    test_a3_historique()
    test_a4_vitrine()
    test_b_contrib()
    test_b_trous()
    test_b2_bande()
    test_mt_poids()
    test_forgeward_veto_ev_inchange()
    test_pas_poisson()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S12 scorer : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
