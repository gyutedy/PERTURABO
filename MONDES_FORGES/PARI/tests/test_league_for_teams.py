#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""league_for_teams — ligue retrouvee par les equipes quand l'en-tete est generique."""
from __future__ import annotations

import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD / "F00_RADAR" / "CODEBASE"))
import capteurs  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


def run_checks():
    PASS.clear()
    N[0] = 0
    check("middlesbrough", capteurs.league_for_teams("Middlesbrough FC", "Swansea City") == "E1")
    check("bristol", capteurs.league_for_teams("Bristol City", "Wrexham AFC") == "E1")
    check("cardiff", capteurs.league_for_teams("Cardiff City", "Preston North End") == "E1")
    check("charlton", capteurs.league_for_teams("Charlton Athletic", "Lincoln City") == "E1")
    check("inconnu", capteurs.league_for_teams("Equipe X", "Equipe Y") is None)
    check("mapping present", (WORLD / "ARCHIVUM" / "teams" / "league_by_team.json").exists())
    print(f"league_for_teams : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_league_for_teams():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
