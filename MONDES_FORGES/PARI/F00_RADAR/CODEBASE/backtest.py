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
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.insert(0, HERE)


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


def _alnum(name):
    return "".join(c for c in (name or "").lower() if c.isalnum())


def _team_key(name):
    try:
        from capteurs import team_key
        return team_key(name) or _alnum(name)
    except Exception:
        return _alnum(name)


def _index_elo(elo_map):
    idx = {}
    for k, v in (elo_map or {}).items():
        if v is None:
            continue
        try:
            val = float(v)
        except (TypeError, ValueError):
            continue
        idx[_alnum(k)] = val
        tk = _team_key(k)
        if tk:
            idx.setdefault(tk, val)
    return idx


def _elo_of(idx, name):
    if not name:
        return None
    raw = (name or "").strip()
    if raw in idx:
        return idx[raw]
    a = _alnum(raw)
    if a in idx:
        return idx[a]
    tk = _team_key(raw)
    if tk in idx:
        return idx[tk]
    return None


def elo_slope(rows, elo_map):
    """Pente buts_dom - buts_ext vs (elo_dom - elo_ext)/400. Finite ou None."""
    if not elo_map:
        return None, 0
    idx = _index_elo(elo_map)
    xs, ys = [], []
    for r in rows:
        home, away = (r.get("HomeTeam") or "").strip(), (r.get("AwayTeam") or "").strip()
        fthg, ftag = _num(r, "FTHG"), _num(r, "FTAG")
        eh, ea = _elo_of(idx, home), _elo_of(idx, away)
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


def _season_of(name):
    stem = os.path.splitext(os.path.basename(name))[0]
    parts = stem.split("_")
    if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) in (4, 6):
        return parts[-1]
    return None


def measure_file(path, elo_map=None):
    rows = load_csv(path)
    if not rows:
        return None
    base = os.path.basename(path)
    code = (rows[0].get("Div") or (base.split("_")[1] if "_" in base else "")).upper()
    part, n_mt = part_mt1(rows)
    slope, n_elo = elo_slope(rows, elo_map or {})
    rec = {"league_code": code, "n_mt": n_mt, "n_elo": n_elo, "source": base, "n_files": 1}
    season = _season_of(base)
    if season:
        rec["seasons"] = [season]
    if part is not None:
        rec["part_mt1"] = round(part, 4)
    if slope is not None:
        rec["elo_slope"] = round(slope, 6)
    return rec


def merge_recs(a, b):
    """Fusion ponderee par n. Dernier fichier n'ecrase plus. Zero Data si n=0."""
    if not a:
        return b
    if not b:
        return a
    n_mt = (a.get("n_mt") or 0) + (b.get("n_mt") or 0)
    wa = (a.get("n_mt") or 0) if a.get("part_mt1") is not None else 0
    wb = (b.get("n_mt") or 0) if b.get("part_mt1") is not None else 0
    part = None
    if wa + wb:
        part = ((a.get("part_mt1") or 0) * wa + (b.get("part_mt1") or 0) * wb) / (wa + wb)
    n_elo = (a.get("n_elo") or 0) + (b.get("n_elo") or 0)
    wea = (a.get("n_elo") or 0) if a.get("elo_slope") is not None else 0
    web = (b.get("n_elo") or 0) if b.get("elo_slope") is not None else 0
    slope = None
    if wea + web:
        slope = ((a.get("elo_slope") or 0) * wea + (b.get("elo_slope") or 0) * web) / (wea + web)
    sources = []
    for rec in (a, b):
        src = rec.get("sources") or rec.get("source")
        if isinstance(src, list):
            sources.extend(src)
        elif src:
            sources.append(src)
    seasons = []
    for rec in (a, b):
        seasons.extend(rec.get("seasons") or [])
    rec = {
        "league_code": a.get("league_code") or b.get("league_code"),
        "n_mt": n_mt,
        "n_elo": n_elo,
        "source": sources[-1] if sources else None,
        "sources": sources,
        "n_files": (a.get("n_files") or 1) + (b.get("n_files") or 1),
        "seasons": sorted(set(seasons)),
    }
    if part is not None:
        rec["part_mt1"] = round(part, 4)
    if slope is not None and math.isfinite(slope):
        rec["elo_slope"] = round(slope, 6)
    return rec


def scan_dir(csv_dir, elo_map=None):
    """Groupe par ligue, concatene les lignes, mesure une fois (pente Elo juste)."""
    out = {}
    if not csv_dir or not os.path.isdir(csv_dir):
        return out
    buckets = {}
    files = {}
    for name in sorted(os.listdir(csv_dir)):
        if not name.lower().endswith(".csv"):
            continue
        path = os.path.join(csv_dir, name)
        rows = load_csv(path)
        if not rows:
            continue
        code = (rows[0].get("Div") or (name.split("_")[1] if "_" in name else "")).upper()
        if not code:
            continue
        buckets.setdefault(code, []).extend(rows)
        files.setdefault(code, []).append(name)
    for code, rows in buckets.items():
        part, n_mt = part_mt1(rows)
        slope, n_elo = elo_slope(rows, elo_map or {})
        seasons = []
        for name in files[code]:
            s = _season_of(name)
            if s:
                seasons.append(s)
        rec = {
            "league_code": code,
            "n_mt": n_mt,
            "n_elo": n_elo,
            "source": files[code][-1],
            "sources": files[code],
            "n_files": len(files[code]),
            "seasons": sorted(set(seasons)),
        }
        if part is not None:
            rec["part_mt1"] = round(part, 4)
        if slope is not None:
            rec["elo_slope"] = round(slope, 6)
        out[code] = rec
    return out


def load_elo(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        blob = json.load(f)
    if isinstance(blob, dict):
        if "elos" in blob and isinstance(blob["elos"], dict):
            blob = blob["elos"]
        elif "teams" in blob and isinstance(blob["teams"], dict):
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
    parser.add_argument("--elo", default=os.path.join(world, "ARCHIVUM", "teams", "elo.json"))
    parser.add_argument("--out", default=os.path.join(world, "ARCHIVUM", "learnings", "shares.json"))
    args = parser.parse_args()
    elo_map = load_elo(args.elo)
    shares = scan_dir(args.csv_dir, elo_map=elo_map)
    blob = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offline": True,
        "leagues": shares,
        "holes": [] if elo_map else ["elo"],
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
