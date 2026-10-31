"""
CONNECTEUR Understat xG — SANS CLÉ (JSON embarqué dans la page ligue).
Jamais dans Poisson. Métadonnée ; miss = trou déclaré.
Ligues : EPL, La_liga, Bundesliga, Serie_A, Ligue_1.
"""

import json
import os
import re
import sys

CAP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import http_util

LEAGUE = {
    "E0": "EPL",
    "SP1": "La_liga",
    "D1": "Bundesliga",
    "I1": "Serie_A",
    "F1": "Ligue_1",
}

TEAMS_RE = re.compile(r"teamsData\s*=\s*JSON\.parse\('(.+?)'\)", re.DOTALL)


def _unescape(blob):
    return blob.encode("utf-8").decode("unicode_escape")


def _norm(name):
    return "".join(c for c in (name or "").lower() if c.isalnum())


def season_year(date):
    if not date or len(str(date)) < 7:
        return 2026
    y, m = int(str(date)[:4]), int(str(date)[5:7])
    return y if m >= 7 else y - 1


def fetch_league(code, date=None):
    slug = LEAGUE.get((code or "").upper())
    if not slug:
        return None
    year = season_year(date)
    html = http_util.get_text(f"https://understat.com/league/{slug}/{year}")
    if not html:
        return None
    m = TEAMS_RE.search(html)
    if not m:
        return None
    try:
        data = json.loads(_unescape(m.group(1)))
    except (json.JSONDecodeError, UnicodeError, ValueError):
        return None
    out = {}
    iterable = data.values() if isinstance(data, dict) else data
    for t in iterable:
        if not isinstance(t, dict):
            continue
        title = t.get("title") or t.get("team_name") or ""
        xg = None
        hist = t.get("history") or []
        if hist and isinstance(hist[-1], dict):
            try:
                xg = float(hist[-1].get("xG") or hist[-1].get("npxG") or 0)
            except (TypeError, ValueError):
                xg = None
        if title:
            rec = {"name": title, "xg": xg}
            out[_norm(title)] = rec
            out[title] = rec
    return {"league": slug, "season": year, "teams": out} if out else None


def lookup(blob, team):
    if not blob:
        return None
    teams = blob.get("teams") or {}
    n = _norm(team)
    hit = teams.get(n) or teams.get(team)
    if hit:
        return hit
    for k, v in teams.items():
        kn = _norm(k)
        if n and kn and min(len(n), len(kn)) >= 5 and (n in kn or kn in n):
            return v
    return None
