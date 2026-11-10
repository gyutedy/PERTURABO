#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V1 — market_csv Zero Data. Zero reseau. Fixture locale."""

import csv
import io
import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))

import market_csv  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    print("=" * 70)
    print("TEST V1 — market_csv")
    print("=" * 70)

    check("v1.num_refuse_1", market_csv._num("1.0") is None)
    check("v1.num_refuse_0", market_csv._num("0") is None)
    check("v1.num_refuse_vide", market_csv._num("") is None)
    check("v1.num_refuse_none", market_csv._num(None) is None)
    check("v1.num_ok", market_csv._num("1.85") == 1.85)
    check("v1.num_virgule", market_csv._num("2,10") == 2.10)

    check("v1.score_zero", market_csv._score("0") == 0)
    check("v1.score_un", market_csv._score("1") == 1)
    check("v1.score_vide", market_csv._score("") is None)

    tmp = tempfile.mkdtemp(prefix="pari-v1-")
    fields = [
        "Div", "Date", "HomeTeam", "AwayTeam",
        "FTHG", "FTAG", "HTHG", "HTAG",
        "B365H", "B365D", "B365A",
        "PSCH", "PSCD", "PSCA",
        "B365>2.5", "B365<2.5",
    ]
    _write_csv(os.path.join(tmp, "E0.csv"), fields, [
        {
            "Div": "E0", "Date": "09/08/2025", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea",
            "FTHG": "0", "FTAG": "0", "HTHG": "0", "HTAG": "0",
            "B365H": "1.85", "B365D": "3.60", "B365A": "4.20",
            "PSCH": "1.90", "PSCD": "3.50", "PSCA": "4.00",
            "B365>2.5": "1.80", "B365<2.5": "2.05",
        },
        {
            "Div": "E0", "Date": "10/08/2025", "HomeTeam": "Liverpool", "AwayTeam": "Everton",
            "FTHG": "2", "FTAG": "1", "HTHG": "1", "HTAG": "0",
            "B365H": "1.70", "B365D": "3.80", "B365A": "5.00",
            "PSCH": "", "PSCD": "", "PSCA": "",
            "B365>2.5": "1.90", "B365<2.5": "1.95",
        },
        {
            "Div": "E0", "Date": "bad", "HomeTeam": "Ghost", "AwayTeam": "Void",
            "FTHG": "1", "FTAG": "1", "HTHG": "0", "HTAG": "0",
            "B365H": "2.00", "B365D": "3.20", "B365A": "3.80",
            "PSCH": "2.10", "PSCD": "3.10", "PSCA": "3.70",
            "B365>2.5": "1.85", "B365<2.5": "2.00",
        },
    ])
    _write_csv(os.path.join(tmp, "SP1.csv"), fields, [
        {
            "Div": "SP1", "Date": "2025-08-11", "HomeTeam": "Barca", "AwayTeam": "Madrid",
            "FTHG": "3", "FTAG": "1", "HTHG": "2", "HTAG": "0",
            "B365H": "2.10", "B365D": "3.40", "B365A": "3.50",
            "PSCH": "2.20", "PSCD": "3.30", "PSCA": "3.40",
            "B365>2.5": "1.70", "B365<2.5": "2.20",
        },
    ])

    blob = market_csv.load_dir(tmp)
    check("v1.n_lignes", blob["n_lignes"] if False else len(blob["rows"]) == 3, str(len(blob["rows"])))
    check("v1.files", blob["files"] == ["E0.csv", "SP1.csv"], str(blob["files"]))
    check("v1.columns_reelles", "B365H" in blob["columns"] and "PSCH" in blob["columns"], str(blob["columns"][:8]))
    check("v1.pas_invente", "FAKECOL" not in blob["columns"])

    rows = blob["rows"]
    r0 = rows[0]
    check("v1.ouverts", r0["ouverts"]["home"] == 1.85 and r0["ouverts"]["draw"] == 3.60)
    check("v1.cloture", r0["cloture"]["home"] == 1.90)
    check("v1.ou_ouverts", "2.5" in r0["ou_ouverts"] and r0["ou_ouverts"]["2.5"]["over"] == 1.80)
    check("v1.score_00", r0["fthg"] == 0 and r0["ftag"] == 0 and "score_ft" not in r0["holes"])
    check("v1.champs", all(k in r0 for k in ("ouverts", "cloture", "ou_ouverts", "holes")))

    r1 = next(r for r in rows if r["home"] == "Liverpool")
    check("v1.cloture_none", r1["cloture"]["home"] is None)
    check("v1.hole_cloture", "cotes_1x2_cloture" in r1["holes"], str(r1["holes"]))

    r_ghost = [r for r in rows if r["home"] == "Ghost"]
    check("v1.date_bad_skip", r_ghost == [])

    absent = market_csv.load_dir(os.path.join(tmp, "nope"))
    check("v1.dossier_absent", absent["holes"] == ["dossier_absent"] and absent["rows"] == [])

    empty = tempfile.mkdtemp(prefix="pari-v1e-")
    vide = market_csv.load_dir(empty)
    check("v1.aucune_ligne", vide["holes"] == ["aucune_ligne"])

    rec_path = os.path.join(tmp, "inventaire.json")
    old_argv = sys.argv
    buf = io.StringIO()
    sys.argv = ["market_csv.py", "--dir", tmp, "--inventaire", "--out", rec_path]
    try:
        old_stdout = sys.stdout
        sys.stdout = buf
        market_csv.main()
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv
    rec = json.load(open(rec_path, encoding="utf-8"))
    check("v1.inventaire_n", rec["n_lignes"] == 3, str(rec["n_lignes"]))
    check("v1.inventaire_div", rec["divisions"].get("E0") == 2 and rec["divisions"].get("SP1") == 1, str(rec["divisions"]))
    check("v1.hors_couverture", "I1" in rec["hors_couverture"] and "E0" not in rec["hors_couverture"], str(rec["hors_couverture"]))
    check("v1.hors_pas_estime", rec["divisions"].get("I1") is None)

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"V1 market_csv : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
