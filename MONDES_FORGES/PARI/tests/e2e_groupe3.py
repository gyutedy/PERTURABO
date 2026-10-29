#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E Groupe 3 (Phases 4+5) — monde PARI v2
================================================
1. Siège complet sur carte démo (stats + cotes) → top3.json à jour.
2. Mode tickets : budget 6000 FC · sur-ticket 3000 FC · 3 tickets.
3. Assertions combinator/preview2 (allocation, classe SUR_TICKET, somme = budget,
   jambes <= max, charte PERTURABO, responsive).
4. Régression : --mode demo reste vert.
"""

import os
import subprocess
import sys
import json

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "PARI"))
PY = sys.executable
ENV = {**os.environ, "PARI_AUTO_GATES": "1", "PYTHONIOENCODING": "utf-8"}
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'✅ PASS' if ok else '❌ FAIL'} — {name}" + (f" — {note}" if note else ""))


def run(cmd, cwd=WORLD, timeout=600):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=ENV, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("=" * 70)
    print("E2E GROUPE 3 — PHASE 4 (tickets + backroll) + PHASE 5 (preview 2)")
    print("=" * 70)

    carte = os.path.join(WORLD, "ARCHIVUM", "fixtures", "e2e_g3_carte.json")
    sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
    import orchestrator  # noqa: E402
    orchestrator.make_demo_fixtures(carte, n=18)

    # Nettoie les notes qualitatives du group 2 (pas le cas scénario ici)
    notes_path = os.path.join(WORLD, "ARCHIVUM", "fixtures", "notes_qualitatives.json")
    if os.path.exists(notes_path):
        os.remove(notes_path)

    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "siege", "--fixtures", carte])
    check("P4.siege", os.path.exists(os.path.join(WORLD, "F03_FORGEWARD/OUT/top3.json")))

    # — Mode tickets, look: opérateur: "6000 FC, 3000 sur le ticket sûr, le reste divisé" —
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "tickets",
                  "--combos", "3", "--jambes", "3:2:2",
                  "--budget-fc", "6000", "--surticket-fc", "3000"])
    check("P4.tickets_run", r == 0, out.splitlines()[-1][:90] if out.strip() else "")

    tj = json.load(open(os.path.join(WORLD, "F05_PACKAGER/OUT/tickets.json"), encoding="utf-8"))
    tickets = tj["tickets"]
    ok = len(tickets) == 3
    check("P4.nb_tickets", ok, f"{len(tickets)} tickets")
    total = sum(t["mise_fc"] for t in tickets)
    ok = abs(total - 6000) < 0.02 and tj["budget"]["reste_fc"] <= 0.02
    check("P4.budget_plein", ok, f"alloué {total} / 6000 FC, reste {tj['budget']['reste_fc']}")
    ok = (tickets[0]["classe"] == "SUR_TICKET" and abs(tickets[0]["mise_fc"] - 3000) < 0.02)
    check("P4.surticket_3000", ok, f"T1 mise {tickets[0]['mise_fc']}")
    ok = all(t["nb_jambes"] <= 4 for t in tickets)
    check("P4.jambes_max", ok, f"{[t['nb_jambes'] for t in tickets]} jambes (max 4)")
    ok = all(t["cote_totale"] > 1.01 for t in tickets)
    check("P4.cotes_valides", ok, str([t["cote_totale"] for t in tickets]))
    ok = tickets[0]["jambes"][0]["score_commun"] >= max(
        t["jambes"][-1]["score_commun"] for t in tickets[1:]) if len(tickets) > 1 else True
    check("P4.classeA_en_tete", ok, "les matchs au score le plus haut sont dans le ticket sûr")

    # — Preview 2 —
    html_path = os.path.join(WORLD, "SHARED/OUT/preview2.html")
    ok = os.path.exists(html_path)
    content = open(html_path, encoding="utf-8").read() if ok else ""
    tokens = ["PERTURABO", "TICKET FINAL", "Budget du jour", "SUR_TICKET", "d4a017"]
    ok = ok and all(tok in content for tok in tokens)
    check("P5.preview2_charte", ok, "tokens PERTURABO + ticket final + budget présents")
    ok = "T3" in content and "cote" in content
    check("P5.preview2_tickets", ok, "3 cartes de tickets rendues")

    # — Régression : mode démo v1 —
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "demo"], timeout=600)
    check("P5.demo_regression", r == 0, out.splitlines()[0][:90] if out.strip() else "")

    n_fail = sum(1 for _, ok_, _ in CHECKS if not ok_)
    print("=" * 70)
    print(f"E2E GROUPE 3 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          (" — ✅ GROUPE 3 OK" if n_fail == 0 else f" — ❌ {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
