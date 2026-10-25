"""
F03 FORGEWARD — La forge de la valeur (EV, Kelly, combinés)
============================================================
De-marging des cotes Winner Bet (normalisation overround), calcul de l'Expected
Value par marché, mise ¼ Kelly plafonnée, scanner de combinés.

Doctrine :
  EV = P_modèle × cote − 1
  Seuil : +3% (Top 5) / +8% (exotique) [profil Warsmith]
  VALUE  : EV ≥ seuil → mise proposée
  THIN   : 0 < EV < seuil  → passable, mise réduite (½ Kelly)
  NO BET : EV ≤ 0, ou données insuffisantes
  Combiné : jambes indépendantes toutes +EV, EV_comb = Π(1+EV_i)−1,
            ⅛ Kelly, max 1u, max 3 jambes.

Usage:
  python forgeward.py --analysis F02_BREACHER/OUT/analysis.json \
                      --fixture ../.../fixtures/matches.json \
                      --profile ../../ARCHIVUM/rules/warsmith_profile.json
"""

import json
import argparse
import os
from datetime import datetime, timezone

# Groupes de marchés mutuellement exclusifs (pour le de-marging)
MARKET_GROUPS = [
    ("1X2", ["1", "X", "2"]),
    ("OU_2.5", ["o2.5", "u2.5"]),
    ("MT_PROLIFIQUE", ["mt1", "mte", "mt2"]),
]
SELECTION_LABELS = {
    "1": "Victoire Domicile", "X": "Nul", "2": "Victoire Extérieur",
    "o2.5": "Over 2.5", "u2.5": "Under 2.5",
    "mt1": "1re MT plus prolifique", "mte": "Égalité de mi-temps",
    "mt2": "2e MT plus prolifique", "btts": "Les deux marquent",
}


def de_marge(cotes: dict):
    """Par groupe de marchés : proba implicite normalisée (no-vig) + overround."""
    novig = {}
    overrounds = {}
    for _groupe, keys in MARKET_GROUPS:
        present = {k: cotes[k] for k in keys if cotes.get(k)}
        if len(present) < 2:
            continue
        s = sum(1 / v for v in present.values())
        for k, v in present.items():
            novig[k] = (1 / v) / s
        overrounds.setdefault("marches", {}).__setitem__(keys[0], round(s - 1, 4))
    return novig, overrounds


def kelly(p: float, cote: float, fraction: float) -> float:
    """Fraction de bankroll : 0 si edge négatif."""
    edge = p * cote - 1
    if edge <= 0 or cote <= 1:
        return 0.0
    return fraction * edge / (cote - 1)


def predict_match(m: dict, analysis: dict, pool: dict, tier: str):
    seuil = pool["seuil_ev_top5"] if tier == "top5" else pool["seuil_ev_exotique"]
    out_item = {
        "id": m["id"], "match": f"{m['dom']} vs {m['ext']}",
        "selections": [], "verdict": "NO_BET", "meilleure_ev": None,
    }
    probs = {k: v for k, v in analysis["probas"].items()}
    single_verdicts = []
    for sel, cote in (m.get("cotes") or {}).items():
        p = probs.get(sel)
        if p is None:
            continue
        mise_max = pool["mise_max_pct_bankroll"] if tier == "top5" else pool["mise_max_pct_exotique"]
        ev = p * cote - 1
        quality = analysis["data_quality"]["niveau"]
        if quality == "basse" or "mj_insuffisant" in analysis["data_quality"]["flags"]:
            verdict = "NO_BET"
        elif ev >= seuil:
            verdict = "VALUE"
        elif ev > 0:
            verdict = "THIN"
        else:
            verdict = "NO_BET"
        mise = None
        if verdict == "VALUE":
            f = kelly(p, cote, pool["kelly_fraction"])
        elif verdict == "THIN":
            f = kelly(p, cote, pool["kelly_fraction"] / 2)
        if verdict in ("VALUE", "THIN") and f:
            f = min(f, mise_max)
            mise = round(f * 100, 2)  # 1u = 1% bankroll
        out_item["selections"].append({
            "marche": next((g for g, ks in MARKET_GROUPS for kk in ks if kk == sel), None) or "BTTS",
            "selection": sel,
            "selection_label": SELECTION_LABELS.get(sel, sel),
            "cote": cote,
            "cote_juste_marche": None,
            "p_modele": round(p, 4),
            "ev": round(ev, 4),
            "verdict": verdict,
            "mise_units": mise,
        })
        single_verdicts.append(verdict)
        if out_item["meilleure_ev"] is None or ev > out_item["meilleure_ev"]:
            out_item["meilleure_ev"] = round(ev, 4)

    # De-marging propre (no-vig) par groupe
    novig, _ = de_marge(m.get("cotes") or {}) if m.get("cotes") else ({}, None)
    for sel_obj in out_item["selections"]:
        sel_obj["cote_juste_marche"] = (
            round(1 / novig[sel_obj["selection"]], 3) if sel_obj["selection"] in novig else None
        )

    if any(v == "VALUE" for v in single_verdicts):
        out_item["verdict"] = "GO"
    elif any(v == "THIN" for v in single_verdicts):
        out_item["verdict"] = "THIN"
    return out_item


def build_predications(intel, analyses, profile):
    pool = {
        "seuil_ev_top5": profile.get("seuil_ev_top5", 0.03),
        "seuil_ev_exotique": profile.get("seuil_ev_exotique", 0.08),
        "kelly_fraction": profile.get("kelly_fraction", 0.25),
        "mise_max_pct_bankroll": profile.get("mise_max_pct_bankroll", 0.05),
        "mise_max_pct_exotique": profile.get("mise_max_pct_exotique", 0.03),
    }
    tier = intel.get("ligue_tier", "exotique")
    by_id = {a["id"]: a for a in analyses}
    predictions = [predict_match(m, by_id[m["id"]], pool, tier) for m in intel["matchs"] if m["id"] in by_id]

    # Combinés : jambes VALUE indépendants (match différents), max 3 jambes
    jambes = sorted(
        (dict(s, match_id=p["id"]) for p in predictions for s in p["selections"] if s["verdict"] == "VALUE"),
        key=lambda s: s["ev"], reverse=True,
    )
    combines = []
    if len(jambes) >= 2:
        best = jambes[:3]
        ev_comb = 1.0
        for s in best:
            ev_comb *= (1 + s["ev"])
        ev_comb -= 1
        p_tot = 1.0
        c_tot = 1.0
        for s in best:
            p_tot *= s["p_modele"]
            c_tot *= s["cote"]
        f = kelly(p_tot, c_tot, profile.get("combiné_kelly_fraction", 0.125)) if p_tot * c_tot > 1 and c_tot > 1 else 0.0
        mise = round(min(f * 100, 1.0), 2)  # max 1u
        combines.append({
            "jambes": [{"match_id": s["match_id"], "selection": s["selection"],
                        "cote": s["cote"], "p_modele": s["p_modele"]} for s in best],
            "cote_totale": round(c_tot, 2),
            "ev_combine": round(ev_comb, 4),
            "mise_units": mise,
        })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seuil_ev_applique": pool["seuil_ev_top5" if tier == "top5" else "seuil_ev_exotique"],
        "ligue_tier": tier,
        "predictions": predictions,
        "combines": combines,
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="F03 FORGEWARD — EV/Kelly PARI")
    parser.add_argument("--intel", required=True, help="F01_SENTINEL/OUT/matches_intel.json")
    parser.add_argument("--analysis", required=True, help="F02_BREACHER/OUT/analysis.json")
    parser.add_argument("--profile", default=os.path.join(here, "..", "..", "ARCHIVUM", "rules", "warsmith_profile.json"))
    parser.add_argument("--output", default=os.path.join(here, "..", "OUT", "predictions.json"))
    args = parser.parse_args()

    with open(args.intel, "r", encoding="utf-8") as f:
        intel = json.load(f)
    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    with open(args.profile, "r", encoding="utf-8") as f:
        profile = json.load(f)

    out = build_predications(intel, analysis["analyses"], profile)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    values = sum(1 for p in out["predictions"] if p["verdict"] == "GO")
    nogay = sum(1 for p in out["predictions"] if p["verdict"] == "NO_BET")
    print(f"[FORGEWARD] seuil EV: {out['seuil_ev_applique']:.0%} (tier: {out['ligue_tier']})")
    print(f"[FORGEWARD] {values} matchs GO / {nogay} NO BET / {len(out['predictions'])} au total")
    for p in out["predictions"]:
        if p["verdict"] == "GO":
            best = max(p["selections"], key=lambda s: s["ev"])
            mise = next(s["mise_units"] for s in p["selections"] if s["verdict"] == "VALUE") or 0
            print(f"  🔥 {p['match']:<28} {best['selection']:<6} cote {best['cote']:<5} EV {best['ev']:+.1%} → mise {mise}u")
    if out["combines"]:
        c = out["combines"][0]
        print(f"  🧩 COMBINÉ {len(c['jambes'])} jambes — cote {c['cote_totale']} — EV {c['ev_combine']:+.1%} → {c['mise_units']}u")
    print(f"[FORGEWARD] Sortie: {args.output}")


if __name__ == "__main__":
    main()
