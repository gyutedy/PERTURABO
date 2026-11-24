#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_vision — E2E offline : parsing, gardes V1-V4, LLM generique, jamais un p."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
for d in ("F01_SENTINEL", "F00_RADAR", "ORCHESTRATOR"):
    sys.path.insert(0, str(WORLD / d / "CODEBASE"))

import winner_vision as wv  # noqa: E402
import llm_vision as lv  # noqa: E402

PASS, N = [], [0]


def check(name, cond):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name)
        raise AssertionError(name)


TXT_BASKET = """Atlanta Hawks - Detroit Pistons
Today 21:30 | #20064
ML 2.08/1.73
Total 226.5
Under 1.80 / Over 1.87"""

TXT_BASKET_B = TXT_BASKET

TXT_BASKET_MAUVAIS = TXT_BASKET.replace("2.08", "2.80")

TXT_FOOT = """Erzurumspor FK - Goztepe Izmir
Today 11:30 | #401
1X2 2.57/3.00/2.57
2.5: 1.60/2.15
HSH 3.10/3.00/2.02"""


def run_checks():
    PASS.clear()
    N[0] = 0
    blob = wv.build(TXT_BASKET, "basket")
    m = blob["matches"][0]
    check("basket match_key", m["match_key"] == "atlantahawks_detroitpistons")
    check("basket ML+total+U/O", m["odds"] == {"ml_1": 2.08, "ml_2": 1.73,
          "total_line": 226.5, "total_under": 1.80, "total_over": 1.87})
    check("basket zero trou", m["holes"] == [] and blob["holes"] == [])
    check("jamais un p", not any("p_" in k or "prob" in k
          for k in json.dumps(blob).lower().split('"')))

    ok = wv.build(TXT_BASKET, "basket", text_b=TXT_BASKET_B)
    check("V1 concordance = aucun trou", ok["holes"] == [])
    ko = wv.build(TXT_BASKET, "basket", text_b=TXT_BASKET_MAUVAIS)
    check("V1 divergence = transcription_instable",
          any(h.startswith("transcription_instable") for h in ko["holes"]))
    check("V1 jamais de moyenne", ko["matches"][0]["odds"]["ml_1"] == 2.08)

    bad = """A - B
ML 0.95/1.73
Total 999.5
Under 1.80 / Over 1.87"""
    bb = wv.build(bad, "basket")["matches"][0]
    check("V2 cote <= 1.0 -> null + trou", bb["odds"]["ml_1"] is None
          and any("cote_hors_bornes" in h for h in bb["holes"]))
    check("V2 ligne hors [180,320] -> trou", bb["odds"]["total_line"] is None
          and any("ligne_hors_bornes" in h for h in bb["holes"]))

    fb = wv.build(TXT_FOOT, "foot")["matches"][0]
    txt_uo = ("Team A - Team B\nToday 20:45 | #1\n1X2 2.10/3.40/3.50\n"
              "Ligne 2.5\nUnder 1.60 / Over 2.15\nHSH 3.10/3.00/2.02")
    uo = wv.build(txt_uo, "foot")["matches"][0]["odds"]
    check("ligne + Under/Over tokens", uo.get("total_line") == 2.5
          and uo.get("under_2_5") == 1.60 and uo.get("over_2_5") == 2.15)
    check("foot 1X2+OU parse", fb["odds"]["home"] == 2.57 and fb["odds"]["under_2_5"] == 1.60)
    check("foot HSH diagnostic_only", set(fb["diagnostic_only"]) ==
          {"hsh_first", "hsh_equal", "hsh_second"} and fb["odds"]["hsh_second"] == 2.02)
    grid = """A - B
1X2 1.10/1.10/1.10
2.5: 1.60/2.15
HSH 3.10/3.00/2.02"""
    gb = wv.build(grid, "foot")["matches"][0]
    check("V3 grille incoherente", "grille_incoherente" in gb["holes"])

    empty = wv.build("ML 2.00/1.90 sans equipes", "basket")
    check("V4 bloc vide = trou declare", empty["matches"] == []
          and "equipes_absentes" in empty["holes"])

    src = Path(wv.__file__).read_text(encoding="utf-8")
    check("heresie #11", "perturabo" not in src.lower() and "breacher" not in src.lower())

    many = "\n\n".join("Team%d - Team%d\nML 2.0%d/1.7%d\nTotal 22%d.5\nUnder 1.80 / Over 1.87"
                       % (i, i + 100, i % 10, i % 10, 0 + i % 9) for i in range(12))
    check("plus de 10 matchs lus", len(wv.build(many, "basket")["matches"]) == 12)

    for k in (lv.KEY_VAR, lv.URL_VAR, lv.MODEL_VAR):
        os.environ.pop(k, None)
    old_world = lv.WORLD
    lv.WORLD = tempfile.mkdtemp(prefix="pari-llm-vide-")
    try:
        cfg = lv.config()
        check("LLM config absente = 3 trous", cfg[3] == ["llm_key_absent", "llm_url_absent", "llm_model_absent"])
    finally:
        lv.WORLD = old_world
    tmp = tempfile.mkdtemp(prefix="pari-llm-")
    with open(os.path.join(tmp, "env_pari"), "w", encoding="utf-8") as f:
        f.write("PARI_WINNER_LLM_KEY=test-key\nPARI_WINNER_LLM_BASE_URL=https://example.invalid/v1\n"
                "PARI_WINNER_LLM_MODEL=test-model\n")
    old_world = lv.WORLD
    lv.WORLD = tmp
    try:
        url, model, key, holes = lv.config()
        check("LLM config lue depuis env_pari", url.endswith("/v1") and model == "test-model"
              and key == "test-key" and holes == [])
        check("LLM cle jamais dans le slate", "test-key" not in json.dumps(blob))
    finally:
        lv.WORLD = old_world
        for k in (lv.KEY_VAR, lv.URL_VAR, lv.MODEL_VAR):
            os.environ.pop(k, None)

    print(f"winner_vision : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_vision():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
