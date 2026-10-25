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
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
TOP5 = {"E0", "SP1", "I1", "D1", "F1"}


def _download(code: str, season: str) -> str:
    url = BASE_URL.format(season=season, code=code)
    req = urllib.request.Request(url, headers={"User-Agent": "PERTURABO-PARI/1.0 (warsmith)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    return raw.decode("cp1252", errors="replace")


def _num(row, *keys):
    for k in keys:
        v = (row.get(k) or "").strip()
        if v:
            try:
                return float(v)
            except ValueError:
                pass
    return None


def build_team_stats(code: str, season: str, last_n: int = 12, extra_seasons=None) -> dict:
    """Stats par équipe, split Domicile/Extérieur, sur les `last_n` derniers
    matchs PAR ÉQUIPE (fenêtre glissante, jamais un quota global).

    extra_seasons : saisons antérieures à fusionner (ex: ['2526']) —
    indispensable si la saison en cours vient de démarrer (< 6 matchs/équipe).
    """
    # téléchargements : saison en cours + extras (silencieux si absente)
    seasons = [season] + [s for s in (extra_seasons or []) if s != season]
    rows = []
    for s in seasons:
        try:
            rows += list(csv.DictReader(io.StringIO(_download(code, s))))
        except Exception:
            pass  # saison absente / season gap → on continue avec ce qu'on a

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
