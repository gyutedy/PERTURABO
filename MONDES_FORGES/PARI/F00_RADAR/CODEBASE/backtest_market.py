#!/usr/bin/env python3
"""
BACKTEST MARKET — calibration OOS RPS/ECE vs marche (stdlib, offline). Pack V2c.
==============================================================================
Walk-forward cut-off explicite, jamais in-sample. Fit train seulement.
Cote absente / <= 1.0 = hole. Score 0-0 lu. n_oos < seuil = pas de GO.
Ne touche pas tickets_enabled. Sortie calibration_moteur.json (gitignore).

Usage:
  python backtest_market.py --dir ARCHIVUM/cache/f00 --cutoff 2025-01-01
"""

from __future__ import annotations

import argparse
import json
import math
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

import fit_dc  # noqa: E402
import market_csv  # noqa: E402
import model_dc  # noqa: E402
import moteur_flag  # noqa: E402
import walkforward  # noqa: E402

DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "learnings", "calibration_moteur.json")
EPS = 1e-15


def parse_cutoff(raw):
    return walkforward.parse_cutoff(raw)


def split_cutoff(rows, cutoff):
    cut = parse_cutoff(cutoff)
    if cut is None:
        return [], [], "cutoff_absent"
    train, test = [], []
    for r in rows or []:
        dt = parse_cutoff(r.get("date") or r.get("Date"))
        if dt is None:
            continue
        if dt < cut:
            train.append(r)
        else:
            test.append(r)
    return train, test, None


def implied_1x2(h, d, a):
    try:
        h, d, a = float(h), float(d), float(a)
    except (TypeError, ValueError):
        return None
    if h <= 1.0 or d <= 1.0 or a <= 1.0:
        return None
    ih, idr, ia = 1.0 / h, 1.0 / d, 1.0 / a
    s = ih + idr + ia
    if s <= 0:
        return None
    return ih / s, idr / s, ia / s


def odds_1x2(row):
    ov = (row or {}).get("ouverts")
    if isinstance(ov, dict):
        got = implied_1x2(ov.get("home"), ov.get("draw"), ov.get("away"))
        if got:
            return got
    for trio in (("B365H", "B365D", "B365A"), ("AvgH", "AvgD", "AvgA"),
                 ("PSH", "PSD", "PSA")):
        got = implied_1x2(row.get(trio[0]), row.get(trio[1]), row.get(trio[2]))
        if got:
            return got
    return None


def outcome_of(fthg, ftag):
    if fthg is None or ftag is None:
        return None
    if fthg > ftag:
        return "H"
    if fthg < ftag:
        return "A"
    return "D"


def p_modele_1x2(lh, la, rho):
    m = model_dc.score_matrix(lh, la, rho)
    if not m:
        return None
    p1 = px = p2 = 0.0
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            if i > j:
                p1 += p
            elif i == j:
                px += p
            else:
                p2 += p
    s = p1 + px + p2
    if s <= 0:
        return None
    return p1 / s, px / s, p2 / s


def logloss_1x2(p1, px, p2, outcome):
    if outcome == "H":
        p = p1
    elif outcome == "D":
        p = px
    elif outcome == "A":
        p = p2
    else:
        return None
    if p is None or p <= 0.0:
        return None
    return -math.log(max(p, EPS))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def _round(v, n=6):
    if v is None:
        return None
    if isinstance(v, float):
        return round(v, n)
    return v


def apply_gates(n, rps_gap, ece, logloss_gap, gates=None):
    gates = gates if isinstance(gates, dict) else (moteur_flag.gates() or {})
    min_n = int(gates.get("min_matches_oos") if gates.get("min_matches_oos") is not None else 300)
    rps_max = float(gates.get("rps_gap_max") if gates.get("rps_gap_max") is not None else 0.0)
    ece_max = float(gates.get("ece_max") if gates.get("ece_max") is not None else 0.03)
    ll_max = float(gates.get("logloss_gap_max") if gates.get("logloss_gap_max") is not None else 0.0)
    holes = []
    reasons = []
    if n is None or n < min_n:
        return {
            "verdict": None,
            "reasons": ["n_oos<%d" % min_n],
            "holes": ["n_oos"],
            "gates": {
                "rps_gap_max": rps_max, "ece_max": ece_max,
                "logloss_gap_max": ll_max, "min_matches_oos": min_n,
            },
        }
    if rps_gap is None:
        holes.append("rps")
    elif rps_gap > rps_max:
        reasons.append("rps_gap")
    if ece is None:
        holes.append("ece")
    elif ece > ece_max:
        reasons.append("ece")
    if logloss_gap is None:
        holes.append("logloss")
    elif logloss_gap > ll_max:
        reasons.append("logloss_gap")
    if holes:
        verdict = None
    elif reasons:
        verdict = "NO-GO"
    else:
        verdict = "GO"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "holes": holes,
        "gates": {
            "rps_gap_max": rps_max, "ece_max": ece_max,
            "logloss_gap_max": ll_max, "min_matches_oos": min_n,
        },
    }


def _ece_bins():
    try:
        import empirique
        cfg = empirique.load_config()
        return int(cfg.get("ece_bins") or 10)
    except Exception:
        return 10


def _by_div(rows):
    out = {}
    for r in rows:
        code = (r.get("div") or r.get("Div") or "").strip().upper()
        out.setdefault(code, []).append(r)
    return out


def evaluate(rows, cutoff, cfg=None, gates=None, ece_bins=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blob = {
        "generated_at": now,
        "engine": "dc_mle",
        "engine_version": "pari.model_dc.v1",
        "cutoff": None,
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
        "offline": True,
    }
    train, test, hole = split_cutoff(rows, cutoff)
    blob["n_train"] = len(train)
    blob["n_test"] = len(test)
    cut = parse_cutoff(cutoff)
    blob["cutoff"] = cut.strftime("%Y-%m-%d") if cut else None
    if hole:
        blob["holes"].append(hole)
        g = apply_gates(0, None, None, None, gates)
        blob.update({k: g[k] for k in ("verdict", "reasons")})
        blob["holes"] = list(dict.fromkeys(blob["holes"] + g["holes"]))
        blob["gates"] = g["gates"]
        return blob
    if any(parse_cutoff(r.get("date") or r.get("Date")) >= cut for r in train):
        blob["holes"].append("in_sample")
        g = apply_gates(0, None, None, None, gates)
        blob["verdict"] = None
        blob["reasons"] = ["in_sample"]
        blob["holes"] = list(dict.fromkeys(blob["holes"] + g["holes"]))
        blob["gates"] = g["gates"]
        return blob
    as_of = cut.strftime("%Y-%m-%d")
    fitted = {}
    for code, lg_rows in _by_div(train).items():
        rec = fit_dc.fit_league(lg_rows, code=code, as_of=as_of, cfg=cfg)
        fitted[code] = rec
        if rec.get("params") != "fitted":
            blob["holes"].append("ligue_absente")
    rps_m, rps_k, ll_m, ll_k = [], [], [], []
    pairs = []
    skipped = 0
    bins = int(ece_bins) if ece_bins else _ece_bins()
    for r in test:
        home, away, fthg, ftag, _dt = fit_dc._row_fields(r)
        outc = outcome_of(fthg, ftag)
        mk = odds_1x2(r)
        if outc is None:
            skipped += 1
            blob["holes"].append("score_ft")
            continue
        if mk is None:
            skipped += 1
            blob["holes"].append("cotes_1x2")
            continue
        code = (r.get("div") or r.get("Div") or "").strip().upper()
        rec = fitted.get(code)
        lam = model_dc.lambdas_for(home, away, rec) if rec else {
            "lh": None, "la": None, "holes": ["ligue_absente"],
        }
        if lam.get("lh") is None or lam.get("la") is None:
            skipped += 1
            blob["holes"].extend(lam.get("holes") or ["equipe_absente"])
            continue
        pm = p_modele_1x2(lam["lh"], lam["la"], lam.get("rho"))
        if pm is None:
            skipped += 1
            blob["holes"].append("p_nulle")
            continue
        rm = walkforward.rps_1x2(pm[0], pm[1], pm[2], outc)
        rk = walkforward.rps_1x2(mk[0], mk[1], mk[2], outc)
        lm = logloss_1x2(pm[0], pm[1], pm[2], outc)
        lk = logloss_1x2(mk[0], mk[1], mk[2], outc)
        if None in (rm, rk, lm, lk):
            skipped += 1
            blob["holes"].append("p_nulle")
            continue
        rps_m.append(rm)
        rps_k.append(rk)
        ll_m.append(lm)
        ll_k.append(lk)
        y1 = 1.0 if outc == "H" else 0.0
        yx = 1.0 if outc == "D" else 0.0
        y2 = 1.0 if outc == "A" else 0.0
        pairs.extend([(pm[0], y1), (pm[1], yx), (pm[2], y2)])
    n = len(rps_m)
    blob["n"] = n
    blob["n_skipped"] = skipped
    blob["rps_modele"] = _round(_mean(rps_m))
    blob["rps_marche"] = _round(_mean(rps_k))
    blob["logloss_modele"] = _round(_mean(ll_m))
    blob["logloss_marche"] = _round(_mean(ll_k))
    if blob["rps_modele"] is not None and blob["rps_marche"] is not None:
        blob["rps_gap"] = _round(blob["rps_modele"] - blob["rps_marche"])
    if blob["logloss_modele"] is not None and blob["logloss_marche"] is not None:
        blob["logloss_gap"] = _round(blob["logloss_modele"] - blob["logloss_marche"])
    blob["ece"] = _round(walkforward.ece(pairs, bins=bins) if pairs else None)
    blob["holes"] = list(dict.fromkeys(blob["holes"]))
    g = apply_gates(n, blob["rps_gap"], blob["ece"], blob["logloss_gap"], gates)
    blob["verdict"] = g["verdict"]
    blob["reasons"] = g["reasons"]
    blob["holes"] = list(dict.fromkeys(blob["holes"] + g["holes"]))
    blob["gates"] = g["gates"]
    return blob


def run_dir(csv_dir, cutoff, out=None, cfg=None, gates=None):
    loaded = market_csv.load_dir(csv_dir)
    rec = evaluate(loaded.get("rows") or [], cutoff, cfg=cfg, gates=gates)
    rec["dir"] = os.path.abspath(csv_dir) if csv_dir else None
    rec["files"] = loaded.get("files") or []
    for h in loaded.get("holes") or []:
        if h not in rec["holes"]:
            rec["holes"].append(h)
    if loaded.get("holes") and not (loaded.get("rows") or []):
        rec["verdict"] = None
        if "n_oos" not in rec["holes"]:
            rec["holes"].append("n_oos")
        rec["reasons"] = list(dict.fromkeys((rec.get("reasons") or []) + loaded["holes"]))
    if out:
        save(rec, out)
    return rec


def save(blob, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load(path=None):
    p = path or DEFAULT_OUT
    if not p or not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def main():
    ap = argparse.ArgumentParser(description="V2c calibration RPS/ECE vs marche")
    ap.add_argument("--dir", default=os.path.join(WORLD, "ARCHIVUM", "cache", "f00"))
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    rec = run_dir(args.dir, args.cutoff, out=args.out)
    print(json.dumps({
        "out": os.path.abspath(args.out),
        "n": rec.get("n"),
        "verdict": rec.get("verdict"),
        "rps_gap": rec.get("rps_gap"),
        "ece": rec.get("ece"),
        "logloss_gap": rec.get("logloss_gap"),
        "holes": rec.get("holes"),
        "reasons": rec.get("reasons"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
