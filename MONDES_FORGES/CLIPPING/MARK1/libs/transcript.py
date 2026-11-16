"""libs/transcript.py -- lire une transcription produite par F00B_VOX.

POURQUOI LIRE ET NON APPELER
    MARK1 ne parle qu'a ARCHIVUM. Il ne declenche jamais F00B_VOX : c'est
    l'operateur qui lance le workflow perturabo_transcribe, qui telecharge la
    VOD, la decoupe, la transcrit et COMMITE le resultat dans
        ARCHIVUM/montage/transcripts/v<VODID>_transcript.json

    MARK1 constate que le fichier existe. Consequences, toutes des avantages :
      - la transcription est payee UNE fois et relue autant de fois qu'on veut
      - chaque transcription est un commit date, donc tracable
      - si le service Modal tombe, MARK1 continue sur l'existant

FORMAT (celui de la forge)
    {
      "video_id": "...", "title": "...", "duration": 915,
      "transcript": {
        "text": "...",
        "segments": [{"start": 0.0, "text": "...", "duration": 4.88}, ...],
        "status": "OK", "segment_count": 397
      }
    }

CE QUE CE MODULE FAIT
    - cherche le transcript d'une VOD dans ARCHIVUM (par id)
    - lit les segments horodates
    - choisit une fenetre de N secondes a partir d'un timestamp
    - rend le texte d'une fenetre : c'est `source_text` pour M00B
"""

from __future__ import annotations

import glob
import json
import os
import re


def vod_id(vod_url):
    """Extrait l'identifiant d'une URL Twitch ou YouTube.

    https://twitch.tv/videos/2927914500        -> 2927914500
    https://www.youtube.com/watch?v=ElGoUp-0cqY -> ElGoUp-0cqY
    """
    url = str(vod_url or "").strip()
    if not url:
        return ""
    m = re.search(r"/videos?/(\d{6,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)
    m = re.search(r"([0-9]{6,}|[A-Za-z0-9_-]{11})$", url.rstrip("/"))
    return m.group(1) if m else ""


def find_transcript(cfg, root, vod_url_or_id):
    """Trouve le fichier de transcription dans ARCHIVUM.

    Ordre : nom exact -> contient l'id -> None.
    """
    rel = (cfg.get("archivum") or {}).get("transcripts_dir",
                                           "../ARCHIVUM/montage/transcripts")
    base = os.path.normpath(os.path.join(root, rel))
    vid = vod_id(vod_url_or_id) or str(vod_url_or_id or "").strip()
    if not vid:
        return None
    if not os.path.isdir(base):
        return None

    for pattern in ("v%s_transcript.json" % vid, "*%s*transcript*.json" % vid, "*%s*.json" % vid):
        hits = sorted(glob.glob(os.path.join(base, pattern)))
        if hits:
            return hits[0]
    return None


def load(path):
    """Charge un transcript. Rend la structure brute ou leve une erreur claire."""
    if not os.path.exists(path):
        raise FileNotFoundError("transcript introuvable : %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def segments(doc):
    """Rend la liste des segments horodates, quel que soit l'emboitement."""
    t = (doc or {}).get("transcript")
    if isinstance(t, dict):
        segs = t.get("segments") or []
        if segs:
            return segs
        # repli : un seul segment couvrant tout
        if t.get("text"):
            return [{"start": 0.0, "text": t["text"],
                     "duration": float((doc or {}).get("duration") or 0)}]
    if isinstance(t, list):
        return t
    return []


def full_text(doc):
    """Le texte complet, ou reconstitue depuis les segments."""
    t = (doc or {}).get("transcript")
    if isinstance(t, dict) and t.get("text"):
        return t["text"]
    return " ".join(s.get("text", "") for s in segments(doc)).strip()


def window_text(doc, start_sec, end_sec):
    """Texte des segments couvrant [start, end]. Borne proprement."""
    segs = segments(doc)
    if not segs:
        return ""
    lo = float(start_sec)
    hi = float(end_sec)
    out = []
    for s in segs:
        st = float(s.get("start") or 0)
        dur = float(s.get("duration") or 0)
        en = st + dur if dur else st
        if en <= lo or st >= hi:
            continue
        out.append((s.get("text") or "").strip())
    return " ".join(x for x in out if x).strip()


def duration(doc):
    segs = segments(doc)
    if segs:
        last = max(segs, key=lambda s: float(s.get("start") or 0))
        return float(last.get("start") or 0) + float(last.get("duration") or 0)
    return float((doc or {}).get("duration") or 0)


def candidate_windows(doc, cfg, limit=None):
    """Propose des fenetres de segment autour des marqueurs d'enjeu.

    MARK1 ne "comprend" pas la video : il reperera les zones ou le texte dit
    quelque chose (chiffres, marqueurs d'enjeu) et propose une fenetre autour.
    L'operateur valide aux gates.

    Rend une liste de {start_sec, end_sec, source_text, score}.
    """
    from libs.s1_context import load_lang

    segs = segments(doc)
    if not segs:
        return []

    lang = (cfg.get("default_language") or "en")
    spec = load_lang(lang)
    markers = tuple(spec.get("stake", ()))
    lo = float(cfg.get("min_segment_sec", 8))
    hi = float(cfg.get("max_segment_sec", 90))
    target = min(max(float(cfg.get("target_segment_sec", 30)), lo), hi)

    num = re.compile(r"\d")

    scored = []
    for i, s in enumerate(segs):
        txt = (s.get("text") or "")
        low = txt.lower()
        score = 0
        score += sum(1 for m in markers if m in low)
        score += 2 * len(num.findall(txt))
        if score:
            scored.append((score, float(s.get("start") or 0), i))

    scored.sort(key=lambda x: (-x[0], x[1]))

    out = []
    used = []
    for score, start, idx in scored:
        if any(abs(start - u) < target for u in used):
            continue
        end = start + target
        # ne pas depasser la duree reelle
        total = duration(doc)
        if total and end > total:
            end = total
            start = max(0.0, end - target)
        if end - start < lo:
            continue
        used.append(start)
        out.append({
            "start_sec": round(start, 1),
            "end_sec": round(end, 1),
            "source_text": window_text(doc, start, end),
            "score": score,
        })
        if limit and len(out) >= limit:
            break
    return out
