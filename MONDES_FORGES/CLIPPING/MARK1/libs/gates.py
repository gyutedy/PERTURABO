"""libs/gates.py -- les portes. Une porte = une fonction (ok, code, message).

DOUZE CODES, DIX IMPLEMENTEES ICI (V3.6).
    G0_PACK, D0_DIRECTIVE, M0B_CYCLE, M1_SELECTION, M2_METADATA,
    M2B_COMPLIANCE, M3_WATERMARK, M5_VOX, A1_ACCOUNT, A2_CAMPAIGN,
    X1_EXPORT                     -> implementees et APPELEES par cmd_export
    C2_DISCLOSURE, S2_DURATION    -> implementees mais non appelees : M2 et G0
                                     font deja le travail (redondance assumee)

CHANGEMENT V3.5 : A1_ACCOUNT et A2_CAMPAIGN etaient ecrites et testees mais
JAMAIS appelees par cmd_export. Le guide promettait qu'un compte banni ou une
campagne non financee ne pouvait pas exporter : c'etait faux. Elles sont
maintenant branchees avant l'export.

CHANGEMENT V3.5 : M3_WATERMARK ne juge plus l'opacite, la position ni la taille.
MARK1 ne produit pas de video : il DECRIT le watermark pour OMNIS_WATCH, qui le
pose. Verifier l'opacite ici refusait un PNG conforme des que la campagne
changeait de seuil, sans qu'aucun pixel n'ait ete regarde. Le seuil reste dans
la directive (watermark_rules.json) et voyage dans le pack.

CHANGEMENT V3.6 : M2B_COMPLIANCE ne MESURE plus le focus, elle ENREGISTRE la
declaration de l'operateur. Voir libs/compliance.py pour le detail et le motif.

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
    "M0B_CYCLE",
    "M2B_COMPLIANCE",
    "G0_PACK",
    "A1_ACCOUNT",
    "A2_CAMPAIGN",
    "C2_DISCLOSURE",
    "S2_DURATION",
    "X1_EXPORT",
)

# Codes dont une fonction existe dans ce module.
IMPLEMENTED = (
    "D0_DIRECTIVE",
    "M1_SELECTION",
    "M2_METADATA",
    "M3_WATERMARK",
    "M5_VOX",
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
            reasons.append("%s: aucun texte (key_fact vide : ni source_text ni "
                           "transcript fournis au selecteur)" % seg.get("id"))

    if reasons:
        return False, "M1_SELECTION", "; ".join(reasons)
    return True, "M1_SELECTION", "%d segments, langue %s" % (len(sel), lang_dir)


def m2_metadata(assets, cfg, had_oracle=False):
    """Toutes les metadonnees sont-elles completes et sous contrainte ?

    Rouge si : overlay_title absent ou invalide, metadata_title trop long,
    description trop longue, 0 tag, 0 hashtag, caption sans disclosure.
    """
    if not assets:
        return False, "M2_METADATA", "aucun asset"

    from libs import title_forge
    reasons = []
    tmax = int(cfg.get("metadata_title_max_chars", 85))
    dmax = int(cfg.get("description_max_chars", 220))
    require_disc = bool(cfg.get("require_disclosure", True))
    disc = [t.lower() for t in cfg.get("disclosure_tags", ["#ad"])]

    for a in assets:
        aid = a.get("id")
        ot = a.get("overlay_title") or ""
        viol = title_forge.validate(ot, cfg, a.get("language"))
        if viol:
            reasons.append("%s: overlay %s" % (aid, ",".join(viol)))
        if len(a.get("metadata_title") or "") > tmax:
            reasons.append("%s: metadata_title > %d" % (aid, tmax))
        if len(a.get("description") or "") > dmax:
            reasons.append("%s: description > %d" % (aid, dmax))
        if not a.get("tags"):
            reasons.append("%s: 0 tag" % aid)
        if not a.get("hashtags"):
            reasons.append("%s: 0 hashtag" % aid)
        if require_disc:
            cap = (a.get("caption") or "").lower()
            if not any(d in cap for d in disc):
                reasons.append("%s: caption sans disclosure" % aid)

    if reasons:
        return False, "M2_METADATA", "; ".join(reasons)
    return True, "M2_METADATA", "%d assets valides%s" % (
        len(assets), " (via ORACLE)" if had_oracle else "")


def m3_watermark(wm, directive, cfg):
    """Le watermark existe-t-il et peut-il etre livre ?

    MARK1 ne pose AUCUN watermark : il n'a pas le droit de toucher une video
    (doctrine CLIPPING). `vexillum.py` decrit seulement comment le poser, et
    `packager` embarque le fichier dans le pack pour qu'OMNIS_WATCH le trouve.

    Donc le seul fait verifiable ici est : le fichier est-il la, non vide, et
    pourra-t-il etre copie dans EXPORT/. L'opacite, la position et la taille
    sont des CONSIGNES transmises au consommateur, pas des proprietes que
    MARK1 peut controler. Les verifier ici serait juger le travail d'un autre.
    (Avant V3.5 cette porte comparait l'opacite a un 0.75 ecrit en dur, ce
    qui violait R1 et refusait un PNG conforme le jour ou la regle changeait.)

    Le format est libre (png / jpeg / jpg, V3.7) : la campagne fournit ce
    qu'elle veut, MARK1 ne convertit rien et ne se plaint pas du format.
    """
    platforms = (directive or {}).get("platforms") or []
    if not platforms:
        return False, "M3_WATERMARK", "aucune plateforme"

    if not isinstance(wm, dict):
        return False, "M3_WATERMARK", "descriptif watermark absent"

    reasons = []
    if wm.get("required") and not wm.get("exists"):
        reasons.append("watermark requis mais absent ou vide")
    if wm.get("exists") and not wm.get("path"):
        reasons.append("watermark present sans chemin exploitable")

    if reasons:
        return False, "M3_WATERMARK", "; ".join(dict.fromkeys(reasons))

    fmt = (wm.get("format") or "").upper()
    return True, "M3_WATERMARK", "%s%s (%s)" % (
        wm.get("file") or "aucun",
        " [%s]" % fmt if fmt else "",
        "requis" if wm.get("required") else "optionnel")


def m5_vox(vox_results, cfg):
    """La transcription est-elle disponible pour chaque segment ?

    Une transcription vide est toleree SI le pack portait deja source_text
    (la raison le dit). Elle est refusee si le segment n'a ni l'un ni l'autre.
    """
    if not vox_results:
        return False, "M5_VOX", "aucun resultat de transcription"

    reasons = []
    for r in vox_results:
        if not (r.get("transcript") or "").strip():
            reason = r.get("reason") or ""
            if "source_text du pack" in reason:
                continue
            reasons.append("%s: %s" % (r.get("asset_id"), reason or "transcription vide"))

    if reasons:
        return False, "M5_VOX", "; ".join(reasons)
    with_text = sum(1 for r in vox_results if (r.get("transcript") or "").strip())
    return True, "M5_VOX", "%d segments, %d transcrits" % (len(vox_results), with_text)


def m0b_cycle(directive, cfg, today=None):
    """Le cycle de campagne est-il encore ouvert ?

    La directive le dit : "Always follow the announcement for the current
    cycle". Un pack exporte avec un cycle expire est refuse au paiement,
    sans que rien ne l'ait signale. Cette porte le signale.
    """
    from datetime import date, datetime

    cycle = (directive or {}).get("cycle") or {}
    start = cycle.get("start")
    end = cycle.get("end")
    if not end:
        return False, "M0B_CYCLE", "cycle.end absent de la directive"

    if today is None:
        today = date.today()
    elif isinstance(today, str):
        today = datetime.strptime(today[:10], "%Y-%m-%d").date()

    try:
        end_d = datetime.strptime(str(end)[:10], "%Y-%m-%d").date()
    except ValueError:
        return False, "M0B_CYCLE", "cycle.end illisible : %r" % (end,)

    if today > end_d:
        return False, "M0B_CYCLE", "cycle expire le %s (aujourd'hui %s)" % (end_d, today)

    if start:
        try:
            start_d = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
            if today < start_d:
                return False, "M0B_CYCLE", "cycle pas encore ouvert (%s)" % start_d
        except ValueError:
            pass

    return True, "M0B_CYCLE", "cycle %s -> %s, ouvert" % (start or "?", end_d)


def m2b_compliance(assets, cfg):
    """Les regles de contenu verifiables sont-elles respectees ?

    Couvre : vocabulaire interdit, main focus, bait, negative PR.
    Ne couvre PAS : logos, caption editee, post prive -- MARK1 ne produit
    pas la video, ces regles appartiennent a OMNIS_WATCH.
    """
    from libs import compliance

    if not assets:
        return False, "M2B_COMPLIANCE", "aucun asset"

    reasons = []
    for a in assets:
        ok, why = compliance.check_asset(a, cfg)
        if not ok:
            reasons.append("%s: %s" % (a.get("id"), " | ".join(why)))

    if reasons:
        return False, "M2B_COMPLIANCE", "; ".join(reasons)
    return True, "M2B_COMPLIANCE", "%d assets conformes" % len(assets)


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
        # V3 : le titre n'est PLUS exige a l'entree. C'est MARK1 qui le
        # produit (overlay M00C). L'exiger en amont contredisait la doctrine
        # "le moteur produit, l'operateur valide".
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
