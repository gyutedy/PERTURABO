#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V0 — gel moteur. Zero reseau. Ledger intact."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import moteur_flag  # noqa: E402
import workflow  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST V0 — gel moteur")
    print("=" * 70)

    cfg = json.load(open(os.path.join(WORLD, "config", "moteur.json"), encoding="utf-8"))
    check("v0.cfg_false", cfg.get("tickets_enabled") is False)
    check("v0.cfg_require", cfg.get("require_calibration") is True)
    check("v0.flag_false", moteur_flag.tickets_enabled() is False)
    check("v0.engine", moteur_flag.engine() == "dc_mle")

    tmp = tempfile.mkdtemp(prefix="pari-v0-")
    p = os.path.join(tmp, "moteur.json")
    json.dump({"tickets_enabled": True}, open(p, "w"))
    check("v0.path_true", moteur_flag.tickets_enabled(p) is True)
    moteur_flag.set_tickets(False, p)
    check("v0.set_false", moteur_flag.tickets_enabled(p) is False)
    check("v0.illisible", moteur_flag.tickets_enabled(os.path.join(tmp, "absent.json")) is False)

    told = []
    old_tell = workflow.tell
    old_state = workflow.STATE_PATH
    old_dir = workflow.STATE_DIR
    old_world = workflow.WORLD
    workflow.tell = lambda t: told.append(t)
    workflow.WORLD = tmp
    workflow.STATE_DIR = os.path.join(tmp, "SHARED", "STATE")
    os.makedirs(workflow.STATE_DIR, exist_ok=True)
    workflow.STATE_PATH = os.path.join(workflow.STATE_DIR, "campagne.json")
    tix = os.path.join(tmp, "F05_PACKAGER", "OUT")
    os.makedirs(tix, exist_ok=True)
    tix_path = os.path.join(tix, "tickets.json")
    json.dump({"tickets": ["KEEP"]}, open(tix_path, "w"))
    mtime = os.path.getmtime(tix_path)
    try:
        st = {"steps": {"valider1": "x"}, "budget_fc": 3000, "surticket_fc": 800}
        workflow.cmd_valider2(st, "")
        check("v0.valider2_gele", told and "MOTEUR GELE" in told[-1], (told[-1] if told else "")[:80])
        check("v0.tickets_intacts", os.path.getmtime(tix_path) == mtime)

        told.clear()
        workflow.cmd_modele(st, "")
        check("v0.modele_gele", told and "GELE" in told[-1], (told[-1] if told else "")[:80])

        told.clear()
        workflow.cmd_gel(st, "off")
        check("v0.gel_off_refuse", told and "Refus" in told[-1], (told[-1] if told else "")[:80])
        check("v0.flag_reste_false", moteur_flag.tickets_enabled() is False)
    finally:
        workflow.tell = old_tell
        workflow.STATE_PATH = old_state
        workflow.STATE_DIR = old_dir
        workflow.WORLD = old_world

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V0 gel : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
