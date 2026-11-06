#!/usr/bin/env python3
"""
CLV — closing line value (S9 / v3.10)
=====================================
clv = cote_prise / cote_cloture - 1
Cloture absente = exclu, jamais 0. Stdlib only. Zero Data, Zero Calc.
"""

from __future__ import annotations

import json
import os
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CFG_PATH = os.path.join(WORLD, "config", "clv.json")

DEFAULTS = {
    "clv_beat_pct": 0.55,
    "clv_median_pt": 0.5,
    "clv_alerte_pt": -3.0,
    "n_variance": 30,
    "n_lock": 50,
    "mc_draws": 2000,
    "mc_seed": 42,
}


def load_config(path=None):
    cfg = dict(DEFAULTS)
    p = path or CFG_PATH
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return cfg
        if isinstance(raw, dict):
            for k in DEFAULTS:
                if k in raw:
                    cfg[k] = raw[k]
    return cfg


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clv_ratio(prise, close):
    p = _f(prise)
    c = _f(close)
    if p is None or c is None:
        return None
    if p <= 1 or c <= 1:
        return None
    return p / c - 1.0


def close_product(jambes):
    prod = 1.0
    n = 0
    for j in jambes or []:
        c = _f((j or {}).get("book_odds_close"))
        if c is None or c <= 1:
            return None
        prod *= c
        n += 1
    if n == 0 or prod <= 1:
        return None
    return prod


def ticket_clv(snap_t, settle_t):
    snap_t = snap_t or {}
    settle_t = settle_t or {}
    prise = snap_t.get("cote_totale")
    if prise is None:
        prise = settle_t.get("cote_totale")
    if prise is None:
        prise = settle_t.get("cote")
    close = close_product(settle_t.get("jambes"))
    return clv_ratio(prise, close)


def to_pts(ratio):
    r = _f(ratio)
    if r is None:
        return None
    return r * 100.0


def aggregate(ratios, mises=None):
    vals = []
    weights = []
    if mises is None:
        mises = [None] * len(ratios or [])
    for r, m in zip(ratios or [], mises):
        v = _f(r)
        if v is None:
            continue
        vals.append(v)
        weights.append(_f(m))
    if not vals:
        return {
            "n": 0,
            "median": None,
            "median_pt": None,
            "pct_pos": None,
            "mean_weighted": None,
            "mean_weighted_pt": None,
            "holes": ["clv"],
        }
    med = float(median(vals))
    pct_pos = sum(1 for v in vals if v > 0) / len(vals)
    num = 0.0
    den = 0.0
    n_w = 0
    for v, w in zip(vals, weights):
        if w is None or w <= 0:
            continue
        num += v * w
        den += w
        n_w += 1
    if n_w:
        mean_w = num / den
    else:
        mean_w = sum(vals) / len(vals)
    return {
        "n": len(vals),
        "median": med,
        "median_pt": med * 100.0,
        "pct_pos": pct_pos,
        "mean_weighted": mean_w,
        "mean_weighted_pt": mean_w * 100.0,
        "holes": [],
    }


def collect_from_lots(lots):
    rows = []
    for lot in lots or []:
        snap_map = {
            t.get("rang_ticket"): t
            for t in ((lot.get("snapshot_t0") or {}).get("tickets") or [])
        }
        for t in (lot.get("settle") or {}).get("tickets") or []:
            src = snap_map.get(t.get("rang_ticket")) or {}
            ratio = t.get("clv")
            if ratio is None:
                ratio = ticket_clv(src, t)
            mise = src.get("mise_fc")
            if mise is None:
                mise = t.get("mise_fc")
            rows.append({
                "clv": ratio,
                "mise_fc": mise,
                "ticket": t,
                "snap": src,
                "lot": lot,
            })
    return rows
