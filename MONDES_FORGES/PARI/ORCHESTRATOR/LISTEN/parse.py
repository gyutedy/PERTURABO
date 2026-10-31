#!/usr/bin/env python3
"""
LISTEN — parseur Telegram (spec Python, zero reseau)
====================================================
Miroir de la logique du Cloudflare Worker. Les tests e2e tournent ICI.
Le Worker JS reimplemente les memes regles ; si un test casse, le Worker
doit etre aligne avant deploy.

Usage:
  python parse.py --update-json update.json --chat-id 7710898895
"""

from __future__ import annotations

import json
import os
import sys

KNOWN = (
    "start",
    "capture",
    "bankroll",
    "budget",
    "surticket",
    "combos",
    "valider-1",
    "valider-2",
    "valider1",
    "valider2",
    "data",
    "status",
    "roi",
    "stop",
)
LOCAL = ("help", "aide")
MAX_CAPTURE = 4096
CANON = {
    "valider1": "valider-1",
    "valider2": "valider-2",
}


def _text_of(update):
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    text = msg.get("text") or msg.get("caption") or ""
    return msg, chat, text


def _head_cmd(text):
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None, raw
    first, _, rest = raw.partition("\n")
    token = first.split(None, 1)
    name = token[0][1:]
    if "@" in name:
        name = name.split("@", 1)[0]
    name = name.lower()
    arg0 = token[1].strip() if len(token) > 1 else ""
    body = rest.strip()
    extra = "\n".join(p for p in (arg0, body) if p)
    return name, extra


def parse_update(update, allowed_chat_id):
    """update Telegram → dict action (dispatch | local | ignore | reply)."""
    msg, chat, text = _text_of(update or {})
    chat_id = str(chat.get("id") or "")
    allowed = str(allowed_chat_id or "")
    if not chat_id or not text.strip():
        return {"ok": False, "action": "ignore", "reason": "empty"}
    if not allowed or chat_id != allowed:
        return {"ok": False, "action": "ignore", "reason": "foreign_chat"}
    name, extra = _head_cmd(text)
    if not name:
        return {
            "ok": False,
            "action": "reply",
            "reason": "not_a_command",
            "reply": "Commande inconnue. /help pour la liste.",
            "chat_id": chat_id,
        }
    if name in LOCAL:
        return {
            "ok": True,
            "action": "local",
            "cmd": "/help",
            "chat_id": chat_id,
            "reply": (
                "Campagne PARI — commandes :\n"
                "/start\n"
                "/capture  (colle le tableau markdown DANS le meme message)\n"
                "/bankroll 50000  (pot global, une fois)\n"
                "/budget 3000 800  (plafond jour + mise FORCEE ticket sur)\n"
                "/combos 3  ou  /combos 3:3:2:2\n"
                 "/valider-1\n"
                 "/valider-2  (lot + token L-XXX, anti-cannibal)\n"
                 "/data  /data N  /data ledger\n"
                 "/status  /status ledger\n"
                 "/roi  /roi settle L-XXX\n"
                 "/stop"
             ),
         }
    canon = CANON.get(name, name)
    if canon not in KNOWN:
        return {
            "ok": False,
            "action": "reply",
            "reason": "unknown",
            "chat_id": chat_id,
            "reply": "Commande inconnue : /" + name + ". /help pour la liste.",
        }
    if canon == "capture":
        if not extra.strip():
            return {
                "ok": False,
                "action": "reply",
                "reason": "capture_empty",
                "chat_id": chat_id,
                "reply": (
                    "Colle le tableau markdown Winner Bet DANS le meme message, "
                    "sous /capture. png/pdf plus tard. Plafond 4096 caracteres."
                ),
            }
        if len(extra.encode("utf-8")) > MAX_CAPTURE:
            return {
                "ok": False,
                "action": "reply",
                "reason": "capture_too_long",
                "chat_id": chat_id,
                "reply": "Capture trop longue (limite Telegram 4096). Decoupe, png plus tard.",
            }
        return {
            "ok": True,
            "action": "dispatch",
            "cmd": "/capture",
            "capture_text": extra,
            "chat_id": chat_id,
            "update_id": update.get("update_id"),
            "message_id": msg.get("message_id"),
        }
    cmd = "/" + canon
    if extra.strip() and canon in (
        "budget", "combos", "bankroll", "surticket", "data", "status", "roi",
    ):
        cmd = cmd + " " + extra.split("\n", 1)[0].strip()
    return {
        "ok": True,
        "action": "dispatch",
        "cmd": cmd,
        "capture_text": None,
        "chat_id": chat_id,
        "update_id": update.get("update_id"),
        "message_id": msg.get("message_id"),
    }


def main(argv):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    path = None
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--chat-id" and args:
            chat_id = args.pop(0)
        elif a == "--update-json" and args:
            path = args.pop(0)
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
    if not path:
        print("usage: parse.py --update-json FILE|-- --chat-id ID", file=sys.stderr)
        return 2
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    update = json.loads(raw)
    out = parse_update(update, chat_id)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
