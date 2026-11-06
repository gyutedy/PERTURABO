#!/usr/bin/env python3
"""
F06 LEDGER — lots tokenises (v2.2.8)
====================================
Token = cle (L-XXX), pas la date. Snapshot T0 a /valider-2.
Settle scores football-data.co.uk : G/P/EN_ATTENTE, jamais invente.
Journal 2 volets (S3) : procedure immutable a freeze, outcome au settle.
F06 n'apprend pas : pas d'ecriture calibration.json.
"""

from __future__ import annotations

import csv
import json
import os
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
LEARN = os.path.join(WORLD, "ARCHIVUM", "learnings")
LOTS_PATH = os.path.join(LEARN, "lots.json")
TICKETS_PATH = os.path.join(LEARN, "tickets.json")
ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_CAP_DIR = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
if _CAP_DIR not in sys.path:
    sys.path.insert(0, _CAP_DIR)


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_lots(path=None):
    p = path or LOTS_PATH
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"note": "LEDGER F06 lots — token = cle (L-XXX). F06 n'apprend pas.", "lots": []}


def save_lots(box, path=None):
    p = path or LOTS_PATH
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(box, f, indent=2, ensure_ascii=False)


def taken_tokens(box=None):
    box = box or load_lots()
    return {str(l.get("token") or "") for l in box.get("lots") or []}


def new_token(taken=None):
    taken = taken or taken_tokens()
    for _ in range(200):
        t = "L-" + "".join(secrets.choice(ALPH) for _ in range(3))
        if t not in taken:
            return t
    raise RuntimeError("token space exhausted")


def new_capture_id(taken=None):
    taken = taken or set()
    for _ in range(200):
        t = "C-" + "".join(secrets.choice(ALPH) for _ in range(3))
        if t not in taken:
            return t
    raise RuntimeError("capture id space exhausted")


def leg_key(match_id, marche, selection):
    return (str(match_id or ""), str(marche or ""), str(selection or ""))


def legs_from_tickets(tickets):
    out = []
    for t in tickets or []:
        for j in t.get("jambes") or []:
            out.append({
                "match_id": j.get("match_id"),
                "marche": j.get("marche") or "",
                "selection": j.get("selection"),
            })
    return out


def append_lot(lot, path=None):
    box = load_lots(path)
    box.setdefault("lots", []).append(lot)
    save_lots(box, path)
    return lot


def find_lot(token, path=None):
    box = load_lots(path)
    tok = str(token or "").strip().upper()
    if tok and not tok.startswith("L-"):
        tok = "L-" + tok
    for lot in box.get("lots") or []:
        if str(lot.get("token") or "").upper() == tok:
            return lot, box
    return None, box


def freeze_lot(token, campagne, capture_id, tickets_doc, consumed_legs, budget_fc, surticket_fc,
               bundle_id=None, procedure=None):
    snap_tickets = json.loads(json.dumps(tickets_doc.get("tickets") or []))
    snap_budget = json.loads(json.dumps(tickets_doc.get("budget") or {}))
    lot = {
        "token": token,
        "campagne": campagne,
        "capture_id": capture_id,
        "created_at": now_iso(),
        "status": "OUVERT",
        "budget_fc": budget_fc,
        "surticket_fc": surticket_fc,
        "alloue_fc": (tickets_doc.get("budget") or {}).get("alloue_fc") or 0,
        "consumed_legs": list(consumed_legs or []),
        "snapshot_t0": {
            "generated_at": tickets_doc.get("generated_at") or now_iso(),
            "tickets": snap_tickets,
            "budget": snap_budget,
        },
        "settle": {"settled_at": None, "source": "football-data.co.uk", "tickets": []},
    }
    if bundle_id:
        lot["bundle_id"] = bundle_id
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    import journal as _journal
    _journal.attach_procedure(lot, tickets_doc, procedure=procedure)
    return lot


def _team_key(name):
    try:
        import capteurs
        return capteurs.team_key(name or "")
    except Exception:
        return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def split_match(label):
    raw = label or ""
    for sep in (" vs ", " v ", " - "):
        if sep in raw:
            a, b = raw.split(sep, 1)
            return a.strip(), b.strip()
    return raw.strip(), ""


def load_csv_rows(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def _row_teams(row):
    home = row.get("HomeTeam") or row.get("Home") or ""
    away = row.get("AwayTeam") or row.get("Away") or ""
    return home, away


def find_csv_row(dom, ext, rows):
    kd, ke = _team_key(dom), _team_key(ext)
    if not kd or not ke:
        return None
    best = None
    for row in rows:
        h, a = _row_teams(row)
        kh, ka = _team_key(h), _team_key(a)
        if not kh or not ka:
            continue
        if kh == kd and ka == ke:
            return row
        if (kd in kh or kh in kd) and (ke in ka or ka in ke):
            best = row
    return best


def resolve_1x2(selection, selection_label, ftr):
    ftr = (ftr or "").strip().upper()
    sel = (selection or "").strip().upper()
    lab = (selection_label or "").lower()
    if not ftr:
        return None
    want = None
    if sel in ("1", "H", "DOM") or "victoire domicile" in lab or "home" in lab:
        want = "H"
    elif sel in ("2", "A", "EXT") or "victoire extérieur" in lab or "victoire exterieur" in lab or "away" in lab:
        want = "A"
    elif sel in ("X", "D", "NUL") or lab.strip() in ("nul", "draw", "égalité", "egalite"):
        want = "D"
    if want is None:
        return None
    return "G" if ftr == want else "P"


def load_close_map(odds_dir=None):
    """Cotes marche T-0 (latest_t0.json). T-2h n est PAS la cloture."""
    d = odds_dir or os.path.join(WORLD, "ARCHIVUM", "odds")
    p = os.path.join(d, "latest_t0.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for item in blob.get("scanned") or []:
        mid = item.get("id")
        cotes = item.get("cotes_marche") or {}
        if mid and isinstance(cotes, dict):
            out[str(mid)] = cotes
    return out


def close_for_jambe(jambe, close_map):
    """Cote cloture T-0. Absente / invalide → None, jamais 0."""
    mid = str((jambe or {}).get("match_id") or "")
    sel = (jambe or {}).get("selection")
    cotes = (close_map or {}).get(mid) or {}
    v = cotes.get(sel) if sel is not None else None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f <= 1:
        return None
    return f


def settle_leg(jambe, rows):
    """CSV hit → G/P ; marche non 1X2 ou match absent → EN_ATTENTE. Jamais invente."""
    dom, ext = split_match(jambe.get("match") or "")
    row = find_csv_row(dom, ext, rows)
    if not row:
        return "EN_ATTENTE"
    marche = (jambe.get("marche") or "1X2").upper()
    if marche not in ("1X2", "1N2", "HDA"):
        return "EN_ATTENTE"
    ftr = row.get("FTR") or ""
    got = resolve_1x2(jambe.get("selection"), jambe.get("selection_label"), ftr)
    if got is None:
        return "EN_ATTENTE"
    return got


def settle_lot(token, csv_path, lots_path=None, odds_dir=None):
    lot, box = find_lot(token, lots_path)
    if not lot:
        return None, "token inconnu : " + str(token)
    rows = load_csv_rows(csv_path)
    close_map = load_close_map(odds_dir)
    tickets_out = []
    for t in (lot.get("snapshot_t0") or {}).get("tickets") or []:
        jambes_out = []
        for j in t.get("jambes") or []:
            res = settle_leg(j, rows)
            jj = dict(j)
            jj["resultat"] = res
            close = close_for_jambe(j, close_map)
            if close is not None:
                jj["book_odds_close"] = close
            else:
                holes = list(jj.get("holes") or [])
                holes.append("book_odds_close")
                jj["holes"] = holes
            jambes_out.append(jj)
        results = [x["resultat"] for x in jambes_out]
        if any(r == "EN_ATTENTE" for r in results):
            tres = "EN_ATTENTE"
            pnl = None
        elif results and all(r == "G" for r in results):
            tres = "G"
            mise = float(t.get("mise_fc") or 0)
            cote = float(t.get("cote_totale") or 1)
            pnl = round(mise * (cote - 1), 2)
        else:
            tres = "P"
            pnl = round(-float(t.get("mise_fc") or 0), 2)
        tickets_out.append({
            "rang_ticket": t.get("rang_ticket"),
            "resultat": tres,
            "pnl_fc": pnl,
            "jambes": jambes_out,
        })
    lot["settle"] = {
        "settled_at": now_iso(),
        "source": csv_path or "football-data.co.uk",
        "tickets": tickets_out,
    }
    if tickets_out and all(t["resultat"] != "EN_ATTENTE" for t in tickets_out):
        lot["status"] = "SETTLE"
    elif any(t["resultat"] != "EN_ATTENTE" for t in tickets_out):
        lot["status"] = "SETTLE_PARTIEL"
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    import clv as _clv
    snap_map = {
        t.get("rang_ticket"): t
        for t in (lot.get("snapshot_t0") or {}).get("tickets") or []
    }
    ratios = []
    mises = []
    for t in tickets_out:
        src = snap_map.get(t.get("rang_ticket")) or {}
        ratio = _clv.ticket_clv(src, t)
        if ratio is None:
            holes = list(t.get("holes") or [])
            if "clv" not in holes:
                holes.append("clv")
            t["holes"] = holes
            t["clv"] = None
        else:
            t["clv"] = ratio
            ratios.append(ratio)
            mises.append(src.get("mise_fc") if src.get("mise_fc") is not None else t.get("mise_fc"))
    agg = _clv.aggregate(ratios, mises)
    lot["settle"]["clv"] = agg
    if agg.get("median") is not None:
        lot["settle"]["clv_median"] = agg["median"]
    import journal as _journal
    _journal.attach_outcome(lot)
    save_lots(box, lots_path)
    return lot, None


def format_settle(lot):
    tok = lot.get("token")
    lines = ["SETTLE **" + tok + "** · " + (lot.get("status") or "")]
    pnl_sum = 0
    n_pnl = 0
    for t in (lot.get("settle") or {}).get("tickets") or []:
        pnl = t.get("pnl_fc")
        extra = ""
        if pnl is not None:
            extra = f" · PnL {pnl:+.0f} FC"
            pnl_sum += pnl
            n_pnl += 1
        lines.append(f"T${t.get('rang_ticket')} {t.get('resultat')}{extra}")
        for j in t.get("jambes") or []:
            close = j.get("book_odds_close")
            close_s = f" close {close}" if close is not None else " close trou"
            lines.append(
                f"  {j.get('match')} ({j.get('selection_label') or j.get('selection')})"
                f" → {j.get('resultat')}{close_s}"
            )
    if n_pnl:
        lines.append(f"PnL lot : **{pnl_sum:+.0f} FC**")
    lines.append("F06 n'apprend pas.")
    return "\n".join(lines)


def format_lots(box, campagne=None, consumed=None):
    lots = box.get("lots") or []
    if campagne:
        lots = [l for l in lots if l.get("campagne") == campagne]
    if not lots:
        return "Aucun lot F06." + (" Campagne " + campagne if campagne else "")
    lines = ["LEDGER F06 · " + str(len(lots)) + " lot(s)"]
    for l in lots:
        n = len((l.get("snapshot_t0") or {}).get("tickets") or [])
        lines.append(
            f"  {l.get('token')} [{l.get('status')}] {n} ticket(s) · "
            f"budget {l.get('budget_fc') or 0:.0f} FC · capture {l.get('capture_id')}"
        )
    if consumed:
        lines.append("Jambes consommees (capture) :")
        for c in consumed:
            lines.append(f"  {c.get('match_id')} {c.get('marche')} {c.get('selection')}")
    return "\n".join(lines)
