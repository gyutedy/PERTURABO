#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F01 — capture basket Winner Bet : ML seule, heure Kinshasa, zero cote inventee."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))

import input_capture_basket as icb  # noqa: E402

CHECKS = []
BLOB = {
    "contract": "pari.basket_params.v1",
    "base": 110.0, "home_adv": 2.0, "sigma": 16.0,
    "teams": {
        "Toronto Raptors": {"rtg": 0.5, "off": 1.0, "n": 60},
        "New York Knicks": {"rtg": 1.0, "off": 1.5, "n": 60},
        "Minnesota Timberwolves": {"rtg": 2.0, "off": 2.0, "n": 60},
        "Portland Trail Blazers": {"rtg": -1.0, "off": -1.0, "n": 60},
        "San Antonio Spurs": {"rtg": 3.0, "off": 3.0, "n": 60},
        "Detroit Pistons": {"rtg": -2.0, "off": -2.0, "n": 60},
        "LA Clippers": {"rtg": 1.5, "off": 1.2, "n": 60},
        "Utah Jazz": {"rtg": -1.5, "off": -1.2, "n": 60},
        "Los Angeles Lakers": {"rtg": 2.5, "off": 2.5, "n": 60},
        "Charlotte Hornets": {"rtg": -2.5, "off": -2.5, "n": 60},
    },
    "n_matches": 600, "holes": [],
}

TABLE = """| Compétition & Match | Horaire | 1 (ML) | 2 (ML) | 1 (1X2) | X (1X2) | 2 (1X2) | Handicap / Total 1 | Handicap / Total 2 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **USA, NBA**<br>Toronto Raptors vs New York Knicks | Demain 01:30 (#20071) | 2.42 | 1.55 | 2.60 | 9.60 | 1.63 | 1.85 | 1.89 |
| **USA, NBA**<br>Minnesota Timberwolves vs Portland Trail Blazers | Demain 02:00 (#20105) | 1.64 | 2.23 | 1.74 | 9.60 | 2.39 | 1.91 | 1.83 |
| **USA, NBA**<br>San Antonio Spurs vs Detroit Pistons | Demain 02:00 (#20089) | 1.22 | 4.10 | 1.28 | 9.80 | 4.70 | 1.84 | 1.90 |
| **USA, NBA**<br>LA Clippers vs Utah Jazz | Demain 04:30 (#20104) | 1.41 | 2.85 | 1.48 | 9.80 | 3.10 | 1.90 | 1.84 |
| **USA, NBA**<br>Los Angeles Lakers vs Charlotte Hornets | Demain 05:00 (#20106) | 1.33 | 3.25 | 1.40 | 9.60 | 3.60 | 1.90 | 1.84 |
"""


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok)))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST F01 — capture basket (ML + Kinshasa)")
    print("=" * 70)

    original = icb.engine_basket.load
    icb.engine_basket.load = lambda path=None: BLOB
    try:
        now = icb.datetime(2026, 11, 17, 20, 0, tzinfo=icb.TZ)
        parsed = icb.parse_markdown(TABLE + TABLE, now=now)
        matchs = parsed["captures"][0]["matchs"]
        check("cbc.n_matchs", parsed["n_matchs"] == 5, str(parsed["n_matchs"]))
        check("cbc.doublons", any("doublon_ignore" in w for w in parsed["warnings"]))
        first = matchs[0]
        check("cbc.game_id", first["game_id"] == "20071")
        check("cbc.equipes", first["dom"] == "Toronto Raptors"
              and first["ext"] == "New York Knicks")
        check("cbc.ml", first["ml_home"] == 2.42 and first["ml_away"] == 1.55)
        check("cbc.kinshasa", first["date"] == "2026-11-18T01:30:00+01:00",
              str(first["date"]))
        check("cbc.1x2_non_utilise", first["diag"]["1x2"]["utilise"] is False
              and first["diag"]["1x2"]["draw"] == 9.6)
        check("cbc.handi_sans_ligne", "handicap_total_sans_ligne" in first["holes"])
        check("cbc.handi_non_utilise", first["diag"]["handicap_total"]["utilise"] is False)
        a = first["analyse"]
        check("cbc.analyse_p", a["p_home"] is not None and 0.0 < a["p_home"] < 1.0,
              str(a["p_home"]))
        check("cbc.analyse_ev", a["ev_home"] is not None
              and abs(a["ev_home"] - (a["p_home"] * 2.42 - 1)) < 0.001)

        sale = TABLE.replace("| 2.42 | 1.55 |", "|  | 1.0 |", 1)
        mauvaise = icb.parse_markdown(sale, now=now)["captures"][0]["matchs"][0]
        check("cbc.ml_vide", mauvaise["ml_home"] is None)
        check("cbc.ml_invalide", mauvaise["ml_away"] is None)
        check("cbc.trous_declares", "ml_home_absente" in mauvaise["holes"]
              and "ml_away_absente" in mauvaise["holes"])
        check("cbc.pas_d_invention", mauvaise["analyse"]["ev_home"] is None)
    finally:
        icb.engine_basket.load = original

    ok = all(v for _, v in CHECKS)
    print("=" * 70)
    print(f"RESULTAT: {sum(v for _, v in CHECKS)}/{len(CHECKS)} " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
