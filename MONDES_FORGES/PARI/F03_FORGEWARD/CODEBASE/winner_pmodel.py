#!/usr/bin/env python3
"""
WINNER P-MODELE — diagnostic EV sur les cotes Winner reelles.
=============================================================
Le p_modele n'est PAS lu dans les cotes : il est calcule par le moteur
Dixon-Coles deja entraine (F02/fit_dc) sur les CSV historiques, puis
compare aux cotes Winner deviguees (F03/devig).

Regles : aucune probabilite inventee, aucun ticket, aucun seuil abaisse.
Equipe ou ligue introuvable = trou + EV None. Les marches diagnostic_only
(HSH) ne sont jamais utilisees ici.
Sortie : ARCHIVUM/winner/pmodel_{sport}.json (observations, pas un ticket).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
for _p in (HERE, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"),
           os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import devig  # noqa: E402
import fit_dc  # noqa: E402
import model_dc  # noqa: E402
import winner_ingest  # noqa: E402

DEFAULT_PARAMS = os.path.join(WORLD, "ARCHIVUM", "learnings", "dc_params.json")
CONTRACT = "pari.winner_pmodel.v1"
EV_FLOOR = 0.03
SUFFIX = ("calcio", "balompie", "football club", "fussballclub", "deportivo",
          "club", "cf", "fc", "ac", "sd", "ca", "rc", "sc", "as", "ss", "cd", "ud", "ad")
ALIASES = {
    "atleticomadrid": "athmadrid",
    "acmilan": "milan",
}
BLOCK = ("fortuna", "b team", "ii", "u21", "feminin")


def norm_team(value):
    txt = unicodedata.normalize("NFKD", str(value or ""))
    txt = "".join(c for c in txt if not unicodedata.combining(c)).lower()
    words = re.sub(r"[^a-z0-9]+", " ", txt).split()
    while words and words[-1] in SUFFIX:
        words.pop()
    return "".join(words)


def resolve(team, blob):
    """Nom Winner -> nom football-data. Aucune approximation hasardeuse."""
    key = ALIASES.get(norm_team(team), norm_team(team))
    if not key or any(b in key for b in BLOCK):
        return None, None
    found = []
    for code, rec in (blob.get("leagues") or {}).items():
        for name in (rec.get("teams") or {}):
            if norm_team(name) == key:
                found.append((code, name))
    if len(found) == 1:
        return found[0]
    return None, None


def p_1x2(lh, la, rho):
    m = model_dc.score_matrix(lh, la, rho=rho)
    if not m:
        return None
    p1 = px = p2 = 0.0
    for i, row in enumerate(m):
        for j, q in enumerate(row):
            if i > j:
                p1 += q
            elif i == j:
                px += q
            else:
                p2 += q
    return {"1": p1, "X": px, "2": p2} if min(p1, px, p2) > 0 else None


def p_ou25(lh, la, rho, line=2.5):
    """P(over/under) depuis LA MEME matrice de scores (aucune nouvelle equation)."""
    m = model_dc.score_matrix(lh, la, rho=rho)
    if not m:
        return None
    over = sum(q for i, row in enumerate(m) for j, q in enumerate(row) if i + j > line)
    under = 1.0 - over
    if min(over, under) <= 0:
        return None
    return {"over": over, "under": under}


def analyse(match, blob):
    """Un match -> diagnostic p_modele/EV. Jamais de ticket."""
    holes = []
    cotes = match.get("odds") or {}
    need = ("home", "draw", "away")
    if any(cotes.get(k) is None or float(cotes[k]) <= 1 for k in need):
        return {"match_key": match.get("match_key"), "holes": ["cotes_1x2_absentes"],
                "p_modele": None, "ev": None, "ticket": False}
    lcode, lname = resolve(match.get("home"), blob)
    acode, aname = resolve(match.get("away"), blob)
    if not lname or not aname or lcode != acode:
        return {"match_key": match.get("match_key"),
                "holes": ["equipe_absente:" + str(match.get("home"))
                          if not lname else "equipe_absente:" + str(match.get("away"))]
                if not lname or not aname else ["ligue_differente"],
                "p_modele": None, "ev": None, "ticket": False}
    rec = fit_dc.params_for(lcode, blob=blob)
    if rec.get("params") != "fitted":
        return {"match_key": match.get("match_key"), "holes": ["params_absents:" + lcode],
                "p_modele": None, "ev": None, "ticket": False}
    lam = model_dc.lambdas_for(lname, aname, rec)
    if lam.get("lh") is None:
        return {"match_key": match.get("match_key"), "holes": lam.get("holes") or ["lambda_absent"],
                "p_modele": None, "ev": None, "ticket": False}
    rho = rec.get("rho") if rec.get("rho") is not None else model_dc.RHO_DC
    p = p_1x2(lam["lh"], lam["la"], rho)
    if p is None:
        return {"match_key": match.get("match_key"), "holes": ["p_nulle"],
                "p_modele": None, "ev": None, "ticket": False}
    fair = devig.multiplicative({k: cotes[k] for k in need})
    if not fair["ok"]:
        return {"match_key": match.get("match_key"), "holes": fair["holes"],
                "p_modele": p, "ev": None, "ticket": False}
    sel = {"home": "1", "draw": "X", "away": "2"}
    ev = {k: round(p[sel[k]] * float(cotes[k]) - 1.0, 6) for k in need}
    edge = {k: round(p[sel[k]] / fair["p_fair"][k] - 1.0, 6) for k in need}
    holes = []
    ou = {"p_modele": None, "p_fair": None, "cote": None, "ev": None,
          "edge_net": None, "holes": ["ou25_absente"]}
    ou_cotes = {k: cotes.get(k) for k in ("under_2_5", "over_2_5")}
    if all(v is not None and float(v) > 1 for v in ou_cotes.values()):
        p_ou = p_ou25(lam["lh"], lam["la"], rho)
        f_ou = devig.multiplicative(ou_cotes)
        if p_ou and f_ou["ok"]:
            mapping = {"under_2_5": "under", "over_2_5": "over"}
            ou = {
                "p_modele": {k: round(p_ou[mapping[k]], 6) for k in ou_cotes},
                "p_fair": {k: round(f_ou["p_fair"][k], 6) for k in ou_cotes},
                "cote": {k: float(ou_cotes[k]) for k in ou_cotes},
                "ev": {k: round(p_ou[mapping[k]] * float(ou_cotes[k]) - 1.0, 6)
                       for k in ou_cotes},
                "edge_net": {k: round(p_ou[mapping[k]] / f_ou["p_fair"][k] - 1.0, 6)
                             for k in ou_cotes},
                "holes": [],
            }
    return {
        "match_key": match.get("match_key"),
        "home": match.get("home"), "away": match.get("away"),
        "league": lcode,
        "p_modele": {k: round(p[sel[k]], 6) for k in need},
        "p_fair": {k: round(fair["p_fair"][k], 6) for k in need},
        "cote": {k: float(cotes[k]) for k in need},
        "ev": ev,
        "edge_net": edge,
        "ou25": ou,
        "holes": holes,
        "ticket": False,
    }


def run(sport="foot", params_path=None, out_path=None):
    blob = fit_dc.load_params(params_path or DEFAULT_PARAMS) or {}
    view = winner_ingest.ingest(sport)
    recs = [analyse(dict(m, match_key=key), blob) for key, m in view["matches"].items()]
    out = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sport": sport,
        "source": "F02 fit_dc (CSV historiques) + F03 devig + cotes Winner",
        "analyses": recs,
        "n_analyse": len(recs),
        "n_avec_p": sum(1 for r in recs if r.get("p_modele")),
        "tickets_enabled": False,
    }
    target = out_path or os.path.join(WORLD, "ARCHIVUM", "winner", "pmodel_%s.json" % sport)
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def main():
    ap = argparse.ArgumentParser(description="EV Winner via p_modele Dixon-Coles")
    ap.add_argument("--sport", choices=("foot", "basket"), default="foot")
    ap.add_argument("--params", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = run(args.sport, args.params, args.out)
    print(json.dumps({k: out[k] for k in ("contract", "sport", "n_analyse", "n_avec_p",
                                          "tickets_enabled")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
