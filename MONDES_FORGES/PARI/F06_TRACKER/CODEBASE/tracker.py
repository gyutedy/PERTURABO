"""
F06 TRACKER — Le ledger du monde PARI
======================================
Tickets (TOUS — gagnants ET perdants), ROI, calibration, pronostiqueurs.
Post-Porte 4 : chaque pari réel est loggé, chaque résultat settle, chaque
proba prédite rejoint calibration.json quand le résultat tombe.

Usage:
  python tracker.py add --file nouveau_ticket.json
  python tracker.py settle --id TICKET_0002 --resultat gagne|perdu|annule --pnl-units 2.3
  python tracker.py roi
  python tracker.py calibration
  python tracker.py pronostic --slug chaine_a --resultat gagne
"""

import json
import argparse
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LEARN = os.path.join(HERE, "..", "..", "ARCHIVUM", "learnings")
TICKETS = os.path.join(LEARN, "tickets.json")
CALIB = os.path.join(LEARN, "calibration.json")
CHANNELS = os.path.join(HERE, "..", "..", "ARCHIVUM", "pronostics", "channels.json")

BUCKETS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log(msg):
    with open(os.path.join(HERE, "..", "TRACKING", "F06_LOG.md"), "a", encoding="utf-8") as f:
        f.write(f"- [{now()}] {msg}\n")
    print(f"[TRACKER] {msg}")


def cmd_add(args):
    with open(args.file, "r", encoding="utf-8") as f:
        t = json.load(f)
    box = load(TICKETS, {"tickets": []})
    if not t.get("id"):
        t["id"] = f"TICKET_{len(box['tickets']) + 1:04d}"
    t.setdefault("logged_at", now())
    box["tickets"].append(t)
    save(TICKETS, box)
    _log(f"ticket {t['id']} ajouté ({t.get('nb_jambes')} jambes, mise {t.get('mise_units')}u)")


def cmd_settle(args):
    box = load(TICKETS, {"tickets": []})
    tt = next((t for t in box["tickets"] if t["id"] == args.id), None)
    if not tt:
        print(f"[TRACKER] ❌ ticket inconnu: {args.id}")
        return
    res = {"gagne": "gagné", "perdu": "perdu", "annule": "annulé"}.get(args.resultat.lower(), args.resultat)
    tt["resultat"] = res
    pnl = None
    if res == "gagné":
        pnl = args.pnl_units if args.pnl_units is not None else round(
            (tt.get("cote_totale") or 1) - 1, 2) * (tt.get("mise_units") or 1)
    elif res == "perdu":
        pnl = -(tt.get("mise_units") or 0)
    elif args.pnl_units is not None:
        pnl = args.pnl_units
    tt["pnl_units"] = round(pnl, 2) if pnl is not None else None
    tt["settled_at"] = now()
    save(TICKETS, box)
    _log(f"ticket {tt['id']} settle → {res}, pnl {tt['pnl_units']}u")

    # calibration : proba prédite du siège vs réalisé
    sp = tt.get("score_predit") or (tt.get("jambes") or [{}])[0].get("p_modele")
    if isinstance(sp, (int, float)):
        cal = load(CALIB, {"records": [], "tickets_settle": 0})
        cal.setdefault("records", []).append({"ticket": tt["id"], "p": sp, "gagne": res == "gagné", "ts": now()})
        cal["tickets_settle"] = len(cal["records"])
        save(CALIB, cal)
        cmd_calibration(quiet=True)
        _log(f"calibration: score_predit {sp:.0%} → {'gagné' if res == 'gagné' else 'non'}")


def cmd_roi(args):
    box = load(TICKETS, {"tickets": []})
    settled = [t for t in box["tickets"] if t.get("resultat") and t.get("pnl_units") is not None]
    if not settled:
        print("[TRACKER] Aucun ticket settle. Rien à calculer.")
        return
    mises = sum(t.get("mise_units") or 0 for t in settled)
    pnl = sum(t["pnl_units"] for t in settled)
    roi = pnl / mises if mises else 0
    wins = sum(1 for t in settled if t["resultat"] == "gagné")
    print(f"[TRACKER] Tickets settle: {len(settled)} · PnL: {pnl:+.2f}u · ROI: {roi:+.1%} · Réussite: {wins}/{len(settled)}")
    _log(f"ROI report: {roi:+.1%}")


def cmd_calibration(args=None, quiet=False):
    cal = load(CALIB, {"records": []})
    recs = cal.get("records", [])
    if not recs:
        print("[TRACKER] Aucun record de calibration.")
        return
    out = {"buckets": [], "tickets_settle": len(recs), "records": recs}
    for lo, hi in BUCKETS:
        bs = [r for r in recs if lo <= r["p"] < hi]
        if bs:
            out["buckets"].append({
                "bucket": f"{lo:.0%}-{hi:.0%}",
                "p_predite_moy": round(sum(r["p"] for r in bs) / len(bs), 3),
                "realise": round(sum(1 for r in bs if r["gagne"]) / len(bs), 3),
                "n": len(bs),
            })
    out["buckets"] += [{"bucket": f"{lo:.0%}-{hi:.0%}", "p_predite_moy": None, "realise": None, "n": 0}
                       for lo, hi in BUCKETS if not [r for r in recs if lo <= r["p"] < hi]]
    out["buckets"].sort(key=lambda b: b["bucket"])
    save(CALIB, out)
    if not quiet:
        print("[TRACKER] Calibration:")
        for b in out["buckets"]:
            if b["n"]:
                print(f"  {b['bucket']:<9} prédit {b['p_predite_moy']:.0%} → réalisé {b['realise']:.0%} (n={b['n']})")


def cmd_pronostic(args):
    ch = load(CHANNELS, {"channels": []})
    c = next((x for x in ch["channels"] if x["slug"] == args.slug), None)
    if not c:
        print(f"[TRACKER] canal inconnu: {args.slug} — ajoute-le dans channels.json")
        return
    c["pronostics_count"] = c.get("pronostics_count", 0) + 1
    g = c.get("pronostics_gagnes", 0) + (1 if args.resultat.lower() == "gagne" else 0)
    c["pronostics_gagnes"] = g
    c["taux_reussite"] = round(g / c["pronostics_count"], 3)
    save(CHANNELS, ch)
    _log(f"pronostic {args.slug} → {args.resultat} ({g}/{c['pronostics_count']})")


def main():
    parser = argparse.ArgumentParser(description="F06 TRACKER — ledger PARI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("--file", required=True)
    s = sub.add_parser("settle"); s.add_argument("--id", required=True)
    s.add_argument("--resultat", required=True)
    s.add_argument("--pnl-units", type=float, default=None)
    sub.add_parser("roi")
    sub.add_parser("calibration")
    pp = sub.add_parser("pronostic"); pp.add_argument("--slug", required=True)
    pp.add_argument("--resultat", required=True)
    args = parser.parse_args()
    os.makedirs(os.path.join(HERE, "..", "TRACKING"), exist_ok=True)

    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "settle":
        cmd_settle(args)
    elif args.cmd == "roi":
        cmd_roi(args)
    elif args.cmd == "calibration":
        cmd_calibration(args)
    elif args.cmd == "pronostic":
        cmd_pronostic(args)


if __name__ == "__main__":
    main()
