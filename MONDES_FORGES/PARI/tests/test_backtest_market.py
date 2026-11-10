#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2c — backtest_market calibration RPS/ECE. Zero reseau. Gel intact."""

import ast
import csv
import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import backtest_market  # noqa: E402
import model_dc  # noqa: E402
import moteur_flag  # noqa: E402
import workflow  # noqa: E402

CHECKS = []
CFG_SMALL = {
    "half_life_days": 60.0,
    "min_team_matches": 4,
    "min_league_matches": 20,
    "sigma_att": 0.35,
    "sigma_def": 0.35,
    "sigma_rho": 0.25,
    "elo_scale": 0.0015,
    "elo_prior_weight": 0.5,
    "elo_prior_full_matches": 10,
    "max_iterations": 80,
    "tol": 1e-6,
}
GATES_LOOSE = {
    "rps_gap_max": 1.0,
    "ece_max": 1.0,
    "logloss_gap_max": 10.0,
    "min_matches_oos": 5,
}
GATES_STRICT_N = {
    "rps_gap_max": 1.0,
    "ece_max": 1.0,
    "logloss_gap_max": 10.0,
    "min_matches_oos": 300,
}


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "backtest_market.py"), encoding="utf-8").read()


def _odds(p1, px, p2, margin=1.08):
    return {
        "home": round(margin / p1, 3),
        "draw": round(margin / px, 3),
        "away": round(margin / p2, 3),
    }


def _rows(n_test=10):
    teams = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    att = {"Alpha": 0.4, "Beta": 0.2, "Gamma": 0.0, "Delta": -0.1, "Epsilon": -0.2, "Zeta": -0.3}
    deff = {"Alpha": 0.3, "Beta": 0.1, "Gamma": 0.0, "Delta": -0.1, "Epsilon": -0.2, "Zeta": -0.3}
    train, test = [], []
    day = 1
    for h in teams:
        for a in teams:
            if h == a:
                continue
            lh, la = model_dc.lambdas(0.25, 0.25, att[h], deff[h], att[a], deff[a])
            i = int(round(lh))
            j = int(round(la))
            pm = backtest_market.p_modele_1x2(lh, la, -0.13)
            ov = _odds(pm[0], pm[1], pm[2])
            rec = {
                "div": "E0", "home": h, "away": a, "fthg": i, "ftag": j,
                "date": "2025-08-%02d" % min(day, 28),
                "ouverts": ov,
            }
            train.append(rec)
            day = day + 1 if day < 28 else 1
    pairs = [(h, a) for h in teams for a in teams if h != a]
    for k in range(n_test):
        h, a = pairs[k % len(pairs)]
        lh, la = model_dc.lambdas(0.25, 0.25, att[h], deff[h], att[a], deff[a])
        i = int(round(lh))
        j = int(round(la))
        rec = {
            "div": "E0", "home": h, "away": a, "fthg": i, "ftag": j,
            "date": "2025-10-%02d" % (1 + (k % 28)),
            "ouverts": {"home": 2.50, "draw": 3.40, "away": 2.80},
        }
        test.append(rec)
    return train, test


def _write_csv(path, rows):
    fields = [
        "Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
        "B365H", "B365D", "B365A",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            ov = r.get("ouverts") or {}
            w.writerow({
                "Div": r["div"], "Date": r["date"],
                "HomeTeam": r["home"], "AwayTeam": r["away"],
                "FTHG": r["fthg"], "FTAG": r["ftag"],
                "B365H": ov.get("home", ""),
                "B365D": ov.get("draw", ""),
                "B365A": ov.get("away", ""),
            })


def main():
    print("=" * 70)
    print("TEST V2c — backtest_market")
    print("=" * 70)

    g_go = backtest_market.apply_gates(400, -0.01, 0.02, -0.02)
    check("v2c.gate_go", g_go["verdict"] == "GO", str(g_go))
    check("v2c.gate_go_reasons", g_go["reasons"] == [])

    g_rps = backtest_market.apply_gates(400, 0.01, 0.01, -0.01)
    check("v2c.gate_rps_nogo", g_rps["verdict"] == "NO-GO" and "rps_gap" in g_rps["reasons"], str(g_rps))

    g_ece = backtest_market.apply_gates(400, -0.01, 0.05, -0.01)
    check("v2c.gate_ece_nogo", g_ece["verdict"] == "NO-GO" and "ece" in g_ece["reasons"], str(g_ece))

    g_ll = backtest_market.apply_gates(400, -0.01, 0.01, 0.02)
    check("v2c.gate_ll_nogo", g_ll["verdict"] == "NO-GO" and "logloss_gap" in g_ll["reasons"], str(g_ll))

    g_n = backtest_market.apply_gates(12, -0.50, 0.001, -0.50)
    check("v2c.gate_n_none", g_n["verdict"] is None and "n_oos" in g_n["holes"], str(g_n))
    check("v2c.gate_n_pas_go", g_n["verdict"] != "GO")

    g_miss = backtest_market.apply_gates(400, None, 0.01, -0.01)
    check("v2c.gate_rps_hole", g_miss["verdict"] is None and "rps" in g_miss["holes"], str(g_miss))

    cfg = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
    check("v2c.cfg_rps0", cfg["gates"]["rps_gap_max"] == 0.0)
    check("v2c.cfg_ece03", cfg["gates"]["ece_max"] == 0.03)
    check("v2c.cfg_ll0", cfg["gates"]["logloss_gap_max"] == 0.0)
    check("v2c.cfg_n300", cfg["gates"]["min_matches_oos"] == 300)
    check("v2c.gel", moteur_flag.tickets_enabled() is False)
    check("v2c.cfg_false", cfg.get("tickets_enabled") is False)

    check("v2c.imp_none", backtest_market.implied_1x2(None, 3.0, 4.0) is None)
    check("v2c.imp_le1", backtest_market.implied_1x2(1.0, 3.0, 4.0) is None)
    got = backtest_market.implied_1x2(2.0, 4.0, 4.0)
    check("v2c.imp_ok", got is not None and abs(sum(got) - 1.0) < 1e-12, str(got))

    check("v2c.out_00", backtest_market.outcome_of(0, 0) == "D")
    check("v2c.out_h", backtest_market.outcome_of(2, 1) == "H")
    check("v2c.out_none", backtest_market.outcome_of(None, 0) is None)

    ll = backtest_market.logloss_1x2(1.0, 0.0, 0.0, "H")
    check("v2c.ll_sure", ll is not None and abs(ll) < 1e-9, str(ll))
    check("v2c.ll_none", backtest_market.logloss_1x2(0.4, 0.3, 0.3, "Z") is None)

    rec_cut = backtest_market.evaluate([], None)
    check("v2c.cut_abs", "cutoff_absent" in (rec_cut.get("holes") or []), str(rec_cut.get("holes")))
    check("v2c.cut_abs_verdict", rec_cut.get("verdict") is None)

    train, test = _rows(8)
    rows = train + test
    rec = backtest_market.evaluate(rows, "2025-09-15", cfg=CFG_SMALL, gates=GATES_LOOSE)
    check("v2c.wf_not_insample", rec.get("in_sample") is False)
    check("v2c.wf_cutoff", rec.get("cutoff") == "2025-09-15")
    check("v2c.wf_n_train", rec.get("n_train") == 30, str(rec.get("n_train")))
    check("v2c.wf_n_test", rec.get("n_test") == 8, str(rec.get("n_test")))
    check("v2c.wf_n", rec.get("n") >= 5, str(rec.get("n")))
    check("v2c.rps_m", rec.get("rps_modele") is not None, str(rec.get("rps_modele")))
    check("v2c.rps_k", rec.get("rps_marche") is not None, str(rec.get("rps_marche")))
    check("v2c.rps_gap", rec.get("rps_gap") is not None)
    check("v2c.ece", rec.get("ece") is not None and rec["ece"] >= 0, str(rec.get("ece")))
    check("v2c.ll_m", rec.get("logloss_modele") is not None)
    check("v2c.verdict_set", rec.get("verdict") in ("GO", "NO-GO"), str(rec.get("verdict")))
    check("v2c.pas_elo1500", "1500" not in json.dumps(rec))

    rec_n = backtest_market.evaluate(rows, "2025-09-15", cfg=CFG_SMALL, gates=GATES_STRICT_N)
    check("v2c.n_oos_none", rec_n.get("verdict") is None, str(rec_n.get("verdict")))
    check("v2c.n_oos_hole", "n_oos" in (rec_n.get("holes") or []), str(rec_n.get("holes")))

    zrow = dict(test[0])
    zrow["fthg"] = 0
    zrow["ftag"] = 0
    rec_z = backtest_market.evaluate(train + [zrow], "2025-09-15", cfg=CFG_SMALL, gates=GATES_LOOSE)
    check("v2c.score00", rec_z.get("n", 0) >= 1, str(rec_z.get("n")))
    check("v2c.score00_pas_hole", "score_ft" not in (rec_z.get("holes") or []), str(rec_z.get("holes")))

    bad = dict(test[0])
    bad["ouverts"] = {"home": 1.0, "draw": 3.4, "away": 2.8}
    rec_bad = backtest_market.evaluate(train + [bad], "2025-09-15", cfg=CFG_SMALL, gates=GATES_LOOSE)
    check("v2c.cote_le1", rec_bad.get("n", 1) == 0 or "cotes_1x2" in (rec_bad.get("holes") or []),
          str((rec_bad.get("n"), rec_bad.get("holes"))))
    check("v2c.cote_le1_skip", rec_bad.get("n_skipped", 0) >= 1, str(rec_bad.get("n_skipped")))

    ghost = dict(test[0])
    ghost["home"] = "Ghost"
    rec_g = backtest_market.evaluate(train + [ghost], "2025-09-15", cfg=CFG_SMALL, gates=GATES_LOOSE)
    check("v2c.ghost_skip", rec_g.get("n", 1) == 0 or "equipe_absente" in (rec_g.get("holes") or []),
          str(rec_g.get("holes")))

    tmp = tempfile.mkdtemp(prefix="pari-v2c-")
    absent = backtest_market.run_dir(os.path.join(tmp, "nope"), "2025-09-15")
    check("v2c.dir_absent", "dossier_absent" in (absent.get("holes") or []), str(absent.get("holes")))
    check("v2c.dir_absent_verdict", absent.get("verdict") is None)

    vide = backtest_market.run_dir(tmp, "2025-09-15")
    check("v2c.dir_vide", "aucune_ligne" in (vide.get("holes") or []), str(vide.get("holes")))

    csv_dir = os.path.join(tmp, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    _write_csv(os.path.join(csv_dir, "E0.csv"), rows)
    learn = os.path.join(tmp, "ARCHIVUM", "learnings")
    os.makedirs(learn, exist_ok=True)
    outp = os.path.join(learn, "calibration_moteur.json")
    rec_cli = backtest_market.run_dir(csv_dir, "2025-09-15", out=outp, cfg=CFG_SMALL, gates=GATES_LOOSE)
    check("v2c.roundtrip_n", rec_cli.get("n") >= 5, str(rec_cli.get("n")))
    loaded = backtest_market.load(outp)
    check("v2c.roundtrip", loaded is not None and loaded.get("n") == rec_cli.get("n"))
    check("v2c.blob_keys", all(k in loaded for k in (
        "generated_at", "n", "verdict", "rps_modele", "rps_marche", "ece",
        "logloss_modele", "logloss_marche")), str(sorted(loaded)[:8]))

    blob_nogo = dict(loaded)
    blob_nogo["verdict"] = "NO-GO"
    json.dump(blob_nogo, open(outp, "w"), indent=2)

    told = []
    old_tell = workflow.tell
    old_world = workflow.WORLD
    workflow.tell = lambda t: told.append(t)
    workflow.WORLD = tmp
    try:
        st = {}
        workflow.cmd_modele(st, "")
        check("v2c.modele_mesure", told and "verdict=" in told[-1], (told[-1] if told else "")[:80])
        told.clear()
        workflow.cmd_gel(st, "off")
        check("v2c.gel_off_refuse", told and "Refus" in told[-1], (told[-1] if told else "")[:80])
        check("v2c.flag_reste_false", moteur_flag.tickets_enabled() is False)
        check("v2c.cfg_reste_false", json.load(open(
            os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"
        )).get("tickets_enabled") is False)
    finally:
        workflow.tell = old_tell
        workflow.WORLD = old_world

    src = _src()
    check("v2c.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("v2c.pas_tickets", "set_tickets" not in src)
    ast.parse(src)
    check("v2c.ast_ok", True)

    gi = open(os.path.join(WORLD, ".gitignore"), encoding="utf-8").read()
    check("v2c.gitignore", "calibration_moteur.json" in gi)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V2c backtest_market : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
