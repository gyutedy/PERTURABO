#!/usr/bin/env python3
"""
CAPTURE ALERTS — rappel Telegram toutes les 2h des que la premiere
capture Winner d'un match est enregistree (meme a T-20h). Arret au
coup d'envoi ou sur /stop (statut TERMINE dans watch_*.json).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1]
for d in ("F06_TRACKER", "ORCHESTRATOR"):
    p = WORLD / d / "CODEBASE"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import winner_watch  # noqa: E402
import notifier  # noqa: E402


def run(sport=None):
    sports = [sport] if sport in ("foot", "basket") else ["foot", "basket"]
    sent = []
    for s in sports:
        for message in winner_watch.due_alerts(s):
            ok = notifier.send(message)
            sent.append({"sport": s, "sent": bool(ok), "message": message})
    return sent


def main():
    import argparse
    ap = argparse.ArgumentParser(description="rappels capture Winner 2h")
    ap.add_argument("--sport", choices=("foot", "basket"), default=None)
    args = ap.parse_args()
    recs = run(args.sport)
    print("[capture-alerts] %d rappel(s)" % len(recs))
    for r in recs:
        print(" ", r["sport"], "envoye" if r["sent"] else "ECHEC", r["message"][:110])


if __name__ == "__main__":
    main()
