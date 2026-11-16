"""M00E_PACKAGER -- assemble le pack V3 pour OMNIS_WATCH.

CE QUE CE PACK EST
    Le contrat entre MARK1 et OMNIS_WATCH. Il ne contient AUCUNE video : il
    dit quoi publier, avec quel titre, quelle caption, quel watermark, et il
    porte les tokens qui permettent de suivre un clip jusqu'a son paiement.

CE QU'IL PORTE (impose par le plan V3)
    mode, directive_source, language, source, asset_mode, subject,
    internal_terms, campaign, account, watermark{...}, assets[...],
    pack_token, generated_at

ORDRE IMPOSE
    watermark (M3) et transcription (M5) sont deja resolus quand on arrive ici.
    Le pack porte donc tout ce qu'OMNIS_WATCH doit savoir.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime


def _pack_token(payload):
    """8 hex stables : hash du contenu utile, pas de l'horodatage."""
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]


def _clip_token(asset_id, pack_token, today):
    return "%s-%s-%s" % (asset_id, today, pack_token)


def build(assets, directive, watermark, cfg, pack_meta):
    """Assemble et rend le dict du pack V3.

    `assets` : liste de segments complets (overlay + metadonnees + tokens).
    """
    now = datetime.now()
    today = now.strftime("%Y%m%d")

    source = {
        "campaign_id": directive.get("campaign_id"),
        "directive_path": directive.get("_path") or directive.get("source_file"),
        "platforms": directive.get("platforms"),
        "payouts_usd_per_1k": {k: v.get("usd_per_1k")
                               for k, v in (directive.get("payouts") or {}).items()},
    }

    content_sig = [{
        "id": a.get("id"),
        "overlay_title": a.get("overlay_title"),
        "metadata_title": a.get("metadata_title"),
        "caption": a.get("caption"),
    } for a in assets]
    pack_token = _pack_token(content_sig)

    out_assets = []
    for a in assets:
        item = {
            "id": a.get("id"),
            "start_sec": a.get("start_sec"),
            "end_sec": a.get("end_sec"),
            "overlay_title": a.get("overlay_title"),
            "metadata_title": a.get("metadata_title"),
            "description": a.get("description"),
            "tags": a.get("tags") or [],
            "hashtags": a.get("hashtags") or [],
            "caption": a.get("caption"),
            "clip_token": _clip_token(a.get("id"), pack_token, today),
            "exported_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if a.get("transcript"):
            item["transcript"] = a["transcript"]
        out_assets.append(item)

    return {
        "mode": pack_meta.get("mode", "mark1"),
        "overlay_mode": pack_meta.get("overlay_mode", "oracle"),
        "directive_source": directive.get("campaign_id"),
        "language": directive.get("language"),
        "source": source,
        "asset_mode": pack_meta.get("asset_mode", cfg.get("default_asset_mode", "blur")),
        "subject": directive.get("creator_name") or pack_meta.get("subject") or "",
        "internal_terms": directive.get("internal_terms") or [],
        "campaign": {
            "campaign_id": directive.get("campaign_id"),
            "language": directive.get("language"),
            "platforms": directive.get("platforms"),
            "anti_spam": directive.get("anti_spam"),
        },
        "account": pack_meta.get("account") or {},
        "watermark": watermark,
        "assets": out_assets,
        "pack_token": pack_token,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write(pack, cfg, root):
    """Ecrit le pack dans EXPORT/ et rend le chemin."""
    rel = cfg.get("export_dir", "../EXPORT")
    base = os.path.normpath(os.path.join(root, rel))
    os.makedirs(base, exist_ok=True)
    name = "%s%s.json" % (cfg.get("export_prefix", "production_pack_mark1_"),
                          pack["pack_token"])
    path = os.path.join(base, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, ensure_ascii=False, indent=2)
    return path
