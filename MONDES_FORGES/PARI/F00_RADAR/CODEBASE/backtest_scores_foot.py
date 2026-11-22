#!/usr/bin/env python3
"""
BACKTEST SCORES FOOT — walk-forward 1X2 vs marche (stdlib, offline).
===================================================================
Source : CSV football-data.co.uk via market_csv.load_dir (FTHG/FTAG,
cotes ouverture + cloture). OOS = dernier tiers, ou cutoff explicite.
Refit Dixon-Coles tous les 30 jours sur t < date du match (aucune fuite).
Metriques : Brier 1X2, RPS, log-loss, ECE bine, CLV sur les paris du
modele. Verdict via backtest_market.apply_gates — UNE seule autorite.
Sortie : ARCHIVUM/learnings/calibration_scores_foot.json (gitignore).
Ne touche jamais tickets_enabled.
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
for _p in (HERE, os.path.join(WORLD, "F02_BREACHER", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import backtest_market  # noqa: E402  autorite des portes
import fit_dc  # noqa: E402  MLE Dixon-Coles
import market_csv  # noqa: E402  contrat de donnees foot
import model_dc  # noqa: E402  matrice de scores
import moteur_flag  # noqa: E402  lecture des gates
import walkforward  # noqa: E402  RPS 1X2

DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "learnings", "calibration_scores_foot.json")
DEFAULT_CACHE = os.path.join(WORLD, "ARCHIVUM", "cache", "f00")
FOOT_CFG = os.path.join(WORLD, "config", "moteur.json")
REFIT_DAYS = 30
Y3 = {"1": (1, 0, 0), "X": (0, 1, 0), "2": (0, 0, 1)}
OUTCOME_RPS = {"1": "H", "X": "D", "2": "A"}
KEY_ODDS = {"1": "home", "X": "draw", "2": "away"}
EPS = 1e-15
CONTRACT = "pari.calibration_scores_foot.v1"


def ece_binned(pairs, bins=10):
    """Vrai ECE bine (identique a backtest_basket.ece_binned)."""
    if not pairs:
        return None
    n = len(pairs)
    acc = 0.0
    for k in range(bins):
        lo, hi = k / bins, (k + 1) / bins
        bk = [(p, y) for p, y in pairs
              if (lo <= p < hi) or (k == bins - 1 and lo <= p <= hi)]
        if not bk:
            continue
        acc += len(bk) / n * abs(sum(p for p, _ in bk) / len(bk)
                                 - sum(y for _, y in bk) / len(bk))
    return acc


def _ordinal(d):
    return datetime.strptime((d or "")[:10], "%Y-%m-%d").toordinal()


def _outcome(row):
    h, a = row.get("fthg"), row.get("ftag")
    if h is None or a is None:
        return None
    return "1" if h > a else "X" if h == a else "2"


def _fit_all(hist, as_of, cfg=None):
    """Fit par ligue sur l'historique ANTIEURIEUR uniquement."""
    by_div = {}
    for r in hist:
        by_div.setdefault(r.get("div") or "X", []).append(r)
    blobs = {}
    for code, rws in by_div.items():
        try:
            rec = fit_dc.fit_league(rws, code=code, as_of=as_of, cfg=cfg)
            if rec and rec.get("params") == "fitted":
                blobs[code] = rec
        except Exception:
            continue
    return {"leagues": blobs}


def _p_1x2(lh, la, rho):
    """Probas 1X2 depuis la vraie matrice de scores Dixon-Coles."""
    m = model_dc.score_matrix(lh, la, rho=rho)
    if not m:
        return None
    p1 = px = p2 = 0.0
    for i, row in enumerate(m):
        for j, q in enumerate(row):
            if i > j:
                p1 += q
            elif i == j:
                px += q
            else:
                p2 += q
    if min(p1, px, p2) <= 0:
        return None
    return p1, px, p2


def _split(rows, cutoff):
    """(train, test). Sans cutoff : OOS = dernier tiers."""
    if cutoff:
        cut = walkforward.parse_cutoff(cutoff)
        if cut is None:
            return rows[:int(len(rows) * 2 / 3)], rows[int(len(rows) * 2 / 3):]
        cut_s = cut.isoformat()[:10]
        return ([r for r in rows if r["date"] < cut_s],
                [r for r in rows if r["date"] >= cut_s])
    i0 = int(len(rows) * 2 / 3)
    return rows[:i0], rows[i0:]


def run(csv_dir=None, out_path=None, cutoff=None, cfg=None, gates=None):
    data = market_csv.load_dir(csv_dir or DEFAULT_CACHE)
    rows = [r for r in (data.get("rows") or [])
            if r.get("date") and r.get("fthg") is not None and r.get("ftag") is not None]
    holes = list(data.get("holes") or [])
    rows.sort(key=lambda r: r["date"])
    if len(rows) < 100:
        holes.append("historique_insuffisant")
        return {"contract": CONTRACT, "generated_at": datetime.now(timezone.utc).isoformat(),
                "verdict": None, "reasons": [], "holes": holes,
                "n_oos": 0, "n_marche": 0, "in_sample": False,
                "tickets_enabled": False}
    train, test = _split(rows, cutoff)
    n = 0
    brier_m = rps_m = ll_m = 0.0
    brier_mk = rps_mk = ll_mk = 0.0
    n_mk = 0
    pairs_ece = []
    clv_sum = 0.0
    clv_n = 0
    last_refit = -10 ** 9
    blobs = None
    for r in test:
        o = _ordinal(r["date"])
        if o - last_refit >= REFIT_DAYS or blobs is None:
            hist = [x for x in train if _ordinal(x["date"]) < o]
            blobs = _fit_all(hist, r["date"], cfg=cfg)
            last_refit = o
        code = r.get("div") or "X"
        rec = fit_dc.params_for(code, blob=blobs)
        lam = model_dc.lambdas_for(r.get("home"), r.get("away"), rec)
        lh, la = lam.get("lh"), lam.get("la")
        if lh is None or la is None:
            holes.append("lambda_absent:" + code)
            continue
        rho = rec.get("rho") if rec.get("rho") is not None else model_dc.RHO_DC
        triple = _p_1x2(lh, la, rho)
        if triple is None:
            holes.append("p_nulle")
            continue
        p1, px, p2 = triple
        outcome = _outcome(r)
        if outcome is None:
            continue
        p = {"1": p1, "X": px, "2": p2}
        pv = (p1, px, p2)
        y = Y3[outcome]
        n += 1
        brier_m += sum((pv[k] - y[k]) ** 2 for k in range(3))
        rps_rps = walkforward.rps_1x2(p1, px, p2, OUTCOME_RPS[outcome])
        if rps_rps is not None:
            rps_m += rps_rps
        ll_m -= math.log(max(p[outcome], EPS))
        fav = max(p, key=p.get)
        pairs_ece.append((p[fav], 1.0 if fav == outcome else 0.0))
        cl = r.get("cloture") or {}
        mk = backtest_market.implied_1x2(cl.get("home"), cl.get("draw"), cl.get("away"))
        if mk is None:
            holes.append("marche_absent")
            continue
        n_mk += 1
        pmk = {"1": mk[0], "X": mk[1], "2": mk[2]}
        mkv = (mk[0], mk[1], mk[2])
        ym = Y3[outcome]
        brier_mk += sum((mkv[k] - ym[k]) ** 2 for k in range(3))
        rps_mk_r = walkforward.rps_1x2(mk[0], mk[1], mk[2], OUTCOME_RPS[outcome])
        if rps_mk_r is not None:
            rps_mk += rps_mk_r
        ll_mk -= math.log(max(pmk[outcome], EPS))
        op = r.get("ouverts") or {}
        k = KEY_ODDS[fav]
        if (p[fav] > pmk[fav] + 0.03 and op.get(k) is not None
                and cl.get(k) is not None and float(cl[k]) > 1.0):
            clv_sum += float(op[k]) / float(cl[k]) - 1.0
            clv_n += 1
    brier_m = round(brier_m / n, 6) if n else None
    brier_mk = round(brier_mk / n_mk, 6) if n_mk else None
    rps_m = round(rps_m / n, 6) if n else None
    rps_mk = round(rps_mk / n_mk, 6) if n_mk else None
    ll_m = round(ll_m / n, 6) if n else None
    ll_mk = round(ll_mk / n_mk, 6) if n_mk else None
    ece = round(ece_binned(pairs_ece), 6) if n else None
    clv = round(clv_sum / clv_n, 6) if clv_n else None
    rps_gap = round(rps_m - rps_mk, 6) if rps_m is not None and rps_mk is not None else None
    ll_gap = round(ll_m - ll_mk, 6) if ll_m is not None and ll_mk is not None else None
    if n_mk:
        verdict_block = backtest_market.apply_gates(
            n, rps_gap, ece, ll_gap,
            gates=gates if isinstance(gates, dict) else (moteur_flag.gates(FOOT_CFG) or {}))
    else:
        verdict_block = {"verdict": None, "reasons": [],
                         "holes": ["marche_absent"], "gates": {}}
    out = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "dc_mle",
        "in_sample": False,
        "n_oos": n,
        "n_marche": n_mk,
        "brier_modele": brier_m,
        "brier_marche": brier_mk,
        "rps_modele": rps_m,
        "rps_marche": rps_mk,
        "rps_gap": rps_gap,
        "logloss_modele": ll_m,
        "logloss_marche": ll_mk,
        "logloss_gap": ll_gap,
        "ece": ece,
        "clv_model_bets": clv,
        "n_clv": clv_n,
        "verdict": verdict_block.get("verdict"),
        "reasons": list(verdict_block.get("reasons") or []),
        "holes": list(dict.fromkeys(holes + list(verdict_block.get("holes") or []))),
        "tickets_enabled": False,
    }
    target = out_path or DEFAULT_OUT
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    backtest_market.save(out, target)
    out["out"] = os.path.abspath(target)
    return out


def main():
    ap = argparse.ArgumentParser(description="backtest scores foot 1X2 walk-forward")
    ap.add_argument("--dir", default=DEFAULT_CACHE)
    ap.add_argument("--cutoff", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    print(json.dumps(run(csv_dir=args.dir, out_path=args.out, cutoff=args.cutoff),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
