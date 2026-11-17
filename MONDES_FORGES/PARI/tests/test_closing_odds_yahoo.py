#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F01 — jonction cotes Yahoo/MGM : x0 cote inventee, idempotence, trous declares."""

import csv
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors"))

import closing_odds_yahoo as coy  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok)))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST F01 — closing_odds_yahoo")
    print("=" * 70)

    check("coy.nom_lakers", coy.normalize_team("LA Lakers") == "Los Angeles Lakers")
    check("coy.nom_clippers", coy.normalize_team("LA Clippers") == "LA Clippers")
    check("coy.nom_inconnu", coy.normalize_team("Paris") is None)
    check("coy.cote_vide", coy.odds_num("") is None)
    check("coy.cote_un", coy.odds_num("1.0") is None)
    check("coy.cote_texte", coy.odds_num("x") is None)
    check("coy.cote_valide", coy.odds_num("2,150") == 2.15)

    source = [
        {"game_id": "nba.g.1", "game_date": "2024-01-02-10:00",
         "home_team": "Denver", "away_team": "LA Lakers",
         "money_home_decimal_odds": "1.80", "money_away_decimal_odds": "2.10"},
        {"game_id": "nba.g.2", "game_date": "2024-01-03-10:00",
         "home_team": "Boston", "away_team": "Miami",
         "money_home_decimal_odds": "", "money_away_decimal_odds": "2.10"},
        {"game_id": "nba.g.3", "game_date": "2024-01-04-10:00",
         "home_team": "Atlanta", "away_team": "Paris",
         "money_home_decimal_odds": "1.90", "money_away_decimal_odds": "2.00"},
    ]
    index, holes, unknown = coy.index_odds(source)
    key = ("2024-01-02", "Denver Nuggets", "Los Angeles Lakers")
    check("coy.index_cle", index.get(key) == (1.8, 2.1))
    check("coy.index_trou_cote", any("cote_source_absente" in h for h in holes))
    check("coy.index_equipe_inconnue", unknown == ["Paris"])

    tmp = tempfile.mkdtemp(prefix="pari-yahoo-")
    path = os.path.join(tmp, "2024_25.csv")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=[
            "game_id", "date", "team_home", "team_away",
            "pts_home", "pts_away", "odds_home", "odds_away"])
        w.writeheader()
        w.writerow({"game_id": "M1", "date": "2024-01-02",
                    "team_home": "Denver Nuggets", "team_away": "Los Angeles Lakers",
                    "pts_home": 119, "pts_away": 107, "odds_home": "", "odds_away": ""})
        w.writerow({"game_id": "M2", "date": "2024-01-05",
                    "team_home": "Boston Celtics", "team_away": "Miami Heat",
                    "pts_home": 100, "pts_away": 98, "odds_home": "", "odds_away": ""})

    first = coy.patch(path, index)
    check("coy.patch_rempli", first["cotes_remplies"] == 1, str(first))
    check("coy.patch_non_joint", first["jonction_introuvable"] == 1)
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check("coy.pas_d_invention", rows[1]["odds_home"] == "" and rows[1]["odds_away"] == "")
    check("coy.cote_ecrite", rows[0]["odds_home"] == "1.800" and rows[0]["odds_away"] == "2.100")

    second = coy.patch(path, index)
    check("coy.idempotence", second["deja_presentes"] == 1 and second["cotes_remplies"] == 0)

    ok = all(v for _, v in CHECKS)
    print("=" * 70)
    print(f"RESULTAT: {sum(v for _, v in CHECKS)}/{len(CHECKS)} " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
