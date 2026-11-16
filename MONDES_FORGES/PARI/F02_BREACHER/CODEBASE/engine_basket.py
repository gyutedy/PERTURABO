#!/usr/bin/env python3
"""
ENGINE BASKET — lecture des params + prediction mu/sigma. Jamais un p.
=====================================================================
Meme contrat que engine_dc.py (foot) : renvoie des moyennes et des trous,
jamais une probabilite. Les probas vivent dans model_basket.probas_from.
Fail-safe : params absents = holes=["params_absents"], mu=None.
"""
from __future__ import annotations
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
ENV_PATH = "PARI_BASKET_PARAMS_PATH"
DEFAULT_PATH = os.path.join(WORLD, "ARCHIVUM", "state", "basket_params.json")


def _path(path=None):
    if path:
        return path
    env = os.environ.get(ENV_PATH)
    return env if env else DEFAULT_PATH


def load(path=None):
    import fit_basket
    return fit_basket.load_params(_path(path))


def predict(m, blob=None, path=None):
    """m = {home|dom, away|ext} -> {mu_home, mu_away, sigma, engine, holes}.
    Jamais d'estimation cachee : equipe inconnue = mu None + hole."""
    if blob is None:
        blob = load(path)
    if not blob:
        return {"mu_home": None, "mu_away": None, "sigma": None,
                "engine": "basket_mle", "holes": ["params_absents"]}
    home = ((m or {}).get("dom") or (m or {}).get("home") or "").strip()
    away = ((m or {}).get("ext") or (m or {}).get("away") or "").strip()
    teams = blob.get("teams") or {}
    holes = list(blob.get("holes") or [])
    th, ta = teams.get(home), teams.get(away)
    if not home or not away:
        holes.append("equipe_absente")
        th = ta = None
    if th is None or ta is None:
        holes.append("equipe_inconnue:" + (home if th is None else away))
        return {"mu_home": None, "mu_away": None, "sigma": blob.get("sigma"),
                "engine": "basket_mle", "holes": holes}
    base = float(blob.get("base") or 0.0)
    hca = float(blob.get("home_adv") or 0.0)
    mu_h = base + th["off"] - ta["off"] + hca / 2.0
    mu_a = base + ta["off"] - th["off"] - hca / 2.0
    return {
        "mu_home": round(mu_h, 3),
        "mu_away": round(mu_a, 3),
        "sigma": blob.get("sigma"),
        "margin_edge": round((th["rtg"] - ta["rtg"]) + hca, 3),
        "engine": "basket_mle",
        "holes": holes,
    }
