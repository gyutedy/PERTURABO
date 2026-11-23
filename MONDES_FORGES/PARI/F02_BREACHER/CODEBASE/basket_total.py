#!/usr/bin/env python3
"""
BASKET TOTAL — calibration du marche "nombre total de points".
=============================================================
Meme esprit que le foot O/U : la cote Over/Under porte sur le TOTAL
des DEUX equipes, pas sur les points d'une seule equipe. Modele ridge
stdlib : points marques/encaisses recents + repos. sigma_total = ecart
type des residus mesure HORS echantillon (jamais pose a la main).
"""
from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "state", "basket_total.json")
CONTRACT = "pari.basket_total.v1"
CUTOFF_TRAIN = "2026-01-01"
CUTOFF_TEST = "2026-11-22"


def _dt(s):
    return date.fromisoformat(str(s or "")[:10])


def state_at(rows, upto, window=10):
    st = {}
    for r in rows:
        if r["date"] >= upto:
            break
        for t, own, opp in ((r["home"], r["pts_home"], r["pts_away"]),
                            (r["away"], r["pts_away"], r["pts_home"])):
            d = st.setdefault(t, {"scored": [], "allowed": [], "last": r["date"]})
            d["scored"].append(own)
            d["allowed"].append(opp)
            d["last"] = r["date"]
    return st


def avg(vals, window=10):
    v = vals[-window:]
    return sum(v) / len(v) if v else None


def features(home, away, day, st, base):
    h, a = st.get(home) or {}, st.get(away) or {}
    sh, sa = avg(h.get("scored") or []), avg(a.get("scored") or [])
    ah, aa = avg(h.get("allowed") or []), avg(a.get("allowed") or [])
    if sh is None or sa is None:
        return None
    rest_h = (_dt(day) - _dt(h["last"])).days if h.get("last") else 14
    rest_a = (_dt(day) - _dt(a["last"])).days if a.get("last") else 14
    return [1.0, (sh + ah + sa + aa) / 2 - base, rest_h - rest_a]


def _solve(X, Y, lam=200.0):
    p = len(X[0])
    A = [[sum(x[i] * x[j] for x in X) + (lam if i == j and i != 0 else 0)
          for j in range(p)] for i in range(p)]
    b = [sum(x[i] * y for x, y in zip(X, Y)) for i in range(p)]
    for i in range(p):
        for j in range(i + 1, p):
            f = A[j][i] / A[i][i]
            for k in range(i, p):
                A[j][k] -= f * A[i][k]
            b[j] -= f * b[i]
    w = [0.0] * p
    for i in reversed(range(p)):
        w[i] = (b[i] - sum(A[i][j] * w[j] for j in range(i + 1, p))) / A[i][i]
    return w


def fit(rows, out=None):
    rows = sorted([r for r in rows if r.get("date") and r.get("pts_home") is not None],
                  key=lambda r: r["date"])
    base = sum(r["pts_home"] + r["pts_away"] for r in rows) / len(rows)
    train = [r for r in rows if r["date"] < CUTOFF_TRAIN]
    test = [r for r in rows if CUTOFF_TRAIN <= r["date"] < CUTOFF_TEST]
    X, Y = [], []
    for r in train:
        st = state_at(rows, r["date"])
        f = features(r["home"], r["away"], r["date"], st, base)
        if f:
            X.append(f)
            Y.append(r["pts_home"] + r["pts_away"])
    w = _solve(X, Y)
    residus = []
    for r in test:
        st = state_at(rows, r["date"])
        f = features(r["home"], r["away"], r["date"], st, base)
        if f:
            pred = sum(a * b for a, b in zip(w, f))
            residus.append((r["pts_home"] + r["pts_away"]) - pred)
    sigma = math.sqrt(sum(x * x for x in residus) / len(residus)) if residus else None
    blob = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "nba_api boxscores (via basket_feed)",
        "n_train": len(X), "n_test": len(residus),
        "base_total": round(base, 4),
        "weights": [round(x, 6) for x in w],
        "sigma_total": round(sigma, 4) if sigma else None,
        "tickets_enabled": False,
    }
    target = out or DEFAULT_OUT
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    return blob


def load(path=None):
    try:
        with open(path or DEFAULT_OUT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def p_over(blob, home, away, day, st, line):
    if not blob or not blob.get("sigma_total"):
        return None
    f = features(home, away, day, st, blob["base_total"])
    if not f:
        return None
    mu = sum(a * b for a, b in zip(f, blob["weights"]))
    z = (float(line) - mu) / blob["sigma_total"]
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def main():
    import sys
    p = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
    if p not in sys.path:
        sys.path.insert(0, p)
    import market_basket
    rows, holes = market_basket.load_dir()
    b = fit(rows)
    print("[total] n=%d/%d base=%.1f sigma_total=%.2f poids=%s" %
          (b["n_train"], b["n_test"], b["base_total"], b["sigma_total"], b["weights"]))


if __name__ == "__main__":
    main()
