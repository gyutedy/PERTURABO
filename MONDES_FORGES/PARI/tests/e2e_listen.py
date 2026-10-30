#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E LISTEN — parseur Telegram + inbox capture (zero reseau)
===========================================================
Couvre le contrat schema_listen.json, le parseur ORCHESTRATOR/LISTEN/parse.py
et le fallback /capture de workflow.py vers F01_SENTINEL/IN/capture_telegram.md.

Aucun appel Telegram, aucun dispatch GitHub, aucun webhook.
"""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LISTEN = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN")
sys.path.insert(0, LISTEN)
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import parse  # noqa: E402
import workflow  # noqa: E402

CHECKS = []
CHAT = "7710898895"


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def upd(text, chat_id=CHAT, update_id=1, message_id=10):
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "chat": {"id": int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id, "type": "private"},
            "text": text,
        },
    }


def main():
    print("=" * 70)
    print("E2E LISTEN — parseur + inbox (zero reseau)")
    print("=" * 70)

    schema_path = os.path.join(WORLD, "CONTRACTS", "schema_listen.json")
    schema = json.load(open(schema_path, encoding="utf-8"))
    check("L0.schema_exists", "cmd" in schema.get("properties", {}) and "chat_id" in schema.get("required", []))

    r = parse.parse_update(upd("/start"), CHAT)
    check("L1.start_dispatch", r.get("ok") and r.get("action") == "dispatch" and r.get("cmd") == "/start", str(r.get("cmd")))

    r = parse.parse_update(upd("/start@Handleer_one_bot"), CHAT)
    check("L1.start_mention", r.get("ok") and r.get("cmd") == "/start", str(r.get("cmd")))

    r = parse.parse_update(upd("/start"), "999")
    check("L2.foreign_ignored", (not r.get("ok")) and r.get("action") == "ignore" and r.get("reason") == "foreign_chat")

    r = parse.parse_update(upd(""), CHAT)
    check("L2.empty_ignored", (not r.get("ok")) and r.get("action") == "ignore")

    r = parse.parse_update(upd("/capture"), CHAT)
    check("L3.capture_empty_refused", (not r.get("ok")) and r.get("reason") == "capture_empty", r.get("reason"))

    md = (
        "| Competition | Horaire | 1 | X | 2 |\n"
        "| :--- | :--- | :---: | :---: | :---: |\n"
        "| **Premier League**<br>Arsenal vs Chelsea | Aujourd'hui 18:00 | 1.85 | 3.60 | 4.20 |"
    )
    r = parse.parse_update(upd("/capture\n" + md), CHAT)
    check(
        "L3.capture_markdown",
        r.get("ok") and r.get("action") == "dispatch" and r.get("cmd") == "/capture" and "Arsenal vs Chelsea" in (r.get("capture_text") or ""),
        (r.get("cmd") or "") + " n=" + str(len(r.get("capture_text") or "")),
    )

    r = parse.parse_update(upd("/capture " + md.split("\n")[0]), CHAT)
    check("L3.capture_same_line", r.get("ok") and r.get("cmd") == "/capture" and "Competition" in (r.get("capture_text") or ""))

    too = "X" * 5000
    r = parse.parse_update(upd("/capture\n" + too), CHAT)
    check("L3.capture_too_long", (not r.get("ok")) and r.get("reason") == "capture_too_long")

    r = parse.parse_update(upd("/budget 6000"), CHAT)
    check("L4.budget", r.get("ok") and r.get("cmd") == "/budget 6000", str(r.get("cmd")))

    r = parse.parse_update(upd("/combos 3:3:2:2"), CHAT)
    check("L4.combos", r.get("ok") and r.get("cmd") == "/combos 3:3:2:2", str(r.get("cmd")))

    r = parse.parse_update(upd("/valider-1"), CHAT)
    check("L4.valider1", r.get("ok") and r.get("cmd") == "/valider-1")

    r = parse.parse_update(upd("/valider1"), CHAT)
    check("L4.valider1_alias", r.get("ok") and r.get("cmd") == "/valider-1", str(r.get("cmd")))

    r = parse.parse_update(upd("/help"), CHAT)
    check("L5.help_local", r.get("ok") and r.get("action") == "local" and "/start" in (r.get("reply") or ""))

    r = parse.parse_update(upd("/radar"), CHAT)
    check("L5.unknown_reply", (not r.get("ok")) and r.get("action") == "reply" and r.get("reason") == "unknown")

    r = parse.parse_update(upd("bonjour"), CHAT)
    check("L5.not_a_command", (not r.get("ok")) and r.get("action") == "reply")

    payload = parse.parse_update(upd("/capture\n" + md), CHAT)
    needed = {"cmd", "chat_id"}
    check("L6.contrat_champs", needed.issubset(payload.keys()) and payload.get("capture_text"))

    inbox_dir = tempfile.mkdtemp(prefix="pari-listen-")
    inbox = os.path.join(inbox_dir, "capture_telegram.md")
    with open(inbox, "w", encoding="utf-8") as f:
        f.write(md)
    old_inbox = workflow.INBOX_CAPTURE
    workflow.INBOX_CAPTURE = inbox
    try:
        got = workflow.resolve_capture("")
        check("L7.inbox_fallback", got == inbox, str(got))
        explicit = os.path.join(inbox_dir, "autre.md")
        with open(explicit, "w", encoding="utf-8") as f:
            f.write("x")
        got2 = workflow.resolve_capture(explicit)
        check("L7.explicit_path_gagne", got2 == explicit, str(got2))
        workflow.INBOX_CAPTURE = os.path.join(inbox_dir, "absent.md")
        got3 = workflow.resolve_capture("")
        check("L7.sans_inbox_none", got3 is None, str(got3))
    finally:
        workflow.INBOX_CAPTURE = old_inbox

    yml = os.path.join(WORLD, "..", "..", ".github", "workflows", "pari_listen.yml")
    yml = os.path.normpath(yml)
    raw = open(yml, encoding="utf-8").read() if os.path.exists(yml) else ""
    check("L8.workflow_exists", "name: pari-listen" in raw and "workflow.py" in raw)
    check("L8.concurrency", "group: pari-campagne" in raw and "cancel-in-progress: false" in raw)
    check("L8.inbox_write", "capture_telegram.md" in raw)
    check("L8.pages_non_bloquant", "continue-on-error: true" in raw)

    wf_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()
    check(
        "L10.capture_passe_path",
        'run_orch("--mode", "input-capture", "--capture", path)' in wf_src
        and 'run_orch("--mode", "input-capture", "--capture", fichier)' not in wf_src,
    )

    import notifier  # noqa: E402
    old_tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    old_chat = os.environ.get("TELEGRAM_CHAT_ID")
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    try:
        notifier._load_env_file()
        check("L9.env_pari_si_secret_vide", bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("TELEGRAM_CHAT_ID")))
    finally:
        if old_tok is None:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        else:
            os.environ["TELEGRAM_BOT_TOKEN"] = old_tok
        if old_chat is None:
            os.environ.pop("TELEGRAM_CHAT_ID", None)
        else:
            os.environ["TELEGRAM_CHAT_ID"] = old_chat

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"LISTEN {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
