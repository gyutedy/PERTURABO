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

    print(f"paper_trader : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_paper_trader():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
