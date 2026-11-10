#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2b — engine_dc cablage breacher. Zero reseau. Gel intact. Pas de calibration."""

import ast
import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import breacher  # noqa: E402
import engine_dc  # noqa: E402
import fit_dc  # noqa: E402
import model_dc  # noqa: E402
import moteur_flag  # noqa: E402

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


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src(name):
    return open(os.path.join(WORLD, "F02_BREACHER", "CODEBASE", name), encoding="utf-8").read()


def _rows():
    teams = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    att = {"Alpha": 0.4, "Beta": 0.2, "Gamma": 0.0, "Delta": -0.1, "Epsilon": -0.2, "Zeta": -0.3}
    deff = {"Alpha": 0.3, "Beta": 0.1, "Gamma": 0.0, "Delta": -0.1, "Epsilon": -0.2, "Zeta": -0.3}
    rows = []
    day = 1
    for h in teams:
        for a in teams:
            if h == a:
                continue
            lh, la = model_dc.lambdas(0.25, 0.25, att[h], deff[h], att[a], deff[a])
            rows.append({
                "home": h, "away": a, "fthg": int(round(lh)), "ftag": int(round(la)),
                "date": "2025-08-%02d" % min(day, 28),
            })
            day = day + 1 if day < 28 else 1
    return rows


def _match(dom, ext, league="E0"):
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    return {
        "id": "M1", "dom": dom, "ext": ext, "league_code": league,
        "stats": {"dom": dict(stub), "ext": dict(stub)},
    }


def _avg():
    return {
        "buts_dom_moy": 1.5, "buts_ext_moy": 1.2,
        "bonus_domicile": 1.10, "bonus_exterieur": 0.95,
        "rho": -0.13, "part_mt1_ligue": 0.44, "league_code": "E0",
        "params": "default",
    }


def main():
    print("=" * 70)
    print("TEST V2b — engine_dc")
    print("=" * 70)

    old_env = os.environ.get("PARI_DC_PARAMS_PATH")
    os.environ["PARI_DC_PARAMS_PATH"] = os.path.join(tempfile.mkdtemp(prefix="pari-v2b-miss-"), "nope.json")
    fit_dc._PARAMS_CACHE = None

    m = _match("Alpha", "Zeta")
    avg = _avg()
    ov = engine_dc.overlay(m, avg, 1.11, 0.99, -0.13)
    check("v2b.absent_poisson", ov["engine"] == "poisson", str(ov["engine"]))
    check("v2b.absent_lh", ov["lambda_dom"] == 1.11 and ov["lambda_ext"] == 0.99)
    check("v2b.absent_hole", "params_absents" in (ov.get("holes") or []), str(ov.get("holes")))

    a0 = breacher.analyse_match(m, avg)
    check("v2b.wire_poisson", a0.get("engine") == "poisson", str(a0.get("engine")))
    check("v2b.wire_hole", "params_absents" in (a0.get("holes") or []), str(a0.get("holes")))
    check("v2b.lambda_pos", a0["lambdas"]["dom_total"] > 0)

    rec = fit_dc.fit_league(_rows(), code="E0", cfg=CFG_SMALL)
    tmp = tempfile.mkdtemp(prefix="pari-v2b-")
    path = os.path.join(tmp, "dc_params.json")
    blob = {"leagues": {"E0": rec}, "engine": "dc_mle"}
    fit_dc.save_params(blob, path)
    os.environ["PARI_DC_PARAMS_PATH"] = path
    fit_dc._PARAMS_CACHE = None

    want = model_dc.lambdas_for("Alpha", "Zeta", rec)
    ov2 = engine_dc.overlay(m, avg, 9.99, 9.99, -0.13, blob=blob)
    check("v2b.mle_engine", ov2["engine"] == "dc_mle", str(ov2["engine"]))
    check("v2b.mle_lh", abs(ov2["lambda_dom"] - want["lh"]) < 1e-9, str(ov2["lambda_dom"]))
    check("v2b.mle_la", abs(ov2["lambda_ext"] - want["la"]) < 1e-9, str(ov2["lambda_ext"]))
    check("v2b.mle_not_999", ov2["lambda_dom"] != 9.99)

    ghost = engine_dc.overlay(_match("Ghost", "Zeta"), avg, 1.11, 0.99, -0.13, blob=blob)
    check("v2b.ghost_poisson", ghost["engine"] == "poisson")
    check("v2b.ghost_lh", ghost["lambda_dom"] == 1.11)
    check("v2b.ghost_hole", "equipe_absente" in (ghost.get("holes") or []), str(ghost.get("holes")))

    a1 = breacher.analyse_match(m, avg)
    check("v2b.wire_mle", a1.get("engine") == "dc_mle", str(a1.get("engine")))
    check("v2b.wire_mle_lh", abs(a1["lambdas"]["dom_total"] - round(want["lh"], 3)) < 1e-9,
          str(a1["lambdas"]["dom_total"]))

    a_ghost = breacher.analyse_match(_match("Ghost", "Zeta"), avg)
    check("v2b.wire_ghost", a_ghost.get("engine") == "poisson")
    check("v2b.wire_ghost_hole", "equipe_absente" in (a_ghost.get("holes") or []))

    miss_lg = engine_dc.overlay(_match("Alpha", "Zeta", "I1"), {"league_code": "I1"}, 1.11, 0.99, -0.13, blob=blob)
    check("v2b.ligue_poisson", miss_lg["engine"] == "poisson")
    check("v2b.ligue_hole", "ligue_absente" in (miss_lg.get("holes") or []), str(miss_lg.get("holes")))

    check("v2b.gel", moteur_flag.tickets_enabled() is False)
    cfg = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
    check("v2b.cfg_false", cfg.get("tickets_enabled") is False)

    src = _src("engine_dc.py")
    check("v2b.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("v2b.pas_tickets", "set_tickets" not in src)
    check("v2b.pas_calib", "backtest_market" not in src)
    ast.parse(src)
    check("v2b.ast_ok", True)

    src_b = _src("breacher.py")
    check("v2b.breacher_import", "import engine_dc" in src_b)

    if old_env is None:
        os.environ.pop("PARI_DC_PARAMS_PATH", None)
    else:
        os.environ["PARI_DC_PARAMS_PATH"] = old_env
    fit_dc._PARAMS_CACHE = None

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V2b engine_dc : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
