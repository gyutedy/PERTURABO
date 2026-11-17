#!/usr/bin/env python3
"""
BASKET FEED — capteur F01 : boxscores NBA + cotes 2-way de cloture.
==================================================================
Telecharge les boxscores via nba_api (stats.nba.com, sans cle) et les
cotes de cloture h2h via The Odds API historique (cle payante requise).
Ecrit un CSV par saison dans ARCHIVUM/cache/basket/ :
  game_id,date,team_home,team_away,pts_home,pts_away,odds_home,odds_away
Cote absente = cellule vide (trou declare cote backtest), jamais 0, jamais
une valeur estimee. Le moteur F02 ne fait aucun appel reseau : tout passe
par ce capteur.

Usage :
  python basket_feed.py --seasons 2023-24,2024-25
  python basket_feed.py --seasons 2024-25 --skip-odds
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ENV_PATH = os.path.join(WORLD, "env_pari")
DEFAULT_DIR = os.path.join(WORLD, "ARCHIVUM", "cache", "basket")
FIELDS = ("game_id", "date", "team_home", "team_away", "pts_home", "pts_away",
          "odds_home", "odds_away")
ODDS_URL = ("https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds"
            "?apiKey={key}&regions=us&markets=h2h&oddsFormat=decimal&date={day}T23:59:00Z")


def _odds_key():
    try:
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("ODDS_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return os.environ.get("ODDS_API_KEY", "")


def fetch_scores(season):
    from nba_api.stats.endpoints import leaguegamelog
    df = leaguegamelog.LeagueGameLog(
        season=season, season_type_all_star="Regular Season",
        player_or_team_abbreviation="T", timeout=60,
    ).get_data_frames()[0]
    games = {}
    for _, row in df.iterrows():
        gid = str(row["GAME_ID"])
        if not gid:
            continue
        matchup = str(row["MATCHUP"])
        name = str(row["TEAM_NAME"]).strip()
        pts = row["PTS"]
        try:
            pts = int(float(pts))
        except (TypeError, ValueError):
            continue
        rec = games.setdefault(gid, {
            "game_id": gid, "date": str(row["GAME_DATE"])[:10],
            "home": None, "away": None, "pts_home": None, "pts_away": None,
        })
        if "vs." in matchup:
            rec["home"], rec["pts_home"] = name, pts
        elif "@" in matchup:
            rec["away"], rec["pts_away"] = name, pts
    out = []
    for g in games.values():
        if all(g.get(k) is not None for k in ("home", "away", "pts_home", "pts_away")):
            out.append(g)
    out.sort(key=lambda g: (g["date"], g["game_id"]))
    return out


def fetch_odds(day, key):
    """Snapshot de fin de journee -> {(home, away): (odds_home, odds_away)}."""
    url = ODDS_URL.format(key=key, day=day)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            events = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None, "historique_indisponible"
        return {}, "odds_http_%s" % e.code
    except Exception:
        return {}, "odds_indisponible"
    out = {}
    for ev in events or []:
        home, away = ev.get("home_team"), ev.get("away_team")
        for bm in ev.get("bookmakers") or []:
            for mk in bm.get("markets") or []:
                if mk.get("key") != "h2h":
                    continue
                prices = {str(o.get("name")): o.get("price") for o in mk.get("outcomes") or []}
                oh, oa = prices.get(home), prices.get(away)
                if oh and oa:
                    try:
                        fh, fa = float(oh), float(oa)
                        if fh > 1.0 and fa > 1.0:
                            out[(home, away)] = (fh, fa)
                    except (TypeError, ValueError):
                        pass
                break
    return out, None


def build(season, seasons_dir, skip_odds=False):
    rows = fetch_scores(season)
    key = "" if skip_odds else _odds_key()
    days = sorted({r["date"] for r in rows})
    odds_by_day = {}
    blocked = False
    if key:
        for day in days:
            got, err = fetch_odds(day, key)
            if err == "historique_indisponible":
                blocked = True
                break
            odds_by_day[day] = got or {}

    csv_rows = []
    n_odds = 0
    for r in rows:
        prices = odds_by_day.get(r["date"], {}).get((r["home"], r["away"]))
        if prices:
            n_odds += 1
        csv_rows.append({
            "game_id": r["game_id"], "date": r["date"],
            "team_home": r["home"], "team_away": r["away"],
            "pts_home": r["pts_home"], "pts_away": r["pts_away"],
            "odds_home": prices[0] if prices else "",
            "odds_away": prices[1] if prices else "",
        })

    os.makedirs(seasons_dir, exist_ok=True)
    label = season.replace("-", "_") + ".csv"
    path = os.path.join(seasons_dir, label)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(csv_rows)
    return {
        "saison": season, "fichier": path, "matchs": len(csv_rows),
        "avec_cotes": n_odds, "sans_cotes": len(csv_rows) - n_odds,
        "historique_bloque": blocked, "cle_odds_presente": bool(key),
    }


def main():
    ap = argparse.ArgumentParser(description="F01 basket feed — boxscores + cotes")
    ap.add_argument("--seasons", default="2023-24,2024-25")
    ap.add_argument("--out-dir", default=DEFAULT_DIR)
    ap.add_argument("--skip-odds", action="store_true")
    args = ap.parse_args()
    for season in [s.strip() for s in args.seasons.split(",") if s.strip()]:
        try:
            rec = build(season, args.out_dir, skip_odds=args.skip_odds)
            print(json.dumps(rec, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"saison": season, "erreur": type(e).__name__,
                              "detail": str(e)[:200]}, ensure_ascii=False))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
