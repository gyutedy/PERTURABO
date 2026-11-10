#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V5 — Telegram relais /vanus. Lecture seule. Jamais un p. Gel intact."""

import ast
import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import moteur_flag  # noqa: E402
import workflow  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()


def _parse():
    return open(os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "parse.py"), encoding="utf-8").read()


def _js():
    return open(os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "src", "index.js"), encoding="utf-8").read()


def _blob(niveau="isole", selection="home", n=1, found=1, extra=None):
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
    matches = {
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
    }
    if extra:
        matches.update(extra)
    return {
        "contract": "vanus.signal.v1",
        "generated_at": "2026-11-09T12:00:00Z",
        "slate_date": "2026-11-09",
        "indexes_vus": ["predictlix"],
        "matches": matches,
        "holes": [],
    }


def _carte():
    return {
        "matchs": [
            {"id": "M1", "dom": "Arsenal", "ext": "Chelsea", "date": "2026-11-09"},
            {"id": "M2", "dom": "Barca", "ext": "Madrid", "date": "2026-11-09"},
        ]
    }


def _world(blob=None, carte=None):
    tmp = tempfile.mkdtemp(prefix="pari-v5-")
    os.makedirs(os.path.join(tmp, "ARCHIVUM", "vanus"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "ARCHIVUM", "fixtures"), exist_ok=True)
    if blob is not None:
        json.dump(blob, open(os.path.join(tmp, "ARCHIVUM", "vanus", "latest.json"), "w", encoding="utf-8"))
    if carte is not None:
        json.dump(carte, open(os.path.join(tmp, "ARCHIVUM", "fixtures", "matches.json"), "w", encoding="utf-8"))
    return tmp


def main():
    print("=" * 70)
    print("TEST V5 — Telegram /vanus")
    print("=" * 70)

    src = _src()
    py = _parse()
    js = _js()
    check("v5.cmd", "def cmd_vanus" in src and '"vanus"' in src)
    check("v5.parse_known", '"vanus"' in py and '"modele"' in py and '"gel"' in py)
    check("v5.js_known", '"vanus"' in js and '"modele"' in js and '"gel"' in js)
    check("v5.stdlib_wf", "import numpy" not in src and "import scipy" not in src)
    check("v5.pas_poisson", "score_matrix" not in src.split("def cmd_vanus")[1].split("def cmd_modele")[0])
    check("v5.jamais_un_p", "Jamais un p" in src or "jamais un p" in src)
    ast.parse(src)
    check("v5.ast", True)

    schema = json.load(open(os.path.join(WORLD, "CONTRACTS", "schema_listen.json"), encoding="utf-8"))
    pat = (schema.get("properties") or {}).get("cmd", {}).get("pattern") or ""
    check("v5.schema_vanus", "vanus" in pat and "modele" in pat and "gel" in pat, pat)

    told = []
    old_tell = workflow.tell
    old_world = workflow.WORLD
    workflow.tell = lambda t: told.append(t)

    tmp_abs = _world(blob=None, carte=_carte())
    workflow.WORLD = tmp_abs
    try:
        workflow.cmd_vanus({}, "")
        check("v5.absent", told and "absent" in told[-1].lower(), (told[-1] if told else "")[:80])
        check("v5.absent_pas_p", told and "p_modele" not in told[-1])
    finally:
        workflow.WORLD = old_world

    told.clear()
    tmp_bad = _world(blob={"contract": "nope", "matches": {}}, carte=_carte())
    workflow.WORLD = tmp_bad
    try:
        workflow.cmd_vanus({}, "")
        check("v5.contrat", told and "contrat" in told[-1].lower(), (told[-1] if told else "")[:80])
    finally:
        workflow.WORLD = old_world

    told.clear()
    tmp_empty = _world(blob=_blob("jackpot", n=6, found=6), carte={"matchs": []})
    workflow.WORLD = tmp_empty
    try:
        workflow.cmd_vanus({}, "")
        check("v5.carte_vide", told and "carte vide" in told[-1].lower(), (told[-1] if told else "")[:80])
    finally:
        workflow.WORLD = old_world

    told.clear()
    tmp_ok = _world(blob=_blob("jackpot", selection="home", n=6, found=6), carte=_carte())
    workflow.WORLD = tmp_ok
    try:
        workflow.cmd_vanus({}, "")
        msg = told[-1] if told else ""
        check("v5.jackpot_veto", "veto" in msg.lower() and "vanus_jackpot" in msg, msg[:120])
        check("v5.jackpot_oppose", "veto=2" in msg, msg[:120])
        check("v5.jackpot_m2_hole", "vanus_match" in msg, msg[:160])
        check("v5.jackpot_pas_p", "p_modele" not in msg and "0.58" not in msg)

        told.clear()
        workflow.cmd_vanus({}, "M1")
        m1 = told[-1] if told else ""
        check("v5.id_m1", "M1" in m1 and "veto" in m1.lower(), m1[:120])
        check("v5.id_pas_m2", "M2" not in m1)

        told.clear()
        workflow.cmd_vanus({}, "99")
        check("v5.id_inconnu", told and "introuvable" in told[-1].lower(), (told[-1] if told else "")[:80])
    finally:
        workflow.WORLD = old_world

    told.clear()
    tmp_al = _world(blob=_blob("alarme", selection="home", n=2, found=2), carte=_carte())
    workflow.WORLD = tmp_al
    try:
        workflow.cmd_vanus({}, "M1")
        al = told[-1] if told else ""
        check("v5.alarme_info", "info" in al.lower() and "vanus_alarme" in al, al[:120])
        check("v5.alarme_pas_veto", "veto=—" in al or "veto=-" in al, al[:120])
    finally:
        workflow.WORLD = old_world

    told.clear()
    tmp_is = _world(blob=_blob("isole", selection="home", n=1, found=1), carte=_carte())
    workflow.WORLD = tmp_is
    try:
        workflow.cmd_vanus({}, "M1")
        iso = told[-1] if told else ""
        check("v5.isole_pass", "pass" in iso.lower(), iso[:120])
    finally:
        workflow.WORLD = old_world

    told.clear()
    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    tmp_sk = _world(blob=_blob("jackpot", n=6, found=6), carte=_carte())
    workflow.WORLD = tmp_sk
    try:
        workflow.cmd_vanus({}, "")
        sk = told[-1] if told else ""
        check("v5.skip_hole", "skip" in sk.lower(), sk[:80])
        check("v5.skip_pas_veto", "vanus_jackpot" not in sk)
    finally:
        workflow.WORLD = old_world
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    workflow.tell = old_tell
    check("v5.gel", moteur_flag.tickets_enabled() is False)
    check("v5.cmds", "vanus" in workflow.CMDS and "modele" in workflow.CMDS)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V5 telegram : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
