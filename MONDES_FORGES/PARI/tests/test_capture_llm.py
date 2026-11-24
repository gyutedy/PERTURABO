#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capture_llm — fusion photo -> LLM -> tableau Winner (sans reseau)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
_LISTEN = WORLD / "ORCHESTRATOR" / "LISTEN"
sys.path.insert(0, str(_LISTEN))

_spec = importlib.util.spec_from_file_location("capture_llm_mod", _LISTEN / "capture_llm.py")
cl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cl)

PASS, N = [], [0]


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


SLATE = {
    "matches": [{
        "home": "Team A", "away": "Team B", "kickoff": "20:00", "kickoff_raw": "Today 20:00",
        "source_event_id": "123",
        "odds": {"home": 2.10, "draw": 3.40, "away": 3.50, "under_2_5": 1.80, "over_2_5": 2.00,
                 "hsh_first": 3.10, "hsh_equal": 3.00, "hsh_second": 2.02,
                 "ml_1": 2.10, "ml_2": 1.80},
    }],
    "holes": [],
}


def run_checks():
    PASS.clear()
    N[0] = 0
    check("sport depuis cmd", cl.sport_of("/capture foot") == "foot"
          and cl.sport_of("/capture basket") == "basket")
    foot = cl.markdown(SLATE, "foot")
    check("entete foot", "| 1 | X | 2 | Moins | Plus | 1st | Égal | 2nd |" in foot)
    foot_line = cl.markdown({**SLATE, "matches": [{**SLATE["matches"][0],
        "odds": {**SLATE["matches"][0]["odds"], "total_line": 2.5}}]}, "foot")
    check("ligne 2.5 dans entete", "| Moins 2.5 | Plus 2.5 |" in foot_line)
    check("ligne foot", "Team A vs Team B" in foot and "Aujourd'hui 20:00 (#123)" in foot
          and "2.1" in foot and "1.8" in foot)
    basket = cl.markdown(SLATE, "basket")
    check("entete basket", "1 (ML)" in basket and "2 (ML)" in basket)
    check("ligne basket", "Demain 20:00" not in basket and "Aujourd'hui 20:00" in basket)
    fake = {"home": "A - B", "away": "", "kickoff_raw": "Tomorrow 21:00", "kickoff": "21:00",
            "source_event_id": "9", "odds": {"1": 2.0}}
    check("jour demain", "Demain 21:00" in cl.markdown({"matches": [fake]}, "foot"))
    src = (_LISTEN / "capture_llm.py").read_text(encoding="utf-8")
    check("repli OCR", "capture_telegram.md" in src and "photo_absente" in src)
    check("pas de mise auto", "set_tickets" not in src and "tickets_enabled" not in src
          and "mise_fc" not in src)

    print(f"capture_llm : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_capture_llm():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
