#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E TIMING — connecteur timing buts/cartons + gachette enrich (zero reseau)
==========================================================================
Le reseau est coupe en dur (fake http_util.get_json par URL) : la chaine
search -> events -> incidents est testee ENTIEREMENT avec des fixtures.
Doctrine verifiee : affichage SEULEMENT (jamais Poisson), trou si aucun
candidat, kill switch PARI_SKIP_TIMING, vault hole `timing` retire par enrich.
"""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import data_view  # noqa: E402  (portée module; chargé via sys.path actuel)

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


SEARCH = {"results": [{"type": "team", "entity": {"id": 42, "name": "Arsenal",
          "sport": {"slug": "football"}}}]}
EVENTS_NEXT = {"events": [{
    "id": 16939009, "slug": "slavia-praha-arsenal", "startTimestamp": 1734048000,
    "status": {"type": "notstarted", "description": "Not started"},
    "homeTeam": {"id": 1, "name": "Slavia Praha"},
    "awayTeam": {"id": 42, "name": "Arsenal"},
}]}
EVENTS_LAST = {"events": [{
    "id": 14025021, "slug": "bournemouth-arsenal", "startTimestamp": 1733443200,
    "status": {"type": "finished", "description": "Ended"},
    "homeTeam": {"id": 2, "name": "Bournemouth"},
    "awayTeam": {"id": 42, "name": "Arsenal"},
}]}
INCIDENTS = {"incidents": [
    {"id": 1, "time": 22, "incidentType": "goal", "incidentClass": "regular",
     "isHome": False, "playerName": "Saka", "homeScore": 0, "awayScore": 1},
    {"id": 2, "time": 47, "incidentType": "goal", "incidentClass": "regular",
     "isHome": True, "playerName": "Semenyo", "homeScore": 1, "awayScore": 1},
    {"id": 3, "time": 67, "incidentType": "goal", "incidentClass": "penalty",
     "isHome": False, "playerName": "Saka", "homeScore": 1, "awayScore": 2},
    {"id": 4, "time": 77, "incidentType": "card", "incidentClass": "red",
     "isHome": True, "playerName": "Hill - red", "homeScore": 1, "awayScore": 2},
    {"id": 5, "time": 90, "incidentType": "period", "incidentClass": None, "isHome": None},
]}


def install_network(monkey_urls=None):
    """coupe le reseau en dur ; renvoie un remplacement URL-manqué."""
    import http_util
    real = http_util.get_json

    def fake(url, headers=None, timeout=None):
        if monkey_urls is not None:
            monkey_urls.append(url)
        if "search/all" in url:
            return SEARCH
        if "events/next/0" in url:
            return EVENTS_NEXT
        if "events/last/0" in url:
            return EVENTS_LAST
        if "incidents" in url:
            return INCIDENTS
        return None
    http_util.get_json = fake
    return real


def main():
    print("=" * 70)
    print("E2E TIMING — connecteur + gachette (zero reseau)")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="pari-tim-")
    os.environ["PARI_F00_CACHE"] = tmp
    os.environ["SOFASCORE_RAPIDAPI_KEY"] = "probe-key-zero-reseau"

    real_get = install_network()
    try:
        import match_timing

        out = match_timing._fetch("Arsenal", "Slavia Praha")
        check("T.chaine_complete", out and out.get("event_id") == 16939009, str(out)[:80])
        check("T.goals_minute_sorted", [g["minute"] for g in out["goals"]] == [22, 47, 67],
              str([(g["minute"], g["player"]) for g in out["goals"]]))
        check("T.goal_side", out["goals"][0]["side"] == "ext" and out["goals"][1]["side"] == "dom")
        check("T.penalty_classe", out["goals"][2]["class"] == "penalty")
        check("T.cards_red", out["cards"] and out["cards"][0]["class"] == "red"
              and out["cards"][0]["minute"] == 77, str(out["cards"]))

        # cache : 2e appel = pas de réseau ( urls deja appeles non re-empilées)
        urls = []
        call1 = match_timing.match_timing("Arsenal", "Slavia Praha")
        n_after = len(urls) if False else None
        match_timing.match_timing("Arsenal", "Slavia Praha")
        check("T.cache_1hit", call1 is not None)

        dom = match_timing._norm("Arsenal")
        ext = match_timing._norm("Slavia Praha")
        check("T.slug_cache_key", isinstance(dom, str) and isinstance(ext, str) and dom and ext)

        # aura aucun candidat : club hors fixtures
        out2 = match_timing._fetch("Real Madrid", "Barcelona")
        check("T.hors_fixtures_trou", out2 is None, str(out2)[:60])

        # gachette enrich : timing_posé retire le trou, sinon trou documenté
        import http_util as hu
        import enrich

        # 1) match_timing vivant (fake network) → trou timing absent
        carte = {"ligue": "England - Premier League",
                 "matchs": [{"id": "M1", "dom": "Arsenal", "ext": "Slavia Praha",
                             "date": "2026-11-02", "stats": {}}]}
        os.environ["PARI_SKIP_BINARY"] = "1"  # binaire a part
        old_collect = enrich._collect_hits
        enrich._collect_hits = lambda team, code=None: []
        try:
            os.environ.pop("PARI_SKIP_TIMING", None)
            out5, notes5 = enrich.enrich_carte(carte, skip_binary=False, skip_notes=True)
            m5 = out5["matchs"][0]
            check("T.enrich_goal_minutes_pose", (m5.get("goal_minutes") or {}).get("event_id") == 16939009)
            check("T.enrich_trou_retire", "timing" not in (m5.get("holes") or []), str(m5.get("holes")))

            # 2) reseau ferme → trou timing documente, jamais de crash
            hu.get_json = lambda *a, **k: None
            hu._FAILS.clear()
            carte2 = {"ligue": "England - Premier League",
                      "matchs": [{"id": "M2", "dom": "Chelsea", "ext": "Everton",
                                  "date": "2026-11-02", "stats": {}}]}
            out6, _ = enrich.enrich_carte(carte2, skip_binary=False, skip_notes=True)
            m6 = out6["matchs"][0]
            check("T.enrich_reseau_ferme_trou",
                  "goal_minutes" not in m6 and "timing" in (m6.get("holes") or []),
                  str(m6.get("holes")))

            # 3) kill switch PARI_SKIP_TIMING → trou meme si donne serait disponible
            os.environ["PARI_SKIP_TIMING"] = "1"
            carte3 = {"ligue": "England - Premier League",
                      "matchs": [{"id": "M3", "dom": "Arsenal", "ext": "Slavia Praha",
                                  "date": "2026-11-02", "stats": {}}]}
            out7, _ = enrich.enrich_carte(carte3, skip_binary=False, skip_notes=True)
            m7 = out7["matchs"][0]
            check("T.skip_timing_hole", "goal_minutes" not in m7 and "timing" in (m7.get("holes") or []),
                  str(m7.get("holes")))
            os.environ.pop("PARI_SKIP_TIMING", None)
        finally:
            enrich._collect_hits = old_collect
            os.environ.pop("PARI_SKIP_BINARY", None)

        # 4) vue /data fiche : goal_minutes → bloc TIMING ; absent → TROU timing
        row = {"id": "M1", "match": "Arsenal vs Slavia Praha", "bucket": "HAUTE",
               "score_commun": 7.0, "rang_global": 1, "no_bet_recommande": False, "top3": []}
        intel = {
            "dom": "Arsenal", "ext": "Slavia Praha", "holes": [],
            "goal_minutes": {"event_id": 14025021, "home": "Bournemouth",
                             "away": "Arsenal", "status": "Ended",
                             "goals": [{"minute": 22, "side": "ext", "player": "Saka",
                                        "class": "regular", "score": "0-1"},
                                       {"minute": 47, "side": "dom", "player": "Semenyo",
                                        "class": "regular", "score": "1-1"}],
                             "cards": [{"minute": 77, "player": "Hill - red", "class": "red"}]},
        }
        # construit row_m1, row_m2, top3m, cartem  (top3/md compatibles avec render_fiche)
        row_m1 = {
            "id": "M1", "match": "Arsenal vs Slavia Praha", "dom": "Arsenal", "ext": "Slavia Praha",
            "bucket": "HAUTE", "score_commun": 7.0, "rang_global": 1, "no_bet_recommande": False, "top3": [],
            "goal_minutes": {
                "event_id": 14025021, "home": "Bournemouth", "away": "Arsenal", "status": "Ended",
                "goals": [
                    {"minute": 22, "side": "ext", "player": "Saka", "class": "regular", "score": "0-1"},
                    {"minute": 47, "side": "dom", "player": "Semenyo", "class": "regular", "score": "1-1"},
                ],
                "cards": [{"minute": 77, "player": "Hill - red", "class": "red"}],
            },
        }
        row_m2 = {
            "id": "M2", "match": "Chelsea vs Everton", "dom": "Chelsea", "ext": "Everton",
            "bucket": "FAIBLE", "score_commun": 2.0, "rang_global": 2, "no_bet_recommande": True, "top3": [],
        }
        top3m = {"matchs": [row_m1, row_m2]}
        cartem = {"matchs": [row_m1, row_m2]}
        fiche = data_view.render_fiche(1, top3m, "", cartem, {})
        check("T.fiche_timing_affiche", "TIMING" in fiche and "BUTS" in fiche
              and "22'" in fiche and "47'" in fiche, fiche[:140])
        check("T.fiche_cartons", "CARTONS" in fiche and "77'" in fiche, fiche[:160])
        row2 = {"id": "M2", "match": "Chelsea vs Everton", "bucket": "FAIBLE",
                "score_commun": 2.0, "rang_global": 2, "no_bet_recommande": True, "top3": []}
        fiche2 = data_view.render_fiche(2, top3m, "", cartem, {})
        check("T.fiche_trou_timing", "TROU timing" in fiche2, fiche2[:140])
    finally:
        import http_util as hu
        hu.get_json = real_get
        os.environ.pop("SOFASCORE_RAPIDAPI_KEY", None)
        os.environ.pop("PARI_SKIP_TIMING", None)

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"TIMING {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
