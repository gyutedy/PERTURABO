#!/usr/bin/env python3
"""
FIT BASKET — ratings par maximum de vraisemblance approche (stdlib).
==================================================================
Modele : marge observee ~ N((rtg_h - rtg_a) + home_adv, sigma) et
points d'une equipe ~ N(base + off + def_adv, sigma_pts).
Estimation : descente de gradient ridge, poids temporels exponentiels.
Meme discipline que fit_dc.py (foot) :
  - un seul pass de fitting ecrit ARCHIVUM/state/basket_params.json ;
  - centre : moyenne des rtg = 0 a 1e-6 pres (verifie en sortie) ;
  - aucun parametre invente : equipe sans >= min_team_matches matchs
    recoit rtg=0.0 + hole "equipe_pauvre", jamais une estimation cachee.
"""
from __future__ import annotations
import json
import math
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(WORLD, "ARCHIVUM", "state", "basket_params.json")


def _cfg(cfg=None):
    base = {
        "half_life_days": 45.0,
        "min_team_matches": 5,
        "sigma_rtg": 4.0,
        "sigma_pts": 2.5,
        "home_adv_init": 2.5,
        "lr": 0.02,
        "max_iterations": 400,
        "tol": 1e-9,
    }
    base.update(cfg or {})
    return base


def _days_since(date_str, as_of=None):
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        now = as_of or datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0.0, (now - d).total_seconds() / 86400.0)
    except ValueError:
        return 0.0


def prepare(rows, cfg=None, as_of=None):
    """rows market_basket -> observations ponderees.
    obs = {home, away, margin, total_h, total_a, weight} """
    c = _cfg(cfg)
    obs = []
    for r in rows:
        if r.get("pts_home") is None or r.get("pts_away") is None:
            continue
        age = _days_since(r.get("date") or "", as_of)
        obs.append({
            "home": r["home"], "away": r["away"],
            "margin": float(r["pts_home"] - r["pts_away"]),
            "total_h": float(r["pts_home"]), "total_a": float(r["pts_away"]),
            "weight": model_w(age, c["half_life_days"]),
        })
    return obs


def model_w(age_days, half_life):
    if half_life <= 0:
        return 1.0
    return 0.5 ** (float(age_days) / float(half_life))


def _team_names(obs):
    names = set()
    for o in obs:
        names.add(o["home"])
        names.add(o["away"])
    return sorted(names)


def fit(obs, cfg=None):
    """MLE approche (ridge + gradient). Renvoie le blob de params.
    Verdict de centre exige : |somme(rtg)| <= 1e-6 apres recentrage."""
    c = _cfg(cfg)
    names = _team_names(obs)
    if not names:
        return {"teams": {}, "home_adv": c["home_adv_init"], "base": None,
                "sigma": None, "holes": ["aucun_match"], "n_matches": 0}
    rtg = {t: 0.0 for t in names}
    off = {t: 0.0 for t in names}
    n_m = {t: 0 for t in names}
    tot_h = tot_a = 0.0
    for o in obs:
        n_m[o["home"]] += 1
        n_m[o["away"]] += 1
        tot_h += o["total_h"]
        tot_a += o["total_a"]
    base = (tot_h + tot_a) / (2.0 * max(1, len(obs)))
    home_adv = float(c["home_adv_init"])
    lr = float(c["lr"])
    s2 = c["sigma_rtg"] ** 2
    sig2 = c["sigma_pts"] ** 2
    prev = None
    for it in range(int(c["max_iterations"])):
        g = {t: 0.0 for t in names}
        go = {t: 0.0 for t in names}
        gh = 0.0
        for o in obs:
            w = o["weight"]
            # marge
            pred = (rtg[o["home"]] - rtg[o["away"]]) + home_adv
            err = o["margin"] - pred
            g[o["home"]] += w * err
            g[o["away"]] -= w * err
            gh += w * err
            # points (off = ecart a base ; def adverse agit positivement sur l'adv.)
            eh = o["total_h"] - (base + off[o["home"]] - off[o["away"]])
            ea = o["total_a"] - (base + off[o["away"]] - off[o["home"]])
            go[o["home"]] += w * eh
            go[o["away"]] += w * ea
        n = float(len(obs))
        for t in names:
            rtg[t] += lr * (g[t] / n - rtg[t] / s2)
            off[t] += lr * (go[t] / n - off[t] / sig2)
        home_adv += lr * (gh / n - home_adv / (4.0 * s2))
        # recentrage (identifiabilite)
        m = sum(rtg.values()) / len(names)
        for t in names:
            rtg[t] -= m
        cur = abs(sum(rtg.values())) + abs(home_adv)
        if prev is not None and abs(cur - prev) < c["tol"]:
            break
        prev = cur
    # sigma residuel de la marge
    se = 0.0
    for o in obs:
        pred = (rtg[o["home"]] - rtg[o["away"]]) + home_adv
        se += o["weight"] * (o["margin"] - pred) ** 2
    wsum = sum(o["weight"] for o in obs)
    sigma = math.sqrt(max(se / max(wsum, 1e-9), 1.0))
    teams = {}
    holes = []
    for t in names:
        if n_m[t] < int(c["min_team_matches"]):
            teams[t] = {"rtg": 0.0, "off": 0.0, "n": n_m[t]}
            holes.append("equipe_pauvre:" + t)
        else:
            teams[t] = {"rtg": round(rtg[t], 4), "off": round(off[t], 4),
                        "n": n_m[t]}
    blob = {
        "contract": "pari.basket_params.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": round(base, 4),
        "home_adv": round(home_adv, 4),
        "sigma": round(sigma, 4),
        "teams": teams,
        "n_matches": len(obs),
        "holes": holes,
        "center_residual": round(abs(sum(rtg.values())), 9),
    }
    return blob


def load_params(path=None):
    """Blob stocke ou None. Jamais reconstruit a la volee."""
    target = path or DEFAULT_OUT
    try:
        with open(target, encoding="utf-8") as f:
            blob = json.load(f)
        if blob.get("contract") != "pari.basket_params.v1":
            return None
        return blob
    except (OSError, json.JSONDecodeError):
        return None


def save_params(blob, path=None):
    target = path or DEFAULT_OUT
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    return target


def main():
    import market_basket
    rows, holes = market_basket.load_dir()
    obs = prepare(rows)
    blob = fit(obs)
    out = save_params(blob)
    print("params ->", out)
    print("matchs:", blob["n_matches"], "| sigma:", blob["sigma"],
          "| centre residu:", blob["center_residual"], "| holes:", len(blob["holes"]))


if __name__ == "__main__":
    main()
