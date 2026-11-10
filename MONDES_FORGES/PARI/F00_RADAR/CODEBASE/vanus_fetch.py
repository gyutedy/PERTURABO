#!/usr/bin/env python3
"""
VANUS FETCH — CSV Big 5 football-data.co.uk (stdlib, Zero Data).
================================================================
Telecharge E0/SP1/I1/D1/F1 vers ARCHIVUM/cache/f00/.
Timeout / HTML / vide / skip = hole. Jamais invente. Pas de gate.

Usage :
  python vanus_fetch.py --season 2526
  python vanus_fetch.py --season 2526 --dir ARCHIVUM/cache/f00
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import urllib.error
import urllib.request

BIG5 = ("E0", "SP1", "I1", "D1", "F1")
BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
UA = "PERTURABO-PARI/F00"
TIMEOUT = int(os.environ.get("PARI_F00_TIMEOUT", "8"))

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "ARCHIVUM", "cache", "f00"))


def skipped():
    return os.environ.get("PARI_SKIP_VANUS") == "1"


def cache_path(code, season, cache_dir):
    return os.path.join(cache_dir, "uk_%s_%s.csv" % (code, season))


def url_for(code, season):
    return BASE_URL.format(season=season, code=code)


def is_html(text):
    blob = (text or "").lstrip().lower()
    if not blob:
        return False
    head = blob[:400]
    return head.startswith("<!doctype") or head.startswith("<html") or "<html" in head


def n_lignes_csv(text):
    if not text or not str(text).strip() or is_html(text):
        return 0
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except (csv.Error, TypeError, ValueError):
        return 0
    return len(rows)


def _decode(raw):
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _default_get(url, timeout=None):
    timeout = TIMEOUT if timeout is None else timeout
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _decode(r.read())


def fetch_one(code, season="2526", cache_dir=None, getter=None, timeout=None):
    cache_dir = cache_dir or DEFAULT_DIR
    rec = {
        "code": code,
        "season": season,
        "ok": False,
        "path": None,
        "n_lignes": 0,
        "holes": [],
        "url": url_for(code, season),
    }
    if skipped():
        rec["holes"] = ["skip"]
        return rec
    getter = getter or _default_get
    try:
        text = getter(rec["url"], timeout=timeout)
    except TimeoutError:
        rec["holes"] = ["timeout"]
        return rec
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError):
        rec["holes"] = ["http"]
        return rec
    except Exception:
        rec["holes"] = ["http"]
        return rec
    if text is None:
        rec["holes"] = ["vide"]
        return rec
    if is_html(text):
        rec["holes"] = ["html"]
        return rec
    n = n_lignes_csv(text)
    if n <= 0:
        rec["holes"] = ["vide"]
        return rec
    os.makedirs(cache_dir, exist_ok=True)
    path = cache_path(code, season, cache_dir)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    rec["ok"] = True
    rec["path"] = path
    rec["n_lignes"] = n
    rec["holes"] = []
    return rec


def fetch(season="2526", cache_dir=None, codes=None, getter=None, timeout=None):
    cache_dir = cache_dir or DEFAULT_DIR
    codes = tuple(codes) if codes else BIG5
    if skipped():
        detail = [fetch_one(c, season=season, cache_dir=cache_dir, getter=getter, timeout=timeout)
                  for c in codes]
        return {
            "dir": os.path.abspath(cache_dir),
            "season": season,
            "files": [],
            "n_lignes": 0,
            "divisions": {},
            "hors_couverture": [c for c in BIG5],
            "holes": ["skip"],
            "detail": detail,
        }
    detail = []
    files = []
    divisions = {}
    holes = []
    n_total = 0
    for code in codes:
        rec = fetch_one(code, season=season, cache_dir=cache_dir, getter=getter, timeout=timeout)
        detail.append(rec)
        if rec.get("ok") and rec.get("n_lignes"):
            files.append(os.path.basename(rec["path"]))
            divisions[code] = rec["n_lignes"]
            n_total += rec["n_lignes"]
        else:
            holes.extend(["%s:%s" % (code, h) for h in (rec.get("holes") or ["vide"])])
    hors = [c for c in BIG5 if divisions.get(c, 0) <= 0]
    return {
        "dir": os.path.abspath(cache_dir),
        "season": season,
        "files": files,
        "n_lignes": n_total,
        "divisions": divisions,
        "hors_couverture": hors,
        "holes": holes,
        "detail": detail,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="2526")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--code", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    codes = (args.code,) if args.code else None
    blob = fetch(season=args.season, cache_dir=args.dir, codes=codes)
    rec = {k: blob[k] for k in ("dir", "season", "files", "n_lignes", "divisions", "hors_couverture", "holes")}
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    if args.out:
        parent = os.path.dirname(os.path.abspath(args.out))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
