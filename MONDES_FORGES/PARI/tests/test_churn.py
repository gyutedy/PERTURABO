#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 — churn config/ >2 / 7j hors calibration. Zero reseau."""

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import churn  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_window():
    tmp = tempfile.mkdtemp(prefix="pari_churn_")
    try:
        logp = os.path.join(tmp, "config", "churn.json")
        now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        r1 = churn.record_change("a.json", world=tmp, now=now - timedelta(days=1),
                                 log_path_override=logp)
        r2 = churn.record_change("b.json", world=tmp, now=now - timedelta(hours=2),
                                 log_path_override=logp)
        check("c.deux_ok", r2.get("churn_suspect") is False and r2.get("n_7j") == 2,
              str(r2))
        r3 = churn.record_change("c.json", world=tmp, now=now, log_path_override=logp)
        check("c.trois_suspect", r3.get("churn_suspect") is True and r3.get("n_7j") == 3,
              str(r3))
        check("c.r1_pas_suspect", r1.get("churn_suspect") is False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_calibration_exclue():
    tmp = tempfile.mkdtemp(prefix="pari_churn_")
    try:
        logp = os.path.join(tmp, "config", "churn.json")
        now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        churn.record_change("a.json", world=tmp, now=now - timedelta(hours=3),
                            log_path_override=logp)
        churn.record_change("b.json", world=tmp, now=now - timedelta(hours=2),
                            log_path_override=logp)
        rec = churn.record_change("calibration.json", world=tmp, now=now,
                                  log_path_override=logp)
        check("c.calib_flag", rec.get("calibration") is True)
        check("c.calib_pas_compte", rec.get("n_7j") == 2 and rec.get("churn_suspect") is False,
              str(rec))
        rec2 = churn.record_change("league_params.json", calibration=True,
                                   world=tmp, now=now, log_path_override=logp)
        check("c.calib_kw", rec2.get("n_7j") == 2, str(rec2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_hors_fenetre():
    tmp = tempfile.mkdtemp(prefix="pari_churn_")
    try:
        logp = os.path.join(tmp, "config", "churn.json")
        now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        churn.record_change("old.json", world=tmp, now=now - timedelta(days=8),
                            log_path_override=logp)
        churn.record_change("a.json", world=tmp, now=now - timedelta(days=1),
                            log_path_override=logp)
        rec = churn.status(world=tmp, now=now, log_path_override=logp)
        check("c.old_ignore", rec.get("n_7j") == 1, str(rec))
        check("c.old_pas_suspect", rec.get("churn_suspect") is False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_is_calibration_name():
    check("c.name_calib", churn.is_calibration("ARCHIVUM/learnings/calibration.json"))
    check("c.name_lambda", churn.is_calibration("config/lambda.json") is False)


def main():
    print("=" * 70)
    print("TEST S3 — churn")
    print("=" * 70)
    test_window()
    test_calibration_exclue()
    test_hors_fenetre()
    test_is_calibration_name()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S3 churn : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
