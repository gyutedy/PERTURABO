#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S16 — backtest poids B1-B6. n<50 lock. Une seule maj. Seed 42. Zero reseau."""

import json
import os
import shutil
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))

import backtest_weights as bw  # noqa: E402
import market_scorer as scorer  # noqa: E402

CHECKS = []
SEED = 42


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _lot(n_g, n_p, ligue="E0", marche="OU_2.5", token="L-AAA"):
    tickets_s = []
    tickets_t = []
    for i in range(n_g + n_p):
        res = "G" if i < n_g else "P"
        tickets_s.append({
            "rang_ticket": i + 1,
            "resultat": res,
            "pnl_fc": 10 if res == "G" else -10,
            "jambes": [{"marche": marche, "match_id": "M1", "selection": "o2.5"}],
        })
        tickets_t.append({
            "rang_ticket": i + 1,
            "mise_fc": 100,
            "jambes": [{"marche": marche, "match_id": "M1", "selection": "o2.5"}],
        })
    return {
        "token": token,
        "league_code": ligue,
        "bundle_id": "B-AAA",
        "snapshot_t0": {"tickets": tickets_t},
        "settle": {"tickets": tickets_s},
    }


def _profiles():
    return {
        "note": "a priori",
        "version": 1,
        "overround_max": 0.20,
        "cote_min": 1.10,
        "default": {
            "seuil": 0.50,
            "poids": {"B1": 0.30, "B2": 0.20, "B3": 0.20, "B4": 0.15, "B5": 0.10, "B6": 0.05},
        },
        "marches": {"OU_2.5": {"seuil": 0.50}},
    }


def test_n_lock():
    lots = [_lot(10, 10)]
    rec = bw.retune(lots, "/tmp/nope.json", seed=SEED, apply=False)
    check("w.lock", rec.get("locked") is True and rec.get("n") == 20, str(rec.get("n")))
    check("w.lock_reason", rec.get("reason") == "n_lock")
    check("w.lock_not_written", rec.get("written") is False)


def test_n50_propose():
    lots = [_lot(30, 20)]
    rec = bw.propose(lots, _profiles(), seed=SEED)
    check("w.n50", rec.get("n") == 50 and rec.get("locked") is False, str(rec.get("n")))
    prop = rec.get("proposed") or {}
    d = (prop.get("default") or {}).get("poids") or {}
    s = sum(d[k] for k in bw.KEYS)
    check("w.renorm", abs(s - 1.0) < 1e-6, str(s))
    check("w.seed", rec.get("seed") == 42)


def test_write_once():
    tmp = tempfile.mkdtemp(prefix="pari-bw-")
    try:
        path = os.path.join(tmp, "market_profiles.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_profiles(), f)
        jpath = os.path.join(tmp, "scorer_weight_journal.json")
        lots = [_lot(40, 10)]
        rec = bw.retune(lots, path, seed=SEED, apply=True, journal=jpath, now="2026-11-07T00:00:00Z")
        check("w.write", rec.get("written") is True, str(rec.get("reason")))
        blob = json.load(open(path, encoding="utf-8"))
        check("w.version", blob.get("version") == 2, str(blob.get("version")))
        check("w.flag", blob.get("s16_updated") is True)
        rec2 = bw.retune(lots, path, seed=SEED, apply=True, journal=jpath)
        check("w.once", rec2.get("written") is False and rec2.get("reason") == "already_updated")
        j = json.load(open(jpath, encoding="utf-8"))
        check("w.journal_one", len(j.get("events") or []) == 1, str(len(j.get("events") or [])))
        a_priori = json.load(open(os.path.join(WORLD, "ARCHIVUM", "learnings", "market_profiles.json")))
        check("w.prod_intact", a_priori.get("version") == 1 and not a_priori.get("s16_updated"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cell_ligue():
    lots = [_lot(8, 0, ligue="E0", marche="OU_2.5")] + [_lot(8, 0, ligue="SP1", marche="1X2", token="L-BBB")]
    lots = lots  # 16 tickets — locked
    rec = bw.propose(lots + [_lot(20, 14, ligue="E0", marche="OU_2.5", token="L-CCC")], _profiles(), seed=SEED)
    check("w.cells_n", rec.get("n") >= 50, str(rec.get("n")))
    ligues = (rec.get("proposed") or {}).get("ligues") or {}
    check("w.ligue_e0", "E0" in ligues, str(list(ligues)))


def test_profile_for_ligue():
    tmp = tempfile.mkdtemp(prefix="pari-pf-")
    try:
        p = os.path.join(tmp, "p.json")
        blob = _profiles()
        blob["ligues"] = {"E0": {"marches": {"OU_2.5": {"seuil": 0.55, "poids": {"B1": 0.40, "B2": 0.10, "B3": 0.20, "B4": 0.15, "B5": 0.10, "B6": 0.05}}}}}
        with open(p, "w") as f:
            json.dump(blob, f)
        loaded = scorer.load_profiles(p)
        rec = scorer.profile_for("OU_2.5", loaded, ligue="E0")
        check("w.overlay_seuil", abs(rec["seuil"] - 0.55) < 1e-12, str(rec["seuil"]))
        check("w.overlay_b1", abs(rec["poids"]["B1"] - 0.40) < 1e-12, str(rec["poids"]["B1"]))
        rec2 = scorer.profile_for("OU_2.5", loaded, ligue="SP1")
        check("w.no_overlay", abs(rec2["seuil"] - 0.50) < 1e-12)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_attente_ignore():
    lot = _lot(0, 0)
    lot["settle"]["tickets"] = [{"rang_ticket": 1, "resultat": "EN_ATTENTE", "jambes": []}]
    lot["snapshot_t0"]["tickets"] = [{"rang_ticket": 1, "jambes": []}]
    n = bw.count_real_tickets([lot])
    check("w.attente_zero", n == 0)


def main():
    print("=" * 70)
    print("TEST S16 — backtest poids scorer seed 42")
    print("=" * 70)
    test_n_lock()
    test_n50_propose()
    test_write_once()
    test_cell_ligue()
    test_profile_for_ligue()
    test_attente_ignore()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S16 weights : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
