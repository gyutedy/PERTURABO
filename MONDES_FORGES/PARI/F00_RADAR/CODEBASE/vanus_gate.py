#!/usr/bin/env python3
"""
VANUS GATE — greffe vanus.signal.v1 (stdlib, Zero Data). Pack V3.
=================================================================
Lecture seule. Un pick VANUS = observation, jamais une probabilite.
Timeout / skip / contrat faux / match absent = hole. Pas un p.
Alarme = flag info. Jackpot = veto selections opposees. Isole = pass.
Ne cable pas capteurs / qualitative / workflow. Tickets geles.

Usage :
  python vanus_gate.py --signal ARCHIVUM/vanus/latest.json --home Arsenal --away Chelsea --date 2026-11-09
"""

from __future__ import annotations

import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_SIGNAL = os.path.join(WORLD, "ARCHIVUM", "vanus", "latest.json")
CONTRACT = "vanus.signal.v1"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

PICK_TO_PARI = {
    "home": "1",
    "draw": "X",
    "away": "2",
    "over_2_5": "o2.5",
    "under_2_5": "u2.5",
    "btts_yes": "btts",
    "btts_no": "btts_no",
}
OPPOSE = {
    "home": "away",
    "away": "home",
    "over_2_5": "under_2_5",
    "under_2_5": "over_2_5",
    "btts_yes": "btts_no",
    "btts_no": "btts_yes",
}


def skipped():
    return os.environ.get("PARI_SKIP_VANUS") == "1"


def _norm(value):
    return _NON_ALNUM.sub("", str(value or "").lower())


def match_key(home, away, date=None):
    h, a = _norm(home), _norm(away)
    base = "_".join(sorted([x for x in (h, a) if x]))
    day = str(date or "")[:10]
    return "%s_%s" % (base, day) if day else base


def _uniq(seq):
    out = []
    seen = set()
    for x in seq or []:
        s = str(x)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _blank(holes=None, action="skip", flags=None):
    return {
        "ok": False,
        "action": action,
        "niveau": None,
        "selection": None,
        "n": 0,
        "found": 0,
        "flags": list(flags or []),
        "veto": [],
        "holes": list(holes or []),
        "match_key": None,
        "contract": None,
    }


def load(path=None):
    if skipped():
        return None, ["skip"]
    p = path or DEFAULT_SIGNAL
    if not p or not os.path.isfile(p):
        return None, ["vanus_absent"]
    try:
        with open(p, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return None, ["vanus_json"]
    if not isinstance(blob, dict):
        return None, ["vanus_json"]
    return blob, []


def validate(blob):
    if not isinstance(blob, dict):
        return ["contrat"]
    holes = []
    if blob.get("contract") != CONTRACT:
        holes.append("contrat")
    matches = blob.get("matches")
    if matches is None:
        holes.append("matches")
    elif not isinstance(matches, dict):
        holes.append("matches")
    return holes


def find_match(blob, home, away, date=None):
    if not isinstance(blob, dict):
        return None
    matches = blob.get("matches") or {}
    if not isinstance(matches, dict):
        return None
    key = match_key(home, away, date)
    rec = matches.get(key)
    if isinstance(rec, dict):
        return rec
    h, a, day = _norm(home), _norm(away), str(date or "")[:10]
    for rec in matches.values():
        if not isinstance(rec, dict):
            continue
        rh, ra = _norm(rec.get("home")), _norm(rec.get("away"))
        rd = str(rec.get("kickoff") or rec.get("date") or "")[:10]
        if {rh, ra} == {h, a} and (not day or not rd or rd == day):
            return rec
    return None


def _consensus(entry):
    if not isinstance(entry, dict):
        return {}
    c = entry.get("consensus")
    return c if isinstance(c, dict) else {}


def veto_codes(selection):
    opp = OPPOSE.get(selection)
    if not opp:
        return []
    code = PICK_TO_PARI.get(opp)
    return [code] if code else []


def gate(home, away, date=None, path=None, blob=None):
    if skipped():
        return _blank(["skip"])
    holes = []
    if blob is None:
        blob, load_holes = load(path)
        holes.extend(load_holes)
        if blob is None:
            rec = _blank(holes)
            rec["match_key"] = match_key(home, away, date)
            return rec
    holes.extend(validate(blob))
    if "contrat" in holes or "matches" in holes:
        rec = _blank(_uniq(holes))
        rec["contract"] = blob.get("contract") if isinstance(blob, dict) else None
        rec["match_key"] = match_key(home, away, date)
        return rec
    entry = find_match(blob, home, away, date)
    rec = {
        "ok": False,
        "action": "skip",
        "niveau": None,
        "selection": None,
        "n": 0,
        "found": 0,
        "flags": [],
        "veto": [],
        "holes": [],
        "match_key": match_key(home, away, date),
        "contract": blob.get("contract"),
    }
    if entry is None:
        rec["holes"] = _uniq(holes + ["vanus_match"])
        return rec
    cons = _consensus(entry)
    niveau = cons.get("niveau")
    sel = cons.get("selection")
    rec["niveau"] = niveau
    rec["selection"] = sel if sel else None
    rec["n"] = int(cons.get("n") or 0)
    rec["found"] = int(cons.get("found") or 0)
    rec["ok"] = True
    rec["holes"] = _uniq(holes + list(entry.get("holes") or []))
    if niveau == "jackpot":
        rec["action"] = "veto"
        rec["flags"] = ["vanus_jackpot"]
        rec["veto"] = veto_codes(sel)
    elif niveau == "alarme":
        rec["action"] = "info"
        rec["flags"] = ["vanus_alarme"]
    elif niveau in ("isole", "aucun"):
        rec["action"] = "pass"
    else:
        rec["action"] = "pass"
        rec["holes"] = _uniq(rec["holes"] + ["niveau"])
    return rec


def stamp_event(event, rec):
    if not isinstance(event, dict):
        return event
    out = dict(event)
    holes = _uniq(list(out.get("holes") or []) + list((rec or {}).get("holes") or []))
    flags = _uniq(list(out.get("vanus_flags") or []) + list((rec or {}).get("flags") or []))
    out["vanus_flags"] = flags
    out["vanus_action"] = (rec or {}).get("action")
    out["vanus_veto"] = list((rec or {}).get("veto") or [])
    if holes:
        out["holes"] = holes
    return out


def stamp_predictions(predictions, path=None, blob=None):
    if not isinstance(predictions, dict):
        return predictions
    out = dict(predictions)
    events = []
    for ev in out.get("matchs") or out.get("events") or []:
        if not isinstance(ev, dict):
            events.append(ev)
            continue
        home = ev.get("dom") or ev.get("home") or ""
        away = ev.get("ext") or ev.get("away") or ""
        date = ev.get("date")
        rec = gate(home, away, date=date, path=path, blob=blob)
        events.append(stamp_event(ev, rec))
    if "matchs" in out:
        out["matchs"] = events
    elif "events" in out:
        out["events"] = events
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", default=DEFAULT_SIGNAL)
    ap.add_argument("--home", required=True)
    ap.add_argument("--away", required=True)
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    rec = gate(args.home, args.away, date=args.date, path=args.signal)
    print(json.dumps(rec, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
