#!/usr/bin/env python3
"""
MARKET BASKET — contrat de donnees boxscores (stdlib, offline).
=============================================================
CSV: game_id,date,team_home,team_away,pts_home,pts_away
Colonnes optionnelles: odds_home, odds_away (cotes de cloture 2-way pour le
Brier marche du backtest). Absentes = None + trou `marche_absent` cote backtest,
jamais 0, jamais 1.0. La ligne reste valide pour le fit.
Regles heritees de market_csv.py (foot) :
  - valeur absente = None, jamais 0, jamais estimee ;
  - trous declares dans "holes", jamais silencieux ;
  - aucune cote lue ici (le prix reste une competence F03).
"""
from __future__ import annotations
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_DIR = os.path.join(WORLD, "ARCHIVUM", "cache", "basket")
REQUIRED = ("game_id", "date", "team_home", "team_away", "pts_home", "pts_away")


def _num(raw):
    """int ou None. Une cellule vide/videuse = None, jamais 0."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _date(raw):
    raw = (raw or "").strip()
    return raw if raw else None


def _odds_num(raw):
    """Cote 2-way : float > 1.0 ou None. Jamais 0, jamais 1.0."""
    txt = str(raw or "").strip().replace(",", ".")
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val > 1.0 else None


def read_rows(path):
    """Lignes brutes du CSV + holes d'entete. Jamais d'exception sur donnee sale."""
    holes = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return [], ["entete_absente"]
            missing = [c for c in REQUIRED if c not in reader.fieldnames]
            if missing:
                return [], ["colonnes_absentes:" + ",".join(missing)]
            rows = list(reader)
    except OSError:
        return [], ["fichier_illisible"]
    return rows, holes


def normalize(row):
    """Une ligne CSV -> dict contrat. Equipe absente = ligne ecartee avec trou."""
    holes = []
    home = (row.get("team_home") or "").strip()
    away = (row.get("team_away") or "").strip()
    ph, pa = _num(row.get("pts_home")), _num(row.get("pts_away"))
    if not home or not away:
        holes.append("equipe_absente")
    if ph is None or pa is None:
        holes.append("score_absent")
    gid = (row.get("game_id") or "").strip()
    if not gid:
        holes.append("game_id_absent")
    return {
        "game_id": gid or None,
        "date": _date(row.get("date")),
        "home": home or None,
        "away": away or None,
        "pts_home": ph,
        "pts_away": pa,
        "odds_home": _odds_num(row.get("odds_home")),
        "odds_away": _odds_num(row.get("odds_away")),
        "source_prix": (row.get("source_prix") or "").strip() or None,
        "holes": holes,
    }


def load_dir(csv_dir=None):
    """Tous les CSV du dossier -> (rows valides, holes globaux)."""
    d = csv_dir or DEFAULT_DIR
    rows, holes = [], []
    if not os.path.isdir(d):
        return [], ["dossier_absent:" + d]
    for name in sorted(os.listdir(d)):
        if not name.lower().endswith(".csv"):
            continue
        raw, h = read_rows(os.path.join(d, name))
        holes.extend([name + ":" + x for x in h])
        for r in raw:
            n = normalize(r)
            if n["holes"]:
                holes.append(name + ":" + ",".join(n["holes"]))
            else:
                rows.append(n)
    return rows, holes


def main():
    rows, holes = load_dir()
    print("matchs valides:", len(rows))
    print("holes:", len(holes))
    for h in holes[:20]:
        print("  -", h)


if __name__ == "__main__":
    main()
