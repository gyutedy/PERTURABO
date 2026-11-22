#!/usr/bin/env python3
"""
WRITE ENV PARI — reconstruit MONDES_FORGES/PARI/env_pari depuis les Secrets GitHub.
=================================================================================
Appele par les workflows Actions avec un bloc `env:` mappant chaque secret.
Seules les variables NON VIDES sont ecrites. Aucune valeur n'est affichee ni
journalisee. Le fichier reste gitignore : il n'existe plus dans le depot.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
TARGET = os.path.join(REPO, "MONDES_FORGES", "PARI", "env_pari")

KEYS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "API_FOOTBALL_KEY",
    "FOOTBALL_DATA_ORG_KEY",
    "SPORTRADAR_API_KEY",
    "WHOSCORED_KEY",
    "RAPIDAPI_WHOSCORED_KEY",
    "WHOSCORED_HOST",
    "SOFASCORE_RAPIDAPI_KEY",
    "SOFASCORE_HOST",
    "ORACLE_API_KEY",
    "ORACLE_BASE_URL",
    "ORACLE_MODEL",
    "ZRO_API_KEY",
    "ZRO_BASE_URL",
    "ZRO_MODEL",
    "ODDS_API_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
)


def build_lines(environ=None):
    env = environ if environ is not None else os.environ
    return ["%s=%s" % (k, str(env.get(k) or "").strip())
            for k in KEYS if str(env.get(k) or "").strip()]


def write(target=None, environ=None):
    path = target or TARGET
    lines = build_lines(environ)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def main():
    count = write()
    print("[env_pari] %d/%d secrets ecrits (valeurs non affichees)" % (count, len(KEYS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
