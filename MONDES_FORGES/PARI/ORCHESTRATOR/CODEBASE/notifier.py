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


def send(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[TELEGRAM] ❌ Clés absentes. Ajoute-les (jamais dans le code) :")
        print("   1. @BotFather → /newbot → copie le token")
        print("   2. Envoie un message à ton bot, puis ouvre "
              "https://api.telegram.org/bot<TOKEN>/getUpdates → chat.id")
        print("   3. Settings → Keys (workspace) ET GitHub Secrets → "
              "TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID")
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
