"""
CONNECTEUR football-data.org (clé FOOTBALL_DATA_ORG_KEY, plan gratuit) — calendrier
====================================================================================
https://api.football-data.org/v4 — 12 compétitions, 10 calls/min, €0.
Donne les fixtures (paires + horaires + goal events si dispo / plan).

Usage (via capteurs.py):
  python capteurs.py fixtures-list --source football-data-org --competition PL \\
         --date-from 2026-10-24 --date-to 2026-10-27

Codes compétition : PL, PD (La Liga), SA, BL1, FL1.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.football-data.org/v4"


def _key():
    key = os.environ.get("FOOTBALL_DATA_ORG_KEY")
    if not key:
        raise SystemExit("[FOOTBALL-DATA.ORG] Clé absente — ajoute FOOTBALL_DATA_ORG_KEY "
                         "(Settings → Keys, puis GitHub Secrets). Plan gratuit : 12 compétitions.")
    return key


def fixtures(date_from: str, date_to: str, competition: str = "PL", timeout: int = 60) -> dict:
    url = f"{BASE}/matches?dateFrom={date_from}&dateTo={date_to}&competitions={competition}"
    req = urllib.request.Request(
        url,
        headers={"X-Auth-Token": _key(), "User-Agent": "PERTURABO-PARI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    out = []
    for m in data.get("matches", []) or []:
        out.append({
            "id": f"FDO{m.get('id')}",
            "dom": (m.get("homeTeam") or {}).get("name"),
            "ext": (m.get("awayTeam") or {}).get("name"),
            "date": m.get("utcDate"),
            "ligue": (m.get("competition") or {}).get("name"),
            "round": (m.get("matchday") and f"J{m['matchday']}") or (m.get("stage") or ""),
        })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "football-data.org",
        "competition": competition,
        "date_from": date_from,
        "date_to": date_to,
        "fixtures": out,
    }
