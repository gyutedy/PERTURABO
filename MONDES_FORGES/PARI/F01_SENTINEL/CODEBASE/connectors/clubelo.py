"""
CONNECTEUR ClubElo (AUCUNE CLE) — ratings Elo de tous les clubs
================================================================
https://api.clubelo.com/<AAAA-MM-JJ> renvoie un CSV (Club, ..., Elo).
Timeout / CSV vide = trou declare, jamais d'invention.

Usage (via capteurs.py): python capteurs.py build-elo --date 2026-10-25 --out ARCHIVUM/teams/elo.json
"""

import csv
import io
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

TIMEOUT = int(os.environ.get("PARI_F00_TIMEOUT", "8"))


def _norm(name: str) -> str:
    return "".join(c for c in (name or "").lower() if c.isalnum())


def _fetch_csv(date: str = None, timeout: int = None):
    """GET CSV ClubElo. Timeout / reseau = None (trou), jamais d'invention."""
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timeout = TIMEOUT if timeout is None else timeout
    url = f"https://api.clubelo.com/{date}"
    req = urllib.request.Request(url, headers={"User-Agent": "PERTURABO-PARI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def _parse_csv(text):
    if not text or not str(text).strip():
        return {}
    rows = csv.DictReader(io.StringIO(text))
    out = {}
    for row in rows:
        club = (row.get("Club") or "").strip()
        elo = (row.get("Elo") or "").strip()
        if club and elo:
            try:
                out[club] = float(elo)
            except ValueError:
                pass
    return out


def _hole(date):
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "api.clubelo.com",
        "date": date,
        "nb_clubs": 0,
        "holes": ["elo"],
    }
    return {"meta": meta, "elos": {}, "holes": ["elo"]}


def elo_map(date: str = None, timeout: int = None):
    """Carte Elo du jour. Timeout / vide = blob trou (elos vides), jamais None silencieux cote caller."""
    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        text = _fetch_csv(date, timeout=timeout)
    except Exception:
        return _hole(date)
    if text is None:
        return _hole(date)
    elos = _parse_csv(text)
    if not elos:
        return _hole(date)
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "api.clubelo.com",
        "date": date,
        "nb_clubs": len(elos),
    }
    return {"meta": meta, "elos": elos}


def best_match(team: str, elos: dict, min_len: int = 4):
    """Correspondance approximative : normalisation exacte, sinon sous-chaine."""
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
