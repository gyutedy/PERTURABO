#!/usr/bin/env python3
"""
WINNER WATCH — etat des campagnes de capture Winner (same-book).
===============================================================
Un seul bookmaker (Winner) de la premiere capture jusqu'a T-0 :
le projet ne contacte pas Winner, il enregistre les captures fournies
par l'operateur, devine le match, rappelle toutes les 2h et calcule
le CLV en comparant la premiere cote a la derniere avant coup d'envoi.
Yahoo / The Odds API ne sont PAS utilises ici (aucun proxy cross-book).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
WATCH_DIR = os.path.join(WORLD, "ARCHIVUM", "winner")
CONTRACT = "pari.winner_watch.v1"
ALERTE_H = 2
TZ_KIN = timezone(timedelta(hours=1), "Africa/Kinshasa")


def path(sport):
    return os.path.join(WATCH_DIR, "watch_%s.json" % sport)


def blank(sport):
    return {"contract": CONTRACT, "sport": sport, "generated_at": None,
            "campagne": None, "campagne_uid": None, "matches": {},
            "tickets_enabled": False}


def load(sport):
    try:
        with open(path(sport), encoding="utf-8") as f:
            blob = json.load(f)
        if blob.get("contract") == CONTRACT:
            return blob
    except (OSError, json.JSONDecodeError):
        pass
    return blank(sport)


def save(blob, sport=None):
    sport = sport or blob.get("sport") or "foot"
    os.makedirs(WATCH_DIR, exist_ok=True)
    blob["generated_at"] = datetime.now(timezone.utc).isoformat()
    blob["contract"] = CONTRACT
    with open(path(sport), "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    return blob


def key_of(home, away, source_id=None):
    if source_id:
        return str(source_id)
    a = re.sub(r"[^a-z0-9]", "", str(home or "").lower())
    b = re.sub(r"[^a-z0-9]", "", str(away or "").lower())
    return "_".join(sorted([a, b])) if a and b else None


def kickoff_iso(raw):
    if not raw:
        return None
    try:
        if "T" in str(raw):
            return datetime.fromisoformat(str(raw)).isoformat()
        day, hour = str(raw)[:10], str(raw)[11:16] if len(str(raw)) > 11 else "19:00"
        h, m = (int(x) for x in hour.split(":")[:2])
        return datetime(int(day[:4]), int(day[5:7]), int(day[8:10]), h, m, tzinfo=TZ_KIN).isoformat()
    except (ValueError, TypeError):
        return None


def resolve(blob, match, now=None):
    """Devine l'entree. Retourne (cle, mode, holes). Aucun token a taper."""
    now = now or datetime.now(timezone.utc)
    matches = blob.setdefault("matches", {})
    sid = match.get("source_event_id")
    key = key_of(match.get("home"), match.get("away"), sid)
    if sid and str(sid) in matches:
        return str(sid), "id", []
    if key and key in matches:
        return key, "match_key", []
    actifs = [(k, v) for k, v in matches.items()
              if v.get("statut") == "ACTIF" and v.get("kickoff_iso")]
    proches = []
    for k, v in actifs:
        try:
            dt = datetime.fromisoformat(v["kickoff_iso"])
            if abs((dt - now).total_seconds()) <= 6 * 3600:
                proches.append(k)
        except (ValueError, TypeError):
            continue
    if len(proches) == 1:
        return proches[0], "match_inferé", ["match_inferé"]
    if len(proches) > 1:
        return (key or "auto"), "nouveau", ["match_ambigu"]
    return (key or "auto"), "nouveau", ["match_nouveau"]


def upsert(sport, capture, campagne=None, campagne_uid=None, now=None):
    """Enregistre une capture Winner pour un match. Sans ecrasement."""
    now = now or datetime.now(timezone.utc)
    blob = load(sport)
    blob["campagne"] = campagne or blob.get("campagne")
    blob["campagne_uid"] = campagne_uid or blob.get("campagne_uid")
    key, mode, holes = resolve(blob, capture, now)
    entry = blob["matches"].setdefault(key, {
        "match_key": key,
        "source_event_id": capture.get("source_event_id"),
        "home": capture.get("home"), "away": capture.get("away"),
        "kickoff_iso": capture.get("kickoff_iso"),
        "statut": "ACTIF",
        "captures": [], "next_alert_at": None, "last_alert_at": None,
    })
    for field in ("source_event_id", "home", "away", "kickoff_iso"):
        if capture.get(field) and not entry.get(field):
            entry[field] = capture[field]
    seq = max([c.get("seq", 0) for c in entry["captures"]] or [0]) + 1
    rec = {
        "seq": seq,
        "capture_id": capture.get("capture_id"),
        "at": capture.get("at") or now.isoformat(),
        "heures_avant_coup": None,
        "cotes": capture.get("cotes") or {},
        "source": "winner_capture",
        "mode_detection": mode,
    }
    if entry.get("kickoff_iso"):
        try:
            dt = datetime.fromisoformat(entry["kickoff_iso"])
            rec["heures_avant_coup"] = round((dt - datetime.fromisoformat(rec["at"])).total_seconds() / 3600, 2)
            if now >= dt and entry["statut"] == "ACTIF":
                entry["statut"] = "TERMINE"
        except (ValueError, TypeError):
            pass
    entry["captures"].append(rec)
    if holes:
        entry.setdefault("holes", []).extend(h for h in holes if h not in entry.get("holes", []))
    if entry["statut"] == "ACTIF" and not entry.get("next_alert_at") and seq == 1:
        entry["next_alert_at"] = (datetime.fromisoformat(rec["at"]) + timedelta(hours=ALERTE_H)).isoformat()
    return save(blob, sport), entry, rec


def new_campaign(sport, campagne=None, campagne_uid=None):
    """Nouvelle campagne : etat watch vierge (les ids M1.. se repetent)."""
    blob = blank(sport)
    blob["campagne"] = campagne
    blob["campagne_uid"] = campagne_uid
    return save(blob, sport)


def mark_stop(sport=None):
    """Arret des alertes : /stop ou coup d'envoi."""
    out = {}
    for s in ([sport] if sport else ("foot", "basket")):
        blob = load(s)
        for k, v in blob.get("matches", {}).items():
            if v.get("statut") == "ACTIF":
                v["statut"] = "TERMINE"
                v["arret_manuel"] = True
        out[s] = save(blob, s)
    return out


def due_alerts(sport, now=None):
    """Rappels 2h. Anti-derive : on saute les fenetres manquees."""
    now = now or datetime.now(timezone.utc)
    blob = load(sport)
    messages = []
    for key, v in blob.get("matches", {}).items():
        if v.get("statut") != "ACTIF":
            continue
        if not v.get("kickoff_iso") or not v.get("next_alert_at"):
            continue
        try:
            kick = datetime.fromisoformat(v["kickoff_iso"])
            nxt = datetime.fromisoformat(v["next_alert_at"])
        except (ValueError, TypeError):
            continue
        if now >= kick:
            v["statut"] = "TERMINE"
            v["arret_manuel"] = False
            continue
        if now < nxt:
            continue
        while nxt <= now:
            nxt += timedelta(hours=ALERTE_H)
        v["next_alert_at"] = nxt.isoformat()
        v["last_alert_at"] = now.isoformat()
        reste = max(0, int((kick - now).total_seconds() / 3600))
        messages.append(
            "RAPPEL WINNER — %s %s-%s (#%s) dans ~%dh. "
            "Envoie la capture Winner maintenant (same-book, /capture)." %
            (sport.upper(), v.get("home"), v.get("away"), key, reste))
    if messages:
        save(blob, sport)
    return messages


def cote_for(entry, selection):
    for c in reversed(entry.get("captures") or []):
        v = (c.get("cotes") or {}).get(selection)
        if v is not None:
            return float(v)
    return None


def clv(sport, key, selection):
    """CLV same-book : premiere cote / derniere cote - 1."""
    blob = load(sport)
    entry = blob.get("matches", {}).get(key)
    if not entry:
        return None, "match_introuvable"
    caps = [c for c in entry.get("captures") or []
            if (c.get("cotes") or {}).get(selection) is not None]
    if len(caps) < 2:
        return None, "clv_absent"
    first = float(caps[0]["cotes"][selection])
    last = float(caps[-1]["cotes"][selection])
    if first <= 1 or last <= 1:
        return None, "cote_invalide"
    return round(first / last - 1.0, 6), None


def main():
    import argparse
    ap = argparse.ArgumentParser(description="etat Winner / alertes")
    ap.add_argument("--sport", choices=("foot", "basket"), default="foot")
    ap.add_argument("--alerts", action="store_true")
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args()
    if args.stop:
        mark_stop(args.sport)
        print("[watch] arret", args.sport)
    elif args.alerts:
        for m in due_alerts(args.sport):
            print(m)
    else:
        print(json.dumps(load(args.sport), ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
