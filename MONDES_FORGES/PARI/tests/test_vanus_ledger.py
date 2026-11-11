#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V6 — ledger freeze greffe vanus_gate. Flags T0. Jamais un p. Gel intact."""

import ast
import json
import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))

import moteur_flag  # noqa: E402
import ledger  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F06_TRACKER", "CODEBASE", "ledger.py"), encoding="utf-8").read()


def _blob(niveau="isole", selection="home", n=1, found=1):
    indexes = {
        "predictlix": {"pick": "home", "model_pct": None, "at": "2026-11-09T10:00:00Z"},
        "dailysportpick": None,
        "metapred": None,
        "footinsights": None,
        "besoccer": None,
        "vitibet": None,
    }
    if n >= 2:
        indexes["metapred"] = {"pick": "home", "model_pct": None, "at": "2026-11-09T12:00:00Z"}
    key = "arsenal_chelsea_2026-11-09"
    return {
        "contract": "vanus.signal.v1",
        "generated_at": "2026-11-09T12:00:00Z",
        "slate_date": "2026-11-09",
        "indexes_vus": ["predictlix"],
        "matches": {
            key: {
                "match_key": key,
                "competition": "Premier League",
                "home": "Arsenal",
                "away": "Chelsea",
                "kickoff": "2026-11-09T20:00:00Z",
                "indexes": indexes,
                "consensus": {
                    "selection": selection,
                    "n": n,
                    "found": found,
                    "niveau": niveau,
                    "agreeing": ["predictlix"] if n == 1 else ["metapred", "predictlix"],
                },
                "marches": {},
                "reference": {"sharp": None, "sharp_issue": None, "sharp_marche": None, "source": None, "at": None},
                "couverture": {"n_index": 6, "n_presents": found, "n_marches": 0, "niveaux": "faible"},
                "holes": ["cotes_ou_2_5"],
            }
        },
        "holes": [],
    }


def _tix():
    return {
        "generated_at": "2026-11-09T00:00:00Z",
        "tickets": [{
            "rang_ticket": 1,
            "cote_totale": 1.9,
            "mise_fc": 100,
            "jambes": [{
                "match_id": "M1",
                "match": "Arsenal vs Chelsea",
                "date": "2026-11-09",
                "marche": "1X2",
                "selection": "1",
                "selection_label": "Victoire Domicile",
                "cote": 1.9,
                "p_modele": 0.58,
                "ev": 0.102,
            }],
        }],
        "budget": {"budget_fc": 300, "alloue_fc": 100, "reste_fc": 200},
        "warnings": [],
        "regles": {"jambes_max": 4, "mise_min_fc": 100.0},
    }


def _freeze(blob=None, tix=None, **kw):
    doc = tix if tix is not None else _tix()
    return ledger.freeze_lot(
        "L-V6A", "PARI-TEST", "C-V6A", doc,
        ledger.legs_from_tickets(doc["tickets"]), 300, 100,
        vanus_blob=blob, **kw)


def main():
    print("=" * 70)
    print("TEST V6 — ledger vanus")
    print("=" * 70)

    src = _src()
    check("v6.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("v6.pas_tickets_flag", "set_tickets" not in src and "tickets_enabled" not in src)
    check("v6.pas_poisson", "score_matrix" not in src and "lambda_dom" not in src)
    check("v6.stamp", "def stamp_vanus" in src)
    ast.parse(src)
    check("v6.ast", True)

    tix = _tix()
    p0 = tix["tickets"][0]["jambes"][0]["p_modele"]
    ev0 = tix["tickets"][0]["jambes"][0]["ev"]

    lot7 = ledger.freeze_lot(
        "L-7AR", "PARI-TEST", "C-7AR", _tix(),
        ledger.legs_from_tickets(_tix()["tickets"]), 300, 100)
    check("v6.freeze_7args", lot7.get("token") == "L-7AR")
    check("v6.7args_vanus_key", "vanus" in lot7, str(lot7.keys()))
    check("v6.7args_hole", "vanus_absent" in ((lot7.get("vanus") or {}).get("holes") or [])
          or "skip" in ((lot7.get("vanus") or {}).get("holes") or []),
          str((lot7.get("vanus") or {}).get("holes")))

    lot_jk = _freeze(_blob("jackpot", "home", n=6, found=6))
    jambe = ((lot_jk.get("snapshot_t0") or {}).get("tickets") or [{}])[0].get("jambes") or [{}]
    j0 = jambe[0]
    check("v6.jackpot_flag", j0.get("vanus_action") == "veto", str(j0.get("vanus_action")))
    check("v6.jackpot_flags", "vanus_jackpot" in (j0.get("vanus_flags") or []), str(j0.get("vanus_flags")))
    check("v6.jackpot_veto", j0.get("vanus_veto") == ["2"], str(j0.get("vanus_veto")))
    check("v6.jackpot_keep", j0.get("selection") == "1")
    check("v6.jackpot_p", j0.get("p_modele") == 0.58)
    check("v6.jackpot_ev", j0.get("ev") == 0.102)
    check("v6.jackpot_n_veto", (lot_jk.get("vanus") or {}).get("n_veto") == 1, str(lot_jk.get("vanus")))
    proc = (lot_jk.get("journal") or {}).get("procedure") or {}
    check("v6.jackpot_proc_check", "vanus_gate" in (proc.get("checks") or []), str(proc.get("checks")))

    lot_al = _freeze(_blob("alarme", "home", n=2, found=2))
    ja = ((lot_al.get("snapshot_t0") or {}).get("tickets") or [{}])[0]["jambes"][0]
    check("v6.alarme_info", ja.get("vanus_action") == "info", str(ja.get("vanus_action")))
    check("v6.alarme_flag", "vanus_alarme" in (ja.get("vanus_flags") or []))
    check("v6.alarme_p", ja.get("p_modele") == 0.58)
    check("v6.alarme_n_info", (lot_al.get("vanus") or {}).get("n_info") == 1)

    lot_is = _freeze(_blob("isole", "home", n=1, found=1))
    ji = ((lot_is.get("snapshot_t0") or {}).get("tickets") or [{}])[0]["jambes"][0]
    check("v6.isole_pass", ji.get("vanus_action") == "pass")
    check("v6.isole_p", ji.get("p_modele") == 0.58)

    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    try:
        lot_sk = _freeze(_blob("jackpot", "home", n=6, found=6))
        js = ((lot_sk.get("snapshot_t0") or {}).get("tickets") or [{}])[0]["jambes"][0]
        check("v6.skip_action", js.get("vanus_action") == "skip", str(js.get("vanus_action")))
        check("v6.skip_hole", "skip" in ((lot_sk.get("vanus") or {}).get("holes") or []),
              str((lot_sk.get("vanus") or {}).get("holes")))
        check("v6.skip_keep", js.get("selection") == "1" and js.get("p_modele") == 0.58)
        check("v6.skip_pas_veto", (lot_sk.get("vanus") or {}).get("n_veto") == 0)
    finally:
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    tix2 = _tix()
    tix2["tickets"][0]["jambes"].append({
        "match_id": "M2",
        "match": "Barca vs Madrid",
        "date": "2026-11-09",
        "marche": "1X2",
        "selection": "1",
        "cote": 2.10,
        "p_modele": 0.50,
        "ev": 0.05,
    })
    lot_miss = _freeze(_blob("jackpot", "home", n=6, found=6), tix=tix2)
    check("v6.match_miss", "vanus_match" in ((lot_miss.get("vanus") or {}).get("holes") or []),
          str((lot_miss.get("vanus") or {}).get("holes")))
    jmiss = ((lot_miss.get("snapshot_t0") or {}).get("tickets") or [{}])[0]["jambes"][1]
    check("v6.miss_p", jmiss.get("p_modele") == 0.50)

    check("v6.src_p_intact", tix["tickets"][0]["jambes"][0]["p_modele"] == p0)
    check("v6.src_ev_intact", tix["tickets"][0]["jambes"][0]["ev"] == ev0)
    check("v6.src_pas_flag", tix["tickets"][0]["jambes"][0].get("vanus_flags") is None)

    lot_kw = ledger.freeze_lot(
        "L-BND", "PARI-TEST", "C-BND", _tix(),
        ledger.legs_from_tickets(_tix()["tickets"]), 300, 100,
        bundle_id="B-V6")
    check("v6.kwargs_bundle", lot_kw.get("bundle_id") == "B-V6")

    check("v6.gel", moteur_flag.tickets_enabled() is False)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V6 ledger : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
