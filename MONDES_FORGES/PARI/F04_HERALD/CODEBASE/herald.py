"""
F04 HERALD — La frégate lourde (monde PARI)
============================================
Rédige les fiches de siège lisibles (MD) à partir des analyses + prédictions.
Sans clé Oracle : template structuré (100% suffisant). Avec ORACLE_API_KEY :
paragraphe "lecture du siège" généré par le LLM — jamais de chiffre du LLM.

Usage:
  python herald.py --analysis ../../F02_BREACHER/OUT/analysis.json \
                   --predictions ../../F03_FORGEWARD/OUT/predictions.json \
                   [--carte ../../TYRANT/OUT/carte_verdict.json]
"""

import json
import argparse
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_HINT = os.path.join(HERE, "..", "..", "ARCHIVUM", "rules", "warsmith_profile.json")


def format_pct(x):
    return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "—"


VERDICT_STYLE = {"GO": "🔥", "THIN": "🟡", "NO_BET": "⛔"}


def report_md(m_pred, m_analysis, oracle_text=None):
    p, a = m_pred, m_analysis
    lam = a["lambdas"]
    q = a["data_quality"]
    lines = [
        f"# 🏟️ FICHE DE SIÈGE — {p['match']}",
        f"*Générée le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — siege_id courant*",
        "",
        f"**Verdict match : {VERDICT_STYLE.get(p['verdict'], '')} {p['verdict']}** — meilleure EV: {format_pct(p.get('meilleure_ev'))}",
        "",
        "## Modèle (Dixon-Coles)",
        "",
        f"- λ attendus : dom {lam['dom_total']:.2f} — ext {lam['ext_total']:.2f} "
        f"(MT1: {lam['dom_mt1']:.2f}+{lam['ext_mt1']:.2f} · MT2: {lam['dom_mt2']:.2f}+{lam['ext_mt2']:.2f})",
        f"- Score le plus probable : **{a['probas']['score_le_plus_probable']}**",
        f"- 1 / X / 2 : {format_pct(a['probas']['1'])} / {format_pct(a['probas']['X'])} / {format_pct(a['probas']['2'])}",
        f"- Over 2.5 : **{format_pct(a['probas']['o2.5'])}** · Under 2.5 : {format_pct(a['probas']['u2.5'])}",
        f"- Les deux marquent : {format_pct(a['probas'].get('btts'))}",
        f"- Mi-temps : MT1 {format_pct(a['probas']['mt1_plus'])} · Égalité {format_pct(a['probas']['mte'])} · **MT2 {format_pct(a['probas']['mt2_plus'])}**",
        f"- Qualité data : {q['niveau']}" + (f" ({', '.join(q['flags'])})" if q["flags"] else ""),
        "",
        "## Confrontation cotes (Winner Bet)",
        "",
        "| Marché | Sélection | Cote | P modèle | EV | Verdict | Mise |",
        "|---|---|---|---|---|---|---|",
    ]
    if p["selections"]:
        for s in p["selections"]:
            mise = f"{s['mise_units']}u" if s.get("mise_units") else "—"
            lines.append(
                f"| {s['marche']} | {s['selection_label']} | {s['cote']} "
                f"| {format_pct(s['p_modele'])} | {format_pct(s['ev'])} "
                f"| {VERDICT_STYLE.get(s['verdict'], '')} {s['verdict']} | {mise} |"
            )
    else:
        lines.append("| — aucune cote fournie — mode radar uniquement — |")
    if oracle_text:
        lines += ["", "## Lecture du Tyrant/Oracle", "", f"> {oracle_text}"]
    lines += [
        "",
        "## Ordre de marche",
        "",
    ]
    best = [s for s in p["selections"] if s["verdict"] == "VALUE"]
    if best:
        s = best[0]
        lines.append(f"- Miser **{s['mise_units']}u** sur **{s['selection_label']}** @ {s['cote']} (¼ Kelly plafonné).")
    else:
        lines.append("- ⛔ **NO BET / PASSER LE MATCH** — aucune valeur mathématique identifiée.")
    lines += [
        "",
        "*1u = 1% de la bankroll. Mise max 5% (3% exotique). L'opérateur humain place le pari — le monde ne passe jamais d'ordre.*",
        "",
        "*Jeu responsable : le pari est un divertissement à maîtriser. On analyse des probabilités, on ne promet rien.*",
        "",
        "Fer au-dedans, Fer au-dehors.",
    ]
    return "\n".join(lines)


def oracle_reading(carte):
    """Une lecture Oracle globale de la carte si la clé est là (optionnel)."""
    key = os.environ.get("ORACLE_API_KEY")
    if not key or not carte:
        return None
    try:
        import urllib.request
        base = os.environ.get("ORACLE_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("ORACLE_MODEL", "gpt-4o-mini")
        resume = "\n".join(
            f"- {v['match']}: {v['verdict']} ({'; '.join(v['raisons']) or '—'})" for v in carte.get("verdicts", [])[:20]
        )
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "Tu es le HERALD du monde PARI. Rédige un court résumé de siège (4-6 phrases), "
                    "style rapport militaire sobre, sur la carte de matchs fournie. N'invente AUCUN chiffre, "
                    "AUCUNE probabilité. Rappelle la prudence en dernière phrase.")},
                {"role": "user", "content": resume},
            ],
            "max_tokens": 350,
        }).encode()
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"(Oracle indisponible: {e})"


def main():
    parser = argparse.ArgumentParser(description="F04 HERALD — fiches de siège")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--carte", default=None)
    parser.add_argument("--out-dir", default=os.path.join(HERE, "..", "OUT", "reports"))
    args = parser.parse_args()

    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    with open(args.predictions, "r", encoding="utf-8") as f:
        predictions = json.load(f)
    carte = None
    if args.carte and os.path.exists(args.carte):
        with open(args.carte, "r", encoding="utf-8") as f:
            carte = json.load(f)

    by_id = {a["id"]: a for a in analysis["analyses"]}
    oracle_txt = oracle_reading(carte)
    os.makedirs(args.out_dir, exist_ok=True)
    index = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "reports": [], "oracle_utilise": bool(oracle_txt and oracle_txt.startswith("(") is False)}
    for p in predictions["predictions"]:
        a = by_id.get(p["id"])
        if not a:
            continue
        slug = f"{p['id']}_fiche.md"
        path = os.path.join(args.out_dir, slug)
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_md(p, a, oracle_text=oracle_txt))
        index["reports"].append({"id": p["id"], "match": p["match"], "verdict": p["verdict"], "file": path})
        print(f"[HERALD] 📄 {path}")

    idx_path = os.path.join(HERE, "..", "OUT", "reports_index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"[HERALD] {len(index['reports'])} fiches — index: {idx_path}")


if __name__ == "__main__":
    main()
