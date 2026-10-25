"""
CONNECTEUR API-Football (clé API_FOOTBALL_KEY) — calendrier des matchs à venir
===============================================================================
https://v3.football.api-sports.io — 100 requêtes/jour gratuites.
Donne la LISTE des fixtures (paires + ids) d'une ligue à une date.

Usage (via capteurs.py):
  python capteurs.py fixtures-list --source api-football --league-id 39 --date 2026-10-25

League IDs usuels : 39 Premier League, 140 La Liga, 135 Serie A,
78 Bundesliga, 61 Ligue 1.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

BASE = "https://v3.football.api-sports.io"


def _season_for(date: str) -> int:
    y = int(date[:4])
    return y if int(date[5:7]) >= 7 else y - 1


def _key():
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        raise SystemExit("[API-FOOTBALL] Clé absente — ajoute API_FOOTBALL_KEY "
                         "(Settings → Keys, puis GitHub Secrets). 100 req/jour gratuites.")
    return key


def fixtures(date: str, league_id: int, timeout: int = 60) -> dict:
    season = _season_for(date)
    url = f"{BASE}/fixtures?date={date}&league={league_id}&season={season}"
    req = urllib.request.Request(
        url,
        headers={"x-apisports-key": _key(), "User-Agent": "PERTURABO-PARI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    out = []
    for fx in data.get("response", []):
        out.append({
            "id": f"AF{fx['fixture']['id']}",
            "dom": fx["teams"]["home"]["name"],
            "ext": fx["teams"]["away"]["name"],
            "date": fx["fixture"]["date"],
            "ligue": fx["league"]["name"],
            "round": fx["league"].get("round"),
        })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "api-football",
        "league_id": league_id,
        "date": date,
        "season": season,
        "fixtures": out,
    }
