"""libs/title_forge.py -- 12 gabarits de titre, zero LLM.

REGLE (decision D7, trouvee par un test) :
    generate() ne rend QUE des titres valides. Il n existe pas de repli qui
    rendrait un titre violant une porte. Si aucun gabarit ne passe, generate()
    rend une liste vide -- et l operateur ecrit son titre a la main.

Aucun seuil ici : tout vient de config/selection.json via `cfg`.
"""

from __future__ import annotations

import json
import os

# 12 gabarits. {number} et {stake} sont optionnels : un gabarit dont les trous
# ne sont pas remplis est simplement ecarte par generate().
TEMPLATES = (
    {"id": "T01", "stake": "perte", "pattern": "Il a perdu {number}"},
    {"id": "T02", "stake": "perte", "pattern": "Elle a tout perdu en {unit}"},
    {"id": "T03", "stake": "gain", "pattern": "Il a gagne {number} en une nuit"},
    {"id": "T04", "stake": "choc", "pattern": "Ce jour la tout a bascule"},
    {"id": "T05", "stake": "choc", "pattern": "Personne ne savait ce qui allait arriver"},
    {"id": "T06", "stake": "temoignage", "pattern": "Il raconte ce qu il a vraiment vu"},
    {"id": "T07", "stake": "temoignage", "pattern": "Elle explique comment elle a survecu"},
    {"id": "T08", "stake": "chiffre", "pattern": "{number} dollars en {unit}"},
    {"id": "T09", "stake": "chiffre", "pattern": "{number} personnes ont vu la meme chose"},
    {"id": "T10", "stake": "retournement", "pattern": "Tout le monde pensait qu il mentait"},
    {"id": "T11", "stake": "retournement", "pattern": "La verite est sortie trois jours apres"},
    {"id": "T12", "stake": "avertissement", "pattern": "Ne faites jamais ce qu il a fait"},
)

_STAKE_MARKERS_FR = (
    "perdu", "perd", "gagne", "paye", "dollars", "euro", "euros",
    "tout", "rien", "jamais", "survecu", "bascule", "verite", "mentait",
    "personne", "personnes", "nuit", "jour", "apres", "avant", "vue", "vraiment",
)


def _stake_markers(cfg, lang=None):
    """Marqueurs d'enjeu pour la langue. Repli FR si lexique absent.

    Sans ce chargement, une campagne `en` ne pouvait jamais rien faire passer :
    la liste etait francaise en dur (bug trouve en V3).
    """
    code = (lang or cfg.get("default_language") or "fr").lower()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang", "%s.json" % code)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            markers = json.load(fh).get("stake_markers") or []
        if markers:
            return tuple(m.lower() for m in markers)
    except (OSError, ValueError):
        pass
    return _STAKE_MARKERS_FR


def _word_count(text):
    return len([w for w in text.replace(",", " ").split() if w])


def _stoplist(cfg, lang=None):
    """Rend la stoplist CTA pour la langue demandee.

    Accepte les deux formes de config : une liste plate (V2) ou un dict par
    langue (V3). Retrocompatible : sans langue, on fusionne toutes les langues,
    ce qui est plus strict et ne laisse passer aucun CTA.
    """
    raw = cfg.get("cta_stoplist", ())
    if isinstance(raw, dict):
        if lang and lang in raw:
            return [s.lower() for s in raw[lang]]
        merged = []
        for v in raw.values():
            merged.extend(v)
        return [s.lower() for s in merged]
    return [s.lower() for s in raw]


def validate(title, cfg, lang=None):
    """Rend la liste des violations. Liste vide = titre valide.

    Codes : empty, too_long, too_short, too_many_words, cta, question_mark,
            no_stake.
    """
    t = (title or "").strip()
    v = []
    if not t:
        return ["empty"]

    lower = t.lower()

    if len(t) > int(cfg.get("title_max_chars", 60)):
        v.append("too_long")
    if len(t) < 12:
        v.append("too_short")

    wc = _word_count(t)
    if wc > int(cfg.get("title_max_words", 8)):
        v.append("too_many_words")
    if wc < int(cfg.get("title_min_words", 4)):
        v.append("too_short")

    if any(s in lower for s in _stoplist(cfg, lang)):
        v.append("cta")

    if not cfg.get("allowed_question_mark", False) and "?" in t:
        v.append("question_mark")

    if not any(m in lower for m in _stake_markers(cfg, lang)):
        v.append("no_stake")

    return v


def generate(fields, cfg, lang=None):
    """Rend les candidats valides, tries par ordre de gabarit.

    `fields` : {"text": ..., "subject": ..., "number": ..., "unit": ...}
    Chaque candidat : {"template_id", "stake", "text", "violations", "ok"}.
    Seuls les candidats ok=True sont rendus. Si aucun gabarit ne passe : [].
    """
    text = (fields.get("text") or "").strip()
    number = str(fields.get("number") or "").strip()
    unit = str(fields.get("unit") or "une nuit").strip()

    out = []
    seen = set()
    for tpl in TEMPLATES:
        pattern = tpl["pattern"]
        if "{number}" in pattern and not number:
            continue
        try:
            title = pattern.format(number=number, unit=unit) if (
                "{number}" in pattern or "{unit}" in pattern
            ) else pattern
        except (KeyError, IndexError):
            continue
        title = title.strip()
        if not title or title in seen:
            continue
        seen.add(title)
        viol = validate(title, cfg, lang)
        if viol:
            continue
        out.append({
            "template_id": tpl["id"],
            "stake": tpl["stake"],
            "text": title,
            "violations": viol,
            "ok": True,
        })
    return out
