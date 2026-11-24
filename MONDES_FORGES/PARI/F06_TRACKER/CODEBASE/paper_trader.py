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


def record_basket(source=None, out=None, ev_floor=EV_FLOOR, mise=1.0):
    """Paris simules basket : uniquement si le modele est valide (GO)."""
    pm = source or os.path.join(WORLD, "ARCHIVUM", "winner", "pmodel_basket.json")
    blob = _load(pm)
    if not isinstance(blob, dict) or not blob.get("fiable"):
        return {"skipped": "modele_non_valide", "ajoutes": []}
    ledger = _load(out or DEFAULT_OUT)
    if not isinstance(ledger, dict):
        ledger = {"contract": CONTRACT, "bets": []}
    ledger.setdefault("bets", [])
    seen = {b.get("id") for b in ledger["bets"]}
    added = []
    for r in blob.get("analyses") or []:
        for key, selection in (("home", "1"), ("away", "2")):
            ev = (r.get("ev") or {}).get(key)
            cote = (r.get("cote") or {}).get(key)
            p = (r.get("p_modele") or {}).get(key)
            if ev is None or ev < ev_floor or not cote or not p:
                continue
            bid = "%s|%s|ML|%s|%s" % (blob.get("generated_at", "")[:10],
                                      r.get("match_key"), selection, cote)
            if bid in seen:
                continue
            seen.add(bid)
            bet = {"id": bid, "generated_at": blob.get("generated_at"),
                   "sport": "basket", "match_key": r.get("match_key"),
                   "home": r.get("home"), "away": r.get("away"),
                   "marche": "ML", "selection": selection,
                   "cote": cote, "p_modele": p, "ev": round(ev, 6),
                   "mise": mise, "resultat": "EN_ATTENTE", "ticket": False,
                   "clv": None, "holes": ["clv_absent_close_api"]}
            ledger["bets"].append(bet)
            added.append(bet)
    target = out or DEFAULT_OUT
    with open(target, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    return {"skipped": None, "ajoutes": added}


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
        clv_same = None
        try:
            import winner_watch as ww
            sport_bet = bet.get("sport") or "foot"
            watch = ww.load(sport_bet)
            key = bet.get("match_key") or ww.key_of(bet.get("home"), bet.get("away"))
            if key not in watch.get("matches", {}):
                for k, v in watch.get("matches", {}).items():
                    if (v.get("source_event_id") and str(v["source_event_id"]) == str(bet.get("source_event_id"))) \
                            or ww.key_of(v.get("home"), v.get("away")) == ww.key_of(bet.get("home"), bet.get("away")):
                        key = k
                        break
            if key in watch.get("matches", {}):
                clv_same, hole_clv = ww.clv(sport_bet, key, bet.get("selection"))
                if hole_clv:
                    bet.setdefault("holes", []).append(hole_clv)
        except Exception:
            pass
        if clv_same is not None:
            bet["clv"] = clv_same
            bet["clv_source"] = "winner_same_book"
            bet["cote_cloture"] = None
        elif close and float(close) > 1:
            bet["cote_cloture"] = float(close)
            bet["clv"] = round(float(bet["cote"]) / float(close) - 1.0, 6)
            bet["clv_source"] = "proxy_football_data"
            bet.setdefault("holes", []).append("clv_proxy_only")
        regles += 1
    ledger["generated_at"] = datetime.now(timezone.utc).isoformat()
    with open(out or DEFAULT_OUT, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    return {**report(ledger), "regles": regles}


def settle_api(out=None, api_key=None):
    """Reglement via API-Football (source whitelistee) quand les CSV sont en retard."""
    import urllib.parse
    import urllib.request
    ledger = _load(out or DEFAULT_OUT)
    if not isinstance(ledger, dict):
        return {"n": 0, "regles": 0}
    key = (api_key or os.environ.get("API_FOOTBALL_KEY") or "").strip()
    if not key:
        return {"n": 0, "holes": ["api_key_absent"]}
    base = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": key}

    def get(path):
        import urllib.error
        req = urllib.request.Request(base + path, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise RuntimeError("quota_api_epuise") from exc
            return {}

    def team_id(name):
        q = urllib.parse.quote(str(name or "").split()[0])
        data = get("/teams?search=" + q)
        target = winner_pmodel.norm_team(name)
        for item in data.get("response") or []:
            t = item.get("team") or {}
            cand = winner_pmodel.norm_team(t.get("name"))
            if cand and (cand == target or cand in target or target in cand):
                return t.get("id")
        return None

    cache = {}
    regles = 0
    for bet in ledger.get("bets") or []:
        if bet.get("resultat") != "EN_ATTENTE":
            continue
        for side in ("home", "away"):
            name = bet.get(side)
            if name not in cache:
                cache[name] = team_id(name)
        hid, aid = cache.get(bet.get("home")), cache.get(bet.get("away"))
        if not hid or not aid:
            bet["holes"] = ["equipe_api_introuvable"]
            continue
        date = (bet.get("date_csv") or bet.get("generated_at") or "")[:10]
        if not date:
            continue
        from datetime import timedelta
        base_date = datetime.strptime(date, "%Y-%m-%d")
        match = None
        for delta in (0, -1, 1, -2, 2):
            day = (base_date + timedelta(days=delta)).strftime("%Y-%m-%d")
            data = get("/fixtures?date=" + urllib.parse.quote(day))
            for fx in data.get("response") or []:
                teams = fx.get("teams") or {}
                if ((teams.get("home") or {}).get("id") == hid
                        and (teams.get("away") or {}).get("id") == aid):
                    match = fx
                    break
            if match:
                break
        if not match:
            bet["holes"] = ["fixture_api_absent"]
            continue
        score = match.get("score") or {}
        h, a = (score.get("fulltime") or {}).get("home"), (score.get("fulltime") or {}).get("away")
        if h is None or a is None or (match.get("fixture") or {}).get("status", {}).get("short") != "FT":
            bet["holes"] = ["score_api_absent"]
            continue
        gagnant = _outcome({"fthg": h, "ftag": a}, bet.get("marche"), bet.get("selection"))
        bet["resultat"] = "G" if gagnant else "P"
        bet["score"] = "%s-%s" % (h, a)
        bet["date_csv"] = date
        bet["source_resultat"] = "api_football"
        bet["holes"] = ["clv_absent_close_api"]
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
    ap.add_argument("--settle-api", action="store_true", help="regle via API-Football")
    args = ap.parse_args()
    if args.settle_api:
        print(json.dumps(settle_api(out=args.out), indent=2, ensure_ascii=False))
        return
    if args.settle:
        rec = settle(out=args.out)
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return
    if args.sport == "basket":
        rec = record_basket(out=args.out, ev_floor=args.ev_floor)
        print(json.dumps({"sport": "basket", "skipped": rec["skipped"],
                          "ajoutes": len(rec["ajoutes"])}, indent=2, ensure_ascii=False))
        return
    ledger, added = record(args.sport, out=args.out, ev_floor=args.ev_floor)
    print(json.dumps({"sport": args.sport, "ajoutes": len(added),
                      **report(ledger)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
