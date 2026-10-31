"""
CONNECTEUR Sportradar StatsHub — voix 2 notes.
Clé optionnelle SPORTRADAR_API_KEY. Absente / timeout = [].
Indépendant d'Opta / SofaScore.
"""

import os
import sys

CAP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import cache
import http_util

BASE = os.environ.get("SPORTRADAR_BASE", "https://api.sportradar.com/soccer/trial/v4/en")


def _key():
    return os.environ.get("SPORTRADAR_API_KEY") or os.environ.get("SR_API_KEY")


def missing_players(team_name):
    payload, _ = cache.get_or_fetch("sportradar", team_name, lambda: _fetch(team_name))
    return payload or []


def _fetch(team_name):
    key = _key()
    if not key:
        return []
    q = (team_name or "").strip()
    if not q:
        return []
    from urllib.parse import quote
    data = http_util.get_json(
        f"{BASE}/competitors/sr:competitor:search.json?query={quote(q)}&api_key={key}"
    )
    if not data:
        return []
    comps = data.get("competitors") or data.get("results") or []
    cid = None
    for c in comps:
        comp = c.get("competitor") or c
        if comp.get("id"):
            cid = comp["id"]
            break
    if not cid:
        return []
    miss = http_util.get_json(f"{BASE}/competitors/{cid}/missing_players.json?api_key={key}")
    if not miss:
        return []
    out = []
    players = miss.get("missing_players") or miss.get("players") or []
    for p in players:
        player = p.get("player") or p
        pname = player.get("name") or "?"
        reason = (p.get("reason") or p.get("type") or "").lower()
        theme = "suspensions" if ("susp" in reason or "ban" in reason) else "blessures"
        out.append({
            "source": "sportradar",
            "theme": theme,
            "fact": f"{pname} ({reason or 'indisponible'})",
            "ts": p.get("start_date") or p.get("updated"),
            "team": team_name,
        })
    return out
