"""S11 — election marches, couverture, anti meme-navire.

Canon Telegram : /marches (ASCII). Alias /marchés si Telegram garde l accent.
EV_FLOOR 0.03 inviolable. EV combo plancher 0.05. Jamais jambe de remplissage.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

EV_FLOOR = 0.03
EV_COMBO_FLOOR = 0.05
CONCENTRATION_ALERTE = 0.60
TANK_P = 0.55

_HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(_HERE, "..", ".."))
LOG_PATH = os.path.join(WORLD, "ARCHIVUM", "learnings", "market_election_log.json")

ALIASES = {
    "1x2": "1X2",
    "1n2": "1X2",
    "h2h": "1X2",
    "o/u0.5": "OU_0.5",
    "ou0.5": "OU_0.5",
    "ou_0.5": "OU_0.5",
    "o0.5": "OU_0.5",
    "u0.5": "OU_0.5",
    "o/u1.5": "OU_1.5",
    "ou1.5": "OU_1.5",
    "ou_1.5": "OU_1.5",
    "o1.5": "OU_1.5",
    "u1.5": "OU_1.5",
    "o/u2.5": "OU_2.5",
    "ou2.5": "OU_2.5",
    "ou_2.5": "OU_2.5",
    "o2.5": "OU_2.5",
    "u2.5": "OU_2.5",
    "over": "OU_2.5",
    "under": "OU_2.5",
    "o/u3.5": "OU_3.5",
    "ou3.5": "OU_3.5",
    "ou_3.5": "OU_3.5",
    "o3.5": "OU_3.5",
    "u3.5": "OU_3.5",
    "o/u4.5": "OU_4.5",
    "ou4.5": "OU_4.5",
    "ou_4.5": "OU_4.5",
    "o4.5": "OU_4.5",
    "u4.5": "OU_4.5",
    "mt2": "MT_PROLIFIQUE",
    "mt": "MT_PROLIFIQUE",
    "mt1": "MT_PROLIFIQUE",
    "mte": "MT_PROLIFIQUE",
    "mt_prolifique": "MT_PROLIFIQUE",
    "btts": "BTTS",
    "dc": "DC",
    "cs": "CS",
    "tt": "TT_H_2.5",
}


def _norm_token(raw):
    s = (raw or "").strip().lower()
    s = s.replace(" ", "")
    s = s.replace("é", "e").replace("è", "e")
    return s


def canon_marche(raw):
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = _norm_token(s)
    if key in ALIASES:
        return ALIASES[key]
    compact = key.replace("-", "_")
    if compact in ALIASES:
        return ALIASES[compact]
    known = {
        "1x2": "1X2",
        "ou_0.5": "OU_0.5",
        "ou_1.5": "OU_1.5",
        "ou_2.5": "OU_2.5",
        "ou_3.5": "OU_3.5",
        "ou_4.5": "OU_4.5",
        "mt_prolifique": "MT_PROLIFIQUE",
        "btts": "BTTS",
        "dc": "DC",
        "cs": "CS",
    }
    if compact in known:
        return known[compact]
    if s in ("1X2", "OU_0.5", "OU_1.5", "OU_2.5", "OU_3.5", "OU_4.5",
             "MT_PROLIFIQUE", "BTTS", "DC", "CS",
             "TT_H_0.5", "TT_H_1.5", "TT_H_2.5",
             "TT_A_0.5", "TT_A_1.5", "TT_A_2.5"):
        return s
    return s.upper().replace("/", "_").replace("-", "_")


def parse_marches_arg(text):
    """Parse 'O/U2.5,MT2 mono' → (canons, mono, inconnus)."""
    raw = (text or "").strip()
    if not raw:
        return [], False, []
    bits = []
    for chunk in raw.replace(";", ",").split(","):
        bits.extend(chunk.split())
    mono = False
    tokens = []
    for b in bits:
        key = _norm_token(b)
        if key in ("mono", "mono-marche", "monomarche"):
            mono = True
            continue
        tokens.append(b)
    canons = []
    inconnus = []
    seen = set()
    for t in tokens:
        c = canon_marche(t)
        if not c:
            inconnus.append(t)
            continue
        if c in seen:
            continue
        seen.add(c)
        canons.append(c)
    return canons, mono, inconnus


def x_de_tank(top):
    """X 1X2 sous un favori p_fav >= TANK_P. p_fav manquant = pas tank (legacy)."""
    if not top:
        return False
    if str(top.get("selection") or "") != "X":
        return False
    m = canon_marche(top.get("marche"))
    if m and m != "1X2":
        return False
    pf = top.get("p_fav")
    if pf is None:
        return False
    try:
        return float(pf) >= TANK_P
    except (TypeError, ValueError):
        return False


def jambe_jouable(top):
    if not top:
        return False
    v = top.get("verdict")
    if v is not None and v != "VALUE":
        return False
    if top.get("scorer_eligible") is False:
        return False
    if x_de_tank(top) and top.get("vestiaire_ok") is not True:
        return False
    return True


def _eligible_top(event, ev_floor=EV_FLOOR):
    if event.get("no_bet_recommande") or event.get("bucket") == "FAIBLE":
        return []
    out = []
    for top in event.get("top3") or []:
        if not jambe_jouable(top):
            continue
        ev = top.get("ev")
        if ev is None:
            continue
        try:
            evf = float(ev)
        except (TypeError, ValueError):
            continue
        if evf < ev_floor:
            continue
        out.append(top)
    return out


def coverage_rows(top3, ev_floor=EV_FLOOR):
    """Par marche : n matchs au-dessus du seuil, meilleur EV, marge (trou si absente)."""
    matchs = (top3 or {}).get("matchs") if isinstance(top3, dict) else (top3 or [])
    if isinstance(top3, dict):
        matchs = top3.get("matchs") or []
    acc = {}
    for e in matchs:
        seen_m = set()
        for top in _eligible_top(e, ev_floor=ev_floor):
            m = canon_marche(top.get("marche"))
            if not m:
                continue
            rec = acc.setdefault(m, {"marche": m, "n": 0, "best_ev": None, "marges": []})
            if m not in seen_m:
                rec["n"] += 1
                seen_m.add(m)
            ev = float(top.get("ev") or 0)
            if rec["best_ev"] is None or ev > rec["best_ev"]:
                rec["best_ev"] = ev
            marge = top.get("overround")
            if marge is None:
                marge = top.get("marge")
            if marge is not None:
                try:
                    rec["marges"].append(float(marge))
                except (TypeError, ValueError):
                    pass
    rows = []
    for m, rec in sorted(acc.items(), key=lambda kv: (-kv[1]["n"], -(kv[1]["best_ev"] or 0), kv[0])):
        marges = rec["marges"]
        rows.append({
            "marche": m,
            "n": rec["n"],
            "best_ev": rec["best_ev"],
            "marge": (sum(marges) / len(marges)) if marges else None,
        })
    return rows


def coverage_n(top3, markets, ev_floor=EV_FLOOR):
    wanted = {canon_marche(m) for m in (markets or [])}
    n = 0
    matchs = (top3 or {}).get("matchs") if isinstance(top3, dict) else (top3 or [])
    if isinstance(top3, dict):
        matchs = top3.get("matchs") or []
    for e in matchs:
        for top in _eligible_top(e, ev_floor=ev_floor):
            if not wanted or canon_marche(top.get("marche")) in wanted:
                n += 1
                break
    return n


def format_coverage(top3, markets=None, ev_floor=EV_FLOOR):
    rows = coverage_rows(top3, ev_floor=ev_floor)
    wanted = {canon_marche(m) for m in markets} if markets else None
    lines = ["COUVERTURE (VALUE F03)", "Marche          n  meilleur EV  marge"]
    shown = 0
    total_n = 0
    for r in rows:
        if wanted is not None and r["marche"] not in wanted:
            continue
        shown += 1
        total_n += r["n"]
        evs = f"+{r['best_ev'] * 100:.1f}%" if r["best_ev"] is not None else "—"
        mg = f"{r['marge'] * 100:.1f}%" if r["marge"] is not None else "—"
        lines.append(f"{r['marche']:<14} {r['n']:>2}  {evs:>11}  {mg}")
    if shown == 0:
        lines.append("(aucun marche au-dessus du seuil)")
    if total_n == 0:
        lines.append("0 match → 0 ticket.")
    return "\n".join(lines)


def filter_events(events, markets, ev_floor=EV_FLOOR):
    """Garde les top elus, tri EV desc. markets=[] → pool vide. markets=None → pas de filtre marche."""
    if markets is not None and not markets:
        return []
    wanted = {canon_marche(m) for m in markets} if markets is not None else None
    out = []
    for e in events or []:
        if e.get("no_bet_recommande") or e.get("bucket") == "FAIBLE":
            continue
        tops = []
        for top in e.get("top3") or []:
            if wanted is not None and canon_marche(top.get("marche")) not in wanted:
                continue
            if not jambe_jouable(top):
                continue
            ev = top.get("ev")
            if ev is None:
                continue
            try:
                if float(ev) < ev_floor:
                    continue
            except (TypeError, ValueError):
                continue
            tops.append(top)
        tops.sort(key=lambda t: -float(t.get("ev") or 0))
        if not tops:
            continue
        e2 = dict(e)
        e2["top3"] = tops
        out.append(e2)
    out.sort(key=lambda e: -float((e.get("top3") or [{}])[0].get("ev") or 0))
    return out


def combo_ev(sel_list):
    v = 1.0
    n = 0
    for s in sel_list or []:
        ev = s.get("ev")
        if ev is None:
            continue
        try:
            v *= (1.0 + float(ev))
            n += 1
        except (TypeError, ValueError):
            continue
    if n == 0:
        return None
    return v - 1.0


def refuse_floor(ev_floor):
    if ev_floor is None:
        return False
    try:
        return float(ev_floor) < EV_FLOOR - 1e-12
    except (TypeError, ValueError):
        return True


def jambes_cap(jbt, n_plus=10):
    n_req = max(jbt) if jbt else 1
    return max(1, int(n_req) + int(n_plus))


def load_log(path=None):
    p = path or LOG_PATH
    if not os.path.exists(p):
        return {"elections": []}
    try:
        with open(p, encoding="utf-8") as f:
            blob = json.load(f)
        if isinstance(blob, dict) and isinstance(blob.get("elections"), list):
            return blob
        if isinstance(blob, list):
            return {"elections": blob}
    except (OSError, json.JSONDecodeError):
        pass
    return {"elections": []}


def append_election(marches, campagne=None, mono=False, path=None, ts=None):
    p = path or LOG_PATH
    blob = load_log(p)
    rec = {
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campagne": campagne,
        "marches": list(marches or []),
        "mono": bool(mono),
    }
    blob.setdefault("elections", []).append(rec)
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
    return rec


def concentration(path=None, log=None):
    blob = log if log is not None else load_log(path)
    counts = {}
    total = 0
    for rec in blob.get("elections") or []:
        for m in rec.get("marches") or []:
            c = canon_marche(m)
            counts[c] = counts.get(c, 0) + 1
            total += 1
    if total <= 0:
        return {"ok": True, "total": 0, "max_marche": None, "share": 0.0, "alerte": False}
    max_m = max(counts, key=counts.get)
    share = counts[max_m] / total
    return {
        "ok": True,
        "total": total,
        "max_marche": max_m,
        "share": share,
        "counts": counts,
        "alerte": share > CONCENTRATION_ALERTE,
    }
