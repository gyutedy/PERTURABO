#!/usr/bin/env python3
"""
METRO — Oracle meta-review avant /valider-2 (S16)
=================================================
Risques, trous, ranking qualitatif. Jamais un chiffre.
Lit `content`. Jamais le champ reasoning. Cle absente = skip.
"""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))

DIGIT_RE = re.compile(r"[0-9０-９]")

SYSTEM = (
    "Tu es le TYRANT en revue qualitative avant tickets. "
    "Liste les risques, les trous declares, un ranking qualitatif "
    "(premier / deuxieme / troisieme, jamais un chiffre). "
    "Aucun digit, aucune cote, aucune probabilite, aucun pourcentage. "
    "N invente rien. Si un trou manque, dis-le en mots. "
    "Termine par une nuance de prudence."
)


def has_digit(text):
    return bool(DIGIT_RE.search(text or ""))


def strip_digits(text):
    t = DIGIT_RE.sub("", text or "")
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def sanitize_reply(text):
    raw = (text or "").strip()
    if not raw:
        return None, ["oracle_empty"]
    if has_digit(raw):
        return None, ["oracle_digit"]
    return raw, []


def _skip_env():
    for k in ("PARI_SKIP_ORACLE", "PARI_SKIP_F00", "PARI_SKIP_INJECT", "PARI_SKIP_BINARY"):
        if os.environ.get(k) == "1":
            return True
    return False


def _words(seq, empty="aucun"):
    out = []
    for x in seq or []:
        s = strip_digits(str(x))
        if s:
            out.append(s)
    return " ".join(out) if out else empty


def build_prompt(top3=None, notes=None, qualitative=None):
    lines = ["Revue qualitative avant tickets. Aucun chiffre."]
    for m in (top3 or {}).get("matchs") or []:
        label = strip_digits(m.get("match") or m.get("id") or "match")
        bucket = strip_digits(m.get("bucket") or "")
        holes = list(m.get("holes") or [])
        pieges = []
        for t in m.get("top3") or []:
            pieges.extend(t.get("pieges") or [])
            holes.extend(t.get("scorer_holes") or t.get("holes") or [])
        flags = m.get("state_flags") or m.get("flags") or []
        lines.append(
            "Match {0}. Bucket {1}. Trous {2}. Pieges {3}. Flags {4}.".format(
                label or "sans nom",
                bucket or "indetermine",
                _words(holes),
                _words(pieges),
                _words(flags),
            )
        )
    nbox = notes or {}
    n_items = nbox.get("items") or nbox.get("notes") or []
    themes = []
    for it in n_items:
        if isinstance(it, dict):
            themes.append(it.get("theme") or it.get("vote") or "")
        else:
            themes.append(it)
    if themes:
        lines.append("Notes themes: " + _words(themes, "silence"))
    else:
        lines.append("Notes themes: silence.")
    qv = qualitative or {}
    exclus = []
    for v in qv.get("verdicts") or qv.get("matchs") or []:
        if isinstance(v, dict):
            exclus.extend(v.get("marches_exclus") or [])
            if v.get("no_bet_recommande"):
                exclus.append("no_bet")
    if exclus:
        lines.append("Tyrant exclus: " + _words(exclus))
    body = "\n".join(lines)
    if has_digit(body):
        body = strip_digits(body)
    return body


def format_telegram(rec):
    rec = rec or {}
    if rec.get("skipped"):
        reason = rec.get("reason") or "skip"
        return "METRO Oracle: skip ({0}).".format(reason)
    holes = rec.get("holes") or []
    text = rec.get("text")
    if text:
        return "METRO Oracle:\n" + text
    if holes:
        return "METRO Oracle: trou " + ", ".join(holes) + "."
    return "METRO Oracle: silence."


def review(top3=None, notes=None, qualitative=None, timeout=8):
    prompt = build_prompt(top3, notes, qualitative)
    rec = {
        "ok": False,
        "text": None,
        "holes": [],
        "skipped": False,
        "reason": None,
    }
    if _skip_env():
        rec["skipped"] = True
        rec["reason"] = "skip_env"
        rec["ok"] = True
        rec["holes"] = ["oracle_skip"]
        return rec
    key = os.environ.get("ORACLE_API_KEY") or os.environ.get("ZRO_API_KEY")
    if not key:
        rec["skipped"] = True
        rec["reason"] = "no_key"
        rec["ok"] = True
        rec["holes"] = ["oracle_key"]
        return rec
    try:
        import urllib.request
        base = (
            os.environ.get("ORACLE_BASE_URL")
            or os.environ.get("ZRO_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = (
            os.environ.get("ORACLE_MODEL")
            or os.environ.get("ZRO_MODEL")
            or "gpt-4o-mini"
        )
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
        }).encode()
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        text, holes = sanitize_reply(content)
        rec["holes"] = holes
        rec["text"] = text
        rec["ok"] = text is not None
        if not rec["ok"] and not holes:
            rec["holes"] = ["oracle_empty"]
        return rec
    except Exception:
        rec["ok"] = True
        rec["skipped"] = True
        rec["reason"] = "oracle_indisponible"
        rec["holes"] = ["oracle_indisponible"]
        return rec
