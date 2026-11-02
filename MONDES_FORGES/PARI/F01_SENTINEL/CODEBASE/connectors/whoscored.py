"""
CONNECTEUR WhoScored / Opta — voix 3 notes.
Pas de scrape HTML lourd : RapidAPI WHOSCORED_KEY si présente, sinon trou.
Jamais le même upstream que Sofa/API-Sports.
"""

import os
import sys

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

HOST = os.environ.get("WHOSCORED_HOST", "whoscored.p.rapidapi.com")


def _key():
    return os.environ.get("WHOSCORED_KEY") or os.environ.get("RAPIDAPI_WHOSCORED_KEY")


def missing_players(team_name):
    payload, _ = cache.get_or_fetch("whoscored", team_name, lambda: _fetch(team_name))
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
        f"https://{HOST}/search?query={quote(q)}",
        headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST},
    )
    if not data:
        return []
    tid = None
    rows = data if isinstance(data, list) else (data.get("teams") or data.get("results") or [])
    for row in rows:
        if isinstance(row, dict) and (row.get("id") or row.get("teamId")):
            tid = row.get("id") or row.get("teamId")
            break
    if not tid:
        return []
    miss = http_util.get_json(
        f"https://{HOST}/team/{tid}/injuries",
        headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST},
    )
    if not miss:
        return []
    out = []
    players = miss if isinstance(miss, list) else (miss.get("injuries") or miss.get("players") or [])
    for p in players:
        if not isinstance(p, dict):
            continue
        pname = p.get("name") or p.get("playerName") or "?"
        reason = (p.get("reason") or p.get("status") or p.get("type") or "").lower()
        theme = "suspensions" if ("susp" in reason or "ban" in reason) else "blessures"
        out.append({
            "source": "whoscored",
            "theme": theme,
            "fact": f"{pname} ({reason or 'indisponible'})",
            "ts": p.get("date") or p.get("updated"),
            "team": team_name,
        })
    return out
