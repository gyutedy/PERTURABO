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

LIGUES_TOP5 = ["premier league", "la liga", "laliga", "liga santander", "serie a", "bundesliga", "ligue 1"]
_WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _load_env_pari():
    for name in (".env", "env_pari"):
        path = os.path.join(_WORLD, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    if key and val and not os.environ.get(key):
                        os.environ[key] = val
        except OSError:
            pass


_load_env_pari()


FLAG_EMPIRIQUE = "incoherence_modele_empirique"
O25_GAP = 0.20


def flag_empirique(p_modele, empirique, gap=None):
    """Flag TYRANT si |P_modele - O2.5 empirique| >= 0.20. Trou = pas de flag."""
    if p_modele is None or empirique is None:
        return False
    try:
        p, e = float(p_modele), float(empirique)
    except (TypeError, ValueError):
        return False
    thr = O25_GAP if gap is None else float(gap)
    return abs(p - e) >= thr


def stamp_empirique(carte, analysis, gap=None):
    """Ajoute le flag aux verdicts. Ne change pas GO/NO_BET. Jamais un 0 invente."""
    if not carte or not analysis:
        return carte
    rate = analysis.get("o2.5_empirique")
    by_id = {}
    for a in analysis.get("analyses") or []:
        by_id[a.get("id")] = a
    for v in carte.get("verdicts") or []:
        a = by_id.get(v.get("id")) or {}
        p = (a.get("probas") or {}).get("o2.5")
        emp = a.get("o2.5_empirique") if a.get("o2.5_empirique") is not None else rate
        flags = list(v.get("flags") or [])
        if flag_empirique(p, emp, gap=gap):
            if FLAG_EMPIRIQUE not in flags:
                flags.append(FLAG_EMPIRIQUE)
            raisons = list(v.get("raisons") or [])
            if FLAG_EMPIRIQUE not in raisons:
                raisons.append(FLAG_EMPIRIQUE)
            v["raisons"] = raisons
        v["flags"] = flags
        if emp is not None:
            v["o2.5_empirique"] = emp
        if p is not None:
            v["o2.5_modele"] = p
    return carte


def detect_tier(ligue: str) -> str:
    lw = (ligue or "").lower().replace("-", " ")
    compact = lw.replace(" ", "")
    if "laliga2" in compact or "la liga 2" in lw:
        return "exotique"
    return "top5" if any(k in lw or k.replace(" ", "") in compact for k in LIGUES_TOP5) else "exotique"


def oracle_comment(notes: str, match_label: str):
    """Oracle (clé OpenAI-compatible, GitHub Secret). Fallback silencieux → None."""
    key = os.environ.get("ORACLE_API_KEY") or os.environ.get("ZRO_API_KEY")
    if not key or not (notes or "").strip():
        return None
    try:
        import urllib.request
        base = os.environ.get("ORACLE_BASE_URL") or os.environ.get("ZRO_BASE_URL") or "https://api.openai.com/v1"
        model = os.environ.get("ORACLE_MODEL") or os.environ.get("ZRO_MODEL") or "gpt-4o-mini"
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
            "max_tokens": 400,
        }).encode()
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        msg = data["choices"][0]["message"]
        return (msg.get("content") or "").strip() or None
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
    parser.add_argument("--analysis", default=None)
    parser.add_argument("--output", default=os.path.join(here, "..", "OUT", "carte_verdict.json"))
    args = parser.parse_args()
    with open(args.intel, "r", encoding="utf-8") as f:
        intel = json.load(f)
    carte = build_carte(intel)
    if args.analysis and os.path.exists(args.analysis):
        try:
            with open(args.analysis, encoding="utf-8") as f:
                analysis = json.load(f)
            stamp_empirique(carte, analysis)
        except (OSError, json.JSONDecodeError):
            pass
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
