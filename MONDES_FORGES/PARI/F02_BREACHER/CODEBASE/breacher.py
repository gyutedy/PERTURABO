"""
F02 BREACHER — Le moteur mathématique du monde PARI
====================================================
Dixon-Coles (correction bas-scores) + Poisson par mi-temps.
Python pur (stdlib), zéro dépendance — Replit/GitHub Action ready.

Doctrine clé :
  λ par part de la moyene de la ligue (baseline), split mi-temps par part
  d'équipe si fiable, part ligue ~44%/56% sinon (flag estimate).
  P(MT2>MT1) est calculée depuis la matrice — JAMAIS à partir de la part
  des buts (les 0-0/0-0 et 1-0/0-0 brisent le pari MT2).

Usage:
  python breacher.py --input F01_SENTINEL/OUT/matches_intel.json
  (ou importé par radar.py / orchestrator.py)
"""

import json
import math
import argparse
import os
import sys
from datetime import datetime, timezone

RHO_DC = -0.13           # correction bas-scores Dixon-Coles (typique ~ -0.13)
DEFAULT_PART_MT1 = 0.44  # part structurelle des buts en 1re MT (ligues pros)
MAX_GOALS = 10           # grille de la matrice (buts 0..MAX par équipe)
_SHARES_CACHE = None
_STAT_KEYS = ("mj", "marques", "encaisses")


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def tau_dc(lh: float, la: float, rho: float, i: int, j: int) -> float:
    """Facteur de correction Dixon-Coles pour les bas scores."""
    if i == 0 and j == 0:
        return 1.0 - lh * la * rho
    if i == 0 and j == 1:
        return 1.0 + lh * rho
    if i == 1 and j == 0:
        return 1.0 + la * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lh: float, la: float, rho: float = RHO_DC, max_goals: int = MAX_GOALS):
    """Matrice P[i][j] = P(domicile i buts, extérieur j buts), corrigée DC."""
    ph = [poisson_pmf(i, lh) for i in range(max_goals + 1)]
    pa = [poisson_pmf(j, la) for j in range(max_goals + 1)]
    m = [[ph[i] * pa[j] * tau_dc(lh, la, rho, i, j) for j in range(max_goals + 1)]
         for i in range(max_goals + 1)]
    total = sum(sum(row) for row in m)
    return [[x / total for x in row] for row in m]


def matrix_stats(m):
    """Probas depuis la matrice. Equations inchangees. S4 = memes cellules, plus de marches."""
    p1 = px = p2 = po25 = pbtts = 0.0
    ou_over = {0.5: 0.0, 1.5: 0.0, 3.5: 0.0, 4.5: 0.0}
    tt_h = {0.5: 0.0, 1.5: 0.0, 2.5: 0.0}
    tt_a = {0.5: 0.0, 1.5: 0.0, 2.5: 0.0}
    best_p, best_ij = 0.0, (0, 0)
    scores = {}
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            tot = i + j
            if i > j:
                p1 += p
            elif i == j:
                px += p
            else:
                p2 += p
            if tot >= 3:
                po25 += p
            if tot >= 1:
                ou_over[0.5] += p
            if tot >= 2:
                ou_over[1.5] += p
            if tot >= 4:
                ou_over[3.5] += p
            if tot >= 5:
                ou_over[4.5] += p
            if i >= 1 and j >= 1:
                pbtts += p
            if i >= 1:
                tt_h[0.5] += p
            if i >= 2:
                tt_h[1.5] += p
            if i >= 3:
                tt_h[2.5] += p
            if j >= 1:
                tt_a[0.5] += p
            if j >= 2:
                tt_a[1.5] += p
            if j >= 3:
                tt_a[2.5] += p
            scores[f"{i}-{j}"] = p
            if p > best_p:
                best_p, best_ij = p, (i, j)
    out = {
        "1": p1, "X": px, "2": p2, "o2.5": po25, "u2.5": 1 - po25,
        "btts": pbtts, "btts_no": 1.0 - pbtts,
        "o0.5": ou_over[0.5], "u0.5": 1.0 - ou_over[0.5],
        "o1.5": ou_over[1.5], "u1.5": 1.0 - ou_over[1.5],
        "o3.5": ou_over[3.5], "u3.5": 1.0 - ou_over[3.5],
        "o4.5": ou_over[4.5], "u4.5": 1.0 - ou_over[4.5],
        "dc_1x": p1 + px, "dc_x2": px + p2, "dc_12": p1 + p2,
        "tt_h_o0.5": tt_h[0.5], "tt_h_u0.5": 1.0 - tt_h[0.5],
        "tt_h_o1.5": tt_h[1.5], "tt_h_u1.5": 1.0 - tt_h[1.5],
        "tt_h_o2.5": tt_h[2.5], "tt_h_u2.5": 1.0 - tt_h[2.5],
        "tt_a_o0.5": tt_a[0.5], "tt_a_u0.5": 1.0 - tt_a[0.5],
        "tt_a_o1.5": tt_a[1.5], "tt_a_u1.5": 1.0 - tt_a[1.5],
        "tt_a_o2.5": tt_a[2.5], "tt_a_u2.5": 1.0 - tt_a[2.5],
        "score_le_plus_probable": f"{best_ij[0]}-{best_ij[1]}",
        "_scores": scores,
    }
    return out


def score_key(sel):
    raw = str(sel or "").strip().lower()
    if raw.startswith("cs_"):
        raw = raw[3:]
    parts = raw.replace(":", "-").split("-")
    if len(parts) != 2:
        return None
    try:
        i, j = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if i < 0 or j < 0:
        return None
    return f"{i}-{j}"


def top_scores(scores, n=10, extra_keys=None):
    ranked = sorted((scores or {}).items(), key=lambda kv: -kv[1])
    out = {}
    for k, v in ranked[:n]:
        out[k] = v
    for key in extra_keys or []:
        sk = score_key(key)
        if sk and sk in scores:
            out[sk] = scores[sk]
    return out


def half_total_distribution(m):
    """Distribution du total de buts d'une mi-temps (somme des buts des 2 équipes)."""
    d = [0.0] * (2 * MAX_GOALS + 1)
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            d[i + j] += p
    return d


def mt_probas(m1, m2):
    """P(MT1 > / = / < MT2) depuis les deux matrices de mi-temps (indépendance assumée)."""
    t1 = half_total_distribution(m1)
    t2 = half_total_distribution(m2)
    mt1_plus = mte = mt2_plus = 0.0
    for a, pa in enumerate(t1):
        if pa == 0:
            continue
        for b, pb in enumerate(t2):
            if pb == 0:
                continue
            if a < b:
                mt2_plus += pa * pb
            elif a == b:
                mte += pa * pb
            else:
                mt1_plus += pa * pb
    return {"mt1_plus": mt1_plus, "mte": mte, "mt2_plus": mt2_plus}


def _stats_ok(side):
    return bool(side) and all(side.get(k) is not None for k in _STAT_KEYS)


def _load_shares():
    global _SHARES_CACHE
    if _SHARES_CACHE is not None:
        return _SHARES_CACHE
    path = os.environ.get("PARI_SHARES_PATH")
    if not path or not os.path.exists(path):
        _SHARES_CACHE = {}
        return _SHARES_CACHE
    try:
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
    except (OSError, json.JSONDecodeError):
        blob = {}
    _SHARES_CACHE = blob if isinstance(blob, dict) else {}
    return _SHARES_CACHE


def _league_code_of(matchs, ligue=None, league_code=None):
    if league_code:
        return league_code
    if matchs:
        c = matchs[0].get("league_code")
        if c:
            return c
        ligue = ligue or matchs[0].get("ligue")
    if not ligue:
        return None
    try:
        cap_dir = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "F00_RADAR", "CODEBASE"))
        if cap_dir not in sys.path:
            sys.path.insert(0, cap_dir)
        from capteurs import ligue_code as resolve
        return resolve(ligue)
    except Exception:
        return None


def stamp_league_code(matchs, ligue=None, league_code=None):
    code = _league_code_of(matchs, ligue=ligue, league_code=league_code)
    if not code:
        return code
    for m in matchs:
        if not m.get("league_code"):
            m["league_code"] = code
        if ligue and not m.get("ligue"):
            m["ligue"] = ligue
    return code


def _part_mt1_from_shares(code):
    if not code:
        return None
    shares = _load_shares()
    rec = shares.get(code) or shares.get(str(code).upper()) or {}
    if not isinstance(rec, dict):
        return None
    val = rec.get("part_mt1") or rec.get("part_mt1_ligue")
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if 0.30 <= f <= 0.60:
        return f
    return None


def _part_mt1_measured(matchs):
    parts, n = 0.0, 0
    for m in matchs:
        s = m.get("stats") or {}
        for side in (s.get("dom"), s.get("ext")):
            if not _stats_ok(side):
                continue
            tot = side.get("marques") or 0
            mt1 = side.get("marques_mt1")
            if tot and mt1 is not None:
                parts += mt1 / tot
                n += 1
    if n < 4:
        return None
    return parts / n


def league_averages(matchs, ligue=None, league_code=None):
    """Moyennes de la ligue (baseline) : buts domicile/ext sur l'échantillon."""
    dom_x, ext_x, n = 0.0, 0.0, 0
    for m in matchs:
        s = m.get("stats") or {}
        sd, se = s.get("dom"), s.get("ext")
        if not _stats_ok(sd) or not _stats_ok(se):
            continue
        dom_x += sd["marques"] / max(sd["mj"], 1)
        ext_x += se["marques"] / max(se["mj"], 1)
        n += 1
    if n == 0:
        raise ValueError("Aucune stat d'équipe valide — Zero Data, Zero Calc")
    code = _league_code_of(matchs, ligue=ligue, league_code=league_code)
    part = _part_mt1_from_shares(code) or _part_mt1_measured(matchs) or DEFAULT_PART_MT1
    return {
        "buts_dom_moy": dom_x / n,
        "buts_ext_moy": ext_x / n,
        "part_mt1_ligue": part,
        "league_code": code,
    }


def half_split_lambda(lam_total, scored_mt1, conceded_mt1, flags, part_ligue=None):
    """λ de 1re MT : part équipe si fiable, part ligue sinon (flag estimate)."""
    fallback = part_ligue if part_ligue is not None else DEFAULT_PART_MT1
    parts = []
    if scored_mt1 is not None:
        parts.append(scored_mt1)
    else:
        parts.append(fallback)
        flags.append("mt_split_estimate")
    if conceded_mt1 is not None:
        parts.append(conceded_mt1)
    else:
        parts.append(fallback)
        flags.append("mt_split_estimate_opp")
    return lam_total * (sum(parts) / len(parts))


def analyse_match(m, avg):
    flags = []
    sd, se = m["stats"]["dom"], m["stats"]["ext"]
    if sd["mj"] < 6 or se["mj"] < 6:
        flags.append("mj_insuffisant")
    if m.get("cotes") is None:
        flags.append("sans_cotes")

    # Forces attaque/défense relatives à la ligue (baseline)
    att_dom = max(sd["marques"] / max(sd["mj"], 1) / avg["buts_dom_moy"], 0.05)
    att_ext = max(se["marques"] / max(se["mj"], 1) / avg["buts_ext_moy"], 0.05)
    def_dom = max(sd["encaisses"] / max(sd["mj"], 1) / avg["buts_ext_moy"], 0.05)
    def_ext = max(se["encaisses"] / max(se["mj"], 1) / avg["buts_dom_moy"], 0.05)

    # Bonus domicile standard (~+10%)
    lambda_dom = att_dom * def_ext * avg["buts_dom_moy"] * 1.10
    lambda_ext = att_ext * def_dom * avg["buts_ext_moy"] * 0.95

    # Split mi-temps : part d'équipe si présente, part ligue sinon
    scored_mt1_dom = (sd["marques_mt1"] / sd["marques"]) if sd.get("marques_mt1") else None
    scored_mt1_ext = (se["marques_mt1"] / se["marques"]) if se.get("marques_mt1") else None
    conceded_mt1_ext = (se["encaisses_mt1"] / se["encaisses"]) if se.get("encaisses_mt1") else None
    conceded_mt1_dom = (sd["encaisses_mt1"] / sd["encaisses"]) if sd.get("encaisses_mt1") else None

    part = avg.get("part_mt1_ligue", DEFAULT_PART_MT1)
    lam_dom_mt1 = half_split_lambda(lambda_dom, scored_mt1_dom, conceded_mt1_ext, flags, part)
    lam_ext_mt1 = half_split_lambda(lambda_ext, scored_mt1_ext, conceded_mt1_dom, flags, part)
    lam_dom_mt2 = lambda_dom - lam_dom_mt1
    lam_ext_mt2 = lambda_ext - lam_ext_mt1

    m_total = score_matrix(lambda_dom, lambda_ext)
    m_mt1 = score_matrix(lam_dom_mt1, lam_ext_mt1)
    m_mt2 = score_matrix(lam_dom_mt2, lam_ext_mt2)

    probas = matrix_stats(m_total)
    scores = probas.pop("_scores", {})
    probas.update(mt_probas(m_mt1, m_mt2))
    cs = top_scores(scores, n=10, extra_keys=(m.get("cotes") or {}).keys())

    quality = "haute" if not flags else ("moyenne" if set(flags) <= {"sans_cotes", "mt_split_estimate", "mt_split_estimate_opp"} else "basse")
    rounded = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in probas.items()}
    return {
        "id": m["id"],
        "match": f"{m['dom']} vs {m['ext']}",
        "lambdas": {
            "dom_total": round(lambda_dom, 3), "ext_total": round(lambda_ext, 3),
            "dom_mt1": round(lam_dom_mt1, 3), "dom_mt2": round(lam_dom_mt2, 3),
            "ext_mt1": round(lam_ext_mt1, 3), "ext_mt2": round(lam_ext_mt2, 3),
        },
        "probas": rounded,
        "cs": {k: round(v, 4) for k, v in cs.items()},
        "data_quality": {"niveau": quality, "flags": flags},
    }


def analyse_fixtures(matchs, ligue=None, league_code=None):
    stamp_league_code(matchs, ligue=ligue, league_code=league_code)
    usable = [m for m in matchs if _stats_ok((m.get("stats") or {}).get("dom"))
              and _stats_ok((m.get("stats") or {}).get("ext"))]
    try:
        avg = league_averages(usable, ligue=ligue, league_code=league_code)
    except ValueError:
        # Zero Data, Zero Calc : aucune stat d'équipe → analyses vides, pas de crash.
        # Le flux capture seul (cotes sans stats historiques) doit être complété
        # par la bibliothèque de stats (capteurs build-stats + inject) avant siège.
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ligue": ligue or (matchs[0].get("ligue", "?") if matchs else "?"),
            "ligue_moyennes": None,
            "analyses": [],
            "message": ("Zero Data, Zero Calc — aucune stat d'équipe dans la carte. "
                        "Ajoute les stats via capteurs.py build-stats + inject, ou une carte manuelle."),
        }
    moy = {}
    for k, v in avg.items():
        if isinstance(v, float):
            moy[k] = round(v, 4)
        else:
            moy[k] = v
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ligue": ligue or (matchs[0].get("ligue", "?") if matchs else "?"),
        "ligue_moyennes": moy,
        "analyses": [analyse_match(m, avg) for m in usable],
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="F02 BREACHER — moteur math PARI")
    parser.add_argument("--input", required=True, help="F01_SENTINEL/OUT/matches_intel.json")
    parser.add_argument("--output",
                        default=os.path.join(here, "..", "OUT", "analysis.json"))
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        intel = json.load(f)
    out = analyse_fixtures(
        intel["matchs"],
        ligue=intel.get("ligue"),
        league_code=intel.get("league_code"),
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"[BREACHER] {len(out['analyses'])} matchs analysés — ligue: {out['ligue']}")
    print(f"[BREACHER] Ligue moyennes: {out['ligue_moyennes']}")
    for a in out["analyses"][:5]:
        p = a["probas"]
        print(f"  {a['id']} {a['match']:<32} λ={a['lambdas']['dom_total']:.2f}-{a['lambdas']['ext_total']:.2f} "
              f"1:{p['1']:.0%} O2.5:{p['o2.5']:.0%} MT2>:{p['mt2_plus']:.0%} qualité:{a['data_quality']['niveau']}")
    print(f"[BREACHER] Sortie: {args.output}")


if __name__ == "__main__":
    main()
