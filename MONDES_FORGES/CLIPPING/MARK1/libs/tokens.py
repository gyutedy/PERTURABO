"""libs/tokens.py -- l identite du clip (NOUVEAU en V2).

DEUX TOKENS, DEUX ROLES
    pack_token : identite du CONTENU du pack. 8 caracteres hexadecimaux.
                 Stable : deux exports du meme pack rendent le meme token.
                 Insensible a l ordre des cles (on serialise trie).
    clip_token : identite d UN CLIP. Contient le pack_token.
                 Formule : <asset_id>-<AAAAMMJJ>-<pack_token>
                 Exemple : A01-20261115-3f9a1c07

POURQUOI PAR CLIP ET PAS PAR PACK
    Un pack sert plusieurs clips. La V1 identifiait le pack, donc le ledger ne
    pouvait pas apparier une ligne a un lien publie. Le clip_token contient le
    pack_token : on remonte du clip au pack sans table de correspondance.

CE MODULE N ECRIT RIEN. Il calcule.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def export_date(when=None):
    """Date d export au format AAAAMMJJ, en UTC."""
    d = when or datetime.now(timezone.utc)
    return d.strftime("%Y%m%d")


def pack_token(pack):
    """8 caracteres hexadecimaux, derives du contenu du pack.

    Les cles deja generees (pack_token, clip_token, exported_at) sont exclues :
    sinon un second export du meme pack produirait un token different, et le
    ledger creerait des doublons fantomes.
    """
    if not isinstance(pack, dict):
        raise TypeError("pack_token attend un dict")
    clean = _strip_generated(pack)
    blob = json.dumps(clean, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]


def _strip_generated(obj):
    if isinstance(obj, dict):
        return {
            k: _strip_generated(v)
            for k, v in obj.items()
            if k not in ("pack_token", "clip_token", "exported_at")
        }
    if isinstance(obj, list):
        return [_strip_generated(v) for v in obj]
    return obj


def clip_token(asset_id, date, ptoken):
    """A01 + 20261115 + 3f9a1c07 -> A01-20261115-3f9a1c07."""
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
