#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data_view — marches calcules mais non retenus, avec motif."""
from __future__ import annotations

import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD / "ORCHESTRATOR" / "CODEBASE"))
import data_view as dv  # noqa: E402

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
    sel = lambda m, s, ev, **kw: {"marche": m, "selection": s, "cote": 2.0,
                                  "ev": ev, "verdict": "VALUE", **kw}
    row = {"id": "M1", "match": "A vs B", "bucket": "HAUTE", "score_commun": 8.0,
           "top3": [sel("1X2", "1", 0.12)]}
    preds = {"seuil_ev_applique": 0.08, "predictions": [{
        "id": "M1", "match": "A vs B", "selections": [
            sel("1X2", "1", 0.12), sel("1X2", "X", -0.05),
            sel("MT_OU_1.5", "ht_o1.5", 0.027),
            sel("OU_2.5", "u2.5", 0.10, scorer_eligible=False,
                scorer_score=0.4, scorer_seuil=0.5),
        ]}]}
    ec = dv.marches_ecartes(row, preds)
    check("3 ecartes", len(ec) == 3, str(ec))
    check("retenu absent", not any("1X2 1 a" in x for x in ec))
    check("motif negatif", any("EV -5.0% <= 0" in x for x in ec), str(ec))
    check("motif seuil", any("EV +2.7% < seuil 8%" in x for x in ec), str(ec))
    check("motif scorer", any("scorer 0.4 < 0.5" in x for x in ec), str(ec))
    body = dv.render_fiche(1, {"matchs": [row]}, "", {}, {}, predictions=preds)
    check("section dans fiche", "MARCHES CALCULES MAIS NON RETENUS" in body)
    print(f"data_ecartes : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_data_ecartes():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
