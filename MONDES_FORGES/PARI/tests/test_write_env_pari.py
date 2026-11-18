#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI — write_env_pari : secrets non vides seulement, jamais de valeur affichee."""

import importlib.util
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(WORLD, "..", "..", ".github", "scripts", "write_env_pari.py")
spec = importlib.util.spec_from_file_location("write_env_pari", SCRIPT)
wep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wep)

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok)))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST CI — write_env_pari")
    print("=" * 70)

    fake = {
        "TELEGRAM_BOT_TOKEN": "FAKE_TOKEN",
        "TELEGRAM_CHAT_ID": "   ",
        "ODDS_API_KEY": "FAKE_ODDS",
        "CLOUDFLARE_API_TOKEN": "FAKE_CF",
    }
    lines = wep.build_lines(fake)
    check("wep.seulement_non_vides", len(lines) == 3, str(len(lines)))
    check("wep.pas_de_vide", all("=" in line and not line.endswith("=") for line in lines))
    check("wep.noms_connus", all(line.split("=", 1)[0] in wep.KEYS for line in lines))

    target = os.path.join(tempfile.mkdtemp(prefix="pari-env-"), "env_pari")
    count = wep.write(target=target, environ=fake)
    check("wep.compte", count == 3, str(count))
    with open(target, encoding="utf-8") as handle:
        contenu = handle.read()
    check("wep.fichier_cree", os.path.isfile(target))
    check("wep.valeurs_presentes", "TELEGRAM_BOT_TOKEN=FAKE_TOKEN" in contenu
          and "ODDS_API_KEY=FAKE_ODDS" in contenu)
    check("wep.pas_de_chat_vide", "TELEGRAM_CHAT_ID=" not in contenu)

    ok = all(v for _, v in CHECKS)
    print("=" * 70)
    print(f"RESULTAT: {sum(v for _, v in CHECKS)}/{len(CHECKS)} " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
