"""M00D_VEXILLUM -- le vexillum (le drapeau) : le watermark de la campagne.

CE QUE LA DIRECTIVE EXIGE
    ARCHIVUM/campaign/watermarks/watermark_rules.json :
        opacity_min 0.75, position centered, size_pct 15
    Et la directive : watermark obligatoire sur tiktok / IG reels / YT shorts,
    optionnel sur X.

CE QUE CE MODULE FAIT
    trouve le watermark, verifie qu'il existe et pese > 0 octet, calcule
    l'opacite a appliquer (>= opacity_min), rend la liste des plateformes par
    obligation.

PNG OU JPEG (V3.7)
    Le fournisseur livre ce qu'il veut : Clipify donne parfois un PNG
    transparent, parfois un JPEG deja aplati avec son fond. Les deux sont
    acceptes (.png, .jpeg, .jpg). Ce module ne cherchait que des `.png` : un
    JPEG valide pose dans watermarks/ etait invisible, et la porte M3 refusait
    d'exporter en disant "PNG absent" alors qu'il etait la.
    MARK1 ne convertit RIEN : le format livre voyage tel quel dans le pack, et
    c'est OMNIS_WATCH qui decide comment le compositer.

CE QU'IL NE FAIT PAS
    Il ne pose PAS le watermark : MARK1 ne touche jamais une video. Il decrit
    comment le poser, pour que celui qui monte la video (OMNIS_WATCH) le fasse.
"""

from __future__ import annotations

import json
import os

#: Formats acceptes pour le fichier watermark. L'ordre fait la priorite :
#: un PNG (fond transparent) est prefere a un JPEG (fond aplati) si les deux
#: existent pour le meme createur.
WATERMARK_EXTS = (".png", ".jpeg", ".jpg")


def _rules(cfg, root):
    rel = (cfg.get("directiva") or {}).get("watermark_rules",
                                           "../ARCHIVUM/campaign/watermarks/watermark_rules.json")
    path = os.path.normpath(os.path.join(root, rel))
    out = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            out = json.load(fh)
    return out


def find_watermark(cfg, root, creator, campaign_id):
    """Trouve le watermark du createur (png/jpeg/jpg). Sinon (None, []).

    Ordre : correspondance exacte du slug -> slug_1 -> slug*, et a
    correspondance egale, l'ordre de WATERMARK_EXTS (png avant jpeg).
    Rend (chemin_absolu_ou_None, [tous les fichiers watermark disponibles]).
    """
    rel = (cfg.get("directiva") or {}).get("watermark_dir",
                                           "../ARCHIVUM/campaign/watermarks")
    base = os.path.normpath(os.path.join(root, rel))
    if not os.path.isdir(base):
        return None, []

    def _ext_rank(name):
        ext = os.path.splitext(name)[1].lower()
        return WATERMARK_EXTS.index(ext) if ext in WATERMARK_EXTS else len(WATERMARK_EXTS)

    assets = sorted(
        (f for f in os.listdir(base)
         if f.lower().endswith(WATERMARK_EXTS) and not f.startswith(".")),
        key=lambda n: (_ext_rank(n), n.lower()))
    if not assets:
        return None, []

    slugs = []
    for src in (creator, campaign_id):
        if not src:
            continue
        s = "".join(ch for ch in str(src).lower() if ch.isalnum())
        if s:
            slugs.append(s)

    for slug in slugs:
        # 1. exact, 2. slug_1, 3. slug*
        for wanted in (slug, slug + "_1"):
            for name in assets:
                if name.lower().rsplit(".", 1)[0] == wanted:
                    return os.path.join(base, name), assets
        for name in assets:
            if name.lower().rsplit(".", 1)[0].startswith(slug):
                return os.path.join(base, name), assets

    return None, assets


def build(cfg, root, directive, platform):
    """Rend le descriptif watermark pour une plateforme.

    Cles : file, path, format, ext, opacity, position, size_pct, required,
    exists, available_watermarks
    """
    wcfg = cfg.get("watermark") or {}
    rules = _rules(cfg, root)

    creator = directive.get("creator_name") or ""
    campaign_id = directive.get("campaign_id") or ""
    asset, all_assets = find_watermark(cfg, root, creator, campaign_id)

    opacity_min = float(rules.get("opacity_min", 0.75))
    opacity = max(float(wcfg.get("opacity", 0.80)), opacity_min)
    position = (directive.get("watermark") or {}).get("position") \
        or rules.get("position") or wcfg.get("position", "center")
    size_pct = int(rules.get("size_pct") or wcfg.get("size_pct", 15))

    obliged = wcfg.get("platforms_obliged", ["tiktok", "instagram_reels", "youtube_shorts"])
    required = platform in obliged

    exists = bool(asset) and os.path.exists(asset) and os.path.getsize(asset) > 0
    ext = os.path.splitext(asset)[1].lower() if asset else ""

    return {
        "file": os.path.basename(asset) if asset else "",
        "path": asset or "",
        "format": ext.lstrip(".") or "",
        "ext": ext,
        "opacity": round(opacity, 3),
        "position": position,
        "size_pct": size_pct,
        "required": required,
        "exists": exists,
        "available_watermarks": all_assets,
    }
