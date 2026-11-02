#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E ODDS T-2h — The Odds API + recast EV (zero reseau).
Cle absente = trou. Jamais Poisson. Jamais scrape Winner.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = os.path.normpath(os.path.join(WORLD, "..", ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors"))

CHECKS = []
NOW = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


FX = [{
    "id": "ev1",
    "sport_key": "soccer_epl",
    "commence_time": "2026-11-02T18:00:00Z",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "bookmakers": [{
        "key": "pinnacle",
        "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Arsenal", "price": 1.90},
                {"name": "Draw", "price": 3.60},
                {"name": "Chelsea", "price": 4.20},
            ]},
            {"key": "totals", "outcomes": [
                {"name": "Over", "price": 1.85, "point": 2.5},
                {"name": "Under", "price": 2.05, "point": 2.5},
            ]},
        ],
    }],
}]


def install_net(payload=None):
    import http_util
    real = http_util.get_json
    blob = FX if payload is None else payload

    def fake(url, headers=None, timeout=None):
        if "the-odds-api.com" in url or "odds" in url:
            return blob
        return None

    http_util.get_json = fake
    return real


def main():
    print("=" * 70)
    print("E2E ODDS T-2h (zero reseau)")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="pari-odds-")
    os.environ["PARI_F00_CACHE"] = tmp
    os.environ.pop("ODDS_API_KEY", None)
    os.environ.pop("THE_ODDS_API_KEY", None)
    os.environ.pop("PARI_SKIP_ODDS", None)

    import odds_api
    import odds_watch

    check("O.cle_absente_league", odds_api.league_odds("E0") == [])
    check("O.cle_absente_match", odds_api.match_odds("Arsenal", "Chelsea", "E0") is None)

    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-odds-hit-")
    os.environ["ODDS_API_KEY"] = "probe-zero-reseau"
    real = install_net()
    try:
        rows = odds_api.league_odds("E0")
        check("O.parse_h2h", rows and rows[0]["cotes"].get("1") == 1.90
              and rows[0]["cotes"].get("X") == 3.60
              and rows[0]["cotes"].get("2") == 4.20, str(rows[:1]))
        check("O.parse_totals", rows[0]["cotes"].get("o2.5") == 1.85
              and rows[0]["cotes"].get("u2.5") == 2.05)
        check("O.book_pinnacle", rows[0].get("bookmaker") == "pinnacle")

        hit = odds_api.match_odds("Arsenal FC", "Chelsea", "E0")
        check("O.match_difflib", hit and hit["cotes"].get("1") == 1.90, str(hit)[:80] if hit else "none")

        flip = odds_api.match_odds("Chelsea", "Arsenal", "E0")
        check("O.match_flipped", flip and flip.get("flipped") and flip["cotes"].get("1") == 4.20,
              str((flip or {}).get("cotes")))

        miss = odds_api.match_odds("Ghost FC", "Nowhere", "E0")
        check("O.match_trou", miss is None)

        a, b = odds_api.league_odds("E0"), odds_api.league_odds("E0")
        check("O.cache_1hit", a == b)
    finally:
        import http_util
        http_util.get_json = real

    sels = [
        {"selection": "1", "p_modele": 0.55, "ev": 0.10, "verdict": "VALUE", "cote": 2.00},
        {"selection": "X", "p_modele": 0.25, "ev": -0.10, "verdict": "NO_BET", "cote": 3.60},
    ]
    alerts, moves = odds_watch.recast(
        {"1": 2.00, "X": 3.60},
        {"1": 1.70, "X": 3.60},
        sels, seuil=0.03,
    )
    kinds = [a["kind"] for a in alerts]
    check("O.recast_estompe", "ESTOMPE" in kinds, str(alerts))
    check("O.recast_move", any(m["selection"] == "1" for m in moves), str(moves))

    alerts2, _ = odds_watch.recast(
        {"1": 2.00}, {"1": 1.90},
        [{"selection": "1", "p_modele": 0.55, "ev": 0.10, "verdict": "VALUE"}],
        seuil=0.08,
    )
    check("O.recast_aminci", alerts2 and alerts2[0]["kind"] == "AMINCI", str(alerts2))

    ko = NOW + timedelta(hours=2)
    check("O.fenetre_in", odds_watch.in_window(ko, now=NOW, horizon_h=3))
    check("O.fenetre_out", not odds_watch.in_window(NOW + timedelta(hours=8), now=NOW, horizon_h=3))
    check("O.fenetre_passe", not odds_watch.in_window(NOW - timedelta(hours=1), now=NOW, horizon_h=3))
    check("O.kickoff_parse", odds_watch.parse_kickoff({"date": "2026-11-02", "heure": "18:00"}).hour == 18)

    carte = {"ligue": "Premier League", "matchs": [{
        "id": "M1", "dom": "Arsenal", "ext": "Chelsea",
        "ligue": "Premier League", "date": "2026-11-02", "heure": "18:00",
        "cotes": {"1": 2.00, "X": 3.60, "2": 4.00, "o2.5": 1.90, "u2.5": 2.00},
    }]}
    preds = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1",
        "selections": [
            {"selection": "1", "p_modele": 0.48, "ev": 0.10, "verdict": "VALUE", "cote": 2.00},
        ],
    }]}
    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-odds-scan-")
    os.environ["ODDS_API_KEY"] = "probe-zero-reseau"
    real = install_net()
    try:
        res = odds_watch.scan(carte=carte, predictions=preds, now=NOW, horizon_h=3)
        check("O.scan_in_window", len(res["scanned"]) == 1 and res["reason"] == "ok", str(res["reason"]))
        check("O.scan_alerte", any(a.get("kind") == "ESTOMPE" for a in res["alerts"]), str(res["alerts"]))
        msg = odds_watch.format_alerts(res)
        check("O.format_alerte", "ESTOMPE" in msg and "Arsenal" in msg, msg[:120])

        late = dict(carte)
        late["matchs"] = [dict(carte["matchs"][0], heure="23:00")]
        res2 = odds_watch.scan(carte=late, predictions=preds, now=NOW, horizon_h=3)
        check("O.scan_hors_fenetre", res2["scanned"] == [] and res2["skipped"], str(res2["skipped"]))
    finally:
        import http_util
        http_util.get_json = real

    os.environ["PARI_SKIP_ODDS"] = "1"
    res3 = odds_watch.scan(carte=carte, predictions=preds, now=NOW)
    check("O.skip_env", res3["reason"] == "PARI_SKIP_ODDS")
    os.environ.pop("PARI_SKIP_ODDS", None)

    os.environ.pop("ODDS_API_KEY", None)
    os.environ.pop("THE_ODDS_API_KEY", None)
    import importlib
    importlib.reload(odds_api)
    importlib.reload(odds_watch)
    res4 = odds_watch.scan(carte=carte, predictions=preds, now=NOW)
    check("O.skip_sans_cle", "absente" in (res4.get("reason") or ""), res4.get("reason"))

    cap_src = open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "capteurs.py"), encoding="utf-8").read()
    check("O.cli_odds_watch", "odds-watch" in cap_src and "cmd_odds_watch" in cap_src)

    ow_src = open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "odds_watch.py"), encoding="utf-8").read()
    oa_src = open(os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors", "odds_api.py"), encoding="utf-8").read()
    check("O.pas_poisson", "import breacher" not in ow_src and "dixon" not in ow_src.lower()
          and "lambda" not in ow_src)
    check("O.pas_scrape_winner", "winner.bet" not in ow_src.lower() and "winner.bet" not in oa_src.lower()
          and "beautifulsoup" not in ow_src.lower())

    wf_p = os.path.join(REPO, ".github", "workflows", "pari_odds_t2h.yml")
    wf = open(wf_p, encoding="utf-8").read() if os.path.exists(wf_p) else ""
    check("O.workflow", "odds_watch.py" in wf and "cron" in wf)
    check("O.pas_github_secrets", "${{ secrets." not in wf)
    check("O.workflow_env_pari", "env_pari" in wf or "ODDS_API_KEY" in open(
        os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors", "odds_api.py"), encoding="utf-8").read())

    conn = open(os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors", "odds_api.py"), encoding="utf-8").read()
    check("O.env_pari_loader", "env_pari" in conn and "ODDS_API_KEY" in conn)

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"ODDS {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
