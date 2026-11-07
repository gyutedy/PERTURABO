#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S14 — detecteurs pieges + /data scorer. Zero reseau. Poisson inchange."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import forgeward  # noqa: E402
import market_scorer as scorer  # noqa: E402
from input_capture import parse_capture, to_carte  # noqa: E402
import data_view  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _ov(*cotes):
    return sum(1.0 / c for c in cotes) - 1.0


def _flat(parsed):
    rows = []
    for b in parsed.get("captures") or []:
        for m in b.get("matchs") or []:
            rows.append(m)
    return rows


def _score(sel, cote, marche, group, extra=None, analysis=None):
    return scorer.score(
        sel, cote, marche, group,
        analysis=analysis or {"data_quality": {"niveau": "haute", "flags": []}},
        extra=extra or {},
    )


def test_cote_plate_x10():
    rows = [
        "| Compétition & Match | Horaire | 1 | X | 2 | Moins | Plus | 1st | Égal | 2nd |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    teams = [
        ("Everton FC", "Coventry City"),
        ("Arsenal FC", "Hull City"),
        ("Manchester City", "Fulham FC"),
        ("Brentford FC", "Everton FC"),
        ("Chelsea FC", "Leeds United"),
        ("Liverpool FC", "West Ham"),
        ("Tottenham FC", "Wolves"),
        ("Newcastle FC", "Burnley"),
        ("Aston Villa", "Sunderland"),
        ("Brighton FC", "Bournemouth"),
        ("Crystal Palace", "Nottingham"),
    ]
    for i, (d, e) in enumerate(teams):
        mt2 = "2.10" if i < 10 else "2.40"
        rows.append(
            f"| Angleterre - Premier League<br>{d} vs {e} | 06/11/26 21:00 | "
            f"1.70 | 3.80 | 4.50 | 1.50 | 2.20 | 2.10 | 3.40 | {mt2} |"
        )
    p = parse_capture("\n".join(rows) + "\n")
    ms = _flat(p)
    n_plate = sum(1 for m in ms if m.get("cote_plate"))
    check("p.plate10", n_plate == 10, f"n_plate={n_plate} n={len(ms)}")
    last = next(m for m in ms if m.get("dom") == "Crystal Palace")
    check("p.11e_libre", not last.get("cote_plate"), f"cotes={last.get('cotes')}")
    carte = to_carte(p)
    n_c = sum(1 for m in carte["matchs"] if m.get("cote_plate"))
    check("p.carte10", n_c == 10, f"n_c={n_c}")
    flagged = next(m for m in ms if m.get("cote_plate"))
    rec = _score(
        "mt2", 2.10, "MT_PROLIFIQUE",
        {"mt1": 2.10, "mte": 3.40, "mt2": 2.10},
        extra={"cote_plate": True, "match": flagged, "p_modele": 0.52, "ev": 0.092,
               "cote": 2.10, "cote_t2h": 2.05, "double_confirmation": True},
    )
    check("p.flag_scorer", "cote_plate" in rec["pieges"], str(rec["pieges"]))
    check("p.detail", rec["piege_detail"]["cote_plate"] is True)
    check("p.cotes_gardees", (flagged.get("cotes") or {}).get("mt2") == 2.10)


def test_marge_22_retire():
    ov = _ov(2.10, 3.40, 2.10)
    check("v.ov22", ov > 0.20, str(ov))
    mt_bad = {"mt1": 2.10, "mte": 3.40, "mt2": 2.10}
    vitrine, ov2 = scorer.detect_marche_vitrine(mt_bad)
    check("v.detect", vitrine is True, str(ov2))
    rec = _score(
        "mt2", 2.10, "MT_PROLIFIQUE", mt_bad,
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.05,
               "double_confirmation": True},
    )
    check("v.a4", "A4" in rec["refuse"], str(rec["refuse"]))
    check("v.eligible", rec["eligible"] is False)
    check("v.flag", "marche_vitrine" in rec["pieges"], str(rec["pieges"]))
    analysis = {
        "probas": {"mt1": 0.33, "mte": 0.30, "mt2": 0.37, "1": 0.50, "X": 0.25, "2": 0.25},
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
    mt2 = next(s for s in out["selections"] if s["selection"] == "mt2")
    check("v.fw_nobet", mt2["verdict"] == "NO_BET")
    check("v.fw_mise", mt2["mise_units"] is None)
    check("v.fw_vitrine", "marche_vitrine" in (mt2.get("pieges") or []), str(mt2.get("pieges")))
    check("v.fw_ev", abs(mt2["ev"] - round(0.37 * 2.10 - 1, 4)) < 1e-12, str(mt2["ev"]))


def test_marge_anomalique():
    mt_ok = {"mt1": 2.20, "mte": 3.60, "mt2": 2.20}
    ov = scorer.overround(mt_ok)
    check("a.ov187", ov is not None and 0.10 < ov < 0.20, str(ov))
    anom, _ = scorer.detect_marge_anomalique(mt_ok)
    check("a.flag", anom is True)
    vitrine, _ = scorer.detect_marche_vitrine(mt_ok)
    check("a.pas_vitrine", vitrine is False)
    rec = _score(
        "mt2", 2.20, "MT_PROLIFIQUE", mt_ok,
        extra={"p_modele": 0.52, "ev": 0.144, "cote": 2.20, "cote_t2h": 2.10,
               "double_confirmation": True},
    )
    check("a.eligible", rec["eligible"] is True)
    check("a.piege", "marge_anomalique" in rec["pieges"], str(rec["pieges"]))
    check("a.pas_a4", "A4" not in rec["refuse"])
    tight = {"1": 2.10, "X": 3.40, "2": 3.50}
    anom2, ov2 = scorer.detect_marge_anomalique(tight)
    check("a.1x2_ok", anom2 is False, str(ov2))


def test_cote_figee_sur_news():
    rec = _score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.10,
               "notes_out": 2, "double_confirmation": True},
    )
    check("f.flag", "cote_figee_sur_news" in rec["pieges"], str(rec["pieges"]))
    rec2 = _score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.00,
               "notes_out": 2, "double_confirmation": True},
    )
    check("f.move_pas_figee", "cote_figee_sur_news" not in rec2["pieges"], str(rec2["pieges"]))
    rec3 = _score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.10,
               "notes_out": 0, "double_confirmation": True},
    )
    check("f.sans_news", "cote_figee_sur_news" not in rec3["pieges"], str(rec3["pieges"]))
    rec4 = _score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "notes_out": 2,
               "double_confirmation": True},
    )
    check("f.trou_t2h", "cote_figee_sur_news" not in rec4["pieges"])
    check("f.b3_hole", "b3_asymetrie" in rec4["holes"], str(rec4["holes"]))


def test_lecture_trois_temps():
    lect = scorer.lecture_cotes(2.20, extra={"cote_t2h": 2.10, "cote_t0": 2.00})
    check("l.cap", lect["capture"] == 2.20)
    check("l.t2h", lect["t2h"] == 2.10)
    check("l.t0", lect["t0"] == 2.00)
    check("l.move_t2h", lect["move_t2h"] is not None)
    rec = _score(
        "1", 2.20, "1X2", {"1": 2.20, "X": 3.40, "2": 3.40},
        extra={"p_modele": 0.50, "ev": 0.10, "cote": 2.20, "cote_t2h": 2.10,
               "cote_t0": 2.00, "double_confirmation": True},
    )
    check("l.stamp", rec["lecture_cotes"]["t0"] == 2.00, str(rec["lecture_cotes"]))
    rec_t0 = _score(
        "1", 2.20, "1X2", {"1": 2.20, "X": 3.40, "2": 3.40},
        extra={"p_modele": 0.50, "ev": 0.10, "cote": 2.20, "cote_t0": 2.00,
               "double_confirmation": True},
    )
    check("l.b3_via_t0", rec_t0["contrib"]["B3"]["raw"] == 1.0, str(rec_t0["contrib"]["B3"]))
    check("l.pas_hole_t0", "b3_asymetrie" not in rec_t0["holes"], str(rec_t0["holes"]))


def test_data_criteres():
    rec = _score(
        "1", 2.10, "1X2", {"1": 2.10, "X": 3.40, "2": 3.50},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.00,
               "double_confirmation": True},
    )
    line = scorer.format_criteres(rec)
    check("d.scorer", line.startswith("SCORER"), line)
    check("d.edge", "edge" in line, line)
    check("d.bande", "bande" in line, line)
    check("d.info", "info" in line, line)
    check("d.data", "data" in line, line)
    check("d.marge", "marge" in line, line)
    check("d.confirm", "confirm" in line, line)
    rec_v = _score(
        "mt2", 2.10, "MT_PROLIFIQUE", {"mt1": 2.10, "mte": 3.40, "mt2": 2.10},
        extra={"p_modele": 0.52, "ev": 0.092, "cote": 2.10, "cote_t2h": 2.05,
               "cote_plate": True, "double_confirmation": True},
    )
    line_v = scorer.format_criteres(rec_v)
    check("d.pieges", "PIEGES" in line_v and "marche_vitrine" in line_v, line_v)
    check("d.plate", "cote_plate" in line_v, line_v)
    sel = {
        "scorer_score": rec["score"], "scorer_seuil": rec["seuil"],
        "scorer_eligible": rec["eligible"], "scorer_contrib": rec["contrib"],
        "scorer_refuse": rec["refuse"], "pieges": rec["pieges"],
    }
    via_dv = data_view.format_criteres(sel)
    check("d.dv", "SCORER" in via_dv and "edge" in via_dv, via_dv)
    top3 = {
        "matchs": [{
            "id": "M1", "match": "A vs B", "dom": "A", "ext": "B",
            "bucket": "HAUTE", "score_commun": 8.0, "rang_global": 1,
            "top3": [{
                "selection": "1", "cote": 2.10, "scorer_score": rec_v["score"],
                "scorer_seuil": rec_v["seuil"], "scorer_eligible": False,
                "scorer_contrib": rec_v["contrib"], "scorer_refuse": rec_v["refuse"],
                "pieges": rec_v["pieges"], "lecture_cotes": rec_v["lecture_cotes"],
            }],
        }]
    }
    compact = data_view.render_compact(top3, "", {"matchs": [{"id": "M1", "dom": "A", "ext": "B"}]}, {})
    check("d.compact_col", "PIEGES" in compact, compact[:120])
    check("d.compact_flag", "marche_vitrine" in compact or "cote_plate" in compact, compact)
    fiche = data_view.render_fiche(1, top3, "", {"matchs": [{"id": "M1", "dom": "A", "ext": "B"}]}, {})
    check("d.fiche_scorer", "SCORER" in fiche, fiche)
    check("d.fiche_pieges", "PIEGES" in fiche, fiche)
    check("d.fiche_cotes", "COTES" in fiche and "T-2h" in fiche, fiche)


def test_ev_p_inchange():
    analysis = {
        "probas": {"1": 0.50, "X": 0.25, "2": 0.25, "mt1": 0.33, "mte": 0.30, "mt2": 0.37},
        "cs": {},
        "data_quality": {"niveau": "haute", "flags": []},
    }
    m = {
        "id": "M1", "dom": "A", "ext": "B",
        "cotes": {"1": 2.10, "X": 3.40, "2": 3.50, "mt1": 2.20, "mte": 3.60, "mt2": 2.20},
        "odds_t2h": {"1": 2.00, "X": 3.30, "2": 3.40, "mt1": 2.10, "mte": 3.50, "mt2": 2.10},
        "odds_t0": {"1": 1.95, "X": 3.20, "2": 3.30, "mt1": 2.05, "mte": 3.40, "mt2": 2.05},
        "cote_plate": True,
        "notes_out": 1,
    }
    pool = {
        "seuil_ev_top5": 0.03, "seuil_ev_exotique": 0.08,
        "kelly_fraction": 0.25, "mise_max_pct_bankroll": 0.05, "mise_max_pct_exotique": 0.03,
    }
    out = forgeward.predict_match(m, analysis, pool, "top5")
    one = next(s for s in out["selections"] if s["selection"] == "1")
    check("e.ev", abs(one["ev"] - round(0.50 * 2.10 - 1, 4)) < 1e-12, str(one["ev"]))
    check("e.p", one["p_modele"] == 0.50)
    check("e.lect", (one.get("lecture_cotes") or {}).get("t0") == 1.95, str(one.get("lecture_cotes")))
    check("e.plate", "cote_plate" in (one.get("pieges") or []), str(one.get("pieges")))


def test_pas_poisson():
    import breacher
    src = open(os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE", "market_scorer.py"), encoding="utf-8").read()
    check("n.pas_score_matrix", "score_matrix" not in src)
    check("n.pas_lambda", "lambda_dom" not in src)
    m = breacher.score_matrix(1.4, 1.1)
    st = breacher.matrix_stats(m)
    check("n.poisson_intact", "o2.5" in st and st["o2.5"] > 0)


def main():
    print("=" * 70)
    print("TEST S14 — pieges + /data scorer")
    print("=" * 70)
    test_cote_plate_x10()
    test_marge_22_retire()
    test_marge_anomalique()
    test_cote_figee_sur_news()
    test_lecture_trois_temps()
    test_data_criteres()
    test_ev_p_inchange()
    test_pas_poisson()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S14 pieges : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
