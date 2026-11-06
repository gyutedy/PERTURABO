#!/usr/bin/env python3
"""
DEVIG — multiplicatif defaut + additif 2e passe (S8 / v3.9)
===========================================================
Diagnostic seulement. Jamais un producteur de p.
Issue manquante → holes, pas de devig cote unique.
Invariant multiplicatif : S>1 => fair_odds_i > cote_i.
Additif = sensibilite, jamais le p_fair / EV / verdict.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONFIG_PATH = os.path.join(WORLD, "config", "devig.json")

DEFAULT_BONUS_PT = 0.01
DEFAULT_METHOD = "multiplicative"


def load_bonus(path=None):
    p = path or CONFIG_PATH
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
            val = blob.get("double_confirmation_bonus_pt")
            if val is not None:
                return float(val)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return DEFAULT_BONUS_PT


def _present_cotes(cotes):
    present = {}
    holes = []
    for k, v in (cotes or {}).items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            holes.append("cote:" + str(k))
            continue
        if f <= 1:
            holes.append("cote_invalide:" + str(k))
            continue
        present[str(k)] = f
    return present, holes


def multiplicative(cotes):
    """Devig multiplicatif. <2 issues → holes, pas de fair. Cote unique refusee."""
    present, holes = _present_cotes(cotes)
    if len(present) == 1:
        only = next(iter(present))
        return {
            "ok": False,
            "method": "multiplicative",
            "S": None,
            "p_fair": {},
            "fair_odds": {},
            "holes": holes + ["issue_manquante", "cote_unique:" + only],
        }
    if len(present) < 2:
        return {
            "ok": False,
            "method": "multiplicative",
            "S": None,
            "p_fair": {},
            "fair_odds": {},
            "holes": holes + ["issue_manquante"],
        }
    impl = {k: 1.0 / v for k, v in present.items()}
    s = sum(impl.values())
    p_fair = {k: impl[k] / s for k in present}
    fair_odds = {k: 1.0 / p_fair[k] for k in present}
    if s > 1:
        for k in present:
            if not (fair_odds[k] > present[k]):
                holes.append("invariant:" + k)
    return {
        "ok": True,
        "method": "multiplicative",
        "S": s,
        "p_fair": p_fair,
        "fair_odds": fair_odds,
        "cotes": present,
        "holes": holes,
    }


def additive(cotes):
    """Devig additif. 2e passe diagnostic. <2 issues → holes. p<=0 → hole, jamais clip."""
    present, holes = _present_cotes(cotes)
    if len(present) == 1:
        only = next(iter(present))
        return {
            "ok": False,
            "method": "additive",
            "S": None,
            "p_fair": {},
            "fair_odds": {},
            "holes": holes + ["issue_manquante", "cote_unique:" + only],
        }
    if len(present) < 2:
        return {
            "ok": False,
            "method": "additive",
            "S": None,
            "p_fair": {},
            "fair_odds": {},
            "holes": holes + ["issue_manquante"],
        }
    impl = {k: 1.0 / v for k, v in present.items()}
    s = sum(impl.values())
    n = len(present)
    over = (s - 1.0) / n
    p_fair = {k: impl[k] - over for k in present}
    if any(p_fair[k] <= 0 for k in present):
        return {
            "ok": False,
            "method": "additive",
            "S": s,
            "p_fair": {},
            "fair_odds": {},
            "cotes": present,
            "holes": holes + ["p_additif_non_positif"],
        }
    fair_odds = {k: 1.0 / p_fair[k] for k in present}
    return {
        "ok": True,
        "method": "additive",
        "S": s,
        "p_fair": p_fair,
        "fair_odds": fair_odds,
        "cotes": present,
        "holes": holes,
    }


def gap(multi_rec, add_rec):
    """Ecart p_fair multiplicatif - additif. Diagnostic, jamais un p."""
    holes = []
    gap_p = {}
    if not (multi_rec or {}).get("ok"):
        holes.extend((multi_rec or {}).get("holes") or ["multi_fail"])
    if not (add_rec or {}).get("ok"):
        holes.extend((add_rec or {}).get("holes") or ["add_fail"])
        return {"ok": False, "gap_p": {}, "holes": holes}
    pm = (multi_rec or {}).get("p_fair") or {}
    pa = (add_rec or {}).get("p_fair") or {}
    keys = [k for k in pm if k in pa]
    if not keys:
        return {"ok": False, "gap_p": {}, "holes": holes + ["gap_vide"]}
    for k in keys:
        gap_p[k] = pm[k] - pa[k]
    return {"ok": True, "gap_p": gap_p, "holes": holes}


def edge_net_devig(p_modele, cote, p_fair):
    """Diagnostic P_modele / P_fair - 1. EV brute inchangee ailleurs. cote ignoree."""
    if p_modele is None or p_fair is None:
        return None
    try:
        pm, pf = float(p_modele), float(p_fair)
    except (TypeError, ValueError):
        return None
    if pf <= 0:
        return None
    return pm / pf - 1.0


def double_confirmation(p_modele, cote, p_fair, bonus_pt=None):
    """P_modele > P_fair ET P_modele * cote > 1. Bonus seuil config (init 1 pt)."""
    holes = []
    if p_modele is None or cote is None:
        return {"ok": False, "flag": False, "holes": ["p_ou_cote"]}
    if p_fair is None:
        holes.append("p_fair")
        return {"ok": False, "flag": False, "holes": holes}
    try:
        pm, c, pf = float(p_modele), float(cote), float(p_fair)
    except (TypeError, ValueError):
        return {"ok": False, "flag": False, "holes": ["cast"]}
    bonus = DEFAULT_BONUS_PT if bonus_pt is None else float(bonus_pt)
    ev = pm * c - 1
    cond_fair = pm > pf
    cond_ev = ev > 0
    cond_bonus = ev >= bonus
    return {
        "ok": True,
        "flag": bool(cond_fair and cond_ev),
        "p_modele_gt_p_fair": cond_fair,
        "ev_positif": cond_ev,
        "bonus_ok": cond_bonus,
        "bonus_pt": bonus,
        "holes": holes,
    }
