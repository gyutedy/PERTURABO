"""
F00 RADAR / CAPTEURS — Scan complet d'une ligue (monde PARI)
=============================================================
Avant la Porte 1 : récupère TOUS les matchs de la carte, lance le moteur
Dixon-Coles (F02) sur chacun, et produit un classement.

Score composite (poids par marchés actifs du profil Warsmith) :
  0.55 × P(O2.5) + 0.30 × P(MT2 > MT1) + 0.15 × min(1, λ_total/4)
Sortie : radar.json + SHARED/OUT/RADAR.md (lisible sur téléphone)

Usage:
  python radar.py --input ../../ARCHIVUM/fixtures/matches.json [--top 20]
"""

import json
import argparse
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BREACHER_DIR = os.path.join(HERE, "..", "..", "F02_BREACHER", "CODEBASE")
sys.path.insert(0, HERE)
sys.path.insert(0, BREACHER_DIR)
import breacher  # noqa: E402
from capteurs import ligue_code as resolve_ligue_code  # noqa: E402

_STAT_KEYS = ("mj", "marques", "encaisses")
LEARNINGS_MIN = 50
_CLIP_LO, _CLIP_HI = 0.85, 1.15
_MARKET_TO_COMP = {
    "ou_2.5": "o2.5", "ou25": "o2.5", "o2.5": "o2.5", "over25": "o2.5",
    "u2.5": "o2.5", "under25": "o2.5",
    "mt_prolifique": "mt2_plus", "mt2": "mt2_plus", "mt2_plus": "mt2_plus",
    "mt2>": "mt2_plus", "mt2plus": "mt2_plus",
}


def stats_complete(m):
    s = m.get("stats") or {}
    for side in ("dom", "ext"):
        t = s.get(side) or {}
        if not all(t.get(k) is not None for k in _STAT_KEYS):
            return False
    return True


def stamp_ligue(matchs, ligue=None, league_code=None):
    """Tampon ligue + league_code sur chaque match. Jamais invente un code hors mapping."""
    code = league_code
    name = ligue
    if matchs:
        name = name or matchs[0].get("ligue")
        code = code or matchs[0].get("league_code")
    if not code and name:
        code = resolve_ligue_code(name)
    for m in matchs:
        lg = m.get("ligue") or name
        if lg and not m.get("ligue"):
            m["ligue"] = lg
        c = league_code or m.get("league_code") or (resolve_ligue_code(m.get("ligue") or name or "") if (m.get("ligue") or name) else None) or code
        if c:
            m["league_code"] = c
    return matchs


def split_complete(matchs):
    complete, holes = [], []
    for m in matchs:
        if stats_complete(m):
            complete.append(m)
        else:
            holes.append(m.get("id") or "?")
    return complete, holes


def _tickets_path():
    return os.environ.get("PARI_TICKETS_PATH") or os.path.join(
        HERE, "..", "..", "ARCHIVUM", "learnings", "tickets.json"
    )


def _comp_of(raw):
    s = (raw or "").lower().replace(" ", "").replace("-", "").replace("_", "")
    aliases = {
        "ou25": "o2.5", "o25": "o2.5", "over25": "o2.5", "u25": "o2.5",
        "under25": "o2.5", "ou2.5": "o2.5",
        "mtprolifique": "mt2_plus", "mt2": "mt2_plus", "mt2plus": "mt2_plus",
        "mt2>": "mt2_plus",
    }
    return _MARKET_TO_COMP.get((raw or "").lower().replace(" ", "")) or aliases.get(s)


def _clip_factor(roi):
    return max(_CLIP_LO, min(_CLIP_HI, 1.0 + (roi or 0.0)))


def load_learnings(path=None):
    """Poids F06 : identity si < 50 tickets settle. Par marche si assez. F06 n'apprend pas."""
    path = path or _tickets_path()
    tickets = []
    if path and os.path.exists(path):
        try:
            blob = json.load(open(path, encoding="utf-8"))
            tickets = blob.get("tickets") or []
        except (OSError, json.JSONDecodeError):
            tickets = []
    settled = [t for t in tickets if t.get("resultat") in ("gagné", "gagne", "perdu")]
    n = len(settled)
    out = {"active": False, "n": n, "min": LEARNINGS_MIN, "factor": 1.0,
           "by_comp": {"o2.5": 1.0, "mt2_plus": 1.0}, "reason": "sous 50 tickets"}
    if n < LEARNINGS_MIN:
        return out
    mises = sum(t.get("mise_units") or 0 for t in settled)
    pnl = sum(t.get("pnl_units") or 0 for t in settled)
    roi = (pnl / mises) if mises else 0.0
    factor = _clip_factor(roi)
    buckets = {}
    for t in settled:
        comps = set()
        k = _comp_of(t.get("marche"))
        if k:
            comps.add(k)
        for j in t.get("jambes") or []:
            k = _comp_of(j.get("marche") or j.get("selection"))
            if k:
                comps.add(k)
        for k in comps:
            buckets.setdefault(k, []).append(t)
    by_comp = {"o2.5": 1.0, "mt2_plus": 1.0}
    by_n = {}
    for k, ts in buckets.items():
        if len(ts) < 8:
            by_n[k] = len(ts)
            continue
        m = sum(x.get("mise_units") or 0 for x in ts)
        p = sum(x.get("pnl_units") or 0 for x in ts)
        r = (p / m) if m else 0.0
        by_comp[k] = round(_clip_factor(r), 4)
        by_n[k] = len(ts)
    out.update({"active": True, "factor": round(factor, 4), "roi": round(roi, 4),
                "by_comp": by_comp, "by_n": by_n, "reason": f"{n} tickets settle"})
    return out


def apply_learnings(analyse, learnings=None):
    """Recompose le score : poids O2.5 / MT2 par marche. Facteur global seul ne reordonne pas."""
    learnings = learnings if learnings is not None else load_learnings()
    by_comp = learnings.get("by_comp") or {}
    f_o = by_comp.get("o2.5") or 1.0
    f_m = by_comp.get("mt2_plus") or 1.0
    if not learnings.get("active"):
        f_o = f_m = 1.0
    for a in analyse.get("analyses") or []:
        p = a.get("probas") or {}
        lam = a.get("lambdas") or {}
        lam_total = (lam.get("dom_total") or 0) + (lam.get("ext_total") or 0)
        raw = a.get("radar_score_raw")
        if raw is None:
            raw = round(
                0.55 * (p.get("o2.5") or 0) + 0.30 * (p.get("mt2_plus") or 0)
                + 0.15 * min(1.0, lam_total / 4.0), 4
            )
            a["radar_score_raw"] = raw
        if learnings.get("active"):
            a["radar_score"] = round(
                0.55 * (p.get("o2.5") or 0) * f_o
                + 0.30 * (p.get("mt2_plus") or 0) * f_m
                + 0.15 * min(1.0, lam_total / 4.0), 4
            )
        else:
            a["radar_score"] = raw
    analyse["learnings"] = learnings
    return analyse


def run_radar(matchs, top=20, ligue=None, league_code=None):
    stamp_ligue(matchs, ligue=ligue, league_code=league_code)
    complete, holes = split_complete(matchs)
    analyse = breacher.analyse_fixtures(complete, ligue=ligue, league_code=league_code)
    for m, a in zip(complete, analyse.get("analyses") or []):
        if m.get("ligue"):
            analyse["ligue"] = m["ligue"]
        lam_total = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        a["radar_score_raw"] = round(
            0.55 * a["probas"]["o2.5"] + 0.30 * a["probas"]["mt2_plus"] + 0.15 * min(1.0, lam_total / 4.0), 4
        )
        a["radar_score"] = a["radar_score_raw"]
    apply_learnings(analyse)
    ranked = sorted(analyse.get("analyses") or [], key=lambda a: a.get("radar_score") or 0, reverse=True)
    analyse["analyses"] = ranked
    analyse["top_ids"] = [a["id"] for a in ranked[:top]]
    analyse["holes"] = holes
    return analyse


def render_radar_md(analyse, top=20, max_rows=200):
    ranked = analyse["analyses"][:max_rows]
    lines = [
        f"# RADAR DE SIÈGE — {analyse.get('ligue', 'ligue')}",
        f"*Généré le {analyse['generated_at']} — moteur: Dixon-Coles PARI*",
        "",
        "| Rang | Match | λ total | P(O2.5) | P(MT2>) | Score |",
        "|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(ranked, 1):
        lam = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        badge = "*" if i <= top else " "
        lines.append(
            f"| {badge} {i} | {a['match']} ({a['id']}) | {lam:.2f} "
            f"| {a['probas']['o2.5']:.0%} | {a['probas']['mt2_plus']:.0%} | {a['radar_score']:.3f} |"
        )
    holes = analyse.get("holes") or []
    if holes:
        lines += ["", f"Trous declares ({len(holes)}) : " + ", ".join(str(h) for h in holes) + " — Zero Data, Zero Calc."]
    learn = analyse.get("learnings") or {}
    if learn.get("active"):
        lines += ["", f"Learnings F06 actifs (n={learn.get('n')}, facteur {learn.get('factor')})."]
    else:
        lines += ["", "Learnings F06 : identity (sous 50 tickets settle) — F06 n'apprend pas."]
    lines += ["", f"**Top {top}** passe la coupe noire ; le reste est archivé.",
              "", "*Le radar sert à trouver où creuser — la Value sort après la "
              "comparaison aux cotes du book (Compartiment 3).*"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="F00 RADAR — scan ligue PARI")
    parser.add_argument("--input", required=True)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--out-json", default=os.path.join(HERE, "..", "OUT", "radar.json"))
    parser.add_argument("--out-md", default=os.path.join(HERE, "..", "..", "SHARED", "OUT", "RADAR.md"))
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        carte = json.load(f)
    matchs = carte.get("matchs", [])
    analyse = run_radar(
        matchs, top=args.top,
        ligue=carte.get("ligue"), league_code=carte.get("league_code"),
    )
    analyse["ligue"] = carte.get("ligue", analyse.get("ligue") or "ligue")
    analyse["ligue_tier"] = carte.get("ligue_tier", "exotique")

    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(analyse, f, indent=2, ensure_ascii=False)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(render_radar_md(analyse, top=args.top))

    holes = analyse.get("holes") or []
    print(f"[RADAR] {len(analyse.get('analyses') or [])} matchs scannés — {args.top} TOP"
          + (f" — {len(holes)} trou(s): {', '.join(str(h) for h in holes)}" if holes else ""))
    for i, a in enumerate(analyse["analyses"][: args.top], 1):
        lam = a["lambdas"]["dom_total"] + a["lambdas"]["ext_total"]
        print(f"  {i:>2}. {a['match']:<30} λ{lam:.2f} O2.5:{a['probas']['o2.5']:.0%} MT2>:{a['probas']['mt2_plus']:.0%}")
    print(f"[RADAR] JSON: {args.out_json}")
    print(f"[RADAR] MD:   {args.out_md}")


if __name__ == "__main__":
    main()
