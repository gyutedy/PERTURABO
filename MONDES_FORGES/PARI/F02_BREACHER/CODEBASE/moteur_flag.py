#!/usr/bin/env python3
"""
MOTEUR FLAG — le seul lecteur de config/moteur.json.
====================================================
Phase 0 : aucun ticket tant que le moteur Dixon-Coles n'est pas valide.
Le ledger F06 n'est jamais touche. Fail-safe : fichier illisible = GELE.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
PATH = os.path.join(WORLD, "config", "moteur.json")

DEFAULTS = {
    "engine": "dc_mle",
    "engine_version": "pari.model_dc.v1",
    "tickets_enabled": False,
    "require_calibration": True,
    "gates": {},
    "fit": {},
}


def load(path=None):
    """Blob complet. Fichier absent ou casse = defauts (donc GELE)."""
    p = path or PATH
    blob = dict(DEFAULTS)
    try:
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return blob
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k == "note":
                continue
            blob[k] = v
    return blob


def tickets_enabled(path=None):
    """True seulement si le drapeau est explicitement true."""
    return load(path).get("tickets_enabled") is True


def engine(path=None):
    return str(load(path).get("engine") or "dc_mle")


def gates(path=None):
    blob = load(path).get("gates") or {}
    return blob if isinstance(blob, dict) else {}


def fit_config(path=None):
    blob = load(path).get("fit") or {}
    return blob if isinstance(blob, dict) else {}


def set_tickets(enabled, path=None):
    """Ecriture atomique du seul champ tickets_enabled. Le reste est preserve."""
    p = path or PATH
    blob = load(p)
    blob["tickets_enabled"] = bool(enabled)
    os.makedirs(os.path.dirname(os.path.abspath(p)) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, p)
    return blob
