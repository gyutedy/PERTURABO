#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 — research bundle SHA-256. Gap declare, jamais comble. Zero reseau."""

import json
import os
import shutil
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))

import research_bundle as rb  # noqa: E402
import ledger  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _tmp_world():
    root = tempfile.mkdtemp(prefix="pari_rb_")
    for rel in (
        ("F01_SENTINEL", "OUT"),
        ("F02_BREACHER", "OUT"),
        ("F03_FORGEWARD", "OUT"),
        ("ARCHIVUM", "fixtures"),
        ("SHARED", "OUT"),
        ("ARCHIVUM", "research"),
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


def _seed(tmp, missing=()):
    files = {
        ("F01_SENTINEL", "OUT", "capture_parsed.json"): {"n_matchs": 2},
        ("ARCHIVUM", "fixtures", "matches.json"): {"matchs": [{"id": "M1"}]},
        ("F01_SENTINEL", "OUT", "matches_intel.json"): {"generated_at": "Z", "source": "t",
                                                       "ligue": "E0", "matchs": []},
        ("F02_BREACHER", "OUT", "analysis.json"): {"generated_at": "Z", "ligue": "E0",
                                                  "analyses": []},
        ("F03_FORGEWARD", "OUT", "predictions.json"): {"generated_at": "Z", "predictions": []},
        ("F03_FORGEWARD", "OUT", "top3.json"): {"generated_at": "Z", "matchs": []},
        ("ARCHIVUM", "fixtures", "notes_qualitatives.json"): {"notes_count": 0},
        ("SHARED", "OUT", "preview1.html"): "<html>PERTURABO</html>",
    }
    skip = set(missing)
    for rel, obj in files.items():
        if rel[-1] in skip:
            continue
        _write(os.path.join(tmp, *rel), obj)


def test_build_and_verify():
    tmp = _tmp_world()
    try:
        _seed(tmp)
        man = rb.build_bundle(world=tmp, campagne="PARI-TEST", capture_id="C-AAA",
                              out_root=os.path.join(tmp, "ARCHIVUM", "research"))
        check("rb.id", str(man.get("bundle_id") or "").startswith("B-"), str(man.get("bundle_id")))
        check("rb.sha", len(man.get("manifest_sha256") or "") == 64)
        check("rb.holes_empty", man.get("holes") == [], str(man.get("holes")))
        check("rb.n8", len(man.get("files") or []) == 8, str(len(man.get("files") or [])))
        ver = rb.verify_bundle(man["path"])
        check("rb.verify_ok", ver.get("ok") is True, str(ver))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_gap_declare():
    tmp = _tmp_world()
    try:
        _seed(tmp, missing=("preview1.html", "top3.json"))
        man = rb.build_bundle(world=tmp, out_root=os.path.join(tmp, "ARCHIVUM", "research"))
        holes = man.get("holes") or []
        check("gap.preview", "preview1.html" in holes, str(holes))
        check("gap.top3", "top3.json" in holes, str(holes))
        names = [f["name"] for f in man.get("files") or []]
        check("gap.pas_comble", "preview1.html" not in names and "top3.json" not in names, str(names))
        ver = rb.verify_bundle(man["path"])
        check("gap.verify_ok", ver.get("ok") is True, str(ver))
        check("gap.verify_holes", "preview1.html" in (ver.get("holes") or []))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_tamper():
    tmp = _tmp_world()
    try:
        _seed(tmp)
        man = rb.build_bundle(world=tmp, out_root=os.path.join(tmp, "ARCHIVUM", "research"))
        target = os.path.join(man["path"], "top3.json")
        with open(target, "w", encoding="utf-8") as f:
            f.write('{"tampered": true}')
        ver = rb.verify_bundle(man["path"])
        check("tamper.fail", ver.get("ok") is False, str(ver))
        check("tamper.mismatch", any("mismatch:top3.json" == e for e in ver.get("errors") or []),
              str(ver.get("errors")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cli_verify():
    tmp = _tmp_world()
    try:
        _seed(tmp)
        man = rb.build_bundle(world=tmp, out_root=os.path.join(tmp, "ARCHIVUM", "research"))
        rc = rb.main(["--verify", man["path"]])
        check("cli.verify_rc", rc == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_freeze_lot_bundle():
    tmp = tempfile.mkdtemp(prefix="pari_lot_")
    try:
        tix = {
            "generated_at": "2026-11-06T00:00:00Z",
            "tickets": [{"rang_ticket": 1, "jambes": [
                {"match_id": "M1", "marche": "1X2", "selection": "1"}]}],
            "budget": {"budget_fc": 300, "alloue_fc": 300, "reste_fc": 0},
        }
        lot = ledger.freeze_lot(
            "L-TST", "PARI-TEST", "C-ZZZ", tix,
            ledger.legs_from_tickets(tix["tickets"]), 300, 100,
            bundle_id="B-XYZ")
        check("lot.bundle", lot.get("bundle_id") == "B-XYZ", str(lot.get("bundle_id")))
        lot2 = ledger.freeze_lot(
            "L-TS2", "PARI-TEST", "C-ZZZ", tix,
            ledger.legs_from_tickets(tix["tickets"]), 300, 100)
        check("lot.sans_bundle", "bundle_id" not in lot2, str(lot2.keys()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=" * 70)
    print("TEST S2 — research bundle")
    print("=" * 70)
    test_build_and_verify()
    test_gap_declare()
    test_tamper()
    test_cli_verify()
    test_freeze_lot_bundle()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S2 bundle : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
