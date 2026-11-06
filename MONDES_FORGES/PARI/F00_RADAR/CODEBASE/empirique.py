"""
F00 EMPIRIQUE — taux O2.5 saison vs P_modele (stdlib, offline).
================================================================
|P_modele - empirique| >= 0.20 → flag `incoherence_modele_empirique`.
Saison absente → hole, jamais de taux invente. Zero reseau.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F02 = os.path.join(WORLD, "F02_BREACHER", "CODEBASE")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if F02 not in sys.path:
    sys.path.insert(0, F02)

import backtest  # noqa: E402
import baseline  # noqa: E402

_CFG = None
FLAG = "incoherence_modele_empirique"


def load_config(path=None):
    global _CFG
    if path is None and _CFG is not None:
        return _CFG
    p = path or os.path.join(WORLD, "config", "empirique.json")
    cfg = {"o25_gap": 0.20, "ev_min": 0.03, "kelly_frac": 0.25, "ece_bins": 10}
    if p and os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
            if isinstance(blob, dict):
                for k in ("o25_gap", "ev_min", "kelly_frac", "ece_bins"):
                    if k in blob:
                        cfg[k] = blob[k]
        except (OSError, json.JSONDecodeError):
            pass
    if path is None:
        _CFG = cfg
    return cfg


def o25_rate(rows):
    n, hits = 0, 0
    for r in rows:
        h, a = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if h is None or a is None:
            continue
        n += 1
        if (h + a) >= 3:
            hits += 1
    if n == 0:
        return None, 0
    return hits / n, n


def league_o25(code, csv_dir=None):
    if not code:
        return None, 0, None
    rows, source = baseline.load_season_rows(code, csv_dir=csv_dir)
    if not rows:
        return None, 0, None
    rate, n = o25_rate(rows)
    return rate, n, source


def gap_flag(p_modele, empirique, gap=None):
    if p_modele is None or empirique is None:
        return False, None
    try:
        p = float(p_modele)
        e = float(empirique)
    except (TypeError, ValueError):
        return False, None
    thr = float(gap if gap is not None else load_config()["o25_gap"])
    diff = abs(p - e)
    return diff >= thr, diff


def stamp(analyse, csv_dir=None, gap=None):
    code = None
    moy = analyse.get("ligue_moyennes") or {}
    if isinstance(moy, dict):
        code = moy.get("league_code")
    code = code or analyse.get("league_code")
    rate, n, source = league_o25(code, csv_dir=csv_dir)
    holes = list(analyse.get("empirique_holes") or [])
    analyse["o2.5_empirique"] = rate
    analyse["o2.5_empirique_n"] = n
    if rate is None:
        if "o2.5_empirique" not in holes:
            holes.append("o2.5_empirique")
        analyse["empirique_holes"] = holes
        return analyse
    analyse["empirique_source"] = source
    flagged = 0
    for a in analyse.get("analyses") or []:
        p = (a.get("probas") or {}).get("o2.5")
        hit, diff = gap_flag(p, rate, gap=gap)
        a["o2.5_empirique"] = rate
        a["o2.5_ecart"] = diff
        dq = a.setdefault("data_quality", {})
        flags = list(dq.get("flags") or [])
        if hit and FLAG not in flags:
            flags.append(FLAG)
            flagged += 1
        dq["flags"] = flags
        a["data_quality"] = dq
    analyse["empirique_flags"] = flagged
    analyse["empirique_holes"] = holes
    return analyse
