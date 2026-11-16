"""M00E_PACKAGER -- assemble le pack V3 pour OMNIS_WATCH.

CE QUE CE PACK EST
    Le contrat entre MARK1 et OMNIS_WATCH. Il ne contient AUCUNE video : il
    dit quoi publier, avec quel titre, quelle caption, quel watermark, et il
    porte les tokens qui permettent de suivre un clip jusqu'a son paiement.

CE QU'IL PORTE (impose par le plan V3)
    mode, directive_source, language, source, asset_mode, subject,
    internal_terms, campaign, account, focus_declared, watermark{...},
    assets[...], pack_token, generated_at

FOCUS_DECLARED (V3.6)
    La campagne exige "main focus or topic", mais MARK1 ne voit pas la video :
    il ne peut pas prouver qu'elle est a l'ecran. Quand l'operateur l'affirme
    (pack d'entree : `focus_declared`), la declaration voyage DANS le pack
    livrable. C'est ce qui rend la regle auditable en aval au lieu d'etre
    devinee ici.

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
    """8 hex stables : delegue a `libs.tokens`, source de verite unique.

    V3.8 : ce module avait sa PROPRE formule (hash des 4 champs par asset),
    et `libs/tokens.pack_token` en avait une autre (hash du pack entier).
    Sur un meme pack ils rendaient deux tokens differents, donc
    `clip_tokens(pack)` pouvait fabriquer des identites qui ne correspondaient
    a aucun clip livre. Un seul calcul desormais, et c'est `libs.tokens`.
    """
    from libs import tokens
    return tokens.pack_token(payload)


def _clip_token(asset_id, pack_token, today):
    from libs import tokens
    return tokens.clip_token(asset_id, today, pack_token)


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

    # V3.8 : `exported_at` vit au niveau du PACK, pas dans chaque asset.
    # Il etait duplique par asset alors que `libs/tokens` le cherchait a la
    # racine : deux modules ne s'accordaient pas sur ou trouver la donnee.
    exported_at = now.strftime("%Y-%m-%dT%H:%M:%S")

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
            "exported_at": exported_at,
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
        "focus_declared": pack_meta.get("focus_declared") or None,
        "watermark": watermark,
        "assets": out_assets,
        "pack_token": pack_token,
        "exported_at": exported_at,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write(pack, cfg, root):
    """Ecrit le pack dans EXPORT/ et rend le chemin.

    EXPORT/ est le seul dossier que le consommateur (OMNIS_WATCH) lit. Le pack
    est autonome : il porte le JSON ET le fichier watermark, copies a cote sous
    <prefix><pack_token><ext>. L'EXTENSION D'ORIGINE EST CONSERVEE (V3.7) :
    forcer `.png` sur un JPEG livre produisait un fichier mal nomme, que
    certains outils refusent d'ouvrir. `pack.watermark.file` devient ce nom
    relatif, pour que le consommateur n'ait aucune resolution de chemin a faire.
    """
    rel = cfg.get("export_dir", "../EXPORT")
    base = os.path.normpath(os.path.join(root, rel))
    os.makedirs(base, exist_ok=True)
    name = "%s%s.json" % (cfg.get("export_prefix", "production_pack_mark1_"),
                          pack["pack_token"])
    path = os.path.join(base, name)

    wm = pack.get("watermark") or {}
    src_wm = wm.pop("path", None)
    if src_wm and os.path.exists(src_wm) and os.path.getsize(src_wm) > 0:
        ext = os.path.splitext(src_wm)[1].lower() or ".png"
        wm_name = "%s%s%s" % (cfg.get("export_prefix", "production_pack_mark1_"),
                               pack["pack_token"], ext)
        dst = os.path.join(base, wm_name)
        try:
            with open(src_wm, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
            wm["file"] = wm_name
            wm["bundled"] = True
            wm["bundled_ext"] = ext.lstrip(".")
        except OSError:
            wm["bundled"] = False
    else:
        wm["bundled"] = False
    pack["watermark"] = wm

    # un pack sans declaration de focus reste un pack sans focus etabli :
    # on ne l'invente pas, on le dit.

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, ensure_ascii=False, indent=2)
    return path
