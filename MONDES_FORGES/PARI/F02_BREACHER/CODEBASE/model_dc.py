#!/usr/bin/env python3
"""
MODEL DC — Dixon-Coles MLE (stdlib, offline). Pack V2a.
========================================================
Probabilites de score, lambdas, log-vraisemblance, priors, poids temporel.
Jamais un producteur de ticket. Equipe absente / params default = holes, pas d'invention.

Usage:
  import model_dc
  model_dc.log_pmf(0, 0, 1.2, 1.1, -0.13)
"""

from __future__ import annotations

import math

RHO_DC = -0.13
MAX_GOALS = 10
LH_MIN = 1e-6
LH_MAX = 12.0
RHO_LO = -0.30
RHO_HI = 0.05
ELO_CENTER = 1500.0


def poisson_pmf(k, lam):
    if k < 0 or lam < 0:
        return 0.0
    if lam == 0.0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def tau_dc(lh, la, rho, i, j):
    if i == 0 and j == 0:
        return 1.0 - lh * la * rho
    if i == 0 and j == 1:
        return 1.0 + lh * rho
    if i == 1 and j == 0:
        return 1.0 + la * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def clip_lambda(lam):
    if lam is None:
        return None
    if lam < LH_MIN:
        return LH_MIN
    if lam > LH_MAX:
        return LH_MAX
    return lam


def clip_rho(rho):
    if rho is None:
        return None
    if rho < RHO_LO:
        return RHO_LO
    if rho > RHO_HI:
        return RHO_HI
    return rho


def lambdas(mu, home_adv, att_h, def_h, att_a, def_a):
    """lh, la depuis les parametres log-lineaires. None in -> None out."""
    if None in (mu, home_adv, att_h, def_h, att_a, def_a):
        return None, None
    lh = clip_lambda(math.exp(mu + home_adv + att_h - def_a))
    la = clip_lambda(math.exp(mu + att_a - def_h))
    return lh, la


def score_matrix(lh, la, rho=RHO_DC, max_goals=MAX_GOALS):
    if lh is None or la is None:
        return None
    rho = RHO_DC if rho is None else rho
    ph = [poisson_pmf(i, lh) for i in range(max_goals + 1)]
    pa = [poisson_pmf(j, la) for j in range(max_goals + 1)]
    m = [[ph[i] * pa[j] * tau_dc(lh, la, rho, i, j) for j in range(max_goals + 1)]
         for i in range(max_goals + 1)]
    total = sum(sum(row) for row in m)
    if total <= 0:
        return None
    return [[x / total for x in row] for row in m]


def log_pmf(i, j, lh, la, rho=RHO_DC):
    """log P(i, j). Score 0 autorise. lh/la/tau invalides = -inf."""
    if lh is None or la is None or i is None or j is None:
        return float("-inf")
    if i < 0 or j < 0:
        return float("-inf")
    lh, la = clip_lambda(lh), clip_lambda(la)
    rho = RHO_DC if rho is None else rho
    tau = tau_dc(lh, la, rho, i, j)
    if tau <= 0 or lh <= 0 or la <= 0:
        return float("-inf")
    return (math.log(tau) - lh + i * math.log(lh) - math.lgamma(i + 1)
            - la + j * math.log(la) - math.lgamma(j + 1))


def dlogp_dlh_dla_drho(i, j, lh, la, rho):
    """Derivees de log P par rapport a lh, la, rho."""
    if lh is None or la is None or i is None or j is None:
        return 0.0, 0.0, 0.0
    lh, la = clip_lambda(lh), clip_lambda(la)
    tau = tau_dc(lh, la, rho, i, j)
    if tau <= 0 or lh <= 0 or la <= 0:
        return 0.0, 0.0, 0.0
    dtau_h = dtau_a = dtau_r = 0.0
    if i == 0 and j == 0:
        dtau_h, dtau_a, dtau_r = -la * rho, -lh * rho, -lh * la
    elif i == 0 and j == 1:
        dtau_h, dtau_a, dtau_r = rho, 0.0, lh
    elif i == 1 and j == 0:
        dtau_h, dtau_a, dtau_r = 0.0, rho, la
    elif i == 1 and j == 1:
        dtau_h, dtau_a, dtau_r = 0.0, 0.0, -1.0
    inv = 1.0 / tau
    glh = inv * dtau_h - 1.0 + i / lh
    gla = inv * dtau_a - 1.0 + j / la
    gr = inv * dtau_r
    return glh, gla, gr


def time_weight(age_days, half_life=60.0):
    if half_life is None or half_life <= 0:
        return 1.0
    if age_days is None:
        return None
    if age_days < 0:
        return 0.0
    if age_days == 0:
        return 1.0
    return 0.5 ** (float(age_days) / float(half_life))


def elo_prior_mean(elo, n_matches, cfg):
    """Moyenne a priori att. elo absent = None (trou, jamais 1500 invente)."""
    if elo is None:
        return None
    scale = float(cfg.get("elo_scale") or 0.0015)
    weight = float(cfg.get("elo_prior_weight") or 0.5)
    full = float(cfg.get("elo_prior_full_matches") or 10)
    if full <= 0:
        full = 10.0
    n = 0.0 if n_matches is None else float(n_matches)
    frac = min(n, full) / full
    return weight * frac * scale * (float(elo) - ELO_CENTER)


def log_prior_gauss(value, mean, sigma):
    if value is None or sigma is None or sigma <= 0:
        return 0.0
    m = 0.0 if mean is None else mean
    z = (value - m) / sigma
    return -0.5 * z * z


def lambdas_for(home, away, rec):
    """lh, la pour un match. Equipe absente / non fite = None + holes."""
    holes = []
    if not rec or rec.get("params") != "fitted":
        holes.extend(list(rec.get("holes") or ["non_fite"]))
        return {"lh": None, "la": None, "holes": holes or ["non_fite"]}
    teams = rec.get("teams") or {}
    if home not in teams:
        holes.append("equipe_absente")
    if away not in teams:
        holes.append("equipe_absente")
    if holes:
        return {"lh": None, "la": None, "holes": holes}
    th, ta = teams[home], teams[away]
    att_h, def_h = th.get("att"), th.get("def")
    att_a, def_a = ta.get("att"), ta.get("def")
    lh, la = lambdas(rec.get("mu"), rec.get("home_adv"), att_h, def_h, att_a, def_a)
    if lh is None or la is None:
        return {"lh": None, "la": None, "holes": ["lambda"]}
    return {"lh": lh, "la": la, "rho": rec.get("rho"), "holes": []}
