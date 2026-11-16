"""M00B_SELECTOR -- selectionne les segments et pose le cadre du titre.

CE QU'ELLE FAIT
    1. prend les assets du pack d'entree,
    2. applique S2_DURATION sur chaque borne,
    3. extrait du texte du segment (source_text / transcription) :
         - entity     : le sujet declare (directive) ou un nom propre frequent
         - numbers[]  : les chiffres (montants, durees, ages)
         - key_fact   : la phrase d'accroche la plus "enjeu" (proche d'un
                        marqueur d'enjeu de la langue)
    4. verifie que la langue de travail == langue de la directive.

CE QU'ELLE NE FAIT PAS
    Aucun appel reseau. Elle ne genere PAS de titre : elle pose le cadre
    que M00C utilisera. Elle ne parle jamais a F00.
"""

from __future__ import annotations

import json
import os
import re

_NUM = re.compile(r"\d[\d\s.,]*")
_STAKE_WORD = re.compile(r"[A-Za-z\u00C0-\u017F'-]+")


def _load_lang_markers(lang, root):
    """Marqueurs d'enjeu de la langue (stake_markers), depuis libs/lang/."""
    path = os.path.join(root, "libs", "lang", "%s.json" % (lang or "en"))
    if not os.path.exists(path):
        path = os.path.join(root, "libs", "lang", "en.json")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return tuple(data.get("stake_markers", []))


def _extract_numbers(text):
    out = []
    for m in _NUM.finditer(text or ""):
        v = m.group(0).replace(" ", "").replace(",", "")
        try:
            f = float(v)
        except ValueError:
            continue
        out.append(int(f) if f.is_integer() else f)
    # dedupe en gardant l'ordre
    seen, uniq = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def _extract_entities(text, subject, lang, root):
    """Entites capitalisees hors universels. Le sujet declare est prioritaire."""
    import sys
    sys.path.insert(0, root)
    from libs.s1_context import load_lang, _candidate_entities
    spec = load_lang(lang)
    candidates = [seq for seq, _ in _candidate_entities(text or "", spec)]
    subject_low = (subject or "").strip().lower()
    # le sujet passe en tete s'il apparait
    for seq in candidates:
        if subject_low and seq.lower() in subject_low:
            return [seq] + [s for s in candidates if s != seq]
    return candidates[:3]


def _key_fact(text, lang, root):
    """La premiere phrase qui contient un marqueur d'enjeu, sinon 8 premiers mots."""
    markers = _load_lang_markers(lang, root)
    lowered = (text or "").lower()
    for sent in re.split(r"[.!?]\s+", (text or "")):
        if any(m in lowered for m in markers):
            return sent.strip()[:160]
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    return " ".join(words[:8])


def select(pack, directive, cfg, root):
    """Rend la selection : une liste de segments avec leur cadre de titre.

    Chaque segment : id, start_sec, end_sec, source_text, entity, numbers[],
                     key_fact, langue, titre brut (celui du pack, s'il existe).

    `source_text` est CONSERVE tel quel depuis V3.6 : M2B_COMPLIANCE mesure le
    focus et le bait sur ce texte. L'oublier ici vidait la mesure et faisait
    echouer le bait a 0 % sur tous les assets, sans que rien ne le signale.
    """
    lang = directive.get("language") or cfg.get("default_language", "en")
    subject = directive.get("creator_name") or pack.get("subject") or ""
    markers = _load_lang_markers(lang, root)

    out = []
    for asset in (pack.get("assets") or []):
        text = (asset.get("source_text") or asset.get("transcript") or "").strip()
        seg = {
            "id": asset.get("id"),
            "start_sec": asset.get("start_sec"),
            "end_sec": asset.get("end_sec"),
            "source_text": text,
            "language": lang,
            "entity": _extract_entities(text, subject, lang, root),
            "numbers": _extract_numbers(text),
            "key_fact": _key_fact(text, lang, root),
            "title": asset.get("title") or "",
            "overlay_title": asset.get("overlay_title") or "",
            "caption": asset.get("caption") or "",
        }
        out.append(seg)
    return out
