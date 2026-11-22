#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_ingest — E2E offline : contrat, marques diagnostic, trous."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD / "F00_RADAR" / "CODEBASE"))

import winner_ingest as wi  # noqa: E402

PASS, N = [], [0]


def check(name, cond):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name)
        raise AssertionError(name)


SLATE = {
    "contract": "vanus.slate.v1", "index": "winner_basket", "sport": "basket",
    "generated_at": "2026-11-22T10:00:00+00:00", "source": "x",
    "matches": [
        {"match_key": "atlantahawks_detroitpistons", "home": "Atlanta Hawks",
         "away": "Detroit Pistons", "kickoff": "21:30", "source_event_id": "20064",
         "odds": {"ml_1": 2.08, "ml_2": 1.73, "total_line": 226.5,
                  "total_under": 1.80, "total_over": 1.87},
         "diagnostic_only": [], "holes": []},
        {"match_key": None, "home": None, "away": None, "kickoff": None,
         "source_event_id": None, "odds": {}, "diagnostic_only": [], "holes": []},
    ],
    "holes": [],
}


def run_checks():
    PASS.clear()
    N[0] = 0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(SLATE, f)
        p_basket = f.name
    view = wi.ingest("basket", path=p_basket)
    check("vue indexee", len(view["matches"]) == 1)
    m = view["matches"]["atlantahawks_detroitpistons"]
    check("odds transmises telles quelles", m["odds"]["ml_1"] == 2.08
          and m["odds"]["total_line"] == 226.5)
    check("match_key absent -> trou", "match_key_absent" in view["holes"])
    check("aucune probabilite produite", not any("p_" in k or "prob" in k
          for k in json.dumps(view).lower().split('"')))
    target = wi.save(view, "basket", path=p_basket.replace("slate_", "latest_"))
    check("sauvegarde ecrite", os.path.exists(target))

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"contract": "autre.v9", "matches": []}, f)
        p_bad = f.name
    bad = wi.ingest("basket", path=p_bad)
    check("contrat inattendu = jete", bad["matches"] == {}
          and "contrat_inattendu" in bad["holes"])

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"contract": "vanus.slate.v1", "sport": "foot", "matches": []}, f)
        p_cross = f.name
    cross = wi.ingest("basket", path=p_cross)
    check("cross-sport refuse", "sport_differents:foot" in cross["holes"])

    absent = wi.ingest("basket", path=os.path.join(tempfile.mkdtemp(), "inexistant.json"))
    check("slate absent = trou", absent["matches"] == {} and "slate_absent" in absent["holes"])

    diag = json.loads(json.dumps(SLATE))
    diag["matches"][0]["diagnostic_only"] = ["hsh_first"]
    diag["matches"][0]["odds"]["hsh_first"] = 3.10
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({**diag, "sport": "foot"}, f)
        p_diag = f.name
    dv = wi.ingest("foot", path=p_diag)
    check("diagnostic conserve et marque",
          "hsh_first" in list(dv["matches"].values())[0]["diagnostic_only"])

    print(f"winner_ingest : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_ingest():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
