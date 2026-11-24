#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HT Under/Over 1.5 — matrice mi-temps -> proba -> cote Winner -> EV."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F00_RADAR", "F02_BREACHER", "F03_FORGEWARD", "F01_SENTINEL"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import breacher  # noqa: E402
import forgeward  # noqa: E402
import market_scorer  # noqa: E402
import winner_vision as wv  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "capture_llm_ht", WORLD / "ORCHESTRATOR" / "LISTEN" / "capture_llm.py")
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


TXT = """Bristol City - Wrexham AFC
Today 20:45 | #159
1X2 2.45/3.25/2.92
Ligne 2.5
Under 1.67 / Over 2.17
HT Under 1.29 / HT Over 2.77
HSH 3.10/3.00/2.02"""


def run_checks():
    PASS.clear()
    N[0] = 0
    slate = wv.build(TXT, "foot")
    o = slate["matches"][0]["odds"]
    check("slate HT", o.get("ht_u1.5") == 1.29 and o.get("ht_o1.5") == 2.77, str(o))
    md = cl.markdown(slate, "foot")
    check("tableau HT", "HT Moins 1.5" in md and "HT Plus 1.5" in md and "1.29" in md)

    stub = {"mj": 12, "marques": 18, "encaisses": 10, "marques_mt1": 8, "encaisses_mt1": 4}
    m = {"id": "M1", "dom": "A", "ext": "B",
         "cotes": {"ht_u1.5": 1.29, "ht_o1.5": 2.77, "1": 2.45, "X": 3.25, "2": 2.92},
         "stats": {"dom": dict(stub), "ext": dict(stub)}}
    avg = {"buts_dom_moy": 1.6584, "buts_ext_moy": 1.2486, "rho": -0.02,
           "bonus_domicile": 1.1213, "bonus_exterieur": 0.8787,
           "part_mt1_ligue": 0.4603, "params": "fitted", "league_code": "E1"}
    a = breacher.analyse_match(m, avg)
    u = a["probas"].get("ht_u1.5")
    check("proba HT", u is not None and 0 < u < 1)
    check("somme HT", abs(a["probas"]["ht_u1.5"] + a["probas"]["ht_o1.5"] - 1) < 1e-9)

    pool = {"seuil_ev_top5": 0.03, "seuil_ev_exotique": 0.08,
            "mise_max_pct_bankroll": 0.05, "mise_max_pct_exotique": 0.03,
            "kelly_fraction": 0.125}
    rec = forgeward.predict_match(m, a, pool, "top5")
    sels = [s for s in rec["selections"] if s["marche"] == "MT_OU_1.5"]
    check("selection MT_OU_1.5", len(sels) == 2, str([s["selection"] for s in sels]))
    check("EV calculee", all(s.get("ev") is not None and s.get("p_fair") for s in sels))
    check("groupe scorer", "MT_OU_1.5" in market_scorer.GROUP_KEYS)

    print(f"ht_market : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_ht_market():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
