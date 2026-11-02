"""
F00 BACKTEST — parts MT1 et pente Elo depuis CSV cache (offline).
=================================================================
Lit les CSV football-data deja caches. Zero reseau, zero requete externe.
Sortie shares.json : {CODE: {part_mt1, n_mt, elo_slope, n_elo}}.

Usage:
  python backtest.py --csv-dir ARCHIVUM/cache/f00 --out ARCHIVUM/learnings/shares.json
"""

import argparse
import csv
import io
import json
import math
import os
from datetime import datetime, timezone


def _num(row, key):
    v = row.get(key)
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _dkey(row):
    raw = (row.get("Date") or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.min


def load_csv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    return list(csv.DictReader(io.StringIO(text)))


def part_mt1(rows):
    parts, n = 0.0, 0
    for r in rows:
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        hthg, htag = _num(r, "HTHG"), _num(r, "HTAG")
        if None in (fthg, ftag, hthg, htag):
            continue
        tot = fthg + ftag
        if tot <= 0:
            continue
        parts += (hthg + htag) / tot
        n += 1
    if n == 0:
        return None, 0
    return parts / n, n


def elo_slope(rows, elo_map):
    """Pente buts_dom - buts_ext vs (elo_dom - elo_ext)/400. Finite ou None."""
    if not elo_map:
        return None, 0
    xs, ys = [], []
    for r in rows:
        home, away = (r.get("HomeTeam") or "").strip(), (r.get("AwayTeam") or "").strip()
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        eh, ea = elo_map.get(home), elo_map.get(away)
        if None in (fthg, ftag, eh, ea):
            continue
        xs.append((eh - ea) / 400.0)
        ys.append(fthg - ftag)
    n = len(xs)
    if n < 8:
        return None, n
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0, n
    slope = num / den
    if not math.isfinite(slope):
        return None, n
    return slope, n


def measure_file(path, elo_map=None):
    rows = load_csv(path)
    if not rows:
        return None
    code = (rows[0].get("Div") or os.path.basename(path).split("_")[1] if "_" in os.path.basename(path) else "").upper()
    part, n_mt = part_mt1(rows)
    slope, n_elo = elo_slope(rows, elo_map or {})
    rec = {"league_code": code, "n_mt": n_mt, "n_elo": n_elo, "source": os.path.basename(path)}
    if part is not None:
        rec["part_mt1"] = round(part, 4)
    if slope is not None:
        rec["elo_slope"] = round(slope, 6)
    return rec


def scan_dir(csv_dir, elo_map=None):
    out = {}
    if not csv_dir or not os.path.isdir(csv_dir):
        return out
    for name in sorted(os.listdir(csv_dir)):
        if not name.lower().endswith(".csv"):
            continue
        rec = measure_file(os.path.join(csv_dir, name), elo_map=elo_map)
        if rec and rec.get("league_code"):
            out[rec["league_code"]] = rec
    return out


def load_elo(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        blob = json.load(f)
    if isinstance(blob, dict) and "teams" in blob:
        blob = blob["teams"]
    out = {}
    if isinstance(blob, dict):
        for k, v in blob.items():
            try:
                out[k] = float(v if not isinstance(v, dict) else v.get("elo"))
            except (TypeError, ValueError):
                continue
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    world = os.path.normpath(os.path.join(here, "..", ".."))
    parser = argparse.ArgumentParser(description="F00 BACKTEST shares MT1 / Elo (offline)")
    parser.add_argument("--csv-dir", default=os.environ.get("PARI_UK_CACHE") or os.path.join(world, "ARCHIVUM", "cache", "f00"))
    parser.add_argument("--elo", default=None)
    parser.add_argument("--out", default=os.path.join(world, "ARCHIVUM", "learnings", "shares.json"))
    args = parser.parse_args()
    elo_map = load_elo(args.elo)
    shares = scan_dir(args.csv_dir, elo_map=elo_map)
    blob = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offline": True,
        "leagues": shares,
    }
    for code, rec in shares.items():
        blob[code] = rec
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
    print(f"[BACKTEST] {len(shares)} ligue(s) → {args.out}")
    for code, rec in shares.items():
        print(f"  {code} part_mt1={rec.get('part_mt1')} n={rec.get('n_mt')} elo_slope={rec.get('elo_slope')}")


if __name__ == "__main__":
    main()
