#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_watch — campagne, devinage, alertes 2h, CLV same-book."""
from __future__ import annotations

import importlib.util
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "winner_watch_mod", WORLD / "F06_TRACKER" / "CODEBASE" / "winner_watch.py")
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)

PASS, N = [], [0]
NOW = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)


def check(name, cond, note=""):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name, note)
        raise AssertionError(name)


def cap(seq, odds, at, sid="20010"):
    return {"source_event_id": sid, "home": "Team A", "away": "Team B",
            "kickoff_iso": (NOW + timedelta(hours=2)).isoformat(),
            "capture_id": "C-X%02d" % seq, "at": at.isoformat(),
            "cotes": odds}


def run_checks():
    PASS.clear()
    N[0] = 0
    old = ww.WATCH_DIR
    ww.WATCH_DIR = tempfile.mkdtemp(prefix="pari-watch-")
    try:
        t0 = NOW - timedelta(hours=20)
        blob, entry, rec = ww.upsert("basket", cap(1, {"1": 2.29, "2": 1.61}, t0),
                                     "PARI-20261124", "A1B2", now=NOW)
        check("1ere capture", rec["seq"] == 1 and entry["statut"] == "ACTIF")
        check("campagne uid", blob["campagne_uid"] == "A1B2")
        check("prochaine alerte +2h", entry["next_alert_at"] is not None
              and datetime.fromisoformat(entry["next_alert_at"]) > t0)
        check("heures avant coup", rec["heures_avant_coup"] is not None
              and rec["heures_avant_coup"] > 10)

        # devinage par id
        key, mode, holes = ww.resolve(ww.load("basket"), cap(2, {}, NOW), NOW)
        check("devinage par id", key == "20010" and mode == "id" and not holes)

        # 2e capture + CLV same-book
        ww.upsert("basket", cap(2, {"1": 2.10, "2": 1.75}, NOW), now=NOW)
        clv, hole = ww.clv("basket", "20010", "1")
        check("clv same-book", clv is not None and clv > 0 and hole is None,
              "%s %s" % (clv, hole))
        clv1, hole1 = ww.clv("basket", "20010", "X")
        check("clv absent", clv1 is None and hole1 == "clv_absent")

        # alertes : avant la 1ere fenetre rien, apres 2h un rappel
        early = NOW - timedelta(hours=19)
        check("pas d alerte trop tot", ww.due_alerts("basket", early) == [])
        nxt = datetime.fromisoformat(ww.load("basket")["matches"]["20010"]["next_alert_at"])
        msgs = ww.due_alerts("basket", nxt + timedelta(minutes=5))
        check("alerte 2h", len(msgs) == 1 and "RAPPEL WINNER" in msgs[0], str(msgs))
        check("anti spam", ww.due_alerts("basket", nxt + timedelta(minutes=6)) == [])

        # arret /stop
        ww.mark_stop("basket")
        check("stop", ww.load("basket")["matches"]["20010"]["statut"] == "TERMINE")

        # nouvelle campagne : etat vierge (ids M1.. ne collisionnent pas)
        nc = ww.new_campaign("basket", "PARI-20261125", "ZZZZ")
        check("nouvelle campagne vierge", nc["matches"] == {}
              and nc["campagne_uid"] == "ZZZZ")

        # ambiguite : deux matchs actifs proches dans le meme etat
        blob2 = ww.blank("basket")
        for sid in ("20010", "999"):
            blob2["matches"][sid] = {
                "statut": "ACTIF", "kickoff_iso": (NOW + timedelta(hours=2)).isoformat(),
                "home": "Team " + sid, "away": "Autre " + sid,
            }
        _, mode2, holes2 = ww.resolve(blob2, {"home": "Team C", "away": "Team D"}, NOW)
        check("match ambigu", "match_ambigu" in holes2, str((mode2, holes2)))
    finally:
        ww.WATCH_DIR = old

    print(f"winner_watch : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_watch():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
