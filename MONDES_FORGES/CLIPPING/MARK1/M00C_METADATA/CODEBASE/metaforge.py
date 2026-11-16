"""M00C_METADATA / metaforge -- les 4 champs de metadonnees, ZERO LLM.

CE QUE CE MODULE PRODUIT, sans aucun appel reseau :
    metadata_title  <= 85 car., gabarit + entite + fait
    description     <= 220 car., accroche + handle + hashtags, sans CTA
    tags[]          frequence + entites + termes de la directive, lowercase
    hashtags[]      ceux de la directive + 1-2 derives du sujet
    caption[plat]   handle + hashtags + #ad, par plateforme

La directive est la loi : les handles et hashtags viennent d'elle, jamais
d'une invention. Un handle invente = pas paye.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-z\u00C0-\u017F'-]+")

# Mots vides exclus des tags (EN + FR).
_STOP = frozenset("""
the a an and or but of in on at to for with from by is are was were be been
this that these those it he she they we you i his her their our your my
as if when while then than there here what which who whom how why
il elle ils elles le la les un une des de du au aux et ou mais donc car
ce cet cette ces son sa ses leur leurs mon ma mes ton ta tes
est sont etait etaient a ont avait avaient
que qui quoi dont ou si quand comme pour par dans sur sous avec sans
""".split())


def _clean(text):
    return " ".join(str(text or "").split())


def _words(text):
    return [w for w in _WORD.findall(text or "") if len(w) > 2]


def make_metadata_title(segment, directive, cfg):
    """Titre de publication. <= metadata_title_max_chars.

    Forme : '<Creator> <key_fact court>' quand c'est possible, sinon le
    key_fact seul, sinon le titre du pack. Toujours tronque proprement.
    """
    limit = int(cfg.get("metadata_title_max_chars", 85))
    creator = (directive.get("creator_name") or "").strip()
    fact = _clean(segment.get("key_fact") or "")
    fallback = _clean(segment.get("title") or "")

    # si le fait commence deja par le nom du createur, ne pas le repeter
    if creator and fact and fact.lower().startswith(creator.lower()):
        fact = fact[len(creator):].strip(" ,.;:-")

    for cand in (
        ("%s %s" % (creator, fact)).strip() if creator and fact else "",
        fact,
        fallback,
    ):
        if not cand:
            continue
        if len(cand) <= limit:
            return cand
        cut = cand[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:-")
        if len(cut) >= 20:
            return cut
    return (fallback or fact or "")[:limit]


def make_description(segment, directive, cfg):
    """Description de publication. <= description_max_chars, sans CTA.

    Forme observee dans le vrai pack de la forge :
        '<phrase de contenu>. #hashtag @handle'
    """
    limit = int(cfg.get("description_max_chars", 220))
    fact = _clean(segment.get("key_fact") or "")
    plat = (directive.get("platforms") or ["tiktok"])[0]
    cap = (directive.get("captions") or {}).get(plat) or {}

    handle = cap.get("handle") or ""
    hashtags = " ".join(cap.get("hashtags") or [])

    suffix = " ".join(x for x in (hashtags, handle) if x)
    body = fact
    if body and not body.endswith((".", "!", "?")):
        body += "."
    out = ("%s %s" % (body, suffix)).strip()
    if len(out) > limit:
        room = limit - len(suffix) - 1
        if room > 20:
            out = ("%s %s" % (body[:room].rsplit(" ", 1)[0].rstrip(" ,.;:-") + ".", suffix)).strip()
        else:
            out = suffix[:limit]
    return out


def make_tags(segment, directive, cfg, limit=10):
    """Tags lowercase : frequence dans le texte + entites + termes du sujet."""
    text = " ".join([
        _clean(segment.get("key_fact") or ""),
        _clean(segment.get("title") or ""),
        _clean(segment.get("source_text") or ""),
    ])
    counts = {}
    for w in _words(text):
        low = w.lower()
        if low in _STOP:
            continue
        counts[low] = counts.get(low, 0) + 1

    ordered = [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    # entites en tete (elles portent le sujet)
    ents = [e.lower().replace(" ", "") for e in (segment.get("entity") or [])]

    out = []
    for t in ents + ordered:
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def make_hashtags(segment, directive, cfg, limit=5):
    """Hashtags de la directive + 1-2 derives du sujet. Toujours avec #."""
    out = []
    for plat in (directive.get("platforms") or []):
        cap = (directive.get("captions") or {}).get(plat) or {}
        for h in (cap.get("hashtags") or []):
            if h.startswith("#") and h not in out:
                out.append(h)

    # derives : premiere entite en un seul mot
    for e in (segment.get("entity") or []):
        slug = re.sub(r"[^a-z0-9]", "", e.lower())
        if not slug:
            continue
        tag = "#" + slug
        if tag not in out:
            out.append(tag)
        if len(out) >= limit:
            break
    return out[:limit]


def make_caption(segment, directive, cfg, platform):
    """Caption par plateforme : handle de la directive + hashtags + disclosure."""
    cap = (directive.get("captions") or {}).get(platform) or {}
    handle = cap.get("handle") or ""
    hashtags = [h for h in (cap.get("hashtags") or []) if h]

    tags = cfg.get("disclosure_tags", ["#ad"])
    disclosure = tags[0] if cfg.get("require_disclosure", True) else ""

    title = _clean(segment.get("overlay_title") or segment.get("metadata_title")
                   or segment.get("title") or "")

    parts = [p for p in (title, handle) if p]
    if hashtags:
        parts.append(" ".join(hashtags))
    if disclosure:
        parts.append(disclosure)
    return " ".join(parts).strip()


def build(segment, directive, cfg, platform):
    """Assemble les 4 champs mecaniques + la caption pour une plateforme."""
    seg = dict(segment)
    seg["metadata_title"] = make_metadata_title(seg, directive, cfg)
    seg["description"] = make_description(seg, directive, cfg)
    seg["tags"] = make_tags(seg, directive, cfg)
    seg["hashtags"] = make_hashtags(seg, directive, cfg)
    seg["caption"] = make_caption(seg, directive, cfg, platform)
    seg["platform"] = platform

    # Vocabulaire interdit : on NETTOIE les champs mecaniques, on ne touche
    # pas a overlay_title (remplace automatiquement, il sonnerait faux ;
    # la porte M2B le refuse a la place).
    from libs import compliance
    for field in ("metadata_title", "description", "caption"):
        cleaned, hits = compliance.scrub(seg.get(field) or "", cfg)
        if hits:
            seg[field] = cleaned
            seg.setdefault("scrubbed", []).extend("%s:%s" % (field, h) for h in hits)
    seg["tags"] = [t for t in (compliance.scrub(x, cfg)[0] for x in seg.get("tags") or [])]
    seg["tags"] = [t for t in dict.fromkeys(seg["tags"]) if t]

    return seg
