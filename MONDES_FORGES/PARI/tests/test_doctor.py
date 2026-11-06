#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 — doctor offline GO/CHECK/FAIL. Noms de cles seulement. Zero reseau."""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import doctor  # noqa: E402

CHECKS = []
KEY_WATCH = doctor.KEY_WATCH


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _wipe_keys():
    saved = {}
    for k in KEY_WATCH:
        if k in os.environ:
            saved[k] = os.environ.pop(k)
    return saved


def _restore_keys(saved):
    for k, v in saved.items():
        os.environ[k] = v


def _tmp_world():
    root = tempfile.mkdtemp(prefix="pari_doc_")
    for rel in (
        ("CONTRACTS",),
        ("F01_SENTINEL", "OUT"),
        ("F02_BREACHER", "OUT"),
        ("F03_FORGEWARD", "OUT"),
        ("F05_PACKAGER", "OUT"),
        ("ARCHIVUM", "learnings"),
        ("ARCHIVUM", "teams"),
        ("ARCHIVUM", "odds"),
        ("ARCHIVUM", "cache", "f00"),
        ("F01_SENTINEL", "CODEBASE", "connectors"),
        ("F00_RADAR", "CODEBASE"),
    ):
        os.makedirs(os.path.join(root, *rel), exist_ok=True)
    return root


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f)


def _copy_schemas(tmp):
    src = os.path.join(WORLD, "CONTRACTS")
    dst = os.path.join(tmp, "CONTRACTS")
    os.makedirs(dst, exist_ok=True)
    for name in (
        "schema_match_intel.json",
        "schema_analysis.json",
        "schema_predictions.json",
        "schema_pari_pack.json",
    ):
        shutil.copy2(os.path.join(src, name), os.path.join(dst, name))


def test_cli_json():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        rec = doctor.diagnose(world=tmp, code_world=WORLD)
        check("cli.verdict", rec.get("verdict") in ("GO", "CHECK", "FAIL"), rec.get("verdict"))
        check("cli.mode", rec.get("mode") == "offline")
        blob = json.dumps(rec)
        check("cli.pas_valeur_cle", "ghp_" not in blob and "sk-" not in blob)
        txt = doctor.format_telegram(rec)
        check("cli.telegram", "DOCTOR" in txt and rec["verdict"] in txt, txt[:80])
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_cles_noms():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        _write(os.path.join(tmp, "env_pari"), "API_FOOTBALL_KEY=super-secret-value-NE-PAS-LOGGER\n")
        rec = doctor.check_cles(tmp)
        check("cles.present", "API_FOOTBALL_KEY" in rec.get("present"), str(rec.get("present")))
        dumped = json.dumps(rec)
        check("cles.pas_secret", "super-secret-value-NE-PAS-LOGGER" not in dumped, dumped)
        check("cles.absent_noms", "ORACLE_API_KEY" in rec.get("absent"))
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_contrats_fail():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        _write(os.path.join(tmp, "F01_SENTINEL", "OUT", "matches_intel.json"), {"ligue": "E0"})
        rec = doctor.check_contrats(tmp, WORLD)
        check("ct.fail_ok_false", rec.get("ok") is False)
        miss = rec.get("missing_fields") or []
        check("ct.missing", any("generated_at" in m or "matchs" in m for m in miss), str(miss[:4]))
        full = doctor.diagnose(world=tmp, code_world=WORLD)
        check("ct.verdict_fail", full.get("verdict") == "FAIL", full.get("verdict"))
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_whitelist_e1_d2():
    rec = doctor.check_whitelist(WORLD)
    check("wl.ok", rec.get("ok") is True)
    ligues = rec.get("ligues") or []
    check("wl.e1", "E1" in ligues, str(ligues))
    check("wl.d2", "D2" in ligues, str(ligues))
    holes = rec.get("holes") or []
    check("wl.espn_e1_trou", "espn:E1" in holes, str(holes))
    check("wl.espn_d2_trou", "espn:D2" in holes, str(holes))
    check("wl.pas_invente", rec.get("note") != "")


def test_gate_bruit():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        _write(os.path.join(tmp, "ARCHIVUM", "learnings", "lots.json"), {"lots": []})
        rec = doctor.diagnose(world=tmp, code_world=WORLD)
        gate = rec.get("gate") or {}
        check("gate.bruit", gate.get("niveau") == "bruit", str(gate))
        check("gate.n", gate.get("n_tickets") == 0, str(gate.get("n_tickets")))
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_gate_niveaux():
    check("gate.300", doctor.gate_for(300)["niveau"] == "observation")
    check("gate.499", doctor.gate_for(499)["niveau"] == "observation")
    check("gate.500", doctor.gate_for(500)["niveau"] == "moteur")
    check("gate.299", doctor.gate_for(299)["niveau"] == "bruit")


def test_clv_alerte():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        now = datetime(2026, 11, 6, tzinfo=timezone.utc)
        lots = {
            "lots": [
                {
                    "token": "L-AAA",
                    "created_at": "2026-11-01T00:00:00Z",
                    "clv": -4.2,
                },
                {
                    "token": "L-BBB",
                    "created_at": "2026-11-02T00:00:00Z",
                    "clv": -5.0,
                },
            ]
        }
        _write(os.path.join(tmp, "ARCHIVUM", "learnings", "lots.json"), lots)
        rec = doctor.check_clv(tmp, now=now)
        check("clv.alerte", rec.get("alerte") is True, str(rec))
        check("clv.median", rec.get("median_30j") is not None and rec["median_30j"] < -3)
        full = doctor.diagnose(world=tmp, code_world=WORLD, now=now)
        check("clv.fail", full.get("verdict") == "FAIL", full.get("verdict"))
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_clv_trou():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        _write(os.path.join(tmp, "ARCHIVUM", "learnings", "lots.json"), {"lots": []})
        rec = doctor.check_clv(tmp)
        check("clv.trou", "clv" in (rec.get("holes") or []), str(rec))
        check("clv.pas_zero", rec.get("median_30j") is None)
        check("clv.pas_alerte_sans_data", rec.get("alerte") is False)
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def test_cache_holes():
    saved = _wipe_keys()
    try:
        tmp = _tmp_world()
        rec = doctor.check_cache(tmp)
        check("cache.ok_trou", rec.get("ok") is True)
        holes = rec.get("holes") or []
        check("cache.elo_trou", "elo" in holes, str(holes))
        check("cache.pas_invente", rec.get("age_hours", {}).get("elo") is None)
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        _restore_keys(saved)


def main():
    print("=" * 70)
    print("TEST S2 — doctor")
    print("=" * 70)
    test_cli_json()
    test_cles_noms()
    test_contrats_fail()
    test_whitelist_e1_d2()
    test_gate_bruit()
    test_gate_niveaux()
    test_clv_alerte()
    test_clv_trou()
    test_cache_holes()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S2 doctor : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
