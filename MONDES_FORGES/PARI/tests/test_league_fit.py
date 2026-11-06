#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 — fit ligue rho / bonus / part_mt1. Fixture SP1. Zero reseau."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import breacher  # noqa: E402
import league_fit  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _reset():
    league_fit._PARAMS_CACHE = None
    league_fit._CONFIG_CACHE = None
    breacher._SHARES_CACHE = None


def test_fit_sp1():
    csv_path = os.path.join(WORLD, "tests", "fixtures", "uk_SP1_2526.csv")
    rec = league_fit.fit_file(csv_path)
    check("lf.sp1_ok", rec is not None and rec.get("league_code") == "SP1", str(rec and rec.get("league_code")))
    check("lf.sp1_fitted", rec.get("params") == "fitted", str(rec.get("params")))
    check("lf.sp1_n", rec.get("n") == 6, str(rec.get("n")))
    rho = rec.get("rho")
    check("lf.rho_range", rho is not None and -0.3 <= rho <= 0.1, str(rho))
    bonus = rec.get("bonus_domicile")
    check("lf.bonus_gt1", bonus is not None and bonus > 1.0, str(bonus))
    check("lf.bonus_clip", 1.0 <= bonus <= 1.25, str(bonus))
    expected = 1.0 + (13.0 - 8.0) / (13.0 + 8.0)
    check("lf.bonus_formula", abs(bonus - expected) < 1e-12, f"{bonus} vs {expected}")
    part = rec.get("part_mt1")
    check("lf.part_range", part is not None and 0.30 <= part <= 0.60, str(part))
    check("lf.rho_grid_has_013", -0.13 in league_fit._grid(-0.25, 0.05, 0.01))


def test_n_lt4_default():
    rows = [
        {"Div": "E0", "FTHG": "1", "FTAG": "0", "HTHG": "0", "HTAG": "0"},
        {"Div": "E0", "FTHG": "2", "FTAG": "1", "HTHG": "1", "HTAG": "0"},
    ]
    rec = league_fit.fit_league(rows, code="E0")
    check("lf.nlt4_default", rec.get("params") == "default", str(rec.get("params")))
    check("lf.nlt4_rho", rec.get("rho") == -0.13, str(rec.get("rho")))
    check("lf.nlt4_bonus", rec.get("bonus_domicile") == 1.10, str(rec.get("bonus_domicile")))
    check("lf.nlt4_hole", "n<4" in (rec.get("holes") or []), str(rec.get("holes")))


def test_params_for_missing():
    rec = league_fit.params_for("ZZ", path=os.path.join(tempfile.mkdtemp(), "nope.json"))
    check("lf.missing_default", rec.get("params") == "default")
    check("lf.missing_rho", rec.get("rho") == -0.13)
    check("lf.missing_bonus", rec.get("bonus_domicile") == 1.10)


def test_save_load_roundtrip():
    csv_path = os.path.join(WORLD, "tests", "fixtures", "uk_SP1_2526.csv")
    rec = league_fit.fit_file(csv_path)
    tmp = tempfile.mkdtemp(prefix="pari-lf-")
    out = os.path.join(tmp, "league_params.json")
    blob = league_fit.wrap_blob({"SP1": rec})
    league_fit.save_params(blob, out)
    loaded = league_fit.params_for("SP1", path=out)
    check("lf.round_fitted", loaded.get("params") == "fitted")
    check("lf.round_rho", loaded.get("rho") == rec.get("rho"), str(loaded.get("rho")))
    check("lf.round_bonus", abs(loaded.get("bonus_domicile") - rec.get("bonus_domicile")) < 1e-12)


def test_wiring_bonus_default_inchange():
    _reset()
    os.environ.pop("PARI_LEAGUE_PARAMS_PATH", None)
    os.environ.pop("PARI_UK_CACHE", None)
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    ms = [
        {"id": "M1", "dom": "A", "ext": "B", "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "C", "ext": "D", "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    avg = breacher.league_averages(ms, league_code="E0", csv_dir=os.path.join(tmp := tempfile.mkdtemp(), "empty"))
    check("lf.wire_bonus_110", abs(avg.get("bonus_domicile") - 1.10) < 1e-12, str(avg.get("bonus_domicile")))
    check("lf.wire_bonus_e095", abs(avg.get("bonus_exterieur") - 0.95) < 1e-12, str(avg.get("bonus_exterieur")))
    check("lf.wire_rho_dc", abs(avg.get("rho") - breacher.RHO_DC) < 1e-12, str(avg.get("rho")))
    check("lf.wire_params_default", avg.get("params") == "default")
    a = breacher.analyse_match(ms[0], avg)
    avg2 = dict(avg)
    avg2["bonus_domicile"] = 1.10
    avg2["bonus_exterieur"] = 0.95
    avg2["rho"] = breacher.RHO_DC
    b = breacher.analyse_match(ms[0], avg2)
    check("lf.wire_lambda_inchange", a["lambdas"]["dom_total"] == b["lambdas"]["dom_total"],
          str((a["lambdas"]["dom_total"], b["lambdas"]["dom_total"])))
    del tmp


def test_wiring_fitted_overrides():
    csv_path = os.path.join(WORLD, "tests", "fixtures", "uk_SP1_2526.csv")
    rec = league_fit.fit_file(csv_path)
    tmp = tempfile.mkdtemp(prefix="pari-lfw-")
    out = os.path.join(tmp, "league_params.json")
    league_fit.save_params(league_fit.wrap_blob({"SP1": rec}), out)
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    ms = [
        {"id": "M1", "dom": "A", "ext": "B", "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "C", "ext": "D", "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    avg = breacher.league_averages(ms, league_code="SP1", csv_dir=tmp, params_path=out)
    check("lf.fit_params", avg.get("params") == "fitted", str(avg.get("params")))
    check("lf.fit_bonus", abs(avg.get("bonus_domicile") - rec["bonus_domicile"]) < 1e-12,
          str(avg.get("bonus_domicile")))
    a = breacher.analyse_match(ms[0], avg)
    check("lf.fit_lambda_pos", a["lambdas"]["dom_total"] > 0)


def test_config_defaults():
    cfg = league_fit.load_config()
    check("lf.cfg_half", cfg.get("half_life_days") == 45, str(cfg.get("half_life_days")))
    check("lf.cfg_rho", cfg["defaults"]["rho"] == -0.13)
    check("lf.cfg_min", cfg.get("min_matches") == 4)


def test_fit_dir_cli_blob():
    blob = league_fit.fit_dir(os.path.join(WORLD, "tests", "fixtures"))
    check("lf.dir_sp1", "SP1" in (blob.get("leagues") or {}), str(list((blob.get("leagues") or {}))))
    check("lf.dir_nfiles", (blob["leagues"]["SP1"].get("n_files") or 0) >= 1)
    check("lf.dir_offline", blob.get("offline") is True)


def main():
    print("=" * 70)
    print("TEST S6 — league_fit")
    print("=" * 70)
    _reset()
    test_fit_sp1()
    test_n_lt4_default()
    test_params_for_missing()
    test_save_load_roundtrip()
    test_wiring_bonus_default_inchange()
    test_wiring_fitted_overrides()
    test_config_defaults()
    test_fit_dir_cli_blob()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S6 league_fit : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
