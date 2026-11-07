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
    "marches",
    "marchés",
    "valider-1",
    "valider-2",
    "valider1",
    "valider2",
    "approve",
    "data",
    "radar",
    "pack",
    "match",
    "status",
    "roi",
    "stop",
)
LOCAL = ("help", "aide")
MAX_CAPTURE = 4096
CANON = {
    "valider1": "valider-1",
    "valider2": "valider-2",
    "marchés": "marches",
}


def _text_of(update):
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    text = msg.get("text") or msg.get("caption") or ""
    return msg, chat, text


def _photo_file_id(msg):
    """Plus grande photo, ou document image. Sinon None. Zero reseau."""
    photos = msg.get("photo") or []
    if photos:
        best = max(photos, key=lambda p: (p.get("file_size") or 0, p.get("width") or 0))
        fid = (best or {}).get("file_id")
        if fid:
            return fid
    doc = msg.get("document") or {}
    mime = (doc.get("mime_type") or "").lower()
    name = (doc.get("file_name") or "").lower()
    if doc.get("file_id") and (
        mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp"))
    ):
        return doc["file_id"]
    return None


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
    if not chat_id:
        return {"ok": False, "action": "ignore", "reason": "empty"}
    if not text.strip():
        if _photo_file_id(msg):
            return {
                "ok": False,
                "action": "reply",
                "reason": "capture_empty",
                "chat_id": chat_id,
                "reply": "Photo recu sans commande. Envoie la photo AVEC caption /capture.",
            }
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
                "/capture  (markdown DANS le meme message, OU photo + caption /capture)\n"
                "/bankroll 50000  (pot global, une fois)\n"
                "/budget 3000 800  (plafond jour + mise FORCEE ticket sur)\n"
                "/combos 3  ou  /combos 3:3:2:2\n"
                "/marches  (hint du jour apres /valider-1 ; alias /marchés, option mono)\n"
                 "/valider-1\n"
                 "/valider-2  (lot pending + token L-XXX, anti-cannibal)\n"
                 "/approve L-XXX  (fige le lot pending)\n"
                 "/data  /data N  /data ledger  /data diag\n"
                 "/radar  /pack  /match ID\n"
                 "/status  /status ledger  /status doctor\n"
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
        file_id = _photo_file_id(msg)
        if not extra.strip() and not file_id:
            return {
                "ok": False,
                "action": "reply",
                "reason": "capture_empty",
                "chat_id": chat_id,
                "reply": (
                    "Colle le tableau markdown Winner Bet DANS le meme message, "
                    "sous /capture — ou envoie une PHOTO avec caption /capture. "
                    "Plafond markdown 4096 caracteres."
                ),
            }
        if not file_id and len(extra.encode("utf-8")) > MAX_CAPTURE:
            return {
                "ok": False,
                "action": "reply",
                "reason": "capture_too_long",
                "chat_id": chat_id,
                "reply": "Capture trop longue (limite Telegram 4096). Envoie une photo avec caption /capture.",
            }
        return {
            "ok": True,
            "action": "dispatch",
            "cmd": "/capture",
            "capture_text": None if file_id else extra,
            "capture_file_id": file_id,
            "chat_id": chat_id,
            "update_id": update.get("update_id"),
            "message_id": msg.get("message_id"),
        }
    cmd = "/" + canon
    if extra.strip() and canon in (
        "budget", "combos", "bankroll", "surticket", "data", "status", "roi",
        "radar", "pack", "match", "marches", "approve",
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
