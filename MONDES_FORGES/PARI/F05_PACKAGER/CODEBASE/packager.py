"""
F05 PACKAGER — Le pari pack final (monde PARI)
===============================================
Assemble la synthèse : TOP N picks (10-20) triés par EV, liste NO BET,
combinés candidats, zone loterie (budget séparé), métriques + disclaimer.

Sortie: F05_PACKAGER/OUT/pari_pack.json  (contrat schema_pari_pack.json)

Usage:
  python packager.py --predictions ../../F03_FORGEWARD/OUT/predictions.json \
                     --analysis ../../F02_BREACHER/OUT/analysis.json \
                     --carte ../../TYRANT/OUT/carte_verdict.json [--top 10]
"""

import json
import argparse
import os
from datetime import datetime, timezone

SELECTION_LABELS = {
    "1": "Victoire Domicile", "X": "Nul", "2": "Victoire Extérieur",
    "o2.5": "Over 2.5", "u2.5": "Under 2.5",
    "mt1": "1re MT plus prolifique", "mte": "Égalité de mi-temps",
    "mt2": "2e MT plus prolifique", "btts": "Les deux marquent",
}

DISCLAIMER = ("🪙 Jeu responsable : le pari est un divertissement à maîtriser. Ces probabilités ne sont des "
              "certitudes ; une EV positive est un verdict long terme, pas une promesse du jour.")


def build_pack(predictions, analysis, carte, top=10, devise="USD"):
    picks = []
    no_bet = []
    analyses = (analysis or {}).get("analyses") or []
    qualite_by_id = {}
    for a in analyses:
        dq = a.get("data_quality") if isinstance(a.get("data_quality"), dict) else {}
        if a.get("id"):
            qualite_by_id[a["id"]] = dq.get("niveau") or "basse"

    for p in (predictions or {}).get("predictions") or []:
        if p.get("verdict") == "GO":
            sels = p.get("selections") or []
            for s in sorted(sels, key=lambda s: s.get("ev") or 0, reverse=True):
                if s.get("verdict") == "VALUE":
                    picks.append({
                        "match_id": p["id"],
                        "match": p["match"],
                        "marche": s["marche"],
                        "selection": s["selection"],
                        "selection_label": s.get("selection_label", SELECTION_LABELS.get(s["selection"], s["selection"])),
                        "cote": s["cote"],
                        "p_modele": s["p_modele"],
                        "ev": s["ev"],
                        "mise_units": s.get("mise_units") or 0,
                        "note_risque": f"qualité data: {qualite_by_id.get(p['id'], 'basse')}",
                    })
        elif p["verdict"] == "NO_BET":
            raison = "EV < seuil sur tous les marchés" if p["selections"] else "aucune cote fournie"
            no_bet.append({"match_id": p["id"], "match": p["match"], "raison": raison})

    picks.sort(key=lambda x: x["ev"], reverse=True)
    picks = picks[:top]
    for i, pk in enumerate(picks, 1):
        pk["rang"] = i

    preds = (predictions or {}).get("predictions") or []
    combines = (predictions or {}).get("combines") or []
    mise_totale = round(sum(x["mise_units"] for x in picks)
                        + sum(c.get("mise_units") or 0 for c in combines), 2)
    ev_moy = round(sum(x["ev"] for x in picks) / len(picks), 4) if picks else None

    pack = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "siege_id": None,  # renseigné par l'orchestrateur/IW_CUSTOS
        "devise": devise,
        "titre": f"DIRECTION DES SIÈGES — TOP {len(picks)}",
        "top_picks": picks,
        "no_bet": no_bet,
        "combines": combines,
        "loterie": {
            "budget_pct_bankroll": 0.02,
            "note": "Zone DIVERTISSEMENT séparée. Combinés 10+ jambes cote 100+ : jamais dans le capital de chasse.",
            "tickets_suggeres": [],
        },
        "metriques": {
            "mise_totale_units": mise_totale,
            "ev_moyenne_pct": ev_moy,
            "nb_matchs_analyses": len(preds),
            "nb_no_bet": len(no_bet),
            "nb_matchs_go": sum(1 for p in preds if p.get("verdict") in ("GO", "THIN")),
        },
        "disclaimer": DISCLAIMER,
    }
    if carte:
        pack["carte_tyran"] = {"ligue": carte.get("ligue"), "ligue_tier": carte.get("ligue_tier"),
                               "seuil_ev": carte.get("seuil_ev_applique")}
    return pack


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="F05 PACKAGER — pari pack")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--carte", default=None)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--output", default=os.path.join(here, "..", "OUT", "pari_pack.json"))
    args = parser.parse_args()

    with open(args.predictions, "r", encoding="utf-8") as f:
        predictions = json.load(f)
    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    carte = None
    if args.carte and os.path.exists(args.carte):
        with open(args.carte, "r", encoding="utf-8") as f:
            carte = json.load(f)

    pack = build_pack(predictions, analysis, carte, top=args.top)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, ensure_ascii=False)

    print(f"[PACKAGER] 🏆 {pack['titre']}")
    for x in pack["top_picks"]:
        print(f"  #{x['rang']:>2} {x['match']:<26} {x['selection_label']:<22} "
              f"cote {x['cote']:<5} EV {x['ev']:+.1%} mise {x['mise_units'] or 0}u")
    m = pack["metriques"]
    print(f"[PACKAGER] Mise totale: {m['mise_totale_units']}u — EV moyenne: "
          f"{(m['ev_moyenne_pct'] or 0):+.1%} — NO BET: {m['nb_no_bet']}/{m['nb_matchs_analyses']}")
    for c in pack["combines"]:
        print(f"  🧩 COMBINÉ {len(c['jambes'])} jambes — cote {c['cote_totale']} — EV {c['ev_combine']:+.1%} — {c['mise_units']}u")
    print(f"[PACKAGER] Disclaimer embarqué. Sortie: {args.output}")


if __name__ == "__main__":
    main()
