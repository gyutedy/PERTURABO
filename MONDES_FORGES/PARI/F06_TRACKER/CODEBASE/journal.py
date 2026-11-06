#!/usr/bin/env python3
"""
JOURNAL F06 — 2 volets (S3 / v3.3)
==================================
(a) procedure a la creation : checks, trous, seuils, Kelly. IMMUTABLE.
(b) outcome au settle : mise, cote, G/P, pnl, CLV si connu. Jamais mute (a).
CLV absent = hole, jamais 0. Stdlib only. Zero Data, Zero Calc.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _copy(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))


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


def build_procedure(tickets_doc=None, extra=None):
    """Volet (a). Trous declares, jamais inventes."""
    tickets_doc = tickets_doc or {}
    extra = extra or {}
    tickets = tickets_doc.get("tickets") or []
    warnings = list(tickets_doc.get("warnings") or [])
    regles = tickets_doc.get("regles") or {}
    holes = list(extra.get("holes") or [])

    for t in tickets:
        holes.extend(t.get("holes") or [])
        for j in t.get("jambes") or []:
            holes.extend(j.get("holes") or [])

    checks = list(extra.get("checks") or [])
    if not checks:
        checks = ["freeze_lot", "snapshot_t0"]
    for t in tickets:
        for j in t.get("jambes") or []:
            if j.get("devig_gap") is not None:
                if "devig_gap" not in checks:
                    checks.append("devig_gap")
                break
        else:
            continue
        break

    seuils = extra.get("seuils")
    if seuils is None:
        seuils = {}
        if "seuil_ev" in regles:
            seuils["ev"] = regles.get("seuil_ev")
        if "bonus_seuil_ev" in regles:
            seuils["bonus_ev"] = regles.get("bonus_seuil_ev")
        if not seuils:
            holes.append("seuils")
            seuils = None

    kelly = extra.get("kelly")
    if kelly is None:
        fracs = []
        for t in tickets:
            frac = t.get("kelly_fraction")
            if frac is None:
                frac = t.get("kelly")
            if frac is not None:
                fracs.append(frac)
        if fracs:
            kelly = {"fractions": fracs, "source": "tickets"}
        else:
            holes.append("kelly")
            kelly = None

    return {
        "attached_at": now_iso(),
        "checks": checks,
        "holes": _uniq(holes),
        "seuils": seuils,
        "kelly": kelly,
        "warnings": warnings,
        "regles": regles or None,
    }


def attach_procedure(lot, tickets_doc=None, procedure=None):
    """Pose le volet procedure. Refuse toute reecriture."""
    box = lot.setdefault("journal", {})
    if "procedure" in box:
        raise ValueError("procedure immutable")
    proc = procedure if procedure is not None else build_procedure(tickets_doc or {})
    box["procedure"] = _copy(proc)
    return lot


def build_outcome(lot):
    """Volet (b) depuis settle + snapshot T0. CLV absent = hole, pas 0."""
    settle = lot.get("settle") or {}
    snap = lot.get("snapshot_t0") or {}
    snap_tix = {t.get("rang_ticket"): t for t in snap.get("tickets") or []}
    out_tix = []
    holes = []
    pnl_sum = 0.0
    n_pnl = 0
    for t in settle.get("tickets") or []:
        rang = t.get("rang_ticket")
        src = snap_tix.get(rang) or {}
        clv = t.get("clv")
        if clv is None:
            clv = src.get("clv")
        rec = {
            "rang_ticket": rang,
            "mise_fc": src.get("mise_fc") if src.get("mise_fc") is not None else t.get("mise_fc"),
            "cote": src.get("cote_totale") if src.get("cote_totale") is not None else t.get("cote"),
            "resultat": t.get("resultat"),
            "pnl_fc": t.get("pnl_fc"),
        }
        if clv is None:
            rec["clv"] = None
            holes.append("clv")
        else:
            rec["clv"] = clv
        out_tix.append(rec)
        if t.get("pnl_fc") is not None:
            pnl_sum += float(t["pnl_fc"])
            n_pnl += 1
    return {
        "attached_at": now_iso(),
        "tickets": out_tix,
        "pnl_lot_fc": round(pnl_sum, 2) if n_pnl else None,
        "holes": _uniq(holes),
    }


def attach_outcome(lot):
    """Pose le volet outcome. Ne mute jamais procedure."""
    box = lot.setdefault("journal", {})
    frozen = json.dumps(box.get("procedure"), sort_keys=True, ensure_ascii=False)
    box["outcome"] = build_outcome(lot)
    after = json.dumps(box.get("procedure"), sort_keys=True, ensure_ascii=False)
    if frozen != after:
        raise RuntimeError("journal.procedure immutable")
    return lot
