#!/usr/bin/env python3
"""
MARKET PRIORITY — paliers (S5 / v3.5)
=====================================
Palier suivant si >= min_tickets_mesures (defaut 30).
corners / cards fermes sans data → holes, jamais ouverts.
n = tickets settles G/P seulement. EN_ATTENTE = pas mesure. Absent = 0, pas invente.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONFIG_PATH = os.path.join(WORLD, "config", "market_priority.json")
LOTS_PATH = os.path.join(WORLD, "ARCHIVUM", "learnings", "lots.json")

DEFAULT_MIN_N = 30
DEFAULT_PALIERS = [
    {"id": 0, "marches": ["1X2", "OU_2.5", "BTTS", "MT_PROLIFIQUE"]},
    {"id": 1, "marches": ["OU_1.5", "OU_3.5", "DC",
                         "TT_H_0.5", "TT_H_1.5", "TT_H_2.5",
                         "TT_A_0.5", "TT_A_1.5", "TT_A_2.5"]},
    {"id": 2, "marches": ["OU_0.5", "OU_4.5", "CS"]},
]
DEFAULT_FERMES = ["corners", "cards"]


def load_config(path=None):
    p = path or CONFIG_PATH
    blob = {}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f) or {}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            blob = {}
    min_n = blob.get("min_tickets_mesures")
    try:
        min_n = int(min_n)
    except (TypeError, ValueError):
        min_n = DEFAULT_MIN_N
    if min_n < 1:
        min_n = DEFAULT_MIN_N
    paliers = blob.get("paliers") or DEFAULT_PALIERS
    out_p = []
    for i, pal in enumerate(paliers):
        if isinstance(pal, dict):
            pid = pal.get("id", i)
            marches = list(pal.get("marches") or [])
        else:
            pid = i
            marches = list(pal)
        out_p.append({"id": int(pid), "marches": [str(m) for m in marches]})
    fermes = blob.get("fermes_sans_data") or DEFAULT_FERMES
    fermes = [str(x).lower() for x in fermes]
    return {
        "min_tickets_mesures": min_n,
        "paliers": out_p,
        "fermes_sans_data": fermes,
        "holes": [] if blob else ["config_market_priority"],
    }


def n_tickets_mesures(world=None, lots_box=None, lots_path=None):
    """Tickets settles G ou P. EN_ATTENTE ignore. Fichier absent = 0, pas invente."""
    if lots_box is None:
        root = world or WORLD
        p = lots_path or os.path.join(root, "ARCHIVUM", "learnings", "lots.json")
        if not os.path.exists(p):
            return 0
        try:
            with open(p, encoding="utf-8") as f:
                lots_box = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            return 0
    n = 0
    for lot in lots_box.get("lots") or []:
        settle = (lot.get("settle") or {}).get("tickets") or []
        for t in settle:
            r = t.get("resultat")
            if r in ("G", "P"):
                n += 1
    return n


def palier_ouvert(palier_id, n, min_n=DEFAULT_MIN_N):
    """Palier 0 toujours. Palier k ouvert si n >= k * min_n."""
    try:
        pid = int(palier_id)
        nn = int(n)
        mn = int(min_n)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return True
    if mn < 1:
        mn = DEFAULT_MIN_N
    return nn >= pid * mn


def _norm(marche):
    return str(marche or "").strip()


def marche_status(marche, n=None, cfg=None, world=None, lots_box=None):
    """open / palier / holes. corners/cards = fermes, holes sans_data."""
    cfg = cfg or load_config()
    if n is None:
        n = n_tickets_mesures(world=world, lots_box=lots_box)
    key = _norm(marche)
    key_l = key.lower()
    fermes = cfg.get("fermes_sans_data") or DEFAULT_FERMES
    if key_l in fermes or key_l in ("corner", "carton", "cartons"):
        tag = "corners" if "corner" in key_l else "cards"
        if key_l in ("cards", "card", "carton", "cartons"):
            tag = "cards"
        if "corner" in key_l:
            tag = "corners"
        return {
            "marche": key,
            "open": False,
            "palier": None,
            "n_tickets_mesures": n,
            "holes": ["sans_data", tag],
        }
    min_n = cfg.get("min_tickets_mesures") or DEFAULT_MIN_N
    found = None
    for pal in cfg.get("paliers") or []:
        marches = pal.get("marches") or []
        if key in marches or key_l in [m.lower() for m in marches]:
            found = pal
            break
    if found is None:
        return {
            "marche": key,
            "open": False,
            "palier": None,
            "n_tickets_mesures": n,
            "holes": ["marche_inconnu"],
        }
    pid = found.get("id", 0)
    opened = palier_ouvert(pid, n, min_n)
    holes = [] if opened else ["palier_ferme"]
    return {
        "marche": key,
        "open": bool(opened),
        "palier": pid,
        "n_tickets_mesures": n,
        "holes": holes,
    }


def stamp_jambe(jambe, n=None, cfg=None, world=None, lots_box=None):
    """Ajoute holes priorite sur la jambe. Ne droppe pas."""
    st = marche_status(jambe.get("marche"), n=n, cfg=cfg, world=world, lots_box=lots_box)
    if not st.get("open"):
        jambe.setdefault("holes", [])
        for h in st.get("holes") or []:
            if h not in jambe["holes"]:
                jambe["holes"].append(h)
        jambe["priority_open"] = False
    else:
        jambe["priority_open"] = True
    jambe["priority_palier"] = st.get("palier")
    return jambe
