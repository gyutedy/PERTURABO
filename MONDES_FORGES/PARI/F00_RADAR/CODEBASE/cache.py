"""
F00 — cache disque 1 hit / équipe / jour (et 1 hit / ligue / jour).
Timeout / ban / miss → voix absente, jamais de retry infini.
"""

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "ARCHIVUM", "cache", "f00"))


def utc_day(now=None):
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d")


def path_for(kind, key, day=None, cache_dir=None):
    cache_dir = cache_dir or os.environ.get("PARI_F00_CACHE") or DEFAULT_DIR
    day = day or utc_day()
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(key))[:80]
    return os.path.join(cache_dir, day, kind, safe + ".json")


def load(kind, key, day=None, cache_dir=None):
    p = path_for(kind, key, day=day, cache_dir=cache_dir)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def store(kind, key, payload, day=None, cache_dir=None):
    p = path_for(kind, key, day=day, cache_dir=cache_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    blob = {
        "cached_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": kind,
        "key": key,
        "payload": payload,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False)
    return blob


def get_or_fetch(kind, key, fetcher, day=None, cache_dir=None):
    """1 hit/jour. fetcher() → payload ou None (trou). Exception = trou, pas de retry."""
    hit = load(kind, key, day=day, cache_dir=cache_dir)
    if hit is not None:
        return hit.get("payload"), True
    try:
        payload = fetcher()
    except Exception:
        payload = None
    store(kind, key, payload, day=day, cache_dir=cache_dir)
    return payload, False
