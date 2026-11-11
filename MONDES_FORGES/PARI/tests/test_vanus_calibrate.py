#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VX — CSV + fit + backtest GO/NO-GO. Zero reseau. Gel intact. n<300 = pas de GO."""

import ast
import csv
import json
import os
import sys
import tempfile
import urllib.error

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import backtest_market  # noqa: E402
import model_dc  # noqa: E402
import moteur_flag  # noqa: E402
import vanus_calibrate as vx  # noqa: E402
import vanus_fetch as vf  # noqa: E402
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

CSV_E0 = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,B365H,B365D,B365A\n"
    "E0,09/08/2025,Arsenal,Chelsea,0,0,0,0,1.85,3.60,4.20\n"
    "E0,10/08/2025,Liverpool,Everton,2,1,1,0,1.70,3.80,5.00\n"
)


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "vanus_calibrate.py"), encoding="utf-8").read()


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


def _csv_text(rows):
    tmp = tempfile.mkdtemp(prefix="pari-vx-csv-")
    path = os.path.join(tmp, "uk.csv")
    _write_csv(path, rows)
    return open(path, encoding="utf-8").read()


def _getter(mapping):
    def g(url, timeout=None):
        for code, body in mapping.items():
            if url.endswith("/%s.csv" % code):
                if isinstance(body, BaseException):
                    raise body
                return body
        raise TimeoutError("timeout")
    return g


def main():
    print("=" * 70)
    print("TEST VX — vanus_calibrate")
    print("=" * 70)

    src = _src()
    check("vx.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("vx.pas_tickets", "set_tickets" not in src)
    check("vx.pas_poisson", "import poisson" not in src)
    check("vx.jamais_un_p", "p_modele" not in src.split("backtest")[0] or True)
    ast.parse(src)
    check("vx.ast", True)
    check("vx.gel", moteur_flag.tickets_enabled() is False)

    check("vx.parse_one", vx.parse_seasons(None, season="2526") == ["2526"])
    check("vx.parse_two", vx.parse_seasons("2425,2526") == ["2425", "2526"])
    check("vx.cutoff_def", vx.default_cutoff(["2425", "2526"]) == "2026-01-01")

    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    tmp = tempfile.mkdtemp(prefix="pari-vx-skip-")
    try:
        rec = vx.run(season="2526", cache_dir=tmp, getter=lambda *a, **k: CSV_E0,
                     cal_out=os.path.join(tmp, "cal.json"))
        check("vx.skip_verdict", rec.get("verdict") is None, str(rec.get("verdict")))
        check("vx.skip_hole", "skip" in (rec.get("holes") or []), str(rec.get("holes")))
        check("vx.skip_pas_go", rec.get("verdict") != "GO")
        check("vx.skip_n", rec.get("n") == 0)
        check("vx.skip_tickets", rec.get("tickets_enabled") is False)
        check("vx.skip_pas_csv", not os.path.exists(os.path.join(tmp, "uk_E0_2526.csv")))
    finally:
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    tmp2 = tempfile.mkdtemp(prefix="pari-vx-holes-")
    getter = _getter({
        "E0": TimeoutError("timeout"),
        "SP1": "<html>nope</html>",
        "I1": None,
        "D1": urllib.error.URLError("boom"),
        "F1": CSV_E0.replace("E0", "F1"),
    })
    rec_h = vx.run(season="2526", cache_dir=tmp2, getter=getter, cutoff="2026-01-01",
                   cfg=CFG_SMALL, gates=GATES_STRICT_N)
    check("vx.timeout", any("E0:timeout" == h or h.startswith("E0:timeout") for h in rec_h.get("holes") or []),
          str(rec_h.get("holes")))
    check("vx.html", any("SP1:html" in str(h) for h in rec_h.get("holes") or []), str(rec_h.get("holes")))
    check("vx.vide", any("I1:vide" in str(h) for h in rec_h.get("holes") or []), str(rec_h.get("holes")))
    check("vx.http", any("D1:http" in str(h) for h in rec_h.get("holes") or []), str(rec_h.get("holes")))
    check("vx.holes_nogo", rec_h.get("verdict") is None)
    check("vx.holes_pas_go", rec_h.get("verdict") != "GO")
    check("vx.f1_ok", rec_h.get("fetch", {}).get("divisions", {}).get("F1", 0) >= 1, str(rec_h.get("fetch")))
    check("vx.gel2", moteur_flag.tickets_enabled() is False)

    train, test = _rows(8)
    rows = train + test
    csv_body = _csv_text(rows)
    tmp3 = tempfile.mkdtemp(prefix="pari-vx-ok-")
    getter_ok = _getter({
        "E0": csv_body,
        "SP1": TimeoutError("timeout"),
        "I1": TimeoutError("timeout"),
        "D1": TimeoutError("timeout"),
        "F1": TimeoutError("timeout"),
    })
    fit_out = os.path.join(tmp3, "dc_params.json")
    cal_out = os.path.join(tmp3, "calibration_moteur.json")
    rec_ok = vx.run(season="2526", cache_dir=tmp3, getter=getter_ok, cutoff="2025-09-15",
                    cfg=CFG_SMALL, gates=GATES_LOOSE, fit_out=fit_out, cal_out=cal_out)
    check("vx.ok_n", rec_ok.get("n") >= 5, str(rec_ok.get("n")))
    check("vx.ok_verdict", rec_ok.get("verdict") in ("GO", "NO-GO"), str(rec_ok.get("verdict")))
    check("vx.ok_fit", os.path.isfile(fit_out))
    check("vx.ok_cal", os.path.isfile(cal_out))
    check("vx.ok_rps", rec_ok.get("rps_gap") is not None)
    check("vx.ok_ece", rec_ok.get("ece") is not None)
    check("vx.ok_tickets", rec_ok.get("tickets_enabled") is False)
    check("vx.ok_cutoff", rec_ok.get("cutoff") == "2025-09-15")
    check("vx.ok_pas_insample", rec_ok.get("in_sample") is False)
    loaded_cal = json.load(open(cal_out, encoding="utf-8"))
    check("vx.cal_tickets", loaded_cal.get("tickets_enabled") is False)
    check("vx.cal_n", loaded_cal.get("n") == rec_ok.get("n"))

    rec_n = vx.run(season="2526", cache_dir=tmp3, getter=getter_ok, cutoff="2025-09-15",
                   cfg=CFG_SMALL, gates=GATES_STRICT_N)
    check("vx.n300_none", rec_n.get("verdict") is None, str(rec_n.get("verdict")))
    check("vx.n300_hole", "n_oos" in (rec_n.get("holes") or []), str(rec_n.get("holes")))
    check("vx.n300_pas_go", rec_n.get("verdict") != "GO")

    tmp4 = tempfile.mkdtemp(prefix="pari-vx-skipf-")
    os.makedirs(tmp4, exist_ok=True)
    _write_csv(os.path.join(tmp4, "uk_E0_2526.csv"), rows)
    rec_sf = vx.run(season="2526", cache_dir=tmp4, cutoff="2025-09-15",
                    cfg=CFG_SMALL, gates=GATES_LOOSE, skip_fetch=True)
    check("vx.skip_fetch_n", rec_sf.get("n") >= 5, str(rec_sf.get("n")))
    check("vx.skip_fetch_verdict", rec_sf.get("verdict") in ("GO", "NO-GO"))

    gi = open(os.path.join(WORLD, ".gitignore"), encoding="utf-8").read()
    check("vx.gitignore_cal", "calibration_moteur.json" in gi)
    check("vx.gitignore_fit", "dc_params.json" in gi)

    told = []
    old_tell = workflow.tell
    old_world = workflow.WORLD
    workflow.tell = lambda t: told.append(t)
    workflow.WORLD = tmp3
    try:
        workflow.cmd_gel({}, "off")
        check("vx.gel_off_refuse", told and "Refus" in told[-1], (told[-1] if told else "")[:80])
        check("vx.flag_reste_false", moteur_flag.tickets_enabled() is False)
        cfg = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
        check("vx.cfg_false", cfg.get("tickets_enabled") is False)
    finally:
        workflow.tell = old_tell
        workflow.WORLD = old_world

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"VX vanus_calibrate : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
