#!/usr/bin/env python3
"""
MODEL BASKET — modeles de score + Monte-Carlo (stdlib, offline).
=============================================================
Score d'une equipe ~ N(mu, sigma), mu et sigma estimes par fit_basket.py.
Ce fichier ne lit aucun fichier : fonctions pures, meme discipline que
model_dc.py. Aucune probabilite produite hors d'une matrice simulee.
"""
from __future__ import annotations
import math
import random

SQRT2 = math.sqrt(2.0)


def norm_cdf(x, mu=0.0, sigma=1.0):
    """CDF normale. sigma <= 0 interdit (protection explicite)."""
    if sigma <= 0:
        raise ValueError("sigma doit etre > 0")
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * SQRT2)))


def expected_margin(rtg_h, rtg_a, home_adv):
    """Ecart de points attendu (domicile - exterieur)."""
    return (rtg_h - rtg_a) + home_adv


def expected_totals(pts_base, off_h, off_a, def_h, def_a):
    """Totaux de points attendus (domicile, exterieur).
    off/def sont des ecarts a la moyenne de la ligue (pts_base)."""
    mu_h = pts_base + off_h + def_a
    mu_a = pts_base + off_a + def_h
    return mu_h, mu_a


def p_home_win(mu_h, mu_a, sigma):
    """P(domicile gagne) — pas de nul au basket (prolongation)."""
    return 1.0 - norm_cdf(0.0, mu=mu_h - mu_a, sigma=sigma)


def p_total_over(mu_h, mu_a, sigma_total, line):
    """P(total points > line)."""
    return 1.0 - norm_cdf(line, mu=mu_h + mu_a, sigma=sigma_total)


def p_spread_home(mu_h, mu_a, sigma, line):
    """P(marge domicile > line). line<0 = domicile favori de |line| points."""
    return 1.0 - norm_cdf(line, mu=mu_h - mu_a, sigma=sigma)


def simulate_matrix(mu_h, mu_a, sigma, sims=10000, seed=None):
    """Matrice de scores simulee -> probas par ecart de 1 pt.
    Renvoie ({ecart: p}, simulations). Graine fixable pour tests."""
    if sims <= 0 or sigma <= 0:
        raise ValueError("sims et sigma doivent etre > 0")
    rng = random.Random(seed)
    counts = {}
    for _ in range(sims):
        sh = int(round(rng.gauss(mu_h, sigma)))
        sa = int(round(rng.gauss(mu_a, sigma)))
        counts[(sh, sa)] = counts.get((sh, sa), 0) + 1
    matrix = {k: v / float(sims) for k, v in counts.items()}
    return matrix, sims


def matrix_stats(matrix, sims, spread_line=-1.5, total_line=220.5):
    """Probas agregees depuis la matrice. Cles alignees sur la convention
    breacher.py du foot : "1" domicile, "2" exterieur (pas de "X" au basket).
    Renvoie aussi _n = simulations, pour la tracabilite."""
    p1 = p2 = o = 0.0
    for (sh, sa), p in matrix.items():
        if sh > sa:
            p1 += p
        elif sa > sh:
            p2 += p
        if sh + sa > total_line:
            o += p
    return {
        "1": round(p1, 4),
        "2": round(p2, 4),
        "total_over": round(o, 4),
        "total_under": round(1.0 - o, 4),
        "spread_home": round(p_spread_home_eps(matrix, spread_line), 4),
        "_n": sims,
    }


def p_spread_home_eps(matrix, line):
    """P(marge > line) depuis la matrice discrete (marge = sh - sa)."""
    tot = 0.0
    for (sh, sa), p in matrix.items():
        if sh - sa > line:
            tot += p
    return tot


def probas_from(mu_h, mu_a, sigma, cfg=None, seed=None):
    """Point d'entree unique : mu/sigma -> dict de probas + tracabilite."""
    cfg = cfg or {}
    sims = int(cfg.get("mc_sims") or 10000)
    spread = float(cfg.get("spread_line") or -1.5)
    matrix, sims = simulate_matrix(mu_h, mu_a, sigma, sims=sims, seed=seed)
    return matrix_stats(matrix, sims, spread_line=spread)


def time_weight(age_days, half_life=45.0):
    """Poids temporel exponentiel — meme convention que model_dc.py (foot)."""
    if half_life <= 0:
        return 1.0
    return 0.5 ** (float(age_days) / float(half_life))
