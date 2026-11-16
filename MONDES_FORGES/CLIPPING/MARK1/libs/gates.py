"""libs/gates.py -- les portes. Une porte = une fonction (ok, code, message).

ONZE CODES, HUIT IMPLEMENTEES EN V2.
    G0_PACK, A1_ACCOUNT, A2_CAMPAIGN, S1_CONTEXT, C2_DISCLOSURE,
    S2_DURATION, X1_EXPORT          -> implementees ici
    T1_TITLE, T2_HOOK, S3_HERESY    -> codes reserves, verifies par les
                                       fonctions de libs/ (title_forge, s1_context)

CHANGEMENT V2 : R1_RENDER est supprimee et remplacee par X1_EXPORT.
R1 verifiait un fichier MP4 (taille, dimensions, codec). MARK1 ne produit plus
de MP4 : la porte verifie desormais le pack livrable. Motif : doctrine CLIPPING.

CHANGEMENT V2 (aligne sur CONTRACTS/clipping_rules.md) :
    C2_DISCLOSURE est nouvelle et implemente la regle C2 du forge
    (#ad / #sponsored obligatoire dans la caption). Elle etait absente du CDC V1.
"""

from __future__ import annotations

CODES = (
    "D0_DIRECTIVE",
    "G0_PACK",
    "A1_ACCOUNT",
    "A2_CAMPAIGN",
    "S1_CONTEXT",
    "C2_DISCLOSURE",
    "S2_DURATION",
    "X1_EXPORT",
    "T1_TITLE",
    "T2_HOOK",
    "S3_HERESY",
)

# Codes dont une fonction existe dans ce module.
IMPLEMENTED = (
    "D0_DIRECTIVE",
    "M1_SELECTION",
    "G0_PACK",
    "A1_ACCOUNT",
    "A2_CAMPAIGN",
    "C2_DISCLOSURE",
    "S2_DURATION",
    "X1_EXPORT",
)


def d0_directive(directive, cfg):
    """La directive de campagne est-elle complete et utilisable ?

    C'est la porte qui applique la doctrine : MARK1 lit la directive depuis
    ARCHIVUM a CHAQUE siege, et refuse un siege qui ne s'appuie pas sur une
    directive valide. Les champs manquants sont listes, pas devines.
    """
    d = directive or {}
    missing = list(d.get("missing") or [])
    reasons = []

    if not d.get("campaign_id"):
        missing.append("campaign_id")
    if not d.get("language"):
        missing.append("language")

    if missing:
        reasons.append("champs manquants: " + ", ".join(missing))

    platforms = d.get("platforms") or []
    if not platforms:
        reasons.append("aucune plateforme")

    # langue : la directive doit etre EN ou FR (connue du moteur)
    langs = {code for code, spec in (cfg.get("languages") or {}).items()
             if spec.get("directive_value")}
    lang = d.get("language") or ""
    if lang not in langs and lang not in (cfg.get("languages") or {}):
        reasons.append("langue %r inconnue (attendu %s)" % (lang, sorted(langs)))

    # payout : unite reelle de la campagne, comparee au plancher
    rate = None
    for code, spec in (d.get("payouts") or {}).items():
        rate = spec.get("usd_per_1k")
        break
    plancher = float(cfg.get("min_cpm_usd_per_1k", 0.15))
    if rate is None:
        reasons.append("aucun payout exploitable")
    elif rate < plancher:
        reasons.append("payout %.4f $/1k < plancher %.2f $/1k" % (rate, plancher))

    # captions : un handle au moins
    captions = d.get("captions") or {}
    if not captions:
        reasons.append("aucune regle de caption")

    if reasons:
        return False, "D0_DIRECTIVE", "; ".join(reasons)
    return True, "D0_DIRECTIVE", "%s | %s | %.2f $/1k | %d plates | %d captions" % (
        d.get("campaign_id"), d.get("language"),
        rate if rate is not None else 0.0,
        len(platforms), len(captions))


def m1_selection(selection, directive, cfg):
    """La selection est-elle exploitable ?

    Refuse si : 0 segment ; langue inconnue ; langue != directive ;
    un segment hors bornes ; un segment sans texte (cadre vide).
    """
    sel = selection or []
    if not sel:
        return False, "M1_SELECTION", "aucun segment"

    lang_dir = (directive or {}).get("language") or ""
    reasons = []
    for seg in sel:
        if not seg.get("id"):
            reasons.append("segment sans id")
        if seg.get("language") and lang_dir and seg["language"] != lang_dir:
            reasons.append("%s: langue %s != directive %s"
                           % (seg.get("id"), seg["language"], lang_dir))
        try:
            dur = float(seg.get("end_sec") or 0) - float(seg.get("start_sec") or 0)
        except (TypeError, ValueError):
            reasons.append("%s: bornes invalides" % seg.get("id")); continue
        lo = float(cfg.get("min_segment_sec", 8)); hi = float(cfg.get("max_segment_sec", 90))
        if dur < lo or dur > hi:
            reasons.append("%s: %.1fs hors [%.0f,%.0f]" % (seg.get("id"), dur, lo, hi))
        if not (seg.get("key_fact") or "").strip():
            reasons.append("%s: aucun texte (source_text manquant)" % seg.get("id"))

    if reasons:
        return False, "M1_SELECTION", "; ".join(reasons)
    return True, "M1_SELECTION", "%d segments, langue %s" % (len(sel), lang_dir)


def g0_pack(pack, cfg):
    """Le pack d entree est-il conforme au contrat MARK1 ?

    Seuil G0 sorti du code : `max_segment_sec` vient de cfg, pas d une constante.
    """
    if not isinstance(pack, dict):
        return False, "G0_PACK", "pack n est pas un objet JSON"

    if pack.get("mode") != "mark1":
        return False, "G0_PACK", "mode attendu 'mark1', recu %r" % (pack.get("mode"),)

    source = pack.get("source") or {}
    if not source.get("vod_url"):
        return False, "G0_PACK", "source.vod_url manquant"

    render = pack.get("asset_mode") or pack.get("render") or {}
    if isinstance(render, dict):
        style = render.get("style") or render.get("mode")
    else:
        style = render
    allowed = cfg.get("allowed_asset_modes", ["blur", "reframing"])
    if style and style not in allowed:
        return False, "G0_PACK", "asset_mode %r hors %r" % (style, list(allowed))

    assets = pack.get("assets")
    if not isinstance(assets, list) or not assets:
        return False, "G0_PACK", "assets[] vide ou absent"

    seen = set()
    max_seg = float(cfg.get("max_segment_sec", 90))
    min_seg = float(cfg.get("min_segment_sec", 8))
    for a in assets:
        aid = a.get("id")
        if not aid:
            return False, "G0_PACK", "asset sans id"
        if aid in seen:
            return False, "G0_PACK", "id %r en double" % (aid,)
        seen.add(aid)
        if not str(a.get("title") or "").strip():
            return False, "G0_PACK", "asset %s : titre vide" % (aid,)
        try:
            start = float(a.get("start_sec"))
            end = float(a.get("end_sec"))
        except (TypeError, ValueError):
            return False, "G0_PACK", "asset %s : bornes non numeriques" % (aid,)
        if end <= start:
            return False, "G0_PACK", "asset %s : end_sec <= start_sec" % (aid,)
        dur = end - start
        if dur > max_seg:
            return False, "G0_PACK", "asset %s : %.1fs > %.0fs" % (aid, dur, max_seg)
        if dur < min_seg:
            return False, "G0_PACK", "asset %s : %.1fs < %.0fs" % (aid, dur, min_seg)

    return True, "G0_PACK", "%d assets" % len(assets)


def a1_account(account, cfg):
    """Le compte est-il autorise a publier ? (regle C5 du forge)"""
    acc = account or {}
    if acc.get("banned"):
        return False, "A1_ACCOUNT", "compte banni"

    try:
        days = int(acc.get("warmup_days") or 0)
    except (TypeError, ValueError):
        return False, "A1_ACCOUNT", "warmup_days non numerique"

    need = int(cfg.get("min_warmup_days", 7))
    if days < need:
        return False, "A1_ACCOUNT", "warmup %dj < %dj" % (days, need)
    return True, "A1_ACCOUNT", "warmup %dj" % days


def a2_campaign(verdict):
    """La campagne est-elle eligible ? (`verdict` vient de libs.campaign.evaluate)"""
    v = verdict or {}
    if v.get("eligible"):
        return True, "A2_CAMPAIGN", "CPM %.2f $/1k, net %.4f" % (
            v.get("rate_usd_per_1k") or 0.0,
            v.get("net_per_1k_usd") or 0.0,
        )
    reasons = ", ".join(v.get("reasons") or ["inconnu"])
    return False, "A2_CAMPAIGN", reasons


def c2_disclosure(asset, cfg):
    """Regle C2 du forge : #ad ou #sponsored visible dans la caption.

    Sans cette mention, la campagne rejette et la plateforme shadowban.
    Ce n est pas une precaution : c est une condition de paiement.
    """
    if not cfg.get("require_disclosure", True):
        return True, "C2_DISCLOSURE", "desactive par config"

    tags = [t.lower() for t in cfg.get("disclosure_tags", ["#ad", "#sponsored"])]
    caption = str((asset or {}).get("caption") or "").lower()
    if not caption:
        return False, "C2_DISCLOSURE", "%s : caption absente" % ((asset or {}).get("id"),)
    if any(t in caption for t in tags):
        return True, "C2_DISCLOSURE", "mention presente"
    return False, "C2_DISCLOSURE", "%s : aucune mention parmi %r" % (
        (asset or {}).get("id"), tags)


def s2_duration(start, end, cfg):
    """Les bornes du segment tiennent-elles dans min/max_segment_sec ?"""
    try:
        s = float(start)
        e = float(end)
    except (TypeError, ValueError):
        return False, "S2_DURATION", "bornes non numeriques"

    if e <= s:
        return False, "S2_DURATION", "end <= start"
    dur = e - s
    lo = float(cfg.get("min_segment_sec", 8))
    hi = float(cfg.get("max_segment_sec", 90))
    if dur < lo:
        return False, "S2_DURATION", "%.1fs < %.0fs" % (dur, lo)
    if dur > hi:
        return False, "S2_DURATION", "%.1fs > %.0fs" % (dur, hi)
    return True, "S2_DURATION", "%.1fs" % dur


def x1_export(pack, cfg):
    """La porte finale (ex-R1_RENDER). Verifie le PACK, pas un fichier video.

    Criteres : mode, asset_mode autorise, un clip_token non vide et unique par
    asset. Le pack doit etre ecrit dans EXPORT/ par l appelant : cette porte ne
    fait pas d ecriture disque, elle valide.
    """
    if not isinstance(pack, dict):
        return False, "X1_EXPORT", "pack invalide"

    if pack.get("mode") != "mark1":
        return False, "X1_EXPORT", "mode %r" % (pack.get("mode"),)

    render = pack.get("asset_mode") or pack.get("render") or {}
    style = render.get("style") if isinstance(render, dict) else render
    allowed = cfg.get("allowed_asset_modes", ["blur", "reframing"])
    if not style:
        return False, "X1_EXPORT", "asset_mode absent"
    if style not in allowed:
        return False, "X1_EXPORT", "asset_mode %r hors %r" % (style, list(allowed))

    if not pack.get("pack_token"):
        return False, "X1_EXPORT", "pack_token absent"

    assets = pack.get("assets") or []
    if not assets:
        return False, "X1_EXPORT", "aucun asset"

    seen = set()
    for a in assets:
        tok = str(a.get("clip_token") or "").strip()
        if not tok:
            return False, "X1_EXPORT", "asset %s : clip_token absent" % (a.get("id"),)
        if tok in seen:
            return False, "X1_EXPORT", "clip_token en double : %s" % (tok,)
        seen.add(tok)
        if not a.get("exported_at"):
            return False, "X1_EXPORT", "asset %s : exported_at absent" % (a.get("id"),)

    return True, "X1_EXPORT", "%d clip_tokens uniques, mode=%s" % (len(seen), style)
