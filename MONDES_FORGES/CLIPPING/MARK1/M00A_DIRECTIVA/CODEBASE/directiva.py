"""M00A_DIRECTIVA -- lit la directive de campagne depuis ARCHIVUM.

POURQUOI CETTE SOUS-FREGATE EXISTE
    La conformite de la caption est une condition de paiement, pas une precaution.
    Une campagne qui exige `@aishah` dans la caption ne paie pas un clip sans ce
    handle. MARK1 doit donc lire la directive a chaque siege, depuis ARCHIVUM.

CE QU'ELLE LIT
    ARCHIVUM/campaign/campaign_directive.json :
        campaign_id, language, platforms, payout.per_platform,
        caption_rules[plateforme] (handle, hashtags, caption_format),
        watermark, anti_spam, content_source, cycle

CE QU'ELLE CALCULE
    payout_usd_per_1k = payout_usd / views_per_unit * 1000
    C'est l'unite REELLE de la campagne, pas un CPM derive invente.

CE QU'ELLE NE FAIT PAS
    Aucun appel reseau. Aucune ecriture hors de son OUT/.
    Elle ne parle jamais a F00 : elle lit des fichiers d'ARCHIVUM, rien d'autre.
"""

from __future__ import annotations

import json
import os

_PLATFORM_ALIASES = {
    "tiktok": "tiktok",
    "twitter_x": "twitter_x",
    "x": "twitter_x",
    "x (twitter)": "twitter_x",
    "instagram_reels": "instagram_reels",
    "ig reels": "instagram_reels",
    "instagram": "instagram_reels",
    "youtube_shorts": "youtube_shorts",
    "youtube": "youtube_shorts",
}


def _norm_platform(name):
    """'YouTube Shorts' -> 'youtube_shorts'. Tolere les variantes de la directive."""
    raw = str(name or "").strip().lower()
    if raw in _PLATFORM_ALIASES:
        return _PLATFORM_ALIASES[raw]
    slug = raw.replace(" ", "_").replace("-", "_")
    return _PLATFORM_ALIASES.get(slug, slug)


def _norm_language(value, cfg):
    """Traduit 'English'/'French' vers 'en'/'fr' via config.languages."""
    raw = str(value or "").strip()
    if not raw:
        return cfg.get("default_language", "en")
    for code, spec in (cfg.get("languages") or {}).items():
        if raw.lower() in (code.lower(), str(spec.get("directive_value", "")).lower()):
            return code
    return raw.lower()


def load(path):
    """Lit le JSON de directive. Rend un dict, ou leve une erreur explicite."""
    if not os.path.exists(path):
        raise FileNotFoundError("directive introuvable : %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def parse(raw, cfg):
    """Transforme la directive brute en structure utilisable par MARK1.

    Cles rendues :
        campaign_id, creator_name, language, language_raw, platforms[],
        payouts{plateforme: {payout_usd, views_per_unit, usd_per_1k}},
        min_payout_usd, max_payout_usd, budget_usd,
        captions{plateforme: {handle, hashtags[], format}},
        watermark, anti_spam, content_source, cycle, missing[]
    """
    d = raw or {}
    missing = []

    campaign_id = d.get("campaign_id")
    if not campaign_id:
        missing.append("campaign_id")

    lang_raw = d.get("language")
    if not lang_raw:
        missing.append("language")
    language = _norm_language(lang_raw, cfg)

    platforms = []
    for p in (d.get("platforms") or []):
        code = _norm_platform(p)
        if code and code not in platforms:
            platforms.append(code)
    if not platforms:
        missing.append("platforms")

    # payout -> unite reelle
    payouts = {}
    payout_raw = d.get("payout") or {}
    per = payout_raw.get("per_platform") or {}
    for pname, spec in per.items():
        code = _norm_platform(pname)
        usd = float((spec or {}).get("payout_usd") or 0)
        views = float((spec or {}).get("views_per_unit") or 0)
        if views > 0:
            payouts[code] = {
                "payout_usd": usd,
                "views_per_unit": views,
                "usd_per_1k": round(usd / views * 1000.0, 6),
            }
    if not payouts:
        missing.append("payout")

    def _money(key):
        v = payout_raw.get(key)
        if v is None:
            return None
        digits = "".join(ch for ch in str(v) if ch.isdigit() or ch == ".")
        try:
            return float(digits)
        except ValueError:
            return None

    # captions par plateforme
    captions = {}
    for pname, spec in (d.get("caption_rules") or {}).items():
        code = _norm_platform(pname)
        s = spec or {}
        captions[code] = {
            "handle": s.get("handle") or s.get("handle_tag") or "",
            "hashtags": list(s.get("hashtags") or []),
            "format": s.get("caption_format") or "",
        }
    if not captions and platforms:
        missing.append("caption_rules")

    return {
        "campaign_id": campaign_id,
        "creator_name": d.get("creator_name") or "",
        "language": language,
        "language_raw": lang_raw,
        "platforms": platforms,
        "payouts": payouts,
        "min_payout_usd": _money("minimum"),
        "max_payout_usd": _money("maximum"),
        "budget_usd": _money("budget"),
        "captions": captions,
        "watermark": d.get("watermark") or {},
        "anti_spam": bool(d.get("anti_spam")),
        "content_source": d.get("content_source") or {},
        "cycle": d.get("cycle") or {},
        "source_file": d.get("source_file") or "",
        "missing": missing,
    }


def run(cfg, root):
    """Charge + parse. Rend (directive, message). Leve si introuvable."""
    rel = (cfg.get("directiva") or {}).get("path", "../../ARCHIVUM/campaign/campaign_directive.json")
    path = os.path.normpath(os.path.join(root, rel))
    raw = load(path)
    parsed = parse(raw, cfg)
    parsed["_path"] = path
    return parsed
