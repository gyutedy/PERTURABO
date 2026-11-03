#!/usr/bin/env python3
"""Inbox Telegram pour pari_listen.yml.

Ecrit capture_telegram.md (texte) ou capture_telegram.jpg|png|webp (photo).
Retire le leftover de l'autre format. Zero reseau si pas de file_id.
Hors /capture : no-op, jamais de crash.
"""
import json
import os
import urllib.request
from pathlib import Path

PHOTO_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def load_token():
    t = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if t:
        return t
    p = Path("env_pari")
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "TELEGRAM_BOT_TOKEN":
            return v.strip().strip('"').strip("'")
    return ""


def drop(path):
    if path.exists():
        path.unlink()
        print("[listen] retire leftover", path.name)


def write_photo(inbox, file_id):
    token = load_token()
    if not token:
        print("[listen] capture_file_id sans TELEGRAM_BOT_TOKEN — skip download")
        return
    api = "https://api.telegram.org"
    url = api + "/bot" + token + "/getFile?file_id=" + urllib.request.quote(file_id)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            blob = json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print("[listen] getFile echec:", type(e).__name__)
        blob = {}
    fpath = ((blob.get("result") or {}).get("file_path") or "") if blob.get("ok") else ""
    if not fpath:
        print("[listen] getFile sans file_path — trou, pas d invention")
        return
    ext = Path(fpath).suffix.lower() or ".jpg"
    if ext not in PHOTO_EXTS:
        ext = ".jpg"
    dest = inbox / ("capture_telegram" + ext)
    file_url = api + "/file/bot" + token + "/" + fpath
    try:
        with urllib.request.urlopen(file_url, timeout=60) as r:
            dest.write_bytes(r.read())
        print("[listen] photo inbox", dest.name, dest.stat().st_size, "octets")
        drop(inbox / "capture_telegram.md")
    except Exception as e:
        print("[listen] download photo echec:", type(e).__name__)


def write_markdown(inbox, text):
    dest = inbox / "capture_telegram.md"
    dest.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    print("[listen] inbox md", dest.stat().st_size, "octets")
    for ext in PHOTO_EXTS:
        drop(inbox / ("capture_telegram" + ext))


def main():
    inbox = Path("F01_SENTINEL/IN")
    inbox.mkdir(parents=True, exist_ok=True)
    file_id = (os.environ.get("CAPTURE_FILE_ID") or "").strip()
    text = os.environ.get("CAPTURE_TEXT") or ""
    cmd = os.environ.get("CMD") or ""
    if file_id:
        write_photo(inbox, file_id)
    elif text.strip():
        write_markdown(inbox, text)
    else:
        print("[listen] pas de capture (cmd=%s)" % cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
