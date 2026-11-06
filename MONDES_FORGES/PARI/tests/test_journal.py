#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 — journal 2 volets. procedure immutable, outcome au settle. Zero reseau."""

import json
import os
import shutil
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))

import journal  # noqa: E402
import ledger  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _tix():
    return {
        "generated_at": "2026-11-06T00:00:00Z",
        "tickets": [{
            "rang_ticket": 1,
            "cote_totale": 1.7,
            "mise_fc": 100,
            "jambes": [{
                "match_id": "M1",
                "match": "Arsenal vs Chelsea",
                "marche": "1X2",
                "selection": "1",
                "selection_label": "Victoire Domicile",
                "cote": 1.7,
            }],
        }],
        "budget": {"budget_fc": 300, "alloue_fc": 100, "reste_fc": 200},
        "warnings": [],
        "regles": {"jambes_max": 4, "mise_min_fc": 100.0},
    }


def test_build_holes():
    proc = journal.build_procedure(_tix())
    holes = proc.get("holes") or []
    check("j.holes_kelly", "kelly" in holes, str(holes))
    check("j.holes_seuils", "seuils" in holes, str(holes))
    check("j.kelly_none", proc.get("kelly") is None)
    check("j.seuils_none", proc.get("seuils") is None)
    extra = journal.build_procedure(_tix(), extra={
        "kelly": {"fraction": 0.125},
        "seuils": {"ev": 0.03},
        "checks": ["doctor"],
    })
    check("j.extra_kelly", extra.get("kelly", {}).get("fraction") == 0.125)
    check("j.extra_pas_hole_kelly", "kelly" not in (extra.get("holes") or []))


def test_attach_immutable():
    lot = {"token": "L-AAA"}
    journal.attach_procedure(lot, _tix())
    check("j.proc_pose", "procedure" in (lot.get("journal") or {}))
    frozen = json.dumps(lot["journal"]["procedure"], sort_keys=True)
    raised = False
    try:
        journal.attach_procedure(lot, _tix())
    except ValueError:
        raised = True
    check("j.proc_refuse_rewrite", raised)
    check("j.proc_intact", json.dumps(lot["journal"]["procedure"], sort_keys=True) == frozen)


def test_freeze_lot_7args():
    tix = _tix()
    lot = ledger.freeze_lot(
        "L-TST", "PARI-TEST", "C-ZZZ", tix,
        ledger.legs_from_tickets(tix["tickets"]), 300, 100)
    check("j.freeze_7args", lot.get("token") == "L-TST")
    proc = (lot.get("journal") or {}).get("procedure") or {}
    check("j.freeze_proc", bool(proc.get("checks")), str(proc.keys()))
    check("j.freeze_sans_outcome", "outcome" not in (lot.get("journal") or {}))


def test_outcome_settle_no_mutate():
    tmp = tempfile.mkdtemp(prefix="pari_jnl_")
    old_lots = ledger.LOTS_PATH
    try:
        lots_path = os.path.join(tmp, "lots.json")
        ledger.LOTS_PATH = lots_path
        tix = _tix()
        lot = ledger.freeze_lot(
            "L-SET", "PARI-TEST", "C-ZZZ", tix,
            ledger.legs_from_tickets(tix["tickets"]), 300, 100)
        ledger.append_lot(lot, lots_path)
        frozen = json.dumps(lot["journal"]["procedure"], sort_keys=True)
        csv_path = os.path.join(tmp, "settle.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("HomeTeam,AwayTeam,FTR\nArsenal,Chelsea,H\n")
        got, err = ledger.settle_lot("L-SET", csv_path, lots_path)
        check("j.settle_err", err is None, str(err))
        out = (got.get("journal") or {}).get("outcome") or {}
        check("j.outcome_pose", bool(out.get("tickets")), str(out.keys()))
        rec = (out.get("tickets") or [{}])[0]
        check("j.outcome_G", rec.get("resultat") == "G", str(rec.get("resultat")))
        check("j.outcome_mise", rec.get("mise_fc") == 100, str(rec.get("mise_fc")))
        check("j.outcome_cote", rec.get("cote") == 1.7, str(rec.get("cote")))
        check("j.clv_trou", rec.get("clv") is None and "clv" in (out.get("holes") or []),
              str(out.get("holes")))
        check("j.clv_pas_zero", rec.get("clv") != 0)
        check("j.proc_apres_settle",
              json.dumps(got["journal"]["procedure"], sort_keys=True) == frozen)
    finally:
        ledger.LOTS_PATH = old_lots
        shutil.rmtree(tmp, ignore_errors=True)


def test_attach_outcome_keeps_procedure():
    lot = {"token": "L-BBB", "snapshot_t0": {"tickets": []}, "settle": {"tickets": []}}
    journal.attach_procedure(lot, _tix(), procedure={"checks": ["x"], "holes": ["kelly"]})
    frozen = json.dumps(lot["journal"]["procedure"], sort_keys=True)
    journal.attach_outcome(lot)
    check("j.outcome_sans_mute",
          json.dumps(lot["journal"]["procedure"], sort_keys=True) == frozen)


def main():
    print("=" * 70)
    print("TEST S3 — journal")
    print("=" * 70)
    test_build_holes()
    test_attach_immutable()
    test_freeze_lot_7args()
    test_outcome_settle_no_mutate()
    test_attach_outcome_keeps_procedure()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S3 journal : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
