#!/usr/bin/env python3
"""
BASKET CALIB — modele marges Ameliore : ratings + repos + forme (cahier V3 P2).
==============================================================================
Entrainement STRICTEMENT anterieur au cutoff (aucune fuite). Ridge stdlib.
Le modele reste juge par backtest_market.apply_gates : un brier_gap > 0
signifie qu'il est MOINS bon que le marche -> verdict NO-GO, aucun pari.
"""
from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timezone


def _p_home(margin, sigma):
    try:
        return 0.5 * (1.0 + math.erf(margin / (float(sigma) * math.sqrt(2.0))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.5

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "state", "basket_calib.json")
CONTRACT = "pari.basket_calib.v1"
FEATURES = ("interception", "rating_diff", "rest_diff", "form_diff", "ratings_present")
SIGMA = 15.0
LAMBDA = 500.0
CUTOFF = "2025-01-01"


def _dt(s):
    return date.fromisoformat(str(s or "")[:10])


def state_at(rows, upto):
    last, diffs = {}, {}
    for r in rows:
        if (r.get("date") or "") >= upto:
            break
        for t, sign in ((r.get("home"), 1), (r.get("away"), -1)):
            if not t:
                continue
            last[t] = r["date"]
            diffs.setdefault(t, []).append(sign * (r.get("pts_home", 0) - r.get("pts_away", 0)))
    return last, diffs


def features(home, away, day, last, diffs, ratings=None):
    rh = (_dt(day) - _dt(last[home])).days if home in last else 30
    ra = (_dt(day) - _dt(last[away])).days if away in last else 30
    fh = sum(diffs.get(home, [])[-5:]) / max(1, len(diffs.get(home, [])[-5:]))
    fa = sum(diffs.get(away, [])[-5:]) / max(1, len(diffs.get(away, [])[-5:]))
    ratings = ratings or {}
    present = 1.0 if home in ratings and away in ratings else 0.0
    rt = (ratings.get(home, {}).get("rtg", 0) - ratings.get(away, {}).get("rtg", 0)) if present else 0.0
    return [1.0, rt, float(rh - ra), float(fh - fa), present]


def _solve(X, Y, lam):
    p = len(X[0])
    A = [[sum(x[i] * x[j] for x in X) + (lam if i == j else 0) for j in range(p)] for i in range(p)]
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


def fit(rows, ratings, cutoff=CUTOFF, lam=LAMBDA, out=None):
    rows = sorted([r for r in rows if r.get("date") and r.get("pts_home") is not None
                   and r.get("pts_away") is not None], key=lambda r: r["date"])
    train = [r for r in rows if r["date"] < cutoff]
    X, Y = [], []
    for r in train:
        last, diffs = state_at(rows, r["date"])
        X.append(features(r["home"], r["away"], r["date"], last, diffs, ratings))
        Y.append(r["pts_home"] - r["pts_away"])
    w = _solve(X, Y, lam)
    bm = bk = 0.0
    n_test = 0
    for r in rows:
        if r["date"] < cutoff or r.get("pts_home") is None:
            continue
        mk = None
        try:
            oh, oa = float(r.get("odds_home")), float(r.get("odds_away"))
            s = 1 / oh + 1 / oa
            mk = (1 / oh) / s
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        if mk is None:
            continue
        last, diffs = state_at(rows, r["date"])
        m = sum(a * b for a, b in zip(w, features(r["home"], r["away"], r["date"],
                                                 last, diffs, ratings)))
        p = _p_home(m, SIGMA)
        y = 1.0 if r["pts_home"] > r["pts_away"] else 0.0
        bm += (p - y) ** 2
        bk += (mk - y) ** 2
        n_test += 1
    gap = round(bm / n_test - bk / n_test, 6) if n_test else None
    blob = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff,
        "n_train": len(train),
        "n_test": n_test,
        "brier_model": round(bm / n_test, 6) if n_test else None,
        "brier_marche": round(bk / n_test, 6) if n_test else None,
        "brier_gap": gap,
        "verdict": ("GO" if gap is not None and gap <= 0 else "NO-GO"),
        "lambda": lam,
        "sigma": SIGMA,
        "features": list(FEATURES),
        "weights": [round(x, 6) for x in w],
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


def predict_margin(blob, home, away, day, last, diffs, ratings=None):
    if not blob:
        return None, ["calibration_absente"]
    f = features(home, away, day, last, diffs, ratings)
    w = blob.get("weights") or []
    if len(w) != len(f):
        return None, ["poids_invalides"]
    m = sum(a * b for a, b in zip(w, f))
    holes = []
    if not f[-1]:
        holes.append("equipes_hors_calibration")
    if all(x == last.get(home) for x in [last.get(home)]) and home not in last:
        holes.append("forme_absente:" + str(home))
    return round(m, 4), holes


def main():
    p = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)
    import market_basket
    import fit_basket
    rows, holes = market_basket.load_dir()
    train = [r for r in rows if (r.get("date") or "")[:10] < CUTOFF]
    ratings = (fit_basket.fit(fit_basket.prepare(train)) or {}).get("teams") or {}
    blob = fit(rows, ratings)
    print("[calib] n=%d sigma=%.1f poids=%s -> %s" %
          (blob["n_train"], blob["sigma"], blob["weights"], DEFAULT_OUT))


if __name__ == "__main__":
    main()
