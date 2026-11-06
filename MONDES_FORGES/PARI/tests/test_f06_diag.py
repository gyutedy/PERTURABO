#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9 — CLV metrique + F06 diagnostic. n<50 = jamais verdict/mise. Zero reseau."""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "LISTEN"))

import clv  # noqa: E402
import diag  # noqa: E402
import doctor  # noqa: E402
import ledger  # noqa: E402
import parse  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_clv_ratio():
    r = clv.clv_ratio(1.7, 1.88)
    expected = 1.7 / 1.88 - 1.0
    check("d.ratio", r is not None and abs(r - expected) < 1e-12, str(r))
    check("d.ratio_pos", clv.clv_ratio(2.0, 1.80) > 0)
    check("d.ratio_trou_none", clv.clv_ratio(1.7, None) is None)
    check("d.ratio_trou_pas_zero", clv.clv_ratio(1.7, None) != 0)
    check("d.ratio_close_1", clv.clv_ratio(1.7, 1.0) is None)
    check("d.ratio_close_0", clv.clv_ratio(1.7, 0) is None)
    check("d.pts", abs(clv.to_pts(0.005) - 0.5) < 1e-12)


def test_aggregate():
    ratios = [0.02, -0.01, 0.04, 0.00]
    mises = [100, 200, 100, 50]
    agg = clv.aggregate(ratios, mises)
    check("d.agg_n", agg["n"] == 4)
    check("d.agg_median", abs(agg["median"] - 0.01) < 1e-12, str(agg["median"]))
    check("d.agg_beat", abs(agg["pct_pos"] - 0.5) < 1e-12, str(agg["pct_pos"]))
    w = (0.02 * 100 + -0.01 * 200 + 0.04 * 100 + 0.00 * 50) / 450
    check("d.agg_mean_w", abs(agg["mean_weighted"] - w) < 1e-12, str(agg["mean_weighted"]))
    empty = clv.aggregate([], [])
    check("d.agg_vide_hole", "clv" in (empty.get("holes") or []))
    check("d.agg_vide_pas_zero", empty.get("median") is None)


def test_ticket_clv_combo():
    snap = {"cote_totale": 3.4, "mise_fc": 100}
    settle = {
        "jambes": [
            {"book_odds_close": 1.80},
            {"book_odds_close": 1.90},
        ]
    }
    r = clv.ticket_clv(snap, settle)
    expected = 3.4 / (1.80 * 1.90) - 1.0
    check("d.combo", r is not None and abs(r - expected) < 1e-12, str(r))
    settle_trou = {"jambes": [{"book_odds_close": 1.80}, {"book_odds_close": None}]}
    check("d.combo_trou", clv.ticket_clv(snap, settle_trou) is None)


def _ticket(rang, resultat, p, cote, close, mise=100):
    return {
        "snap": {
            "rang_ticket": rang,
            "cote_totale": cote,
            "mise_fc": mise,
            "p_aggregee": p,
            "jambes": [{"p_modele": p, "cote": cote, "match_id": "M" + str(rang)}],
        },
        "settle": {
            "rang_ticket": rang,
            "resultat": resultat,
            "pnl_fc": round(mise * (cote - 1), 2) if resultat == "G" else -mise,
            "clv": clv.clv_ratio(cote, close),
            "jambes": [{"book_odds_close": close, "match_id": "M" + str(rang)}],
        },
    }


def _lots(n, resultat="G", p=0.55, cote=1.90, close=1.85, mise=100):
    tix_snap = []
    tix_set = []
    for i in range(n):
        rec = _ticket(i + 1, resultat, p, cote, close, mise)
        tix_snap.append(rec["snap"])
        tix_set.append(rec["settle"])
    return [{
        "token": "L-DIA",
        "created_at": "2026-11-06T00:00:00Z",
        "snapshot_t0": {"tickets": tix_snap},
        "settle": {"tickets": tix_set},
    }]


def test_lock_sous_50():
    lots = _lots(49)
    report = diag.diagnose(lots)
    check("d.lock_49", report.get("locked") is True, str(report.get("n")))
    check("d.lock_n", report.get("n") == 49, str(report.get("n")))
    check("d.lock_verdict", report.get("verdict") is None)
    check("d.lock_mise", report.get("mise") is None)
    check("d.lock_role", report.get("role") == "diagnostic")
    v = diag.as_verdict(report)
    check("d.as_verdict_none", v is None, str(v))
    txt = diag.format_telegram(report)
    check("d.fmt_locked", "LOCKED" in txt and "jamais verdict/mise" in txt.lower()
          or "jamais verdict" in txt, txt[:200])


def test_lock_zero():
    report = diag.diagnose([])
    check("d.zero_lock", report.get("locked") is True)
    check("d.zero_n", report.get("n") == 0)
    check("d.zero_verdict", report.get("verdict") is None)
    check("d.zero_mise", report.get("mise") is None)
    check("d.zero_pev", report.get("p_ev_positif") is None)
    check("d.zero_clv_hole", "clv" in ((report.get("clv") or {}).get("holes") or []))


def test_unlock_50_pas_mise():
    lots = _lots(50)
    report = diag.diagnose(lots)
    check("d.50_n", report.get("n") == 50, str(report.get("n")))
    check("d.50_unlock", report.get("locked") is False)
    check("d.50_verdict", report.get("verdict") is None)
    check("d.50_mise", report.get("mise") is None)
    v = diag.as_verdict(report)
    check("d.50_as_verdict_pas_mise", v is None or v.get("mise") is None, str(v))


def test_platt_beta_mc():
    pairs = [(0.8, 1.0)] * 20 + [(0.2, 0.0)] * 20
    a, b, holes = diag.platt_fit(pairs)
    check("d.platt_ok", a is not None and b is not None and not holes, str((a, b, holes)))
    check("d.platt_a_pos", a > 0, str(a))
    cal_hi = diag.platt_apply(0.8, a, b)
    cal_lo = diag.platt_apply(0.2, a, b)
    check("d.platt_ordre", cal_hi is not None and cal_lo is not None and cal_hi > cal_lo,
          str((cal_hi, cal_lo)))
    a2, b2, _ = diag.platt_fit([(0.5, 1)])
    check("d.platt_n1_trou", a2 is None and "n_platt" in (diag.platt_fit([(0.5, 1)])[2]))

    bb = diag.beta_binomial([1, 1, 0, 1])
    check("d.bb_ok", bb is not None and bb["n"] == 4 and bb["k"] == 3)
    check("d.bb_mean", abs(bb["mean"] - 4 / 6) < 1e-12, str(bb["mean"]))
    check("d.bb_vide", diag.beta_binomial([]) is None)

    obs = [{"p": 0.70, "cote": 1.60, "mise": 100, "y": 1.0} for _ in range(8)]
    p1 = diag.p_ev_positif(obs, draws=400, seed=42)
    p2 = diag.p_ev_positif(obs, draws=400, seed=42)
    p3 = diag.p_ev_positif(obs, draws=400, seed=7)
    check("d.mc_seede", p1 is not None and p1 == p2, str(p1))
    check("d.mc_seed_change", p3 is not None and p3 != p1, str((p1, p3)))
    check("d.mc_range", 0.0 <= p1 <= 1.0)


def test_cibles_config():
    cfg = clv.load_config()
    check("d.cfg_beat", abs(float(cfg["clv_beat_pct"]) - 0.55) < 1e-12)
    check("d.cfg_median_pt", abs(float(cfg["clv_median_pt"]) - 0.5) < 1e-12)
    check("d.cfg_n_lock", int(cfg["n_lock"]) == 50)
    check("d.cfg_n_var", int(cfg["n_variance"]) == 30)
    check("d.cfg_seed", int(cfg["mc_seed"]) == 42)
    report = diag.diagnose(_lots(3))
    cibles = report.get("cibles") or {}
    check("d.rep_cible_beat", abs(float(cibles.get("beat_pct")) - 0.55) < 1e-12)
    check("d.rep_cible_med", abs(float(cibles.get("median_pt")) - 0.5) < 1e-12)


def test_settle_clv_pose():
    tmp = tempfile.mkdtemp(prefix="pari_s9_")
    old = ledger.LOTS_PATH
    try:
        lots_path = os.path.join(tmp, "lots.json")
        ledger.LOTS_PATH = lots_path
        tix = {
            "generated_at": "2026-11-06T00:00:00Z",
            "tickets": [{
                "rang_ticket": 1,
                "cote_totale": 1.7,
                "mise_fc": 100,
                "p_aggregee": 0.62,
                "jambes": [{
                    "match_id": "M1",
                    "match": "Arsenal vs Chelsea",
                    "marche": "1X2",
                    "selection": "1",
                    "selection_label": "Victoire Domicile",
                    "cote": 1.7,
                    "p_modele": 0.62,
                }],
            }],
            "budget": {"budget_fc": 300, "alloue_fc": 100, "reste_fc": 200},
            "warnings": [],
            "regles": {},
        }
        lot = ledger.freeze_lot(
            "L-S9A", "PARI-TEST", "C-ZZZ", tix,
            ledger.legs_from_tickets(tix["tickets"]), 300, 100)
        ledger.append_lot(lot, lots_path)
        csv_path = os.path.join(tmp, "settle.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("HomeTeam,AwayTeam,FTR\nArsenal,Chelsea,H\n")
        odds_dir = os.path.join(tmp, "odds")
        os.makedirs(odds_dir, exist_ok=True)
        with open(os.path.join(odds_dir, "latest_t0.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": "t0", "scanned": [
                {"id": "M1", "cotes_marche": {"1": 1.88}}
            ]}, f)
        got, err = ledger.settle_lot("L-S9A", csv_path, lots_path, odds_dir=odds_dir)
        check("d.set_err", err is None, str(err))
        t = ((got.get("settle") or {}).get("tickets") or [{}])[0]
        expected = 1.7 / 1.88 - 1.0
        check("d.set_clv", t.get("clv") is not None and abs(t["clv"] - expected) < 1e-12,
              str(t.get("clv")))
        check("d.set_clv_pas_zero", t.get("clv") != 0)
        agg = (got.get("settle") or {}).get("clv") or {}
        check("d.set_agg_n", agg.get("n") == 1, str(agg))
        rec = ((got.get("journal") or {}).get("outcome") or {}).get("tickets") or [{}]
        check("d.set_jnl_clv", rec[0].get("clv") is not None
              and abs(rec[0]["clv"] - expected) < 1e-12, str(rec[0].get("clv")))
    finally:
        ledger.LOTS_PATH = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_doctor_variance_n30():
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    tmp = tempfile.mkdtemp(prefix="pari_s9doc_")
    try:
        lots = {
            "lots": [
                {
                    "token": "L-N30",
                    "created_at": "2026-11-01T00:00:00Z",
                    "clv": 0.01,
                }
            ]
        }
        os.makedirs(os.path.join(tmp, "ARCHIVUM", "learnings"), exist_ok=True)
        with open(os.path.join(tmp, "ARCHIVUM", "learnings", "lots.json"), "w", encoding="utf-8") as f:
            json.dump(lots, f)
        rec = doctor.check_clv(tmp, now=now)
        check("d.doc_n1", rec.get("n") == 1, str(rec.get("n")))
        check("d.doc_var", "n<30" in (rec.get("note") or ""), str(rec.get("note")))
        check("d.doc_pas_alerte", rec.get("alerte") is False)
        check("d.doc_pas_zero", rec.get("median_30j") != 0 or rec.get("median_pt") is not None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_parse_data_diag():
    chat = "7710898895"
    r = parse.parse_update({
        "message": {"chat": {"id": chat}, "text": "/data diag"},
    }, chat)
    check("d.parse_diag", r.get("ok") and r.get("cmd") == "/data diag", str(r.get("cmd")))
    h = parse.parse_update({
        "message": {"chat": {"id": chat}, "text": "/help"},
    }, chat)
    txt = h.get("reply") or ""
    check("d.help_diag", "/data diag" in txt, txt)


def test_jamais_mise_dans_diag():
    src = open(os.path.join(WORLD, "F06_TRACKER", "CODEBASE", "diag.py"), encoding="utf-8").read()
    check("d.src_lock50", "n < lock_at" in src or "n < 50" in src or "locked" in src)
    check("d.src_verdict_none", '"verdict": None' in src or "'verdict': None" in src)
    check("d.src_mise_none", '"mise": None' in src or "'mise': None" in src)
    check("d.src_pas_poisson", "import breacher" not in src and "dixon" not in src.lower())


def main():
    print("=" * 70)
    print("TEST S9 — CLV metrique + F06 diagnostic")
    print("=" * 70)
    test_clv_ratio()
    test_aggregate()
    test_ticket_clv_combo()
    test_lock_sous_50()
    test_lock_zero()
    test_unlock_50_pas_mise()
    test_platt_beta_mc()
    test_cibles_config()
    test_settle_clv_pose()
    test_doctor_variance_n30()
    test_parse_data_diag()
    test_jamais_mise_dans_diag()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S9 f06_diag : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
