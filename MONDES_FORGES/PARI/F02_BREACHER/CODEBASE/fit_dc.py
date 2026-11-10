#!/usr/bin/env python3
"""
FIT DC — MLE Dixon-Coles par ligue (stdlib, offline). Pack V2a.
==============================================================
Lit les lignes market_csv. Equipe / ligue sous-seuil = holes, jamais invente.
Elo absent = prior 0 + hole, jamais 1500. Sortie gitignore.
Ne cable pas breacher (V2b).

Usage:
  python fit_dc.py --dir ARCHIVUM/cache/f00 --out ARCHIVUM/learnings/dc_params.json
"""

from __future__ import annotations

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

import market_csv  # noqa: E402
import model_dc  # noqa: E402
import moteur_flag  # noqa: E402

_PARAMS_CACHE = None


def _cfg(cfg=None):
    base = {
        "half_life_days": 60.0,
        "min_team_matches": 5,
        "min_league_matches": 60,
        "sigma_att": 0.35,
        "sigma_def": 0.35,
        "sigma_rho": 0.25,
        "elo_scale": 0.0015,
        "elo_prior_weight": 0.5,
        "elo_prior_full_matches": 10,
        "max_iterations": 600,
        "tol": 1e-9,
    }
    src = cfg if isinstance(cfg, dict) else moteur_flag.fit_config()
    if isinstance(src, dict):
        for k, v in src.items():
            if k in base and v is not None:
                base[k] = v
    return base


def _parse_date(raw):
    if isinstance(raw, datetime):
        return raw
    txt = (raw or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def _row_fields(r):
    home = r.get("home") or r.get("HomeTeam")
    away = r.get("away") or r.get("AwayTeam")
    fthg = r.get("fthg") if "fthg" in r else r.get("FTHG")
    ftag = r.get("ftag") if "ftag" in r else r.get("FTAG")
    if not isinstance(fthg, int):
        fthg = market_csv._score(fthg)
    if not isinstance(ftag, int):
        ftag = market_csv._score(ftag)
    dt = _parse_date(r.get("date") or r.get("Date"))
    home = (home or "").strip()
    away = (away or "").strip()
    return home, away, fthg, ftag, dt


def prepare(rows, as_of=None, half_life=60.0):
    parsed = []
    for r in rows:
        home, away, i, j, dt = _row_fields(r)
        if not home or not away or i is None or j is None or dt is None:
            continue
        parsed.append((dt, home, away, int(i), int(j)))
    if not parsed:
        return []
    if as_of is None:
        ref = max(p[0] for p in parsed)
    else:
        ref = _parse_date(as_of) or max(p[0] for p in parsed)
    out = []
    for dt, home, away, i, j in parsed:
        age = (ref - dt).days
        w = model_dc.time_weight(age, half_life)
        if w is None or w <= 0:
            continue
        out.append({"date": dt.strftime("%Y-%m-%d"), "home": home, "away": away,
                    "i": i, "j": j, "w": w, "age_days": age})
    return out


def default_rec(code=None, n=0, holes=None):
    return {
        "league_code": code,
        "n": n,
        "params": "default",
        "mu": None,
        "home_adv": None,
        "rho": None,
        "teams": {},
        "holes": list(holes or ["non_fite"]),
        "ll": None,
        "n_iter": 0,
        "converged": False,
    }


def _ll(matches, teams, mu, home_adv, att, deff, rho, cfg, elo_map, n_matches):
    total = 0.0
    for m in matches:
        h, a = m["home"], m["away"]
        if h not in teams or a not in teams:
            continue
        lh, la = model_dc.lambdas(mu, home_adv, att[h], deff[h], att[a], deff[a])
        lp = model_dc.log_pmf(m["i"], m["j"], lh, la, rho)
        if lp == float("-inf"):
            return float("-inf")
        total += m["w"] * lp
    sa = float(cfg["sigma_att"])
    sd = float(cfg["sigma_def"])
    sr = float(cfg["sigma_rho"])
    for t in teams:
        elo = (elo_map or {}).get(t)
        mean_att = model_dc.elo_prior_mean(elo, n_matches.get(t), cfg)
        total += model_dc.log_prior_gauss(att[t], mean_att if mean_att is not None else 0.0, sa)
        total += model_dc.log_prior_gauss(deff[t], 0.0, sd)
    total += model_dc.log_prior_gauss(rho, model_dc.RHO_DC, sr)
    return total


def _center(mu, att, deff):
    names = list(att)
    if not names:
        return mu
    ma = sum(att[t] for t in names) / len(names)
    md = sum(deff[t] for t in names) / len(names)
    for t in names:
        att[t] -= ma
        deff[t] -= md
    return mu + ma - md


def _step(matches, teams, mu, home_adv, att, deff, rho, cfg, elo_map, n_matches):
    sa = float(cfg["sigma_att"]) ** 2
    sd = float(cfg["sigma_def"]) ** 2
    sr = float(cfg["sigma_rho"]) ** 2
    g_mu = g_h = g_rho = 0.0
    H_mu = H_h = 1e-12
    H_rho = 1e-12
    g_att = {t: 0.0 for t in teams}
    g_def = {t: 0.0 for t in teams}
    H_att = {t: 1e-12 for t in teams}
    H_def = {t: 1e-12 for t in teams}
    for m in matches:
        h, a = m["home"], m["away"]
        if h not in teams or a not in teams:
            continue
        lh, la = model_dc.lambdas(mu, home_adv, att[h], deff[h], att[a], deff[a])
        glh, gla, gr = model_dc.dlogp_dlh_dla_drho(m["i"], m["j"], lh, la, rho)
        w = m["w"]
        g_mu += w * (glh * lh + gla * la)
        g_h += w * (glh * lh)
        g_att[h] += w * (glh * lh)
        g_def[a] += w * (-glh * lh)
        g_att[a] += w * (gla * la)
        g_def[h] += w * (-gla * la)
        g_rho += w * gr
        H_mu += w * (lh + la)
        H_h += w * lh
        H_att[h] += w * lh
        H_def[a] += w * lh
        H_att[a] += w * la
        H_def[h] += w * la
        i, j = m["i"], m["j"]
        tau = model_dc.tau_dc(lh, la, rho, i, j)
        if tau > 0:
            dtau_r = 0.0
            if i == 0 and j == 0:
                dtau_r = -lh * la
            elif i == 0 and j == 1:
                dtau_r = lh
            elif i == 1 and j == 0:
                dtau_r = la
            elif i == 1 and j == 1:
                dtau_r = -1.0
            H_rho += w * (dtau_r * dtau_r) / (tau * tau)
    for t in teams:
        elo = (elo_map or {}).get(t)
        mean_att = model_dc.elo_prior_mean(elo, n_matches.get(t), cfg)
        m_att = 0.0 if mean_att is None else mean_att
        g_att[t] += -(att[t] - m_att) / sa
        H_att[t] += 1.0 / sa
        g_def[t] += -deff[t] / sd
        H_def[t] += 1.0 / sd
    g_rho += -(rho - model_dc.RHO_DC) / sr
    H_rho += 1.0 / sr
    d_mu = g_mu / H_mu
    d_h = g_h / H_h
    d_rho = g_rho / H_rho
    d_att = {t: g_att[t] / H_att[t] for t in teams}
    d_def = {t: g_def[t] / H_def[t] for t in teams}
    return d_mu, d_h, d_att, d_def, d_rho


def _init(matches, teams):
    n = sh = sa = 0.0
    for m in matches:
        if m["home"] not in teams or m["away"] not in teams:
            continue
        sh += m["i"]
        sa += m["j"]
        n += 1
    if n <= 0 or sh + sa <= 0:
        return math.log(1.3), 0.2, model_dc.RHO_DC
    mu = math.log((sh + sa) / (2.0 * n))
    ratio = (sh / n) / max(sa / n, 1e-6)
    home_adv = math.log(ratio) if ratio > 0 else 0.2
    return mu, home_adv, model_dc.RHO_DC


def fit_league(rows, code=None, elo_map=None, as_of=None, cfg=None):
    cfg = _cfg(cfg)
    matches_all = prepare(rows, as_of=as_of, half_life=float(cfg["half_life_days"]))
    n_all = len(matches_all)
    min_lg = int(cfg["min_league_matches"])
    min_tm = int(cfg["min_team_matches"])
    if n_all < min_lg:
        return default_rec(code, n_all, ["n<%d" % min_lg])
    counts = {}
    for m in matches_all:
        counts[m["home"]] = counts.get(m["home"], 0) + 1
        counts[m["away"]] = counts.get(m["away"], 0) + 1
    teams = {t: n for t, n in counts.items() if n >= min_tm}
    dropped = sorted(t for t, n in counts.items() if n < min_tm)
    matches = [m for m in matches_all
               if m["home"] in teams and m["away"] in teams]
    if len(matches) < min_lg or len(teams) < 2:
        holes = ["n<%d" % min_lg]
        if dropped:
            holes.append("equipe_absente")
        return default_rec(code, n_all, holes)
    att = {t: 0.0 for t in teams}
    deff = {t: 0.0 for t in teams}
    mu, home_adv, rho = _init(matches, teams)
    mu = _center(mu, att, deff)
    max_it = int(cfg["max_iterations"])
    tol = float(cfg["tol"])
    ll = _ll(matches, teams, mu, home_adv, att, deff, rho, cfg, elo_map, teams)
    converged = False
    n_iter = 0
    holes = []
    elo_holes = sorted(t for t in teams if not (elo_map or {}).get(t))
    if elo_holes:
        holes.append("elo")
    if dropped:
        holes.append("equipe_absente")
    for n_iter in range(1, max_it + 1):
        d_mu, d_h, d_att, d_def, d_rho = _step(
            matches, teams, mu, home_adv, att, deff, rho, cfg, elo_map, teams)
        step = 1.0
        ll_new = float("-inf")
        mu2 = h2 = rho2 = att2 = deff2 = None
        for _ in range(12):
            att2 = {t: att[t] + step * d_att[t] for t in teams}
            deff2 = {t: deff[t] + step * d_def[t] for t in teams}
            mu2 = _center(mu + step * d_mu, att2, deff2)
            h2 = home_adv + step * d_h
            rho2 = model_dc.clip_rho(rho + step * d_rho)
            ll_new = _ll(matches, teams, mu2, h2, att2, deff2, rho2, cfg, elo_map, teams)
            if ll_new > ll and ll_new != float("-inf"):
                break
            step *= 0.5
        else:
            break
        delta = max(abs(mu2 - mu), abs(h2 - home_adv), abs(rho2 - rho),
                    max(abs(att2[t] - att[t]) for t in teams),
                    max(abs(deff2[t] - deff[t]) for t in teams))
        mu, home_adv, att, deff, rho, ll = mu2, h2, att2, deff2, rho2, ll_new
        if delta < tol:
            converged = True
            break
    if not converged:
        holes.append("non_converged")
    team_blob = {}
    for t in sorted(teams):
        rec_t = {
            "att": round(att[t], 6),
            "def": round(deff[t], 6),
            "n": int(teams[t]),
            "elo": (elo_map or {}).get(t),
        }
        if rec_t["elo"] is None:
            rec_t["holes"] = ["elo"]
        team_blob[t] = rec_t
    return {
        "league_code": code,
        "n": len(matches),
        "n_raw": n_all,
        "params": "fitted",
        "mu": round(mu, 6),
        "home_adv": round(home_adv, 6),
        "rho": round(rho, 6),
        "teams": team_blob,
        "dropped": dropped,
        "holes": holes,
        "ll": round(ll, 4) if ll != float("-inf") else None,
        "n_iter": n_iter,
        "converged": converged,
    }


def fit_dir(csv_dir, elo_map=None, as_of=None, cfg=None):
    blob = market_csv.load_dir(csv_dir)
    if blob.get("holes"):
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "leagues": {},
            "holes": list(blob["holes"]),
        }
    by = market_csv.by_div(blob["rows"])
    leagues = {}
    holes = []
    for code, rows in sorted(by.items()):
        rec = fit_league(rows, code=code, elo_map=elo_map, as_of=as_of, cfg=cfg)
        leagues[code] = rec
        if rec.get("params") != "fitted":
            holes.append(code)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": "dc_mle",
        "engine_version": "pari.model_dc.v1",
        "leagues": leagues,
        "holes": holes,
        "files": blob.get("files") or [],
        "n_lignes": len(blob.get("rows") or []),
    }


def save_params(blob, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load_params(path):
    global _PARAMS_CACHE
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    _PARAMS_CACHE = blob
    return blob


def params_for(code, path=None, blob=None):
    if blob is None:
        blob = load_params(path) if path else _PARAMS_CACHE
    if not blob or not isinstance(blob, dict):
        return default_rec(code, 0, ["params_absents"])
    rec = (blob.get("leagues") or {}).get(code)
    if not rec:
        return default_rec(code, 0, ["ligue_absente"])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(WORLD, "ARCHIVUM", "cache", "f00"))
    ap.add_argument("--out", default=os.path.join(WORLD, "ARCHIVUM", "learnings", "dc_params.json"))
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()
    blob = fit_dir(args.dir, as_of=args.as_of)
    save_params(blob, args.out)
    rec = {
        "out": os.path.abspath(args.out),
        "n_lignes": blob.get("n_lignes"),
        "leagues": {k: {"n": v.get("n"), "params": v.get("params"),
                        "holes": v.get("holes")}
                    for k, v in (blob.get("leagues") or {}).items()},
        "holes": blob.get("holes"),
    }
    print(json.dumps(rec, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
