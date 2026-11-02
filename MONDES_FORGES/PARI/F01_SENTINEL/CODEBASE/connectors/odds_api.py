"""
CONNECTEUR The Odds API — cotes T-2h (voix marche, pas Poisson).
Cle optionnelle ODDS_API_KEY (alias THE_ODDS_API_KEY) dans env_pari.
Absente / timeout / 3 fails = [] (trou), jamais de devine, jamais scrape Winner.
Cache 1 hit / ligue / jour. Matching nom + difflib 0.9.
Marches: h2h (1/X/2) + totals 2.5 (o2.5/u2.5). MT / BTTS = trou si absents.
"""

import difflib
import os
import sys
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote

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

BASE = os.environ.get("ODDS_API_BASE", "https://api.the-odds-api.com/v4")

SPORTS = {
    "E0": "soccer_epl",
    "SP1": "soccer_spain_la_liga",
    "I1": "soccer_italy_serie_a",
    "D1": "soccer_germany_bundesliga",
    "F1": "soccer_france_ligue_one",
    "N1": "soccer_netherlands_eredivisie",
    "T1": "soccer_turkey_super_league",
    "J1": "soccer_japan_j_league",
}

_STRIP = {
    "fc", "cf", "sc", "ac", "afc", "as", "ss", "ssc", "us", "ud", "sd", "cd",
    "ca", "rc", "rcd", "club", "de", "del", "la", "le", "the", "futbol",
    "football", "calcio", "ii", "sv", "vfl", "vfb", "tsg", "fsv", "spvgg",
}


def _key():
    return os.environ.get("ODDS_API_KEY") or os.environ.get("THE_ODDS_API_KEY")


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


def _side_ok(q, e):
    if not q or not e:
        return False
    if q == e or q in e or e in q:
        return True
    return difflib.SequenceMatcher(None, q, e).ratio() >= 0.9


def _pick_book(event):
    books = event.get("bookmakers") or []
    for pref in ("pinnacle", "betfair_ex_eu", "betfair", "unibet"):
        for b in books:
            if (b.get("key") or "") == pref:
                return b
    return books[0] if books else None


def _cotes_from_book(book, home, away):
    out = {}
    nh, na = _norm(home), _norm(away)
    for mk in book.get("markets") or []:
        key = mk.get("key")
        outcomes = mk.get("outcomes") or []
        if key == "h2h":
            for o in outcomes:
                name = o.get("name") or ""
                price = o.get("price")
                if not isinstance(price, (int, float)) or price <= 1:
                    continue
                nn = _norm(name)
                if nn in ("draw", "nul", "tie", "x"):
                    out["X"] = float(price)
                elif _side_ok(nh, nn):
                    out["1"] = float(price)
                elif _side_ok(na, nn):
                    out["2"] = float(price)
        elif key == "totals":
            for o in outcomes:
                point = o.get("point")
                price = o.get("price")
                name = (o.get("name") or "").lower()
                if point != 2.5 or not isinstance(price, (int, float)) or price <= 1:
                    continue
                if name.startswith("over"):
                    out["o2.5"] = float(price)
                elif name.startswith("under"):
                    out["u2.5"] = float(price)
    return out


def _index_events(payload):
    rows = []
    for ev in payload or []:
        if not isinstance(ev, dict):
            continue
        home = ev.get("home_team") or ""
        away = ev.get("away_team") or ""
        book = _pick_book(ev)
        cotes = _cotes_from_book(book, home, away) if book else {}
        rows.append({
            "id": ev.get("id"),
            "home": home,
            "away": away,
            "commence_time": ev.get("commence_time"),
            "sport_key": ev.get("sport_key"),
            "bookmaker": (book or {}).get("key"),
            "cotes": cotes,
        })
    return rows


def _fetch_league(code):
    key = _key()
    sport = SPORTS.get(code or "")
    if not key or not sport:
        return []
    url = (
        f"{BASE}/sports/{quote(sport)}/odds/"
        f"?apiKey={quote(key)}&regions=eu&markets=h2h,totals&oddsFormat=decimal"
    )
    data = http_util.get_json(url)
    if not isinstance(data, list):
        return []
    return _index_events(data)


def league_odds(code):
    if not _key() or (code or "") not in SPORTS:
        return []
    payload, _ = cache.get_or_fetch("oddsapi_league", code or "", lambda: _fetch_league(code))
    return payload or []


def match_odds(dom, ext, code=None):
    nd, ne = _norm(dom), _norm(ext)
    if not nd or not ne:
        return None
    key = f"{code}:{nd}_{ne}" if code else f"{nd}_{ne}"
    payload, _ = cache.get_or_fetch("oddsapi", key, lambda: _fetch_match(dom, ext, code))
    return payload


def _fetch_match(dom, ext, code=None):
    nd, ne = _norm(dom), _norm(ext)
    for row in league_odds(code):
        eh, ea = _norm(row.get("home")), _norm(row.get("away"))
        if _side_ok(nd, eh) and _side_ok(ne, ea):
            return row
        if _side_ok(nd, ea) and _side_ok(ne, eh):
            flipped = dict(row)
            cotes = dict(row.get("cotes") or {})
            if "1" in cotes or "2" in cotes:
                cotes["1"], cotes["2"] = cotes.get("2"), cotes.get("1")
                cotes = {k: v for k, v in cotes.items() if v is not None}
            flipped["cotes"] = cotes
            flipped["home"], flipped["away"] = row.get("away"), row.get("home")
            flipped["flipped"] = True
            return flipped
    return None
