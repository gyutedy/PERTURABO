"""
CONNECTEUR Sportradar StatsHub — voix 2 notes (blessures / suspensions).
API trial v4 : missing_players est publié PAR SAISON, pas par équipe.
Clé optionnelle SPORTRADAR_API_KEY (alias SR_API_KEY). Absente / timeout = [].
1 hit / compétition / jour via cache F00. Indépendant d'Opta / SofaScore.
"""

import difflib
import os
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

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

BASE = os.environ.get("SPORTRADAR_BASE", "https://api.sportradar.com/soccer/trial/v4/en")

COMPETITIONS = {
    "E0": "sr:competition:17",
    "SP1": "sr:competition:8",
    "I1": "sr:competition:23",
    "D1": "sr:competition:35",
    "F1": "sr:competition:34",
    "N1": "sr:competition:37",
}

_STRIP = {
    "fc", "cf", "sc", "ac", "afc", "as", "ss", "ssc", "us", "ud", "sd", "cd",
    "ca", "rc", "rcd", "club", "de", "del", "la", "le", "the", "futbol",
    "football", "calcio", "ii", "sv", "vfl", "vfb", "tsg", "fsv", "spvgg",
    "ogc", "losc",
}


def _key():
    return os.environ.get("SPORTRADAR_API_KEY") or os.environ.get("SR_API_KEY")


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


def _season_id(cid, key):
    cached, _ = cache.get_or_fetch(
        "sportradar_v4_seasonid", cid, lambda: _fetch_season_id(cid, key))
    return cached


def _fetch_season_id(cid, key):
    data = http_util.get_json(f"{BASE}/competitions/{cid}/seasons.json?api_key={key}")
    seasons = (data or {}).get("seasons") or []
    if not seasons:
        return None
    ordered = sorted(seasons, key=lambda s: s.get("start_date") or "")
    return ordered[-1].get("id")


def _competition_facts(code):
    """Liste [{names, facts}] pour une compétition. 1 hit / jour."""
    payload, _ = cache.get_or_fetch(
        "sportradar_v4_comp", code, lambda: _fetch_competition(code))
    return payload or []


def _fetch_competition(code):
    key = _key()
    cid = COMPETITIONS.get(code)
    if not key or not cid:
        return []
    sid = _season_id(cid, key)
    if not sid:
        return []
    data = http_util.get_json(f"{BASE}/seasons/{sid}/missing_players.json?api_key={key}")
    if not data:
        return []
    out = []
    for comp in data.get("competitors") or []:
        players = comp.get("players") or []
        if not players:
            continue
        facts = []
        for p in players:
            pname = p.get("name") or "?"
            reason = (p.get("reason") or p.get("type") or p.get("status") or "").lower()
            theme = "suspensions" if ("susp" in reason or "ban" in reason or "red" in reason) \
                else "blessures"
            facts.append({
                "theme": theme,
                "fact": f"{pname} ({reason or 'indisponible'})",
                "ts": p.get("start_date") or p.get("updated"),
            })
        out.append({
            "names": [n for n in (comp.get("name"), comp.get("short_name"),
                                  comp.get("long_name")) if n],
            "facts": facts,
        })
    return out


def _index():
    """Index normalisé nom → faits sur les 6 championnats (1 build / jour, persiste)."""
    payload, _ = cache.get_or_fetch("sportradar_v4_index", "big6", _build_index)
    return payload or {}


def _index_from(entries):
    idx = {}
    for entry in entries:
        for name in entry.get("names") or []:
            n = _norm(name)
            if n:
                idx.setdefault(n, entry.get("facts") or [])
    return idx


def _build_index():
    idx = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(_competition_facts, list(COMPETITIONS)))
    for entries in results:
        idx.update(_index_from(entries))
    return idx


def _league_index(code):
    """Index d'une seule competition si connue, sinon index complet (cache jour)."""
    if code in COMPETITIONS:
        payload, _ = cache.get_or_fetch(
            "sportradar_v4_index_comp", code, lambda: _index_from(_competition_facts(code)))
        return payload or {}
    return _index()


def missing_players(team_name, code=None):
    """Liste de faits {source, theme, fact, ts, team} ou []. Trou reseau -> []."""
    key_team = f"{code}:{team_name}" if code else team_name
    payload, _ = cache.get_or_fetch(
        "sportradar_v4_team", key_team, lambda: _fetch(team_name, code))
    return payload or []


def _fetch(team_name, code=None):
    name = (team_name or "").strip()
    if not name or not _key():
        return []
    n = _norm(name)
    if not n:
        return []
    idx = _league_index(code)
    facts = idx.get(n)
    if facts is None:
        close = difflib.get_close_matches(n, list(idx), n=1, cutoff=0.9)
        if close:
            facts = idx[close[0]]
    out = []
    for f in facts or []:
        out.append({
            "source": "sportradar",
            "theme": f.get("theme") or "blessures",
            "fact": f.get("fact") or "?",
            "ts": f.get("ts"),
            "team": team_name,
        })
    return out
