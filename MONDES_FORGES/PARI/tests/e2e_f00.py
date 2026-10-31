#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E F00 — vote OUT/DOUTE/IGNORE + enrich hors-réseau + /data notes: N
=====================================================================
Zero reseau. Deux modes Oracle : clé absente = silence ; clé presente
n'invente jamais un OUT.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "TYRANT", "CODEBASE"))

import cache  # noqa: E402
import enrich  # noqa: E402
import vote  # noqa: E402
import qualitative  # noqa: E402
import workflow  # noqa: E402

CHECKS = []
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def hit(src, fact="blessure X", hours=1):
    ts = (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"source": src, "fact": fact, "ts": ts, "theme": "blessures"}


def main():
    print("=" * 70)
    print("E2E F00 — capteurs /capture (zero reseau)")
    print("=" * 70)

    v = vote.vote_theme([hit("sofascore"), hit("sportradar"), hit("whoscored")], now=NOW)
    check("F00.vote_out_3voix", v["verdict"] == "OUT" and set(v["sources"]) == {"sofascore", "sportradar", "opta"})

    v = vote.vote_theme([hit("sofascore"), hit("sofa"), hit("whoscored")], now=NOW)
    check("F00.vote_doute_meme_upstream", v["verdict"] == "DOUTE", v["verdict"])

    v = vote.vote_theme([hit("sofascore"), hit("sportradar")], now=NOW)
    check("F00.vote_doute_2voix", v["verdict"] == "DOUTE")

    v = vote.vote_theme([], now=NOW)
    check("F00.vote_ignore_vide", v["verdict"] == "IGNORE")

    v = vote.vote_theme([hit("sofascore", hours=72), hit("sportradar", hours=72), hit("whoscored", hours=72)], now=NOW)
    check("F00.vote_ignore_hors_fenetre", v["verdict"] == "IGNORE", v["verdict"])

    v = vote.vote_theme([
        hit("sofascore-api"),
        {"source": "api-sports", "fact": "x", "ts": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")},
        {"source": "api_football", "fact": "y", "ts": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")},
    ], now=NOW)
    check("F00.vote_wrappers_pas_3voix", v["verdict"] != "OUT", v["verdict"])

    check("F00.doute_pas_impact", vote.impact_for("blessures", "DOUTE") is None)
    check("F00.out_blessure_eleve", vote.impact_for("blessures", "OUT") == "eleve")
    check("F00.fatigue_2j", vote.impact_for("fatigue", "OUT", rest_days=2) == "eleve")
    check("F00.fatigue_4j", vote.impact_for("fatigue", "OUT", rest_days=4) is None)

    tmp = tempfile.mkdtemp(prefix="pari-f00-")
    os.environ["PARI_F00_CACHE"] = tmp
    cache._FAILS = {} if hasattr(cache, "_FAILS") else None
    a, miss1 = cache.get_or_fetch("t", "k", lambda: {"x": 1})
    b, miss2 = cache.get_or_fetch("t", "k", lambda: {"x": 99})
    check("F00.cache_1hit", a == {"x": 1} and b == {"x": 1} and miss1 is False and miss2 is True)
    c, _ = cache.get_or_fetch("t", "boom", lambda: (_ for _ in ()).throw(RuntimeError("ban")))
    check("F00.cache_trou_exception", c is None)

    old_skip = os.environ.get("PARI_SKIP_F00")
    os.environ["PARI_SKIP_F00"] = "1"
    os.environ["PARI_F00_NOTES"] = "0"
    carte = {
        "ligue": "Espagne - LaLiga",
        "matchs": [{"id": "M1", "dom": "Levante UD", "ext": "Atletico Madrid",
                    "date": "2026-10-31", "stats": {}}],
    }
    out, notes = enrich.enrich_carte(carte)
    check("F00.skip_trou_visible", notes["notes_count"] == 0 and "xg" not in (out["matchs"][0].get("holes") or []),
          str(notes["notes_count"]))
    os.environ["PARI_SKIP_F00"] = "0"
    os.environ["PARI_SKIP_BINARY"] = "1"
    os.environ["PARI_F00_NOTES"] = "0"
    carte2 = {
        "ligue": "Turquie - Super Lig",
        "matchs": [{"id": "M9", "dom": "Konyaspor", "ext": "Galatasaray",
                    "date": "2026-10-31", "ligue": "Turquie - Super Lig", "stats": {}}],
    }
    _, notes2 = enrich.enrich_carte(carte2, skip_binary=True, skip_notes=False)
    check("F00.turquie_pas_3voix", notes2["notes_count"] == 0)

    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "Levante UD vs Atletico Madrid", "verdict": "GO",
        "meilleure_ev": 0.1,
        "selections": [
            {"selection": "mt2", "marche": "MT2", "verdict": "VALUE", "ev": 0.12, "mise_units": 1},
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.08, "mise_units": 1},
        ],
    }]}
    analysis = {"analyses": [{"id": "M1", "data_quality": {"niveau": "haute"}}]}
    notes_out = {
        "generated_at": "2026-10-31T00:00:00Z", "source": "f00_vote", "notes_count": 1,
        "notes": [{"match_id": "M1", "dom": "Levante UD", "ext": "Atletico Madrid",
                   "items": [{"theme": "fatigue", "verdict": "OUT", "impact": "eleve",
                              "detail": "repos 2j", "sources": ["football-data.org"], "window_h": 48}],
                   "themes": {"fatigue": {"impact": "eleve", "detail": "repos 2j"}}}]
    }
    vq, filt = qualitative.apply_qualitative(pred, analysis, notes_out)
    m1 = filt["predictions"][0]
    mt2 = [s for s in m1["selections"] if s["selection"] == "mt2"][0]
    check("F00.tyrant_out_exclut_mt2", mt2["verdict"] == "NO_BET")

    notes_doute = {
        "source": "f00_vote", "notes_count": 0,
        "notes": [{"match_id": "M1", "items": [
            {"theme": "blessures", "verdict": "DOUTE", "detail": "1 voix", "sources": ["sofascore"]}]}],
    }
    vq2, filt2 = qualitative.apply_qualitative(pred, analysis, notes_doute)
    mt2b = [s for s in filt2["predictions"][0]["selections"] if s["selection"] == "mt2"][0]
    check("F00.tyrant_doute_pas_lambda", mt2b["verdict"] == "VALUE", mt2b["verdict"])

    notes_zero = {"source": "f00_vote", "notes_count": 0, "notes": []}
    vq3, filt3 = qualitative.apply_qualitative(pred, analysis, notes_zero)
    check("F00.tyrant_trou_zero", vq3["verdicts"] == [] and filt3["predictions"][0]["selections"][0]["verdict"] == "VALUE")

    wf_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()
    check("F00.gachette_capture", "enrich_f00_capture" in wf_src and "notes: {notes_n}" in wf_src)
    check("F00.data_affiche_notes", 'tell(f"notes: {n_notes}' in wf_src)
    orch_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "orchestrator.py"), encoding="utf-8").read()
    check("F00.siege_filtre_notes_count", "notes_count" in orch_src and "has_notes" in orch_src)

    tyrant_src = open(os.path.join(WORLD, "TYRANT", "CODEBASE", "tyrant.py"), encoding="utf-8").read()
    check("F00.oracle_jamais_out", "oracle_comment" in tyrant_src and "N'invente JAMAIS de chiffre" in tyrant_src)
    check("F00.oracle_silence_sans_cle", 'if not key or not (notes or "").strip()' in tyrant_src)

    schema_n = open(os.path.join(WORLD, "CONTRACTS", "schema_notes_qualitatives.json"), encoding="utf-8").read()
    check("F00.contrat_verdict", "OUT|DOUTE|IGNORE" in schema_n and "notes_count" in schema_n)
    schema_m = open(os.path.join(WORLD, "CONTRACTS", "schema_match_intel.json"), encoding="utf-8").read()
    check("F00.contrat_intel_holes", '"holes"' in schema_m and '"xg"' in schema_m and '"rest_days"' in schema_m)

    told = []
    old_tell = workflow.tell
    workflow.tell = lambda m: told.append(m)
    try:
        st = {"notes_count": 0}
        top = os.path.join(WORLD, "SHARED", "OUT", "TOP3.md")
        os.makedirs(os.path.dirname(top), exist_ok=True)
        open(top, "w", encoding="utf-8").write("### TOP 3\n- **#1 Levante UD vs Atletico Madrid** — score **7/10**\n")
        old_p = workflow.P
        def fake_p(*a):
            if a[-1] == "TOP3.md":
                return top
            if a[-1] == "matches.json":
                p = os.path.join(tmp, "matches.json")
                json.dump({"matchs": [{"dom": "Levante UD", "ext": "Atletico Madrid"}]}, open(p, "w"))
                return p
            if a[-1] == "notes_qualitatives.json":
                return os.path.join(tmp, "absent.json")
            return old_p(*a)
        workflow.P = fake_p
        workflow.cmd_data(st, "")
        check("F00.data_notes_zero", told and told[-1].startswith("notes: 0"), (told[-1] if told else "")[:60])
        workflow.P = old_p
    finally:
        workflow.tell = old_tell
        if old_skip is None:
            os.environ.pop("PARI_SKIP_F00", None)
        else:
            os.environ["PARI_SKIP_F00"] = old_skip

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"F00 {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
