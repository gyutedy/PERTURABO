"""libs/ledger.py -- la table de mesure. CSV, 26 colonnes, cle = clip_token.

REGLE : le ledger est apparie par clip_token, JAMAIS par titre, date ou ordre.
Un titre peut changer apres publication ; deux clips peuvent partager un titre ;
l ordre de publication n est pas l ordre d export.

append() est idempotent : reecrire la meme ligne ne la duplique pas.
update() ne cree jamais de colonne.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

FIELDS = (
    # identite
    "clip_token", "pack_token", "clip_id", "date", "exported_at",
    # source
    "vod_url", "start_sec", "end_sec",
    # rendu (transmis, jamais execute par MARK1)
    "asset_mode",
    # contenu
    "title",
    # campagne
    "campaign_id", "cpm_usd", "platform",
    # publication
    "clip_url", "published_at", "submitted_at",
    # mesure (remplie plus tard, par l operateur ou l outil de statistiques)
    "views_raw", "views_approved", "paid_usd",
    # effort
    "minutes_worked",
    # verdicts
    "outcome", "rejection_reason", "notes",
    # compteur
    "updated_at", "schema_version",
)

SCHEMA_VERSION = "mark1-1"

# Colonnes qu un outil externe a le droit d ecrire (CDC V2 section 17.3).
WRITABLE_EXTERNAL = ("views_approved", "minutes_worked", "paid_usd")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure(path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def read(path):
    """Rend la liste des lignes (dicts). Fichier absent = liste vide."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def append(path, row):
    """Ajoute une ligne. Rend False si le clip_token est deja present.

    Refuse une ligne sans clip_token : elle serait inappariable, donc
    inutilisable. Le CDC section 17.4 fait de ce refus une regle.
    """
    tok = str((row or {}).get("clip_token") or "").strip()
    if not tok:
        return False

    _ensure(path)
    existing = read(path)
    if any(r.get("clip_token") == tok for r in existing):
        return False

    payload = {f: "" for f in FIELDS}
    for k, v in row.items():
        if k in payload and v is not None:
            payload[k] = v
    payload["updated_at"] = now_iso()
    payload["schema_version"] = SCHEMA_VERSION

    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(payload)
    return True


def update(path, clip_token_value, **changes):
    """Complete une ligne existante. Rend False si le token est absent.

    Ignore silencieusement une cle inconnue : l outil de statistiques ne doit
    pas pouvoir fabriquer une colonne (CDC section 17.4).
    """
    tok = str(clip_token_value or "").strip()
    if not tok:
        return False
    rows = read(path)
    if not rows:
        return False

    touched = False
    for r in rows:
        if r.get("clip_token") == tok:
            for k, v in changes.items():
                if k in FIELDS and k not in ("clip_token", "pack_token"):
                    r[k] = v
                    touched = True
            r["updated_at"] = now_iso()
            break
    if not touched:
        return False

    _ensure(path)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in FIELDS})
    return True
