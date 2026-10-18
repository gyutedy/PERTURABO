"""
IW_CUSTOS.py — Gardien du Monde Forge CLIPPING
===============================================

Seul agent autorisé à modifier l'état des frégates dans liber_clipping.json.
Équivalent de IW_CUSTOS.py du core PERTURABO, adapté aux frégates du forge CLIPPING.

Usage:
  python IW_CUSTOS.py --mode check-out --frigate F01
  python IW_CUSTOS.py --mode check-in --frigate F01 --output F01_SCOUT/OUT/source_specimen.json
  python IW_CUSTOS.py --mode close-campaign
  python IW_CUSTOS.py --mode validate --schema liber_clipping.json
  python IW_CUSTOS.py --mode status
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIBER_PATH = os.path.join(_SCRIPT_DIR, "liber_clipping.json")
CAMPAIGN_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "CLIPPING_LOG.md")
TRANSFER_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "IW_TRANSFER_LOG.md")

VALID_FRIGATES = ["F01", "F02", "F03", "F04", "F05", "F06", "TYRANT", "CAPTEURS", "ANGLESMITH"]

FRIGATE_STATUS_KEY = {
    "F01": "f01_scout",
    "F02": "f02_tyrant_camp",
    "F03": "f03_source_hunter",
    "F04": "f04_copywriter",
    "F05": "f05_packager",
    "F06": "f06_tracker",
    "TYRANT": "tyrant",
    "CAPTEURS": "capteurs",
    "ANGLESMITH": "anglesmith",
}

FLOW = [
    "pending",
    "capteurs_done",
    "tyrant_done",
    "verdict_ready",
    "specimen_captured",
    "angles_forged",
    "specimens_selected",
    "text_payloads_forged",
    "packs_assembled",
    "packs_expedited",
    "campaign_closed",
]

FRIGATE_TRANSITIONS = {
    "TYRANT": "tyrant_done",
    "CAPTEURS": "capteurs_done",
    "F01": "specimen_captured",
    "F02": "verdict_ready",
    "ANGLESMITH": "angles_forged",
    "F03": "specimens_selected",
    "F04": "text_payloads_forged",
    "F05": "packs_assembled",
    "F06": "campaign_closed",
}

PRECONDITIONS = {
    "TYRANT": [],
    "CAPTEURS": [],
    "F01": ["tyrant_done", "capteurs_done"],
    "F02": ["specimen_captured"],
    "ANGLESMITH": ["verdict_ready"],
    "F03": ["angles_forged"],
    "F04": ["specimens_selected"],
    "F05": ["text_payloads_forged"],
    "F06": ["packs_assembled"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_liber() -> dict:
    if not os.path.exists(LIBER_PATH):
        raise FileNotFoundError(f"liber_clipping.json introuvable: {LIBER_PATH}")
    with open(LIBER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("fregates_status", {})
    data.setdefault("iw_custos", {})
    data["iw_custos"].setdefault("errors", [])
    return data


def save_liber(data: dict):
    with open(LIBER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def log_campaign(event: str):
    os.makedirs(os.path.join(_SCRIPT_DIR, "TRACKING"), exist_ok=True)
    entry = f"\n## [{now_iso()}] {event}\n"
    with open(CAMPAIGN_LOG, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[IW_CUSTOS] LOG: {event}")


def log_transfer(source: str, dest: str, md5: str, status: str):
    os.makedirs(os.path.join(_SCRIPT_DIR, "TRACKING"), exist_ok=True)
    ts = now_iso()
    header_needed = not os.path.exists(TRANSFER_LOG)
    with open(TRANSFER_LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("| TIMESTAMP | SOURCE | DEST | MD5 | STATUS |\n")
            f.write("|-----------|--------|------|-----|--------|\n")
        f.write(f"| {ts} | {source} | {dest} | {md5} | {status} |\n")


def _advance_fleet_status(cms: dict, completed_frigate: str):
    if completed_frigate not in FRIGATE_TRANSITIONS:
        return
    current = cms.get("fleet_status", "pending")
    try:
        current_idx = FLOW.index(current)
    except ValueError:
        current_idx = 0
    for req in PRECONDITIONS.get(completed_frigate, []):
        try:
            req_idx = FLOW.index(req)
        except ValueError:
            req_idx = 0
        if current_idx < req_idx:
            print(f"[IW_CUSTOS] AVERTISSEMENT: {completed_frigate} check-in"
                  f" mais '{req}' non atteint (actuel: '{current}'). fleet_status inchangé.")
            return
    cms["fleet_status"] = FRIGATE_TRANSITIONS[completed_frigate]


def cmd_check_out(frigate: str):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    cms = load_liber()
    key = FRIGATE_STATUS_KEY[frigate]
    cms["fregates_status"][key] = "processing"
    cms["iw_custos"]["last_validation"] = now_iso()
    save_liber(cms)
    log_campaign(f"{frigate} — check-out — status: processing")
    print(f"[IW_CUSTOS] {frigate} autorisée à lire ses entrées.")


def cmd_check_in(frigate: str, output_path: str):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    if not os.path.exists(output_path):
        print(f"[IW_CUSTOS] ERREUR: Fichier de sortie introuvable: {output_path}")
        cms = load_liber()
        cms["fregates_status"][FRIGATE_STATUS_KEY[frigate]] = "error"
        cms["iw_custos"]["errors"].append(
            {"ts": now_iso(), "frigate": frigate, "msg": f"Output not found: {output_path}"}
        )
        save_liber(cms)
        return

    file_md5 = md5_file(output_path)
    cms = load_liber()
    key = FRIGATE_STATUS_KEY[frigate]
    cms["fregates_status"][key] = "done"
    cms["fregates_status"][f"{key}_output"] = output_path
    cms["iw_custos"]["last_validation"] = now_iso()
    cms["iw_custos"]["errors"] = [e for e in cms["iw_custos"]["errors"]
                                   if e.get("frigate") != frigate]
    _advance_fleet_status(cms, frigate)
    save_liber(cms)
    log_transfer(f"{frigate}/CODEBASE", output_path, file_md5, "OK")
    log_campaign(f"{frigate} — check-in — output: {output_path} — md5: {file_md5} — status: done")
    print(f"[IW_CUSTOS] {frigate} validée. fleet_status: {cms['fleet_status']}")


def cmd_validate(schema_path: str):
    required_keys = [
        "siege_id", "campaign_id", "campaign_status", "current_porte",
        "inputs_warsmith", "fregates_status", "portes_validated",
        "packs_expedies_count", "packs_posted_count", "packs_submitted_whop_count",
        "last_event", "siege_started_at", "siege_closed_at",
    ]
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        missing = [k for k in required_keys if k not in data]
        if missing:
            print(f"[IW_CUSTOS] SCHEMA INVALIDE — Clés manquantes: {missing}")
        else:
            print(f"[IW_CUSTOS] SCHEMA VALIDE — {schema_path}")
        log_campaign(f"Schema validation PASS — {schema_path}")
    except json.JSONDecodeError as e:
        print(f"[IW_CUSTOS] ERREUR JSON: {e}")


def cmd_status():
    cms = load_liber()
    print("\n" + "=" * 58)
    print("IW_CUSTOS — ÉTAT DU FORGE CLIPPING")
    print("-" * 58)
    print(f"fleet_status    : {str(cms.get('fleet_status', 'pending'))}")
    print(f"mode            : {str(cms.get('mode', 'whop'))}")
    print(f"siege_id        : {str(cms.get('siege_id', 'null'))}")
    print(f"campaign_status : {str(cms.get('campaign_status', 'null'))}")
    print(f"current_porte   : {str(cms.get('current_porte', 'null'))}")
    fs = cms.get("fregates_status", {})
    for code, label in [
        ("F01", "F01 SCOUT"), ("F02", "F02 TYRANT_CAMP"), ("F03", "F03 SOURCE_HUNTER"),
        ("F04", "F04 COPYWRITER"), ("F05", "F05 PACKAGER"), ("F06", "F06 TRACKER"),
        ("TYRANT", "TYRANT"), ("CAPTEURS", "CAPTEURS"), ("ANGLESMITH", "ANGLESMITH"),
    ]:
        status = fs.get(FRIGATE_STATUS_KEY[code], "pending")
        print(f"{label:<17}: {str(status)}")
    print(f"Last validation : {str(cms['iw_custos'].get('last_validation', 'jamais'))}")
    errors = cms["iw_custos"].get("errors", [])
    print(f"Erreurs         : {str(len(errors))}")
    print("=" * 58 + "\n")


def cmd_close_campaign():
    """Ferme la campagne dans le ledger — déclenché par F06_TRACKER au
    --close-campaign. Seul IW_CUSTOS écrit liber_clipping.json."""
    cms = load_liber()
    if cms.get("campaign_status") == "closed":
        print(f"[IW_CUSTOS] Campagne déjà fermée: {cms.get('campaign_id')}")
        return
    cms["campaign_status"] = "closed"
    cms["siege_closed_at"] = now_iso()
    cms["last_event"] = "campaign_closed"
    cms["iw_custos"]["last_validation"] = now_iso()
    save_liber(cms)
    log_campaign(f"campaign_closed — {cms.get('campaign_id')} — siege_closed_at: {cms['siege_closed_at']}")
    print(f"[IW_CUSTOS] Campagne fermée. siege_closed_at: {cms['siege_closed_at']}")


def cmd_init_siege(profile: str):
    """Initialise le siège et fige le profil actif (whop|logo).
    Decide au debut du siege: tout le workflow se cale ensuite sur ce profil.
    Un siege = un seul profil (pas de melting mid-campaign)."""
    if profile not in ("whop", "logo"):
        print(f"[IW_CUSTOS] profil inconnu: '{profile}' (attendu: whop|logo)")
        return
    cms = load_liber()
    if cms.get("campaign_status") == "active":
        print(f"[IW_CUSTOS] Siege deja actif ({cms.get('siege_id')}). "
              f"Ferme-le avant d'en initier un nouveau.")
        return
    cms["mode"] = profile
    cms["campaign_status"] = "active"
    cms["current_porte"] = "init"
    cms["fleet_status"] = "pending"
    cms["siege_id"] = f"SIEGE-{profile.upper()}-{now_iso().replace(':', '').replace('-', '')[:15]}"
    cms["siege_started_at"] = now_iso()
    cms["siege_closed_at"] = None
    cms["last_event"] = f"siege_init_mode_{profile}"
    cms["iw_custos"]["last_validation"] = now_iso()
    save_liber(cms)
    log_campaign(f"siege_init — mode={profile} — siege_id={cms['siege_id']}")
    print(f"[IW_CUSTOS] Siege initialise. mode: {profile} — "
          f"siege_id: {cms['siege_id']}")


def main():
    parser = argparse.ArgumentParser(description="IW_CUSTOS — Gardien du forge CLIPPING")
    parser.add_argument("--mode", required=True,
                        choices=["check-out", "check-in", "validate", "status",
                                 "close-campaign", "init-siege"])
    parser.add_argument("--frigate", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--schema", default=LIBER_PATH)
    parser.add_argument("--profile", default=None, choices=["whop", "logo"],
                        help="Profil actif (pour --mode init-siege)")
    args = parser.parse_args()

    if args.mode == "check-out":
        if not args.frigate:
            print("[IW_CUSTOS] --frigate requis pour check-out")
            return
        cmd_check_out(args.frigate)
    elif args.mode == "check-in":
        if not args.frigate or not args.output:
            print("[IW_CUSTOS] --frigate et --output requis pour check-in")
            return
        cmd_check_in(args.frigate, args.output)
    elif args.mode == "validate":
        cmd_validate(args.schema)
    elif args.mode == "status":
        cmd_status()
    elif args.mode == "close-campaign":
        cmd_close_campaign()
    elif args.mode == "init-siege":
        if not args.profile:
            print("[IW_CUSTOS] --profile whop|logo requis pour --mode init-siege")
            return
        cmd_init_siege(args.profile)


if __name__ == "__main__":
    main()
