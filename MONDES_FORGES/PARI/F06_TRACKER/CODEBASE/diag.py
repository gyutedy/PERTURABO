#!/usr/bin/env python3
"""
F06 DIAGNOSTIC — Platt / Beta-Binomial / P(EV>0) MC (S9 / v3.10)
================================================================
n<50 tickets reels : sorties = diagnostic /data, jamais verdict/mise.
F06 n'apprend pas. Stdlib only. Zero Data, Zero Calc. MC seede.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import clv as _clv  # noqa: E402

EPS = 1e-6


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def logit(p):
    x = min(max(float(p), EPS), 1.0 - EPS)
    return math.log(x / (1.0 - x))


def sigmoid(z):
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def platt_fit(pairs, iters=80, lr=0.15):
    xs, ys = [], []
    for p, y in pairs or []:
        pf, yf = _f(p), _f(y)
        if pf is None or yf is None:
            continue
        if not (0.0 < pf < 1.0):
            continue
        xs.append(logit(pf))
        ys.append(1.0 if yf >= 0.5 else 0.0)
    n = len(xs)
    if n < 2:
        return None, None, ["n_platt"]
    a, b = 1.0, 0.0
    for _ in range(iters):
        ga = 0.0
        gb = 0.0
        for x, y in zip(xs, ys):
            pred = sigmoid(a * x + b)
            g = pred - y
            ga += g * x
            gb += g
        a -= lr * ga / n
        b -= lr * gb / n
    return a, b, []


def platt_apply(p, a, b):
    pf = _f(p)
    if pf is None or a is None or b is None:
        return None
    if not (0.0 < pf < 1.0):
        return None
    return sigmoid(a * logit(pf) + b)


def beta_binomial(ys):
    n = 0
    k = 0
    for y in ys or []:
        yf = _f(y)
        if yf is None:
            continue
        n += 1
        if yf >= 0.5:
            k += 1
    if n == 0:
        return None
    alpha = 1.0 + k
    beta = 1.0 + (n - k)
    return {
        "alpha": alpha,
        "beta": beta,
        "n": n,
        "k": k,
        "mean": alpha / (alpha + beta),
    }


def p_ev_positif(obs, a=None, b=None, bb=None, draws=2000, seed=42):
    if not obs:
        return None
    rng = random.Random(seed)
    kappa = 2.0
    if bb:
        kappa = float(bb.get("alpha", 1) + bb.get("beta", 1))
    kappa = max(kappa, 2.0)
    hits = 0
    n_ok = 0
    for _ in range(int(draws)):
        port = 0.0
        wsum = 0.0
        for o in obs:
            p0 = o["p"]
            if a is not None and b is not None:
                cal = platt_apply(p0, a, b)
                if cal is not None:
                    p0 = cal
            aa = max(p0 * kappa, EPS)
            bbv = max((1.0 - p0) * kappa, EPS)
            p_s = rng.betavariate(aa, bbv)
            cote = o["cote"]
            mise = o["mise"]
            port += (p_s * cote - 1.0) * mise
            wsum += mise
        if wsum <= 0:
            continue
        n_ok += 1
        if port > 0:
            hits += 1
    if n_ok == 0:
        return None
    return hits / n_ok


def _p_from_snap(snap):
    p = _f((snap or {}).get("p_aggregee"))
    if p is not None:
        return p
    prod = 1.0
    n = 0
    for j in (snap or {}).get("jambes") or []:
        pj = _f(j.get("p_modele"))
        if pj is None or not (0.0 < pj < 1.0):
            return None
        prod *= pj
        n += 1
    return prod if n else None


def observations(rows):
    out = []
    holes = []
    for r in rows or []:
        t = r.get("ticket") or {}
        if t.get("resultat") not in ("G", "P"):
            continue
        snap = r.get("snap") or {}
        p = _p_from_snap(snap)
        cote = _f(snap.get("cote_totale"))
        if cote is None:
            cote = _f(t.get("cote"))
        if p is None:
            holes.append("p_modele")
            continue
        if cote is None or cote <= 1:
            holes.append("cote")
            continue
        if not (0.0 < p < 1.0):
            holes.append("p_modele")
            continue
        mise = _f(snap.get("mise_fc"))
        if mise is None:
            mise = _f(t.get("mise_fc"))
        if mise is None or mise <= 0:
            mise = 1.0
        y = 1.0 if t.get("resultat") == "G" else 0.0
        out.append({"p": p, "y": y, "cote": cote, "mise": mise, "clv": r.get("clv")})
    return out, holes


def as_verdict(report):
    if not report:
        return None
    if report.get("locked") or int(report.get("n") or 0) < 50:
        return None
    return {
        "role": "diagnostic",
        "p_ev_positif": report.get("p_ev_positif"),
        "platt": report.get("platt"),
        "mise": None,
    }


def diagnose(lots, config=None, n_lock=None, seed=None, draws=None):
    cfg = config or _clv.load_config()
    lock_at = int(cfg["n_lock"] if n_lock is None else n_lock)
    mc_seed = int(cfg["mc_seed"] if seed is None else seed)
    mc_draws = int(cfg["mc_draws"] if draws is None else draws)
    rows = _clv.collect_from_lots(lots)
    obs, holes = observations(rows)
    n = len(obs)
    locked = n < lock_at
    ratios = [r.get("clv") for r in rows]
    mises = [r.get("mise_fc") for r in rows]
    agg = _clv.aggregate(ratios, mises)
    pairs = [(o["p"], o["y"]) for o in obs]
    a, b, pholes = platt_fit(pairs)
    holes.extend(pholes)
    bb = beta_binomial([o["y"] for o in obs])
    if bb is None:
        holes.append("beta_binomial")
    p_ev = None
    if obs:
        p_ev = p_ev_positif(obs, a=a, b=b, bb=bb, draws=mc_draws, seed=mc_seed)
    else:
        holes.append("p_ev_positif")
    uniq = []
    seen = set()
    for h in holes:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    note = "n<50 tickets reels — diagnostic /data, jamais verdict/mise" if locked else (
        "n>=50 — mesure diagnostic /data, jamais une mise (S10 Kelly)"
    )
    if n == 0:
        note = "0 ticket reel — diagnostic vide, jamais verdict/mise"
    platt = None
    if a is not None:
        platt = {"a": round(a, 6), "b": round(b, 6)}
    return {
        "n": n,
        "n_lock": lock_at,
        "locked": locked,
        "role": "diagnostic",
        "note": note,
        "verdict": None,
        "mise": None,
        "platt": platt,
        "beta_binomial": bb,
        "p_ev_positif": p_ev,
        "clv": agg,
        "cibles": {
            "beat_pct": cfg["clv_beat_pct"],
            "median_pt": cfg["clv_median_pt"],
        },
        "mc_seed": mc_seed,
        "holes": uniq,
    }


def format_telegram(report):
    if not report:
        return "F06 DIAG: indisponible"
    n = report.get("n") or 0
    lock = "LOCKED" if report.get("locked") else "UNLOCK"
    lines = [
        f"F06 DIAG n={n} {lock}",
        report.get("note") or "",
    ]
    agg = report.get("clv") or {}
    if agg.get("n"):
        med = agg.get("median_pt")
        beat = agg.get("pct_pos")
        cibles = report.get("cibles") or {}
        med_s = f"{med:+.2f}pt" if med is not None else "trou"
        beat_s = f"{beat * 100:.1f}%" if beat is not None else "trou"
        lines.append(
            f"CLV n={agg['n']} median={med_s} beat={beat_s} "
            f"cible {float(cibles.get('beat_pct') or 0) * 100:.0f}% / "
            f"+{cibles.get('median_pt')}pt"
        )
        mw = agg.get("mean_weighted_pt")
        if mw is not None:
            lines.append(f"CLV mean_w={mw:+.2f}pt")
    else:
        lines.append("CLV: trou (pas 0)")
    platt = report.get("platt")
    if platt:
        lines.append(f"Platt a={platt.get('a')} b={platt.get('b')}")
    else:
        lines.append("Platt: trou")
    bb = report.get("beta_binomial")
    if bb:
        lines.append(
            f"Beta-Binomial a={bb.get('alpha')} b={bb.get('beta')} "
            f"mean={bb.get('mean'):.3f}"
        )
    else:
        lines.append("Beta-Binomial: trou")
    p_ev = report.get("p_ev_positif")
    if p_ev is None:
        lines.append("P(EV>0): trou")
    else:
        lines.append(f"P(EV>0)={p_ev:.3f} (MC seed={report.get('mc_seed')})")
    if n and n < 30:
        lines.append("Doctor: n<30 variance, pas un verdict")
    lines.append("Jamais verdict/mise. F06 n'apprend pas.")
    return "\n".join(x for x in lines if x)
