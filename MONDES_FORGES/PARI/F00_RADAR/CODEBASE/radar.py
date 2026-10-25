"""
F00 RADAR / CAPTEURS — Scan complet d'une ligue (monde PARI)
=============================================================
Avant la Porte 1 : récupère TOUS les matchs de la carte, lance le moteur
Dixon-Coles (F02) sur chacun, et produit un classement.

Score composite (poids par marchés actifs du profil Warsmith) :
  0.55 × P(O2.5) + 0.30 × P(MT2 > MT1) + 0.15 × min(1, λ_total/4)
Sortie : radar.json + SHARED/OUT/RADAR.md (lisible sur téléphone)

Usage:
  python radar.py --input ../../ARCHIVUM/fixtures/matches.json [--top 20]
"""

import json
import argparse
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BREACHER_DIR = os.path.join(HERE, "..", "..", "F02_BREACHER", "CODEBASE")
sys.path.insert(0, BREACHER_DIR)
import breacher  # noqa: E402


def run_radar(matchs, top=20):
    analyse = breacher.analyse_fixtures(matchs)
    for m, a in zip(matchs, analyse["analyses"]):
        if m.get("ligue"):
            analyse["ligue"] = m["ligue"]
        lam_total = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        a["radar_score"] = round(
            0.55 * a["probas"]["o2.5"] + 0.30 * a["probas"]["mt2_plus"] + 0.15 * min(1.0, lam_total / 4.0), 4
        )
    ranked = sorted(analyse["analyses"], key=lambda a: a["radar_score"], reverse=True)
    analyse["analyses"] = ranked
    analyse["top_ids"] = [a["id"] for a in ranked[:top]]
    return analyse


def render_radar_md(analyse, top=20, max_rows=200):
    ranked = analyse["analyses"][:max_rows]
    lines = [
        f"# RADAR DE SIÈGE — {analyse.get('ligue', 'ligue')}",
        f"*Généré le {analyse['generated_at']} — moteur: Dixon-Coles PARI*",
        "",
        "| Rang | Match | λ total | P(O2.5) | P(MT2>) | Score |",
        "|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(ranked, 1):
        lam = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        badge = "🔥" if i <= top else "  "
        lines.append(
            f"| {badge} {i} | {a['match']} ({a['id']}) | {lam:.2f} "
            f"| {a['probas']['o2.5']:.0%} | {a['probas']['mt2_plus']:.0%} | {a['radar_score']:.3f} |"
        )
    lines += ["", f"**Top {top}** passe la coupe noire ; le reste est archivé.",
              "", "*Le radar sert à trouver où creuser — la Value sort après la "
              "comparaison aux cotes Winner Bet (Compartiment 3).*"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="F00 RADAR — scan ligue PARI")
    parser.add_argument("--input", required=True)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--out-json", default=os.path.join(HERE, "..", "OUT", "radar.json"))
    parser.add_argument("--out-md", default=os.path.join(HERE, "..", "..", "SHARED", "OUT", "RADAR.md"))
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        carte = json.load(f)
    matchs = carte.get("matchs", [])
    analyse = run_radar(matchs, top=args.top)
    analyse["ligue"] = carte.get("ligue", "ligue")
    analyse["ligue_tier"] = carte.get("ligue_tier", "exotique")

    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(analyse, f, indent=2, ensure_ascii=False)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(render_radar_md(analyse, top=args.top))

    print(f"[RADAR] {len(matchs)} matchs scannés — {args.top} TOP")
    for i, a in enumerate(analyse["analyses"][: args.top], 1):
        lam = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        print(f"  {i:>2}. {a['match']:<30} λ{lam:.2f} O2.5:{a['probas']['o2.5']:.0%} MT2>:{a['probas']['mt2_plus']:.0%}")
    print(f"[RADAR] JSON: {args.out_json}")
    print(f"[RADAR] MD:   {args.out_md}")


if __name__ == "__main__":
    main()
