#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_trader — journal des paris simules : EV, zero ticket, zero duplication."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD / "F06_TRACKER" / "CODEBASE"))

import paper_trader as pt  # noqa: E402

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


PM = {
    "generated_at": "2026-11-22T18:00:00Z",
    "analyses": [{
        "match_key": "a_b", "home": "A", "away": "B", "p_modele": {"home": .22, "draw": .30, "away": .48},
        "ev": {"home": .42, "draw": .16, "away": -.25},
        "cote": {"home": 6.50, "draw": 3.90, "away": 1.55},
        "ou25": {"p_modele": {"under_2_5": .62, "over_2_5": .38},
                 "cote": {"under_2_5": 1.63, "over_2_5": 2.10},
                 "ev": {"under_2_5": .018, "over_2_5": -.21}},
    }],
}


def run_checks():
    PASS.clear()
    N[0] = 0
    tmp = tempfile.mkdtemp(prefix="pari-paper-")
    src = os.path.join(tmp, "pmodel_foot.json")
    out = os.path.join(tmp, "paper_trades.json")
    with open(src, "w", encoding="utf-8") as f:
        json.dump(PM, f)
    ledger, added = pt.record("foot", source=src, out=out)
    check("2 paris EV >= 3%", len(added) == 2, str([b["selection"] for b in added]))
    check("pas de ticket", all(b["ticket"] is False for b in added))
    check("aucun HSH", not any("hsh" in b["marche"].lower() for b in added))
    check("cote et p conserves", added[0]["cote"] == 6.50 and added[0]["p_modele"] == .22)
    check("ledger en attente", pt.report(ledger)["en_attente"] == 2)
    _, again = pt.record("foot", source=src, out=out)
    check("pas de duplication", len(again) == 0)
    _, strict = pt.record("foot", source=src, out=os.path.join(tmp, "strict.json"), ev_floor=.10)
    check("seuil EV", len(strict) == 2, str([b["selection"] for b in strict]))
    stored = json.load(open(out, encoding="utf-8"))
    check("contrat", stored["contract"] == "pari.paper_trades.v1")

    csv_dir = tempfile.mkdtemp(prefix="pari-paper-csv-")
    with open(os.path.join(csv_dir, "uk_SP1_2627.csv"), "w", encoding="utf-8") as f:
        f.write("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,B365CH,B365CD,B365CA,B365C>2.5,B365C<2.5\n")
        f.write("SP1,22/11/2026,Getafe,Ath Madrid,1,0,2.10,3.40,3.50,2.00,1.80\n")
    params_path = os.path.join(tmp, "dc_params.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump({"leagues": {"SP1": {"params": "fitted", "mu": .2, "home_adv": .1, "rho": -.13,
                   "teams": {"Getafe": {"n": 30}, "Ath Madrid": {"n": 30}}}}}, f)
    ledger2 = {"contract": "pari.paper_trades.v1", "bets": [
        {"id": "b1", "home": "Getafe CF", "away": "Atletico Madrid", "marche": "1X2",
         "selection": "1", "cote": 6.50, "ev": .42, "resultat": "EN_ATTENTE"},
        {"id": "b2", "home": "Getafe CF", "away": "Atletico Madrid", "marche": "OU_2.5",
         "selection": "under", "cote": 1.63, "ev": .018, "resultat": "EN_ATTENTE"},
        {"id": "b3", "home": "Getafe CF", "away": "Atletico Madrid", "marche": "OU_2.5",
         "selection": "over", "cote": 2.10, "ev": .01, "resultat": "EN_ATTENTE"},
    ]}
    led = os.path.join(tmp, "regle.json")
    with open(led, "w", encoding="utf-8") as f:
        json.dump(ledger2, f)
    res = pt.settle(csv_dir=csv_dir, out=led, params_path=params_path)
    done = json.load(open(led, encoding="utf-8"))["bets"]
    check("settle 3 paris", res["regles"] == 3, str(res))
    check("score 1-0 -> G sur 1 et under", done[0]["resultat"] == "G"
          and done[1]["resultat"] == "G" and done[2]["resultat"] == "P",
          str([b.get("resultat") for b in done]))
    check("score lu dans CSV", done[0]["score"] == "1-0")
    check("CLV proxy present", done[0].get("clv") is not None
          and done[0].get("clv_source") == "proxy_football_data", str(done[0].get("clv")))

    print(f"paper_trader : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_paper_trader():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
