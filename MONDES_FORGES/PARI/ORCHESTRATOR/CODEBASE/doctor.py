#!/usr/bin/env python3
"""
DOCTOR — evidence stack (S2 / v3.1)
===================================
GO / CHECK / FAIL. Offline. Noms de cles seulement, jamais les valeurs.
Gate : n<300 bruit ; 300-499 observation ; >=500 verdict moteur.
CLV median 30j < -3 pts = alerte immediate.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))

KEY_WATCH = (
    "FOOTBALL_DATA_ORG_KEY",
    "API_FOOTBALL_KEY",
    "SPORTRADAR_API_KEY",
    "SOFASCORE_RAPIDAPI_KEY",
    "WHOSCORED_KEY",
    "ODDS_API_KEY",
    "THE_ODDS_API_KEY",
    "ORACLE_API_KEY",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)

CONNECTORS = (
    "football_data_uk",
    "clubelo",
    "api_football",
    "football_data_org",
    "understat",
    "sofascore",
    "sportradar",
    "espn",
    "whoscored",
    "odds_api",
)

CONTRACT_ARTEFACTS = (
    ("schema_match_intel.json", ("F01_SENTINEL", "OUT", "matches_intel.json")),
    ("schema_analysis.json", ("F02_BREACHER", "OUT", "analysis.json")),
    ("schema_predictions.json", ("F03_FORGEWARD", "OUT", "predictions.json")),
    ("schema_pari_pack.json", ("F05_PACKAGER", "OUT", "pari_pack.json")),
)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _key_names_from_envfile(world):
    names = []
    for name in ("env_pari", ".env"):
        path = os.path.join(world, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k = line.split("=", 1)[0].strip()
                    if k:
                        names.append(k)
        except OSError:
            pass
    return names


def check_cles(world):
    file_names = set(_key_names_from_envfile(world))
    present, absent = [], []
    for k in KEY_WATCH:
        if k in file_names or os.environ.get(k):
            present.append(k)
        else:
            absent.append(k)
    ok = True
    note = ""
    if not present:
        ok = False
        note = "aucune cle nommee (enrich skip)"
    return {
        "id": "cles",
        "ok": ok,
        "present": present,
        "absent": absent,
        "note": note,
    }


def _required_missing(schema, data, prefix=""):
    missing = []
    if not isinstance(schema, dict):
        return missing
    if not isinstance(data, dict):
        return [prefix or "$"]
    req = schema.get("required") or []
    props = schema.get("properties") or {}
    for k in req:
        if k not in data:
            missing.append(f"{prefix}.{k}" if prefix else k)
    for k, sub in props.items():
        if k not in data or not isinstance(sub, dict):
            continue
        val = data[k]
        if sub.get("type") == "object" and isinstance(val, dict):
            missing += _required_missing(sub, val, f"{prefix}.{k}" if prefix else k)
        elif sub.get("type") == "array" and isinstance(val, list) and val:
            items = sub.get("items")
            if isinstance(items, dict) and isinstance(val[0], dict):
                missing += _required_missing(
                    items, val[0], f"{prefix}.{k}[]" if prefix else f"{k}[]")
    return missing


def check_contrats(world, code_world):
    holes, missing = [], []
    details = []
    for schema_name, rel in CONTRACT_ARTEFACTS:
        schema = _load_json(os.path.join(code_world, "CONTRACTS", schema_name))
        art = os.path.join(world, *rel)
        if schema is None:
            holes.append("schema:" + schema_name)
            continue
        data = _load_json(art)
        if data is None:
            holes.append("/".join(rel))
            details.append({"schema": schema_name, "artefact": "/".join(rel), "status": "absent"})
            continue
        miss = _required_missing(schema, data)
        if miss:
            missing.extend(schema_name + ":" + m for m in miss)
        details.append({
            "schema": schema_name,
            "artefact": "/".join(rel),
            "status": "fail" if miss else "ok",
            "missing": miss,
        })
    return {
        "id": "contrats",
        "ok": not missing,
        "missing_fields": missing,
        "holes": holes,
        "details": details,
    }


def check_whitelist(code_world):
    cap_dir = os.path.join(code_world, "F00_RADAR", "CODEBASE")
    conn_dir = os.path.join(code_world, "F01_SENTINEL", "CODEBASE", "connectors")
    if cap_dir not in sys.path:
        sys.path.insert(0, cap_dir)
    import capteurs  # noqa: E402
    missing_files = []
    for name in CONNECTORS:
        if not os.path.exists(os.path.join(conn_dir, name + ".py")):
            missing_files.append(name)
    espn_leagues = {}
    espn_path = os.path.join(conn_dir, "espn.py")
    if os.path.exists(espn_path):
        if conn_dir not in sys.path:
            sys.path.insert(0, conn_dir)
        import espn  # noqa: E402
        espn_leagues = dict(getattr(espn, "LEAGUES", {}) or {})
    ligues = sorted(set(capteurs.LIGUE_CODE.values()))
    notes_gap = sorted(c for c in ligues if c not in espn_leagues)
    return {
        "id": "whitelist",
        "ok": not missing_files,
        "ligues": ligues,
        "connectors": list(CONNECTORS),
        "missing_connectors": missing_files,
        "holes": ["espn:" + c for c in notes_gap],
        "note": "E1/D2 whitelist sans voix ESPN" if notes_gap else "",
    }


def _age_hours(path, now):
    if not path or not os.path.exists(path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    return (now - mtime).total_seconds() / 3600.0


def check_cache(world, now=None):
    now = now or datetime.now(timezone.utc)
    holes = []
    ages = {}
    paths = {
        "elo": os.path.join(world, "ARCHIVUM", "teams", "elo.json"),
        "odds": os.path.join(world, "ARCHIVUM", "odds", "latest.json"),
        "shares": os.path.join(world, "ARCHIVUM", "learnings", "shares.json"),
    }
    stale = []
    for name, path in paths.items():
        age = _age_hours(path, now)
        if age is None:
            holes.append(name)
            continue
        ages[name] = round(age, 2)
        if age > 48:
            stale.append(name)
        blob = _load_json(path)
        if isinstance(blob, dict) and "elo" in (blob.get("holes") or []):
            holes.append("elo")
    cache_dir = os.path.join(world, "ARCHIVUM", "cache", "f00")
    if not os.path.isdir(cache_dir):
        holes.append("cache/f00")
    return {
        "id": "cache",
        "ok": True,
        "holes": sorted(set(holes)),
        "age_hours": ages,
        "stale_48h": stale,
        "note": "trous declares, jamais inventes",
    }


def _parse_iso(ts):
    raw = (ts or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _clv_values(lots, now):
    cut = now - timedelta(days=30)
    vals = []
    for lot in lots or []:
        created = _parse_iso(lot.get("created_at") or lot.get("settled_at"))
        if created is not None and created < cut:
            continue
        if isinstance(lot.get("clv"), (int, float)):
            vals.append(float(lot["clv"]))
        settle = lot.get("settle") or {}
        if isinstance(settle.get("clv_median"), (int, float)):
            vals.append(float(settle["clv_median"]))
        for t in settle.get("tickets") or []:
            if isinstance(t.get("clv"), (int, float)):
                vals.append(float(t["clv"]))
            elif isinstance(t.get("clv_pts"), (int, float)):
                vals.append(float(t["clv_pts"]))
    return vals


def check_clv(world, now=None):
    now = now or datetime.now(timezone.utc)
    box = _load_json(os.path.join(world, "ARCHIVUM", "learnings", "lots.json")) or {}
    vals = _clv_values(box.get("lots") or [], now)
    if not vals:
        return {
            "id": "clv",
            "ok": True,
            "median_30j": None,
            "n": 0,
            "alerte": False,
            "holes": ["clv"],
            "note": "CLV absent (S8) — trou, pas 0",
        }
    med = float(median(vals))
    alerte = med < -3.0
    return {
        "id": "clv",
        "ok": not alerte,
        "median_30j": round(med, 4),
        "n": len(vals),
        "alerte": alerte,
        "holes": [],
        "note": "CLV median 30j < -3 pts" if alerte else "",
    }


def _n_tickets(world):
    box = _load_json(os.path.join(world, "ARCHIVUM", "learnings", "lots.json")) or {}
    n = 0
    for lot in box.get("lots") or []:
        snap = (lot.get("snapshot_t0") or {}).get("tickets") or lot.get("tickets") or []
        n += len(snap)
        settle = (lot.get("settle") or {}).get("tickets") or []
        if settle and not snap:
            n += len(settle)
    if n:
        return n
    tix = _load_json(os.path.join(world, "ARCHIVUM", "learnings", "tickets.json")) or {}
    return len(tix.get("tickets") or [])


def gate_for(n):
    if n < 300:
        return {"n_tickets": n, "niveau": "bruit", "note": "n<300 — pas un verdict moteur"}
    if n < 500:
        return {"n_tickets": n, "niveau": "observation", "note": "300-499 — observation"}
    return {"n_tickets": n, "niveau": "moteur", "note": "n>=500 — verdict moteur autorise"}


def diagnose(world=None, code_world=None, now=None):
    world = world or CODE_WORLD
    code_world = code_world or CODE_WORLD
    now = now or datetime.now(timezone.utc)
    checks = [
        check_cles(world),
        check_contrats(world, code_world),
        check_whitelist(code_world),
        check_cache(world, now=now),
        check_clv(world, now=now),
    ]
    holes = []
    for c in checks:
        holes.extend(c.get("holes") or [])
    fail_ids = [c["id"] for c in checks if not c.get("ok")]
    clv = next(c for c in checks if c["id"] == "clv")
    contrats = next(c for c in checks if c["id"] == "contrats")
    whitelist = next(c for c in checks if c["id"] == "whitelist")
    if clv.get("alerte") or contrats.get("missing_fields") or whitelist.get("missing_connectors"):
        verdict = "FAIL"
    elif fail_ids or holes:
        verdict = "CHECK"
    else:
        verdict = "GO"
    report = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "offline",
        "verdict": verdict,
        "gate": gate_for(_n_tickets(world)),
        "checks": checks,
        "holes": sorted(set(holes)),
        "fail_ids": fail_ids,
    }
    return report


def format_telegram(report):
    if not report:
        return "doctor: indisponible"
    gate = report.get("gate") or {}
    lines = [
        f"DOCTOR **{report.get('verdict')}** · gate {gate.get('niveau')} (n={gate.get('n_tickets')})",
    ]
    for c in report.get("checks") or []:
        cid = c.get("id")
        if cid == "cles":
            lines.append(
                f"cles: {len(c.get('present') or [])} presentes, "
                f"{len(c.get('absent') or [])} absentes (noms)"
            )
        elif cid == "contrats":
            miss = c.get("missing_fields") or []
            lines.append("contrats: OK" if not miss else "contrats: FAIL " + ",".join(miss[:4]))
        elif cid == "whitelist":
            holes = c.get("holes") or []
            lines.append("whitelist: OK" + (f" · {c.get('note')}" if c.get("note") else ""))
            if holes:
                lines.append("whitelist holes: " + ",".join(holes[:6]))
        elif cid == "cache":
            h = c.get("holes") or []
            lines.append("cache holes: " + (",".join(h) if h else "—"))
        elif cid == "clv":
            if c.get("alerte"):
                lines.append(f"CLV ALERTE median_30j={c.get('median_30j')}")
            elif c.get("holes"):
                lines.append("CLV: trou (pas 0)")
            else:
                lines.append(f"CLV median_30j={c.get('median_30j')}")
    return "\n".join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    world = CODE_WORLD
    as_json = False
    while argv:
        a = argv.pop(0)
        if a == "--world" and argv:
            world = argv.pop(0)
        elif a == "--json":
            as_json = True
        elif a in ("--offline",):
            continue
        elif a in ("-h", "--help"):
            print("doctor.py --offline --json [--world PATH]")
            return 0
    report = diagnose(world=world, code_world=CODE_WORLD)
    if as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_telegram(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
