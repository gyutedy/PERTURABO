#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E Groupe 1 (Phases 0+1) — monde PARI v2
================================================
1. Vérifie la zone transcriptions (catalogue + fraîcheur).
2. Fait tourner le chemin input-capture : texte OCR → parse → VALIDE → carte.
3. Fait tourner le siège réel de bout en bout sur cette carte (PARI_AUTO_GATES=1,
   démo uniquement).
4. Fait tourner --mode demo (chemin v1 historique) pour vérifier qu'aucune
   régression n'est présente.

Sortie : PASS/FAIL par étape, exit 0 only si tout passe.
"""

import os
import subprocess
import sys
import json

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WROOT = os.path.normpath(os.path.join(WORLD, "..", ".."))
PY = sys.executable
ENV = {**os.environ, "PARI_AUTO_GATES": "1", "PYTHONIOENCODING": "utf-8"}

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'✅ PASS' if ok else '❌ FAIL'} — {name}" + (f" — {note}" if note else ""))


def run(cmd, cwd=WORLD, timeout=240):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=ENV, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


CAPTURE_TXT = r"""
Premier League - England  2026-10-29  18:00
Arsenal - Chelsea  1.85 3.60 4.20  O2.5 1.70 U2.5 2.05  MT1 2.10 MT2 2.20
Liverpool - Everton  1X2 1.55/4.10/6.00  BTTS 1.95 BTTS NON 1.85
Ligue 1 - France  19:45
Monaco - Bottled  1.62 3.80 5.10  o1.5 1.25 u1.5 3.90
"""


def main():
    print("=" * 70)
    print("E2E GROUPE 1 — PHASE 0 (transcriptions) + PHASE 1 (input capture)")
    print("=" * 70)

    # ---- Phase 0 : transcriptions -------------------------------------------
    r, out = run([PY, "ingest_transcripts.py", "--freshness", "14"],
                 cwd=os.path.join(WORLD, "ARCHIVUM", "knowledge_base", "RESSOURCES"))
    # exit 0 ou 1 accepté : --freshness signale les sources sans date (TO_CONFIRM)
    # — l'important est que le rapport tourne et liste l'état réel.
    ok = r in (0, 1) and "FRAÎCHEUR RESSOURCES" in out and "Transcriptions déposées" in out
    check("P0.freshness", ok, out.splitlines()[-1][:90] if out.strip() else "")

    audit = os.path.join(WORLD, "ARCHIVUM", "knowledge_base", "RESSOURCES", "AUDIT_CORPUS.md")
    ok = os.path.exists(audit) and "Tableau de conformité" in open(audit, encoding="utf-8").read()
    check("P0.audit_corpus", ok, audit)

    # ---- Phase 1 : input capture --------------------------------------------
    r, out = run([PY, "F01_SENTINEL/CODEBASE/input_capture.py",
                  "--capture", "-", "--out-json", "F01_SENTINEL/OUT/e2e_capture.json"]) \
        if False else (1, "")
    # bypass stdin: écrire la capture dans un fichier temporaire
    cap = os.path.join(WORLD, "F01_SENTINEL", "OUT", "e2e_capture.txt")
    os.makedirs(os.path.dirname(cap), exist_ok=True)
    with open(cap, "w", encoding="utf-8") as f:
        f.write(CAPTURE_TXT)

    r, out = run([PY, "F01_SENTINEL/CODEBASE/input_capture.py",
                  "--capture", cap, "--out-json", os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_capture.json")])
    check("P1.parse", r == 0 and "statut: A_VALIDER" in out, out.splitlines()[0][:90] if out.strip() else "")

    with open(os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_capture.json"), encoding="utf-8") as f:
        parsed = json.load(f)
    n = parsed.get("n_matchs", 0)
    b1 = parsed["captures"][0] if parsed["captures"] else {}
    has_dh = bool(b1.get("date")) and bool(b1.get("heure"))
    m2 = b1["matchs"][1] if len(b1.get("matchs", [])) > 1 else {}
    ok = (n == 3 and has_dh and set(m2.get("cotes", {})) == {"1", "X", "2", "btts", "btts_no"})
    check("P1.parse_contenu", ok, f"n_matchs={n}, date/heure={has_dh}, M2 cotes={sorted(m2.get('cotes', {}))}")

    # Cas Zero Data : match SANS compétition → warning bloquant, rien de deviné
    cap_zd = cap.replace(".txt", "_zerodata.txt")
    with open(cap_zd, "w", encoding="utf-8") as f:
        f.write("Arsenal - Chelsea  1.85 3.60 4.20\n")
    r, out = run([PY, "F01_SENTINEL/CODEBASE/input_capture.py",
                  "--capture", cap_zd, "--out-json", os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_zerodata.json")])
    with open(os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_zerodata.json"), encoding="utf-8") as f:
        zd = json.load(f)
    ok = any("compétition" in w.lower() for w in zd.get("warnings", [])) and zd.get("statut") == "A_VALIDER"
    check("P1.zerodata_warning", ok, "compétition absente détectée, statut A_VALIDER")

    carte = os.path.join(WORLD, "ARCHIVUM/fixtures/e2e_capture.json")
    r, out = run([PY, "F01_SENTINEL/CODEBASE/input_capture.py",
                  "--capture", cap, "--valider", "--out-carte", carte,
                  "--out-json", os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_capture.json")])
    ok = r == 0 and os.path.exists(carte) and '"statut": "VALIDE"' in \
        open(os.path.join(WORLD, "F01_SENTINEL/OUT/e2e_capture.json"), encoding="utf-8").read()
    check("P1.valide_carte", ok, carte)

    # ---- Phase 1 : siège réel de bout en bout --------------------------------
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "siege",
                  "--fixtures", carte])
    siege_ok = r == 0
    for expected in ("GATE 1",):
        siege_ok = siege_ok and expected.lower() in out.lower()
    check("P1.siege_e2e", siege_ok, out.splitlines()[-1][:90] if out.strip() else "")

    pred_ok = os.path.exists(os.path.join(WORLD, "F03_FORGEWARD/OUT/predictions.json"))
    pack_ok = os.path.exists(os.path.join(WORLD, "F05_PACKAGER/OUT/pari_pack.json"))
    check("P1.outputs", pred_ok and pack_ok)

    # ---- Régression : mode demo v1 reste vert --------------------------------
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "demo"], timeout=420)
    check("P1.demo_regression", r == 0, out.splitlines()[0][:90] if out.strip() else "")

    n_fail = sum(1 for _, ok_, _ in CHECKS if not ok_)
    print("=" * 70)
    print(f"E2E GROUPE 1 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          (" — ✅ GROUPE 1 OK" if n_fail == 0 else f" — ❌ {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
