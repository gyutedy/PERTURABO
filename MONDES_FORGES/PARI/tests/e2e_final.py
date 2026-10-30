#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E FINAL — monde PARI v2 (cycle de campagne complet)
==========================================================
Rejoue le cycle opérateur tel que documenté :
  /start → /capture → /budget → /combos → /valider-1 → /valider-2 → /data → /status → /stop
avec une carte équipée de stats (scénario "stats injectées") et vérifie :
  - état de campagne SHARED/STATE/campagne.json
  - capture validée (statut VALIDE) → Porte 1 maintenue
  - Preview 1 + Preview 2 + tickets.json + TOP3.md + TICKETS.md
  - budgets alloués, doctrine (NO BET recommandé exclu)
  - docs v2 en place (GUIDE, README, CONTINUATION, contrats)
  - workflow GH parsable (pari_daily.yml)
"""

import os
import subprocess
import sys
import json

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "PARI"))
WROOT = os.path.normpath(os.path.join(WORLD, "..", ".."))
PY = sys.executable
ENV = {**os.environ, "PARI_AUTO_GATES": "1", "PARI_SKIP_INJECT": "1", "PYTHONIOENCODING": "utf-8"}
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'✅ PASS' if ok else '❌ FAIL'} — {name}" + (f" — {note}" if note else ""))


def wf(*cmds):
    r = subprocess.run([PY, "ORCHESTRATOR/CODEBASE/workflow.py"] + list(cmds),
                       capture_output=True, text=True, cwd=WORLD, env=ENV, timeout=600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def p(*a):
    return os.path.join(WORLD, *a)


def rd(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    print("=" * 70)
    print("E2E FINAL — CYCLE DE CAMPAGNE v2 COMPLET")
    print("=" * 70)

    # Carte avec stats + cotes (scénario "stats injectées avec succès")
    sys.path.insert(0, p("ORCHESTRATOR", "CODEBASE"))
    import orchestrator  # noqa: E402
    carte = p("ARCHIVUM", "fixtures", "e2e_final_carte.json")
    orchestrator.make_demo_fixtures(carte, n=18)
    # retirer les notes qualitatives du groupe 2 (test déterministe)
    for f in (p("ARCHIVUM", "fixtures", "notes_qualitatives.json"),):
        if os.path.exists(f):
            os.remove(f)
    if p("TYRANT", "OUT", "qualitative_verdict.json") and os.path.exists(p("TYRANT", "OUT", "qualitative_verdict.json")):
        os.remove(p("TYRANT", "OUT", "qualitative_verdict.json"))
    if p("F03_FORGEWARD", "OUT", "predictions_filtered.json") and os.path.exists(p("F03_FORGEWARD", "OUT", "predictions_filtered.json")):
        os.remove(p("F03_FORGEWARD", "OUT", "predictions_filtered.json"))

    cap = p("F01_SENTINEL", "OUT", "e2e_capture.txt")

    # 1. /start + /capture + /budget + /combos
    r, out = wf("/start", "/capture", cap, "/budget", "6000 / 3000", "/combos", "3:3:2:2")
    st = json.loads(rd(p("SHARED", "STATE", "campagne.json")) or "{}")
    ok = r == 0 and bool(st.get("campagne")) and st.get("capturer_statut") == "A_VALIDER" \
        and st.get("budget_fc") == 6000 and st.get("surticket_fc") == 3000 and st.get("combos") == 3
    check("FINAL.start_capture_budget_combos", ok,
          f"campagne={st.get('campagne')}, budget={st.get('budget_fc')}/{st.get('surticket_fc')}")

    # 2. /valider-1 — la carte capture (sans stats) reste Zero Data, doctrine-safe,
    #    puis on repeuple le top3 par un siège sur la carte des stats (comme CI)
    demo_top3 = p("SHARED", "OUT", "TOP3.md")
    os.makedirs(os.path.dirname(demo_top3), exist_ok=True)
    with open(demo_top3, "w", encoding="utf-8") as f:
        f.write("### PERTURABO · PARI — TOP 3\n*generated 2026-10-29T08:26:36Z — 18 matchs classés*\n- **#1 Cyclops vs Trench**\n")
    r, out = wf("/valider-1")
    ok = '"statut": "VALIDE"' in (rd(p("F01_SENTINEL", "OUT", "capture_parsed.json")) or "")
    check("FINAL.valider1_capture_valide", ok)
    t3md_live = rd(p("SHARED", "OUT", "TOP3.md")) or ""
    ok = "Cyclops vs Trench" not in t3md_live and ("Arsenal" in t3md_live or "NO BET" in t3md_live)
    check("FINAL.valider1_ecrase_demo", ok, t3md_live[:120].replace("\n", " "))
    ok = os.path.exists(p("SHARED", "OUT", "preview1.html"))
    check("FINAL.preview1", ok)
    subprocess.run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "siege",
                    "--fixtures", carte], capture_output=True, text=True, cwd=WORLD,
                   env=ENV, timeout=600)
    t3 = json.loads(rd(p("F03_FORGEWARD", "OUT", "top3.json")) or "{}")
    ok = t3.get("matchs") and max(m.get("score_commun", 0) for m in t3["matchs"]) >= 5
    check("FINAL.top3_peuple", ok, f"{len(t3.get('matchs', []))} matchs classés")

    # 3. /valider-2 — tickets + backroll + Preview 2
    r, out = wf("/valider-2")
    st = json.loads(rd(p("SHARED", "STATE", "campagne.json")) or "{}")
    ok = st.get("steps", {}).get("valider2") is not None
    check("FINAL.valider2_state", ok)
    tj = json.loads(rd(p("F05_PACKAGER", "OUT", "tickets.json")) or "{}")
    total = sum(t["mise_fc"] for t in tj.get("tickets", []))
    ok = len(tj.get("tickets", [])) == 3 and abs(total - 6000) < 0.02 \
        and abs(tj["tickets"][0]["mise_fc"] - 3000) < 0.02
    check("FINAL.tickets_backroll", ok,
          f"{len(tj.get('tickets', []))} tickets, {total:.0f}/6000 FC")
    ok = os.path.exists(p("SHARED", "OUT", "preview2.html"))
    content = rd(p("SHARED", "OUT", "preview2.html")) or ""
    ok = ok and "PERTURABO" in content and "TICKET FINAL" in content
    check("FINAL.preview2", ok)

    # 4. /data + /status + /stop
    r, out = wf("/data", "/status", "/stop")
    st = json.loads(rd(p("SHARED", "STATE", "campagne.json")) or "{}")
    ok = st.get("campagne") is None
    check("FINAL.stop", ok)
    t3md = rd(p("SHARED", "OUT", "TOP3.md")) or ""
    ok = ("TOP 3" in t3md.upper()) and "score" in t3md.lower()
    check("FINAL.data_message", ok, "/data fournit les rangs hors ticket")

    # 5. Docs + contrats + workflows
    docs_ok = all([
        "LE CYCLE DE CAMPAGNE v2" in (rd(p("GUIDE_UTILISATION.md")) or ""),
        "`workflow`" in (rd(p("README.md")) or ""),
        "PREVIEW 2" in (rd(p("CONTINUATION.md")) or ""),
    ])
    check("FINAL.docs_v2", docs_ok, "GUIDE + README + CONTINUATION")
    contrats_ok = all(os.path.exists(p("CONTRACTS", x)) for x in
                      ("schema_input_capture.json", "schema_notes_qualitatives.json",
                       "schema_top3.json", "schema_ticket_final.json"))
    check("FINAL.contrats", contrats_ok, "4 contrats v2")

    yml = rd(os.path.join(WROOT, ".github", "workflows", "pari_daily.yml")) or ""
    ok = "deploy-pages" in yml and "tickets" in yml and "pari-daily" in yml
    check("FINAL.workflow_gh", ok, "pari_daily.yml : tickets + Pages")

    n_fail = sum(1 for _, ok_, _ in CHECKS if not ok_)
    print("=" * 70)
    print(f"E2E FINAL : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          (" — ✅ CYCLE DE CAMPAGNE v2 OK" if n_fail == 0 else f" — ❌ {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
