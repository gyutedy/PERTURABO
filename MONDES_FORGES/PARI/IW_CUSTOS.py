"""
IW_CUSTOS.py — Gardien de la Flotte PERTURABO / Monde-Forge PARI
================================================================

Seul agent autorisé à modifier fleet_status dans liber_pari.json.
Toutes les frégates passent par lui — jamais de modification directe du liber.

Usage:
  python IW_CUSTOS.py --mode status
  python IW_CUSTOS.py --mode reset --siege-id PARI-001
  python IW_CUSTOS.py --mode check-out --frigate F01
  python IW_CUSTOS.py --mode check-in --frigate F01 --output F01_SENTINEL/OUT/matches_intel.json
  python IW_CUSTOS.py --mode gate --gate 1 --decision yes [--notes "carte ok"]
  python IW_CUSTOS.py --mode validate
"""

import argparse
import json
import os
import hashlib
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIBER_PATH   = os.path.join(_SCRIPT_DIR, "liber_pari.json")
CAMPAIGN_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "IW_CAMPAIGN_LOG.md")
TRANSFER_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "IW_TRANSFER_LOG.md")

VALID_FRIGATES = ["TYRANT", "F01", "F02", "F03", "F04", "F05", "F06"]

FLEET_STATUS_FLOW = [
    "pending_reconnaissance",
    "tyrant_report_ready",
    "intel_captured",
    "analysed",
    "value_detected",
    "reports_ready",
    "pack_ready",
    "tracked",
    "complete",
]

FRIGATE_STATUS_KEY = {
    "TYRANT": "tyrant_report",
    "F01":    "f01_sentinel",
    "F02":    "f02_breacher",
    "F03":    "f03_forgeward",
    "F04":    "f04_herald",
    "F05":    "f05_packager",
    "F06":    "f06_tracker",
}

FRIGATE_TRANSITIONS = {
    "TYRANT": "tyrant_report_ready",
    "F01":    "intel_captured",
    "F02":    "analysed",
    "F03":    "value_detected",
    "F04":    "reports_ready",
    "F05":    "pack_ready",
    "F06":    "tracked",
}

# Préconditions de fleet_status avant qu'une frégate puisse check-in
PRECONDITIONS = {
    "TYRANT": [],
    "F01":    ["tyrant_report_ready"],
    "F02":    ["intel_captured"],
    "F03":    ["analysed"],
    "F04":    ["value_detected"],
    "F05":    ["reports_ready"],
    "F06":    ["pack_ready"],
}

# Gate requise avant check-in
GATE_REQUIRED = {
    "TYRANT": None,
    "F01":    None,        # Gate 1 validée après TYRANT, AVANT F02/F03
    "F02":    "gate_1",
    "F03":    "gate_2",
    "F04":    None,
    "F05":    "gate_3",
    "F06":    "gate_4",
}

GATE_LABELS = {
    1: "Validation carte TYRANT (GO/NO-GO siège)",
    2: "Validation analyses BREACHER (probas, matrice)",
    3: "Validation verdicts FORGEWARD (EV, Kelly, combinés)",
    4: "Validation pari pack + dashboard",
}

TIMESTAMP_KEY = {
    "TYRANT": "tyrant_done",
    "F01":    "intel_done",
    "F02":    "breach_done",
    "F03":    "value_done",
    "F04":    "herald_done",
    "F05":    "pack_done",
    "F06":    "end",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_liber() -> dict:
    with open(LIBER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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
    ts = now_iso()
    with open(CAMPAIGN_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n## [{ts}] {event}\n")


def log_transfer(source: str, dest: str, md5: str, status: str):
    os.makedirs(os.path.join(_SCRIPT_DIR, "TRACKING"), exist_ok=True)
    ts = now_iso()
    entry = f"| {ts} | {source} | {dest} | {md5} | {status} |\n"
    header_needed = not os.path.exists(TRANSFER_LOG)
    with open(TRANSFER_LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("| TIMESTAMP | SOURCE | DEST | MD5 | STATUS |\n")
            f.write("|-----------|--------|------|-----|--------|\n")
        f.write(entry)


def _reset_field(obj, keys):
    for k in keys:
        if k in obj and isinstance(obj[k], (list, dict)):
            if isinstance(obj[k], list):
                obj[k] = [] if True else obj[k]
            else:
                for sub in obj[k]:
                    obj[k][sub] = None
        else:
            obj[k] = None


def cmd_reset(siege_id: str):
    """Initialise un nouveau siège — remet le liber à zéro avec un nouvel ID."""
    liber = load_liber()
    liber["fleet_status"] = "pending_reconnaissance"
    liber["siege_id"] = siege_id
    liber["warsmith_brief"] = {"mode": None, "ligue": None, "horizon": None, "notes": None}

    tr = liber["tyrant_report"]
    tr["status"] = "pending"
    for k in ["carte_valid", "nb_proies", "nb_no_bet", "seuil_ev_applique",
              "recommandation", "justification", "output_path"]:
        tr[k] = None

    for fkey in ["f01_sentinel", "f02_breacher", "f03_forgeward", "f04_herald", "f05_packager"]:
        liber[fkey]["status"] = "pending"
        for k in list(liber[fkey].keys()):
            if k != "status":
                if isinstance(liber[fkey][k], (int, float)):
                    liber[fkey][k] = 0 if k.endswith(("count", "total", "top", "matchs_analyses")) else None
                elif isinstance(liber[fkey][k], bool):
                    liber[fkey][k] = False
                else:
                    liber[fkey][k] = None

    t = liber["f06_tracker"]
    t["status"] = "idle"
    t["tickets_tracked"] = 0
    for k in ["roi_pct", "calibration_path", "last_settle"]:
        t[k] = None

    for gate_key in ["gate_1", "gate_2", "gate_3", "gate_4"]:
        liber["gate_decisions"][gate_key]["validated"] = False
        liber["gate_decisions"][gate_key]["timestamp"] = None
        liber["gate_decisions"][gate_key]["notes"] = None

    ts = now_iso()
    liber["siege_timestamps"] = {
        "start": ts,
        "tyrant_done": None, "intel_done": None, "breach_done": None,
        "value_done": None, "herald_done": None, "pack_done": None, "end": None,
    }
    liber["iw_custos"]["errors"] = []
    liber["iw_custos"]["last_validation"] = ts

    save_liber(liber)
    log_campaign(f"RESET — nouveau siège {siege_id} initialisé")
    print(f"[IW_CUSTOS] Siège {siege_id} initialisé. fleet_status: pending_reconnaissance")


def cmd_check_out(frigate: str):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    liber = load_liber()
    gate_req = GATE_REQUIRED.get(frigate)
    if gate_req:
        gate_data = liber["gate_decisions"].get(gate_req, {})
        if not gate_data.get("validated", False):
            print(f"[IW_CUSTOS] BLOQUÉ: {frigate} requiert {gate_req} validée.")
            print(f"  → Lance: python IW_CUSTOS.py --mode gate --gate {gate_req[-1]} --decision yes")
            return
    key = FRIGATE_STATUS_KEY[frigate]
    liber[key]["status"] = "processing"
    liber["iw_custos"]["last_validation"] = now_iso()
    save_liber(liber)
    log_campaign(f"{frigate} — check-out — status: processing")
    print(f"[IW_CUSTOS] {frigate} autorisée. Lecture des entrées possible.")


def cmd_check_in(frigate: str, output_path: str, extra: str = None):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    if not os.path.exists(output_path):
        print(f"[IW_CUSTOS] ERREUR: Fichier introuvable: {output_path}")
        liber = load_liber()
        liber[FRIGATE_STATUS_KEY[frigate]]["status"] = "error"
        liber["iw_custos"]["errors"].append(
            {"ts": now_iso(), "frigate": frigate, "msg": f"Output not found: {output_path}"}
        )
        save_liber(liber)
        return

    file_md5 = md5_file(output_path)
    liber = load_liber()
    key = FRIGATE_STATUS_KEY[frigate]
    liber[key]["status"] = "done"
    if "output_path" in liber[key]:
        liber[key]["output_path"] = output_path
    elif frigate == "TYRANT":
        liber[key]["output_path"] = output_path
    liber["iw_custos"]["last_validation"] = now_iso()
    liber["iw_custos"]["errors"] = [
        e for e in liber["iw_custos"]["errors"] if e.get("frigate") != frigate
    ]

    ts_key = TIMESTAMP_KEY.get(frigate)
    if ts_key:
        liber["siege_timestamps"][ts_key] = now_iso()

    _advance_fleet_status(liber, frigate)
    save_liber(liber)
    log_transfer(f"{frigate}/CODEBASE", output_path, file_md5, "OK")
    log_campaign(f"{frigate} — check-in — {output_path} — md5:{file_md5} — status:done")
    print(f"[IW_CUSTOS] {frigate} validée. fleet_status: {liber['fleet_status']}")

    _print_next_action(liber, frigate)


def _advance_fleet_status(liber: dict, completed_frigate: str):
    if completed_frigate not in FRIGATE_TRANSITIONS:
        return
    current = liber.get("fleet_status", "pending_reconnaissance")
    try:
        current_idx = FLEET_STATUS_FLOW.index(current)
    except ValueError:
        current_idx = 0
    for req in PRECONDITIONS.get(completed_frigate, []):
        try:
            req_idx = FLEET_STATUS_FLOW.index(req)
        except ValueError:
            req_idx = 0
        if current_idx < req_idx:
            print(f"[IW_CUSTOS] AVERT: {completed_frigate} check-in mais '{req}' non atteint. fleet_status inchangé.")
            return
    liber["fleet_status"] = FRIGATE_TRANSITIONS[completed_frigate]


def _print_next_action(liber: dict, completed_frigate: str):
    NEXT_STEPS = {
        "TYRANT": "→ Gate 1 requise: python IW_CUSTOS.py --mode gate --gate 1 --decision yes",
        "F01":    "→ python IW_CUSTOS.py --mode check-out --frigate F02 (après Gate 1)",
        "F02":    "→ Gate 2 requise: python IW_CUSTOS.py --mode gate --gate 2 --decision yes",
        "F03":    "→ Gate 3 requise: python IW_CUSTOS.py --mode gate --gate 3 --decision yes",
        "F04":    "→ python IW_CUSTOS.py --mode check-in --frigate F04 --output <reports_index>",
        "F05":    "→ Gate 4 requise pour settle F06. Pack + dashboard prêts.",
        "F06":    "→ Siège terminé. Ledger mis à jour. Consulter learnings/calibration.json.",
    }
    msg = NEXT_STEPS.get(completed_frigate, "")
    if msg:
        print(f"[IW_CUSTOS] ACTION SUIVANTE: {msg}")


def cmd_gate(gate_num: int, decision: str, notes: str = None):
    if gate_num not in [1, 2, 3, 4]:
        print("[IW_CUSTOS] ERREUR: gate doit être 1, 2, 3 ou 4")
        return
    liber = load_liber()
    gate_key = f"gate_{gate_num}"
    validated = decision.lower() in ["yes", "oui", "y", "1", "true"]
    liber["gate_decisions"][gate_key]["validated"] = validated
    liber["gate_decisions"][gate_key]["timestamp"] = now_iso()
    liber["gate_decisions"][gate_key]["notes"] = notes
    liber["iw_custos"]["last_validation"] = now_iso()
    save_liber(liber)
    status = "VALIDÉE" if validated else "REJETÉE"
    label = GATE_LABELS[gate_num]
    log_campaign(f"Gate {gate_num} ({label}) — {status}" + (f" — {notes}" if notes else ""))
    print(f"[IW_CUSTOS] Gate {gate_num} ({label}): {status}")
    if not validated:
        print("[IW_CUSTOS] Gate rejetée. Relancer la frégate précédente ou ajuster.")
    else:
        GATE_UNLOCKS = {
            1: "F02 (BREACHER) — pigeon: orchestrator --mode siege",
            2: "F03 (FORGEWARD)",
            3: "F04 (HERALD)",
            4: "settle F06 (TRACKER)",
        }
        unlock = GATE_UNLOCKS.get(gate_num, "")
        if unlock:
            print(f"[IW_CUSTOS] Débloqué: {unlock}")


def cmd_validate():
    required_keys = [
        "fleet_status", "siege_id", "monde", "warsmith_brief",
        "tyrant_report", "f01_sentinel", "f02_breacher", "f03_forgeward",
        "f04_herald", "f05_packager", "f06_tracker",
        "iw_custos", "gate_decisions", "siege_timestamps",
    ]
    try:
        with open(LIBER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        missing = [k for k in required_keys if k not in data]
        if missing:
            print(f"[IW_CUSTOS] SCHEMA INVALIDE — Clés manquantes: {missing}")
            log_campaign("Validation schema — FAIL")
        else:
            print(f"[IW_CUSTOS] SCHEMA VALIDE — {LIBER_PATH}")
            log_campaign("Validation schema — PASS")
    except json.JSONDecodeError as e:
        print(f"[IW_CUSTOS] ERREUR JSON: {e}")


def cmd_status():
    liber = load_liber()
    s = liber
    g = s["gate_decisions"]

    def gstatus(key):
        return "✅" if g[key]["validated"] else "⬜"

    def fstatus(key):
        st = s.get(key, {}).get("status", "?")
        icons = {"pending": "⬜", "processing": "🔄", "done": "✅", "error": "❌", "idle": "💤"}
        return icons.get(st, "?") + " " + st

    nb_values = s["f03_forgeward"].get("values_count", 0) or 0
    nb_nogay = s["f03_forgeward"].get("no_bet_count", 0) or 0
    pack_top = s["f05_packager"].get("pack_top", 0) or 0

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  IW_CUSTOS — MONDE-FORGE PARI                               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  fleet_status    : {s['fleet_status']:<40}║")
    print(f"║  siege_id        : {str(s.get('siege_id') or '—'):<40}║")
    print(f"║  ligue           : {str(s['warsmith_brief'].get('ligue') or '—'):<40}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  TYRANT          : {fstatus('tyrant_report'):<40}║")
    print(f"║  F01 SENTINEL    : {fstatus('f01_sentinel'):<40}║")
    print(f"║  F02 BREACHER    : {fstatus('f02_breacher'):<40}║")
    print(f"║  F03 FORGEWARD   : {fstatus('f03_forgeward')} ({nb_values} values / {nb_nogay} NO BET) ".ljust(63) + "║")
    print(f"║  F04 HERALD      : {fstatus('f04_herald'):<40}║")
    print(f"║  F05 PACKAGER    : {fstatus('f05_packager')} (top {pack_top})".ljust(63) + "║")
    print(f"║  F06 TRACKER     : {fstatus('f06_tracker'):<40}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Gate 1 (carte)      : {gstatus('gate_1'):<35}║")
    print(f"║  Gate 2 (analyses)   : {gstatus('gate_2'):<35}║")
    print(f"║  Gate 3 (verdicts)   : {gstatus('gate_3'):<35}║")
    print(f"║  Gate 4 (pack)       : {gstatus('gate_4'):<35}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    errors = s["iw_custos"]["errors"]
    last_val = s["iw_custos"]["last_validation"] or "jamais"
    print(f"║  Erreurs         : {str(len(errors)):<40}║")
    print(f"║  Last check      : {last_val:<40}║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


def main():
    parser = argparse.ArgumentParser(description="IW_CUSTOS — Gardien Monde-Forge PARI")
    parser.add_argument("--mode", required=True,
                        choices=["status", "reset", "check-out", "check-in", "gate", "validate"])
    parser.add_argument("--frigate", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--siege-id", default=None)
    parser.add_argument("--gate", type=int, default=None)
    parser.add_argument("--decision", default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    if args.mode == "status":
        cmd_status()
    elif args.mode == "reset":
        sid = args.siege_id or f"PARI-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
        cmd_reset(sid)
    elif args.mode == "check-out":
        if not args.frigate:
            print("[IW_CUSTOS] --frigate requis pour check-out")
            return
        cmd_check_out(args.frigate)
    elif args.mode == "check-in":
        if not args.frigate or not args.output:
            print("[IW_CUSTOS] --frigate et --output requis pour check-in")
            return
        cmd_check_in(args.frigate, args.output)
    elif args.mode == "gate":
        if args.gate is None or not args.decision:
            print("[IW_CUSTOS] --gate et --decision requis")
            return
        cmd_gate(args.gate, args.decision, args.notes)
    elif args.mode == "validate":
        cmd_validate()


if __name__ == "__main__":
    main()
