"""
CONNECTEUR SofaScore — voix 1 notes (blessures / suspensions).
API publique search + team missing players. Timeout = trou.
1 hit / équipe / jour via cache F00.
"""

import os
import sys

CAP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import cache
import http_util

BASE = "https://api.sofascore.com/api/v1"


def _search_team(name):
    q = (name or "").strip()
    if not q:
        return None
    data = http_util.get_json(f"{BASE}/search/all?q={urllib_quote(q)}")
    if not data:
        return None
    for group in data.get("results") or []:
        typ = group.get("type") or ""
        entity = group.get("entity") or group
        if typ == "team" or entity.get("name"):
            if (entity.get("sport") or {}).get("slug") in (None, "football"):
                return {"id": entity.get("id"), "name": entity.get("name")}
    return None


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s)


def missing_players(team_name):
    """Liste de faits {theme, fact, ts, source} ou []. Trou réseau → []."""
    payload, _ = cache.get_or_fetch("sofascore", team_name, lambda: _fetch(team_name))
    return payload or []


def _fetch(team_name):
    found = _search_team(team_name)
    if not found or not found.get("id"):
        return []
    tid = found["id"]
    data = http_util.get_json(f"{BASE}/team/{tid}/missing-players")
    if not data:
        return []
    out = []
    groups = data.get("missingPlayers") or data
    if isinstance(groups, dict):
        iterable = []
        for k, v in groups.items():
            if isinstance(v, list):
                iterable.extend(v)
            elif isinstance(v, dict):
                iterable.append(v)
    elif isinstance(groups, list):
        iterable = groups
    else:
        iterable = []
    for p in iterable:
        player = (p.get("player") or p)
        pname = player.get("name") or player.get("shortName") or "?"
        reason = (p.get("reason") or p.get("type") or p.get("status") or "").lower()
        if "susp" in reason or "red" in reason or "cart" in reason:
            theme = "suspensions"
        else:
            theme = "blessures"
        out.append({
            "source": "sofascore",
            "theme": theme,
            "fact": f"{pname} ({reason or 'indisponible'})",
            "ts": p.get("startTimestamp") or p.get("date"),
            "team": team_name,
        })
    return out
