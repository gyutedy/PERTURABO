"""
F02 STATE FACTORS — S13 facteurs etat lambda (table operateur).
================================================================
Table A collée dans le même `/capture`. Jamais un 2e facteur via API (S15).
Vide = x1.00 + holes. Cap cumulé ±20%, journalisé.
rotation_lourde (>=4) : pas de lambda ; flag TYRANT.
Derby / meteo / retour_100 : veto marches_exclus seulement.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))

_CONFIG_CACHE = None

_TRUE = {"1", "oui", "yes", "true", "o", "y", "x"}
_FALSE = {"0", "non", "no", "false", "n", ""}


def _cfg_path():
    return os.path.join(WORLD, "config", "state_factors.json")


def load_config(path=None):
    global _CONFIG_CACHE
    if path is None and _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    p = path or _cfg_path()
    defaults = {
        "att_per_unit": 0.90,
        "att_max_units": 2,
        "milieu": 0.96,
        "def_adverse_per_unit": 1.06,
        "gardien_adverse": 1.05,
        "cap": [0.8, 1.2],
        "rotation_lourde_min": 4,
        "marches_exclus": {
            "derby": ["o2.5", "o3.5", "btts"],
            "meteo": ["o2.5", "o3.5", "btts"],
            "retour_100": ["mt1", "mte", "mt2"],
        },
    }
    if p and os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                blob = json.load(f)
            if isinstance(blob, dict):
                defaults.update(blob)
        except (OSError, json.JSONDecodeError):
            pass
    if path is None:
        _CONFIG_CACHE = defaults
    return defaults


def _as_int(val, default=0):
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().lower().replace(",", ".")
    if s in _FALSE:
        return 0
    if s in _TRUE:
        return 1
    try:
        return int(float(s))
    except ValueError:
        return default


def _as_bool(val):
    if val is None or val == "":
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    s = str(val).strip().lower()
    if s in _FALSE:
        return False
    return s in _TRUE


def _side(effectifs, side):
    rec = (effectifs or {}).get(side) or {}
    return rec if isinstance(rec, dict) else {}


def _clip(factor, lo, hi):
    if factor < lo:
        return lo, True, factor
    if factor > hi:
        return hi, True, factor
    return factor, False, factor


def _factor_for(own, opp, cfg, journal, side):
    f = 1.0
    n_att = min(_as_int(own.get("attaquants_titulaires_absents"), 0), int(cfg.get("att_max_units") or 2))
    if n_att:
        unit = float(cfg.get("att_per_unit") or 0.90)
        chunk = unit ** n_att
        f *= chunk
        journal.append(f"{side} att x{chunk:.4f} ({n_att}u)")
    if _as_bool(own.get("milieu_createur_absent")):
        mil = float(cfg.get("milieu") or 0.96)
        f *= mil
        journal.append(f"{side} milieu x{mil:.4f}")
    n_def = _as_int(opp.get("defenseurs_cles_absents"), 0)
    if n_def:
        unit = float(cfg.get("def_adverse_per_unit") or 1.06)
        chunk = unit ** n_def
        f *= chunk
        journal.append(f"{side} def_adverse x{chunk:.4f} ({n_def}u)")
    if _as_bool(opp.get("gardien_1_absent")):
        gk = float(cfg.get("gardien_adverse") or 1.05)
        f *= gk
        journal.append(f"{side} gardien_adverse x{gk:.4f}")
    return f


def apply(match, lambda_dom, lambda_ext, cfg=None):
    """Ajuste lambdas. Ne touche pas data_quality. Vide = x1.00 + holes."""
    cfg = cfg or load_config()
    cap = cfg.get("cap") or [0.8, 1.2]
    lo, hi = float(cap[0]), float(cap[1])
    raw_d, raw_e = lambda_dom, lambda_ext
    eff = (match or {}).get("effectifs") if isinstance(match, dict) else None
    empty = (not eff) or (not isinstance(eff, dict)) or (not eff.get("dom") and not eff.get("ext"))
    if empty:
        return {
            "lambda_dom": raw_d,
            "lambda_ext": raw_e,
            "lambda_dom_raw": raw_d,
            "lambda_ext_raw": raw_e,
            "factor_dom": 1.0,
            "factor_ext": 1.0,
            "applied": False,
            "flags": [],
            "holes": ["effectifs"],
            "cap_hit": False,
            "journal": [],
        }
    dom = _side(eff, "dom")
    ext = _side(eff, "ext")
    holes = []
    if not dom:
        holes.append("effectifs_dom")
    if not ext:
        holes.append("effectifs_ext")
    journal = []
    f_d = _factor_for(dom, ext, cfg, journal, "dom")
    f_e = _factor_for(ext, dom, cfg, journal, "ext")
    f_d, hit_d, pre_d = _clip(f_d, lo, hi)
    f_e, hit_e, pre_e = _clip(f_e, lo, hi)
    cap_hit = hit_d or hit_e
    flags = []
    if cap_hit:
        flags.append("cap_hit")
        if hit_d:
            journal.append(f"cap_hit dom {pre_d:.4f}->{f_d:.4f}")
        if hit_e:
            journal.append(f"cap_hit ext {pre_e:.4f}->{f_e:.4f}")
    rot_min = int(cfg.get("rotation_lourde_min") or 4)
    rot = max(_as_int(dom.get("rotation_lourde"), 0), _as_int(ext.get("rotation_lourde"), 0))
    if rot >= rot_min:
        flags.append("rotation_lourde")
        journal.append(f"rotation_lourde {rot} (pas de lambda)")
    if _as_bool(eff.get("derby")) or _as_bool(dom.get("derby")) or _as_bool(ext.get("derby")):
        flags.append("derby")
    if _as_bool(eff.get("meteo")) or _as_bool(dom.get("meteo")) or _as_bool(ext.get("meteo")):
        flags.append("meteo")
    if (_as_bool(eff.get("retour_100")) or _as_bool(dom.get("retour_100"))
            or _as_bool(ext.get("retour_100"))):
        flags.append("retour_100")
    return {
        "lambda_dom": raw_d * f_d,
        "lambda_ext": raw_e * f_e,
        "lambda_dom_raw": raw_d,
        "lambda_ext_raw": raw_e,
        "factor_dom": f_d,
        "factor_ext": f_e,
        "applied": True,
        "flags": flags,
        "holes": holes,
        "cap_hit": cap_hit,
        "journal": journal,
    }


def marches_exclus(flags, cfg=None):
    """Veto TYRANT. rotation_lourde / cap_hit ne sortent aucun marché."""
    cfg = cfg or load_config()
    vetoes = cfg.get("marches_exclus") or {}
    out = set()
    skip = {
        "rotation_lourde", "cap_hit",
        "buteur_manquant", "defenseur_manquant",
        "double_motivation", "satisfait_nul",
    }
    for f in flags or []:
        if f in skip:
            continue
        out.update(vetoes.get(f) or [])
    return out
