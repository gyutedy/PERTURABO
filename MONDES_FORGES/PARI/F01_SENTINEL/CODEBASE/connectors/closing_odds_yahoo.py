#!/usr/bin/env python3
"""
CLOSING ODDS YAHOO — greffon F01 : cotes de cloture 2-way gratuites.
==================================================================
Recupere les cotes de cloture MGM/Yahoo (depot public csdurfee/scrape_yahoo_odds)
et remplit les colonnes odds_home / odds_away des CSV basket deja produits par
basket_feed.py. Aucune cle, aucun plan payant, aucune cote estimee.

Jonction stricte sur (date, equipe domicile, equipe exterieure). Les noms courts
Yahoo sont convertis vers les noms complets nba_api. Une cote absente = cellule
vide + trou declare, jamais 0, jamais 1.0, jamais une estimation.

Usage :
  python closing_odds_yahoo.py --dry-run
  python closing_odds_yahoo.py --seasons 2023-24,2024-25
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_DIR = os.path.join(WORLD, "ARCHIVUM", "cache", "basket")

SOURCES = {
    "2023-24": "https://raw.githubusercontent.com/csdurfee/scrape_yahoo_odds/main/yahoo_scrapes/2023/odds.csv",
    "2024-25": "https://raw.githubusercontent.com/csdurfee/scrape_yahoo_odds/main/yahoo_scrapes/2024/odds.csv",
}
LABELS = {
    "2023-24": "2023_24.csv",
    "2024-25": "2024_25.csv",
}
TEAMS = {
    "Atlanta": "Atlanta Hawks",
    "Boston": "Boston Celtics",
    "Brooklyn": "Brooklyn Nets",
    "Charlotte": "Charlotte Hornets",
    "Chicago": "Chicago Bulls",
    "Cleveland": "Cleveland Cavaliers",
    "Dallas": "Dallas Mavericks",
    "Denver": "Denver Nuggets",
    "Detroit": "Detroit Pistons",
    "Golden State": "Golden State Warriors",
    "Houston": "Houston Rockets",
    "Indiana": "Indiana Pacers",
    "LA Clippers": "LA Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "Memphis": "Memphis Grizzlies",
    "Miami": "Miami Heat",
    "Milwaukee": "Milwaukee Bucks",
    "Minnesota": "Minnesota Timberwolves",
    "New Orleans": "New Orleans Pelicans",
    "New York": "New York Knicks",
    "Oklahoma City": "Oklahoma City Thunder",
    "Orlando": "Orlando Magic",
    "Philadelphia": "Philadelphia 76ers",
    "Phoenix": "Phoenix Suns",
    "Portland": "Portland Trail Blazers",
    "Sacramento": "Sacramento Kings",
    "San Antonio": "San Antonio Spurs",
    "Toronto": "Toronto Raptors",
    "Utah": "Utah Jazz",
    "Washington": "Washington Wizards",
}


def normalize_team(name):
    return TEAMS.get((name or "").strip())


def odds_num(raw):
    txt = str(raw or "").strip().replace(",", ".")
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val > 1.0 else None


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "perturabo-pari/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8-sig")
    except Exception as exc:
        return [], "telechargement_echeche:" + type(exc).__name__
    try:
        return list(csv.DictReader(io.StringIO(text))), None
    except Exception as exc:
        return [], "csv_illisible:" + type(exc).__name__


def index_odds(rows):
    index = {}
    holes = []
    unknown = set()
    for row in rows:
        day = (row.get("game_date") or "").strip()[:10]
        home = normalize_team(row.get("home_team"))
        away = normalize_team(row.get("away_team"))
        if home is None:
            unknown.add((row.get("home_team") or "").strip())
        if away is None:
            unknown.add((row.get("away_team") or "").strip())
        if not day or home is None or away is None:
            continue
        oh = odds_num(row.get("money_home_decimal_odds"))
        oa = odds_num(row.get("money_away_decimal_odds"))
        if oh is None or oa is None:
            holes.append((row.get("game_id") or "") + ":cote_source_absente")
            continue
        index[(day, home, away)] = (oh, oa)
    return index, holes, sorted(unknown)


def patch(path, index, dry_run=False):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if "source_prix" not in fields:
            fields.append("source_prix")
        rows = list(reader)
    filled = 0
    deja = 0
    manquantes = []
    for row in rows:
        if odds_num(row.get("odds_home")) is not None and odds_num(row.get("odds_away")) is not None:
            deja += 1
            continue
        key = (
            (row.get("date") or "").strip()[:10],
            (row.get("team_home") or "").strip(),
            (row.get("team_away") or "").strip(),
        )
        prices = index.get(key)
        if prices is None:
            manquantes.append(row.get("game_id") or "")
            continue
        row["odds_home"] = "%.3f" % prices[0]
        row["odds_away"] = "%.3f" % prices[1]
        row["source_prix"] = "proxy_yahoo"
        filled += 1
    if filled and not dry_run:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    return {
        "matchs_csv": len(rows),
        "cotes_remplies": filled,
        "deja_presentes": deja,
        "jonction_introuvable": len(manquantes),
        "exemples_introuvables": manquantes[:10],
        "fichier": path,
    }


def build(season, cache_dir, dry_run=False):
    url = SOURCES.get(season)
    if not url:
        return {"saison": season, "erreur": "saison_inconnue"}
    source, err = fetch(url)
    if err:
        return {"saison": season, "erreur": err}
    index, holes, unknown = index_odds(source)
    path = os.path.join(cache_dir, LABELS[season])
    if not os.path.isfile(path):
        return {"saison": season, "erreur": "csv_absent", "chemin": path}
    result = patch(path, index, dry_run=dry_run)
    result.update({
        "saison": season,
        "lignes_source": len(source),
        "cles_index": len(index),
        "cotes_source_invalides": len(holes),
        "equipes_inconnues": unknown,
        "dry_run": bool(dry_run),
    })
    return result


def main():
    ap = argparse.ArgumentParser(description="F01 — cotes de cloture Yahoo/MGM gratuites")
    ap.add_argument("--seasons", default="2023-24,2024-25")
    ap.add_argument("--cache-dir", default=DEFAULT_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for season in [s.strip() for s in args.seasons.split(",") if s.strip()]:
        print(json.dumps(build(season, args.cache_dir, args.dry_run), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
