"""
F05 PACKAGER — COMBINEINGS + BACKROLL (v2, Phases 4)
=====================================================
L'opérateur demande : nombre de tickets + nombre de matchs par ticket.
Le monde forger compose les tickets depuis le Top 3 / score commun :

  /— Classe A : les matchs au score/bucket le plus élevé (HAUTE d'abord,
  |   puis meilleurs scores) → c'est le TICKET SÛR.
  /— Les autres (MOYENNE, jamais FAIBLE ni NO PAY recommandé) → répartis
      équitablement dans les autres tickets.

Règle « trop complexe à gagner » : si nb jambes demandées > --jambes-max
(défaut 4), le monde DIVISE : le haut des scores dans un ticket, le reste
dans l'autre — jamais une mosaïque de 8 jambes.

BACKROLL / BUDGET (retour de l'opérateur:  « aujour-1 je mets 6000 FC, 3000 FC
sur le ticket sûr, 1000 FC sur chacun des autres ») :
  --budget-fc 6000 --surticket-fc 3000
  → le reste (3000) est divisé équitablement entre les autres tickets ; si un
    ticket reste « bas » (moins de --mise-min-fc par ticket) → warning (pas de mise).
  Version libre : --mises-fc 3000:1000:1000 (déclaration explicite).

Entrées : F03 top3.json (+ veredict qualitatif), budget opérateur.
Sortie  : F05_PACKAGER/OUT/tickets.json   (contrat schema_ticket_final.json)
          SHARED/OUT/TICKETS.md           (résumé Telegram)
"""

import json
import argparse
import os
from datetime import datetime, timezone
import math

JAMBES_MAX_DEF = 4   # au-delà : division en deux classes (A puis B)


def _parse_mises(free_spec):
    """Parse "3000:1000:1000" if valid."""
    vals = [float(x) for x in free_spec.split(":") if x.strip()]
    return vals


def allocate(top3_events, tickets, jambes_by_ticket, surticket_fc, budget_fc,
            mises_free, jambes_max=JAMBES_MAX_DEF, mise_min=100.0, taux=None):
    """Compose les tickets + allocation de backroll. Renvoie (tickets sort, warnings)."""
    warnings = []
    eligible = [w for w in top3_events if not w.get("no_bet_recommande")
                and w.get("bucket") != "FAIBLE"
                and any((w.get("top3") or []))]
    eligible.sort(key=lambda e: (-e["score_commun"], e["rang_global"]))

    if not eligible:
        return {"tickets": [], "budget": {"budget_fc": budget_fc, "alloue_fc": 0,
                "reste_fc": budget_fc}, "warnings": ["Aucun match éligible (buckets FAIBLE / NO BET) — budget non engagé"]}

    # Compositions : classe A (les meilleurs) puis B (les autres) si trop long
    jambes_max = max(1, jambes_max)
    tickets_out = []
    pool = list(eligible)

    # nombre de jambes par ticket demandé par l'opérateur
    jbt = jambes_by_ticket or []
    if len(jbt) < tickets:
        jbt = list(jbt) + [2] * (tickets - len(jbt))
    if max(jbt) > jambes_max:
        warnings.append(f"{max(jbt)} jambes demandées > {jambes_max} → division en deux classes de fiabilité (A puis B)")

    # Ticket 1 (SÛR) : les matchs au score le plus élevé (buckets HAUTE d'abord)
    j1 = min(max(2, jbt[0]), min(len(pool), jambes_max))
    ticket_defs = []
    cl_a = pool[:j1]
    ticket_defs.append((j1, cl_a))
    pool_b = pool[j1:]

    rest_tick = max(0, tickets - 1)
    for k in range(rest_tick):
        if not pool_b:
            break
        # repartition équitable du RESTE entre les tickets restants (à chaque iteration)
        per = max(1, math.ceil(len(pool_b) / max(1, rest_tick - k)))
        jk = min(max(1, jbt[k + 1] if k + 1 < len(jbt) else jbt[-1]), jambes_max)
        chunk = pool_b[:max(jk, per)]
        ticket_defs.append((jk, chunk[:jk] if chunk else chunk))
        pool_b = pool_b[len(chunk):]

    # — Allocation backroll —
    mises = None
    if mises_free:
        mises = _parse_mises(mises_free)
        if len(mises) < tickets:
            mises = list(mises) + [None] * (tickets - len(mises))
    reste = max(0.0, budget_fc - surticket_fc)
    per_other = round(reste / max(1, rest_tick), 2) if rest_tick > 0 else 0.0
    for i, (nj, jambes) in enumerate(ticket_defs):
        jambes = (jambes or [])[:nj]
        if not jambes:
            continue
        cote_totale = 1.0
        sel_list = []
        for e in jambes:
            top = (e["top3"] or [])[0]
            sel_list.append({"match_id": e["id"], "match": e["match"],
                             "selection": top["selection"], "selection_label": top["selection_label"],
                             "cote": top["cote"], "p_modele": top.get("p_modele"),
                             "score_commun": e["score_commun"]})
            cote_totale *= float(top["cote"] or 1)
        if i == 0:
            mise = surticket_fc
            classe = "SUR_TICKET"
        else:
            if mises is not None and i < len(mises) and mises[i] is not None:
                mise = mises[i]
            else:
                mise = per_other
        if mise < mise_min:
            warnings.append(f"Ticket {i+1} : mise {mise} FC < minimum {mise_min} FC — ticket affiché hors mise")
            mise = 0.0
        units = None
        if taux:
            units = round((mise / taux) / 100.0, 2)   # 1u = 1% de la bankroll
        p_agg = 1.0
        for s in sel_list:
            p_agg *= (s.get("p_modele") or 0.5)
        tickets_out.append({
            "rang_ticket": i + 1, "classe": classe if i == 0 else ("AUTRE" if (not mises or mises[i] is None) else "FILE_MIXTE"),
            "nb_jambes": len(sel_list), "jambes": sel_list,
            "cote_totale": round(cote_totale, 2), "p_aggregee": round(p_agg, 3),
            "ev_limitee": None, "mise_fc": mise, "mise_units": units,
            "retour_si_gagne_fc": round(mise * cote_totale, 2),
        })

    alloue = sum(t["mise_fc"] for t in tickets_out)
    out = {"tickets": tickets_out,
           "budget": {"budget_fc": budget_fc, "alloue_fc": alloue, "reste_fc": round(budget_fc - alloue, 2),
                      "taux_fc_usd": taux},
           "regles": {"jambes_max": jambes_max, "mise_min_fc": mise_min,
                      "classe_sur_ticket": "matchs au score le plus haut (buckets puis top3)",
                      "division": f"> {jambes_max} jambes → division en deux classes de fiabilité"}}
    return out, warnings


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    arg = argparse.ArgumentParser(description="F05 — combinaisons + backroll")
    arg.add_argument("--top3", default=os.path.join(here, "..", "..", "F03_FORGEWARD", "OUT", "top3.json"))
    arg.add_argument("--tickets", type=int, default=3, help="nb de tickets demandés par l'opérateur")
    arg.add_argument("--jambes", default=None, help="nb de matchs par ticket, ex: 3 ou 3:2:2")
    arg.add_argument("--budget-fc", type=float, default=0.0, help="budget du jour en FC (backroll)")
    arg.add_argument("--surticket-fc", type=float, default=0.0, help="mise du ticket sûr en FC")
    arg.add_argument("--mises-fc", default=None, help="alternativement, mises explicites 3000:1000:1000")
    arg.add_argument("--jambes-max", type=int, default=JAMBES_MAX_DEF)
    arg.add_argument("--mise-min-fc", type=float, default=100.0)
    arg.add_argument("--taux-fc-usd", type=float, default=None, help="taux FC → USD (pour les unités 1u=1% bankroll)")
    arg.add_argument("--out-json", default=os.path.join(here, "..", "OUT", "tickets.json"))
    arg.add_argument("--out-md", default=os.path.join(here, "..", "..", "SHARED", "OUT", "TICKETS.md"))
    args = arg.parse_args()

    with open(args.top3, encoding="utf-8") as f:
        top3 = json.load(f)

    jbt = [int(x) for x in (args.jambes or "").split(":") if x.strip()] or []
    res, wrn = allocate(
        top3.get("matchs", []), tickets=max(1, args.tickets), jambes_by_ticket=jbt,
        surticket_fc=args.surticket_fc, budget_fc=args.budget_fc,
        mises_free=args.mises_fc, jambes_max=args.jambes_max,
        mise_min=args.mise_min_fc, taux=args.taux_fc_usd)

    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           **res, "warnings": [*wrn, *top3_wrn_from_warnings(top3)]}
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # — MD (résumé Telegram) —
    lines = ["### 🎫 TICKETS DU JOUR — PERTURABO", "",
             f"*budget : {out['budget']['budget_fc']:.0f} FC · alloué {out['budget']['alloue_fc']:.0f} FC · "
             f"reste {out['budget']['reste_fc']:.0f} FC*", ""]
    for t in out["tickets"]:
        jambs = " + ".join(f"{j['match']} ({j['selection_label']} @ {j['cote']})" for j in t["jambes"])
        lines.append(f"**T${t['rang_ticket']}** [{t['classe']}] {t['nb_jambes']} jambes — "
                     f"cote {t['cote_totale']} — proba {t['p_aggregee']*100:.0f}% — mise **{t['mise_fc']:.0f} FC**")
        lines.append(f"    {jambs}")
    for w in out["warnings"]:
        lines.append(f"⚠️ {w}")
    lines.append("")
    lines.append("🪙 Mise max 3% bankroll · pas de martingale · ledger F06 prend TOUS les tickets.")
    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[COMBINATOR] {len(out['tickets'])} tickets — budget alloué {out['budget']['alloue_fc']:.0f}/"
          f"{out['budget']['budget_fc']:.0f} FC")
    for t in out["tickets"]:
        print(f"  T{t['rang_ticket']} [{t['classe']:<11}] {t['nb_jambes']} jambes cote {t['cote_totale']:>6} "
              f"— mise {t['mise_fc']:>8.0f} FC")
    for w in out["warnings"]:
        print(f"  ⚠️ {w}")
    print(f"[COMBINATOR] JSON : {args.out_json}")


def top3_wrn_from_warnings(top3):
    w = []
    nb = sum(1 for r_ in top3.get("matchs", []) if r_.get("no_bet_recommande"))
    if nb:
        w.append(f"{nb} match(s) NO BET recommandé (filtre qualitatif) — exclus des tickets")
    faible = sum(1 for r_ in top3.get("matchs", []) if r_.get("bucket") == "FAIBLE")
    if faible:
        w.append(f"{faible} match(s) bucket FAIBLE — exclus des tickets")
    return w


if __name__ == "__main__":
    main()
