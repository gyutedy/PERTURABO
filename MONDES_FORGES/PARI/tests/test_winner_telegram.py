#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke /winner : 27 commandes, relais Telegram, lecture seule, jamais un p."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F00_RADAR", "F01_SENTINEL", "ORCHESTRATOR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import workflow  # noqa: E402
import importlib.util  # noqa: E402

_LISTEN = WORLD / "ORCHESTRATOR" / "LISTEN"
_spec = importlib.util.spec_from_file_location("parse_listen", _LISTEN / "parse.py")
parse_listen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_listen)
_spec2 = importlib.util.spec_from_file_location("winner_telegram_mod", _LISTEN / "winner_telegram.py")
winner_telegram_mod = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(winner_telegram_mod)

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
    check("cmds_27", len(workflow.CMDS) == 27, str(len(workflow.CMDS)))
    check("winner_enregistre", "winner" in workflow.CMDS)

    tmp = tempfile.mkdtemp(prefix="pari-winner-tg-")
    slate = {
        "contract": "vanus.slate.v1", "index": "winner_vision", "sport": "basket",
        "generated_at": "2026-11-22T12:00:00Z", "source": "test",
        "matches": [{"match_key": "atlantahawks_detroitpistons",
                     "home": "Atlanta Hawks", "away": "Detroit Pistons",
                     "kickoff": "21:30", "source_event_id": "20064",
                     "odds": {"ml_1": 2.08, "ml_2": 1.73, "total_line": 226.5,
                              "total_under": 1.80, "total_over": 1.87},
                     "diagnostic_only": [], "holes": []}],
        "holes": [],
    }
    target = os.path.join(tmp, "slate_basket.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(slate, f)

    old_env = os.environ.get("PARI_WINNER_SLATE_PATH")
    os.environ["PARI_WINNER_SLATE_PATH"] = target
    told = []
    old_tell = workflow.tell
    workflow.tell = lambda t: told.append(t)
    try:
        workflow.cmd_winner({}, "basket")
        workflow.cmd_winner({}, "foot")
    finally:
        workflow.tell = old_tell
        if old_env is None:
            os.environ.pop("PARI_WINNER_SLATE_PATH", None)
        else:
            os.environ["PARI_WINNER_SLATE_PATH"] = old_env
    txt = "\n".join(told)
    check("winner_basket_affiche", "WINNER BASKET" in txt and "2.08" in txt, txt[:120])
    check("winner_devig_rappel", "devig F03 obligatoire" in txt)
    check("winner_pas_p", "p_modele" not in txt and "probabilite" not in txt)
    check("winner_foot_cross_sport", "cross" in txt.lower() or "sport_differents" in txt
          or "Aucun match" in txt, txt[-160:])

    parse_src = (WORLD / "ORCHESTRATOR" / "LISTEN" / "parse.py").read_text(encoding="utf-8")
    js_src = (WORLD / "ORCHESTRATOR" / "LISTEN" / "src" / "index.js").read_text(encoding="utf-8")
    schema = json.loads((WORLD / "CONTRACTS" / "schema_listen.json").read_text(encoding="utf-8"))
    check("relais_parse", '"winner"' in parse_src)
    check("relais_worker", '"winner"' in js_src)
    check("relais_schema", "winner" in schema["properties"]["cmd"]["pattern"])

    upd = {"update_id": 1, "message": {"message_id": 2,
           "chat": {"id": 123}, "caption": "/winner foot",
           "photo": [{"file_id": "abc", "file_size": 10, "width": 10}]}}
    parsed = parse_listen.parse_update(upd, "123")
    check("photo_winner_transmise", parsed.get("ok") and parsed.get("cmd") == "/winner foot"
          and parsed.get("capture_file_id") == "abc", str(parsed)[:200])
    check("sport_depuis_cmd", winner_telegram_mod.sport_of("/winner foot") == "foot"
          and winner_telegram_mod.sport_of("/winner") == "basket")
    yml = (WORLD.parent.parent / ".github" / "workflows" / "pari_listen.yml").read_text(encoding="utf-8")
    check("yml_etape_vision", "winner_telegram.py" in yml and "PARI_WINNER_LLM_KEY" in yml)
    envp = (WORLD.parent.parent / ".github" / "scripts" / "write_env_pari.py").read_text(encoding="utf-8")
    check("env_pari_keys", "PARI_WINNER_LLM_KEY" in envp and "PARI_WINNER_LLM_MODEL" in envp)

    print(f"winner_telegram : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_telegram():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
