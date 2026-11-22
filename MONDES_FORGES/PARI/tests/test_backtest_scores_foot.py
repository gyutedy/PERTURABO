#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T5 — backtest_scores_foot : walk-forward 1X2, une seule autorite de portes."""
import ast
import csv
import json
import os
import sys
import tempfile
from datetime import date, timedelta

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for _p in (os.path.join(WORLD, "F00_RADAR", "CODEBASE"),
           os.path.join(WORLD, "F02_BREACHER", "CODEBASE"),
           os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import backtest_scores_foot as bsf  # noqa: E402

CHECKS = []
CFG = {"min_league_matches": 4, "min_team_matches": 2, "half_life_days": 100000}
GATES_LOOSE = {"min_matches_oos": 5, "rps_gap_max": 10.0,
               "ece_max": 10.0, "logloss_gap_max": 10.0}
GATES_NOGO = {"min_matches_oos": 5, "rps_gap_max": -1.0,
              "ece_max": 10.0, "logloss_gap_max": 10.0}
TEAMS = ("Arsenal", "Chelsea", "Liverpool", "Everton")
HEADER = ("Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
          "B365H", "B365D", "B365A", "B365CH", "B365CD", "B365CA")


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print("[T] %s — %s%s" % ("PASS" if ok else "FAIL", name, (" | " + note) if note else ""))


def _write_csv(directory, n=120, missing_close_at=None):
    path = os.path.join(directory, "uk_E0_2526.csv")
    start = date(2025, 1, 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for i in range(n):
            h = TEAMS[i % 4]
            a = TEAMS[(i // 4 + 1) % 4]
            if h == a:
                a = TEAMS[(TEAMS.index(h) + 1) % 4]
            row = ["E0", (start + timedelta(days=i)).strftime("%d/%m/%Y"),
                   h, a, str((i + 1) % 3), str((i * 2) % 3),
                   "2.10", "3.30", "3.50", "2.00", "3.40", "3.60"]
            if missing_close_at is not None and i == missing_close_at:
                row[9] = row[10] = row[11] = ""
            w.writerow(row)
    return path


def _run(tmp, **kw):
    out = os.path.join(tmp, "out.json")
    rec = bsf.run(csv_dir=tmp, out_path=out, cfg=CFG, **kw)
    return rec, out


def t_source():
    src = open(os.path.join(WORLD, "F00_RADAR", "CODEBASE",
                            "backtest_scores_foot.py"), encoding="utf-8").read()
    ast.parse(src)
    check("t5.ast", True)
    check("t5.gate_unique", "apply_gates" in src)
    check("t5.pas_set_tickets", "set_tickets" not in src)
    check("t5.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("t5.pas_inventer", "historique_insuffisant" in src and "marche_absent" in src)


def t_walkforward():
    tmp = tempfile.mkdtemp(prefix="pari-t5-")
    _write_csv(tmp)
    rec, out = _run(tmp, gates=GATES_LOOSE)
    check("t5.n_oos", rec["n_oos"] == 40, str(rec["n_oos"]))
    check("t5.n_marche", rec["n_marche"] == 40, str(rec["n_marche"]))
    check("t5.metrics", all(rec.get(k) is not None for k in
                            ("rps_modele", "rps_marche", "logloss_modele", "ece")))
    check("t5.gate_loose", rec["verdict"] in ("GO", "NO-GO"), str(rec["verdict"]))
    check("t5.in_sample", rec["in_sample"] is False)
    check("t5.tickets_gele", rec["tickets_enabled"] is False)
    check("t5.contract", rec["contract"] == "pari.calibration_scores_foot.v1")
    blob = json.load(open(out, encoding="utf-8"))
    check("t5.persiste", blob["contract"] == rec["contract"] and os.path.exists(out))
    check("t5.pas_hole", not rec["holes"], str(rec["holes"]))


def t_verdict_gates():
    tmp = tempfile.mkdtemp(prefix="pari-t5-")
    _write_csv(tmp)
    rec, _ = _run(tmp, gates=GATES_NOGO)
    check("t5.nogo", rec["verdict"] == "NO-GO", str(rec["verdict"]))
    check("t5.nogo_reason", "rps_gap" in rec["reasons"], str(rec["reasons"]))


def t_holes():
    tmp = tempfile.mkdtemp(prefix="pari-t5-")
    _write_csv(tmp, missing_close_at=100)
    rec, _ = _run(tmp, gates=GATES_LOOSE)
    check("t5.marche_absent", rec["n_marche"] == 39 and "marche_absent" in rec["holes"],
          "%s / %s" % (rec["n_marche"], rec["holes"]))
    short = tempfile.mkdtemp(prefix="pari-t5-short-")
    _write_csv(short, n=50)
    rec2, _ = _run(short, gates=GATES_LOOSE)
    check("t5.historique_insuffisant",
          rec2["verdict"] is None and "historique_insuffisant" in rec2["holes"])


def t_anteriorite():
    tmp = tempfile.mkdtemp(prefix="pari-t5-")
    _write_csv(tmp)
    seen = []
    original = bsf._fit_all

    def spy(hist, as_of, cfg=None):
        if hist:
            seen.append(max(r["date"] for r in hist))
        return original(hist, as_of, cfg=cfg)
    bsf._fit_all = spy
    try:
        rec, _ = _run(tmp, cutoff="2025-03-01", gates=GATES_LOOSE)
    finally:
        bsf._fit_all = original
    check("t5.cutoff_oos", rec["n_oos"] > 0, str(rec["n_oos"]))
    check("t5.refit_antérieur", bool(seen) and max(seen) < "2025-03-01", str(max(seen) if seen else None))


def t_gitignore():
    gi = open(os.path.join(WORLD, ".gitignore"), encoding="utf-8").read()
    check("t5.gitignore", "calibration_scores_foot.json" in gi)


def main():
    t_source()
    t_walkforward()
    t_verdict_gates()
    t_holes()
    t_anteriorite()
    t_gitignore()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print("T5 backtest_scores_foot : %d/%d PASS" % (len(CHECKS) - n_fail, len(CHECKS)))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
