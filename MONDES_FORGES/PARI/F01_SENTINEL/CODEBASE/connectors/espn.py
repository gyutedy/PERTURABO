"""
CONNECTEUR ESPN — voix 3 notes (blessures / suspensions). Public, sans cle.
GET site.api.espn.com/apis/site/v2/sports/soccer/{league}/injuries
Fetch PAR LIGUE (chemin equipe = {}). Matching nom + difflib 0.9.
Cache 1 hit / ligue / jour + 1 hit / equipe / jour. Timeout / 3 fails = [].
Jamais de devine. Jamais dans Poisson.
"""

import difflib
import os
import sys
import unicodedata
from datetime import datetime, timezone

_THIS = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.normpath(os.path.join(_THIS, "..", "..", "..", "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import cache
import http_util

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

LEAGUES = {
    "E0": "eng.1",
    "SP1": "esp.1",
    "I1": "ita.1",
    "D1": "ger.1",
    "F1": "fra.1",
    "N1": "ned.1",
    "T1": "tur.1",
    "J1": "jpn.1",
}

_STRIP = {
    "fc", "cf", "sc", "ac", "afc", "as", "ss", "ssc", "us", "ud", "sd", "cd",
    "ca", "rc", "rcd", "club", "de", "del", "la", "le", "the", "futbol",
    "football", "calcio", "ii", "sv", "vfl", "vfb", "tsg", "fsv", "spvgg",
}


def _norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    tokens = []
    for raw in s.split():
        tok = "".join(c for c in raw if c.isalnum())
        if not tok or tok.isdigit() or tok in _STRIP:
            continue
        tokens.append(tok)
    return "".join(tokens)


def _theme(status, comment):
    blob = f"{status} {comment}".lower()
    if any(k in blob for k in ("susp", "ban", "red", "eject")):
        return "suspensions"
    return "blessures"


def _facts_from_team(block, team_name, now_iso):
    out = []
    for p in block.get("injuries") or []:
        if not isinstance(p, dict):
            continue
        athlete = p.get("athlete") or {}
        pname = athlete.get("displayName") or athlete.get("shortName") or "?"
        status = p.get("status") or ""
        comment = p.get("shortComment") or p.get("longComment") or ""
        label = status or comment or "indisponible"
        out.append({
            "source": "espn",
            "theme": _theme(status, comment),
            "fact": f"{pname} ({label})",
            "ts": p.get("date") or now_iso,
            "team": team_name,
        })
    return out


def _league_entries(code):
    payload, _ = cache.get_or_fetch("espn_league", code or "", lambda: _fetch_league(code))
    return payload or []


def _fetch_league(code):
    slug = LEAGUES.get(code or "")
    if not slug:
        return []
    data = http_util.get_json(f"{BASE}/{slug}/injuries")
    if not data:
        return []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for block in data.get("injuries") or []:
        if not isinstance(block, dict):
            continue
        names = [n for n in (block.get("displayName"), block.get("name"),
                             block.get("shortDisplayName"), block.get("abbreviation")) if n]
        if not names:
            continue
        facts = _facts_from_team(block, names[0], now_iso)
        if facts:
            out.append({"names": names, "facts": facts, "id": block.get("id")})
    return out


def missing_players(team_name, code=None):
    key = f"{code}:{team_name}" if code else team_name
    payload, _ = cache.get_or_fetch("espn", key, lambda: _fetch(team_name, code))
    return payload or []


def _fetch(team_name, code=None):
    name = (team_name or "").strip()
    if not name:
        return []
    n = _norm(name)
    if not n:
        return []
    entries = _league_entries(code)
    idx = {}
    for entry in entries:
        for raw in entry.get("names") or []:
            k = _norm(raw)
            if k:
                idx.setdefault(k, entry.get("facts") or [])
    facts = idx.get(n)
    if facts is None:
        close = difflib.get_close_matches(n, list(idx), n=1, cutoff=0.9)
        if close:
            facts = idx[close[0]]
    out = []
    for f in facts or []:
        row = dict(f)
        row["team"] = team_name
        out.append(row)
    return out
