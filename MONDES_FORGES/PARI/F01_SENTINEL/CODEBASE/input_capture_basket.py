#!/usr/bin/env python3
"""
INPUT CAPTURE BASKET — tableau Winner Bet → JSON basket (stdlib, offline).
=========================================================================
Sport actif = basket : /capture recoit le tableau avec les colonnes
`1 (ML)` / `2 (ML)`. Seule la moneyline 2-way est utilisee : le moteur
basket ne produit pas de X, et les colonnes 1X2 / Handicap / Total sont
des paris differents, stockes comme diagnostics NON utilises.

Zero Data, Zero Calc : cote ML absente ou <= 1.0 = None + trou declare.
Fuseau : Africa/Kinshasa (UTC+1 toute l'annee). Date "Demain 01:30" resolute
au moment de la capture. Les matchs repetes par copier-coller sont ignorees.

Usage :
  python input_capture_basket.py --capture capture.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F02 = os.path.join(WORLD, "F02_BREACHER", "CODEBASE")
for path in (HERE, F02):
    if path not in sys.path:
        sys.path.insert(0, path)

from extract_input import extract_from_path  # noqa: E402
import engine_basket  # noqa: E402
import model_basket  # noqa: E402

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Africa/Kinshasa")
except Exception:
    from datetime import timezone, timedelta as _td
    TZ = timezone(_td(hours=1), "Africa/Kinshasa")

CONTRACT = "pari.capture_basket.v1"
DEFAULT_OUT = os.path.join(HERE, "..", "OUT", "capture_basket.json")


def odds_num(raw):
    txt = str(raw or "").strip().replace(",", ".")
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val > 1.0 else None


def parse_kickoff(cell, now=None):
    now = now or datetime.now(TZ)
    hid = None
    found = re.search(r"#(\d+)", cell or "")
    if found:
        hid = found.group(1)
    hm = re.search(r"(\d{1,2})[h:.](\d{2})", cell or "")
    hour = int(hm.group(1)) if hm else None
    minute = int(hm.group(2)) if hm else 0
    low = (cell or "").lower()
    day = now.date()
    holes = []
    if "demain" in low:
        day += timedelta(days=1)
    elif "hier" in low:
        day -= timedelta(days=1)
    elif "aujourd" in low:
        pass
    else:
        dm = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", cell or "")
        if dm:
            year = int(dm.group(3))
            year += 2000 if year < 100 else 0
            try:
                day = date(year, int(dm.group(2)), int(dm.group(1)))
            except ValueError:
                holes.append("date_invalide")
        else:
            holes.append("date_relative_inconnue")
    if hour is None or hour > 23 or minute > 59:
        holes.append("heure_absente")
        return None, hid, holes
    try:
        kick = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)
    except ValueError:
        holes.append("date_invalide")
        return None, hid, holes
    return kick.isoformat(), hid, holes


def analyse_match(match):
    pred = engine_basket.predict({"home": match["dom"], "away": match["ext"]})
    holes = list(pred.get("holes") or [])
    out = {
        "engine": "basket_mle",
        "mu_home": pred.get("mu_home"),
        "mu_away": pred.get("mu_away"),
        "sigma": pred.get("sigma"),
        "p_home": None,
        "p_away": None,
        "ev_home": None,
        "ev_away": None,
        "holes": holes,
    }
    if pred.get("mu_home") is None:
        return out
    sigma = pred.get("sigma") or 0.0
    if sigma <= 0:
        out["holes"].append("sigma_absent")
        return out
    p_home = model_basket.p_home_win(
        float(pred["mu_home"]), float(pred["mu_away"]), float(sigma))
    out["p_home"] = round(p_home, 4)
    out["p_away"] = round(1.0 - p_home, 4)
    mh, ma = match.get("ml_home"), match.get("ml_away")
    if mh is not None:
        out["ev_home"] = round(p_home * mh - 1.0, 4)
    if ma is not None:
        out["ev_away"] = round((1.0 - p_home) * ma - 1.0, 4)
    return out


def parse_markdown(text, now=None):
    warnings = []
    matchs = []
    seen = set()
    competition = ""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        while cells and not cells[-1]:
            cells.pop()
        if len(cells) < 4:
            continue
        low0 = cells[0].lower()
        if "match" in low0 and "horaire" in cells[1].lower():
            continue
        if all(set(c) <= set(":- ") for c in cells):
            continue
        head = cells[0].replace("**", "").replace("*", "")
        parts = [p.strip() for p in re.split(r"<br\s*/?>", head, flags=re.I)]
        if parts and "nba" in parts[0].lower():
            competition = parts[0]
        pair = parts[1] if len(parts) > 1 else parts[0]
        teams = re.split(r"\s+vs\.?\s+", pair, flags=re.I)
        if len(teams) != 2:
            warnings.append("paire_equipes_illisible:" + pair[:60])
            continue
        dom, ext = teams[0].strip(), teams[1].strip()
        if not dom or not ext:
            warnings.append("equipe_absente")
            continue
        kick, gid, kholes = parse_kickoff(cells[1], now)
        if not gid:
            gid = "S%-4d" % (len(matchs) + 1)
            warnings.append("game_id_absent:" + gid)
        if gid in seen:
            warnings.append("doublon_ignore:" + gid)
            continue
        seen.add(gid)
        ml_home = odds_num(cells[2])
        ml_away = odds_num(cells[3])
        holes = list(kholes)
        if ml_home is None:
            holes.append("ml_home_absente")
        if ml_away is None:
            holes.append("ml_away_absente")
        diag = {
            "1x2": {
                "home": odds_num(cells[4]) if len(cells) > 4 else None,
                "draw": odds_num(cells[5]) if len(cells) > 5 else None,
                "away": odds_num(cells[6]) if len(cells) > 6 else None,
                "utilise": False,
            },
            "handicap_total": {
                "prix_1": odds_num(cells[7]) if len(cells) > 7 else None,
                "prix_2": odds_num(cells[8]) if len(cells) > 8 else None,
                "ligne": None,
                "utilise": False,
            },
        }
        holes.append("handicap_total_sans_ligne")
        match = {
            "id": gid,
            "game_id": gid,
            "competition": competition,
            "date": kick,
            "dom": dom,
            "ext": ext,
            "ml_home": ml_home,
            "ml_away": ml_away,
            "diag": diag,
            "holes": holes,
        }
        match["analyse"] = analyse_match(match)
        matchs.append(match)
    if not matchs:
        warnings.append("AUCUN match de basket reconnu — Zero Data, Zero Calc")
    resume = []
    for m in matchs:
        a = m["analyse"]
        p_h = "%.3f" % a["p_home"] if a["p_home"] is not None else "—"
        ev_h = "%+.1f%%" % (100 * a["ev_home"]) if a["ev_home"] is not None else "—"
        ev_a = "%+.1f%%" % (100 * a["ev_away"]) if a["ev_away"] is not None else "—"
        resume.append("  %s  %s-%s  ML %s/%s  p1 %s  EV %s / %s" % (
            m["game_id"], m["dom"], m["ext"],
            m["ml_home"] if m["ml_home"] is not None else "—",
            m["ml_away"] if m["ml_away"] is not None else "—",
            p_h, ev_h, ev_a))
    return {
        "contract": CONTRACT,
        "captures": [{
            "competition": competition,
            "matchs": matchs,
            "warnings": warnings,
        }],
        "n_matchs": len(matchs),
        "resume": "\n".join(resume),
        "warnings": warnings,
        "holes": sorted({h for m in matchs for h in m["holes"]}),
        "source_format": "markdown_table_basket",
        "statut": "A_VALIDER",
    }


def main():
    ap = argparse.ArgumentParser(description="F01 — capture basket (ML uniquement)")
    ap.add_argument("--capture", required=True)
    ap.add_argument("--out-json", default=DEFAULT_OUT)
    args = ap.parse_args()
    extracted = extract_from_path(args.capture)
    text = extracted.get("text") or ""
    warnings = list(extracted.get("warnings") or [])
    if text.strip():
        parsed = parse_markdown(text)
        parsed["warnings"] = warnings + parsed["warnings"]
        parsed["source_format"] = (extracted.get("format") or "texte") + "+basket"
    else:
        parsed = {
            "contract": CONTRACT, "captures": [], "n_matchs": 0,
            "resume": "", "warnings": warnings + ["AUCUN texte extractible — Zero Data, Zero Calc"],
            "holes": ["texte_absent"], "source_format": extracted.get("format") or "texte",
            "statut": "A_VALIDER",
        }
    target = os.path.abspath(args.out_json)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(parsed, handle, indent=2, ensure_ascii=False)
    print("[BASKET-CAPTURE] %d match(s) — ML uniquement — %s" % (
        parsed["n_matchs"], parsed["source_format"]))
    print(parsed["resume"])
    for warning in parsed["warnings"]:
        print("  ⚠️ " + warning)
    print("[BASKET-CAPTURE] JSON non valide — relis-le avant d'utiliser. Moteur gelé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
