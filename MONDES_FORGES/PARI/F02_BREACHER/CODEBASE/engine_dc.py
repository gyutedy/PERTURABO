#!/usr/bin/env python3
"""
ENGINE DC — cablage Dixon-Coles MLE dans breacher (stdlib, offline). Pack V2b.
==============================================================================
Params fitted + deux equipes presentes -> lambdas MLE.
Sinon -> None (Poisson carte) + holes, jamais invente.
Ne touche pas tickets_enabled. Calibration = V2c.

Usage:
  import engine_dc
  ov = engine_dc.overlay(match, avg, lh, la, rho)
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fit_dc  # noqa: E402
import model_dc  # noqa: E402

DEFAULT_PATH = os.path.join(WORLD, "ARCHIVUM", "learnings", "dc_params.json")


def _path(path=None):
    if path:
        return path
    env = os.environ.get("PARI_DC_PARAMS_PATH")
    return env if env else DEFAULT_PATH


def load(path=None):
    """Blob dc_params.json ou None. Fichier absent / casse = None, jamais invente."""
    return fit_dc.load_params(_path(path))


_SUFFIX = ("afc", "fc", "cf", "sc", "city", "athletic", "united", "northend", "county")


def _norm(name):
    import re
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _resolve_team(name, rec):
    """Nom capture ('Middlesbrough FC') -> nom CSV ('Middlesbrough')."""
    teams = {_norm(t): t for t in ((rec or {}).get("teams") or {})}
    raw = _norm(name)
    if raw in teams:
        return teams[raw]
    cut = raw
    for suf in _SUFFIX:
        if cut.endswith(suf) and len(cut) - len(suf) >= 4:
            cut = cut[:-len(suf)]
            break
    if cut in teams:
        return teams[cut]
    pres = [k for k in teams if len(k) >= 4 and cut.startswith(k)]
    if len(pres) == 1:
        return teams[pres[0]]
    return None


def try_lambdas(m, avg=None, blob=None, path=None):
    """lh, la MLE ou None + holes. Ne lit jamais _PARAMS_CACHE orphelin."""
    if blob is None:
        blob = load(path)
    if not blob:
        return {"lh": None, "la": None, "holes": ["params_absents"]}
    home = ((m or {}).get("dom") or (m or {}).get("home") or "").strip()
    away = ((m or {}).get("ext") or (m or {}).get("away") or "").strip()
    code = ((m or {}).get("league_code")
            or (avg or {}).get("league_code")
            or "")
    code = str(code).upper() if code else None
    if not home or not away:
        return {"lh": None, "la": None, "holes": ["equipe_absente"]}
    if not code:
        return {"lh": None, "la": None, "holes": ["ligue_absente"]}
    rec = fit_dc.params_for(code, blob=blob)
    if rec.get("params") != "fitted":
        return {"lh": None, "la": None, "holes": rec.get("holes") or ["params_absents"]}
    home_r, away_r = _resolve_team(home, rec), _resolve_team(away, rec)
    if not home_r or not away_r:
        return {"lh": None, "la": None, "holes": ["equipe_absente"]}
    return model_dc.lambdas_for(home_r, away_r, rec)


def overlay(m, avg, lambda_dom, lambda_ext, rho, blob=None, path=None):
    """Remplace les lambdas si MLE dispo. Sinon inchange + holes."""
    got = try_lambdas(m, avg, blob=blob, path=path)
    holes = list((got or {}).get("holes") or [])
    if got and got.get("lh") is not None and got.get("la") is not None:
        return {
            "lambda_dom": got["lh"],
            "lambda_ext": got["la"],
            "rho": got["rho"] if got.get("rho") is not None else rho,
            "engine": "dc_mle",
            "holes": holes,
        }
    return {
        "lambda_dom": lambda_dom,
        "lambda_ext": lambda_ext,
        "rho": rho,
        "engine": "poisson",
        "holes": holes or ["params_absents"],
    }
