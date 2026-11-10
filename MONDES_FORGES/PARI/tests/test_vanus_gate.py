#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V3 — vanus_gate greffe vanus.signal.v1. Zero reseau. Jamais un p. Gel intact."""

import ast
import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import moteur_flag  # noqa: E402
import vanus_gate as vg  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "vanus_gate.py"), encoding="utf-8").read()


def _capteurs():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "capteurs.py"), encoding="utf-8").read()


def _qual():
    return open(os.path.join(WORLD, "TYRANT", "CODEBASE", "qualitative.py"), encoding="utf-8").read()


def _blob(niveau="isole", selection="home", n=1, found=1, extra_index=True):
    indexes = {
        "predictlix": {"pick": "home", "model_pct": None, "at": "2026-11-09T10:00:00Z"},
        "dailysportpick": None,
        "metapred": None,
        "footinsights": None,
        "besoccer": None,
        "vitibet": None,
    }
    if extra_index and n >= 2:
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


def _write(blob):
    tmp = tempfile.mkdtemp(prefix="pari-vg-")
    path = os.path.join(tmp, "latest.json")
    json.dump(blob, open(path, "w", encoding="utf-8"))
    return path


def main():
    print("=" * 70)
    print("TEST V3 — vanus_gate")
    print("=" * 70)

    src = _src()
    check("vg.pas_p_modele", "p_modele" not in src)
    check("vg.pas_poisson", "score_matrix" not in src and "poisson" not in src)
    check("vg.pas_lambda", "lambda_dom" not in src)
    check("vg.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("vg.pas_tickets", "set_tickets" not in src and "tickets_enabled" not in src)
    check("vg.pas_capteurs", "vanus_gate" not in _capteurs())
    check("vg.pas_qualitative", "vanus_gate" not in _qual())
    ast.parse(src)
    check("vg.ast", True)

    check("vg.key", vg.match_key("Arsenal", "Chelsea", "2026-11-09") == "arsenal_chelsea_2026-11-09")
    check("vg.key_sorted", vg.match_key("Chelsea", "Arsenal", "2026-11-09") == "arsenal_chelsea_2026-11-09")

    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    try:
        rec = vg.gate("Arsenal", "Chelsea", "2026-11-09", blob=_blob("jackpot", n=6, found=6))
        check("vg.skip_hole", rec["holes"] == ["skip"] and rec["action"] == "skip", str(rec))
        check("vg.skip_pas_veto", rec["veto"] == [] and rec["ok"] is False)
    finally:
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    rec_abs = vg.gate("Arsenal", "Chelsea", "2026-11-09", path=os.path.join(tempfile.mkdtemp(prefix="pari-vg-x-"), "nope.json"))
    check("vg.absent", "vanus_absent" in rec_abs["holes"] and rec_abs["action"] == "skip", str(rec_abs))

    bad = _write({"contract": "nope", "matches": {}})
    rec_bad = vg.gate("Arsenal", "Chelsea", "2026-11-09", path=bad)
    check("vg.contrat", "contrat" in rec_bad["holes"] and rec_bad["action"] == "skip", str(rec_bad))

    rec_miss = vg.gate("Barca", "Madrid", "2026-11-09", blob=_blob("alarme", n=2, found=2))
    check("vg.match_miss", "vanus_match" in rec_miss["holes"] and rec_miss["action"] == "skip", str(rec_miss))

    rec_is = vg.gate("Arsenal", "Chelsea", "2026-11-09", blob=_blob("isole", n=1, found=1))
    check("vg.isole_pass", rec_is["action"] == "pass" and rec_is["ok"] is True, str(rec_is))
    check("vg.isole_pas_veto", rec_is["veto"] == [] and rec_is["flags"] == [])
    check("vg.isole_trou_ou", "cotes_ou_2_5" in rec_is["holes"], str(rec_is["holes"]))

    rec_al = vg.gate("Arsenal", "Chelsea", "2026-11-09", blob=_blob("alarme", n=2, found=2))
    check("vg.alarme_info", rec_al["action"] == "info" and rec_al["flags"] == ["vanus_alarme"], str(rec_al))
    check("vg.alarme_pas_veto", rec_al["veto"] == [])

    rec_jk = vg.gate("Arsenal", "Chelsea", "2026-11-09", blob=_blob("jackpot", selection="home", n=6, found=6))
    check("vg.jackpot_veto", rec_jk["action"] == "veto" and rec_jk["flags"] == ["vanus_jackpot"], str(rec_jk))
    check("vg.jackpot_oppose", rec_jk["veto"] == ["2"], str(rec_jk["veto"]))

    rec_none = vg.gate("Arsenal", "Chelsea", "2026-11-09", blob=_blob("aucun", selection=None, n=0, found=0, extra_index=False))
    check("vg.aucun_pass", rec_none["action"] == "pass" and rec_none["veto"] == [], str(rec_none))

    ev = {"id": "M1", "dom": "Arsenal", "ext": "Chelsea", "date": "2026-11-09", "p_modele": 0.55, "ev": 0.12, "cote": 2.10}
    stamped = vg.stamp_event(ev, rec_al)
    check("vg.stamp_flag", stamped.get("vanus_flags") == ["vanus_alarme"])
    check("vg.stamp_p_intact", stamped.get("p_modele") == 0.55 and stamped.get("ev") == 0.12)
    check("vg.stamp_src_intact", ev.get("vanus_flags") is None)

    preds = {"matchs": [dict(ev)]}
    out = vg.stamp_predictions(preds, blob=_blob("jackpot", selection="home", n=6, found=6))
    check("vg.pred_veto", out["matchs"][0].get("vanus_action") == "veto")
    check("vg.pred_p", out["matchs"][0].get("p_modele") == 0.55)

    idx = rec_is
    check("vg.null_pas_zero", _blob()["matches"]["arsenal_chelsea_2026-11-09"]["indexes"]["metapred"] is None)
    check("vg.gel", moteur_flag.tickets_enabled() is False)
    check("vg.pick_map", vg.PICK_TO_PARI["over_2_5"] == "o2.5")

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V3 vanus_gate : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
