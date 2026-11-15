#!/usr/bin/env python3
"""mark1.py -- point d entree unique de MARK1. 7 commandes.

MARK1 ne produit JAMAIS de video. Il produit un pack JSON livrable dans EXPORT/
que le consommateur externe (OMNIS_WATCH) transforme en clip.

Aucune dependance, aucun appel reseau, aucun ffmpeg.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from libs import env, gates                                        # noqa: E402
from libs.campaign import evaluate                                 # noqa: E402
from libs.economy import views_needed, revenue, usd_per_hour        # noqa: E402
from libs.ledger import append, read, update, now_iso              # noqa: E402
from libs.s1_context import analyse                                # noqa: E402
from libs.title_forge import generate as gen_titles                # noqa: E402
from libs.tokens import pack_token, clip_tokens                    # noqa: E402


def _cfg():
    return json.loads((ROOT / "config" / "selection.json").read_text(encoding="utf-8"))


def _asset_mode(pack):
    """Lit asset_mode sous ses trois formes possibles, rend la valeur."""
    r = pack.get("asset_mode") or pack.get("render")
    if isinstance(r, dict):
        return r.get("style") or r.get("mode")
    return r


def cmd_doctor(_a):
    cfg = _cfg()
    print("== MARK1 doctor ==")
    print("[OK] dependances : aucune (stdlib seule, aucun ffmpeg)")
    for name, state, usage in env.doctor():
        print("[%7s] %-24s %s" % (state, name, usage))

    exp = (ROOT / cfg["export_dir"]).resolve()
    print("[%s] %-24s %s" % ("OK" if exp.parent.is_dir() else "FAIL", "export_dir", exp))

    modes = cfg.get("allowed_asset_modes", [])
    print("[%s] %-24s %s" % ("OK" if modes and set(modes) <= {"blur", "reframing"}
                             else "FAIL", "asset_modes", ", ".join(modes)))
    print("[OK] GLOBAL")
    return 0


def cmd_pack(a):
    cfg = _cfg()
    pack = json.loads(Path(a.pack).read_text(encoding="utf-8"))
    ok, code, msg = gates.g0_pack(pack, cfg)
    print("[%s] %s : %s" % ("OK" if ok else "FAIL", code, msg))
    return 0 if ok else 2


def cmd_title(a):
    cfg = _cfg()
    text = a.text or ""
    s1 = analyse(text, subject=a.subject or "",
                 internal_terms=a.internal.split(",") if a.internal else ())
    print("S1 dep=%.4f verdict=%s entites=%s internes=%s"
          % (s1["context_dependency"], s1["verdict"],
             s1["unexplained_entities"], s1["internal_terms"]))
    cands = gen_titles({"text": text, "subject": a.subject or "",
                        "number": a.number or "", "unit": a.unit or "une nuit"}, cfg)
    if not cands:
        print("  aucun gabarit valide -- ecris le titre a la main")
    for c in cands:
        print("  %s [%s] %s" % (c["template_id"], c["stake"], c["text"]))
    return 0


def cmd_campaign(a):
    cfg = _cfg()
    c = json.loads(Path(a.campaign).read_text(encoding="utf-8"))
    v = evaluate(c, cfg, a.platform)
    print(json.dumps(v, indent=2, ensure_ascii=False))
    if a.target:
        n = views_needed(float(a.target), float(c.get("rate_usd_per_1k") or 0),
                         float(cfg.get("platform_fee_pct", 0.10)),
                         float(cfg.get("default_approval_rate", 1.0)))
        print("vues brutes necessaires pour %.0f $ nets : %d" % (float(a.target), n))
    return 0


def cmd_export(a):
    """V2 : ne rend RIEN. Ecrit le pack livrable + une ligne de ledger par clip."""
    cfg = _cfg()
    pack = json.loads(Path(a.pack).read_text(encoding="utf-8"))

    ok, code, msg = gates.g0_pack(pack, cfg)
    if not ok:
        print("[FAIL] %s : %s" % (code, msg))
        return 2
    if pack.get("account"):
        ok, code, msg = gates.a1_account(pack["account"], cfg)
        if not ok:
            print("[FAIL] %s : %s" % (code, msg))
            return 2
    if pack.get("campaign"):
        ev = evaluate(pack["campaign"], cfg, a.platform)
        ok, code, msg = gates.a2_campaign(ev)
        if not ok:
            print("[FAIL] %s : %s" % (code, msg))
            return 2
    for asset in pack["assets"]:
        ok, code, msg = gates.s2_duration(asset["start_sec"], asset["end_sec"], cfg)
        if not ok:
            print("[FAIL] %s : %s %s" % (code, asset.get("id"), msg))
            return 2
        ok, code, msg = gates.c2_disclosure(asset, cfg)
        if not ok:
            print("[FAIL] %s : %s" % (code, msg))
            return 2

    now = now_iso()
    pt = pack_token(pack)
    tokens = clip_tokens(pack)
    pack["pack_token"] = pt
    for asset in pack["assets"]:
        asset["clip_token"] = tokens[str(asset["id"])]
        asset["exported_at"] = now

    ok, code, msg = gates.x1_export(pack, cfg)
    if not ok:
        print("[FAIL] %s : %s" % (code, msg))
        return 2

    exp_dir = (ROOT / cfg["export_dir"]).resolve()
    exp_dir.mkdir(parents=True, exist_ok=True)
    camp = pack.get("campaign") or {}
    cid = camp.get("campaign_id") or "unknown"
    out = exp_dir / ("%s%s.json" % (cfg.get("export_prefix", "production_pack_mark1_"), cid))
    out.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[OK] %s : %s" % (code, msg))
    print("[OK] pack ecrit : %s" % out)

    ledger_path = str((ROOT / cfg["ledger_path"]).resolve())
    mode = _asset_mode(pack)
    for asset in pack["assets"]:
        row = {
            "clip_token": asset["clip_token"], "pack_token": pt,
            "clip_id": asset["id"], "date": now[:10], "exported_at": now,
            "vod_url": (pack.get("source") or {}).get("vod_url"),
            "start_sec": asset["start_sec"], "end_sec": asset["end_sec"],
            "asset_mode": mode,
            "title": asset.get("title"),
            "campaign_id": camp.get("campaign_id"),
            "cpm_usd": camp.get("rate_usd_per_1k"), "platform": a.platform,
        }
        print("[%s] ledger : %s" % ("OK" if append(ledger_path, row) else "SKIP",
                                    asset["clip_token"]))
    return 0


def cmd_ledger(a):
    cfg = _cfg()
    if a.add:
        row = json.loads(Path(a.add).read_text(encoding="utf-8"))
        print("ecrit" if append(a.ledger, row) else "refuse ou deja present")
        return 0
    if a.update:
        changes = json.loads(a.changes) if a.changes else {}
        print("mis a jour" if update(a.ledger, a.update, **changes) else "clip_token absent")
        return 0

    rows = read(a.ledger)
    print("%d lignes" % len(rows))
    for r in rows[-10:]:
        print("  %s | %s | views=%s | payout=%s"
              % (r.get("clip_token"), r.get("title"),
                 r.get("views_approved") or "-", r.get("paid_usd") or "-"))
    if a.econ:
        fee = float(cfg.get("platform_fee_pct", 0.10))
        for r in rows:
            try:
                v = int(r.get("views_approved") or 0)
                cpm = float(r.get("cpm_usd") or 0)
                m = float(r.get("minutes_worked") or 0)
            except ValueError:
                continue
            print("  %s : %.2f $ net, %.2f $/h"
                  % (r.get("clip_token"), revenue(v, cpm, fee), usd_per_hour(v, cpm, m, fee)))
    return 0


def cmd_selftest(_a):
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=str(ROOT)).returncode


def main():
    p = argparse.ArgumentParser(prog="mark1")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor").set_defaults(f=cmd_doctor)

    q = sub.add_parser("pack")
    q.add_argument("pack")
    q.set_defaults(f=cmd_pack)

    q = sub.add_parser("title")
    q.add_argument("text")
    q.add_argument("--subject", default="")
    q.add_argument("--number", default="")
    q.add_argument("--unit", default="une nuit")
    q.add_argument("--internal", default="")
    q.set_defaults(f=cmd_title)

    q = sub.add_parser("campaign")
    q.add_argument("campaign")
    q.add_argument("--platform", default="tiktok")
    q.add_argument("--target", default=None)
    q.set_defaults(f=cmd_campaign)

    q = sub.add_parser("export")
    q.add_argument("pack")
    q.add_argument("--platform", default="tiktok")
    q.set_defaults(f=cmd_export)

    q = sub.add_parser("ledger")
    q.add_argument("--ledger", default=str(ROOT / "OUT" / "ledger.csv"))
    q.add_argument("--add", default=None)
    q.add_argument("--update", default=None)
    q.add_argument("--changes", default=None)
    q.add_argument("--econ", action="store_true")
    q.set_defaults(f=cmd_ledger)

    sub.add_parser("selftest").set_defaults(f=cmd_selftest)

    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
