#!/usr/bin/env python3
"""
MARKET CSV — lecture normalisee des CSV football-data.co.uk (stdlib, offline).
=============================================================================
Sortie : lignes normalisees + inventaire des colonnes trouvees/absentes.
Aucune colonne inventee. Une cote absente reste None, jamais 0, jamais 1.0.

Convention de nommage football-data :
  ouverture   B365H / B365D / B365A, B365>2.5 / B365<2.5, PSH / PSD / PSA
  cloture     PSCH / PSCD / PSCA, PC>2.5 / PC<2.5, PSCHH ...
  resultat    FTHG / FTAG / FTR, HTHG / HTAG / HTR

Usage :
  python market_csv.py --dir ARCHIVUM/cache/f00 --inventaire
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from datetime import datetime

BOOKS = ("B365", "PS", "P", "BF", "BW", "IW", "WH", "VC", "LB")
OU_LINES = ("2.5", "1.5", "3.5", "4.5", "0.5")
COVERED = ("E0", "E1", "SP1", "I1", "D1", "D2", "F1", "N1", "T1", "J1")


def _num(raw):
    if raw is None:
        return None
    txt = str(raw).strip().replace(",", ".")
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val > 1.0 else None


def _score(raw):
    if raw is None:
        return None
    txt = str(raw).strip().replace(",", ".")
    if not txt:
        return None
    try:
        val = int(float(txt))
    except ValueError:
        return None
    return val if val >= 0 else None


def _date(raw):
    txt = (raw or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def _pair(row, home_key, away_key):
    return _num(row.get(home_key)), _num(row.get(away_key))


def read_rows(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(io.StringIO(f.read())))


def normalize(row):
    """Une ligne CSV -> un dict normalise. Trous declares dans `holes`."""
    holes = []
    dt = _date(row.get("Date"))
    fthg, ftag = _score(row.get("FTHG")), _score(row.get("FTAG"))
    hthg, htag = _score(row.get("HTHG")), _score(row.get("HTAG"))
    home = (row.get("HomeTeam") or "").strip()
    away = (row.get("AwayTeam") or "").strip()
    if dt is None:
        holes.append("date")
    if fthg is None or ftag is None:
        holes.append("score_ft")
    if hthg is None or htag is None:
        holes.append("score_ht")
    o_h, o_d, o_a = None, None, None
    c_h, c_d, c_a = None, None, None
    used = {}
    for tag in BOOKS:
        h, d, a = (_num(row.get(tag + "H")), _num(row.get(tag + "D")),
                   _num(row.get(tag + "A")))
        if h and d and a:
            o_h, o_d, o_a = h, d, a
            used["1x2"] = tag
            break
    for tag in BOOKS:
        h, d, a = (_num(row.get(tag + "CH")), _num(row.get(tag + "CD")),
                   _num(row.get(tag + "CA")))
        if h and d and a:
            c_h, c_d, c_a = h, d, a
            used["1x2_close"] = tag
            break
    ou_open, ou_close = {}, {}
    for tag in BOOKS:
        for line in OU_LINES:
            over = _num(row.get(tag + ">" + line))
            under = _num(row.get(tag + "<" + line))
            if over and under and line not in ou_open:
                ou_open[line] = {"over": over, "under": under, "book": tag}
    for tag in BOOKS:
        for line in OU_LINES:
            over = _num(row.get(tag + "C>" + line))
            under = _num(row.get(tag + "C<" + line))
            if over and under and line not in ou_close:
                ou_close[line] = {"over": over, "under": under, "book": tag}
    if not (o_h and o_d and o_a):
        holes.append("cotes_1x2")
    if not (c_h and c_d and c_a):
        holes.append("cotes_1x2_cloture")
    if not ou_open:
        holes.append("cotes_ou")
    return {
        "div": (row.get("Div") or "").strip().upper(),
        "date": dt.strftime("%Y-%m-%d") if dt else None,
        "home": home,
        "away": away,
        "fthg": fthg,
        "ftag": ftag,
        "hthg": hthg,
        "htag": htag,
        "ouverts": {"home": o_h, "draw": o_d, "away": o_a},
        "cloture": {"home": c_h, "draw": c_d, "away": c_a},
        "ou_ouverts": ou_open,
        "ou_cloture": ou_close,
        "books": used,
        "holes": holes,
    }


def load_dir(csv_dir):
    """Toutes les lignes de tous les CSV du dossier, triees par date, + inventaire."""
    rows = []
    fichiers = []
    colonnes = set()
    if not csv_dir or not os.path.isdir(csv_dir):
        return {"rows": [], "files": [], "columns": [], "holes": ["dossier_absent"]}
    for name in sorted(os.listdir(csv_dir)):
        if not name.lower().endswith(".csv"):
            continue
        path = os.path.join(csv_dir, name)
        raw = read_rows(path)
        if not raw:
            continue
        colonnes.update(raw[0].keys())
        fichiers.append(name)
        for r in raw:
            n = normalize(r)
            if n.get("date"):
                n["file"] = name
                rows.append(n)
    rows.sort(key=lambda r: r["date"])
    return {
        "rows": rows,
        "files": fichiers,
        "columns": sorted(colonnes),
        "holes": [] if rows else ["aucune_ligne"],
    }


def by_div(rows):
    out = {}
    for r in rows:
        out.setdefault(r["div"], []).append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "ARCHIVUM", "cache", "f00"))
    ap.add_argument("--inventaire", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    blob = load_dir(args.dir)
    divisions = {k: len(v) for k, v in by_div(blob["rows"]).items()}
    rec = {
        "dir": os.path.abspath(args.dir),
        "files": blob["files"],
        "n_lignes": len(blob["rows"]),
        "divisions": divisions,
        "hors_couverture": [c for c in COVERED if c not in divisions],
        "columns": blob["columns"],
        "holes": blob["holes"],
    }
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
