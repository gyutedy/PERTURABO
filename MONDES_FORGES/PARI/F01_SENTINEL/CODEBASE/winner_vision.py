#!/usr/bin/env python3
"""
WINNER VISION — capture / transcription -> slate v1 (voie PRIMAIRE).
====================================================================
La capture d'ecran est lue par un LLM VISION generique (llm_vision.py).
Ce module parse le texte transcrit et applique 4 gardes :
  V1  deux transcriptions independantes doivent coincider, sinon trou
      "transcription_instable" (jamais une moyenne) ;
  V2  bornes : cote [1.01, 50], ligne NBA [180, 320] ;
  V3  coherence de grille 1X2 : somme des implicites dans [1.00, 1.35] ;
  V4  absent = null + trou nomme, jamais 0, jamais estime.
Sortie : vanus.slate.v1 — des OBSERVATIONS, jamais un p.
Usage :
  python winner_vision.py --in transcript.txt --sport basket
  python winner_vision.py --images cap1.PNG cap2.PNG --sport basket
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone

CONTRACT = "vanus.slate.v1"
INDEX_VISION = "winner_vision"
COTE_MIN, COTE_MAX = 1.01, 50.0
TOTAL_MIN, TOTAL_MAX = 180.0, 320.0
GRID_MIN, GRID_MAX = 1.00, 1.35
DIAGNOSTIC_ONLY = ["hsh_first", "hsh_equal", "hsh_second"]

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_COTE = r"([0-9]{1,2}\.[0-9]{2})"
_TOK = {
    "ml": re.compile(r"\bML\s*" + _COTE + r"\s*/\s*" + _COTE, re.I),
    "1x2": re.compile(r"\b1X2\s*" + _COTE + r"\s*/\s*" + _COTE + r"\s*/\s*" + _COTE, re.I),
    "total": re.compile(r"\bTotal\s*([0-9]{3}(?:\.[05])?)", re.I),
    "under": re.compile(r"\bU(?:nder)?\s*2?\.?5?\s*:?\s*" + _COTE, re.I),
    "over": re.compile(r"\bO(?:ver)?\s*2?\.?5?\s*:?\s*" + _COTE, re.I),
    "uo_line": re.compile(r"\b([0-9]{1,3}(?:\.[05])?)\s*:\s*" + _COTE + r"\s*/\s*" + _COTE, re.I),
    "hsh": re.compile(r"\bHSH\s*" + _COTE + r"\s*/\s*" + _COTE + r"\s*/\s*" + _COTE, re.I),
    "mid": re.compile(r"#(\d+)"),
    "time": re.compile(r"\b([0-9]{2}:[0-9]{2})\b"),
}


def _alnum(v):
    return _NON_ALNUM.sub("", str(v or "").lower())


def match_key(home, away):
    h, a = _alnum(home), _alnum(away)
    if not h or not a:
        return None
    return "_".join(sorted([h, a]))


def _f(txt):
    try:
        return float(txt)
    except (TypeError, ValueError):
        return None


def _blocks(text):
    """Un bloc = un match : lignes non vides consecutives."""
    blocks, cur = [], []
    for line in str(text or "").splitlines():
        if line.strip():
            cur.append(line.strip())
        elif cur:
            blocks.append("\n".join(cur))
            cur = []
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def parse_block(block, sport):
    """Un bloc texte -> (match, trous). Jamais d'exception."""
    holes = []
    lines = [l for l in block.splitlines() if l.strip()]
    teams = None
    for l in lines:
        if "-" in l and not _TOK["ml"].search(l):
            parts = [p.strip() for p in l.split("-", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                teams = (parts[0], parts[1])
                break
    if not teams:
        return None, ["equipes_absentes"]
    home, away = teams
    joined = "\n".join(lines)
    mid = _TOK["mid"].search(joined)
    ktime = _TOK["time"].search(joined)

    def cote(raw):
        v = _f(raw)
        if v is None:
            return None, "cote_absente"
        if not (COTE_MIN <= v <= COTE_MAX):
            return None, "cote_hors_bornes"
        return v, None

    odds, diag = {}, []
    m = _TOK["ml"].search(joined)
    if m and sport == "basket":
        for k, raw in (("ml_1", m.group(1)), ("ml_2", m.group(2))):
            v, err = cote(raw)
            odds[k] = v
            if err:
                holes.append("ml_" + err)
    m = _TOK["1x2"].search(joined)
    if m and sport == "foot":
        for k, raw in (("home", m.group(1)), ("draw", m.group(2)), ("away", m.group(3))):
            v, err = cote(raw)
            odds[k] = v
            if err:
                holes.append("1x2_" + err)
        if all(odds.get(k) for k in ("home", "draw", "away")):
            grid = sum(1 / odds[k] for k in ("home", "draw", "away"))
            if not (GRID_MIN <= grid <= GRID_MAX):
                holes.append("grille_incoherente")
    m = _TOK["total"].search(joined)
    if m and sport == "basket":
        tl = _f(m.group(1))
        if tl is None or not (TOTAL_MIN <= tl <= TOTAL_MAX):
            odds["total_line"] = None
            holes.append("ligne_hors_bornes")
        else:
            odds["total_line"] = tl
    if sport == "basket":
        mu, mo = _TOK["under"].search(joined), _TOK["over"].search(joined)
        for k, mm in (("total_under", mu), ("total_over", mo)):
            v, err = cote(mm.group(1)) if mm else (None, "cote_absente")
            odds[k] = v
            if err:
                holes.append(k + "_" + err)
    if sport == "foot":
        mu = _TOK["uo_line"].search(joined)
        if mu:
            odds["under_2_5"], odds["over_2_5"] = _f(mu.group(2)), _f(mu.group(3))
            odds.setdefault("total_line", _f(mu.group(1)))
        else:
            odds.setdefault("under_2_5", None)
            odds.setdefault("over_2_5", None)
            holes.append("ou25_absente")
    mh = _TOK["hsh"].search(joined)
    if sport == "foot":
        if mh:
            odds["hsh_first"], odds["hsh_equal"], odds["hsh_second"] = (
                _f(mh.group(1)), _f(mh.group(2)), _f(mh.group(3)))
            diag = list(DIAGNOSTIC_ONLY)
        else:
            odds.setdefault("hsh_first", None)
            odds.setdefault("hsh_equal", None)
            odds.setdefault("hsh_second", None)
            holes.append("hsh_absente")
    return {
        "match_key": match_key(home, away),
        "index": INDEX_VISION,
        "sport": sport,
        "home": home, "away": away,
        "kickoff": ktime.group(1) if ktime else None,
        "source_event_id": mid.group(1) if mid else None,
        "odds": odds,
        "diagnostic_only": diag,
        "holes": holes,
    }, holes


def parse_transcript(text, sport):
    matches, holes = [], []
    for block in _blocks(text):
        m, h = parse_block(block, sport)
        if m is None:
            holes.extend(h)
            continue
        matches.append(m)
        holes.extend(x for x in h if x)
    return matches, holes


def double_check(matches_a, matches_b):
    """V1 — deux transcriptions independantes. Divergence = trou."""
    holes = []
    ka = {m["match_key"]: m["odds"] for m in matches_a if m["match_key"]}
    kb = {m["match_key"]: m["odds"] for m in matches_b if m["match_key"]}
    if set(ka) != set(kb):
        return ["transcription_instable:blocs_differents"]
    for key in ka:
        for feld in set(ka[key]) | set(kb[key]):
            if ka[key].get(feld) != kb[key].get(feld):
                holes.append("transcription_instable:" + key + ":" + feld)
                break
    return holes


def build(text, sport, text_b=None, extra_holes=None):
    matches, holes = parse_transcript(text, sport)
    if text_b is not None:
        matches_b, _ = parse_transcript(text_b, sport)
        holes.extend(double_check(matches, matches_b))
    if extra_holes:
        holes.extend(extra_holes)
    seen, ordered = set(), []
    for m in sorted(matches, key=lambda x: (x.get("kickoff") or "", x.get("match_key") or "")):
        k = m.get("match_key")
        if k and k in seen:
            holes.append("doublon_ignore:" + k)
            continue
        if k:
            seen.add(k)
        ordered.append(m)
    return {
        "contract": CONTRACT,
        "index": INDEX_VISION,
        "sport": sport,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "winner.bet (capture ecran operateur, vision/OCR siege)",
        "matches": ordered,
        "holes": list(dict.fromkeys(holes)),
    }


def main():
    ap = argparse.ArgumentParser(description="F01 Winner vision (capture -> slate v1)")
    ap.add_argument("--in", dest="inp", default=None)
    ap.add_argument("--in2", dest="inp2", default=None)
    ap.add_argument("--images", nargs="*", default=None)
    ap.add_argument("--sport", choices=("basket", "foot"), default="basket")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    extra = []
    if args.images:
        import llm_vision
        from shutil import copy2
        from datetime import datetime, timezone
        archive = os.path.join("ARCHIVUM", "winner", "images")
        os.makedirs(archive, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        saved = []
        for src in args.images:
            dst = os.path.join(archive, stamp + "_" + os.path.basename(src))
            copy2(src, dst)
            saved.append(dst)
        a, b, extra = llm_vision.read_capture_twice(saved, args.sport)
        text, text_b = a, b
    else:
        if not args.inp:
            ap.error("--in ou --images requis")
        text = open(args.inp, encoding="utf-8").read()
        text_b = open(args.inp2, encoding="utf-8").read() if args.inp2 else None
    blob = build(text, args.sport, text_b, extra_holes=extra)
    out = args.out or os.path.join("ARCHIVUM", "winner", "slate_%s.json" % args.sport)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)
    print(f"[WINNER-VISION] {args.sport}: {len(blob['matches'])} match(s), "
          f"{len(blob['holes'])} trou(s) -> {out}")


if __name__ == "__main__":
    main()
