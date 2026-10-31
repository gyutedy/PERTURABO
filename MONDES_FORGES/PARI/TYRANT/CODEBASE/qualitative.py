"""
TYRANT — FILTRE QUALITATIF BORNÉ (infos non binaires)
=====================================================
Les infos non binaires (blessures, suspensions, fatigue, enjeux, météo,
motivation…) N'ENTRENT JAMAIS dans les calculs F02/F03 (Poisson / Dixon-Coles).
Ce filtre, applied APRÈS F03, est borné et n'a que trois effets possibles :
  1. EXCLURE des marchés éligibles (ex. fatigue élevé → MT2/MTÉ sortent).
  2. MONTER le seuil d'EV exigé (ex. +3 points de marge exigés).
  3. RECOMMANDER le NO BET (2 thèmes à impact élevé, ou 1 élevé + data basse).
Il ne crée jamais de probabilité, n'ajoute jamais de +EV.

Entrées :
  --predictions F03_FORGEWARD/OUT/predictions.json
  --notes      ARCHIVUM/fixtures/notes_qualitatives.json   (contrat schema_notes_qualitatives.json)
  --analysis   F02_BREACHER/OUT/analysis.json             (pour la qualité data)
Sorties :
  --out-verdict  TYRANT/OUT/qualitative_verdict.json
  --out-filtered F03_FORGEWARD/OUT/predictions_filtered.json

Usage:
  python qualitative.py --predictions ../../F03_FORGEWARD/OUT/predictions.json \\
      --notes ../../ARCHIVUM/fixtures/notes_qualitatives.json \\
      --analysis ../../F02_BREACHER/OUT/analysis.json
"""

import json
import argparse
import os
from datetime import datetime, timezone

# --- Table bornée de règles (macro → preset par impact) -----------------------
# effets = (marches_exclus[selection codes], bonus_seuil_ev)
RULES = {
    "default": {"eleve": ([], 0.02), "moyen": ([], 0.01), "faible": ([], 0.0), "inconnu": ([], 0.03)},
    "fatigue": {
        "eleve": (["mt2", "mte"], 0.04),      # la signature MT2 repose sur l'énergie en fin de match
        "moyen": ([], 0.02),
        "faible": ([], 0.0),
    },
    "blessures": {
        "eleve": ([], 0.03),                  # incertitude sur l'effectif → marge exigée plus haute
        "moyen": ([], 0.01),
        "faible": ([], 0.0),
    },
    "suspensions": {
        "eleve": ([], 0.03),
        "moyen": ([], 0.01),
        "faible": ([], 0.0),
    },
    "enjeux": {
        "eleve": ([], 0.03),                  # contexte de match corse → méfiance
        "moyen": ([], 0.01),
        "faible": ([], 0.0),
    },
    "meteo": {
        "eleve": (["o2.5", "o3.5"], 0.02),    # pluie/neige → buts attendus fragilisés
        "moyen": ([], 0.01),
        "faible": ([], 0.0),
    },
    "motivation": {
        "eleve": ([], 0.02),
        "moyen": ([], 0.01),
        "faible": ([], 0.0),
    },
}

IMPACTS = {"eleve", "moyen", "faible", "inconnu"}


def normalize_impacts(note: dict):
    """Impact par thème, une seule ligne par thème ; impact non reconnu = 'inconnu'
    (pour défavorable : jamais gratuit)."""
    themes = {}
    for theme, tinfo in (note.get("themes") or {}).items():
        if tinfo is None:
            continue
        if isinstance(tinfo, str):
            impact, detail = tinfo, ""
        else:
            impact = (tinfo.get("impact") or "inconnu").lower()
            detail = tinfo.get("detail") or ""
        if impact not in IMPACTS:
            impact = "inconnu"
        themes[theme.lower()] = {"impact": impact, "detail": detail}
    return themes


def note_themes_for_tyrant(note: dict):
    """Projection OUT seulement. items F00 priment ; themes v2 opérateur inchangés."""
    items = note.get("items") or []
    if items:
        projected = {}
        for it in items:
            if (it.get("verdict") or "").upper() != "OUT":
                continue
            th = (it.get("theme") or "autre").lower()
            projected[th] = {"impact": it.get("impact") or "eleve", "detail": it.get("detail") or ""}
        if projected:
            return projected
        return {}
    return note.get("themes") or {}


def apply_qualitative(predictions: dict, analysis: dict, notes: dict):
    """Applique le filtre borné. Retourne (verdict_qualitatif, predictions_filtrées)."""
    if int(notes.get("notes_count") or 0) == 0 and not any(
            (n.get("themes") or n.get("items")) for n in notes.get("notes") or []):
        empty_v = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "methode": "filtre qualitatif BORNÉ — notes_count 0, aucun effet.",
            "source_notes": notes.get("source") or "f00_vote",
            "verdicts": [],
        }
        return empty_v, json.loads(json.dumps(predictions))
    qual_by_id = {a["id"]: a.get("data_quality", {}).get("niveau", "basse") for a in analysis.get("analyses", [])}
    note_by_id = {n["match_id"]: n for n in notes.get("notes", []) if n.get("match_id")}

    verdicts = []
    filtered_cp = json.loads(json.dumps(predictions))  # copie profonde indépendante

    for p in filtered_cp["predictions"]:
        note = note_by_id.get(p["id"])
        if note is None:
            plabel = (p.get("match") or "").lower()
            for n in notes.get("notes") or []:
                if n.get("dom") and n.get("ext") and n.get("dom").lower() in plabel and n.get("ext").lower() in plabel:
                    note = n
                    break
        raw = note_themes_for_tyrant(note) if note else {}
        themes = normalize_impacts({"themes": raw}) if raw else {}
        excluded, bonus_total, elevates = set(), 0.0, 0
        for th, info in themes.items():
            rule = RULES.get(th, RULES["default"])
            marches_e, bonus = rule.get(info["impact"], rule.get("inconnu", ([], 0.02)))
            excluded.update(marches_e)
            bonus_total += bonus
            if info["impact"] == "eleve":
                elevates += 1

        quality = qual_by_id.get(p["id"], "basse")
        no_bet_rec = (elevates >= 2) or (elevates >= 1 and quality == "basse") or (bonus_total >= 0.06 and quality != "haute")

        seuil_base = predictions.get("seuil_ev_applique", 0.03)
        for s in p["selections"]:
            sq = s.setdefault("notes_qualitatives", {"themes": themes or None})
            if s.get("verdict") == "NO_BET":
                continue
            eff_seuil = seuil_base + bonus_total
            s["seuil_ev_effectif"] = round(eff_seuil, 4)
            reasons = sq.get("raisons", [])
            if s["selection"] in excluded:
                s["verdict"] = "NO_BET"
                s["mise_units"] = None
                reasons.append("marché exclu par le filtre qualitatif (non-binaire)")
            elif s["ev"] < eff_seuil:
                s["verdict"] = "NO_BET"
                s["mise_units"] = None
                reasons.append(f"EV {s['ev']:.1%} < seuil effectif {eff_seuil:.1%} (bonus qualitatif)")
            if reasons:
                sq["raisons"] = reasons

        if no_bet_rec:
            p["verdict"] = "NO_BET"
            p["meilleure_ev"] = min(p.get("meilleure_ev") or 0, 0)
            for s in p["selections"]:
                if s.get("verdict") != "NO_BET":
                    s["verdict"] = "NO_BET"
                s.setdefault("notes_qualitatives", {"themes": themes or None})
                s["mise_units"] = None
                sq = s["notes_qualitatives"]
                if "themes" not in sq:
                    sq["themes"] = themes or None
                rss = sq.setdefault("raisons", [])
                if not any("NO BET recommandé" in x for x in rss):
                    rss.append("NO BET recommandé par le filtre qualitatif (impact non-binaire trop élevé)")

        verdicts.append({
            "match_id": p["id"], "themes": themes,
            "n_impacts_eleves": elevates, "bonus_seuil_ev": round(bonus_total, 3),
            "marches_exclus": sorted(excluded), "quality_data": quality,
            "no_bet_recommande": no_bet_rec,
        })

    verdict_out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "methode": "filtre qualitatif BORNÉ (exclusion de marches / hausse du seuil d'EV / NO BET recommandé). "
                   "Jamais de probabilité ajoutée.",
        "source_notes": notes.get("source") or "operateur (notes non binaires)",
        "verdicts": verdicts,
    }
    return verdict_out, filtered_cp


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description="TYRANT — filtre qualitatif borné")
    p.add_argument("--predictions", required=True)
    p.add_argument("--notes", required=True)
    p.add_argument("--analysis", default=None)
    p.add_argument("--out-verdict", default=os.path.join(here, "..", "OUT", "qualitative_verdict.json"))
    p.add_argument("--out-filtered", default=os.path.join(here, "..", "..", "F03_FORGEWARD", "OUT", "predictions_filtered.json"))
    args = p.parse_args()

    with open(args.predictions, encoding="utf-8") as f:
        predictions = json.load(f)
    with open(args.notes, encoding="utf-8") as f:
        notes = json.load(f)
    analysis = []
    if args.analysis and os.path.exists(args.analysis):
        with open(args.analysis, encoding="utf-8") as f:
            analysis = json.load(f)

    verdict_out, filtered = apply_qualitative(predictions, analysis, notes)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_verdict)), exist_ok=True)
    with open(args.out_verdict, "w", encoding="utf-8") as f:
        json.dump(verdict_out, f, indent=2, ensure_ascii=False)
    with open(args.out_filtered, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    print(f"[TYRANT-Q] {len(verdict_out['verdicts'])} verdicts qualitatifs — sorties :")
    print(f"  verdict   → {args.out_verdict}")
    print(f"  filtré    → {args.out_filtered}")
    nb_rec = sum(1 for v in verdict_out["verdicts"] if v["no_bet_recommande"])
    print(f"  NO BET recommandé: {nb_rec}/{len(verdict_out['verdicts'])}")


if __name__ == "__main__":
    main()
