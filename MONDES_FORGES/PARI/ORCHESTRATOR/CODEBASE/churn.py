#!/usr/bin/env python3
"""
CHURN — compteur config/ (S3 / v3.3)
====================================
>2 changements / 7j hors calibration → churn_suspect.
Zero Data : un changement hors fenetre n'est pas invente dans le compteur.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONFIG_DIR = os.path.join(WORLD, "config")
LOG_NAME = "churn.json"
WINDOW_DAYS = 7
MAX_CHANGES = 2


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt=None):
    dt = dt or now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_calibration(name):
    return "calibration" in str(name or "").lower()


def log_path(world=None):
    root = world or WORLD
    return os.path.join(root, "config", LOG_NAME)


def load_log(path=None, world=None):
    p = path or log_path(world)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "note": "CHURN config/ — >2 changements / 7j hors calibration = churn_suspect.",
        "events": [],
    }


def save_log(box, path=None, world=None):
    p = path or log_path(world)
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(box, f, indent=2, ensure_ascii=False)
    return p


def evaluate(box, now=None):
    now = now or now_utc()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=WINDOW_DAYS)
    n = 0
    for ev in box.get("events") or []:
        if ev.get("calibration"):
            continue
        at = parse_iso(ev.get("at"))
        if at is None:
            continue
        if at >= cutoff:
            n += 1
    return {
        "n_7j": n,
        "churn_suspect": n > MAX_CHANGES,
        "window_days": WINDOW_DAYS,
        "max_changes": MAX_CHANGES,
    }


def record_change(name, calibration=None, world=None, now=None, log_path_override=None):
    now = now or now_utc()
    if calibration is None:
        calibration = is_calibration(name)
    box = load_log(log_path_override, world)
    box.setdefault("events", []).append({
        "at": iso(now),
        "name": str(name or ""),
        "calibration": bool(calibration),
    })
    save_log(box, log_path_override, world)
    rec = evaluate(box, now)
    rec["name"] = str(name or "")
    rec["calibration"] = bool(calibration)
    return rec


def status(world=None, now=None, log_path_override=None):
    box = load_log(log_path_override, world)
    return evaluate(box, now)
