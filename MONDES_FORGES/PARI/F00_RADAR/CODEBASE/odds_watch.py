"""
F00 ODDS WATCH — rescan T-2h (The Odds API).
Compare cotes capture vs marche. EV recast avec p_modele deja calcule.
Jamais dans Poisson. Cle absente / hors fenetre / timeout = skip, trou declare.
Kill switch PARI_SKIP_ODDS=1.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONNECTORS = os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors")
sys.path.insert(0, HERE)
sys.path.insert(0, CONNECTORS)

import capteurs
import odds_api

ODDS_DIR = os.path.join(WORLD, "ARCHIVUM", "odds")
CARTE_PATH = os.path.join(WORLD, "ARCHIVUM", "fixtures", "matches.json")
PRED_PATH = os.path.join(WORLD, "F03_FORGEWARD", "OUT", "predictions.json")
HORIZON_H = 3
MOVE_PCT = 0.05


def _load_env_pari():
    for name in (".env", "env_pari"):
        path = os.path.join(WORLD, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    if key and val and not os.environ.get(key):
                        os.environ[key] = val
        except OSError:
            pass


_load_env_pari()


def now_utc(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now


def _load(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _dump(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)


def parse_kickoff(m, carte=None):
    day = (m.get("date") or (carte or {}).get("date") or "")[:10]
    heure = (m.get("heure") or m.get("time") or "00:00")[:5]
    if not day or len(day) < 10:
        return None
    try:
        hh, mm = heure.split(":")
        dt = datetime(int(day[:4]), int(day[5:7]), int(day[8:10]),
                      int(hh), int(mm), tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def in_window(kickoff, now=None, horizon_h=HORIZON_H):
    now = now_utc(now)
    if kickoff is None:
        return False
    return now <= kickoff <= now + timedelta(hours=horizon_h)


def _pred_by_id(predictions):
    out = {}
    for p in (predictions or {}).get("predictions") or []:
        out[p.get("id")] = p
    return out


def recast(capture_cotes, market_cotes, selections, seuil=0.03):
    """EV recast. selections = predictions du match. Jamais de p inventee."""
    alerts = []
    moves = []
    by_sel = {s.get("selection"): s for s in selections or []}
    for sel, old in (capture_cotes or {}).items():
        new = (market_cotes or {}).get(sel)
        if not isinstance(old, (int, float)) or not isinstance(new, (int, float)):
            continue
        if old > 0 and abs(new - old) / old >= MOVE_PCT:
            moves.append({"selection": sel, "cote_capture": old, "cote_marche": new})
        s = by_sel.get(sel)
        if not s:
            continue
        p = s.get("p_modele")
        if not isinstance(p, (int, float)):
            continue
        old_ev = s.get("ev")
        if old_ev is None:
            old_ev = p * old - 1
        new_ev = p * new - 1
        verdict = s.get("verdict")
        if verdict == "VALUE" and new_ev <= 0:
            alerts.append({
                "selection": sel, "kind": "ESTOMPE",
                "cote_capture": old, "cote_marche": new,
                "ev_avant": round(old_ev, 4), "ev_apres": round(new_ev, 4),
            })
        elif verdict == "VALUE" and new_ev < seuil:
            alerts.append({
                "selection": sel, "kind": "AMINCI",
                "cote_capture": old, "cote_marche": new,
                "ev_avant": round(old_ev, 4), "ev_apres": round(new_ev, 4),
            })
    return alerts, moves


def scan(carte=None, predictions=None, now=None, horizon_h=HORIZON_H, force=False):
    """Retourne {scanned, skipped, alerts, snapshot, reason}."""
    now = now_utc(now)
    if os.environ.get("PARI_SKIP_ODDS") == "1":
        return {"scanned": [], "skipped": [], "alerts": [], "snapshot": None,
                "reason": "PARI_SKIP_ODDS"}
    if not odds_api._key():
        return {"scanned": [], "skipped": [], "alerts": [], "snapshot": None,
                "reason": "ODDS_API_KEY absente"}
    carte = carte if carte is not None else (_load(CARTE_PATH) or {})
    predictions = predictions if predictions is not None else (_load(PRED_PATH) or {})
    preds = _pred_by_id(predictions)
    seuil = float((predictions or {}).get("seuil_ev_applique") or 0.03)
    scanned, skipped, alerts = [], [], []
    for m in carte.get("matchs") or []:
        mid = m.get("id")
        ko = parse_kickoff(m, carte)
        if not force and not in_window(ko, now=now, horizon_h=horizon_h):
            skipped.append({"id": mid, "reason": "hors_fenetre" if ko else "kickoff_absent"})
            continue
        code = capteurs.ligue_code(m.get("ligue") or carte.get("ligue") or "")
        row = odds_api.match_odds(m.get("dom") or "", m.get("ext") or "", code)
        if not row or not row.get("cotes"):
            skipped.append({"id": mid, "reason": "trou_marche"})
            continue
        rec_alerts, moves = recast(
            m.get("cotes") or {}, row.get("cotes") or {},
            (preds.get(mid) or {}).get("selections") or [],
            seuil=seuil,
        )
        item = {
            "id": mid, "dom": m.get("dom"), "ext": m.get("ext"),
            "code": code, "kickoff": ko.strftime("%Y-%m-%dT%H:%M:%SZ") if ko else None,
            "bookmaker": row.get("bookmaker"),
            "cotes_capture": m.get("cotes") or {},
            "cotes_marche": row.get("cotes") or {},
            "moves": moves, "alerts": rec_alerts,
        }
        scanned.append(item)
        alerts.extend([{**a, "id": mid, "match": f"{m.get('dom')} vs {m.get('ext')}"} for a in rec_alerts])
    snap = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "the-odds-api",
        "horizon_h": horizon_h,
        "scanned": scanned,
        "skipped": skipped,
        "alerts": alerts,
    }
    return {"scanned": scanned, "skipped": skipped, "alerts": alerts,
            "snapshot": snap, "reason": "ok"}


def format_alerts(result):
    alerts = result.get("alerts") or []
    if not alerts:
        n = len(result.get("scanned") or [])
        skip = len(result.get("skipped") or [])
        reason = result.get("reason") or "ok"
        if reason not in ("ok",):
            return f"ODDS T-2h skip: {reason}"
        return f"ODDS T-2h: {n} scan, {skip} skip, 0 alerte."
    lines = [f"ODDS T-2h — {len(alerts)} alerte(s):"]
    for a in alerts:
        lines.append(
            f"- {a.get('match')} {a.get('selection')} {a.get('kind')} "
            f"{a.get('cote_capture')} -> {a.get('cote_marche')} "
            f"EV {a.get('ev_avant')} -> {a.get('ev_apres')}"
        )
    lines.append("Cotes Winner restent la capture. Marche = The Odds API (pas scrape).")
    return "\n".join(lines)


def persist(result, odds_dir=None):
    snap = result.get("snapshot")
    if not snap:
        return None
    odds_dir = odds_dir or ODDS_DIR
    ts = (snap.get("generated_at") or now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")).replace(":", "")
    path = os.path.join(odds_dir, f"t2h_{ts}.json")
    _dump(path, snap)
    _dump(os.path.join(odds_dir, "latest.json"), snap)
    return path


def run(carte_path=None, pred_path=None, now=None, force=False, notify=False):
    carte = _load(carte_path or CARTE_PATH) or {}
    predictions = _load(pred_path or PRED_PATH) or {}
    result = scan(carte=carte, predictions=predictions, now=now, force=force)
    persist(result)
    msg = format_alerts(result)
    print(msg)
    if notify and result.get("alerts"):
        sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
        import notifier
        notifier.send(msg)
    return result


def main():
    import argparse
    p = argparse.ArgumentParser(description="F00 ODDS WATCH T-2h")
    p.add_argument("--carte", default=CARTE_PATH)
    p.add_argument("--predictions", default=PRED_PATH)
    p.add_argument("--force", action="store_true")
    p.add_argument("--notify", action="store_true")
    args = p.parse_args()
    run(carte_path=args.carte, pred_path=args.predictions,
        force=args.force or os.environ.get("PARI_ODDS_FORCE") == "1",
        notify=args.notify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
