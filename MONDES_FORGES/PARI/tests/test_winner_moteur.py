#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moteur + cotes Winner reelles : devig, marges, zero p, zero ticket."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F00_RADAR", "F01_SENTINEL", "F02_BREACHER", "F03_FORGEWARD", "ORCHESTRATOR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import devig  # noqa: E402
import market_scorer  # noqa: E402
import moteur_flag  # noqa: E402
import winner_ingest  # noqa: E402

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
    for sport, marche, keys in (
        ("foot", "1X2", ("home", "draw", "away")),
        ("foot", "OU_2.5", ("under_2_5", "over_2_5")),
        ("basket", "ML", ("ml_1", "ml_2")),
        ("basket", "TOTAL", ("total_under", "total_over")),
    ):
        view = winner_ingest.ingest(sport)
        if not view["matches"]:
            continue
        ok = 0
        marges = []
        for m in view["matches"].values():
            cotes = [m["odds"].get(k) for k in keys]
            if any(c is None or c <= 1 for c in cotes):
                continue
            group = dict(zip(("1", "X", "2") if len(keys) == 3 else ("a", "b"), cotes))
            d = devig.multiplicative(group)
            if not d["ok"]:
                continue
            s = d["S"]
            if s > 1:
                if not all(d["fair_odds"][k] > d["cotes"][k] for k in d["cotes"]):
                    raise AssertionError("invariant devig casse: " + sport + "/" + marche)
            ok += 1
            marges.append(s - 1)
        check("devig_%s_%s" % (sport, marche), ok > 0, "%d matchs" % ok)
        if marges:
            print("  marge moyenne %s/%s : %.2f%% (n=%d)" %
                  (sport, marche, 100 * sum(marges) / len(marges), len(marges)))

    fv = winner_ingest.ingest("foot")
    if fv["matches"]:
        diag = set()
        for m in fv["matches"].values():
            diag.update(m.get("diagnostic_only") or [])
        check("HSH diagnostic_only", diag == {"hsh_first", "hsh_equal", "hsh_second"}, str(diag))
        hsh = [m["odds"]["hsh_second"] for m in fv["matches"].values()
               if m["odds"].get("hsh_second") is not None]
        check("HSH template identique", len(set(hsh)) == 1, str(set(hsh)))
        hsh_m = market_scorer.overround({"a": 3.10, "b": 3.00, "c": 2.02})
        x2_m = market_scorer.overround({"a": 1.63, "b": 4.30, "c": 4.70})
        check("marge HSH superieure au 1X2", hsh_m > x2_m,
              "HSH %.2f%% vs 1X2 %.2f%%" % (100 * hsh_m, 100 * x2_m))

    blob = json.dumps({"foot": fv})
    check("aucune probabilite produite", "p_modele" not in blob and "prob" not in blob.lower())
    check("moteurs gele", moteur_flag.tickets_enabled() is False
          and moteur_flag.tickets_enabled(str(WORLD / "config" / "moteur_basket.json")) is False)
    check("aucun ticket Winner", not (WORLD / "F05_PACKAGER" / "OUT" / "winner_tickets.json").exists())

    print(f"winner_moteur : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_moteur():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
