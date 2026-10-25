"""
CONNECTEUR ClubElo (AUCUNE CLÉ) — ratings Elo de tous les clubs
================================================================
https://api.clubelo.com/<AAAA-MM-JJ> renvoie un CSV (Club, ..., Elo).
Sert de feature de force relative dans la carte de matchs.

Usage (via capteurs.py): python capteurs.py build-elo --date 2026-10-25 --out ARCHIVUM/teams/elo.json
"""

import csv
import io
import os
import urllib.request
from datetime import datetime, timezone


def _norm(name: str) -> str:
    return "".join(c for c in (name or "").lower() if c.isalnum())


def elo_map(date: str = None, timeout: int = 60) -> dict:
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://api.clubelo.com/{date}"
    req = urllib.request.Request(url, headers={"User-Agent": "PERTURABO-PARI/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        rows = csv.DictReader(io.StringIO(r.read().decode("utf-8", errors="replace")))
    out = {}
    for row in rows:
        club = (row.get("Club") or "").strip()
        elo = (row.get("Elo") or "").strip()
        if club and elo:
            try:
                out[club] = float(elo)
            except ValueError:
                pass
    meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "api.clubelo.com", "date": date, "nb_clubs": len(out)}
    return {"meta": meta, "elos": out}


def best_match(team: str, elos: dict, min_len: int = 4):
    """Correspondance approximative : normalisation exacte, sinon sous-chaîne."""
    q = _norm(team)
    if not q:
        return None
    for club, elo in elos.items():
        if _norm(club) == q:
            return club, elo
    candidates = [(club, elo) for club, elo in elos.items()
                  if min(len(q), len(_norm(club))) >= min_len and
                  (q in _norm(club) or _norm(club) in q)]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        candidates.sort(key=lambda ce: abs(len(_norm(ce[0])) - len(q)))
        return candidates[0]
    return None
