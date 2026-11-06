#!/usr/bin/env python3
"""
RESEARCH BUNDLE — evidence hash (S2 / v3.2)
===========================================
A /valider-1 : dossier + manifest.json SHA-256.
--verify. Gap declare, jamais comble.
Token L-XXX reference le bundle (freeze_lot).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

ARTEFACTS = (
    ("capture_parsed.json", ("F01_SENTINEL", "OUT", "capture_parsed.json")),
    ("matches.json", ("ARCHIVUM", "fixtures", "matches.json")),
    ("matches_intel.json", ("F01_SENTINEL", "OUT", "matches_intel.json")),
    ("analysis.json", ("F02_BREACHER", "OUT", "analysis.json")),
    ("predictions.json", ("F03_FORGEWARD", "OUT", "predictions.json")),
    ("top3.json", ("F03_FORGEWARD", "OUT", "top3.json")),
    ("notes_qualitatives.json", ("ARCHIVUM", "fixtures", "notes_qualitatives.json")),
    ("preview1.html", ("SHARED", "OUT", "preview1.html")),
)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def new_bundle_id(taken=None):
    taken = taken or set()
    for _ in range(200):
        t = "B-" + "".join(secrets.choice(ALPH) for _ in range(3))
        if t not in taken:
            return t
    raise RuntimeError("bundle id space exhausted")


def _taken(root):
    if not os.path.isdir(root):
        return set()
    return {name for name in os.listdir(root) if name.startswith("B-")}


def manifest_sha256(files):
    canon = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_bytes(canon.encode("utf-8"))


def build_bundle(world=None, campagne=None, capture_id=None, out_root=None):
    world = world or CODE_WORLD
    root = out_root or os.path.join(world, "ARCHIVUM", "research")
    os.makedirs(root, exist_ok=True)
    bid = new_bundle_id(_taken(root))
    dest = os.path.join(root, bid)
    os.makedirs(dest, exist_ok=True)
    files = []
    holes = []
    for name, rel in ARTEFACTS:
        src = os.path.join(world, *rel)
        if not os.path.exists(src) or not os.path.isfile(src):
            holes.append(name)
            continue
        target = os.path.join(dest, name)
        shutil.copy2(src, target)
        files.append({
            "name": name,
            "src": "/".join(rel),
            "sha256": sha256_file(target),
            "bytes": os.path.getsize(target),
        })
    man = {
        "bundle_id": bid,
        "generated_at": now_iso(),
        "campagne": campagne,
        "capture_id": capture_id,
        "files": files,
        "holes": holes,
        "note": "Gap declare, jamais comble. SHA-256 stdlib.",
    }
    man["manifest_sha256"] = manifest_sha256(files)
    man_path = os.path.join(dest, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2, ensure_ascii=False)
    man["path"] = dest
    man["manifest_path"] = man_path
    return man


def load_manifest(path):
    man_path = path
    if os.path.isdir(path):
        man_path = os.path.join(path, "manifest.json")
    with open(man_path, encoding="utf-8") as f:
        return json.load(f), os.path.dirname(os.path.abspath(man_path))


def verify_bundle(path):
    man, dest = load_manifest(path)
    errors = []
    expected = {f["name"]: f for f in man.get("files") or []}
    for name, meta in expected.items():
        fp = os.path.join(dest, name)
        if not os.path.exists(fp):
            errors.append("missing:" + name)
            continue
        got = sha256_file(fp)
        if got != meta.get("sha256"):
            errors.append("mismatch:" + name)
    for name in man.get("holes") or []:
        fp = os.path.join(dest, name)
        if os.path.exists(fp):
            errors.append("hole_filled:" + name)
    recomputed = manifest_sha256(man.get("files") or [])
    if recomputed != man.get("manifest_sha256"):
        errors.append("manifest_sha256")
    return {
        "ok": not errors,
        "bundle_id": man.get("bundle_id"),
        "errors": errors,
        "holes": list(man.get("holes") or []),
        "n_files": len(expected),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    world = CODE_WORLD
    out_root = None
    verify_path = None
    do_build = False
    campagne = None
    capture_id = None
    while argv:
        a = argv.pop(0)
        if a == "--world" and argv:
            world = argv.pop(0)
        elif a == "--out" and argv:
            out_root = argv.pop(0)
        elif a == "--verify" and argv:
            verify_path = argv.pop(0)
        elif a == "--verify":
            verify_path = argv.pop(0) if argv else None
        elif a == "--build":
            do_build = True
        elif a == "--campagne" and argv:
            campagne = argv.pop(0)
        elif a == "--capture-id" and argv:
            capture_id = argv.pop(0)
        elif a in ("-h", "--help"):
            print("research_bundle.py --build [--world PATH] [--out DIR]")
            print("research_bundle.py --verify DIR")
            return 0
    if verify_path:
        rec = verify_bundle(verify_path)
        json.dump(rec, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if rec.get("ok") else 1
    if do_build or True:
        man = build_bundle(world=world, campagne=campagne, capture_id=capture_id, out_root=out_root)
        json.dump({k: man[k] for k in man if k != "files"}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
