"""
CONNECTEUR SofaScore — voix 1 notes (blessures / suspensions).
RapidAPI sofascore-sport-api si SOFASCORE_RAPIDAPI_KEY / WHOSCORED_KEY.
missingPlayers = lineups du prochain event. Timeout = trou.
1 hit / equipe / jour via cache F00.
"""

import os
import sys
from datetime import datetime, timezone

_THIS = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.normpath(os.path.join(_THIS, "..", "..", "..", "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import cache
import http_util

_WORLD = os.path.normpath(os.path.join(_THIS, "..", "..", ".."))


def _load_env_pari():
    for name in (".env", "env_pari"):
        path = os.path.join(_WORLD, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    if key and val and not os.environ.get(key):
                        os.environ[key] = val
        except OSError:
            pass


_load_env_pari()


def _key():
    return (os.environ.get("SOFASCORE_RAPIDAPI_KEY")
            or os.environ.get("WHOSCORED_KEY")
            or os.environ.get("RAPIDAPI_WHOSCORED_KEY"))


def _host():
    return os.environ.get("SOFASCORE_HOST", "sofascore-sport-api.p.rapidapi.com")


def _headers():
    key = _key()
    if not key:
        return None
    return {"X-RapidAPI-Key": key, "X-RapidAPI-Host": _host()}


def _base():
    if _key():
        return f"https://{_host()}/api"
    return "https://api.sofascore.com/api/v1"


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s)


def _search_team(name):
    q = (name or "").strip()
    if not q:
        return None
    data = http_util.get_json(f"{_base()}/search/all?q={urllib_quote(q)}", headers=_headers())
    if not data:
        return None
    for group in data.get("results") or []:
        typ = group.get("type") or ""
        entity = group.get("entity") or group
        if typ == "team" or entity.get("name"):
            sport = (entity.get("sport") or {}).get("slug")
            if sport in (None, "football"):
                return {"id": entity.get("id"), "name": entity.get("name")}
    return None


def missing_players(team_name):
    """Liste de faits {theme, fact, ts, source} ou []. Trou reseau -> []."""
    payload, _ = cache.get_or_fetch("sofascore", team_name, lambda: _fetch(team_name))
    return payload or []


def _theme(reason, description):
    blob = f"{reason} {description}".lower()
    if any(k in blob for k in ("susp", "ban", "red", "card", "cart")):
        return "suspensions"
    return "blessures"


def _facts_from_missing(rows, team_name, now_iso):
    out = []
    for p in rows or []:
        if not isinstance(p, dict):
            continue
        player = p.get("player") or p
        pname = player.get("name") or player.get("shortName") or "?"
        reason = p.get("reason") or p.get("type") or p.get("status") or ""
        desc = p.get("description") or ""
        label = desc or str(reason) or "indisponible"
        out.append({
            "source": "sofascore",
            "theme": _theme(reason, desc),
            "fact": f"{pname} ({label})",
            "ts": now_iso,
            "team": team_name,
        })
    return out


def _fetch(team_name):
    found = _search_team(team_name)
    if not found or not found.get("id"):
        return []
    tid = found["id"]
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if _key():
        events = http_util.get_json(f"{_base()}/team/{tid}/events/next/0", headers=_headers())
        evs = (events or {}).get("events") or []
        if not evs:
            return []
        ev = evs[0]
        eid = ev.get("id")
        if not eid:
            return []
        lu = http_util.get_json(f"{_base()}/event/{eid}/lineups", headers=_headers())
        if not lu:
            return []
        home_id = (ev.get("homeTeam") or {}).get("id")
        side = "home" if home_id == tid else "away"
        block = lu.get(side) or {}
        return _facts_from_missing(block.get("missingPlayers") or [], team_name, now_iso)
    data = http_util.get_json(f"{_base()}/team/{tid}/missing-players", headers=_headers())
    if not data:
        return []
    groups = data.get("missingPlayers") or data
    if isinstance(groups, dict):
        iterable = []
        for v in groups.values():
            if isinstance(v, list):
                iterable.extend(v)
            elif isinstance(v, dict):
                iterable.append(v)
    elif isinstance(groups, list):
        iterable = groups
    else:
        iterable = []
    return _facts_from_missing(iterable, team_name, now_iso)
