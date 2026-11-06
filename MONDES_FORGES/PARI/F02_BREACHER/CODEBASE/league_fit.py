"""
F02 LEAGUE FIT — rho Dixon-Coles, bonus domicile, part_mt1 (stdlib, offline).
==============================================================================
Lit les CSV football-data caches. Ligue absente / n<4 → defauts + flag.
Zero reseau. Equations Poisson inchangees (le fit ne fait que des parametres).

Usage:
  python league_fit.py --csv tests/fixtures/uk_SP1_2526.csv
  python league_fit.py --csv-dir ARCHIVUM/cache/f00 --out ARCHIVUM/learnings/league_params.json
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F00 = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
if F00 not in sys.path:
    sys.path.insert(0, F00)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import backtest  # noqa: E402

_CONFIG_CACHE = None
_PARAMS_CACHE = None


def _cfg_path():
    return os.path.join(WORLD, "config", "league_fit.json")


def load_config(path=None):
    global _CONFIG_CACHE
    if path is None and _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    p = path or _cfg_path()
    defaults = {
        "half_life_days": 45,
        "min_matches": 4,
        "rho_grid": {"lo": -0.25, "hi": 0.05, "step": 0.01},
        "clip": {
            "bonus_domicile": [1.0, 1.25],
            "bonus_exterieur": [0.75, 1.05],
            "rho": [-0.3, 0.05],
        },
        "defaults": {
            "rho": -0.13,
            "bonus_domicile": 1.10,
            "bonus_exterieur": 0.95,
            "part_mt1": 0.44,
        },
    }
    if p and os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
            if isinstance(blob, dict):
                for k, v in blob.items():
                    if k == "defaults" and isinstance(v, dict):
                        defaults["defaults"].update(v)
                    elif k == "clip" and isinstance(v, dict):
                        defaults["clip"].update(v)
                    elif k == "rho_grid" and isinstance(v, dict):
                        defaults["rho_grid"].update(v)
                    elif k not in ("note",):
                        defaults[k] = v
        except (OSError, json.JSONDecodeError):
            pass
    if path is None:
        _CONFIG_CACHE = defaults
    return defaults


def default_params():
    d = dict(load_config()["defaults"])
    d["params"] = "default"
    d["n"] = 0
    return d


def _clip(val, bounds):
    lo, hi = bounds[0], bounds[1]
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val


def _grid(lo, hi, step):
    if step <= 0:
        return [lo]
    n = int(round((hi - lo) / step)) + 1
    return [round(lo + i * step, 4) for i in range(n)]


def fit_rho(rows, lh, la, cfg=None):
    import breacher
    cfg = cfg or load_config()
    grid = cfg.get("rho_grid") or {}
    lo = float(grid.get("lo", -0.25))
    hi = float(grid.get("hi", 0.05))
    step = float(grid.get("step", 0.01))
    scores = []
    for r in rows:
        i, j = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if i is None or j is None:
            continue
        i, j = int(i), int(j)
        if i > breacher.MAX_GOALS or j > breacher.MAX_GOALS:
            continue
        scores.append((i, j))
    min_n = int(cfg.get("min_matches") or 4)
    if len(scores) < min_n:
        return None
    best_rho, best_ll = None, float("-inf")
    for rho in _grid(lo, hi, step):
        m = breacher.score_matrix(lh, la, rho=rho)
        ll = 0.0
        ok = True
        for i, j in scores:
            p = m[i][j]
            if p <= 0:
                ok = False
                break
            ll += math.log(p)
        if not ok:
            continue
        if ll > best_ll:
            best_ll, best_rho = ll, rho
    return best_rho


def fit_bonus(rows, cfg=None):
    cfg = cfg or load_config()
    n, sh, sa = 0, 0.0, 0.0
    for r in rows:
        h, a = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if h is None or a is None:
            continue
        sh += h
        sa += a
        n += 1
    dflt = cfg["defaults"]
    if n == 0 or (sh + sa) <= 0:
        return dflt["bonus_domicile"], dflt["bonus_exterieur"], n
    mh, ma = sh / n, sa / n
    bonus_d = 1.0 + (mh - ma) / (mh + ma)
    bonus_d = _clip(bonus_d, cfg["clip"]["bonus_domicile"])
    bonus_e = _clip(2.0 - bonus_d, cfg["clip"]["bonus_exterieur"])
    return bonus_d, bonus_e, n


def _code_of(rows, path=None):
    if rows:
        div = (rows[0].get("Div") or "").strip().upper()
        if div:
            return div
    if path:
        base = os.path.basename(path)
        parts = os.path.splitext(base)[0].split("_")
        if len(parts) >= 2:
            return parts[1].upper()
    return None


def fit_league(rows, code=None, source=None, cfg=None):
    cfg = cfg or load_config()
    dflt = default_params()
    code = (code or _code_of(rows) or "").upper() or None
    bonus_d, bonus_e, n = fit_bonus(rows, cfg)
    min_n = int(cfg.get("min_matches") or 4)
    rec = {
        "league_code": code,
        "n": n,
        "source": source,
        "params": "default",
        "rho": dflt["rho"],
        "bonus_domicile": dflt["bonus_domicile"],
        "bonus_exterieur": dflt["bonus_exterieur"],
        "part_mt1": dflt["part_mt1"],
    }
    if n < min_n:
        rec["holes"] = ["n<4"]
        return rec
    sh = sum(backtest._num(r, "FTHG") or 0.0 for r in rows
             if backtest._num(r, "FTHG") is not None and backtest._num(r, "FTAG") is not None)
    sa = sum(backtest._num(r, "FTAG") or 0.0 for r in rows
             if backtest._num(r, "FTHG") is not None and backtest._num(r, "FTAG") is not None)
    lh = sh / n if n else 1.0
    la = sa / n if n else 1.0
    rho = fit_rho(rows, lh, la, cfg)
    if rho is None:
        rho = dflt["rho"]
    else:
        rho = _clip(rho, cfg["clip"]["rho"])
    part, n_mt = backtest.part_mt1(rows)
    rec.update({
        "params": "fitted",
        "rho": rho,
        "bonus_domicile": bonus_d,
        "bonus_exterieur": bonus_e,
        "part_mt1": round(part, 4) if part is not None else dflt["part_mt1"],
        "n_mt": n_mt,
        "lambda_dom_moy": round(lh, 4),
        "lambda_ext_moy": round(la, 4),
    })
    return rec


def fit_file(path, cfg=None):
    rows = backtest.load_csv(path)
    if not rows:
        return None
    return fit_league(rows, source=os.path.basename(path), cfg=cfg)


def wrap_blob(leagues, cfg=None):
    cfg = cfg or load_config()
    blob = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offline": True,
        "defaults": dict(cfg["defaults"]),
        "leagues": leagues,
    }
    for code, rec in leagues.items():
        blob[code] = rec
    return blob


def fit_dir(csv_dir, cfg=None):
    cfg = cfg or load_config()
    leagues = {}
    if not csv_dir or not os.path.isdir(csv_dir):
        return wrap_blob(leagues, cfg)
    buckets = {}
    files = {}
    for name in sorted(os.listdir(csv_dir)):
        if not name.lower().endswith(".csv"):
            continue
        path = os.path.join(csv_dir, name)
        rows = backtest.load_csv(path)
        if not rows:
            continue
        code = _code_of(rows, path)
        if not code:
            continue
        buckets.setdefault(code, []).extend(rows)
        files.setdefault(code, []).append(name)
    for code, rows in buckets.items():
        rec = fit_league(rows, code=code, source=files[code][-1], cfg=cfg)
        rec["sources"] = files[code]
        rec["n_files"] = len(files[code])
        leagues[code] = rec
    return wrap_blob(leagues, cfg)


def params_path_default():
    env = os.environ.get("PARI_LEAGUE_PARAMS_PATH")
    if env:
        return env
    return os.path.join(WORLD, "ARCHIVUM", "learnings", "league_params.json")


def load_params(path=None):
    global _PARAMS_CACHE
    p = path or params_path_default()
    if path is None and _PARAMS_CACHE is not None:
        return _PARAMS_CACHE
    blob = {}
    if p and os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                blob = raw
        except (OSError, json.JSONDecodeError):
            blob = {}
    if path is None:
        _PARAMS_CACHE = blob
    return blob


def params_for(code, path=None):
    if not code:
        rec = dict(default_params())
        rec["params"] = "default"
        return rec
    blob = load_params(path)
    leagues = blob.get("leagues") if isinstance(blob.get("leagues"), dict) else blob
    rec = None
    if isinstance(leagues, dict):
        rec = leagues.get(code) or leagues.get(str(code).upper())
    if not isinstance(rec, dict) or rec.get("params") != "fitted":
        out = dict(default_params())
        out["league_code"] = str(code).upper()
        out["params"] = "default"
        return out
    out = dict(default_params())
    out.update({k: rec[k] for k in rec if k in (
        "rho", "bonus_domicile", "bonus_exterieur", "part_mt1",
        "n", "league_code", "source", "params")})
    out["params"] = "fitted"
    out["league_code"] = str(code).upper()
    return out


def save_params(blob, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
    return path


def main():
    parser = argparse.ArgumentParser(description="F02 LEAGUE FIT — rho / bonus / part_mt1")
    parser.add_argument("--csv", default=None)
    parser.add_argument("--csv-dir", default=os.environ.get("PARI_UK_CACHE") or os.path.join(
        WORLD, "ARCHIVUM", "cache", "f00"))
    parser.add_argument("--out", default=params_path_default())
    args = parser.parse_args()
    if args.csv:
        rec = fit_file(args.csv)
        leagues = {}
        if rec and rec.get("league_code"):
            leagues[rec["league_code"]] = rec
        blob = wrap_blob(leagues)
    else:
        blob = fit_dir(args.csv_dir)
    save_params(blob, args.out)
    print(f"[LEAGUE_FIT] {len(blob.get('leagues') or {})} ligue(s) → {args.out}")
    for code, rec in (blob.get("leagues") or {}).items():
        print(f"  {code} rho={rec.get('rho')} bonus={rec.get('bonus_domicile')} "
              f"part={rec.get('part_mt1')} n={rec.get('n')} params={rec.get('params')}")


if __name__ == "__main__":
    main()
