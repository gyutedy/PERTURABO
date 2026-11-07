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
import sys
from datetime import datetime, timezone
import math

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORGE = os.path.normpath(os.path.join(_HERE, "..", "..", "F03_FORGEWARD", "CODEBASE"))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
if _FORGE not in sys.path:
    sys.path.insert(0, _FORGE)
import compose as _compose  # noqa: E402
import market_priority as _prio  # noqa: E402
import kelly_route as _kelly_route  # noqa: E402
import marches as _marches  # noqa: E402

JAMBES_MAX_DEF = 4
EV_COMBO_FLOOR = _marches.EV_COMBO_FLOOR


def _parse_mises(free_spec):
    """Parse "3000:1000:1000" if valid."""
    vals = [float(x) for x in free_spec.split(":") if x.strip()]
    return vals


EV_FLOOR = 0.03


def leg_key(match_id, marche, selection):
    return (str(match_id or ""), str(marche or ""), str(selection or ""))


def consumed_set(exclude_legs):
    s = set()
    for x in exclude_legs or []:
        if isinstance(x, dict):
            s.add(leg_key(x.get("match_id"), x.get("marche"), x.get("selection")))
        elif isinstance(x, (list, tuple)) and len(x) >= 3:
            s.add(leg_key(x[0], x[1], x[2]))
        elif isinstance(x, str) and "|" in x:
            a, b, c = (x.split("|", 2) + ["", ""])[:3]
            s.add(leg_key(a, b, c))
    return s


def apply_exclusion(events, exclude_legs, ev_floor=EV_FLOOR):
    """Retire (match, marche, selection) deja sortis. Prochain marche Top 3 libre.
    Plancher qualite fixe : pas FAIBLE, pas NO BET, EV >= floor. Jamais descendre."""
    consumed = consumed_set(exclude_legs)
    out = []
    for e in events:
        if e.get("no_bet_recommande") or e.get("bucket") == "FAIBLE":
            continue
        tops = []
        for top in e.get("top3") or []:
            key = leg_key(e.get("id"), top.get("marche"), top.get("selection"))
            if key in consumed:
                continue
            if not _marches.jambe_jouable(top):
                continue
            ev = top.get("ev")
            if ev is not None and float(ev) < ev_floor:
                continue
            tops.append(top)
        if not tops:
            continue
        e2 = dict(e)
        e2["top3"] = tops
        out.append(e2)
    return out


def _pick_jambes(events, nj, mono=False, ev_floor=EV_FLOOR, combo_floor=EV_COMBO_FLOOR):
    """1 match = 1 navire. Jamais 2 jambes du meme match. Jamais remplissage sous floor."""
    picked = []
    used = set()
    marche_ticket = None
    for e in events:
        mid = str(e.get("id") or "")
        if mid in used:
            continue
        tops = e.get("top3") or []
        if not tops:
            continue
        top = next((t for t in tops if _marches.jambe_jouable(t)), None)
        if top is None:
            continue
        m = _marches.canon_marche(top.get("marche"))
        if mono and marche_ticket is None:
            marche_ticket = m
        if mono and m != marche_ticket:
            continue
        ev = top.get("ev")
        try:
            if ev is None or float(ev) < ev_floor:
                continue
        except (TypeError, ValueError):
            continue
        jambe = {
            "match_id": e.get("id"), "match": e.get("match"),
            "marche": top.get("marche") or "",
            "selection": top.get("selection"),
            "selection_label": top.get("selection_label"),
            "cote": top.get("cote"), "p_modele": top.get("p_modele"),
            "ev": top.get("ev"), "bucket": e.get("bucket"),
            "score_commun": e.get("score_commun"),
            "verdict": top.get("verdict"),
            "scorer_eligible": top.get("scorer_eligible"),
            "edge_net_devig": top.get("edge_net_devig"),
            "devig_gap": top.get("devig_gap"),
            "p_fair_additif": top.get("p_fair_additif"),
        }
        trial = picked + [jambe]
        if len(trial) >= 2:
            cev = _marches.combo_ev(trial)
            if cev is not None and cev < combo_floor:
                continue
        picked.append(jambe)
        used.add(mid)
        if len(picked) >= nj:
            break
    return picked


def allocate(top3_events, tickets, jambes_by_ticket, surticket_fc, budget_fc,
            mises_free, jambes_max=JAMBES_MAX_DEF, mise_min=100.0, taux=None,
            exclude_legs=None, lots_box=None, n_mesures=None, prio_cfg=None,
            markets=None, mono=False, ev_floor=EV_FLOOR, combo_floor=EV_COMBO_FLOOR):
    """Compose les tickets + allocation de backroll. Renvoie (tickets sort, warnings)."""
    warnings = []
    if _marches.refuse_floor(ev_floor):
        return {"tickets": [], "budget": {"budget_fc": budget_fc, "alloue_fc": 0,
                "reste_fc": budget_fc}}, ["EV_FLOOR 0.03 inviolable — baisser le floor refuse"]
    pool_src = apply_exclusion(top3_events, exclude_legs, ev_floor=ev_floor)
    if markets is not None:
        pool_src = _marches.filter_events(pool_src, markets, ev_floor=ev_floor)
    eligible = [w for w in pool_src if not w.get("no_bet_recommande")
                and w.get("bucket") != "FAIBLE"
                and any(_marches.jambe_jouable(t) for t in (w.get("top3") or []))]
    if markets is not None:
        eligible.sort(key=lambda e: (-float((e.get("top3") or [{}])[0].get("ev") or 0),
                                    -e.get("score_commun", 0), e.get("rang_global", 0)))
    else:
        eligible.sort(key=lambda e: (-e["score_commun"], e["rang_global"]))

    if not eligible:
        msg = "0 match au-dessus du seuil — 0 ticket. Budget non engage."
        if markets is None:
            msg = "Aucun match éligible (buckets FAIBLE / NO BET) — budget non engagé"
        return {"tickets": [], "budget": {"budget_fc": budget_fc, "alloue_fc": 0,
                "reste_fc": budget_fc}}, [msg]

    jbt = jambes_by_ticket or []
    if len(jbt) < tickets:
        jbt = list(jbt) + [2] * (tickets - len(jbt))
    cap = _marches.jambes_cap(jbt, n_plus=10)
    jambes_max = max(1, cap)
    tickets_out = []
    pool = list(eligible)

    if max(jbt) > jambes_max:
        warnings.append(
            f"{max(jbt)} jambes demandees > {jambes_max} (1..n+10) — cap applique, pas de remplissage")

    j1 = min(max(1, jbt[0]), min(len(pool), jambes_max))
    ticket_defs = []
    cl_a = pool[:j1]
    ticket_defs.append((j1, cl_a))
    pool_b = pool[j1:]

    rest_tick = max(0, tickets - 1)
    for k in range(rest_tick):
        if not pool_b:
            break
        per = max(1, math.ceil(len(pool_b) / max(1, rest_tick - k)))
        jk = min(max(1, jbt[k + 1] if k + 1 < len(jbt) else jbt[-1]), jambes_max)
        chunk = pool_b[:max(jk, per)]
        ticket_defs.append((jk, chunk[:jk] if chunk else chunk))
        pool_b = pool_b[len(chunk):]

    cfg = prio_cfg if prio_cfg is not None else _prio.load_config()
    n_m = n_mesures if n_mesures is not None else _prio.n_tickets_mesures(lots_box=lots_box)

    # — Allocation backroll —
    mises = None
    if mises_free:
        mises = _parse_mises(mises_free)
        if len(mises) < tickets:
            mises = list(mises) + [None] * (tickets - len(mises))
    reste = max(0.0, budget_fc - surticket_fc)
    per_other = round(reste / max(1, rest_tick), 2) if rest_tick > 0 else 0.0
    for i, (nj, chunk) in enumerate(ticket_defs):
        sel_list = _pick_jambes(chunk, nj, mono=mono, ev_floor=ev_floor, combo_floor=combo_floor)
        if not sel_list:
            continue
        cote_totale = 1.0
        for jambe in sel_list:
            _prio.stamp_jambe(jambe, n=n_m, cfg=cfg, lots_box=lots_box)
            cote_totale *= float(jambe.get("cote") or 1)
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
        composed = _compose.compose_ticket(sel_list)
        rec = {
            "rang_ticket": i + 1, "classe": classe if i == 0 else ("AUTRE" if (not mises or mises[i] is None) else "FILE_MIXTE"),
            "nb_jambes": len(sel_list), "jambes": sel_list,
            "cote_totale": round(cote_totale, 2), "p_aggregee": round(p_agg, 3),
            "ev_limitee": None, "mise_fc": mise, "mise_units": units,
            "retour_si_gagne_fc": round(mise * cote_totale, 2),
            "ev_compose_net": composed.get("ev_compose_net"),
            "compose_flags": composed.get("compose_flags") or [],
            "compose_holes": composed.get("compose_holes") or [],
        }
        _kelly_route.stamp_ticket(rec)
        tickets_out.append(rec)

    alloue = sum(t["mise_fc"] for t in tickets_out)
    out = {"tickets": tickets_out,
           "budget": {"budget_fc": budget_fc, "alloue_fc": alloue, "reste_fc": round(budget_fc - alloue, 2),
                      "taux_fc_usd": taux},
             "regles": {"jambes_max": jambes_max, "mise_min_fc": mise_min,
                       "classe_sur_ticket": "matchs au score le plus haut (buckets puis top3)",
                       "division": f"1 a n+10 jambes (cap {jambes_max}) ; meme match interdit",
                       "ev_compose": "produit (1+edge_net)-1 precision machine ; jambe_edge_net_negatif info pas rejet",
                       "ev_floor": ev_floor, "ev_combo_floor": combo_floor,
                       "markets": list(markets) if markets is not None else None,
                       "mono": bool(mono),
                       "market_priority_min": cfg.get("min_tickets_mesures"),
                       "n_tickets_mesures": n_m,
                       "doctrine_edge": "modele calibre + news plus rapide que le book local ; pas d arbitrage"}}
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
    arg.add_argument("--markets", default=None, help="marches elus CSV, ex: OU_2.5,MT_PROLIFIQUE")
    arg.add_argument("--mono", action="store_true", help="toutes les jambes d un ticket = un seul marche")
    arg.add_argument("--ev-floor", type=float, default=EV_FLOOR)
    arg.add_argument("--mise-min-fc", type=float, default=100.0)
    arg.add_argument("--taux-fc-usd", type=float, default=None, help="taux FC → USD (pour les unités 1u=1% bankroll)")
    arg.add_argument("--out-json", default=os.path.join(here, "..", "OUT", "tickets.json"))
    arg.add_argument("--out-md", default=os.path.join(here, "..", "..", "SHARED", "OUT", "TICKETS.md"))
    arg.add_argument("--exclude-legs", default=None,
                     help="JSON file or inline list of {match_id,marche,selection} deja sortis")
    args = arg.parse_args()

    with open(args.top3, encoding="utf-8") as f:
        top3 = json.load(f)

    exclude_legs = None
    if args.exclude_legs:
        raw = args.exclude_legs
        if os.path.exists(raw):
            with open(raw, encoding="utf-8") as f:
                exclude_legs = json.load(f)
        else:
            exclude_legs = json.loads(raw)

    jbt = [int(x) for x in (args.jambes or "").split(":") if x.strip()] or []
    markets = None
    if args.markets is not None:
        markets = [x.strip() for x in args.markets.split(",") if x.strip()]
    res, wrn = allocate(
        top3.get("matchs", []), tickets=max(1, args.tickets), jambes_by_ticket=jbt,
        surticket_fc=args.surticket_fc, budget_fc=args.budget_fc,
        mises_free=args.mises_fc, jambes_max=args.jambes_max,
        mise_min=args.mise_min_fc, taux=args.taux_fc_usd,
        exclude_legs=exclude_legs, markets=markets, mono=bool(args.mono),
        ev_floor=args.ev_floor)

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
