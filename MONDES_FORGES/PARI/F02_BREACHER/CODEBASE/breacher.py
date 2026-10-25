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
from datetime import datetime, timezone

RHO_DC = -0.13           # correction bas-scores Dixon-Coles (typique ~ -0.13)
DEFAULT_PART_MT1 = 0.44  # part structurelle des buts en 1re MT (ligues pros)
MAX_GOALS = 10           # grille de la matrice (buts 0..MAX par équipe)


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
    """Probas 1/X/2, O-U 2.5, BTTS, score le plus probable depuis une matrice."""
    p1 = px = p2 = po25 = pbtts = 0.0
    best_p, best_ij = 0.0, (0, 0)
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            if i > j:
                p1 += p
            elif i == j:
                px += p
            else:
                p2 += p
            if i + j >= 3:
                po25 += p
            if i >= 1 and j >= 1:
                pbtts += p
            if p > best_p:
                best_p, best_ij = p, (i, j)
    return {
        "1": p1, "X": px, "2": p2, "o2.5": po25, "u2.5": 1 - po25,
        "btts": pbtts,
        "score_le_plus_probable": f"{best_ij[0]}-{best_ij[1]}",
    }


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


def league_averages(matchs):
    """Moyennes de la ligue (baseline) : buts dominiciles/ext sur l'échantillon."""
    dom_x, ext_x, n = 0.0, 0.0, 0
    for m in matchs:
        s = m.get("stats") or {}
        sd, se = s.get("dom"), s.get("ext")
        if not sd or not se:
            continue
        dom_x += sd["marques"] / max(sd["mj"], 1)
        ext_x += se["marques"] / max(se["mj"], 1)
        n += 1
    if n == 0:
        raise ValueError("Aucune stat d'équipe valide — Zero Data, Zero Calc")
    return {
        "buts_dom_moy": dom_x / n,
        "buts_ext_moy": ext_x / n,
        "part_mt1_ligue": DEFAULT_PART_MT1,
    }


def half_split_lambda(lam_total, scored_mt1, conceded_mt1, flags):
    """λ de 1re MT : part équipe si fiable, part ligue sinon (flag estimate)."""
    parts = []
    if scored_mt1 is not None:
        parts.append(scored_mt1)
    else:
        parts.append(DEFAULT_PART_MT1)
        flags.append("mt_split_estimate")
    if conceded_mt1 is not None:
        parts.append(conceded_mt1)
    else:
        parts.append(DEFAULT_PART_MT1)
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

    lam_dom_mt1 = half_split_lambda(lambda_dom, scored_mt1_dom, conceded_mt1_ext, flags)
    lam_ext_mt1 = half_split_lambda(lambda_ext, scored_mt1_ext, conceded_mt1_dom, flags)
    lam_dom_mt2 = lambda_dom - lam_dom_mt1
    lam_ext_mt2 = lambda_ext - lam_ext_mt1

    m_total = score_matrix(lambda_dom, lambda_ext)
    m_mt1 = score_matrix(lam_dom_mt1, lam_ext_mt1)
    m_mt2 = score_matrix(lam_dom_mt2, lam_ext_mt2)

    probas = matrix_stats(m_total)
    probas.update(mt_probas(m_mt1, m_mt2))

    quality = "haute" if not flags else ("moyenne" if set(flags) <= {"sans_cotes", "mt_split_estimate", "mt_split_estimate_opp"} else "basse")
    return {
        "id": m["id"],
        "match": f"{m['dom']} vs {m['ext']}",
        "lambdas": {
            "dom_total": round(lambda_dom, 3), "ext_total": round(lambda_ext, 3),
            "dom_mt1": round(lam_dom_mt1, 3), "dom_mt2": round(lam_dom_mt2, 3),
            "ext_mt1": round(lam_ext_mt1, 3), "ext_mt2": round(lam_ext_mt2, 3),
        },
        "probas": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in probas.items()},
        "data_quality": {"niveau": quality, "flags": flags},
    }


def analyse_fixtures(matchs):
    avg = league_averages(matchs)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ligue": matchs[0].get("ligue", "?") if matchs else "?",
        "ligue_moyennes": {k: round(v, 4) for k, v in avg.items()},
        "analyses": [analyse_match(m, avg) for m in matchs],
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
    out = analyse_fixtures(intel["matchs"])
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
