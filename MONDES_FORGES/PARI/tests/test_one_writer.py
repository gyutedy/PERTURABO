#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 — one-writer. sendMessage hors notifier.py = fail.

Worker ACK (LISTEN/src/index.js) et inbox_capture.py getFile autorises.
Zero reseau.
"""

import os

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ALLOWED = os.path.normpath(os.path.join("ORCHESTRATOR", "CODEBASE", "notifier.py"))

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _py_files():
    out = []
    for root, dirs, files in os.walk(WORLD):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for name in files:
            if name.endswith(".py"):
                out.append(os.path.join(root, name))
    return out


def test_sendmessage_only_notifier():
    offenders = []
    notifier_hit = False
    for path in _py_files():
        rel = os.path.relpath(path, WORLD)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        if "sendMessage" not in text:
            continue
        nrel = os.path.normpath(rel).replace("\\", "/")
        if nrel == ALLOWED.replace("\\", "/"):
            notifier_hit = True
            continue
        if nrel.startswith("tests/"):
            continue
        offenders.append(nrel)
    check("ow.notifier_sendMessage", notifier_hit, ALLOWED)
    check("ow.pas_ailleurs", offenders == [], ",".join(offenders))


def test_inbox_getfile_not_send():
    path = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "inbox_capture.py")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    check("ow.inbox_getFile", "getFile" in text)
    check("ow.inbox_pas_sendMessage", "sendMessage" not in text)


def test_worker_ack_allowed():
    path = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "src", "index.js")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    check("ow.worker_ack_sendMessage", "sendMessage" in text and "tgSend" in text)


def main():
    print("=" * 70)
    print("TEST S3 — one-writer")
    print("=" * 70)
    test_sendmessage_only_notifier()
    test_inbox_getfile_not_send()
    test_worker_ack_allowed()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S3 one-writer : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
