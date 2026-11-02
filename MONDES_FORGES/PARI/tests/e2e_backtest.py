#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E BACKTEST — shares MT1, tampon ligue, commandes radar/pack/match. Zero reseau."""

import json
import math
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import backtest  # noqa: E402
import breacher  # noqa: E402
import radar  # noqa: E402
import workflow  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("E2E BACKTEST — shares / tampon / cmds (zero reseau)")
    print("=" * 70)

    src = open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "backtest.py"), encoding="utf-8").read().lower()
    check("B.pas_winner", "winner" not in src)
    check("B.pas_scrape", "scrape" not in src and "http://" not in src and "urllib" not in src)

    csv_dir = os.path.join(WORLD, "tests", "fixtures")
    tmp = tempfile.mkdtemp(prefix="pari-bt-")
    out_shares = os.path.join(tmp, "shares.json")
    elo_path = os.path.join(tmp, "elo.json")
    json.dump({
        "Ath Madrid": 1850, "Barcelona": 1900, "Levante": 1500,
        "Sevilla": 1700, "Valencia": 1650,
    }, open(elo_path, "w"))
    shares = backtest.scan_dir(csv_dir, elo_map=backtest.load_elo(elo_path))
    check("B.shares_sp1", "SP1" in shares, str(list(shares)))
    rec = shares.get("SP1") or {}
    part = rec.get("part_mt1")
    check("B.part_mt1_range", part is not None and 0.30 <= part <= 0.60, str(part))
    slope = rec.get("elo_slope")
    check("B.elo_slope_finite", slope is None or math.isfinite(slope), str(slope))
    blob = {"generated_at": "t", "offline": True, "leagues": shares, "SP1": rec, "E0": {"part_mt1": 0.43, "n_mt": 12}}
    json.dump(blob, open(out_shares, "w"))
    check("B.schema_shares", "part_mt1" in rec and "n_mt" in rec and "league_code" in rec)

    os.environ["PARI_SHARES_PATH"] = out_shares
    breacher._SHARES_CACHE = None
    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    nostub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": None, "encaisses_mt1": None}
    ms = [
        {"id": "M1", "dom": "A", "ext": "B", "ligue": "Angleterre - Premier League",
         "stats": {"dom": dict(nostub), "ext": dict(nostub)}},
        {"id": "M2", "dom": "C", "ext": "D", "ligue": "Angleterre - Premier League",
         "stats": {"dom": dict(nostub), "ext": dict(nostub)}},
    ]
    out = breacher.analyse_fixtures(ms, ligue="Angleterre - Premier League", league_code="E0")
    check("B.shares_path", abs((out["ligue_moyennes"] or {}).get("part_mt1_ligue") - 0.43) < 1e-6,
          str((out.get("ligue_moyennes") or {}).get("part_mt1_ligue")))
    check("B.league_code_stamped", ms[0].get("league_code") == "E0", str(ms[0].get("league_code")))
    flags = (out["analyses"][0].get("data_quality") or {}).get("flags") or []
    check("B.mt_split_estimate", "mt_split_estimate" in flags, str(flags))
    check("B.mt1_lambda", (out["analyses"][0]["lambdas"]["dom_mt1"] or 0) > 0)

    ms2 = [
        {"id": "M1", "dom": "A", "ext": "B", "ligue": "Angleterre - Premier League",
         "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M2", "dom": "C", "ext": "D", "stats": {"dom": dict(stub), "ext": dict(stub)}},
        {"id": "M3", "dom": "E", "ext": "F", "stats": {"dom": {"mj": 12}, "ext": {}}},
    ]
    radar.stamp_ligue(ms2, ligue="Angleterre - Premier League", league_code="E0")
    check("B.radar_stamp_all", all(m.get("league_code") == "E0" for m in ms2), str([m.get("league_code") for m in ms2]))
    complete, holes = radar.split_complete(ms2)
    check("B.radar_holes", holes == ["M3"] and len(complete) == 2, str(holes))
    scan = radar.run_radar(ms2, top=5, ligue="Angleterre - Premier League", league_code="E0")
    check("B.radar_skip_hole", scan.get("holes") == ["M3"] and len(scan.get("analyses") or []) == 2)
    learn = scan.get("learnings") or {}
    check("B.learnings_identity", learn.get("active") is False and learn.get("factor") == 1.0, str(learn))
    a0 = (scan.get("analyses") or [{}])[0]
    check("B.score_raw", a0.get("radar_score") == a0.get("radar_score_raw"),
          str((a0.get("radar_score"), a0.get("radar_score_raw"))))

    merged = backtest.scan_dir(csv_dir)
    rec_m = merged.get("SP1") or {}
    check("B.merge_n_files", rec_m.get("n_files") == 2, str(rec_m.get("n_files")))
    check("B.merge_n_mt", rec_m.get("n_mt") == 12, str(rec_m.get("n_mt")))
    check("B.merge_seasons", set(rec_m.get("seasons") or []) == {"2526", "2627"}, str(rec_m.get("seasons")))

    fake = tempfile.mkdtemp(prefix="pari-tk-")
    tk_path = os.path.join(fake, "tickets.json")
    tickets = [{"id": f"T{i}", "resultat": "gagné" if i % 2 == 0 else "perdu",
                "mise_units": 1.0, "pnl_units": 0.5 if i % 2 == 0 else -1.0}
               for i in range(50)]
    json.dump({"tickets": tickets}, open(tk_path, "w"))
    os.environ["PARI_TICKETS_PATH"] = tk_path
    L = radar.load_learnings()
    check("B.learnings_active", L.get("active") is True and L.get("n") == 50, str(L))
    check("B.learnings_clip", 0.85 <= L.get("factor", 0) <= 1.15, str(L.get("factor")))
    dummy = {"analyses": [{"radar_score_raw": 0.50, "radar_score": 0.50}]}
    radar.apply_learnings(dummy, L)
    check("B.learnings_scale", abs(dummy["analyses"][0]["radar_score"] - 0.50 * L["factor"]) < 1e-6,
          str(dummy["analyses"][0]["radar_score"]))
    os.environ.pop("PARI_TICKETS_PATH", None)

    wf_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()
    check("B.cmd_radar", "def cmd_radar" in wf_src and '"radar":' in wf_src)
    check("B.cmd_pack", "def cmd_pack" in wf_src)
    check("B.cmd_match", "def cmd_match" in wf_src)
    check("B.offline_env", "PARI_SHARES_PATH" in os.environ)

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"BACKTEST {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
