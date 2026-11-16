#!/usr/bin/env python3
"""
MOTEUR SPORT — selecteur du sport actif. Foot = maitre par defaut.
==============================================================
Etat persiste dans ARCHIVUM/state/sport_actif.json. Fichier absent,
casse ou valeur inconnue = "foot" (fail-safe, jamais basket par surprise).
Le gel reste la competence de moteur_flag : ce module ne fait que choisir
LEQUEL fichier de config moteur_flag doit lire.
Interdit : produire un p, toucher au ledger, changer un gate.
"""
from __future__ import annotations
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
STATE_PATH = os.path.join(WORLD, "ARCHIVUM", "state", "sport_actif.json")
SPORTS = ("foot", "basket")


def _cfg_path(sport):
    if sport == "basket":
        return os.path.join(WORLD, "config", "moteur_basket.json")
    return os.path.join(WORLD, "config", "moteur.json")


def actif(path=None):
    """Sport actif. Fail-safe = foot (jamais basket par defaut)."""
    target = path or STATE_PATH
    try:
        with open(target, encoding="utf-8") as f:
            blob = json.load(f)
        sport = str(blob.get("sport", "foot")).strip().lower()
        return sport if sport in SPORTS else "foot"
    except Exception:
        return "foot"


def set_sport(sport, path=None):
    """Ecrit le sport actif. Refuse tout ce qui n'est pas foot|basket."""
    sport = str(sport or "").strip().lower()
    if sport not in SPORTS:
        raise ValueError("sport inconnu: %r (choix: %s)" % (sport, ", ".join(SPORTS)))
    target = path or STATE_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump({"sport": sport}, f, ensure_ascii=False, indent=2)
    return sport


def cfg_path(sport=None):
    """Fichier de config du moteur du sport (actif par defaut)."""
    return _cfg_path(sport or actif())


def both_states():
    """Etat (gel inclus) des deux moteurs, pour affichage /modele."""
    import moteur_flag
    out = {}
    for sport in SPORTS:
        blob = moteur_flag.load(_cfg_path(sport)) or {}
        out[sport] = {
            "engine": blob.get("engine"),
            "tickets_enabled": bool(blob.get("tickets_enabled")),
            "actif": sport == actif(),
        }
    return out


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in SPORTS:
        set_sport(sys.argv[1])
        print("sport actif =", actif())
    else:
        print("sport actif =", actif(), "(choix:", ", ".join(SPORTS) + ")")


if __name__ == "__main__":
    main()
