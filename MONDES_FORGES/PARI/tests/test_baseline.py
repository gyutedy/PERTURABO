#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 — baseline saison EMA demi-vie 45j. Fallback carte. Zero reseau."""

import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import baseline  # noqa: E402
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
    os.environ.pop("PARI_LEAGUE_PARAMS_PATH", None)
    os.environ.pop("PARI_UK_CACHE", None)


def test_ema_weight():
    check("bl.w0", abs(baseline.ema_weight(0, 45) - 1.0) < 1e-12)
    check("bl.w45", abs(baseline.ema_weight(45, 45) - 0.5) < 1e-12)
    check("bl.w90", abs(baseline.ema_weight(90, 45) - 0.25) < 1e-12)


def test_ema_half_life_rows():
    rows = [
        {"Div": "E0", "Date": "01/01/2025", "HomeTeam": "A", "AwayTeam": "B",
         "FTHG": "4", "FTAG": "0"},
        {"Div": "E0", "Date": "01/04/2025", "HomeTeam": "A", "AwayTeam": "B",
         "FTHG": "0", "FTAG": "0"},
    ]
    rec = baseline.compute_baseline(rows, as_of="2025-04-01", half_life=45)
    check("bl.ema_n", rec.get("n") == 2, str(rec.get("n")))
    expected = (4.0 * 0.25 + 0.0 * 1.0) / (0.25 + 1.0)
    check("bl.ema_dom", abs(rec["buts_dom_moy"] - expected) < 1e-12,
          f"{rec['buts_dom_moy']} vs {expected}")
    unweighted = 2.0
    check("bl.ema_ne_moyenne", abs(rec["buts_dom_moy"] - unweighted) > 0.5)
    check("bl.flag_saison", rec.get("baseline") == "saison")
    teams = rec.get("teams") or {}
    check("bl.split_teams", "A" in teams and "B" in teams, str(list(teams)))
    check("bl.split_att", teams["A"].get("att_dom") is not None)
    check("bl.split_def", teams["A"].get("def_dom") is not None)
    check("bl.enc_dom", abs(rec["encaisses_dom_moy"] - rec["buts_ext_moy"]) < 1e-12)
    check("bl.enc_ext", abs(rec["encaisses_ext_moy"] - rec["buts_dom_moy"]) < 1e-12)


def test_sp1_fixture_season():
    rec = baseline.league_baseline("SP1", csv_dir=os.path.join(WORLD, "tests", "fixtures"))
    check("bl.sp1_ok", rec is not None and rec.get("baseline") == "saison")
    check("bl.sp1_n", rec.get("n") >= 6, str(rec.get("n")))
    check("bl.sp1_dom", rec.get("buts_dom_moy") > 0)
    check("bl.sp1_half", rec.get("half_life_days") == 45, str(rec.get("half_life_days")))
    check("bl.sp1_teams", len(rec.get("teams") or {}) >= 2)


def test_missing_season_none():
    rec = baseline.league_baseline("ZZ", csv_dir=tempfile.mkdtemp(prefix="pari-bl-empty-"))
    check("bl.miss_none", rec is None)


def test_fallback_carte():
    _reset()
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    ms = [
        {"id": "M1", "dom": "A", "ext": "B", "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "C", "ext": "D", "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    empty = tempfile.mkdtemp(prefix="pari-bl-fb-")
    avg = breacher.league_averages(ms, league_code="E0", csv_dir=empty)
    check("bl.fb_carte", avg.get("baseline") == "carte", str(avg.get("baseline")))
    check("bl.fb_hole", "saison" in (avg.get("holes") or []), str(avg.get("holes")))
    check("bl.fb_flag", "baseline: carte" in (avg.get("flags") or []), str(avg.get("flags")))
    check("bl.fb_params", avg.get("params") == "default")
    check("bl.fb_params_flag", "params: default" in (avg.get("flags") or []))
    check("bl.fb_moy", abs(avg["buts_dom_moy"] - 18 / 12) < 1e-12, str(avg["buts_dom_moy"]))


def test_season_overrides_carte():
    _reset()
    stub = {"mj": 12, "marques": 99, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    ms = [
        {"id": "M1", "dom": "Ath Madrid", "ext": "Barcelona",
         "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "Levante", "ext": "Sevilla",
         "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    fx = os.path.join(WORLD, "tests", "fixtures")
    avg = breacher.league_averages(ms, league_code="SP1", csv_dir=fx)
    check("bl.ov_saison", avg.get("baseline") == "saison", str(avg.get("baseline")))
    check("bl.ov_pas_99", abs(avg["buts_dom_moy"] - 99 / 12) > 1.0, str(avg["buts_dom_moy"]))
    check("bl.ov_teams", isinstance(avg.get("teams"), dict) and "Ath Madrid" in avg["teams"])
    out = breacher.analyse_fixtures(ms, league_code="SP1")
    moy = out.get("ligue_moyennes") or {}
    check("bl.moy_pas_teams", "teams" not in moy)


def test_shares_priority_part():
    _reset()
    tmp = tempfile.mkdtemp(prefix="pari-bl-sh-")
    shares = os.path.join(tmp, "shares.json")
    with open(shares, "w", encoding="utf-8") as f:
        json_dump = __import__("json").dump
        json_dump({"E0": {"part_mt1": 0.43, "n_mt": 12}}, f)
    os.environ["PARI_SHARES_PATH"] = shares
    breacher._SHARES_CACHE = None
    stub = {"mj": 12, "marques": 18, "encaisses": 10}
    ms = [
        {"id": "M1", "dom": "A", "ext": "B", "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "C", "ext": "D", "stats": {"dom": dict(stub), "ext": dict(stub)}},
    ]
    avg = breacher.league_averages(ms, league_code="E0", csv_dir=tmp)
    check("bl.shares_part", abs(avg.get("part_mt1_ligue") - 0.43) < 1e-6, str(avg.get("part_mt1_ligue")))
    os.environ.pop("PARI_SHARES_PATH", None)
    breacher._SHARES_CACHE = None


def main():
    print("=" * 70)
    print("TEST S6 — baseline")
    print("=" * 70)
    _reset()
    test_ema_weight()
    test_ema_half_life_rows()
    test_sp1_fixture_season()
    test_missing_season_none()
    test_fallback_carte()
    test_season_overrides_carte()
    test_shares_priority_part()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S6 baseline : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
