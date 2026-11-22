#!/usr/bin/env python3
"""
WINNER INGEST — consommation du slate Winner (offline).
=======================================================
Chaine : capture LLM (PARI) ou capteur VANUS -> vanus_fetch --kind slate
-> ARCHIVUM/winner/slate_{sport}.json -> CE module -> latest_{sport}.json
-> input_capture / marches.py (existants).

Contrat valide ou fichier vide + trou : jamais de lecture partielle.
Marches diagnostic_only (HSH foot) conserves et marques : l'ingest ne
decide rien. Aucune cote estimee, aucune probabilite produite. Les cotes
Winner restent retail margees : le devig F03 s'applique comme partout.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
ENV_PATH = "PARI_WINNER_SLATE_PATH"
DEFAULT_DIR = os.path.join(WORLD, "ARCHIVUM", "winner")
CONTRACT = "vanus.slate.v1"


def _path(sport, explicit=None):
    if explicit:
        return explicit
    env = os.environ.get(ENV_PATH)
    if env:
        return env
    return os.path.join(DEFAULT_DIR, "slate_%s.json" % sport)


def load(sport="basket", path=None):
    """Slate brut ou blob vide + trous. Contrat inattendu = jete."""
    target = _path(sport, path)
    try:
        with open(target, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"contract": CONTRACT, "matches": [], "holes": ["slate_absent"]}
    if not isinstance(blob, dict) or blob.get("contract") != CONTRACT:
        return {"contract": CONTRACT, "matches": [], "holes": ["contrat_inattendu"]}
    if blob.get("sport") not in ("foot", "basket"):
        return {"contract": CONTRACT, "matches": [], "holes": ["sport_inconnu"]}
    if blob.get("sport") != sport:
        return {"contract": CONTRACT, "matches": [],
                "holes": ["sport_differents:" + str(blob.get("sport"))]}
    blob.setdefault("matches", [])
    blob.setdefault("holes", [])
    return blob


def ingest(sport="basket", path=None):
    """Slate -> vue indexee par match_key. Aucune probabilite, aucune decision."""
    blob = load(sport, path)
    out = {"contract": CONTRACT, "sport": sport, "generated_at": blob.get("generated_at"),
           "matches": {}, "holes": list(blob.get("holes") or [])}
    for m in blob.get("matches") or []:
        key = m.get("match_key")
        if not key:
            out["holes"].append("match_key_absent")
            continue
        out["matches"][key] = {
            "home": m.get("home"), "away": m.get("away"),
            "kickoff": m.get("kickoff"),
            "source_event_id": m.get("source_event_id"),
            "odds": dict(m.get("odds") or {}),
            "diagnostic_only": list(m.get("diagnostic_only") or []),
            "holes": list(m.get("holes") or []),
        }
    return out


def save(view, sport="basket", path=None):
    target = _path(sport, path).replace("slate_", "latest_")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(view, f, ensure_ascii=False, indent=2)
    return target


def main():
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("foot", "basket") else "basket"
    view = ingest(sport)
    target = save(view, sport)
    print(f"[WINNER-INGEST] {sport}: {len(view['matches'])} match(s), "
          f"{len(view['holes'])} trou(s) -> {target}")


if __name__ == "__main__":
    main()
