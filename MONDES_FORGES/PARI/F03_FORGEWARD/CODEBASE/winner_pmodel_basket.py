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
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
for _p in (HERE, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"),
           os.path.join(WORLD, "F00_RADAR", "CODEBASE")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import basket_calib  # noqa: E402
import basket_total  # noqa: E402
import devig  # noqa: E402
import engine_basket  # noqa: E402
import market_basket  # noqa: E402
import model_basket  # noqa: E402
import winner_ingest  # noqa: E402
from winner_pmodel import EV_FLOOR  # noqa: E402

CONTRACT = "pari.winner_pmodel_basket.v1"


def total_rec(match, blob, st, day, inherited_holes=None):
    base = {"p_over": None, "p_under": None, "cote": None, "ev": None,
            "sigma_total": (blob or {}).get("sigma_total"),
            "holes": list(inherited_holes or []), "diagnostic_only": True}
    odds = match.get("odds") or {}
    if not blob or not st:
        base["holes"].append("total_absent")
        return base
    line = odds.get("total_line")
    uo, oo = odds.get("total_under"), odds.get("total_over")
    if line is None or not uo or not oo or float(uo) <= 1 or float(oo) <= 1:
        base["holes"].append("cotes_total_absentes")
        return base
    p_over = basket_total.p_over(blob, match.get("home"), match.get("away"), day, st, line)
    if p_over is None:
        base["holes"].append("total_non_calcule")
        return base
    fair = devig.multiplicative({"under": uo, "over": oo})
    if not fair["ok"]:
        base["holes"].extend(fair["holes"])
        return base
    p = {"under": 1.0 - p_over, "over": p_over}
    cotes = {"under": float(uo), "over": float(oo)}
    base.update({
        "p_over": round(p_over, 6), "p_under": round(1.0 - p_over, 6),
        "ligne": line,
        "p_fair": {k: round(fair["p_fair"][k], 6) for k in fair["p_fair"]},
        "cote": cotes,
        "ev": {k: round(p[k] * cotes[k] - 1.0, 6) for k in cotes},
        "holes": list(dict.fromkeys(base["holes"])),
    })
    return base


def analyse(match, blob=None, calib=None, rows=None, ratings=None,
            total_blob=None, st_total=None, day=None):
    holes = []
    cotes = match.get("odds") or {}
    if (cotes.get("ml_1") is None or cotes.get("ml_2") is None
            or float(cotes["ml_1"]) <= 1 or float(cotes["ml_2"]) <= 1):
        return {"match_key": match.get("match_key"), "holes": ["ml_absente"],
                "p_modele": None, "ev": None, "ticket": False}
    modele = "mle"
    pred = engine_basket.predict(match, blob=blob)
    if pred.get("mu_home") is None:
        return {"match_key": match.get("match_key"),
                "holes": pred.get("holes") or ["equipe_inconnue"],
                "p_modele": None, "ev": None, "ticket": False}
    p_home = model_basket.p_home_win(pred["mu_home"], pred["mu_away"], pred["sigma"])
    if calib and rows is not None:
        raw_day = (match.get("kickoff") or "")[:10]
        day = raw_day if re.match(r"^\d{4}-\d{2}-\d{2}", raw_day) else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        last, diffs = basket_calib.state_at(rows, day)
        m, ch = basket_calib.predict_margin(calib, match.get("home"), match.get("away"),
                                            day, last, diffs, ratings)
        if m is not None:
            p_home = model_basket.p_home_win(m, -m, calib.get("sigma"))
            modele = "calib"
            for c in ch:
                holes.append(c)
            if match.get("home") not in last or match.get("away") not in last:
                holes.append("forme_absente")
            elif (basket_calib._dt(day) - basket_calib._dt(last[match["home"]])).days > 60:
                holes.append("donnees_anciennes")
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
        "modele": modele,
        "mu_home": pred.get("mu_home"), "mu_away": pred.get("mu_away"),
        "sigma": pred.get("sigma"),
        "p_modele": {k: round(p[k], 6) for k in group},
        "p_fair": {k: round(fair["p_fair"][k], 6) for k in group},
        "cote": {k: float(group[k]) for k in group},
        "ev": ev,
        "edge_net": edge,
        "total": total_rec(match, total_blob, st_total, day, holes),
        "holes": list(dict.fromkeys(holes)),
        "ticket": False,
    }


def run(params_path=None, out_path=None):
    blob = engine_basket.load(params_path)
    calib = basket_calib.load()
    rows, _ = market_basket.load_dir()
    ratings = blob.get("teams") or {}
    total_blob = basket_total.load()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    st_total = basket_total.state_at(rows, today)
    view = winner_ingest.ingest("basket")
    recs = [analyse(dict(m, match_key=k), blob, calib=calib, rows=rows, ratings=ratings,
                    total_blob=total_blob, st_total=st_total, day=today)
            for k, m in view["matches"].items()]
    ph = [r.get("p_modele", {}).get("home") for r in recs if r.get("p_modele")]
    fh = [r.get("p_fair", {}).get("home") for r in recs if r.get("p_fair")]
    dispersion = (max(ph) - min(ph)) if len(ph) >= 2 else 0.0
    marche = (max(fh) - min(fh)) if len(fh) >= 2 else 0.0
    ratio = (dispersion / marche) if marche > 0 else 0.0
    max_ev = max([abs(v) for r in recs for v in (r.get("ev") or {}).values()] or [0])
    verdict_calib = (calib or {}).get("verdict", "INCONNU")
    fiable = (verdict_calib == "GO" and dispersion >= 0.05
              and ratio >= 0.5 and max_ev <= 0.5)
    if not fiable:
        for r in recs:
            if r.get("p_modele"):
                if ratio < 0.5:
                    r.setdefault("holes", []).append("discrimination_faible")
                r.setdefault("holes", []).append("modele_non_valide:" + str(verdict_calib))
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
        "verdict_calibration": verdict_calib,
        "brier_gap_calibration": (calib or {}).get("brier_gap"),
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
