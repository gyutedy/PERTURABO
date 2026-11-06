#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 — empirique O2.5 + walk-forward seede. Zero reseau. Jamais in-sample."""

import csv
import io
import os
import random
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "TYRANT", "CODEBASE"))

import empirique  # noqa: E402
import radar  # noqa: E402
import tyrant  # noqa: E402
import walkforward  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_o25_rate_sp1():
    import backtest
    rows = backtest.load_csv(os.path.join(WORLD, "tests", "fixtures", "uk_SP1_2526.csv"))
    rate, n = empirique.o25_rate(rows)
    check("bt.o25_n", n == 6, str(n))
    hits = sum(1 for r in rows if int(r["FTHG"]) + int(r["FTAG"]) >= 3)
    check("bt.o25_rate", abs(rate - hits / 6) < 1e-12, str(rate))


def test_gap_flag():
    hit, diff = empirique.gap_flag(0.70, 0.40)
    check("bt.gap_hit", hit is True, str(diff))
    check("bt.gap_diff", abs(diff - 0.30) < 1e-12, str(diff))
    hit2, _ = empirique.gap_flag(0.50, 0.40)
    check("bt.gap_ok", hit2 is False)
    hit3, d3 = empirique.gap_flag(0.50, None)
    check("bt.gap_trou", hit3 is False and d3 is None)


def test_stamp_flag_radar():
    fx = os.path.join(WORLD, "tests", "fixtures")
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    ms = [
        {"id": "M1", "dom": "Ath Madrid", "ext": "Barcelona", "league_code": "SP1",
         "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "Levante", "ext": "Sevilla", "league_code": "SP1",
         "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    scan = radar.run_radar(ms, top=5, league_code="SP1", csv_dir=fx)
    rate = scan.get("o2.5_empirique")
    check("bt.radar_emp", rate is not None and 0 < rate < 1, str(rate))
    a0 = (scan.get("analyses") or [{}])[0]
    p = (a0.get("probas") or {}).get("o2.5")
    hit, _ = empirique.gap_flag(p, rate)
    flags = ((a0.get("data_quality") or {}).get("flags") or [])
    if hit:
        check("bt.radar_flag", empirique.FLAG in flags, str(flags))
    else:
        check("bt.radar_noflag", empirique.FLAG not in flags, str((p, rate, flags)))


def test_stamp_trou():
    empty = tempfile.mkdtemp(prefix="pari-emp-")
    analyse = {
        "league_code": "ZZ",
        "ligue_moyennes": {"league_code": "ZZ"},
        "analyses": [{"id": "M1", "probas": {"o2.5": 0.9}, "data_quality": {"flags": []}}],
    }
    empirique.stamp(analyse, csv_dir=empty)
    check("bt.trou_hole", "o2.5_empirique" in (analyse.get("empirique_holes") or []))
    check("bt.trou_rate", analyse.get("o2.5_empirique") is None)
    flags = (analyse["analyses"][0].get("data_quality") or {}).get("flags") or []
    check("bt.trou_pas_flag", empirique.FLAG not in flags, str(flags))


def test_tyrant_flag_pas_nobet():
    carte = {"verdicts": [{"id": "M1", "verdict": "GO", "raisons": [], "flags": []}]}
    analysis = {
        "o2.5_empirique": 0.30,
        "analyses": [{"id": "M1", "probas": {"o2.5": 0.70}}],
    }
    tyrant.stamp_empirique(carte, analysis)
    v = carte["verdicts"][0]
    check("bt.ty_go", v["verdict"] == "GO")
    check("bt.ty_flag", tyrant.FLAG_EMPIRIQUE in (v.get("flags") or []), str(v.get("flags")))
    check("bt.ty_raison", tyrant.FLAG_EMPIRIQUE in (v.get("raisons") or []))
    carte2 = {"verdicts": [{"id": "M1", "verdict": "GO", "raisons": [], "flags": []}]}
    tyrant.stamp_empirique(carte2, {"analyses": [{"id": "M1", "probas": {"o2.5": 0.5}}]})
    check("bt.ty_trou_pas_flag", tyrant.FLAG_EMPIRIQUE not in (carte2["verdicts"][0].get("flags") or []))


def _seeded_rows(n=40, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        day = 1 + (i % 28)
        month = 8 if i < n // 2 else 10
        h = rng.choice([0, 1, 2, 3])
        a = rng.choice([0, 1, 2])
        cote = 1.70 + rng.random() * 0.60
        ftr = "H" if h > a else ("A" if a > h else "D")
        rows.append({
            "Div": "E0",
            "Date": f"{day:02d}/{month:02d}/2025",
            "HomeTeam": "A",
            "AwayTeam": "B",
            "FTHG": str(h),
            "FTAG": str(a),
            "FTR": ftr,
            "Avg>2.5": f"{cote:.3f}",
            "AvgH": "2.10",
            "AvgD": "3.40",
            "AvgA": "3.50",
        })
    return rows


def test_cutoff_split():
    rows = _seeded_rows()
    train, test, hole = walkforward.split_cutoff(rows, "2025-09-15")
    check("bt.cut_hole", hole is None)
    check("bt.cut_train", len(train) == 20, str(len(train)))
    check("bt.cut_test", len(test) == 20, str(len(test)))
    from datetime import datetime
    cut = datetime(2025, 9, 15)
    check("bt.cut_train_before", all(walkforward.backtest._dkey(r) < cut for r in train))
    check("bt.cut_test_on_or_after", all(walkforward.backtest._dkey(r) >= cut for r in test))


def test_jamais_in_sample():
    rows = _seeded_rows()
    rec = walkforward.walk_forward(rows, "2025-09-15")
    check("bt.wf_not_insample", rec.get("in_sample") is False)
    check("bt.wf_n_train", rec.get("n_train") == 20, str(rec.get("n_train")))
    check("bt.wf_n_test", rec.get("n_test") == 20, str(rec.get("n_test")))
    check("bt.wf_cutoff", rec.get("cutoff") == "2025-09-15")
    m = rec.get("metrics") or {}
    check("bt.wf_brier", m.get("brier_o2.5") is not None and 0 <= m["brier_o2.5"] <= 1, str(m.get("brier_o2.5")))
    check("bt.wf_rps", m.get("rps_1x2") is not None and 0 <= m["rps_1x2"] <= 1, str(m.get("rps_1x2")))
    check("bt.wf_ece", m.get("ece_o2.5") is not None and m["ece_o2.5"] >= 0, str(m.get("ece_o2.5")))
    check("bt.wf_n_eval", rec.get("n_eval") == 20, str(rec.get("n_eval")))
    check("bt.wf_odds", m.get("n_odds_o2.5") == 20, str(m.get("n_odds_o2.5")))
    if m.get("n_ev3"):
        check("bt.wf_hit", m.get("hit_rate_ev3") is not None)
        check("bt.wf_yield", m.get("yield_kelly_1_4") is not None)
    else:
        check("bt.wf_hit_none", m.get("hit_rate_ev3") is None)
        check("bt.wf_yield_none", True)


def test_cutoff_absent_hole():
    rec = walkforward.walk_forward(_seeded_rows(), None)
    check("bt.cut_abs", "cutoff_absent" in (rec.get("holes") or []), str(rec.get("holes")))
    check("bt.cut_abs_metrics", rec.get("metrics") == {})


def test_odds_absentes_hole():
    rows = []
    for i in range(8):
        rows.append({
            "Div": "E0", "Date": f"0{i+1}/08/2025", "FTHG": "1", "FTAG": "1", "FTR": "D",
            "HomeTeam": "A", "AwayTeam": "B",
        })
    for i in range(8):
        rows.append({
            "Div": "E0", "Date": f"0{i+1}/10/2025", "FTHG": "2", "FTAG": "2", "FTR": "D",
            "HomeTeam": "A", "AwayTeam": "B",
        })
    rec = walkforward.walk_forward(rows, "2025-09-15")
    check("bt.odds_hole", "odds" in (rec.get("holes") or []), str(rec.get("holes")))
    check("bt.odds_hit_none", (rec.get("metrics") or {}).get("hit_rate_ev3") is None)
    check("bt.odds_yield_none", (rec.get("metrics") or {}).get("yield_kelly_1_4") is None)


def test_brier_seede():
    check("bt.brier0", abs(walkforward.brier(0.5, 0.5) - 0.0) < 1e-12)
    check("bt.brier1", abs(walkforward.brier(1.0, 0.0) - 1.0) < 1e-12)
    rps_h = walkforward.rps_1x2(1.0, 0.0, 0.0, "H")
    check("bt.rps_sure", abs(rps_h) < 1e-12, str(rps_h))
    e = walkforward.ece([(0.8, 1.0), (0.8, 1.0), (0.2, 0.0), (0.2, 0.0)], bins=2)
    check("bt.ece_ok", e is not None and e < 0.3, str(e))


def test_kelly():
    f = walkforward.kelly_frac(0.6, 2.0, 0.25)
    full = (0.6 * 2.0 - 1.0) / (2.0 - 1.0)
    check("bt.kelly_q", abs(f - 0.25 * full) < 1e-12, str(f))
    check("bt.kelly_zero", walkforward.kelly_frac(0.3, 2.0, 0.25) == 0.0)
    check("bt.kelly_trou", walkforward.kelly_frac(0.6, None, 0.25) is None)


def test_report_write():
    tmp = tempfile.mkdtemp(prefix="pari-wf-")
    path = os.path.join(tmp, "seed.csv")
    rows = _seeded_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    open(path, "w", encoding="utf-8").write(buf.getvalue())
    out = os.path.join(tmp, "backtest_report.json")
    rec = walkforward.run_file(path, "2025-09-15", out=out)
    check("bt.rep_file", os.path.exists(out))
    import json
    blob = json.load(open(out, encoding="utf-8"))
    check("bt.rep_cutoff", blob.get("cutoff") == rec.get("cutoff"))
    check("bt.rep_not_insample", blob.get("in_sample") is False)


def test_cfg():
    cfg = empirique.load_config()
    check("bt.cfg_gap", abs(cfg["o25_gap"] - 0.20) < 1e-12)
    check("bt.cfg_ev", abs(cfg["ev_min"] - 0.03) < 1e-12)
    check("bt.cfg_kelly", abs(cfg["kelly_frac"] - 0.25) < 1e-12)


def main():
    print("=" * 70)
    print("TEST S7 — backtest empirique + walk-forward")
    print("=" * 70)
    test_o25_rate_sp1()
    test_gap_flag()
    test_stamp_flag_radar()
    test_stamp_trou()
    test_tyrant_flag_pas_nobet()
    test_cutoff_split()
    test_jamais_in_sample()
    test_cutoff_absent_hole()
    test_odds_absentes_hole()
    test_brier_seede()
    test_kelly()
    test_report_write()
    test_cfg()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S7 backtest : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
