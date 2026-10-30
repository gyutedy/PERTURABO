"""
NOTIFIER — Canal principal Telegram du monde PARI
==================================================
Telegram est PRIVÉ par nature : ton bot, ton chat, notifications push natives
sur le téléphone. Aucun serveur à payer — GitHub Action / terminal suffisent.

Variables (Settings → Keys + GitHub Secrets) :
  TELEGRAM_BOT_TOKEN  : token du bot (BotFather → /newbot)
  TELEGRAM_CHAT_ID    : ton chat_id (botFather getUpdates après 1er message)

Usage:
  python notifier.py --pack F05_PACKAGER/OUT/pari_pack.json [--radar md]
  python notifier.py --text "message direct"
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API = "https://api.telegram.org"


def _load_env_file():
    """Charge MONDES_FORGES/PARI/.env (ou env_pari) si les vars ne sont pas deja posees.
    Les variables d'environnement reelles (GitHub Secrets, workspace) priment toujours."""
    here = os.path.dirname(os.path.abspath(__file__))
    for name in (".env", "env_pari"):
        path = os.path.normpath(os.path.join(here, "..", "..", name))
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    if key and val and not os.environ.get(key):
                        os.environ[key] = val
        except OSError as e:
            print(f"[TELEGRAM] ⚠️ env illisible ({os.path.basename(path)}): {e}")


def default_chat(token: str):
    """Dernier recours : déduit le chat_id du dernier message reçu par le bot (getUpdates)."""
    try:
        with urllib.request.urlopen(f"{API}/bot{token}/getUpdates?limit=5", timeout=30) as r:
            ups = json.loads(r.read().decode())
        for u in reversed(ups.get("result", [])):
            c = (u.get("message") or {}).get("chat", {})
            if c.get("id"):
                return str(c["id"])
    except Exception:
        pass
    return None


def send(text: str) -> bool:
    _load_env_file()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        print("[TELEGRAM] ❌ TELEGRAM_BOT_TOKEN absent (@BotFather → /newbot).")
        return False
    if not chat:
        chat = default_chat(token)
        if chat:
            print(f"[TELEGRAM] ℹ️ chat_id déduit de getUpdates")
    if not chat:
        print("[TELEGRAM] ❌ chat_id introuvable :")
        print("   1. Mets TELEGRAM_CHAT_ID dans env_pari (ou .env) à la racine du monde PARI,")
        print("      ou dans les GitHub Secrets du workflow,")
        print("   2. ou envoie simplement un message à ton bot puis relance (déduit via getUpdates).")
        return False
    ok = True
    for i in range(0, len(text), 3800):
        payload = json.dumps({"chat_id": chat, "text": text[i:i + 3800]}).encode()
        req = urllib.request.Request(
            f"{API}/bot{token}/sendMessage", data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read().decode())
            if not resp.get("ok"):
                ok = False
                print(f"[TELEGRAM] ⚠️ {resp}")
        except Exception as e:
            ok = False
            print(f"[TELEGRAM] ❌ échec: {e}")
    if ok:
        print("[TELEGRAM] ✅ message envoyé")
    return ok


def pack_message(pack: dict) -> str:
    m = pack.get("metriques", {})
    lines = [
        "🛡️ *PARI — DIRECTION DES SIÈGES*",
        f"_Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
    ]
    for x in pack.get("top_picks", [])[:10]:
        lines.append(
            f"{x['rang']}. {x['match']} — {x['selection_label']} @{x['cote']} "
            f"· EV {x['ev'] * 100:+.1f}% · mise {x['mise_units']}u"
        )
    for c in pack.get("combines", []):
        lines.append(f"🧩 Combiné {len(c['jambes'])} jambes — cote {c['cote_totale']} — EV {c['ev_combine'] * 100:+.1f}% — {c['mise_units']}u")
    nb = (pack.get("no_bet") or [])
    lines += [
        "",
        f"⛔ NO BET: {len(nb)} matchs écartés — proba correcte mais cote vidée",
        f"📊 Mise totale: {m.get('mise_totale_units')}u (1u = 1% bankroll) · EV moyenne: {m.get('ev_moyenne_pct')}",
        pack.get("disclaimer", ""),
        "",
        "_L'opérateur place le pari — dernière porte._",
    ]
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="notifier — push Telegram PARI")
    parser.add_argument("--pack", default=None)
    parser.add_argument("--radar", default=None)
    parser.add_argument("--text", default=None)
    args = parser.parse_args()
    if args.text:
        sys.exit(0 if send(args.text) else 1)
    msg = []
    if args.pack and os.path.exists(args.pack):
        with open(args.pack, "r", encoding="utf-8") as f:
            msg.append(pack_message(json.load(f)))
    if args.radar and os.path.exists(args.radar):
        with open(args.radar, "r", encoding="utf-8") as f:
            msg.append(f.read()[:3800])
    if not msg:
        msg = ["PING du monde PARI 🛡️"]
    sys.exit(0 if send("\n\n".join(msg)) else 1)


if __name__ == "__main__":
    main()
