#!/usr/bin/env python3
"""
WINNER P-MODELE BASKET — EV ML depuis le moteur MLE NBA.
========================================================
Le p_modele n'est PAS lu dans les cotes Winner : il vient des parametres
MLE NBA (basket_params.json, 2455 matchs) via engine_basket.predict puis
model_basket.p_home_win. Comparaison aux cotes 2 Way deviguees (F03/devig).

Le marche Total reste DIAGNOSTIC : sigma_total n'est pas calibre sur la
ligne (cahier V3 P1), jamais une cote calculee hazardeuse. HSH n'existe pas.
Aucune mise, aucun ticket, aucun seuil abaisse.
Sortie : ARCHIVUM/winner/pmodel_basket.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
for _p in (HERE, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"),
           os.path.join(WORLD, "F00_RADAR", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import devig  # noqa: E402
import engine_basket  # noqa: E402
import model_basket  # noqa: E402
import winner_ingest  # noqa: E402
from winner_pmodel import EV_FLOOR  # noqa: E402

CONTRACT = "pari.winner_pmodel_basket.v1"


def analyse(match, blob=None):
    holes = []
    cotes = match.get("odds") or {}
    if (cotes.get("ml_1") is None or cotes.get("ml_2") is None
            or float(cotes["ml_1"]) <= 1 or float(cotes["ml_2"]) <= 1):
        return {"match_key": match.get("match_key"), "holes": ["ml_absente"],
                "p_modele": None, "ev": None, "ticket": False}
    pred = engine_basket.predict(match, blob=blob)
    if pred.get("mu_home") is None:
        return {"match_key": match.get("match_key"),
                "holes": pred.get("holes") or ["equipe_inconnue"],
                "p_modele": None, "ev": None, "ticket": False}
    p_home = model_basket.p_home_win(pred["mu_home"], pred["mu_away"], pred["sigma"])
    if not p_home or not (0 < p_home < 1):
        return {"match_key": match.get("match_key"), "holes": ["p_nulle"],
                "p_modele": None, "ev": None, "ticket": False}
    group = {"home": cotes["ml_1"], "away": cotes["ml_2"]}
    fair = devig.multiplicative(group)
    if not fair["ok"]:
        return {"match_key": match.get("match_key"), "holes": fair["holes"],
                "p_modele": p_home, "ev": None, "ticket": False}
    p = {"home": p_home, "away": 1.0 - p_home}
    ev = {k: round(p[k] * float(group[k]) - 1.0, 6) for k in group}
    edge = {k: round(p[k] / fair["p_fair"][k] - 1.0, 6) for k in group}
    return {
        "match_key": match.get("match_key"),
        "home": match.get("home"), "away": match.get("away"),
        "engine": pred.get("engine"),
        "mu_home": pred.get("mu_home"), "mu_away": pred.get("mu_away"),
        "sigma": pred.get("sigma"),
        "p_modele": {k: round(p[k], 6) for k in group},
        "p_fair": {k: round(fair["p_fair"][k], 6) for k in group},
        "cote": {k: float(group[k]) for k in group},
        "ev": ev,
        "edge_net": edge,
        "total": {"p_over": None, "ev": None,
                  "holes": ["sigma_total_non_calibre"], "diagnostic_only": True},
        "holes": [],
        "ticket": False,
    }


def run(params_path=None, out_path=None):
    blob = engine_basket.load(params_path)
    view = winner_ingest.ingest("basket")
    recs = [analyse(dict(m, match_key=k), blob) for k, m in view["matches"].items()]
    ph = [r.get("p_modele", {}).get("home") for r in recs if r.get("p_modele")]
    fh = [r.get("p_fair", {}).get("home") for r in recs if r.get("p_fair")]
    dispersion = (max(ph) - min(ph)) if len(ph) >= 2 else 0.0
    marche = (max(fh) - min(fh)) if len(fh) >= 2 else 0.0
    ratio = (dispersion / marche) if marche > 0 else 0.0
    max_ev = max([abs(v) for r in recs for v in (r.get("ev") or {}).values()] or [0])
    fiable = dispersion >= 0.05 and ratio >= 0.5 and max_ev <= 0.5
    if not fiable:
        for r in recs:
            if r.get("p_modele"):
                r.setdefault("holes", []).append("discrimination_faible")
                r["fiable"] = False
    else:
        for r in recs:
            r["fiable"] = True
    out = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sport": "basket",
        "source": "F02 basket MLE (2455 matchs NBA) + F03 devig + cotes Winner",
        "analyses": recs,
        "n_analyse": len(recs),
        "n_avec_p": sum(1 for r in recs if r.get("p_modele") is not None),
        "n_ev_positif": sum(1 for r in recs if any((v or 0) >= EV_FLOOR for v in (r.get("ev") or {}).values())),
        "dispersion_p_home": round(dispersion, 6),
        "dispersion_marche": round(marche, 6),
        "ratio_dispersion": round(ratio, 4),
        "max_ev_abs": round(max_ev, 6),
        "fiable": fiable,
        "tickets_enabled": False,
    }
    target = out_path or os.path.join(WORLD, "ARCHIVUM", "winner", "pmodel_basket.json")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def main():
    ap = argparse.ArgumentParser(description="EV ML Winner via p_modele basket MLE")
    ap.add_argument("--params", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = run(args.params, args.out)
    print(json.dumps({k: out[k] for k in ("contract", "sport", "n_analyse", "n_avec_p",
                                          "n_ev_positif", "dispersion_p_home",
                                          "dispersion_marche", "ratio_dispersion",
                                          "max_ev_abs", "fiable", "tickets_enabled")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
