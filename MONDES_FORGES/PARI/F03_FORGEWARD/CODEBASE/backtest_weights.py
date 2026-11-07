#!/usr/bin/env python3
"""
BACKTEST POIDS SCORER — une maj market_profiles.json (S16 / v4 R7)
==================================================================
n<50 tickets reels (G/P) : locked, a priori intact.
n>=50 : une seule maj journalisee. Jamais de poids a la main.
Seed 42. Stdlib only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))

KEYS = ("B1", "B2", "B3", "B4", "B5", "B6")
DEFAULT_POIDS = {
    "B1": 0.30, "B2": 0.20, "B3": 0.20, "B4": 0.15, "B5": 0.10, "B6": 0.05,
}
N_LOCK = 50
CELL_MIN = 8
SEED = 42
JOURNAL_NAME = "scorer_weight_journal.json"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clip(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _renorm(poids):
    src = dict(DEFAULT_POIDS)
    src.update(poids or {})
    s = 0.0
    out = {}
    for k in KEYS:
        fv = _f(src.get(k))
        if fv is None or fv < 0:
            fv = DEFAULT_POIDS[k]
        out[k] = fv
        s += fv
    if s <= 0:
        return dict(DEFAULT_POIDS)
    return {k: round(out[k] / s, 4) for k in KEYS}


def count_real_tickets(lots):
    n = 0
    for lot in lots or []:
        for t in (lot.get("settle") or {}).get("tickets") or []:
            if t.get("resultat") in ("G", "P"):
                n += 1
    return n


def _jambe_marche(j):
    return str(j.get("marche") or "")


def _lot_ligue(lot, bundles_dir=None):
    for key in ("league_code", "ligue_code", "ligue"):
        v = lot.get(key)
        if v:
            return str(v)
    bid = lot.get("bundle_id")
    if not bid or not bundles_dir:
        return None
    matches_path = os.path.join(bundles_dir, str(bid), "matches.json")
    if not os.path.exists(matches_path):
        intel = os.path.join(bundles_dir, str(bid), "intel.json")
        matches_path = intel if os.path.exists(intel) else matches_path
    try:
        with open(matches_path, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for m in blob.get("matchs") or blob.get("matches") or []:
        code = m.get("league_code") or m.get("ligue_code")
        if code:
            return str(code)
    return blob.get("ligue_code") or blob.get("league_code") or None


def collect_cells(lots, bundles_dir=None):
    cells = {}
    global_gp = []
    for lot in lots or []:
        ligue = _lot_ligue(lot, bundles_dir) or "_"
        snap = {
            t.get("rang_ticket"): t
            for t in (lot.get("snapshot_t0") or {}).get("tickets") or []
        }
        for t in (lot.get("settle") or {}).get("tickets") or []:
            res = t.get("resultat")
            if res not in ("G", "P"):
                continue
            src = snap.get(t.get("rang_ticket")) or {}
            marches = []
            for j in src.get("jambes") or t.get("jambes") or []:
                m = _jambe_marche(j)
                if m:
                    marches.append(m)
            marche = marches[0] if marches else "_"
            key = (str(ligue), str(marche))
            cells.setdefault(key, []).append(res)
            global_gp.append(res)
    return cells, global_gp


def _hit(seq):
    n = len(seq or [])
    if n == 0:
        return None, 0
    g = sum(1 for x in seq if x == "G")
    return g / float(n), n


def _tilt(poids, hit_rate):
    p = _renorm(poids)
    if hit_rate is None:
        return p
    delta = _clip(hit_rate - 0.50, -0.10, 0.10)
    p["B1"] = p["B1"] + 0.15 * delta
    p["B5"] = p["B5"] - 0.10 * delta
    return _renorm(p)


def _seuil(base, hit_rate):
    s = 0.50 if base is None else float(base)
    if hit_rate is None:
        return round(_clip(s, 0.45, 0.65), 4)
    s = s + (0.50 - hit_rate) * 0.10
    return round(_clip(s, 0.45, 0.65), 4)


def journal_path(world=None):
    root = world or WORLD
    return os.path.join(root, "ARCHIVUM", "learnings", JOURNAL_NAME)


def load_journal(path=None):
    p = path or journal_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "note": "S16 une seule maj poids scorer. Jamais a la main.",
        "events": [],
    }


def profiles_already_updated(blob):
    if not isinstance(blob, dict):
        return False
    if blob.get("s16_updated"):
        return True
    log = blob.get("update_journal") or []
    return bool(log)


def propose(lots, profiles, bundles_dir=None, seed=SEED):
    n = count_real_tickets(lots)
    out = {
        "ok": True,
        "locked": n < N_LOCK,
        "n": n,
        "seed": seed,
        "written": False,
        "reason": None,
        "proposed": None,
    }
    if n < N_LOCK:
        out["reason"] = "n_lock"
        return out
    cells, global_gp = collect_cells(lots, bundles_dir)
    g_hit, g_n = _hit(global_gp)
    default = profiles.get("default") if isinstance(profiles.get("default"), dict) else {}
    base_poids = _renorm(default.get("poids") or DEFAULT_POIDS)
    base_seuil = _f(default.get("seuil"))
    if base_seuil is None:
        base_seuil = 0.50
    proposed = json.loads(json.dumps(profiles))
    proposed["default"] = {
        "seuil": _seuil(base_seuil, g_hit),
        "poids": _tilt(base_poids, g_hit),
    }
    ligues = proposed.get("ligues") if isinstance(proposed.get("ligues"), dict) else {}
    marches_root = proposed.get("marches") if isinstance(proposed.get("marches"), dict) else {}
    for (ligue, marche), seq in sorted(cells.items()):
        hit, cn = _hit(seq)
        if cn < CELL_MIN:
            continue
        rec = {"seuil": _seuil(base_seuil, hit), "poids": _tilt(base_poids, hit), "n": cn}
        if ligue and ligue != "_":
            bucket = ligues.setdefault(ligue, {"marches": {}})
            bucket.setdefault("marches", {})[marche] = rec
        elif marche and marche != "_":
            prev = marches_root.get(marche) if isinstance(marches_root.get(marche), dict) else {}
            merged = dict(prev)
            merged["seuil"] = rec["seuil"]
            merged["poids"] = rec["poids"]
            marches_root[marche] = merged
    proposed["ligues"] = ligues
    proposed["marches"] = marches_root
    proposed["s16_updated"] = True
    proposed["s16_n"] = n
    proposed["s16_seed"] = seed
    out["proposed"] = proposed
    out["global_hit"] = g_hit
    out["global_n"] = g_n
    return out


def retune(lots, profiles_path, bundles_dir=None, seed=SEED, apply=False, journal=None, now=None):
    blob = {}
    if profiles_path and os.path.exists(profiles_path):
        try:
            with open(profiles_path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                blob = raw
        except (OSError, json.JSONDecodeError):
            blob = {}
    n = count_real_tickets(lots)
    result = propose(lots, blob, bundles_dir=bundles_dir, seed=seed)
    if result.get("locked"):
        return result
    if profiles_already_updated(blob):
        result["written"] = False
        result["reason"] = "already_updated"
        result["ok"] = True
        return result
    if not apply:
        result["reason"] = "dry"
        return result
    proposed = result.get("proposed") or blob
    ver = blob.get("version") or 1
    try:
        ver = int(ver) + 1
    except (TypeError, ValueError):
        ver = 2
    proposed["version"] = ver
    proposed["note"] = (
        "S16 backtest n>={0}. Une seule maj. Ne pas retuner a la main.".format(N_LOCK)
    )
    event = {
        "at": now or now_iso(),
        "n": n,
        "seed": seed,
        "version": ver,
        "path": profiles_path,
    }
    log = list(proposed.get("update_journal") or [])
    log.append(event)
    proposed["update_journal"] = log
    os.makedirs(os.path.dirname(os.path.abspath(profiles_path)), exist_ok=True)
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(proposed, f, indent=2, ensure_ascii=False)
        f.write("\n")
    jpath = journal or journal_path()
    box = load_journal(jpath)
    box.setdefault("events", []).append(event)
    os.makedirs(os.path.dirname(os.path.abspath(jpath)), exist_ok=True)
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(box, f, indent=2, ensure_ascii=False)
        f.write("\n")
    result["written"] = True
    result["reason"] = "updated"
    result["version"] = ver
    result["journal"] = jpath
    return result
