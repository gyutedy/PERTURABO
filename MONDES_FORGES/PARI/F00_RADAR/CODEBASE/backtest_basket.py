#!/usr/bin/env python3
"""
BACKTEST BASKET — calibration OOS Brier/ECE vs marche (stdlib, offline).
======================================================================
Reutilise apply_gates de backtest_market.py (foot) : UNE seule autorite
des portes. Ne touche jamais tickets_enabled. Verdict GO exige :
  n >= min_matches_oos ET brier_gap <= brier_gap_max ET ece <= ece_max.
Marche 2 issues (moneyline) : proba implicite sans nul = 1/devig(cote).
Sans cote de cloture : brier_gap = None + hole "marche_absent" — jamais
impute, jamais 'estime a partir de l'ouverture'.
"""
from __future__ import annotations
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
for p in (HERE, os.path.join(WORLD, "F02_BREACHER", "CODEBASE")):
    if p not in sys.path:
        sys.path.insert(0, p)

import backtest_market          # noqa: E402  (autorite des portes)
import market_basket            # noqa: E402
import model_basket             # noqa: E402
import fit_basket               # noqa: E402
import engine_basket            # noqa: E402
import moteur_flag              # noqa: E402

DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "learnings", "calibration_basket.json")


def parse_cutoff(raw):
    """YYYY-MM-DD. Vide = rien."""
    raw = (raw or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw[:10], "%Y-%m-%d").date()


def split_cutoff(rows, cutoff):
    """(train, test) par date stricte. Cutoff absente = (tout, [])."""
    if cutoff is None:
        return list(rows), []
    train = [r for r in rows if (r.get("date") or "")[:10] < cutoff.isoformat()]
    test = [r for r in rows if (r.get("date") or "")[:10] >= cutoff.isoformat()]
    return train, test


def implied_2way(odds_home, odds_away):
    """(p_implicite_home, p_implicite_away) devig multiplicatif, ou None."""
    try:
        oh, oa = float(odds_home), float(odds_away)
        if oh <= 1.0 or oa <= 1.0:
            return None
        inv = 1.0 / oh + 1.0 / oa
        return (1.0 / oh) / inv, (1.0 / oa) / inv
    except (TypeError, ValueError):
        return None


def brier(p_home, outcome_home_win):
    """Brier 2 issues : (p - y)^2."""
    return (p_home - (1.0 if outcome_home_win else 0.0)) ** 2


def ece_binned(pairs, bins=10):
    """Vrai ECE bine : |confiance - precision| moyen, pondere par bin."""
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


def run(cutoff_raw=None, csv_dir=None):
    rows, holes = market_basket.load_dir(csv_dir)
    cutoff = parse_cutoff(cutoff_raw)
    train, test = split_cutoff(rows, cutoff)
    obs_train = fit_basket.prepare(train)
    blob = fit_basket.fit(obs_train)
    fit_basket.save_params(blob)
    if not test:
        holes.append("test_vide")
    n = 0
    brier_model = 0.0
    brier_market = 0.0
    ll_model = 0.0
    ll_market = 0.0
    pairs_ece = []
    for r in test:
        pred = engine_basket.predict(r, blob=blob)
        if pred.get("mu_home") is None:
            holes.append(r.get("game_id") or "" + ":params")
            continue
        sigma = float(pred.get("sigma") or 0.0)
        if sigma <= 0:
            holes.append("sigma_absente")
            continue
        p_home = model_basket.p_home_win(float(pred["mu_home"]),
                                         float(pred["mu_away"]), sigma)
        y = 1.0 if (r.get("pts_home") or 0) > (r.get("pts_away") or 0) else 0.0
        n += 1
        brier_model += brier(p_home, y == 1.0)
        ll_model -= math.log(max(p_home if y == 1.0 else 1.0 - p_home, 1e-12))
        pairs_ece.append((p_home, y))
        mk = implied_2way(r.get("odds_home"), r.get("odds_away"))
        if mk is None:
            holes.append((r.get("game_id") or "") + ":marche_absent")
        else:
            brier_market += brier(mk[0], y == 1.0)
            ll_market -= math.log(max(mk[0] if y == 1.0 else 1.0 - mk[0], 1e-12))
    brier_model = round(brier_model / n, 6) if n else None
    brier_market = round(brier_market / n, 6) if n and brier_market else None
    brier_gap = (round(brier_model - brier_market, 6)
                 if brier_model is not None and brier_market is not None else None)
    ece = round(ece_binned(pairs_ece), 6) if n else None
    ll_gap = (round((ll_model - ll_market) / n, 6) if n and brier_market else None)
    gates = moteur_flag.gates(moteur_sport_cfg()) or {}
    verdict_block = backtest_market.apply_gates(n, brier_gap, ece, ll_gap, gates=gates)
    out = {
        "contract": "pari.calibration_basket.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_oos": n,
        "brier_modele": brier_model,
        "brier_marche": brier_market,
        "brier_gap": brier_gap,
        "ece": ece,
        "logloss_modele": round(ll_model / n, 6) if n else None,
        "logloss_marche": round(ll_market / n, 6) if n and brier_market else None,
        "logloss_gap": ll_gap,
        "verdict": verdict_block.get("verdict"),
        "reasons": verdict_block.get("reasons") or [],
        "holes": list(dict.fromkeys(holes + list(verdict_block.get("holes") or []))),
    }
    os.makedirs(os.path.dirname(DEFAULT_OUT), exist_ok=True)
    with open(DEFAULT_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def moteur_sport_cfg():
    import moteur_sport
    return moteur_sport.cfg_path("basket")


def main():
    cutoff = sys.argv[1] if len(sys.argv) > 1 else None
    out = run(cutoff)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
