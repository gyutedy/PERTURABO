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
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_BREACHER = os.path.normpath(os.path.join(_HERE, "..", "..", "F02_BREACHER", "CODEBASE"))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
if _BREACHER not in sys.path:
    sys.path.insert(0, _BREACHER)
import breacher as _breacher  # noqa: E402
import devig as _devig  # noqa: E402
import kelly_route as _kelly_route  # noqa: E402

# Groupes de marchés mutuellement exclusifs (pour le de-marging)
MARKET_GROUPS = [
    ("1X2", ["1", "X", "2"]),
    ("OU_0.5", ["o0.5", "u0.5"]),
    ("OU_1.5", ["o1.5", "u1.5"]),
    ("OU_2.5", ["o2.5", "u2.5"]),
    ("OU_3.5", ["o3.5", "u3.5"]),
    ("OU_4.5", ["o4.5", "u4.5"]),
    ("DC", ["dc_1x", "dc_x2", "dc_12"]),
    ("TT_H_0.5", ["tt_h_o0.5", "tt_h_u0.5"]),
    ("TT_H_1.5", ["tt_h_o1.5", "tt_h_u1.5"]),
    ("TT_H_2.5", ["tt_h_o2.5", "tt_h_u2.5"]),
    ("TT_A_0.5", ["tt_a_o0.5", "tt_a_u0.5"]),
    ("TT_A_1.5", ["tt_a_o1.5", "tt_a_u1.5"]),
    ("TT_A_2.5", ["tt_a_o2.5", "tt_a_u2.5"]),
    ("MT_PROLIFIQUE", ["mt1", "mte", "mt2"]),
    ("BTTS", ["btts", "btts_no"]),
]
SELECTION_LABELS = {
    "1": "Victoire Domicile", "X": "Nul", "2": "Victoire Extérieur",
    "o0.5": "Over 0.5", "u0.5": "Under 0.5",
    "o1.5": "Over 1.5", "u1.5": "Under 1.5",
    "o2.5": "Over 2.5", "u2.5": "Under 2.5",
    "o3.5": "Over 3.5", "u3.5": "Under 3.5",
    "o4.5": "Over 4.5", "u4.5": "Under 4.5",
    "dc_1x": "Double chance 1X", "dc_x2": "Double chance X2", "dc_12": "Double chance 12",
    "tt_h_o0.5": "Team total domicile Over 0.5", "tt_h_u0.5": "Team total domicile Under 0.5",
    "tt_h_o1.5": "Team total domicile Over 1.5", "tt_h_u1.5": "Team total domicile Under 1.5",
    "tt_h_o2.5": "Team total domicile Over 2.5", "tt_h_u2.5": "Team total domicile Under 2.5",
    "tt_a_o0.5": "Team total exterieur Over 0.5", "tt_a_u0.5": "Team total exterieur Under 0.5",
    "tt_a_o1.5": "Team total exterieur Over 1.5", "tt_a_u1.5": "Team total exterieur Under 1.5",
    "tt_a_o2.5": "Team total exterieur Over 2.5", "tt_a_u2.5": "Team total exterieur Under 2.5",
    "mt1": "1re MT plus prolifique", "mte": "Égalité de mi-temps",
    "mt2": "2e MT plus prolifique", "btts": "Les deux marquent", "btts_no": "Les deux ne marquent pas",
}

def marche_of(sel):
    for g, ks in MARKET_GROUPS:
        if sel in ks:
            return g
    if _breacher.score_key(sel):
        return "CS"
    return "BTTS"


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
    cs = analysis.get("cs") or {}
    bonus = _devig.load_bonus()
    cotes = m.get("cotes") or {}
    by_group = {}
    by_group_add = {}
    for g, keys in MARKET_GROUPS:
        present = {k: cotes[k] for k in keys if cotes.get(k)}
        if present:
            by_group[g] = _devig.multiplicative(present)
            by_group_add[g] = _devig.additive(present)
    single_verdicts = []
    for sel, cote in cotes.items():
        p = probs.get(sel)
        if p is None:
            sk = _breacher.score_key(sel)
            if sk and sk in cs:
                p = cs[sk]
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
        f = None
        if verdict == "VALUE":
            f = kelly(p, cote, pool["kelly_fraction"])
        elif verdict == "THIN":
            f = kelly(p, cote, pool["kelly_fraction"] / 2)
        if verdict in ("VALUE", "THIN") and f:
            f = min(f, mise_max)
            mise = round(f * 100, 2)  # 1u = 1% bankroll
        rec = {
            "marche": marche_of(sel),
            "selection": sel,
            "selection_label": SELECTION_LABELS.get(sel, sel),
            "cote": cote,
            "cote_juste_marche": None,
            "p_modele": round(p, 4),
            "ev": round(ev, 4),
            "verdict": verdict,
            "mise_units": mise,
        }
        grp = rec["marche"]
        dv = by_group.get(grp)
        if dv and dv.get("ok") and sel in (dv.get("p_fair") or {}):
            pf = dv["p_fair"][sel]
            rec["p_fair"] = round(pf, 4)
            rec["fair_odds"] = round(dv["fair_odds"][sel], 3)
            enet = _devig.edge_net_devig(p, cote, pf)
            rec["edge_net_devig"] = round(enet, 4) if enet is not None else None
            dc = _devig.double_confirmation(p, cote, pf, bonus_pt=bonus)
            rec["double_confirmation"] = dc.get("flag")
        else:
            rec["edge_net_devig"] = None
            rec["double_confirmation"] = None
            holes = list((dv or {}).get("holes") or [])
            if holes:
                rec["devig_holes"] = holes
        da = by_group_add.get(grp)
        gp = _devig.gap(dv, da) if dv is not None else {"ok": False, "gap_p": {}, "holes": ["multi_fail"]}
        if da and da.get("ok") and sel in (da.get("p_fair") or {}):
            rec["p_fair_additif"] = round(da["p_fair"][sel], 4)
            rec["fair_odds_additif"] = round(da["fair_odds"][sel], 3)
        else:
            rec["p_fair_additif"] = None
            rec["fair_odds_additif"] = None
            add_holes = list((da or {}).get("holes") or [])
            if add_holes:
                rec["devig_add_holes"] = add_holes
        if gp.get("ok") and sel in (gp.get("gap_p") or {}):
            rec["devig_gap"] = round(gp["gap_p"][sel], 6)
        else:
            rec["devig_gap"] = None
        out_item["selections"].append(rec)
        single_verdicts.append(verdict)
        if out_item["meilleure_ev"] is None or ev > out_item["meilleure_ev"]:
            out_item["meilleure_ev"] = round(ev, 4)

    # De-marging propre (no-vig) par groupe — tri EV inchange
    novig, _ = de_marge(cotes) if cotes else ({}, None)
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
    routed = _kelly_route.route_global()
    pool = {
        "seuil_ev_top5": profile.get("seuil_ev_top5", 0.03),
        "seuil_ev_exotique": profile.get("seuil_ev_exotique", 0.08),
        "kelly_fraction": routed["fraction"],
        "mise_max_pct_bankroll": profile.get("mise_max_pct_bankroll", 0.05),
        "mise_max_pct_exotique": profile.get("mise_max_pct_exotique", 0.03),
    }
    tier = intel.get("ligue_tier", "exotique")
    by_id = {a["id"]: a for a in analyses}
    predictions = []
    for m in intel.get("matchs") or []:
        if m["id"] in by_id:
            predictions.append(predict_match(m, by_id[m["id"]], pool, tier))
        else:
            predictions.append({
                "id": m["id"],
                "match": f"{m.get('dom', '?')} vs {m.get('ext', '?')}",
                "selections": [],
                "verdict": "NO_BET",
                "meilleure_ev": None,
            })

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
        combo_legs = [{"match_id": s["match_id"], "selection": s["selection"],
                       "cote": s["cote"], "p_modele": s["p_modele"]} for s in best]
        combo_route = _kelly_route.route_ticket(jambes=combo_legs)
        f = kelly(p_tot, c_tot, combo_route["fraction"]) if p_tot * c_tot > 1 and c_tot > 1 else 0.0
        mise = round(min(f * 100, 1.0), 2)  # max 1u
        combines.append({
            "jambes": combo_legs,
            "cote_totale": round(c_tot, 2),
            "ev_combine": round(ev_comb, 4),
            "mise_units": mise,
            "kelly_fraction": combo_route["fraction"],
            "kelly_label": combo_route["label"],
            "kelly_holes": list(combo_route.get("holes") or []),
        })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seuil_ev_applique": pool["seuil_ev_top5" if tier == "top5" else "seuil_ev_exotique"],
        "ligue_tier": tier,
        "kelly_fraction": routed["fraction"],
        "kelly_label": routed["label"],
        "kelly_holes": list(routed.get("holes") or []),
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
