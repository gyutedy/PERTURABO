#!/usr/bin/env python3
"""
MARKET SCORER — eligibilite F03 (S12 / v4.2) + pieges S14
=========================================================
Portes A1-A4 binaires hors score. Score B1-B6 dans [0, 1].
S14 : 3e lecture cotes (capture → T-2h → T-0 close). Detecteurs
cote_plate / marge_anomalique / cote_figee_sur_news / marche_vitrine.
Jamais un producteur de p. Poisson F02 inchange. HERALD inchange.
Trou data → score reduit + holes. Stdlib only.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
PROFILES_PATH = os.path.join(WORLD, "ARCHIVUM", "learnings", "market_profiles.json")

KEYS = ("B1", "B2", "B3", "B4", "B5", "B6")
GATES = ("A1", "A2", "A3", "A4")

DEFAULT_POIDS = {
    "B1": 0.30,
    "B2": 0.20,
    "B3": 0.20,
    "B4": 0.15,
    "B5": 0.10,
    "B6": 0.05,
}
DEFAULT_SEUIL = 0.50
OVERROUND_MAX = 0.20
COTE_MIN = 1.10
MARGE_ANOMALIQUE = 0.10
FIGEE_MOVE = 0.01
B3_MOVE = 0.03
CRITERES_LABELS = {
    "B1": "edge",
    "B2": "bande",
    "B3": "info",
    "B4": "data",
    "B5": "marge",
    "B6": "confirm",
}

GROUP_KEYS = {
    "1X2": ("1", "X", "2"),
    "OU_0.5": ("o0.5", "u0.5"),
    "OU_1.5": ("o1.5", "u1.5"),
    "OU_2.5": ("o2.5", "u2.5"),
    "OU_3.5": ("o3.5", "u3.5"),
    "OU_4.5": ("o4.5", "u4.5"),
    "DC": ("dc_1x", "dc_x2", "dc_12"),
    "TT_H_0.5": ("tt_h_o0.5", "tt_h_u0.5"),
    "TT_H_1.5": ("tt_h_o1.5", "tt_h_u1.5"),
    "TT_H_2.5": ("tt_h_o2.5", "tt_h_u2.5"),
    "TT_A_0.5": ("tt_a_o0.5", "tt_a_u0.5"),
    "TT_A_1.5": ("tt_a_o1.5", "tt_a_u1.5"),
    "TT_A_2.5": ("tt_a_o2.5", "tt_a_u2.5"),
    "MT_PROLIFIQUE": ("mt1", "mte", "mt2"),
    "BTTS": ("btts", "btts_no"),
}


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


def load_profiles(path=None):
    p = path or PROFILES_PATH
    blob = {}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                blob = raw
        except (OSError, json.JSONDecodeError):
            blob = {}
    default = blob.get("default") if isinstance(blob.get("default"), dict) else {}
    poids = dict(DEFAULT_POIDS)
    src = default.get("poids") if isinstance(default.get("poids"), dict) else {}
    for k in KEYS:
        if k in src:
            fv = _f(src[k])
            if fv is not None:
                poids[k] = fv
    seuil = _f(default.get("seuil"))
    if seuil is None:
        seuil = DEFAULT_SEUIL
    ov_max = _f(blob.get("overround_max"))
    if ov_max is None:
        ov_max = OVERROUND_MAX
    cote_min = _f(blob.get("cote_min"))
    if cote_min is None:
        cote_min = COTE_MIN
    marches = blob.get("marches") if isinstance(blob.get("marches"), dict) else {}
    return {
        "version": blob.get("version", 1),
        "overround_max": ov_max,
        "cote_min": cote_min,
        "default": {"seuil": seuil, "poids": poids},
        "marches": marches,
        "path": p,
    }


def profile_for(marche, profiles=None):
    profiles = profiles or load_profiles()
    base_poids = dict(profiles["default"]["poids"])
    base_seuil = float(profiles["default"]["seuil"])
    rec = (profiles.get("marches") or {}).get(marche) or {}
    if not isinstance(rec, dict):
        rec = {}
    poids = dict(base_poids)
    src = rec.get("poids") if isinstance(rec.get("poids"), dict) else {}
    for k in KEYS:
        if k in src:
            fv = _f(src[k])
            if fv is not None:
                poids[k] = fv
    seuil = _f(rec.get("seuil"))
    if seuil is None:
        seuil = base_seuil
    return {
        "marche": marche,
        "seuil": seuil,
        "poids": poids,
        "overround_max": float(profiles["overround_max"]),
        "cote_min": float(profiles["cote_min"]),
    }


def overround(cotes):
    present = {}
    for k, v in (cotes or {}).items():
        fv = _f(v)
        if fv is None or fv <= 1:
            continue
        present[str(k)] = fv
    if len(present) < 2:
        return None
    return sum(1.0 / v for v in present.values()) - 1.0


def _present(cotes):
    out = {}
    for k, v in (cotes or {}).items():
        fv = _f(v)
        if fv is None or fv <= 1:
            continue
        out[str(k)] = fv
    return out


def gate_a1(marche, group_cotes, selection=None):
    keys = GROUP_KEYS.get(marche)
    present = _present(group_cotes)
    if keys:
        missing = [k for k in keys if k not in present]
        return (len(missing) == 0, missing)
    if selection is None:
        return (len(present) >= 1, [] if present else ["groupe"])
    sel = str(selection)
    ok = sel in present or len(present) >= 1
    return (ok, [] if ok else [sel])


def gate_a2(cote, cote_min=COTE_MIN):
    fv = _f(cote)
    if fv is None:
        return False
    return fv >= float(cote_min)


def gate_a3(analysis):
    dq = (analysis or {}).get("data_quality") or {}
    flags = list(dq.get("flags") or [])
    niveau = dq.get("niveau")
    if "mj_insuffisant" in flags:
        return False
    if niveau == "basse":
        return False
    return True


def gate_a4(group_cotes, overround_max=OVERROUND_MAX):
    ov = overround(group_cotes)
    if ov is None:
        return True, None
    return ov <= float(overround_max), ov


def detect_cote_plate(match=None, extra=None):
    """Flag parseur S1 : 3 cotes MT identiques sur >= 5 matchs. Cotes conservees."""
    extra = extra or {}
    if extra.get("cote_plate") is True:
        return True
    m = match or extra.get("match") or {}
    return bool(m.get("cote_plate"))


def detect_marge_anomalique(group_cotes, seuil=MARGE_ANOMALIQUE):
    """B5 : overround > 10% = marge anomalique (info). A4 reste a 20%."""
    ov = overround(group_cotes)
    if ov is None:
        return False, None
    return ov > float(seuil), ov


def detect_marche_vitrine(group_cotes, overround_max=OVERROUND_MAX):
    """A4 : overround > 20% = marche vitrine, refuse hors score."""
    a4_ok, ov = gate_a4(group_cotes, overround_max)
    return (not a4_ok), ov


def _cote_from(blob, sel):
    if not isinstance(blob, dict):
        return None
    if sel is None:
        return None
    return _f(blob.get(sel))


def detect_cote_figee_sur_news(cote, extra=None, selection=None):
    """B3 : capture vs T-2h figee (|move| < 1%) alors que notes OUT existent."""
    extra = extra or {}
    t2h = _f(extra.get("cote_t2h"))
    if t2h is None:
        t2h = _f(extra.get("odds_t2h"))
    if t2h is None and selection is not None:
        blob = extra.get("odds_t2h_blob") or extra.get("cotes_t2h") or {}
        t2h = _cote_from(blob, selection)
    fv = _f(cote)
    if t2h is None or t2h <= 1 or fv is None:
        return False
    move = abs(fv - t2h) / t2h
    if move >= FIGEE_MOVE:
        return False
    notes_out = extra.get("notes_out")
    if notes_out is None:
        notes_out = extra.get("out_n")
    try:
        n_out = int(notes_out or 0)
    except (TypeError, ValueError):
        n_out = 0
    return n_out >= 1


def lecture_cotes(cote, extra=None, selection=None):
    """3e lecture : T-0 capture → T-2h → T-0 close. Trou = None, jamais 0."""
    extra = extra or {}
    cap = _f(cote)
    t2h = _f(extra.get("cote_t2h"))
    if t2h is None:
        t2h = _f(extra.get("odds_t2h"))
    if t2h is None and selection is not None:
        t2h = _cote_from(extra.get("odds_t2h_blob") or extra.get("cotes_t2h") or {}, selection)
    close = _f(extra.get("cote_t0"))
    if close is None:
        close = _f(extra.get("cote_close"))
    if close is None and selection is not None:
        close = _cote_from(extra.get("odds_t0_blob") or extra.get("cotes_t0") or {}, selection)
    move_t2h = None
    if cap is not None and t2h is not None and t2h > 1:
        move_t2h = (cap - t2h) / t2h
    move_close = None
    if cap is not None and close is not None and close > 1:
        move_close = (cap - close) / close
    return {
        "capture": cap,
        "t2h": t2h,
        "t0": close,
        "move_t2h": round(move_t2h, 6) if move_t2h is not None else None,
        "move_t0": round(move_close, 6) if move_close is not None else None,
    }


def pieges(selection, cote, marche, group_cotes, extra=None, match=None, overround_max=OVERROUND_MAX):
    extra = extra or {}
    plate = detect_cote_plate(match=match, extra=extra)
    anom, ov = detect_marge_anomalique(group_cotes)
    vitrine, ov_v = detect_marche_vitrine(group_cotes, overround_max)
    figee = detect_cote_figee_sur_news(cote, extra=extra, selection=selection)
    lect = lecture_cotes(cote, extra=extra, selection=selection)
    flags = []
    if plate:
        flags.append("cote_plate")
    if anom:
        flags.append("marge_anomalique")
    if figee:
        flags.append("cote_figee_sur_news")
    if vitrine:
        flags.append("marche_vitrine")
    return {
        "cote_plate": plate,
        "marge_anomalique": anom,
        "cote_figee_sur_news": figee,
        "marche_vitrine": vitrine,
        "flags": flags,
        "overround": round(ov, 6) if ov is not None else (round(ov_v, 6) if ov_v is not None else None),
        "lecture": lect,
    }


def format_criteres(scored):
    """6 criteres B1-B6 + flags pieges. Affichage, jamais un p."""
    scored = scored or {}
    contrib = scored.get("contrib") or {}
    bits = []
    for k in KEYS:
        raw = (contrib.get(k) or {}).get("raw")
        label = CRITERES_LABELS.get(k, k)
        if raw is None:
            bits.append(f"{label} —")
        else:
            bits.append(f"{label} {raw:.2f}")
    score = scored.get("score")
    seuil = scored.get("seuil")
    elig = scored.get("eligible")
    head = "SCORER —"
    if score is not None:
        head = f"SCORER {score:.2f}"
        if seuil is not None:
            head += f"/{seuil:.2f}"
        if elig is True:
            head += " GO"
        elif elig is False:
            head += " NO"
    refuse = scored.get("scorer_refuse") or scored.get("refuse") or []
    if refuse:
        head += " A:" + ",".join(str(x) for x in refuse)
    piege_flags = list(scored.get("pieges") or [])
    if not piege_flags and scored.get("piege_flags"):
        piege_flags = list(scored.get("piege_flags"))
    line = head + "  " + " ".join(bits)
    if piege_flags:
        line += "  PIEGES " + ",".join(piege_flags)
    return line


def _b1(extra, holes):
    p = _f((extra or {}).get("p_modele"))
    cote = _f((extra or {}).get("cote"))
    ev = _f((extra or {}).get("ev"))
    if ev is None:
        if p is None or cote is None:
            holes.append("b1_modele")
            return 0.0
        ev = p * cote - 1.0
    if ev >= 0.03:
        return 1.0
    if ev > 0:
        return 0.5
    return 0.0


def _b2(cote, holes):
    fv = _f(cote)
    if fv is None:
        holes.append("b2_cote")
        return 0.0
    if 1.40 <= fv <= 3.20:
        return 1.0
    if 1.20 <= fv < 1.40 or 3.20 < fv <= 5.0:
        return 0.5
    if fv >= 1.10:
        return 0.25
    return 0.0


def _b3(extra, cote, holes):
    lect = lecture_cotes(cote, extra=extra)
    fv = lect.get("capture")
    if fv is None:
        holes.append("b3_asymetrie")
        return 0.0
    ref = lect.get("t2h")
    if ref is None or ref <= 1:
        ref = lect.get("t0")
    if ref is None or ref <= 1:
        holes.append("b3_asymetrie")
        return 0.0
    move = abs(fv - ref) / ref
    if move >= B3_MOVE:
        return 1.0
    return 0.4


def _b4(analysis, holes):
    dq = (analysis or {}).get("data_quality") or {}
    niveau = dq.get("niveau")
    if niveau == "haute":
        return 1.0
    if niveau == "moyenne":
        return 0.5
    if niveau == "basse":
        return 0.0
    holes.append("b4_qualite")
    return 0.0


def _b5(group_cotes, holes):
    ov = overround(group_cotes)
    if ov is None:
        holes.append("b5_marge")
        return 0.0
    if ov <= 0.06:
        return 1.0
    if ov <= 0.10:
        return 0.7
    if ov <= 0.15:
        return 0.4
    if ov <= 0.20:
        return 0.2
    return 0.0


def _b6(extra, holes):
    dc = (extra or {}).get("double_confirmation")
    if dc is True:
        return 1.0
    if dc is False:
        return 0.3
    holes.append("b6_confirmation")
    return 0.0


def score(selection, cote, marche, group_cotes, analysis=None, extra=None, profiles=None):
    """Eligibilite d une selection. EV / p_modele inchanges (lus, jamais ecrits)."""
    profiles = profiles or load_profiles()
    prof = profile_for(marche, profiles)
    extra = dict(extra or {})
    extra.setdefault("cote", cote)
    holes = []
    a1_ok, a1_missing = gate_a1(marche, group_cotes, selection)
    a2_ok = gate_a2(cote, prof["cote_min"])
    a3_ok = gate_a3(analysis)
    a4_ok, ov = gate_a4(group_cotes, prof["overround_max"])
    if not a1_ok:
        holes.append("a1_groupe")
        for k in a1_missing:
            holes.append("a1:" + str(k))
    if not a2_ok:
        holes.append("a2_praticable")
    if not a3_ok:
        holes.append("a3_historique")
    if not a4_ok:
        holes.append("a4_vitrine")
    gates = {"A1": a1_ok, "A2": a2_ok, "A3": a3_ok, "A4": a4_ok}
    refuse = [g for g in GATES if not gates[g]]

    raw = {
        "B1": _b1(extra, holes),
        "B2": _b2(cote, holes),
        "B3": _b3(extra, cote, holes),
        "B4": _b4(analysis, holes),
        "B5": _b5(group_cotes, holes),
        "B6": _b6(extra, holes),
    }
    poids = prof["poids"]
    contrib = {}
    total = 0.0
    for k in KEYS:
        w = float(poids[k])
        r = float(raw[k])
        c = w * r
        contrib[k] = {"poids": w, "raw": round(r, 4), "contrib": round(c, 6)}
        total += c
    if total < 0:
        total = 0.0
    if total > 1:
        total = 1.0
    gates_ok = len(refuse) == 0
    eligible = bool(gates_ok and total >= float(prof["seuil"]))
    trap = pieges(
        selection, cote, marche, group_cotes,
        extra=extra, match=extra.get("match"),
        overround_max=prof["overround_max"],
    )
    return {
        "eligible": eligible,
        "score": round(total, 4),
        "seuil": float(prof["seuil"]),
        "marche": marche,
        "selection": selection,
        "gates": gates,
        "refuse": refuse,
        "contrib": contrib,
        "overround": round(ov, 6) if ov is not None else None,
        "holes": _uniq(holes),
        "pieges": trap["flags"],
        "piege_detail": {
            "cote_plate": trap["cote_plate"],
            "marge_anomalique": trap["marge_anomalique"],
            "cote_figee_sur_news": trap["cote_figee_sur_news"],
            "marche_vitrine": trap["marche_vitrine"],
        },
        "lecture_cotes": trap["lecture"],
    }
