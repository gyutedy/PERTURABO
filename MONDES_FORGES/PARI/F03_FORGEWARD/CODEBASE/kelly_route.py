#!/usr/bin/env python3
"""
KELLY ROUTE — 1/8 defaut, 1/4 gate ECE (S10 / v3.10.9b)
=======================================================
calibration_validee = ECE_walk_forward <= seuil.
1/4 seulement si calibration OK et P(EV>0) >= 0.55 et n>=50.
P/ECE absents = 1/8 + holes. Combo = MC conjoint toutes jambes.
Budget operateur (mise_fc) intact. Stdlib only. Zero Data, Zero Calc.
"""

from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F06 = os.path.join(WORLD, "F06_TRACKER", "CODEBASE")
if F06 not in sys.path:
    sys.path.insert(0, F06)

CFG_PATH = os.path.join(WORLD, "config", "kelly.json")
REPORT_PATH = os.path.join(WORLD, "ARCHIVUM", "learnings", "backtest_report.json")

EPS = 1e-6

DEFAULTS = {
    "fraction_default": 0.125,
    "fraction_plafond": 0.25,
    "p_ev_positif": 0.55,
    "ece": 0.03,
    "n_lock": 50,
    "mc_draws": 2000,
    "mc_seed": 42,
}


def load_config(path=None):
    cfg = dict(DEFAULTS)
    p = path or CFG_PATH
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return cfg
        if isinstance(raw, dict):
            for k in DEFAULTS:
                if k in raw:
                    cfg[k] = raw[k]
    return cfg


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


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


def decide(ece=None, p_ev=None, n=None, cfg=None):
    cfg = cfg or load_config()
    frac_lo = float(cfg["fraction_default"])
    frac_hi = float(cfg["fraction_plafond"])
    p_min = float(cfg["p_ev_positif"])
    ece_max = float(cfg["ece"])
    n_lock = int(cfg["n_lock"])
    holes = []
    checks = ["kelly_route"]

    ece_f = _f(ece)
    p_f = _f(p_ev)
    n_i = None
    if n is not None:
        try:
            n_i = int(n)
        except (TypeError, ValueError):
            n_i = None

    if ece_f is None:
        holes.append("ece")
        cal = False
    else:
        cal = ece_f <= ece_max
        checks.append("ece_walk_forward")

    if p_f is None:
        holes.append("p_ev")

    locked = n_i is None or n_i < n_lock
    if n_i is None:
        holes.append("n")
    elif locked:
        holes.append("n<50")

    use_hi = bool(cal and p_f is not None and p_f >= p_min and not locked)
    frac = frac_hi if use_hi else frac_lo
    label = "1/4" if use_hi else "1/8"
    return {
        "fraction": frac,
        "label": label,
        "calibration_validee": cal,
        "p_ev": p_f,
        "ece": ece_f,
        "n": n_i,
        "locked": locked,
        "holes": _uniq(holes),
        "checks": checks,
        "gate_1_4": use_hi,
    }


def load_ece(report=None, path=None):
    blob = report
    if blob is None:
        p = path or REPORT_PATH
        if not p or not os.path.exists(p):
            return None, ["ece"]
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None, ["ece"]
    if not isinstance(blob, dict):
        return None, ["ece"]
    m = blob.get("metrics") or {}
    e = _f(m.get("ece_o2.5") if m.get("ece_o2.5") is not None else m.get("ece"))
    if e is not None:
        return e, []
    vals = []
    for rec in (blob.get("leagues") or {}).values():
        mm = (rec or {}).get("metrics") or {}
        ev = _f(mm.get("ece_o2.5") if mm.get("ece_o2.5") is not None else mm.get("ece"))
        if ev is not None:
            vals.append(ev)
    if vals:
        return max(vals), []
    return None, ["ece"]


def load_p_ev(lots=None):
    if lots is None:
        try:
            import ledger as _ledger
            box = _ledger.load_lots()
            lots = box.get("lots") if isinstance(box, dict) else box
        except Exception:
            return None, 0, ["p_ev"]
    try:
        import diag as _diag
        rep = _diag.diagnose(lots or [])
    except Exception:
        return None, 0, ["p_ev"]
    n = int(rep.get("n") or 0)
    p = _f(rep.get("p_ev_positif"))
    holes = []
    if p is None:
        holes.append("p_ev")
    return p, n, holes


def route_global(ece=None, p_ev=None, n=None, lots=None, report=None, cfg=None):
    cfg = cfg or load_config()
    extra = []
    if ece is None:
        ece, h = load_ece(report=report)
        extra.extend(h)
    if p_ev is None or n is None:
        p2, n2, h2 = load_p_ev(lots=lots)
        if p_ev is None:
            p_ev = p2
            extra.extend(h2)
        if n is None:
            n = n2
    rec = decide(ece=ece, p_ev=p_ev, n=n, cfg=cfg)
    rec["holes"] = _uniq(list(rec.get("holes") or []) + extra)
    return rec


def p_ev_conjoint(jambes, draws=None, seed=None, cfg=None):
    cfg = cfg or load_config()
    n_draws = int(cfg["mc_draws"] if draws is None else draws)
    n_seed = int(cfg["mc_seed"] if seed is None else seed)
    legs = []
    holes = []
    for j in jambes or []:
        p = _f((j or {}).get("p_modele"))
        cote = _f((j or {}).get("cote"))
        if p is None or not (0.0 < p < 1.0):
            holes.append("p_modele")
            continue
        if cote is None or cote <= 1:
            holes.append("cote")
            continue
        legs.append({"p": p, "cote": cote})
    if holes:
        return None, _uniq(holes)
    if not legs:
        return None, ["jambes"]
    rng = random.Random(n_seed)
    kappa = 2.0
    hits = 0
    n_ok = 0
    for _ in range(int(n_draws)):
        p_prod = 1.0
        c_prod = 1.0
        for leg in legs:
            p0 = leg["p"]
            aa = max(p0 * kappa, EPS)
            bbv = max((1.0 - p0) * kappa, EPS)
            p_s = rng.betavariate(aa, bbv)
            p_prod *= p_s
            c_prod *= leg["cote"]
        n_ok += 1
        if p_prod * c_prod - 1.0 > 0:
            hits += 1
    if n_ok == 0:
        return None, ["mc"]
    return hits / n_ok, []


def route_ticket(jambes=None, ece=None, p_ev=None, n=None, lots=None, report=None, cfg=None):
    cfg = cfg or load_config()
    legs = list(jambes or [])
    extra = []
    if ece is None:
        ece, h = load_ece(report=report)
        extra.extend(h)
    need_diag = n is None or (p_ev is None and len(legs) < 2)
    if need_diag:
        p2, n2, h2 = load_p_ev(lots=lots)
        if n is None:
            n = n2
        if p_ev is None and len(legs) < 2:
            p_ev = p2
            extra.extend(h2)
        elif n is None:
            extra.extend(x for x in h2 if x != "p_ev")
    if p_ev is None and len(legs) >= 2:
        p_ev, h3 = p_ev_conjoint(legs, cfg=cfg)
        extra.extend(h3)
    rec = decide(ece=ece, p_ev=p_ev, n=n, cfg=cfg)
    rec["holes"] = _uniq(list(rec.get("holes") or []) + extra)
    rec["conjoint"] = len(legs) >= 2
    return rec


def stamp_ticket(ticket, route=None, **kwargs):
    rec = route if route is not None else route_ticket(
        jambes=(ticket or {}).get("jambes"), **kwargs)
    ticket = ticket if ticket is not None else {}
    ticket["kelly_fraction"] = rec["fraction"]
    ticket["kelly_label"] = rec["label"]
    ticket["kelly_holes"] = list(rec.get("holes") or [])
    ticket["kelly_ece"] = rec.get("ece")
    ticket["kelly_p_ev"] = rec.get("p_ev")
    ticket["kelly_calibration_validee"] = rec.get("calibration_validee")
    ticket["kelly"] = {
        "fraction": rec["fraction"],
        "label": rec["label"],
        "p_ev": rec.get("p_ev"),
        "ece": rec.get("ece"),
        "calibration_validee": rec.get("calibration_validee"),
        "holes": list(rec.get("holes") or []),
        "n": rec.get("n"),
        "locked": rec.get("locked"),
        "conjoint": rec.get("conjoint"),
    }
    return ticket


def procedure_extra(route=None, **kwargs):
    rec = route if route is not None else route_global(**kwargs)
    holes = list(rec.get("holes") or [])
    return {
        "kelly": {
            "fraction": rec.get("fraction"),
            "label": rec.get("label"),
            "p_ev": rec.get("p_ev"),
            "ece": rec.get("ece"),
            "calibration_validee": rec.get("calibration_validee"),
            "n": rec.get("n"),
            "locked": rec.get("locked"),
            "holes": holes,
            "checks": list(rec.get("checks") or ["kelly_route"]),
        },
        "holes": holes,
        "checks": list(rec.get("checks") or ["kelly_route"]),
    }


def procedure_extra_from_tickets(tickets_doc, **kwargs):
    tickets = (tickets_doc or {}).get("tickets") or []
    stamped = [t for t in tickets if t.get("kelly_fraction") is not None]
    if not stamped:
        return procedure_extra(**kwargs)
    t0 = stamped[0]
    nested = t0.get("kelly") or {}
    rec = {
        "fraction": t0.get("kelly_fraction"),
        "label": t0.get("kelly_label") or ("1/4" if _f(t0.get("kelly_fraction")) == 0.25 else "1/8"),
        "p_ev": t0.get("kelly_p_ev"),
        "ece": t0.get("kelly_ece"),
        "calibration_validee": t0.get("kelly_calibration_validee"),
        "holes": list(t0.get("kelly_holes") or []),
        "n": nested.get("n"),
        "locked": nested.get("locked"),
        "checks": ["kelly_route"],
    }
    extra = procedure_extra(route=rec)
    extra["kelly"]["fractions"] = [t.get("kelly_fraction") for t in stamped]
    extra["kelly"]["source"] = "tickets"
    return extra
