#!/usr/bin/env python3
"""
BASKET PRIOR — experience "marche comme prior" (cahier P2, phase 5).
====================================================================
On ne remplace pas le prix du book : on modele l'ECART entre le resultat
et la probabilite implicite du book, puis on corrige le prix.
Resultat OOS reel : brier 0,1957 contre 0,1953 au marche -> gap +0,0004.
AUCUN edge : module desactive (enabled=false), jamais producteur de p.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(WORLD, "config", "basket_prior.json")
CONTRACT = "pari.basket_prior.v1"
LAMBDA = 2000.0


def implied(oh, oa):
    try:
        oh, oa = float(oh), float(oa)
        if oh <= 1 or oa <= 1:
            return None
        s = 1 / oh + 1 / oa
        return (1 / oh) / s
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _solve(X, Y, lam):
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


def fit(rows, features_fn, cutoff="2025-01-01", out=None):
    X, Y = [], []
    rows = [r for r in rows if r.get("source_prix") != "proxy_yahoo"]
    for r in rows:
        if r.get("date", "") >= cutoff:
            continue
        pm = implied(r.get("odds_home"), r.get("odds_away"))
        if pm is None:
            continue
        y = 1.0 if r.get("pts_home", 0) > r.get("pts_away", 0) else 0.0
        X.append(features_fn(r))
        Y.append(y - pm)
    w = _solve(X, Y, LAMBDA)
    bm = bk = 0.0
    n = 0
    for r in rows:
        if r.get("date", "") < cutoff:
            continue
        pm = implied(r.get("odds_home"), r.get("odds_away"))
        if pm is None:
            continue
        corr = sum(a * b for a, b in zip(w, features_fn(r)))
        p = min(0.99, max(0.01, pm + corr))
        y = 1.0 if r.get("pts_home", 0) > r.get("pts_away", 0) else 0.0
        bm += (p - y) ** 2
        bk += (pm - y) ** 2
        n += 1
    gap = round(bm / n - bk / n, 6) if n else None
    blob = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_train": len(X), "n_test": n,
        "brier_modele": round(bm / n, 6) if n else None,
        "brier_marche": round(bk / n, 6) if n else None,
        "brier_gap": gap,
        "verdict": "GO" if gap is not None and gap <= 0 else "NO-GO",
        "enabled": False,
        "weights": [round(x, 6) for x in w],
        "note": " aucun edge OOS ; desactive, jamais producteur de p",
        "tickets_enabled": False,
    }
    target = out or DEFAULT_OUT
    with open(target, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    return blob


def load(path=None):
    try:
        with open(path or DEFAULT_OUT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    import sys
    for d in ("F00_RADAR", "F02_BREACHER"):
        p = os.path.join(WORLD, d, "CODEBASE")
        if p not in sys.path:
            sys.path.insert(0, p)
    import market_basket
    import fit_basket
    import basket_calib
    rows, _ = market_basket.load_dir()
    ratings = (fit_basket.load_params() or {}).get("teams") or {}

    def feats(r):
        last, diffs = basket_calib.state_at(rows, r["date"])
        return basket_calib.features(r["home"], r["away"], r["date"], last, diffs, ratings) or [1.0, 0, 0, 0, 0]

    blob = fit(rows, feats)
    print("[prior] gap=%s verdict=%s (desactive)" % (blob["brier_gap"], blob["verdict"]))


if __name__ == "__main__":
    main()
