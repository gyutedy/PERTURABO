"""
CONNECTEUR match_timing — timing des buts / cartons (TROU fermé v2.8).
Host RapidAPI SofaSport déjà souscrit (endpoints /event/{id}/incidents sondés
LIVE 2026-11-02 : 21 incidents sur Bournemouth-Arsenal, time/incidentType/...).
Usage doctrine : **affichage /data et /data N uniquement** — JAMAIS dans Poisson,
JAMAIS dans λ. Trou si reseau ferme / pas de candidat = nerve declared, pas devine.
Cache 1 hit / ematch / jour (cle dom__ext). Kill switch PARI_SKIP_TIMING=1.
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
                    if k and v and not os.environ.get(k):
                        os.environ[k] = v
        except OSError:
            pass


_load_env_pari()

BASE = f"https://{os.environ.get('SOFASCORE_HOST', 'sofascore-sport-api.p.rapidapi.com')}/api"

_STRIP = {"fc", "cf", "sc", "ac", "afc", "as", "ss", "us", "ud", "sd", "cd", "ca", "rc",
          "club", "de", "del", "la", "la", "le", "the", "futbol", "football", "calcio",
          "ii", "sv", "vfl", "vfb", "tsg", "fsv"}


def _key():
    return (os.environ.get("SOFASCORE_RAPIDAPI_KEY")
            or os.environ.get("WHOSCORED_KEY")
            or os.environ.get("RAPIDAPI_WHOSCORED_KEY"))


def _headers():
    k = _key()
    if not k:
        return None
    return {"X-RapidAPI-Key": k, "X-RapidAPI-Host": os.environ.get("SOFASCORE_HOST", "sofascore-sport-api.p.rapidapi.com")}


def _norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    toks = []
    for raw in s.split():
        tok = "".join(c for c in raw if c.isalnum())
        if not tok or tok in _STRIP:
            continue
        toks.append(tok)
    return "".join(toks)


def _side_ok(q, e):
    if not q or not e:
        return False
    if q in e or e in q:
        return True
    return difflib.SequenceMatcher(None, q, e).ratio() >= 0.9


def _search_team(name):
    q = (name or "").strip()
    if not q:
        return None
    data = http_util.get_json(f"{BASE}/search/all?q={q}", headers=_headers())
    if not data:
        return None
    for group in data.get("results") or []:
        entity = group.get("entity") or group
        sport = (entity.get("sport") or {}).get("slug")
        if sport in (None, "football"):
            return entity.get("id")
    return None


def _find_event(dom, ext):
    """event du match dom vs ext parmi next+last des deux teams (matching symetrique)."""
    nd, ne = _norm(dom), _norm(ext)
    evs = []
    for tm in (dom, ext):
        tid = _search_team(tm)
        if not tid:
            continue
        for path in ("events/next/0", "events/last/0"):
            data = http_util.get_json(f"{BASE}/team/{tid}/{path}", headers=_headers()) or {}
            for e in (data.get("events") or []):
                eh = _norm((e.get("homeTeam") or {}).get("name"))
                ea = _norm((e.get("awayTeam") or {}).get("name"))
                if (_side_ok(nd, eh) and _side_ok(ne, ea)) or (_side_ok(nd, ea) and _side_ok(ne, eh)):
                    evs.append(e)
    if not evs:
        return None
    # sans date de carte : event a venir (not started) sinon last ; multiple = le plus recent
    evs = sorted(evs, key=lambda e: e.get("startTimestamp") or 0, reverse=True)
    return evs[0]


def _incidents_out(ev):
    eid = ev.get("id")
    if not eid:
        return None
    data = http_util.get_json(f"{BASE}/event/{eid}/incidents", headers=_headers())
    if not data:
        return None
    arr = data.get("incidents") or []
    goals, cards = [], []
    for i in arr:
        typ = (i.get("incidentType") or "").lower()
        cls = (i.get("incidentClass") or "").lower()
        player = (i.get("playerName") or (i.get("player") or {}).get("name") or "?")
        minute = i.get("time")
        if typ == "goal" or (typ == "penalty" and cls in ("scored", "penalty")):
            side = None
            if i.get("isHome") is True:
                side = "dom"
            elif i.get("isHome") is False:
                side = "ext"
            goals.append({
                "minute": minute,
                "side": side,
                "player": player,
                "class": cls or "normal",
                "score": f"{i.get('homeScore','?')}-{i.get('awayScore','?')}",
            })
        elif typ == "card":
            cards.append({"minute": minute, "player": player, "class": cls or "yellow"})
    return {
        "event_id": eid,
        "slug": ev.get("slug"),
        "status": ((ev.get("status") or {}).get("description") or ""),
        "commenced": (ev.get("startTimestamp") and datetime.fromtimestamp(
            ev["startTimestamp"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")) or None,
        "home": (ev.get("homeTeam") or {}).get("name"),
        "away": (ev.get("awayTeam") or {}).get("name"),
        "goals": goals,
        "cards": cards,
    }


def match_timing(dom, ext):
    """{'goals': [...], 'cards': [...], ...} ou None. Cache 1 hit/couple/jour."""
    payload, _ = cache.get_or_fetch("timing", f"{_norm(dom)}__{_norm(ext)}",
                                    lambda: _fetch(dom, ext))
    return payload


def _fetch(dom, ext):
    if not _key():
        return None
    ev = _find_event(dom, ext)
    if not ev:
        return None
    return _incidents_out(ev)
