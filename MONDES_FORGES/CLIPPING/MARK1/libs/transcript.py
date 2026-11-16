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

FORMATS LUS (les deux formes existent dans ARCHIVUM)
    {
      "video_id": "...", "title": "...", "duration": 915,
      "transcript": {
        "text": "...",
        "segments": [{"start": 0.0, "text": "...", "duration": 4.88}, ...],
        "status": "OK", "segment_count": 397
      }
    }
  et, format reel de F00B_VOX auto_detect (mode words) :
    {
      "vod_url": "...", "vod_duration": 6440.0, "transcription_mode": "words",
      "total_words": 10982,
      "words": [{"word": " Yo,", "start": 75.44, "end": 76.06}, ...],
      "segments": null,
      "chat_messages": [...]
    }
    (ou directement {"transcript": {"segments": [...]}} en mode segments).
    Ce module normalise : words -> segments -> fenetres.

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


def _from_words(words, cfg=None):
    """Regroupe une liste de mots horodates en phrases.

    F00B_VOX auto_detect ecrit `words[]` (mode words) et laisse `segments`
    a null. MARK1 a besoin de phrases : on coupe sur la ponctuation finale et
    sur un silence plus long que `word_silence_sec`. Aucune invention : les
    timestamps viennent des mots.
    """
    gap = float((cfg or {}).get("word_silence_sec", 0.6))
    max_words = int((cfg or {}).get("word_group_max", 60))

    out = []
    buf = []
    prev_end = None

    def flush():
        if not buf:
            return
        text = " ".join(w.get("word", "").strip() for w in buf)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text).strip()
        start = float(buf[0].get("start") or 0)
        end = float(buf[-1].get("end") or buf[-1].get("start") or start)
        out.append({"start": round(start, 3), "text": text,
                    "duration": round(max(0.0, end - start), 3)})
        buf.clear()

    for w in words or []:
        if not isinstance(w, dict):
            continue
        start = float(w.get("start") or 0)
        if prev_end is not None and start - prev_end > gap:
            flush()
        buf.append(w)
        prev_end = float(w.get("end") or start)
        wtext = str(w.get("word") or "").strip()
        if wtext and wtext[-1] in ".!?" or len(buf) >= max_words:
            flush()
    flush()
    return out


def segments(doc, cfg=None):
    """Rend la liste des segments horodates, quel que soit le format produit.

    Ordre de lecture, du plus riche au plus pauvre :
      1. {"transcript": {"segments": [...]}}      (format fixture / mode segments)
      2. {"transcript": "texte"}                  (texte seul)
      3. {"segments": [...]} a la racine            (mode segments de F00B)
      4. {"words": [...]} a la racine               (mode words de F00B)
      5. rien
    """
    doc = doc or {}
    if isinstance(doc, list):
        return doc

    t = doc.get("transcript")
    if isinstance(t, dict):
        segs = t.get("segments")
        if segs:
            return segs
        words = t.get("words")
        if words:
            return _from_words(words, cfg)
        if t.get("text"):
            return [{"start": 0.0, "text": t["text"],
                     "duration": float(doc.get("duration") or doc.get("vod_duration") or 0)}]
    if isinstance(t, str) and t.strip():
        return [{"start": 0.0, "text": t,
                 "duration": float(doc.get("duration") or doc.get("vod_duration") or 0)}]

    segs = doc.get("segments")
    if segs:
        return segs

    words = doc.get("words")
    if words:
        return _from_words(words, cfg)

    return []


def full_text(doc):
    """Le texte complet, ou reconstitue depuis les segments."""
    t = (doc or {}).get("transcript")
    if isinstance(t, dict) and t.get("text"):
        return t["text"]
    segs = segments(doc)
    if segs:
        return " ".join(s.get("text", "") for s in segs).strip()
    words = (doc or {}).get("words")
    if words:
        return _from_words(words)
    return ""


def window_text(doc, start_sec, end_sec, cfg=None):
    """Texte des segments couvrant [start, end]. Borne proprement."""
    segs = segments(doc, cfg)
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


def duration(doc, cfg=None):
    segs = segments(doc, cfg)
    if segs:
        last = max(segs, key=lambda s: float(s.get("start") or 0))
        return float(last.get("start") or 0) + float(last.get("duration") or 0)
    if isinstance(doc, list):
        return 0.0
    return float((doc or {}).get("duration") or (doc or {}).get("vod_duration") or 0)


def candidate_windows(doc, cfg, limit=None):
    """Propose des fenetres de segment autour des marqueurs d'enjeu.

    MARK1 ne "comprend" pas la video : il reperera les zones ou le texte dit
    quelque chose (chiffres, marqueurs d'enjeu) et propose une fenetre autour.
    L'operateur valide aux gates.

    Rend une liste de {start_sec, end_sec, source_text, score}.
    """
    from libs.s1_context import load_lang

    segs = segments(doc, cfg)
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
        total = duration(doc, cfg)
        if total and end > total:
            end = total
            start = max(0.0, end - target)
        if end - start < lo:
            continue
        used.append(start)
        out.append({
            "start_sec": round(start, 1),
            "end_sec": round(end, 1),
            "source_text": window_text(doc, start, end, cfg),
            "score": score,
        })
        if limit and len(out) >= limit:
            break
    return out
