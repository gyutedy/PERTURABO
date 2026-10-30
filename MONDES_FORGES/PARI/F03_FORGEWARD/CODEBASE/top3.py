"""
F03 FORGEWARD — TOP 3 MARCHÉS + SCORE COMMUN (v2, Phase 3)
==========================================================
Après FORGEWARD (EV par marché), l'opérateur NE DEVINE PLUS le marché à viser :
le monde classe, pour CHAQUE match, le **Top 3 des marchés** — les marchés qui
combinaisonnent la cote la plus injuste pour le book (EV haute) et la probabilité
la plus haute selon nos calculs froids (F02 + F03).

  - rang = tri par EV desc, à égalité par p_modele desc.
  - score_commun 01–10 (le "scoring à la clipping") : même échelle pour tous
    les matchs et tous les jours ; sert à regrouper les matchs par bucket de
    fiabilité et à répartir les mises.

Entrée :
  --predictions F03_FORGEWARD/OUT/predictions.json      (ou predictions_filtered.json)
  --analysis    F02_BREACHER/OUT/analysis.json          (qualité data + flags)
  --notes-filter TYRANT/OUT/qualitative_verdict.json    (optionnel — flag no_bet)
Sortie :
  --out-json    F03_FORGEWARD/OUT/top3.json
  --out-md      SHARED/OUT/TOP3.md     (le message source de la commande /data)
"""

import json
import argparse
import os
from datetime import datetime, timezone

QUALITY_WEIGHT = {"haute": 1.0, "moyenne": 0.75, "basse": 0.45}
BUCKETS = [("HAUTE", 7.0), ("MOYENNE", 5.0), ("FAIBLE", 0.0)]
FEEDER_TITRE = "PERTURABO · PARI — TOP 3 MARCHÉS PAR MATCH (score commun 01-10)"


def compute_match(p, quality):
    """Top 3 + score commun d'un match. Le match NO_BET garde son score mais sans top3 exploitable."""
    sel = [s for s in p.get("selections", []) if s.get("verdict") == "VALUE"]
    pool = sel if sel else [s for s in p.get("selections", []) if s.get("ev") is not None]
    sorted_sel = sorted(pool, key=lambda s: (-(s.get("ev") or 0), -(s.get("p_modele") or 0)))
    top3 = [{
        "rang": i + 1, "marche": s.get("marche"), "selection": s.get("selection"),
        "selection_label": s.get("selection_label") or s.get("selection"),
        "cote": s.get("cote"), "p_modele": s.get("p_modele"), "ev": s.get("ev"),
    } for i, s in enumerate(sorted_sel[:3])]

    # score commun 01-10 : qualité data (30%) · proba max du top (40%) · edge EV (30%)
    p_max = max((s.get("p_modele") or 0) for s in pool) if pool else 0.0
    ev_max = max((s.get("ev") or 0) for s in pool) if pool else 0.0
    wq = QUALITY_WEIGHT.get(quality, 0.45)
    wproba = min(1.0, p_max / 0.65)          # 65% de proba = référence parfaite
    wedge = max(0.0, min(1.0, 0.5 + 5 * ev_max))
    score = round(10 * (0.30 * wq + 0.40 * wproba + 0.30 * wedge), 1)
    score = max(0.0, min(10.0, score))
    bucket = next(n for n, seuil in BUCKETS if score >= seuil)
    return top3, score, bucket


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    arg = argparse.ArgumentParser(description="F03 FORGEWARD — Top 3 marchés + score commun")
    arg.add_argument("--predictions", required=True)
    arg.add_argument("--analysis", required=True)
    arg.add_argument("--notes-filter", default=None, help="TYRANT precedent (qualitative_verdict.json)")
    arg.add_argument("--out-json", default=os.path.join(here, "..", "OUT", "top3.json"))
    arg.add_argument("--out-md", default=os.path.join(here, "..", "..", "SHARED", "OUT", "TOP3.md"))
    args = arg.parse_args()

    with open(args.predictions, encoding="utf-8") as f:
        predictions = json.load(f)
    with open(args.analysis, encoding="utf-8") as f:
        analysis = json.load(f)

    quality_by_id = {a["id"]: a.get("data_quality", {}).get("niveau", "basse") for a in analysis.get("analyses", [])}
    norb = {}
    if args.notes_filter and os.path.exists(args.notes_filter):
        with open(args.notes_filter, encoding="utf-8") as f:
            q = json.load(f)
        norb = {v["match_id"]: v for v in q.get("verdicts", [])}

    out_rows = []
    for p in predictions.get("predictions", []):
        qualite = quality_by_id.get(p["id"], "basse")
        top3, score, bucket = compute_match(p, qualite)
        fv = (norb.get(p["id"]) or {})
        out_rows.append({
            "id": p["id"], "match": p.get("match"), "verdict_modele": p.get("verdict"),
            "bucket": bucket, "score_commun": score,
            "no_bet_recommande": bool(fv.get("no_bet_recommande")),
            "marches_exclus_qualitatifs": fv.get("marches_exclus", []),
            "top3": top3,
            "quality_data": qualite,
        })

    out_rows.sort(key=lambda r: r["score_commun"], reverse=True)
    for i, r_ in enumerate(out_rows, 1):
        r_["rang_global"] = i

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "methode": ("Top 3 = tri par EV desc puis p_modele desc, marchés SORTIS du filtre "
                    "qualitatif borné. Score commun 01-10 = 30% qualité data + 40% proba max "
                    "+ 30% edge EV. Buckets : >=7 HAUTE, >=5 MOYENNE, <5 FAIBLE. "
                    "Le score est comparable entre matchs et entre campagnes."),
        "source_predictions": os.path.basename(args.predictions),
        "matchs": out_rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # -------- ../TOP3.md / message /data ------------------------------------
    lines = [f"### 🛡️ {FEEDER_TITRE}", "",
             f"*generated {out['generated_at']} — {len(out_rows)} matchs classés*", ""]
    for r_ in out_rows:
        badge = ("🔴 NO BET (qual.)" if r_["no_bet_recommande"] else
                 "🟢 " + r_["bucket"])
        excl = f" · marchés exclus: {', '.join(r_['marches_exclus_qualitatifs'])}" if r_["marches_exclus_qualitatifs"] else ""
        lines.append(f"- **#{r_['rang_global']} {r_['match']}** — score **{r_['score_commun']}/10** "
                     f"— bucket {badge} (données {r_['quality_data']}){excl}")
        if not r_["top3"]:
            lines.append("    NO BET — Zero Data, Zero Calc (stats absentes, aucune proba).")
        for s in r_["top3"]:
            lines.append(f"    {s['rang']}. {s['selection_label']} — cote {s['cote']} — "
                         f"proba {s['p_modele']:.0%} — EV {s['ev']:+.1%}" if s.get("p_modele") is not None else
                         f"    {s['rang']}. {s['selection_label']} — cote {s['cote']} — EV {s['ev']:+.1%}")
    lines.append("")
    lines.append("🪙 _Jeu responsable : le pari est un divertissement. Les probabilités ne sont pas des certitudes._")
    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[TOP3] {len(out_rows)} matchs — score des {min(3, len(out_rows))} premiers :")
    for r_ in out_rows[:3]:
        print(f"  #{r_['rang_global']} {r_['match']:<32} score {r_['score_commun']}/10 bucket {r_['bucket']}")
    print(f"[TOP3] JSON : {args.out_json}")
    print(f"[TOP3] MD   : {args.out_md}")


if __name__ == "__main__":
    main()
