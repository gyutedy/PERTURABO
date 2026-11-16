"""libs/compliance.py -- les regles de contenu que MARK1 PEUT verifier.

CE QUI EST VERIFIABLE PAR MARK1, ET POURQUOI
    MARK1 ne voit pas la video. Mais il produit du TEXTE et il lit la
    transcription. Donc il peut verifier exactement trois familles de regles :

    1. vocabulaire interdit  -- la campagne interdit "OF creator". MARK1 ecrit
       les tags, la description, la caption : il peut les nettoyer.
    2. main focus            -- "Aishah doit etre le sujet". Mesure sur la
       transcription : si elle n'y est pas, elle n'est pas le sujet.
    3. bait / negative PR    -- l'overlay ne doit pas promettre ce que le
       texte ne tient pas, ni attaquer personnellement.

CE QUI N'EST PAS VERIFIABLE, ET NE DOIT PAS ETRE ICI
    logos visibles, caption non editee sur IG, post prive, engagement
    organique. MARK1 ne produit pas la video : c'est OMNIS_WATCH et
    l'operateur. Les mettre ici serait du theatre.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-z\u00C0-\u017F0-9']+")


def _norm(text):
    return " " + " ".join(_WORD.findall((text or "").lower())) + " "


def find_forbidden(text, cfg):
    """Rend la liste des termes interdits presents dans le texte."""
    ft = cfg.get("forbidden_terms") or {}
    blob = _norm(text)
    found = []
    for term in ft.get("terms") or []:
        if _norm(term).strip() in blob:
            found.append(term)
    return found


def scrub(text, cfg):
    """Remplace les termes interdits par l'alternative approuvee.

    Rend (texte_nettoye, [termes_remplaces]). Utilise pour les champs
    mecaniques (tags, description, caption). Jamais pour overlay_title :
    un titre remplace automatiquement sonne faux, donc on refuse.
    """
    ft = cfg.get("forbidden_terms") or {}
    repl = ft.get("replacements") or {}
    out = text or ""
    hits = []
    for term in ft.get("terms") or []:
        target = repl.get(term) or (ft.get("approved_alternatives") or ["content creator"])[0]
        article = "an" if target[0] in "aeiou" else "a"
        esc = re.escape(term)
        # avec article devant : "an onlyfans star" -> "a content creator star"
        art = re.compile(r"\b(an?)\s+" + esc + r"\b", re.IGNORECASE)
        if art.search(out):
            out = art.sub(article + " " + target, out)
            hits.append(term)
            continue
        word = re.compile(r"\b" + esc + r"\b", re.IGNORECASE)
        if word.search(out):
            out = word.sub(target, out)
            hits.append(term)
    return out, hits


def focus_report(transcript, subject, segment_text, cfg, declared=None):
    """Le focus est-il etabli pour ce segment ?

    V3.6 : on ne compte plus les mots comme critere unique. Deux voies :

    1. DECLARATION -- l'operateur affirme le focus (`focus_declared` du pack).
       C'est la voie normale : la regle de la directive est visuelle
       ("as long as she's featured in the clip") et MARK1 ne voit rien.
       Rend {ok:True, source:"declared"} ; le pack portera la mention, pour
       qu'OMNIS_WATCH et l'operateur assument la declaration.
    2. MESURE -- repli quand rien n'est declare : on compte les mentions du
       nom, comme en V3.1. Zero mention sans declaration = refus : on ne
       clippe pas en silence sur une campagne qui exige "main focus".

    Rend {ok, mentions, ratio, reason, source}.
    """
    spec = cfg.get("focus") or {}
    subj = (subject or "").strip()
    text = (segment_text or transcript or "").lower()

    # -- voie 1 : la declaration de l'operateur --
    if isinstance(declared, dict) and declared.get("asserted_by"):
        return {"ok": True, "mentions": None, "ratio": None,
                "source": "declared",
                "asserted_by": declared.get("asserted_by"),
                "evidence": declared.get("evidence") or "",
                "reason": ""}
    if declared is True:
        return {"ok": True, "mentions": None, "ratio": None,
                "source": "declared", "asserted_by": "operator",
                "evidence": "", "reason": ""}

    if not subj:
        return {"ok": True, "mentions": 0, "ratio": 0.0, "source": "none",
                "reason": "pas de sujet declare"}

    min_ratio = float(spec.get("min_mention_ratio", 0.15))
    # un segment court ne peut pas atteindre un ratio eleve : plancher de mots
    min_words_for_ratio = int(spec.get("min_words_for_ratio", 40))
    min_mentions = int(spec.get("min_mentions", 1))

    tokens = _WORD.findall(subj.lower())
    if not tokens:
        return {"ok": True, "mentions": 0, "ratio": 0.0, "source": "none",
                "reason": "sujet vide"}

    # le nom complet ou le prenom seul comptent
    full = " ".join(tokens)
    mentions = text.count(full)
    if mentions == 0 and len(tokens) > 1:
        mentions = text.count(tokens[0])
    if mentions == 0 and len(tokens) > 1:
        mentions = text.count(tokens[-1])

    words = _WORD.findall(text)
    ratio = round(mentions / max(1, len(words)), 4)

    if mentions < min_mentions:
        return {"ok": False, "mentions": mentions, "ratio": ratio,
                "source": "measured",
                "reason": "sujet absent du segment (0 mention) et aucune "
                          "declaration de focus dans le pack"}
    if len(words) >= min_words_for_ratio and ratio < min_ratio:
        return {"ok": False, "mentions": mentions, "ratio": ratio,
                "source": "measured",
                "reason": "sujet trop peu present (%.1f%% < %.1f%%) et aucune "
                          "declaration de focus dans le pack"
                          % (ratio * 100, min_ratio * 100)}
    return {"ok": True, "mentions": mentions, "ratio": ratio,
            "source": "measured", "reason": ""}


def _content_words(text):
    return set(w for w in _WORD.findall((text or "").lower()) if len(w) > 3)


def bait_report(overlay, source_text, cfg):
    """L'overlay est-il soutenu par le texte source ?

    Un titre de bait promet ('shocking', 'you won't believe') sans que rien
    dans le texte ne le porte. On mesure le recouvrement des mots de contenu :
    si l'overlay parle de choses absentes du segment, c'est du bait.
    """
    spec = cfg.get("bait") or {}
    require = float(spec.get("require_support_ratio", 0.5))
    hype = [h for h in (spec.get("hype_markers") or []) if h in (overlay or "").lower()]

    ov = _content_words(overlay)
    src = _content_words(source_text)
    if not ov:
        return {"ok": True, "ratio": 1.0, "hype": hype, "reason": ""}

    supported = ov & src
    ratio = round(len(supported) / len(ov), 4)

    if hype and ratio < require:
        return {"ok": False, "ratio": ratio, "hype": hype,
                "reason": "marqueurs de hype non soutenus par le texte (%s)"
                          % ", ".join(hype[:3])}
    if ratio < require:
        return {"ok": False, "ratio": ratio, "hype": hype,
                "reason": "overlay non soutenu par le texte (%.0f%% < %.0f%%)"
                          % (ratio * 100, require * 100)}
    return {"ok": True, "ratio": ratio, "hype": hype, "reason": ""}


def negative_pr_report(text, cfg):
    """Marqueurs d'attaque personnelle. Rend {ok, hits, reason}."""
    spec = cfg.get("negative_pr") or {}
    blob = _norm(text)
    hits = [m for m in (spec.get("markers") or []) if _norm(m).strip() and _norm(m).strip() in blob]
    if hits:
        return {"ok": False, "hits": hits,
                "reason": "negative PR : " + ", ".join(hits[:3])}
    return {"ok": True, "hits": [], "reason": ""}


def check_asset(asset, cfg):
    """Tous les controles de contenu pour un asset. Rend (ok, [raisons])."""
    reasons = []

    src = asset.get("source_text") or asset.get("transcript") or ""
    overlay = asset.get("overlay_title") or ""

    # 1. vocabulaire interdit dans l'overlay = refus (jamais de remplacement)
    bad = find_forbidden(overlay, cfg)
    if bad:
        reasons.append("overlay contient un terme interdit : %s" % ", ".join(bad))

    # 2. focus : declaration de l'operateur, sinon mesure (voir focus_report)
    f = focus_report(asset.get("transcript") or "", asset.get("subject") or "",
                     src, cfg, declared=asset.get("focus_declared"))
    if not f["ok"]:
        reasons.append("focus : " + f["reason"])

    # 3. bait
    b = bait_report(overlay, src, cfg)
    if not b["ok"]:
        reasons.append("bait : " + b["reason"])

    # 4. negative PR sur l'ensemble du texte produit
    n = negative_pr_report(" ".join([overlay, asset.get("metadata_title") or "",
                                     asset.get("description") or ""]), cfg)
    if not n["ok"]:
        reasons.append(n["reason"])

    return (not reasons), reasons
