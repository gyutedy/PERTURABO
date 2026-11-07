#!/usr/bin/env python3
"""
TICKET FRICTION — fees + slippage dans le seuil (S16)
=====================================================
Releve EV_FLOOR. Jamais le baisser sous 0.03.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONFIG_PATH = os.path.join(WORLD, "config", "ticket_friction.json")
EV_FLOOR = 0.03
DEFAULT_FEES = 0.005
DEFAULT_SLIPPAGE = 0.005


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_friction(path=None):
    p = path or CONFIG_PATH
    blob = {}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                blob = raw
        except (OSError, json.JSONDecodeError):
            blob = {}
    fees = _f(blob.get("fees"))
    slip = _f(blob.get("slippage"))
    holes = []
    if fees is None:
        fees = DEFAULT_FEES
        holes.append("fees")
    if slip is None:
        slip = DEFAULT_SLIPPAGE
        holes.append("slippage")
    if fees < 0:
        fees = 0.0
        holes.append("fees_neg")
    if slip < 0:
        slip = 0.0
        holes.append("slippage_neg")
    return {
        "fees": fees,
        "slippage": slip,
        "holes": holes,
        "path": p,
    }


def effective_floor(base=None, friction=None):
    base = EV_FLOOR if base is None else float(base)
    if base < EV_FLOOR:
        base = EV_FLOOR
    fr = friction or load_friction()
    ev = base + float(fr["fees"]) + float(fr["slippage"])
    if ev < EV_FLOOR:
        ev = EV_FLOOR
    return ev, fr
