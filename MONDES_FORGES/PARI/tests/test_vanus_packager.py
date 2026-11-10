#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4 — packager greffe vanus_gate. Veto jackpot, flag alarme. Jamais un p. Gel intact."""

import ast
import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))

import moteur_flag  # noqa: E402
import packager  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F05_PACKAGER", "CODEBASE", "packager.py"), encoding="utf-8").read()


def _wf():
    return open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()


def _blob(niveau="isole", selection="home", n=1, found=1):
    indexes = {
        "predictlix": {"pick": "home", "model_pct": None, "at": "2026-11-09T10:00:00Z"},
        "dailysportpick": None,
        "metapred": None,
        "footinsights": None,
        "besoccer": None,
        "vitibet": None,
    }
    if n >= 2:
        indexes["metapred"] = {"pick": "home", "model_pct": None, "at": "2026-11-09T12:00:00Z"}
    key = "arsenal_chelsea_2026-11-09"
    return {
        "contract": "vanus.signal.v1",
        "generated_at": "2026-11-09T12:00:00Z",
        "slate_date": "2026-11-09",
        "indexes_vus": ["predictlix"],
        "matches": {
            key: {
                "match_key": key,
                "competition": "Premier League",
                "home": "Arsenal",
                "away": "Chelsea",
                "kickoff": "2026-11-09T20:00:00Z",
                "indexes": indexes,
                "consensus": {
                    "selection": selection,
                    "n": n,
                    "found": found,
                    "niveau": niveau,
                    "agreeing": ["predictlix"] if n == 1 else ["metapred", "predictlix"],
                },
                "marches": {},
                "reference": {"sharp": None, "sharp_issue": None, "sharp_marche": None, "source": None, "at": None},
                "couverture": {"n_index": 6, "n_presents": found, "n_marches": 0, "niveaux": "faible"},
                "holes": ["cotes_ou_2_5"],
            }
        },
        "holes": [],
    }


def _preds():
    return {
        "predictions": [
            {
                "id": "M1",
                "match": "Arsenal vs Chelsea",
                "date": "2026-11-09",
                "verdict": "GO",
                "selections": [
                    {"marche": "1X2", "selection": "1", "selection_label": "Victoire Domicile",
                     "cote": 1.90, "p_modele": 0.58, "ev": 0.102, "verdict": "VALUE", "mise_units": 1.2},
                    {"marche": "1X2", "selection": "2", "selection_label": "Victoire Extérieur",
                     "cote": 4.20, "p_modele": 0.28, "ev": 0.176, "verdict": "VALUE", "mise_units": 0.8},
                    {"marche": "1X2", "selection": "X", "cote": 3.50, "p_modele": 0.22, "ev": -0.23,
                     "verdict": "NO_BET", "mise_units": 0},
                ],
            },
            {
                "id": "M2",
                "match": "Barca vs Madrid",
                "date": "2026-11-09",
                "verdict": "NO_BET",
                "selections": [],
            },
        ],
        "combines": [
            {
                "jambes": [
                    {"match_id": "M1", "selection": "2", "cote": 4.20, "p_modele": 0.28},
                    {"match_id": "M2", "selection": "1", "cote": 2.10, "p_modele": 0.50},
                ],
                "cote_totale": 8.82,
                "ev_combine": 0.12,
                "mise_units": 0.4,
            }
        ],
    }


def _analysis():
    return {"analyses": [{"id": "M1", "data_quality": {"niveau": "haute"}}]}


def main():
    print("=" * 70)
    print("TEST V4 — packager vanus")
    print("=" * 70)

    src = _src()
    check("pk.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("pk.pas_tickets", "set_tickets" not in src and "tickets_enabled" not in src)
    check("pk.pas_poisson", "score_matrix" not in src and "lambda_dom" not in src)
    check("pk.pas_workflow", "vanus_gate" not in _wf())
    ast.parse(src)
    check("pk.ast", True)

    preds = _preds()
    p1 = preds["predictions"][0]["selections"][0]["p_modele"]
    pack_jk = packager.build_pack(preds, _analysis(), None, vanus_blob=_blob("jackpot", "home", n=6, found=6))
    sels = [x["selection"] for x in pack_jk["top_picks"]]
    check("pk.jackpot_drop_2", "2" not in sels, str(sels))
    check("pk.jackpot_keep_1", "1" in sels, str(sels))
    check("pk.jackpot_no_bet", any(n.get("raison") == "vanus_jackpot" for n in pack_jk["no_bet"]), str(pack_jk["no_bet"]))
    check("pk.jackpot_combo_drop", pack_jk["combines"] == [], str(pack_jk["combines"]))
    check("pk.jackpot_p_intact", preds["predictions"][0]["selections"][0]["p_modele"] == p1)
    check("pk.jackpot_pick_p", pack_jk["top_picks"][0]["p_modele"] == 0.58)
    check("pk.jackpot_nb_veto", pack_jk["metriques"]["nb_vanus_veto"] == 1)

    pack_al = packager.build_pack(_preds(), _analysis(), None, vanus_blob=_blob("alarme", "home", n=2, found=2))
    flags = pack_al["top_picks"][0].get("vanus_flags")
    check("pk.alarme_flag", "vanus_alarme" in (flags or []), str(flags))
    check("pk.alarme_keep_2", any(x["selection"] == "2" for x in pack_al["top_picks"]))
    check("pk.alarme_p", pack_al["top_picks"][0]["p_modele"] in (0.58, 0.28))

    pack_is = packager.build_pack(_preds(), _analysis(), None, vanus_blob=_blob("isole", "home", n=1, found=1))
    check("pk.isole_keep", len(pack_is["top_picks"]) == 2, str(len(pack_is["top_picks"])))
    check("pk.isole_pass", pack_is["top_picks"][0].get("vanus_action") == "pass")

    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    try:
        pack_sk = packager.build_pack(_preds(), _analysis(), None, vanus_blob=_blob("jackpot", "home", n=6, found=6))
        check("pk.skip_keep", len(pack_sk["top_picks"]) == 2, str(len(pack_sk["top_picks"])))
        check("pk.skip_hole", "skip" in (pack_sk.get("vanus_holes") or []), str(pack_sk.get("vanus_holes")))
    finally:
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    check("pk.match_miss_barca", "vanus_match" in (pack_jk.get("vanus_holes") or []), str(pack_jk.get("vanus_holes")))
    reasons = [n.get("raison") for n in pack_jk["no_bet"]]
    check("pk.no_bet_m2", "aucune cote fournie" in reasons)

    check("pk.gel", moteur_flag.tickets_enabled() is False)
    check("pk.src_intact", preds["predictions"][0]["selections"][1]["p_modele"] == 0.28)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V4 packager : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
