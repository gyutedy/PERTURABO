#!/usr/bin/env python3
"""
VANUS CALIBRATE — CSV Big 5 + fit DC + backtest GO/NO-GO (stdlib). Pack VX.
==========================================================================
Fetch football-data → fit_dc → backtest_market. Timeout / HTML / skip = hole.
n_oos < 300 = verdict None, jamais un GO. Ne touche pas tickets_enabled.
F06 n'apprend pas. Sortie gitignore.

Usage :
  python vanus_calibrate.py --season 2526
  python vanus_calibrate.py --seasons 2425,2526 --cutoff 2026-01-01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F02 = os.path.join(WORLD, "F02_BREACHER", "CODEBASE")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if F02 not in sys.path:
    sys.path.insert(0, F02)

import backtest_market  # noqa: E402
import fit_dc  # noqa: E402
import market_csv  # noqa: E402
import vanus_fetch as vf  # noqa: E402

DEFAULT_CACHE = os.path.join(WORLD, "ARCHIVUM", "cache", "f00")
DEFAULT_FIT = os.path.join(WORLD, "ARCHIVUM", "learnings", "dc_params.json")
DEFAULT_CAL = os.path.join(WORLD, "ARCHIVUM", "learnings", "calibration_moteur.json")


def parse_seasons(raw, season=None):
    if raw:
        out = []
        for part in str(raw).split(","):
            s = part.strip()
            if s:
                out.append(s)
        if out:
            return out
    if season:
        return [str(season)]
    return ["2526"]


def default_cutoff(seasons):
    codes = [str(s) for s in (seasons or []) if str(s).strip()]
    if not codes:
        return None
    last = max(codes)
    if len(last) == 4 and last.isdigit():
        return "20%s-01-01" % last[2:4]
    return None


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty(cutoff=None, holes=None, reasons=None):
    holes = list(holes or [])
    rec = backtest_market.evaluate([], cutoff)
    rec["generated_at"] = _now()
    rec["fetch"] = {"files": [], "n_lignes": 0, "divisions": {}, "hors_couverture": list(vf.BIG5), "holes": list(holes)}
    rec["fit"] = {"n_lignes": 0, "leagues": {}, "holes": list(holes)}
    rec["seasons"] = []
    rec["tickets_enabled"] = False
    extra = list(holes)
    rec["holes"] = list(dict.fromkeys((rec.get("holes") or []) + extra))
    if reasons:
        rec["reasons"] = list(dict.fromkeys((rec.get("reasons") or []) + list(reasons)))
    rec["verdict"] = None
    return rec


def run(seasons=None, season=None, cache_dir=None, cutoff=None, getter=None,
        timeout=None, cfg=None, gates=None, fit_out=None, cal_out=None,
        skip_fetch=False):
    seasons = parse_seasons(",".join(seasons) if isinstance(seasons, (list, tuple)) else seasons,
                            season=season)
    cache_dir = cache_dir or DEFAULT_CACHE
    cutoff = cutoff or default_cutoff(seasons)
    blob = {
        "generated_at": _now(),
        "engine": "dc_mle",
        "engine_version": "pari.model_dc.v1",
        "seasons": seasons,
        "cutoff": cutoff,
        "in_sample": False,
        "n": 0,
        "n_train": 0,
        "n_test": 0,
        "n_skipped": 0,
        "verdict": None,
        "rps_modele": None,
        "rps_marche": None,
        "rps_gap": None,
        "ece": None,
        "logloss_modele": None,
        "logloss_marche": None,
        "logloss_gap": None,
        "reasons": [],
        "holes": [],
        "offline": getter is not None,
        "tickets_enabled": False,
        "fetch": {},
        "fit": {},
    }
    if vf.skipped():
        rec = _empty(cutoff, holes=["skip"], reasons=["skip"])
        rec["seasons"] = seasons
        rec["cutoff"] = cutoff
        rec["offline"] = getter is not None
        if cal_out:
            backtest_market.save(rec, cal_out)
            rec["out"] = os.path.abspath(cal_out)
        return rec

    fetch_holes = []
    files = []
    divisions = {}
    n_lignes = 0
    hors = []
    detail = []
    if not skip_fetch:
        for s in seasons:
            got = vf.fetch(season=s, cache_dir=cache_dir, getter=getter, timeout=timeout)
            detail.extend(got.get("detail") or [])
            files.extend(got.get("files") or [])
            n_lignes += int(got.get("n_lignes") or 0)
            for k, v in (got.get("divisions") or {}).items():
                divisions[k] = divisions.get(k, 0) + int(v)
            fetch_holes.extend(got.get("holes") or [])
            hors = list(got.get("hors_couverture") or hors)
        hors = [c for c in vf.BIG5 if divisions.get(c, 0) <= 0]
    else:
        loaded = market_csv.load_dir(cache_dir)
        files = loaded.get("files") or []
        n_lignes = len(loaded.get("rows") or [])
        fetch_holes.extend(loaded.get("holes") or [])
        by = market_csv.by_div(loaded.get("rows") or [])
        divisions = {k: len(v) for k, v in by.items()}
        hors = [c for c in vf.BIG5 if divisions.get(c, 0) <= 0]

    blob["fetch"] = {
        "dir": os.path.abspath(cache_dir),
        "files": files,
        "n_lignes": n_lignes,
        "divisions": divisions,
        "hors_couverture": hors,
        "holes": list(dict.fromkeys(fetch_holes)),
        "detail": [{k: d.get(k) for k in ("code", "season", "ok", "n_lignes", "holes")}
                   for d in detail],
    }
    blob["holes"].extend(blob["fetch"]["holes"])
    if hors:
        blob["holes"].append("hors_couverture")

    fit_blob = fit_dc.fit_dir(cache_dir, as_of=cutoff, cfg=cfg)
    if fit_out:
        fit_dc.save_params(fit_blob, fit_out)
    blob["fit"] = {
        "n_lignes": fit_blob.get("n_lignes") or 0,
        "leagues": {k: {"n": v.get("n"), "params": v.get("params"), "holes": v.get("holes")}
                    for k, v in (fit_blob.get("leagues") or {}).items()},
        "holes": fit_blob.get("holes") or [],
        "out": os.path.abspath(fit_out) if fit_out else None,
    }
    blob["holes"].extend(blob["fit"]["holes"])

    cal = backtest_market.run_dir(cache_dir, cutoff, out=None, cfg=cfg, gates=gates)
    for k in ("n", "n_train", "n_test", "n_skipped", "verdict", "rps_modele",
              "rps_marche", "rps_gap", "ece", "logloss_modele", "logloss_marche",
              "logloss_gap", "reasons", "in_sample", "cutoff", "gates"):
        if k in cal:
            blob[k] = cal[k]
    blob["holes"] = list(dict.fromkeys(list(blob.get("holes") or []) + list(cal.get("holes") or [])))
    blob["tickets_enabled"] = False
    if cal_out:
        backtest_market.save(blob, cal_out)
        blob["out"] = os.path.abspath(cal_out)
    return blob


def main():
    ap = argparse.ArgumentParser(description="VX CSV + fit + backtest GO/NO-GO")
    ap.add_argument("--season", default=None)
    ap.add_argument("--seasons", default=None)
    ap.add_argument("--dir", default=DEFAULT_CACHE)
    ap.add_argument("--cutoff", default=None)
    ap.add_argument("--fit-out", default=DEFAULT_FIT)
    ap.add_argument("--out", default=DEFAULT_CAL)
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    rec = run(
        seasons=args.seasons, season=args.season, cache_dir=args.dir,
        cutoff=args.cutoff, fit_out=args.fit_out, cal_out=args.out,
        skip_fetch=args.skip_fetch,
    )
    print(json.dumps({
        "out": rec.get("out"),
        "seasons": rec.get("seasons"),
        "cutoff": rec.get("cutoff"),
        "n": rec.get("n"),
        "n_train": rec.get("n_train"),
        "n_test": rec.get("n_test"),
        "verdict": rec.get("verdict"),
        "rps_gap": rec.get("rps_gap"),
        "ece": rec.get("ece"),
        "logloss_gap": rec.get("logloss_gap"),
        "holes": rec.get("holes"),
        "reasons": rec.get("reasons"),
        "fetch": {k: rec.get("fetch", {}).get(k) for k in
                  ("n_lignes", "divisions", "hors_couverture", "holes")},
        "fit": rec.get("fit", {}).get("leagues"),
        "tickets_enabled": False,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
