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
for _p in (os.path.join(WORLD, "F00_RADAR", "CODEBASE"),
           os.path.join(WORLD, "F02_BREACHER", "CODEBASE"),
           os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import market_csv  # noqa: E402
import fit_dc  # noqa: E402
import winner_pmodel  # noqa: E402


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


def _outcome(row, marche, selection):
    h, a = row.get("fthg"), row.get("ftag")
    if h is None or a is None:
        return None
    if marche == "1X2":
        real = "1" if h > a else "X" if h == a else "2"
    else:
        total = h + a
        real = "under" if total < 2.5 else "over"
    return real == selection


def settle(csv_dir=None, out=None, params_path=None):
    """Regle les paris EN_ATTENTE avec FTHG/FTAG des CSV + CLV T-0 approximatif.
    Aucune mise reelle. Cote de cloture = proxy football-data (pas Winner)."""
    ledger = _load(out or DEFAULT_OUT)
    if not isinstance(ledger, dict):
        return {"n": 0, "regles": 0}
    params = fit_dc.load_params(params_path) or {}
    data = market_csv.load_dir(csv_dir or os.path.join(WORLD, "ARCHIVUM", "cache", "f00"))
    rows = data.get("rows") or []
    regles = 0
    for bet in ledger.get("bets") or []:
        if bet.get("resultat") != "EN_ATTENTE":
            continue
        _, home = winner_pmodel.resolve(bet.get("home"), params)
        _, away = winner_pmodel.resolve(bet.get("away"), params)
        if not home or not away:
            continue
        candidats = [r for r in rows
                     if winner_pmodel.norm_team(r.get("home")) == winner_pmodel.norm_team(home)
                     and winner_pmodel.norm_team(r.get("away")) == winner_pmodel.norm_team(away)
                     and r.get("date")]
        if len(candidats) != 1:
            bet["holes"] = ["match_csv_absent" if not candidats else "match_csv_ambiguous"]
            continue
        row = candidats[0]
        gagnant = _outcome(row, bet.get("marche"), bet.get("selection"))
        if gagnant is None:
            continue
        bet["resultat"] = "G" if gagnant else "P"
        bet["score"] = "%s-%s" % (row["fthg"], row["ftag"])
        bet["date_csv"] = row["date"]
        cf = row.get("cloture") or {}
        ou = (row.get("ou_cloture") or {}).get("2.5") or {}
        if bet.get("marche") == "1X2":
            key = {"1": "home", "X": "draw", "2": "away"}.get(bet.get("selection"))
            close = cf.get(key)
        else:
            close = ou.get(bet.get("selection"))
        if close and float(close) > 1:
            bet["cote_cloture"] = float(close)
            bet["clv"] = round(float(bet["cote"]) / float(close) - 1.0, 6)
            bet["clv_source"] = "proxy_football_data"
        regles += 1
    ledger["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(out or DEFAULT_OUT, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    return {**report(ledger), "regles": regles}


def main():
    ap = argparse.ArgumentParser(description="journal paper-trading Winner")
    ap.add_argument("--sport", choices=("foot", "basket"), default="foot")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ev-floor", type=float, default=EV_FLOOR)
    ap.add_argument("--settle", action="store_true", help="regle avec les CSV football-data")
    args = ap.parse_args()
    if args.settle:
        rec = settle(out=args.out)
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return
    ledger, added = record(args.sport, out=args.out, ev_floor=args.ev_floor)
    print(json.dumps({"sport": args.sport, "ajoutes": len(added),
                      **report(ledger)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
