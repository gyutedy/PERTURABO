"""
F02 BASELINE — moyennes ligue saison complete + recency EMA (stdlib, offline).
==============================================================================
CSV football-data caches. Demi-vie defaut 45j (config/league_fit.json).
Saison absente → None (breacher retombe sur l'echantillon carte + flag).
Split att/def domicile/exterieur par equipe. Zero reseau.

Usage:
  python baseline.py --csv tests/fixtures/uk_SP1_2526.csv --as-of 2025-10-06
"""

import argparse
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F00 = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
if F00 not in sys.path:
    sys.path.insert(0, F00)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import backtest  # noqa: E402
import league_fit  # noqa: E402


def ema_weight(age_days, half_life=45.0):
    if half_life is None or half_life <= 0:
        return 1.0
    if age_days is None or age_days <= 0:
        return 1.0
    return 0.5 ** (float(age_days) / float(half_life))


def _as_of_dt(as_of, parsed):
    if as_of is None:
        return max(p[0] for p in parsed)
    if isinstance(as_of, datetime):
        return as_of
    raw = str(as_of).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return max(p[0] for p in parsed)


def compute_baseline(rows, as_of=None, half_life=None):
    cfg = league_fit.load_config()
    if half_life is None:
        half_life = float(cfg.get("half_life_days") or 45)
    parsed = []
    for r in rows:
        dt = backtest._dkey(r)
        if dt == datetime.min:
            continue
        fthg, ftag = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if fthg is None or ftag is None:
            continue
        home = (r.get("HomeTeam") or "").strip()
        away = (r.get("AwayTeam") or "").strip()
        parsed.append((dt, home, away, fthg, ftag))
    if not parsed:
        return None
    ref = _as_of_dt(as_of, parsed)
    w_sum = s_dom = s_ext = 0.0
    teams = {}

    def acc(name):
        return teams.setdefault(name, {
            "att_dom": 0.0, "w_att_dom": 0.0,
            "def_dom": 0.0, "w_def_dom": 0.0,
            "att_ext": 0.0, "w_att_ext": 0.0,
            "def_ext": 0.0, "w_def_ext": 0.0,
            "n": 0,
        })

    for dt, home, away, fthg, ftag in parsed:
        age = max((ref - dt).days, 0)
        w = ema_weight(age, half_life)
        s_dom += fthg * w
        s_ext += ftag * w
        w_sum += w
        if home:
            t = acc(home)
            t["att_dom"] += fthg * w
            t["w_att_dom"] += w
            t["def_dom"] += ftag * w
            t["w_def_dom"] += w
            t["n"] += 1
        if away:
            t = acc(away)
            t["att_ext"] += ftag * w
            t["w_att_ext"] += w
            t["def_ext"] += fthg * w
            t["w_def_ext"] += w
            t["n"] += 1
    if w_sum <= 0:
        return None
    out_teams = {}
    for name, t in teams.items():
        rec = {"n": t["n"]}
        rec["att_dom"] = (t["att_dom"] / t["w_att_dom"]) if t["w_att_dom"] else None
        rec["def_dom"] = (t["def_dom"] / t["w_def_dom"]) if t["w_def_dom"] else None
        rec["att_ext"] = (t["att_ext"] / t["w_att_ext"]) if t["w_att_ext"] else None
        rec["def_ext"] = (t["def_ext"] / t["w_def_ext"]) if t["w_def_ext"] else None
        out_teams[name] = rec
    buts_dom = s_dom / w_sum
    buts_ext = s_ext / w_sum
    return {
        "buts_dom_moy": buts_dom,
        "buts_ext_moy": buts_ext,
        "encaisses_dom_moy": buts_ext,
        "encaisses_ext_moy": buts_dom,
        "n": len(parsed),
        "half_life_days": half_life,
        "as_of": ref.strftime("%Y-%m-%d"),
        "teams": out_teams,
        "baseline": "saison",
    }


def csv_dirs(csv_dir=None):
    dirs = []
    if csv_dir:
        dirs.append(csv_dir)
    env = os.environ.get("PARI_UK_CACHE")
    if env and env not in dirs:
        dirs.append(env)
    default = os.path.join(WORLD, "ARCHIVUM", "cache", "f00")
    if default not in dirs:
        dirs.append(default)
    return dirs


def find_season_csv(code, csv_dir):
    if not code or not csv_dir or not os.path.isdir(csv_dir):
        return None
    code = str(code).upper()
    hits = []
    for name in os.listdir(csv_dir):
        if not name.lower().endswith(".csv"):
            continue
        stem = os.path.splitext(name)[0]
        parts = [p.upper() for p in stem.split("_")]
        if code in parts:
            hits.append(name)
    if not hits:
        return None
    hits.sort()
    return os.path.join(csv_dir, hits[-1])


def load_season_rows(code, csv_dir=None):
    if not code:
        return [], None
    all_rows = []
    used = []
    for d in csv_dirs(csv_dir):
        if not d or not os.path.isdir(d):
            continue
        code_u = str(code).upper()
        names = sorted(n for n in os.listdir(d) if n.lower().endswith(".csv"))
        matched = []
        for name in names:
            stem = os.path.splitext(name)[0]
            parts = [p.upper() for p in stem.split("_")]
            if code_u in parts:
                matched.append(name)
        if not matched:
            continue
        for name in matched:
            path = os.path.join(d, name)
            rows = backtest.load_csv(path)
            if rows:
                all_rows.extend(rows)
                used.append(name)
        if all_rows:
            break
    return all_rows, (used[-1] if used else None)


def league_baseline(code, csv_dir=None, as_of=None, half_life=None):
    rows, source = load_season_rows(code, csv_dir=csv_dir)
    if not rows:
        return None
    rec = compute_baseline(rows, as_of=as_of, half_life=half_life)
    if not rec:
        return None
    rec["league_code"] = str(code).upper()
    rec["source"] = source
    return rec


def main():
    parser = argparse.ArgumentParser(description="F02 BASELINE saison EMA")
    parser.add_argument("--csv", default=None)
    parser.add_argument("--csv-dir", default=None)
    parser.add_argument("--code", default=None)
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args()
    if args.csv:
        rows = backtest.load_csv(args.csv)
        rec = compute_baseline(rows, as_of=args.as_of)
        if rec:
            rec["source"] = os.path.basename(args.csv)
            rec["league_code"] = league_fit._code_of(rows, args.csv)
    else:
        rec = league_baseline(args.code, csv_dir=args.csv_dir, as_of=args.as_of)
    if not rec:
        print("[BASELINE] saison absente")
        return
    print(json.dumps({k: v for k, v in rec.items() if k != "teams"}, indent=2, ensure_ascii=False))
    print(f"[BASELINE] teams={len(rec.get('teams') or {})} n={rec.get('n')} "
          f"dom={rec.get('buts_dom_moy')} ext={rec.get('buts_ext_moy')}")


if __name__ == "__main__":
    main()
