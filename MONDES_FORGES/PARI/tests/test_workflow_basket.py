#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cahier B — commutation Telegram. Foot maitre, gels independants, 25 cles CMDS."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("ORCHESTRATOR", "F02_BREACHER"):
    sys.path.insert(0, os.path.join(WORLD, d, "CODEBASE"))

import moteur_sport  # noqa: E402
import moteur_flag  # noqa: E402
import workflow  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


ORIGINAL = ["start", "capture", "bankroll", "budget", "surticket", "combos", "systeme",
            "marches", "marchés", "valider-1", "valider1", "valider-2", "valider2",
            "approve", "data", "radar", "pack", "match", "status", "roi", "stop",
            "modele", "gel", "vanus"]


def main():
    print("=" * 70)
    print("TEST Cahier B — /sport /basket /gel /modele /valider2")
    print("=" * 70)

    keys = list(workflow.CMDS.keys())
    check("b.cmds_original_intact", keys[:len(ORIGINAL)] == ORIGINAL, str(keys[:3]))
    check("b.cmds_ajout_fin", keys[-3:] == ["sport", "basket", "winner"], str(keys[-3:]))
    check("b.cmds_27", len(keys) == 27, str(len(keys)))
    check("b.cmds_sport_fn", workflow.CMDS["sport"][0] is workflow.cmd_sport)
    check("b.cmds_basket_fn", workflow.CMDS["basket"][0] is workflow.cmd_basket)

    tmp = tempfile.mkdtemp(prefix="pari-b-")
    state = os.path.join(tmp, "sport_actif.json")
    old_state = moteur_sport.STATE_PATH
    old_tell = workflow.tell
    told = []
    workflow.tell = lambda t: told.append(t)
    moteur_sport.STATE_PATH = state
    try:
        told.clear()
        workflow.cmd_sport({}, "")
        check("b.sport_defaut_foot", moteur_sport.actif() == "foot")
        check("b.sport_affiche_2", any("foot" in t and "basket" in t for t in told), str(told[-1:]))

        told.clear()
        workflow.cmd_sport({}, "basket")
        check("b.sport_bascule_basket", moteur_sport.actif() == "basket")
        check("b.sport_persiste", json.load(open(state, encoding="utf-8"))["sport"] == "basket")

        cfg_f = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
        cfg_b = json.load(open(os.path.join(WORLD, "config", "moteur_basket.json"), encoding="utf-8"))
        check("b.bascule_ne_degele_pas", cfg_f["tickets_enabled"] is False and cfg_b["tickets_enabled"] is False)

        told.clear()
        workflow.cmd_sport({}, "foot")
        check("b.sport_retour_foot", moteur_sport.actif() == "foot")

        with open(state, "w", encoding="utf-8") as f:
            f.write("{ casse")
        check("b.sport_illisible_foot", moteur_sport.actif() == "foot")

        told.clear()
        workflow.cmd_sport({}, "basket")
        workflow.cmd_gel({}, "off")
        check("b.gel_basket_refuse", told and "Refus" in told[-1], (told[-1] if told else "")[:90])
        check("b.gel_basket_flag_intact", moteur_flag.tickets_enabled(moteur_sport.cfg_path("basket")) is False)

        told.clear()
        workflow.cmd_valider2({"steps": {"valider1": "x"}}, "")
        check("b.valider2_gele_basket", told and "MOTEUR GELE" in told[-1] and "basket" in told[-1],
              (told[-1] if told else "")[:90])

        told.clear()
        workflow.cmd_modele({}, "")
        check("b.modele_2_sports", any("SPORT ACTIF" in t for t in told)
              and any(t.strip().startswith("basket :") for t in told))

        told.clear()
        workflow.cmd_basket({}, "")
        check("b.basket_detail", any("Calibration" in t for t in told)
              and any("n_oos" in t for t in told))
        check("b.basket_reste_actif", moteur_sport.actif() == "basket")
    finally:
        workflow.tell = old_tell
        moteur_sport.STATE_PATH = old_state

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Cahier B commutation : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
