#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 0 — selecteur de sport. Zero reseau. Foot maitre par defaut."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import moteur_sport  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 0 — moteur_sport")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="pari-sport-")
    p = os.path.join(tmp, "sport_actif.json")

    check("sport.absent_foot", moteur_sport.actif(p) == "foot")
    with open(p, "w", encoding="utf-8") as f:
        f.write("{ casse")
    check("sport.casse_foot", moteur_sport.actif(p) == "foot")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"sport": "tennis"}, f)
    check("sport.inconnu_foot", moteur_sport.actif(p) == "foot")

    moteur_sport.set_sport("basket", p)
    check("sport.set_basket", moteur_sport.actif(p) == "basket")
    moteur_sport.set_sport("foot", p)
    check("sport.set_foot", moteur_sport.actif(p) == "foot")

    refused = False
    try:
        moteur_sport.set_sport("tennis", p)
    except ValueError:
        refused = True
    check("sport.refus_inconnu", refused)
    check("sport.intact_apres_refus", moteur_sport.actif(p) == "foot")

    check("sport.cfg_foot", os.path.basename(moteur_sport.cfg_path("foot")) == "moteur.json")
    check("sport.cfg_basket", os.path.basename(moteur_sport.cfg_path("basket")) == "moteur_basket.json")

    cfg_b = json.load(open(os.path.join(WORLD, "config", "moteur_basket.json"), encoding="utf-8"))
    cfg_f = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
    check("sport.basket_gele", cfg_b.get("tickets_enabled") is False)
    check("sport.foot_gele", cfg_f.get("tickets_enabled") is False)
    check("sport.moteurs_separes", cfg_b.get("engine") != cfg_f.get("engine"))

    states = moteur_sport.both_states()
    check("sport.states_2", set(states.keys()) == {"foot", "basket"})
    check("sport.states_actif_foot", states["foot"]["actif"] is True and states["basket"]["actif"] is False)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 0 sport : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
