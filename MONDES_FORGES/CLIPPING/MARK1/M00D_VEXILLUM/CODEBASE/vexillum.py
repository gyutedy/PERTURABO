"""M00D_VEXILLUM -- le vexillum (le drapeau) : le watermark PNG.

CE QUE LA DIRECTIVE EXIGE
    ARCHIVUM/campaign/watermarks/watermark_rules.json :
        opacity_min 0.75, position centered, size_pct 15
    Et la directive : watermark obligatoire sur tiktok / IG reels / YT shorts,
    optionnel sur X.

CE QUE CE MODULE FAIT
    trouve le PNG, verifie qu'il existe et pese > 0 octet, calcule l'opacite
    a appliquer (>= opacity_min), rend la liste des plateformes par obligation.

CE QU'IL NE FAIT PAS
    Il ne pose PAS le watermark : MARK1 ne touche jamais une video. Il decrit
    comment le poser, pour que celui qui monte la video (OMNIS_WATCH) le fasse.
"""

from __future__ import annotations

import json
import os


def _rules(cfg, root):
    rel = (cfg.get("directiva") or {}).get("watermark_rules",
                                           "../ARCHIVUM/campaign/watermarks/watermark_rules.json")
    path = os.path.normpath(os.path.join(root, rel))
    out = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            out = json.load(fh)
    return out


def find_png(cfg, root, creator, campaign_id):
    """Trouve le PNG du createur. Ordre : exact -> _1 -> premier png. Sinon None."""
    rel = (cfg.get("directiva") or {}).get("watermark_dir",
                                           "../ARCHIVUM/campaign/watermarks")
    base = os.path.normpath(os.path.join(root, rel))
    if not os.path.isdir(base):
        return None, []

    pngs = sorted(f for f in os.listdir(base) if f.lower().endswith(".png"))
    slugs = []
    for src in (creator, campaign_id):
        if not src:
            continue
        s = "".join(ch for ch in str(src).lower() if ch.isalnum())
        if s:
            slugs.append(s)

    for slug in slugs:
        for name in pngs:
            stem = name.lower().rsplit(".", 1)[0]
            if stem == slug or stem == slug + "_1" or stem.startswith(slug):
                return os.path.join(base, name), pngs
    return None, pngs


def build(cfg, root, directive, platform):
    """Rend le descriptif watermark pour une plateforme.

    Cles : file, opacity, position, size_pct, required, exists
    """
    wcfg = cfg.get("watermark") or {}
    rules = _rules(cfg, root)

    creator = directive.get("creator_name") or ""
    campaign_id = directive.get("campaign_id") or ""
    png, all_pngs = find_png(cfg, root, creator, campaign_id)

    opacity_min = float(rules.get("opacity_min", 0.75))
    opacity = max(float(wcfg.get("opacity", 0.80)), opacity_min)
    position = (directive.get("watermark") or {}).get("position") \
        or rules.get("position") or wcfg.get("position", "center")
    size_pct = int(rules.get("size_pct") or wcfg.get("size_pct", 15))

    obliged = wcfg.get("platforms_obliged", ["tiktok", "instagram_reels", "youtube_shorts"])
    required = platform in obliged

    exists = bool(png) and os.path.exists(png) and os.path.getsize(png) > 0

    return {
        "file": os.path.basename(png) if png else "",
        "path": png or "",
        "opacity": round(opacity, 3),
        "position": position,
        "size_pct": size_pct,
        "required": required,
        "exists": exists,
        "available_pngs": all_pngs,
    }
