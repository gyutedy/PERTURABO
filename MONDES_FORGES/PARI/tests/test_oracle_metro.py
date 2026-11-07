#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S16 — Oracle metro zero chiffre. Fees+slippage. Approve L-XXX. Zero reseau."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "TYRANT", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "LISTEN"))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))

os.environ["PARI_SKIP_ORACLE"] = "0"
os.environ.pop("ORACLE_API_KEY", None)
os.environ.pop("ZRO_API_KEY", None)

import metro  # noqa: E402
import ticket_friction as friction  # noqa: E402
import parse  # noqa: E402
import workflow  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _top3():
    return {
        "matchs": [{
            "id": "M1", "match": "Arsenal vs Chelsea", "bucket": "HAUTE",
            "top3": [{"marche": "OU", "pieges": ["cote_plate"], "holes": ["b3_info"]}],
            "holes": ["elo"], "flags": ["buteur_manquant"],
        }]
    }


def test_sanitize():
    text, holes = metro.sanitize_reply("Risque fatigue. Trou elo. Premier rang prudent.")
    check("m.sans_digit", text is not None and not metro.has_digit(text), str(text))
    check("m.holes_vides", holes == [], str(holes))
    text2, holes2 = metro.sanitize_reply("EV 3 pct cote 2.10")
    check("m.digit_refuse", text2 is None and "oracle_digit" in holes2, str(holes2))
    text3, holes3 = metro.sanitize_reply("")
    check("m.empty", text3 is None and "oracle_empty" in holes3)


def test_prompt_sans_digit():
    body = metro.build_prompt(_top3(), notes={"items": [{"theme": "fatigue"}]})
    check("m.prompt_no_digit", not metro.has_digit(body), body[:80])
    check("m.prompt_trous", "elo" in body and "cote_plate" in body)


def test_no_key_skip():
    os.environ.pop("ORACLE_API_KEY", None)
    os.environ.pop("ZRO_API_KEY", None)
    rec = metro.review(_top3())
    check("m.no_key_skip", rec.get("skipped") and rec.get("ok"), str(rec))
    check("m.no_key_hole", "oracle_key" in (rec.get("holes") or []))
    line = metro.format_telegram(rec)
    check("m.format_skip", "skip" in line.lower() and not metro.has_digit(line), line)


def test_mock_http_zero_digit():
    os.environ["ORACLE_API_KEY"] = "test-key"
    payload = {"choices": [{"message": {"content": "Risque absences. Trou declare. Premier rang prudent."}}]}
    import urllib.request as ur
    old = ur.urlopen
    ur.urlopen = lambda *a, **k: _FakeResp(payload)
    try:
        rec = metro.review(_top3(), timeout=1)
    finally:
        ur.urlopen = old
        os.environ.pop("ORACLE_API_KEY", None)
    check("m.mock_ok", rec.get("ok") and rec.get("text"), str(rec.get("holes")))
    check("m.mock_no_digit", rec.get("text") and not metro.has_digit(rec.get("text")), rec.get("text"))


def test_mock_http_digit_refuse():
    os.environ["ORACLE_API_KEY"] = "test-key"
    payload = {"choices": [{"message": {"content": "Cote 2.10 trop haute."}}]}
    import urllib.request as ur
    old = ur.urlopen
    ur.urlopen = lambda *a, **k: _FakeResp(payload)
    try:
        rec = metro.review(_top3(), timeout=1)
    finally:
        ur.urlopen = old
        os.environ.pop("ORACLE_API_KEY", None)
    check("m.mock_digit_hole", "oracle_digit" in (rec.get("holes") or []), str(rec))
    check("m.mock_digit_no_text", rec.get("text") is None)


def test_skip_env():
    os.environ["PARI_SKIP_ORACLE"] = "1"
    try:
        rec = metro.review(_top3())
    finally:
        os.environ["PARI_SKIP_ORACLE"] = "0"
    check("m.skip_env", rec.get("skipped") and rec.get("reason") == "skip_env")


def test_friction_floor():
    ev, fr = friction.effective_floor()
    check("f.fees", abs(fr["fees"] - 0.005) < 1e-12, str(fr["fees"]))
    check("f.slip", abs(fr["slippage"] - 0.005) < 1e-12, str(fr["slippage"]))
    check("f.floor_up", abs(ev - 0.04) < 1e-12, str(ev))
    check("f.jamais_sous", ev >= friction.EV_FLOOR)
    ev2, _ = friction.effective_floor(base=0.01)
    check("f.base_clip", ev2 >= friction.EV_FLOOR, str(ev2))
    tmp = tempfile.mkdtemp(prefix="pari-fr-")
    p = os.path.join(tmp, "ticket_friction.json")
    with open(p, "w") as f:
        json.dump({"fees": -1, "slippage": 0.01}, f)
    fr2 = friction.load_friction(p)
    check("f.neg_clip", fr2["fees"] == 0.0 and "fees_neg" in fr2["holes"])


def test_parse_approve():
    upd = lambda t: {"update_id": 1, "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}, "text": t}}
    r = parse.parse_update(upd("/approve L-K7M"), "1")
    check("p.approve", r.get("ok") and r.get("cmd") == "/approve L-K7M", str(r.get("cmd")))


def test_approve_mismatch():
    told = []
    old_tell = workflow.tell
    old_path = workflow.STATE_PATH
    old_dir = workflow.STATE_DIR
    tmp = tempfile.mkdtemp(prefix="pari-ap-")
    workflow.STATE_DIR = os.path.join(tmp, "STATE")
    os.makedirs(workflow.STATE_DIR, exist_ok=True)
    workflow.STATE_PATH = os.path.join(workflow.STATE_DIR, "campagne.json")
    workflow.tell = lambda t: told.append(t)
    try:
        st = {"pending_lot": {"token": "L-AAA"}, "steps": {}}
        workflow.cmd_approve(st, "L-BBB")
        check("a.mismatch", told and "mismatch" in (told[-1] or "").lower(), (told[-1] if told else "")[:80])
        told.clear()
        st2 = {"pending_lot": None, "steps": {}}
        workflow.cmd_approve(st2, "L-AAA")
        check("a.sans_pending", told and "pending" in (told[-1] or "").lower())
    finally:
        workflow.tell = old_tell
        workflow.STATE_PATH = old_path
        workflow.STATE_DIR = old_dir


def test_src_guards():
    src = open(os.path.join(WORLD, "TYRANT", "CODEBASE", "metro.py"), encoding="utf-8").read()
    check("g.content", 'msg.get("content")' in src)
    check("g.jamais_reasoning", "reasoning_content" not in src)
    wf = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()
    check("g.cmd_approve", "def cmd_approve" in wf)
    check("g.ev_floor_cmd", "--ev-floor" in wf)


def main():
    print("=" * 70)
    print("TEST S16 — oracle metro + friction + approve")
    print("=" * 70)
    test_sanitize()
    test_prompt_sans_digit()
    test_no_key_skip()
    test_mock_http_zero_digit()
    test_mock_http_digit_refuse()
    test_skip_env()
    test_friction_floor()
    test_parse_approve()
    test_approve_mismatch()
    test_src_guards()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S16 metro : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
