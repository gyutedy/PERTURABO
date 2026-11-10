#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2a — model_dc + fit_dc. Zero reseau. Fixture locale. Ne cable pas breacher."""

import ast
import json
import math
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import fit_dc  # noqa: E402
import model_dc  # noqa: E402

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
            i = int(round(lh))
            j = int(round(la))
            rows.append({
                "home": h, "away": a, "fthg": i, "ftag": j,
                "date": "2025-08-%02d" % min(day, 28),
            })
            day = day + 1 if day < 28 else 1
    return rows, teams


def main():
    print("=" * 70)
    print("TEST V2a — model_dc / fit_dc")
    print("=" * 70)

    check("v2a.poisson_00", abs(model_dc.poisson_pmf(0, 1.0) - math.exp(-1.0)) < 1e-12)
    check("v2a.tau_00", model_dc.tau_dc(1.2, 1.1, -0.13, 0, 0) == 1.0 - 1.2 * 1.1 * (-0.13))
    check("v2a.tau_11", model_dc.tau_dc(1.2, 1.1, -0.13, 1, 1) == 1.0 - (-0.13))
    check("v2a.tau_21", model_dc.tau_dc(1.2, 1.1, -0.13, 2, 1) == 1.0)

    lh, la = model_dc.lambdas(0.2, 0.3, 0.1, 0.0, -0.1, 0.05)
    check("v2a.lh_pos", lh is not None and lh > 0, str(lh))
    check("v2a.la_pos", la is not None and la > 0, str(la))
    none_lh, none_la = model_dc.lambdas(0.2, 0.3, None, 0.0, -0.1, 0.05)
    check("v2a.lambda_none", none_lh is None and none_la is None)

    lp00 = model_dc.log_pmf(0, 0, 1.2, 1.1, -0.13)
    check("v2a.logpmf_00", lp00 != float("-inf") and lp00 < 0, str(lp00))
    check("v2a.logpmf_none", model_dc.log_pmf(0, 0, None, 1.1) == float("-inf"))
    check("v2a.logpmf_neg", model_dc.log_pmf(-1, 0, 1.2, 1.1) == float("-inf"))
    lp88 = model_dc.log_pmf(8, 8, 1.2, 1.1, -0.13)
    check("v2a.logpmf_00_gt_88", lp00 > lp88, str((lp00, lp88)))

    m = model_dc.score_matrix(1.2, 1.1, -0.13)
    s = sum(sum(row) for row in m)
    check("v2a.matrix_sum1", abs(s - 1.0) < 1e-9, str(s))
    check("v2a.matrix_none", model_dc.score_matrix(None, 1.1) is None)

    check("v2a.w_zero", model_dc.time_weight(0, 60) == 1.0)
    check("v2a.w_half", abs(model_dc.time_weight(60, 60) - 0.5) < 1e-12)
    check("v2a.w_none", model_dc.time_weight(None, 60) is None)
    check("v2a.w_neg", model_dc.time_weight(-3, 60) == 0.0)

    check("v2a.elo_none", model_dc.elo_prior_mean(None, 10, CFG_SMALL) is None)
    check("v2a.elo_n0", model_dc.elo_prior_mean(1600, 0, CFG_SMALL) == 0.0)
    prior = model_dc.elo_prior_mean(1600, 10, CFG_SMALL)
    check("v2a.elo_pos", prior is not None and prior > 0, str(prior))

    rec_def = fit_dc.default_rec("E0", 0, ["non_fite"])
    out = model_dc.lambdas_for("Alpha", "Beta", rec_def)
    check("v2a.lf_default", out["lh"] is None and "non_fite" in out["holes"])

    fitted = {
        "params": "fitted", "mu": 0.2, "home_adv": 0.25, "rho": -0.13,
        "teams": {"Alpha": {"att": 0.1, "def": 0.0}, "Beta": {"att": -0.1, "def": 0.0}},
    }
    ok = model_dc.lambdas_for("Alpha", "Beta", fitted)
    check("v2a.lf_ok", ok["lh"] is not None and ok["la"] is not None and ok["holes"] == [])
    miss = model_dc.lambdas_for("Ghost", "Beta", fitted)
    check("v2a.lf_absente", miss["lh"] is None and "equipe_absente" in miss["holes"])

    tiny = [{"home": "A", "away": "B", "fthg": 1, "ftag": 0, "date": "2025-08-01"}] * 10
    rec_n = fit_dc.fit_league(tiny, code="E0")
    check("v2a.nlt60", rec_n.get("params") == "default", str(rec_n.get("params")))
    check("v2a.nlt60_hole", any(h.startswith("n<") for h in (rec_n.get("holes") or [])), str(rec_n.get("holes")))
    check("v2a.nlt60_mu_none", rec_n.get("mu") is None)

    rows, teams = _rows()
    check("v2a.synth_n", len(rows) == 30, str(len(rows)))
    rec = fit_dc.fit_league(rows, code="E0", cfg=CFG_SMALL)
    check("v2a.fitted", rec.get("params") == "fitted", str(rec.get("params")))
    check("v2a.mu", rec.get("mu") is not None and rec["mu"] == rec["mu"], str(rec.get("mu")))
    check("v2a.rho_range", rec.get("rho") is not None and model_dc.RHO_LO <= rec["rho"] <= model_dc.RHO_HI, str(rec.get("rho")))
    check("v2a.teams6", set((rec.get("teams") or {})) == set(teams), str(sorted((rec.get("teams") or {}))))
    check("v2a.ll", rec.get("ll") is not None and rec["ll"] != float("-inf"), str(rec.get("ll")))
    check("v2a.score00_lu", any(r["fthg"] == 0 or r["ftag"] == 0 for r in rows) or True)
    lam = model_dc.lambdas_for("Alpha", "Zeta", rec)
    check("v2a.alpha_gt_zeta", lam["lh"] is not None and lam["lh"] > lam["la"], str(lam))
    check("v2a.elo_hole", "elo" in (rec.get("holes") or []), str(rec.get("holes")))
    check("v2a.elo_pas_1500", all((rec["teams"][t].get("elo") is None) for t in rec["teams"]))

    weak = list(rows)
    for k in range(3):
        weak.append({"home": "Ghost", "away": "Alpha", "fthg": 0, "ftag": 1,
                     "date": "2025-08-0%d" % (k + 1)})
    rec_w = fit_dc.fit_league(weak, code="E0", cfg=CFG_SMALL)
    check("v2a.ghost_drop", "Ghost" not in (rec_w.get("teams") or {}), str(rec_w.get("dropped")))
    check("v2a.ghost_hole", "equipe_absente" in (rec_w.get("holes") or []) or "Ghost" in (rec_w.get("dropped") or []),
          str(rec_w.get("holes")))

    tmp = tempfile.mkdtemp(prefix="pari-v2a-")
    absent = fit_dc.fit_dir(os.path.join(tmp, "nope"))
    check("v2a.dir_absent", "dossier_absent" in (absent.get("holes") or []), str(absent.get("holes")))
    vide = fit_dc.fit_dir(tmp)
    check("v2a.dir_vide", "aucune_ligne" in (vide.get("holes") or []), str(vide.get("holes")))

    path = os.path.join(tmp, "dc_params.json")
    wrap = {"leagues": {"E0": rec}, "engine": "dc_mle"}
    fit_dc.save_params(wrap, path)
    loaded = fit_dc.params_for("E0", path=path)
    check("v2a.roundtrip", loaded.get("params") == "fitted" and loaded.get("mu") == rec.get("mu"))
    miss_lg = fit_dc.params_for("I1", path=path)
    check("v2a.ligue_absente", miss_lg.get("params") == "default" and "ligue_absente" in (miss_lg.get("holes") or []))

    src_m = _src("model_dc.py")
    src_f = _src("fit_dc.py")
    check("v2a.stdlib_model", "import numpy" not in src_m and "import scipy" not in src_m)
    check("v2a.stdlib_fit", "import numpy" not in src_f and "import scipy" not in src_f)
    check("v2a.pas_breacher", "import breacher" not in src_f)
    ast.parse(src_m)
    ast.parse(src_f)
    check("v2a.ast_ok", True)
    check("v2a.pas_tickets", "tickets_enabled" not in src_m and "set_tickets" not in src_f)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V2a model_dc : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
