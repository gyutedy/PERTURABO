"""
CONNECTEUR football-data.co.uk (AUCUNE CLÉ) — stats d'équipes par venue
=======================================================================
Télécharge le CSV d'une ligue/saison et construit les stats par équipe :
mj, buts marqués/encaissés, SPLIT DOM/EXT, et split par mi-temps (HTHG/HTAG).

C'est LA base gratuite du monde : remplis une carte de matchs en collant
seulement les paires de noms, le capteur injecte les stats.

Usage (via capteurs.py):
  python capteurs.py build-stats --league E0 --season 2627 --include-seasons 2526 \
      --last 12 --out ARCHIVUM/teams/E0_2627.json

Codes ligue : E0 Premier League, SP1 La Liga, I1 Serie A, D1 Bundesliga, F1 Ligue 1,
E1 Championship, P1 Portugal, N1 Pays-Bas, B1 Belgique, T1 Turquie, SC0 Écosse…
Saison : "2627" pour 2026-27.
"""

import csv
import io
import os
import sys
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
TOP5 = {"E0", "SP1", "I1", "D1", "F1"}
_ROWS = {}


def _cache_dir():
    env = os.environ.get("PARI_UK_CACHE")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    world = os.path.normpath(os.path.join(here, "..", "..", ".."))
    return os.path.join(world, "ARCHIVUM", "cache", "f00")


def _cache_path(code: str, season: str) -> str:
    return os.path.join(_cache_dir(), f"uk_{code}_{season}.csv")


def _download(code: str, season: str) -> str:
    url = BASE_URL.format(season=season, code=code)
    req = urllib.request.Request(url, headers={"User-Agent": "PERTURABO-PARI/1.0 (warsmith)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    text = raw.decode("cp1252", errors="replace")
    path = _cache_path(code, season)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def _read_cache_text(code: str, season: str):
    path = _cache_path(code, season)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_csv_text(text: str) -> list:
    return list(csv.DictReader(io.StringIO(text or "")))


def load_rows(code: str, season: str, extra_seasons=None, download=True) -> list:
    """CSV ligue. download=False = cache disque / memoire seulement (zero reseau)."""
    seasons = [season] + [s for s in (extra_seasons or []) if s != season]
    key = (code, tuple(seasons))
    if key in _ROWS:
        return _ROWS[key]
    rows = []
    for s in seasons:
        text = _read_cache_text(code, s)
        if text is None and download:
            try:
                text = _download(code, s)
            except Exception:
                text = None
        if text:
            rows += parse_csv_text(text)
    _ROWS[key] = rows
    return rows


def rows_from_cache(code: str, season: str = "2627", extra_seasons=None) -> list:
    return load_rows(code, season, extra_seasons=extra_seasons or ["2526"], download=False)


def _num(row, *keys):
    for k in keys:
        v = (row.get(k) or "").strip()
        if v:
            try:
                return float(v)
            except ValueError:
                pass
    return None


def _score(a, b):
    if a is None or b is None:
        return None
    return f"{int(a)}-{int(b)}"


def _dkey(r):
    raw = (r.get("Date") or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.min


def _team_key_local(name):
    try:
        cap_dir = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "F00_RADAR", "CODEBASE"))
        if cap_dir not in sys.path:
            sys.path.insert(0, cap_dir)
        from capteurs import team_key
        return team_key(name)
    except Exception:
        return "".join(c for c in (name or "").lower() if c.isalnum())


def _same_team(a, b, key_fn=None):
    fn = key_fn or _team_key_local
    ka, kb = fn(a), fn(b)
    return bool(ka and kb and ka == kb)


def last_matches(rows, team, n=10, key_fn=None):
    """N derniers matchs d'une equipe (plus recents d'abord). Club hors CSV = []."""
    if not team or not rows:
        return []
    out = []
    for r in sorted(rows, key=_dkey, reverse=True):
        home = (r.get("HomeTeam") or "").strip()
        away = (r.get("AwayTeam") or "").strip()
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        if not (home and away and fthg is not None and ftag is not None):
            continue
        if _same_team(team, home, key_fn):
            venue, opp, gs, ga = "H", away, fthg, ftag
            hthg, htag = _num(r, "HTHG"), _num(r, "HTAG")
            hs, hst = _num(r, "HS"), _num(r, "HST")
        elif _same_team(team, away, key_fn):
            venue, opp, gs, ga = "A", home, ftag, fthg
            hthg, htag = _num(r, "HTAG"), _num(r, "HTHG")
            hs, hst = _num(r, "AS"), _num(r, "AST")
        else:
            continue
        line = {
            "date": _dkey(r).strftime("%Y-%m-%d") if _dkey(r) != datetime.min else (r.get("Date") or ""),
            "opp": opp,
            "venue": venue,
            "ft": _score(gs, ga),
            "ht": _score(hthg, htag),
        }
        if hs is not None:
            line["hs"] = hs
        if hst is not None:
            line["hst"] = hst
        out.append(line)
        if len(out) >= n:
            break
    return out


def h2h_matches(rows, dom, ext, key_fn=None):
    """Confrontations CSV (plus recentes d'abord). Sans scores = []."""
    fn = key_fn or _team_key_local
    kd, ke = fn(dom), fn(ext)
    if not (rows and kd and ke):
        return []
    want = {kd, ke}
    out = []
    for r in sorted(rows, key=_dkey, reverse=True):
        home = (r.get("HomeTeam") or "").strip()
        away = (r.get("AwayTeam") or "").strip()
        pair = {fn(home), fn(away)}
        if pair != want or "" in pair:
            continue
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        if fthg is None or ftag is None:
            continue
        hthg, htag = _num(r, "HTHG"), _num(r, "HTAG")
        out.append({
            "date": _dkey(r).strftime("%Y-%m-%d") if _dkey(r) != datetime.min else (r.get("Date") or ""),
            "home": home,
            "away": away,
            "ft": _score(fthg, ftag),
            "ht": _score(hthg, htag),
        })
    return out


def h2h_aggregate(matches, dom, key_fn=None):
    """4-3-5 depuis matches[] (victoires du club `dom` actuel)."""
    agg = {"played": 0, "dom_wins": 0, "draws": 0, "ext_wins": 0}
    if not matches:
        return agg
    for m in matches:
        ft = (m.get("ft") or "").split("-")
        if len(ft) != 2:
            continue
        try:
            hg, ag = int(ft[0]), int(ft[1])
        except ValueError:
            continue
        agg["played"] += 1
        home, away = m.get("home") or "", m.get("away") or ""
        if hg == ag:
            agg["draws"] += 1
        elif _same_team(dom, home, key_fn):
            if hg > ag:
                agg["dom_wins"] += 1
            else:
                agg["ext_wins"] += 1
        elif _same_team(dom, away, key_fn):
            if ag > hg:
                agg["dom_wins"] += 1
            else:
                agg["ext_wins"] += 1
    return agg


def build_team_stats(code: str, season: str, last_n: int = 12, extra_seasons=None) -> dict:
    """Stats par équipe, split Domicile/Extérieur, sur les `last_n` derniers
    matchs PAR ÉQUIPE (fenêtre glissante, jamais un quota global).

    extra_seasons : saisons antérieures à fusionner (ex: ['2526']) —
    indispensable si la saison en cours vient de démarrer (< 6 matchs/équipe).
    """
    seasons = [season] + [s for s in (extra_seasons or []) if s != season]
    rows = load_rows(code, season, extra_seasons=extra_seasons)

    def dkey(r):
        try:
            return datetime.strptime((r.get("Date") or "").strip(), "%d/%m/%Y")
        except ValueError:
            return datetime.max

    rows = [r for r in sorted(rows, key=dkey) if (r.get("HomeTeam") or "").strip()]

    teams = {}
    counted = {"dom": {}, "ext": {}}
    for r in rows:
        home, away = (r.get("HomeTeam") or "").strip(), (r.get("AwayTeam") or "").strip()
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        hthg, htag = _num(r, "HTHG"), _num(r, "HTAG")
        if not (home and away and fthg is not None and ftag is not None):
            continue
        for team, sens, gs, ga, gs1, ga1 in (
            (home, "dom", fthg, ftag, hthg, htag),
            (away, "ext", ftag, fthg, htag, hthg),
        ):
            idx = counted[sens].setdefault(team, 0)
            if idx >= last_n:
                continue  # fenêtre pleine pour cette équipe (les plus RÉCENTS)
            counted[sens][team] = idx + 1
            t = teams.setdefault(team, {"dom": None, "ext": None})
            s = t.get(sens) or {"mj": 0, "marques": 0.0, "encaisses": 0.0,
                                "marques_mt1": 0.0, "encaisses_mt1": 0.0}
            s["mj"] += 1
            s["marques"] += float(gs)
            s["encaisses"] += float(ga)
            if gs1 is not None and ga1 is not None:
                s["marques_mt1"] += float(gs1)
                s["encaisses_mt1"] += float(ga1)
            t[sens] = s

    # normalisation finale : mt2 = total − mt1 quand le split existe
    out_teams = {}
    for name, t in teams.items():
        clean = {}
        for sens, s in t.items():
            if not s or s["mj"] == 0:
                continue
            s["marques"] = float(s["marques"])
            s["encaisses"] = float(s["encaisses"])
            if s["marques_mt1"] or s["encaisses_mt1"]:
                s["marques_mt2"] = round(s["marques"] - s["marques_mt1"], 1)
                s["encaisses_mt2"] = round(s["encaisses"] - s["encaisses_mt1"], 1)
            else:
                s["marques_mt1"] = None
                s["encaisses_mt1"] = None
            clean[sens] = s
        if clean:
            out_teams[name] = clean

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "football-data.co.uk (usage privé, whitelist)",
        "league_code": code,
        "season": season,
        "merged_seasons": seasons,
        "tier": "top5" if code in TOP5 else "secondaire",
        "last_n_considered": last_n,
        "teams": out_teams,
    }
