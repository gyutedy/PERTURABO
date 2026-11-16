"""libs/tokens.py -- l identite du clip. SOURCE DE VERITE UNIQUE (V3.8).

DEUX TOKENS, DEUX ROLES
    pack_token : identite du CONTENU du pack. 8 caracteres hexadecimaux.
                 Stable : deux exports du meme contenu rendent le meme token.
                 Insensible a l ordre des cles (on serialise trie).
    clip_token : identite d UN CLIP. Contient le pack_token.
                 Formule : <asset_id>-<AAAAMMJJ>-<pack_token>
                 Exemple : A01-20261116-e99bd523

CE QUI ENTRE DANS LE pack_token, ET CE QUI N Y ENTRE PAS
    Entre : les 4 champs qui font le contenu editorial d un asset
            (id, overlay_title, metadata_title, caption).
    N entre PAS : la date, l heure, exported_at, le watermark (opacite,
            position, taille), le compte, les plateformes, la declaration de
            focus. Changer l opacite d un watermark ne cree pas un nouveau
            clip : c est le meme contenu, donc le meme token.

POURQUOI C EST CRITIQUE
    Avant la V3.8 il existait DEUX calculs differents : `packager._pack_token`
    hashait 4 champs par asset, `libs.tokens.pack_token` hashait le pack
    entier. Sur le pack e99bd523 ils rendaient 275cfb51 et non e99bd523.
    Un appel a `clip_tokens(pack)` produisait donc des tokens qui ne
    correspondaient a AUCUN clip livre : le ledger aurait cree des lignes
    orphelines et l appariement clip_token <-> lien publie aurait casse en
    silence. Un seul calcul desormais : celui d ici, appele par `packager`.

CE MODULE N ECRIT RIEN. Il calcule.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

#: Les seuls champs d un asset qui definissent son contenu. Toute autre
#: donnee (tags, hashtags, description, timescodes) est mecanicienne ou
#: derivee : la changer ne doit pas creer un nouveau clip.
CONTENT_FIELDS = ("id", "overlay_title", "metadata_title", "caption")

#: Champs du pack exclus du calcul d identite (ils sont generes ou ils
#: decrivent le contenant, pas le contenu).
_STRIP = ("pack_token", "clip_token", "clip_tokens", "exported_at",
          "generated_at", "watermark", "account", "focus_declared")


def export_date(when=None):
    """Date d export au format AAAAMMJJ, en UTC."""
    d = when or datetime.now(timezone.utc)
    return d.strftime("%Y%m%d")


def content_signature(assets):
    """La matiere premiere du pack_token : la liste des 4 champs par asset.

    Rend une liste de dicts, dans l ordre des assets. Cet ordre compte : deux
    packs dont les clips sont permutes sont deux packs differents, parce que
    le pack livre est une liste ordonnee.
    """
    return [{f: (a or {}).get(f) for f in CONTENT_FIELDS}
            for a in (assets or [])]


def pack_token(pack):
    """8 hexadecimaux derives du CONTENU du pack.

    Accepte un pack complet (`{"assets": [...]}`) ou deja une signature
    (liste de dicts), pour que l appelant n ait pas a connaitre la forme.
    """
    if isinstance(pack, dict):
        sig = content_signature(pack.get("assets"))
    elif isinstance(pack, list):
        sig = content_signature(pack)
    else:
        raise TypeError("pack_token attend un dict ou une liste d assets")

    blob = json.dumps(sig, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]


def clip_token(asset_id, date, ptoken):
    """A01 + 20261116 + e99bd523 -> A01-20261116-e99bd523."""
    aid = str(asset_id or "").strip()
    if not aid:
        raise ValueError("clip_token : asset_id vide")
    day = str(date or "").strip()
    if len(day) != 8 or not day.isdigit():
        raise ValueError("clip_token : date attendue AAAAMMJJ, recu %r" % (date,))
    tok = str(ptoken or "").strip()
    if not tok:
        raise ValueError("clip_token : pack_token vide")
    return "%s-%s-%s" % (aid, day, tok)


def clip_tokens(pack, when=None):
    """Rend {asset_id: clip_token} pour tous les assets du pack.

    Un token par asset, tous distincts. Le pack_token est calcule une fois.
    """
    day = export_date(when)
    pt = pack.get("pack_token") or pack_token(pack)
    out = {}
    for asset in (pack.get("assets") or []):
        aid = asset.get("id")
        if not aid:
            raise ValueError("asset sans id : impossible de produire un clip_token")
        out[str(aid)] = clip_token(aid, day, pt)
    if len(set(out.values())) != len(out):
        raise ValueError("deux assets ont produit le meme clip_token")
    return out
