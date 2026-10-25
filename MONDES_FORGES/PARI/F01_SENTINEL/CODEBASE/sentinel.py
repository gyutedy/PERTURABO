"""
F01 SENTINEL — Collecte / nettoyage / validation des données du monde PARI
==========================================================================
Sources autorisées (whitelist) :
  - ARCHIVUM/fixtures/<carte>.json   (la carte de matchs du Warsmith)
  - cotes collées en TXT brut  (--cotes-txt)
  - (later) API-Football / football-data.org / ClubElo via clé Secret

Règle sacrée : Zero Data, Zero Calc. Une donnée manquante est FLAGGÉE,
jamais inventée. Les cotes reconstituées depuis TXT sont affichées pour
validation Warsmith AVANT tout calcul d'EV.

Usage:
  python sentinel.py --input ../../ARCHIVUM/fixtures/matches.json
  echo "Arsenal vs Chelsea : 1.85 / 3.6 / 4.2 | O2.5 1.70 | MT2 2.10" > cotes.txt
  python sentinel.py --input ... --cotes-txt cotes.txt
"""

import json
import re
import argparse
import os
from datetime import datetime, timezone

LIGUES_TOP5 = ["premier league", "la liga", "liga santander", "serie a", "bundesliga", "ligue 1"]


def detect_tier(ligue: str) -> str:
    lw = (ligue or "").lower()
    for k in LIGUES_TOP5:
        if k in lw:
            return "top5"
    return "exotique"


# --- Parseur de cotes TXT brut ------------------------------------------------
KEY_ALIASES = {
    "1": ["1.5?", "1:", "victoire dom", "dom"],  # non utilisé directement, juste doc
}
COTES_PATTERNS = [
    # "O2.5 1.70" / "over 2.5 = 1.70"
    (r"(?:o2\.5|over\s*2\.5|\+2\.5)\s*[:=]?\s*([\d.,]+)", "o2.5"),
    (r"(?:u2\.5|under\s*2\.5|[-–]2\.5)\s*[:=]?\s*([\d.,]+)", "u2.5"),
    (r"(?:mt1|1re\s*mt|1er\s*mt)\s*[:=]?\s*([\d.,]+)", "mt1"),
    (r"(?:mte|egalite|égalité|egal)\s*[:=]?\s*([\d.,]+)", "mte"),
    (r"(?:mt2|2e\s*mt|2d\s*mt)\s*[:=]?\s*([\d.,]+)", "mt2"),
    (r"(?:btts|btts oui|btts_oui|les deux marquent)\s*[:=]?\s*([\d.,]+)", "btts"),
]


def parse_cotes_txt(text: str):
    """Heuristique assumée : extraction key→cote. Pas de devinette sur les équipes :
    le Warsmith relie la sortie au match explicitement."""
    out = {}
    for pat, key in COTES_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(",", "."))
                if 1.01 <= val <= 100:
                    out[key] = val
            except ValueError:
                pass
    # 1X2 : premier triplet "a / b / c" ou a b c
    triple = re.search(r"(?<![\d.])(\d{1,2}\.\d{1,2})\s*[/|\s]\s*(\d{1,2}\.\d{1,2})\s*[/|\s]\s*(\d{1,2}\.\d{1,2})", text)
    if triple:
        try:
            vals = [float(x.replace(",", ".")) for x in triple.groups()]
            if all(1.01 <= v <= 100 for v in vals):
                out.setdefault("1", vals[0])
                out.setdefault("X", vals[1])
                out.setdefault("2", vals[2])
        except ValueError:
            pass
    if not out:
        return None
    return out


# --- Validation de la carte ----------------------------------------------------
def validate_match(m: dict, idx: int) -> dict:
    for fld in ("id", "dom", "ext"):
        if not m.get(fld):
            raise ValueError(f"Match #{idx} : champ requis '{fld}' manquant (Zero Data, Zero Calc)")
    stats = m.get("stats") or {}
    for side in ("dom", "ext"):
        t = stats.get(side) or {}
        if not all(k in t and t[k] is not None for k in ("mj", "marques", "encaisses")):
            raise ValueError(f"Match #{idx} ({m['dom']} vs {m['ext']}) : stats '{side}' incomplètes "
                             f"(mj, marques, encaisses requis) — Zero Data, Zero Calc")
    return m


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="F01 SENTINEL — collecte données PARI")
    parser.add_argument("--input", required=True, help="carte fixtures JSON")
    parser.add_argument("--cotes-txt", default=None, help="fichier texte de cotes brutes (optionnel)")
    parser.add_argument("--output", default=os.path.join(here, "..", "OUT", "matches_intel.json"))
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        carte = json.load(f)

    ligue = carte.get("ligue", "inconnue")
    tier = carte.get("ligue_tier") or detect_tier(ligue)
    matchs = [validate_match(m, i) for i, m in enumerate(carte.get("matchs", []))]

    # Cotes txt : rattachées au premier match sans cotes (usage : 1 match à la fois)
    warn = []
    if args.cotes_txt:
        with open(args.cotes_txt, "r", encoding="utf-8") as f:
            txt = f.read()
        parsed = parse_cotes_txt(txt)
        if parsed is None:
            warn.append("Cotes TXT fournies mais AUCUNE cote reconnue — Zero Data, Zero Calc")
        else:
            target = next((m for m in matchs if not m.get("cotes")), None)
            if target is None:
                warn.append("Tous les matchs ont déjà des cotes — collage txt ignoré")
            else:
                target["cotes"] = {**(target.get("cotes") or {}), **parsed}

    # Contrôles de cohérence
    for m in matchs:
        c = m.get("cotes")
        if c:
            for market, keys in (("1X2", ["1", "X", "2"]),):
                vals = [c[k] for k in keys if c.get(k)]
                if vals:
                    ov = sum(1 / v for v in vals) - 1
                    if ov < 0.005:
                        warn.append(f"{m['id']} {market}: overround suspect ({ov:.3f}) — vérifier les cotes")
                    if ov > 0.20:
                        warn.append(f"{m['id']} {market}: marge très haute ({ov:.1%}) — ligue exotique ?")

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "fixtures_file" + ("+cotes_txt" if args.cotes_txt else ""),
        "ligue": ligue,
        "ligue_tier": tier,
        "matchs": matchs,
        "warnings": warn,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"[SENTINEL] {len(matchs)} matchs — ligue: {ligue} (tier: {tier})")
    for w in warn:
        print(f"[SENTINEL] ⚠️ {w}")
    print(f"[SENTINEL] Sortie: {args.output}")


if __name__ == "__main__":
    main()
