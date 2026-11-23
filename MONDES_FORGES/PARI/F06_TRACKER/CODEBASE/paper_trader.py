#!/usr/bin/env python3
"""
PAPER TRADER Winner — journal des paris SIMULES (aucun ticket, aucune mise).
==========================================================================
Selectionne les jambes a EV reellement positif (>= EV_FLOOR) dans les
pmodel_*.json, les enregistre avec la cote Winner prise, le p_modele et
l'EV. HSH jamais inclus (diagnostic_only). Le reglement (G/P + CLV) se fait
plus tard, quand le resultat existe dans les CSV.
Sortie : ARCHIVUM/winner/paper_trades.json (versionne comme trace).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "winner", "paper_trades.json")
EV_FLOOR = 0.03
CONTRACT = "pari.paper_trades.v1"
MARCHES = (("1X2", "home", "1"), ("1X2", "draw", "X"), ("1X2", "away", "2"),
           ("OU_2.5", "under_2_5", "under"), ("OU_2.5", "over_2_5", "over"))


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def record(sport="foot", source=None, out=None, ev_floor=EV_FLOOR, mise=1.0):
    pm = source or os.path.join(WORLD, "ARCHIVUM", "winner", "pmodel_%s.json" % sport)
    blob = _load(pm)
    ledger = _load(out or DEFAULT_OUT)
    if not isinstance(ledger, dict):
        ledger = {"contract": CONTRACT, "bets": []}
    ledger.setdefault("bets", [])
    seen = {(b.get("id")) for b in ledger["bets"]}
    added = []
    diagnostic = []
    generated = blob.get("generated_at") or datetime.now(timezone.utc).isoformat()
    for r in blob.get("analyses") or []:
        if not r.get("p_modele"):
            continue
        for marche, key, selection in MARCHES:
            section = r if marche == "1X2" else (r.get("ou25") or {})
            ev = (section.get("ev") or {}).get(key)
            if ev is None:
                continue
            cote = (section.get("cote") or {}).get(key)
            if 0 < ev < ev_floor:
                diagnostic.append({
                    "match_key": r.get("match_key"), "marche": marche,
                    "selection": selection, "cote": cote,
                    "ev": round(ev, 6), "pari": False,
                })
            if ev < ev_floor:
                continue
            p = (section.get("p_modele") or {}).get(key)
            if not cote or not p:
                continue
            bid = "%s|%s|%s|%s|%s" % (generated[:10], r.get("match_key"), marche, selection, cote)
            if bid in seen:
                continue
            seen.add(bid)
            bet = {
                "id": bid,
                "generated_at": generated,
                "sport": sport,
                "match_key": r.get("match_key"),
                "home": r.get("home"), "away": r.get("away"),
                "marche": marche, "selection": selection,
                "cote": cote, "p_modele": p, "ev": round(ev, 6),
                "mise": mise, "resultat": "EN_ATTENTE",
                "ticket": False,
            }
            ledger["bets"].append(bet)
            added.append(bet)
    ledger["contract"] = CONTRACT
    ledger["generated_at"] = datetime.now(timezone.utc).isoformat()
    ledger["n_bets"] = len(ledger["bets"])
    ledger["diagnostic"] = diagnostic
    ledger["tickets_enabled"] = False
    target = out or DEFAULT_OUT
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    return ledger, added


def report(ledger):
    bets = ledger.get("bets") or []
    return {"n": len(bets), "en_attente": sum(1 for b in bets if b.get("resultat") == "EN_ATTENTE"),
            "ev_moyenne": (sum(b.get("ev") or 0 for b in bets) / len(bets)) if bets else None}


def main():
    ap = argparse.ArgumentParser(description="journal paper-trading Winner")
    ap.add_argument("--sport", choices=("foot", "basket"), default="foot")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ev-floor", type=float, default=EV_FLOOR)
    args = ap.parse_args()
    ledger, added = record(args.sport, out=args.out, ev_floor=args.ev_floor)
    print(json.dumps({"sport": args.sport, "ajoutes": len(added),
                      **report(ledger)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
