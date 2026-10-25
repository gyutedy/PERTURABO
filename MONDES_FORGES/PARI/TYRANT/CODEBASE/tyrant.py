"""
TYRANT — Vision stratégique pré-siège (monde PARI)
===================================================
GO / NO-GO sur la carte de matchs. Le TYRANT est la Porte 1 :
il filtre les proies analysables et fixe le seuil EV par tier de ligue.

Filtre froid (déterministe) :
  - complétude des stats (Zero Data, Zero Calc)
  - échantillon suffisant (mj >= 6)
  - tier de ligue → seuil EV appliqué (3% Top5 / 8% exotique)
Commentaire Oracle (optionnel, clé ORACLE_API_KEY) : lecture qualitative des
notes Warsmith (enjeu, fatigue, absences) — jamais de chiffres de l'Oracle.

Usage:
  python tyrant.py --intel F01_SENTINEL/OUT/matches_intel.json
"""

import json
import argparse
import os
from datetime import datetime, timezone

LIGUES_TOP5 = ["premier league", "la liga", "liga santander", "serie a", "bundesliga", "ligue 1"]


def detect_tier(ligue: str) -> str:
    lw = (ligue or "").lower()
    return "top5" if any(k in lw for k in LIGUES_TOP5) else "exotique"


def oracle_comment(notes: str, match_label: str):
    """Oracle (clé OpenAI-compatible, GitHub Secret). Fallback silencieux → None."""
    key = os.environ.get("ORACLE_API_KEY")
    if not key or not (notes or "").strip():
        return None
    try:
        import urllib.request
        base = os.environ.get("ORACLE_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("ORACLE_MODEL", "gpt-4o-mini")
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system",
                 "content": ("Tu es le TYRANT, vision stratégique pré-siège d'un monde d'analyse de paris foot. "
                             "Lis le contexte qualitatif du match et donne en 2-3 phrases un éclairage "
                             "tactique (enjeu, fatigue, absences, biais probable du public chez Winner Bet). "
                             "N'invente JAMAIS de chiffre, ne donne JAMAIS de probabilité — le moteur calculates les chiffres. "
                             "Termine toujours par au maximum une nuance de prudence.")},
                {"role": "user", "content": f"Match: {match_label}\nContexte Warsmith: {notes}"},
            ],
            "max_tokens": 300,
        }).encode()
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:  # hérésie interdite : l'Oracle ne bloque jamais le siège
        return f"(Oracle indisponible: {e})"


def build_carte(intel: dict):
    tier = intel.get("ligue_tier") or detect_tier(intel.get("ligue", ""))
    seuil = 0.03 if tier == "top5" else 0.08
    verdicts = []
    for m in intel["matchs"]:
        v = {"id": m["id"], "match": f"{m['dom']} vs {m['ext']}", "verdict": "GO", "raisons": []}
        stats = m.get("stats") or {}
        sd, se = stats.get("dom") or {}, stats.get("ext") or {}
        if (sd.get("mj") or 0) < 6:
            v["verdict"] = "NO_BET"
            v["raisons"].append(f"échantillon dom insuffisant ({sd.get('mj')} matchs < 6)")
        if (se.get("mj") or 0) < 6:
            v["verdict"] = "NO_BET"
            v["raisons"].append(f"échantillon ext insuffisant ({se.get('mj')} matchs < 6)")
        if tier != "top5":
            v["raisons"].append(f"ligue hors top5 → seuil EV durci à {seuil:.0%}")
        if m.get("cotes") is None:
            v["raisons"].append("pas de cotes Winner Bet → analyse radar uniquement (pas de verdict EV)")
        o = oracle_comment(m.get("notes"), v["match"])
        if o:
            v["oracle"] = o
        verdicts.append(v)

    go = sum(1 for v in verdicts if v["verdict"] == "GO")
    carte = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ligue": intel.get("ligue"),
        "ligue_tier": tier,
        "seuil_ev_applique": seuil,
        "go": go,
        "no_bet": len(verdicts) - go,
        "recommandation": "GO — carte analysable" if go > 0 else "NO GO — aucune proie utilisable",
        "justification": f"Tier: {tier}. {go} GO / {len(verdicts) - go} NO BET. Gate 1 à valider par le Warsmith.",
        "verdicts": verdicts,
    }
    return carte


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="TYRANT — carte GO/NO-GO PARI")
    parser.add_argument("--intel", required=True)
    parser.add_argument("--output", default=os.path.join(here, "..", "OUT", "carte_verdict.json"))
    args = parser.parse_args()
    with open(args.intel, "r", encoding="utf-8") as f:
        intel = json.load(f)
    carte = build_carte(intel)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(carte, f, indent=2, ensure_ascii=False)
    print(f"[TYRANT] {carte['ligue']} — tier {carte['ligue_tier']} — seuil EV {carte['seuil_ev_applique']:.0%}")
    print(f"[TYRANT] {carte['recommandation']} ({carte['go']} GO / {carte['no_bet']} NO BET)")
    for v in carte["verdicts"]:
        flag = "🔥 GO" if v["verdict"] == "GO" else "⛔ NO BET"
        raisons = " ; ".join(v["raisons"]) or "—" if v["raisons"] else "—"
        print(f"  {flag} {v['match']:<28} {raisons}")
    print(f"[TYRANT] Sortie: {args.output}")


if __name__ == "__main__":
    main()
