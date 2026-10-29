#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E Groupe 2 (Phases 2+3) — monde PARI v2
================================================
1. Carte de démo (stats + cotes) → siège complet (PARI_AUTO_GATES=1, démo uniquement).
2. Notes qualitatives : M1 fatigue élévé (exclusion MT2/MTÉ attendue),
   M2 fatigue + blessures élèvés (NO BET recommandé attendu).
3. Assertions : predictions_filtered.json, exclusions MT2 sur M1, NO BET sur M2,
   top3.json (score 0-10, buckets), TOP3.md, preview1.html (charte PERTURABO).
4. Régression : --mode demo reste vert.

Sortie : PASS/FAIL par étape, exit 0 seulement si tout passe.
"""

import os
import subprocess
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "PARI"))
PY = sys.executable
ENV = {**os.environ, "PARI_AUTO_GATES": "1", "PYTHONIOENCODING": "utf-8"}

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'✅ PASS' if ok else '❌ FAIL'} — {name}" + (f" — {note}" if note else ""))


def run(cmd, cwd=WORLD, timeout=420):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=ENV, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("=" * 70)
    print("E2E GROUPE 2 — PHASE 2 (non-binaire borné) + PHASE 3 (top3 + preview1)")
    print("=" * 70)

    # Carte de démo (18 matchs, stats + cotes Winner Bet-like)
    carte = os.path.join(WORLD, "ARCHIVUM", "fixtures", "e2e_g2_carte.json")
    sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
    import orchestrator  # noqa: E402
    orchestrator.make_demo_fixtures(carte, n=18)

    # Notes qualitatives sur M1 et M2
    notes_path = os.path.join(WORLD, "ARCHIVUM", "fixtures", "notes_qualitatives.json")
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write("""
{
  "generated_at": "2026-10-29T12:00:00Z",
  "source": "operateur",
  "notes": [
    {"match_id": "M1", "themes": {
        "fatigue": {"impact": "eleve", "detail": "3e match en 7 jours, rotation probable du 11 de départ"}
    }},
    {"match_id": "M2", "themes": {
        "fatigue":   {"impact": "eleve", "detail": "tournée continentale"},
        "blessures": {"impact": "eleve", "detail": "milieu défensif titulaire absent"}
    }}
  ]
}
""")

    # — Siège complet —
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "siege",
                  "--fixtures", carte])
    check("P2.siege", os.path.exists(os.path.join(WORLD, "F03_FORGEWARD/OUT/predictions_filtered.json")))

    import json
    pf = json.load(open(os.path.join(WORLD, "F03_FORGEWARD/OUT/predictions_filtered.json"), encoding="utf-8"))
    by_id = {p["id"]: p for p in pf["predictions"]}

    # M1 : fatigue élèvé → MT2/mte exclus (aucun top exploitant mt2 sur M1)
    m1 = by_id.get("M1", {})
    mt2_on_m1 = [s for s in m1.get("selections", [])
                 if s.get("selection") in ("mt2", "mte") and s.get("verdict") == "VALUE"]
    check("P2.exclusion MT2/mte M1", len(mt2_on_m1) == 0,
          f"VALUE restantes sur mt2/mte de M1: {len(mt2_on_m1)}")

    # le reste des marchés M1 → VALUE puisées au seuil +4 pts
    kept = [s for s in m1.get("selections", []) if s.get("verdict") == "VALUE"]
    ok = all(s.get("ev", -1) >= 0.03 + 0.04 - 1e-9 for s in kept)
    check("P2.seuil bonus M1", ok, f"seuil += 4 pts ({len(kept)} VALUE)")

    # M2 : fatigue + blessures élèvés → NO BET recommandé, tout NO_BET
    m2 = by_id.get("M2", {})
    ok = m2.get("verdict") == "NO_BET" and all(s.get("verdict") == "NO_BET" for s in m2.get("selections", []))
    check("P2.no_bet M2", ok)

    # — Phase 3 : top3 + score commun + TOP3.md + preview1 —
    t3 = json.load(open(os.path.join(WORLD, "F03_FORGEWARD/OUT/top3.json"), encoding="utf-8"))
    ok = (0 <= min(r_["score_commun"] for r_ in t3["matchs"])) and \
         (max(r_["score_commun"] for r_ in t3["matchs"]) <= 10.0) and \
         all(r_["bucket"] in ("HAUTE", "MOYENNE", "FAIBLE") for r_ in t3["matchs"]) and \
         all(1 <= len(r_["top3"]) <= 3 for r_ in t3["matchs"] if r_["verdict_modele"] == "GO")
    check("P3.top3_scores", ok, f"{len(t3['matchs'])} classés, scores "
          f"{min(r_['score_commun'] for r_ in t3['matchs'])}–{max(r_['score_commun'] for r_ in t3['matchs'])}")

    top3_m1 = next(r_ for r_ in t3["matchs"] if r_["id"] == "M1")
    ok = all(s["selection"] not in ("mt2", "mte") for s in top3_m1["top3"])
    check("P3.top3_m1_sans_mt2", ok, str([s["selection"] for s in top3_m1["top3"]]))

    ok = (next(r_ for r_ in t3["matchs"] if r_["id"] == "M2")["no_bet_recommande"])
    check("P3.top3_m2_flag_nobet", ok)

    md = os.path.join(WORLD, "SHARED/OUT/TOP3.md"); html = os.path.join(WORLD, "SHARED/OUT/preview1.html")
    ok = os.path.exists(md)
    check("P3.top3_md", ok, md)

    ok = os.path.exists(html)
    content = open(html, encoding="utf-8").read() if ok else ""
    tokens = ["PERTURABO", "#24507e", "score", "Top 3 marchés", "d4a017"]
    ok = ok and all(token in content for token in tokens)
    check("P3.preview1_charte", ok, "PERTURABO + PERTURABO-BLEU + score présents")

    llammi = content.count("details")
    check("P3.preview1_contenu", llammi >= 3, f"{llammi} blocs <details>")

    # — Régression : mode démo v1 —
    r, out = run([PY, "ORCHESTRATOR/CODEBASE/orchestrator.py", "--mode", "demo"], timeout=600)
    check("P3.demo_regression", r == 0, out.splitlines()[0][:90] if out.strip() else "")

    n_fail = sum(1 for _, ok_, _ in CHECKS if not ok_)
    print("=" * 70)
    print(f"E2E GROUPE 2 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          (" — ✅ GROUPE 2 OK" if n_fail == 0 else f" — ❌ {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
