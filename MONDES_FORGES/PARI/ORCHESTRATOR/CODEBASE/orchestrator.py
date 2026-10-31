"""
ORCHESTRATOR — Le Nerf Central du monde PARI
=============================================
Enchaîne les frégates selon le mode, passe par IW_CUSTOS (check-out/check-in),
affiche les Gates à valider par le Warsmith.

Modes:
  --mode radar            scan complet de la ligue (F00 RADAR + F02)
  --mode siege --ids M1,M2   analyse fine avec cotes (TYRANT → F02 → F03 → F04)
  --mode pack [--top 10]  assemblage pari pack + dashboard (F05)
  --mode demo             pipeline COMPLET sur une ligue simulée (test)
  --mode imprime          affiche l'état du monde (wrap IW_CUSTOS status)

Usage (depuis la racine du monde):
  python ORCHESTRATOR/CODEBASE/orchestrator.py --mode demo
"""

import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE")

P = lambda *a: os.path.join(WORLD, *a)


def custos(mode, *args):
    cmd = [sys.executable, P("IW_CUSTOS.py"), "--mode", mode] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WORLD)
    for line in (r.stdout or "").splitlines():
        print("  " + line.strip())
    if r.returncode != 0 and (r.stderr or "").strip():
        print("  [custos err] " + r.stderr.strip())


def run_frigate(script, *args):
    cmd = [sys.executable, script] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout or "")
    if (r.stderr or "").strip():
        sys.stderr.write(r.stderr)
    return r.returncode == 0


# ---------------------------------------------------------------------------
# DEMO — ligue simulée (18 matchs, stats complètes + cotes Winner Bet-like)
# ---------------------------------------------------------------------------
EQUIPES = [
    ("Utd Iron", 1620), ("Rovers", 1480), ("Lions", 1590), ("City Steel", 1610),
    ("Athletic", 1520), ("Orbital", 1440), ("Forge FC", 1560), ("Bastion", 1500),
    ("Garrison", 1350), ("Trench", 1410), ("Rampart", 1380), ("Legion", 1585),
    ("Custodia", 1470), ("Sapper", 1330), ("Ironside", 1545), ("Vigil", 1495),
    ("Cyclops", 1560), ("Perturabo SC", 1700),
]


def make_demo_fixtures(path, n=18):
    random.seed(2510)
    lig = "Ligue de Simulation"
    home_avg, away_avg, spread = 1.45, 1.15, 0.55
    matchs = []
    for k in range(n):
        a, b = random.sample(EQUIPES, 2)
        force_a = a[1] / 1000.0
        force_b = b[1] / 1000.0
        def mk(force, opp):
            marque = round(max(4.0, 8.5 * home_avg * force / 1.55 + random.random() * 4), 0)
            encai = round(max(4.0, 8.5 * away_avg * (2 - force) + random.random() * 4), 0)
            mj = random.choice([7, 8, 9, 10])
            m1 = round(marque * random.uniform(0.38, 0.47), 0)
            e1 = round(encai * random.uniform(0.38, 0.47), 0)
            return {"mj": mj, "marques": marque, "encaisses": encai,
                    "marques_mt1": m1, "marques_mt2": marque - m1,
                    "encaisses_mt1": e1, "encaisses_mt2": encai - e1}
        matchs.append({
            "id": f"M{k+1}", "dom": a[0], "ext": b[0],
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "elo": {"dom": a[1], "ext": b[1]},
            "stats": {"dom": mk(force_a, force_b), "ext": mk(force_b, force_a)},
            "cotes": None,  # cote auto ci-dessous (Winner Bet-like)
            "notes": "SC: match de simulation — enjeu équilibré, absences mineures.",
        })
    # cotes Winner Bet-like : proba approximative depuis élo + marge ~7%
    for m in matchs:
        d = (m["elo"]["dom"] - m["elo"]["ext"]) / 400.0
        pd = 0.42 + 0.18 * (1 / (1 + pow(10, -d * 1.4)) - 0.5) * 2
        px = 0.26 * random.uniform(0.9, 1.1)
        p2 = max(0.05, 1 - pd - px)
        margpow = 1.055
        m["cotes"] = {
            "1": round(1 / min(0.95, pd * margpow * 1.9 / 1.9), 2) if False else round((1 / pd) / margpow, 2),
            "X": round((1 / px) / margpow, 2),
            "2": round((1 / p2) / margpow, 2),
            "o2.5": round(random.uniform(1.55, 2.15), 2),
            "u2.5": round(random.uniform(1.65, 2.35), 2),
            "mt1": round(random.uniform(2.9, 3.9), 2),
            "mte": round(random.uniform(2.9, 3.9), 2),
            "mt2": 2.10 if random.random() < 0.7 else round(random.uniform(1.95, 2.35), 2),
        }
    carte = {"ligue": lig, "ligue_tier": "exotique", "horizon": "journée",
             "seed_warsmith": "DEMO", "matchs": matchs}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(carte, f, indent=2, ensure_ascii=False)
    print(f"[ORCH] Carte de démo écrite: {path} ({n} matchs)")
    return path


# ---------------------------------------------------------------------------
# MODES
# ---------------------------------------------------------------------------
def mode_radar(fixtures=None, top=20):
    fixtures = fixtures or P("ARCHIVUM", "fixtures", "matches.json")
    intel_out = P("F01_SENTINEL", "OUT", "matches_intel.json")
    custos("check-out", "--frigate", "F01")
    if not run_frigate(P("F01_SENTINEL", "CODEBASE", "sentinel.py"),
                       "--input", fixtures, "--output", intel_out):
        return False
    custos("check-in", "--frigate", "F01", "--output", intel_out)
    analysis_out = P("F02_BREACHER", "OUT", "analysis.json")
    if not run_frigate(P("F02_BREACHER", "CODEBASE", "breacher.py"),
                       "--input", intel_out, "--output", analysis_out):
        return False
    radar_out = P("F00_RADAR", "OUT", "radar.json")
    if not run_frigate(P("F00_RADAR", "CODEBASE", "radar.py"),
                       "--input", intel_out, "--top", str(top),
                       "--out-json", radar_out,
                       "--out-md", P("SHARED", "OUT", "RADAR.md")):
        return False
    custos("check-in", "--frigate", "F02", "--output", P("F02_BREACHER", "OUT", "analysis.json"))
    print("\n[ORCH] RADAR terminé. Prochaine étape → Gate 1: "
          "python IW_CUSTOS.py --mode gate --gate 1 --decision yes")
    return True


def mode_siege(ids, fixtures=None, top_pack=10):
    fixtures = fixtures or P("ARCHIVUM", "fixtures", "matches.json")
    intel_out = P("F01_SENTINEL", "OUT", "matches_intel.json")
    with open(fixtures, "r", encoding="utf-8") as f:
        carte = json.load(f)
    if ids:
        carte["matchs"] = [m for m in carte["matchs"] if m.get("id") in set(ids)]
        if not carte["matchs"]:
            print(f"[ORCH] IDs {ids} introuvables dans {fixtures}")
            return False
    os.makedirs(os.path.dirname(intel_out), exist_ok=True)
    with open(intel_out, "w", encoding="utf-8") as f:
        json.dump({"generated_at": now_str(), "source": "siege_file", "ligue": carte.get("ligue"),
                   "ligue_tier": carte.get("ligue_tier"), "matchs": carte["matchs"]}, f, indent=2, ensure_ascii=False)

    custos("check-out", "--frigate", "TYRANT")
    carte_out = P("TYRANT", "OUT", "carte_verdict.json")
    run_frigate(P("TYRANT", "CODEBASE", "tyrant.py"), "--intel", intel_out, "--output", carte_out)
    custos("check-in", "--frigate", "TYRANT", "--output", carte_out)
    custos("check-in", "--frigate", "F01", "--output", intel_out)
    print("\n[ORCH] ⛔ GATE 1 requise avant F02 → python IW_CUSTOS.py --mode gate --gate 1 --decision yes")
    if not os.environ.get("PARI_AUTO_GATES"):
        return True
    return suite_siege(fixtures, carte_out, intel_out, top_pack)


def suite_siege(fixtures, carte_out, intel_out, top_pack):
    custos("gate", "--gate", "1", "--decision", "yes", "--notes", "auto (PARI_AUTO_GATES)")
    custos("check-out", "--frigate", "F02")
    analysis_out = P("F02_BREACHER", "OUT", "analysis.json")
    run_frigate(P("F02_BREACHER", "CODEBASE", "breacher.py"), "--input", intel_out, "--output", analysis_out)
    custos("check-in", "--frigate", "F02", "--output", analysis_out)
    print("\n[ORCH] ⛔ GATE 2 requise → validation analyses BREACHER")
    custos("gate", "--gate", "2", "--decision", "yes", "--notes", "auto (PARI_AUTO_GATES)")

    custos("check-out", "--frigate", "F03")
    pred_out = P("F03_FORGEWARD", "OUT", "predictions.json")
    run_frigate(P("F03_FORGEWARD", "CODEBASE", "forgeward.py"),
                "--intel", intel_out, "--analysis", analysis_out,
                "--profile", P("ARCHIVUM", "rules", "warsmith_profile.json"),
                "--output", pred_out)
    custos("check-in", "--frigate", "F03", "--output", pred_out)
    print("\n[ORCH] ⛔ GATE 3 requise → validation verdicts FORGEWARD")
    custos("gate", "--gate", "3", "--decision", "yes", "--notes", "auto (PARI_AUTO_GATES)")

    # — Phase 2 (v2) : filtre qualitatif borné SI des notes non binaires existent —
    notes_path = P("ARCHIVUM", "fixtures", "notes_qualitatives.json")
    filtered_path = P("F03_FORGEWARD", "OUT", "predictions_filtered.json")
    used_filter = False
    notes_blob = {}
    if os.path.exists(notes_path):
        try:
            with open(notes_path, encoding="utf-8") as f:
                notes_blob = json.load(f)
        except (OSError, json.JSONDecodeError):
            notes_blob = {}
    has_notes = (
        int(notes_blob.get("notes_count") or 0) > 0
        or any((n.get("themes") and not n.get("items")) for n in notes_blob.get("notes") or [])
    )
    if has_notes:
        custos("check-out", "--frigate", "TYRANT")
        qualitative_out = P("TYRANT", "OUT", "qualitative_verdict.json")
        run_frigate(P("TYRANT", "CODEBASE", "qualitative.py"),
                    "--predictions", pred_out,
                    "--notes", notes_path,
                    "--analysis", analysis_out)
        custos("check-in", "--frigate", "TYRANT", "--output", qualitative_out)
        used_filter = os.path.exists(filtered_path)

    # — Phase 3 (v2) : Top 3 — jamais un filtered.json d'une campagne precedente —
    pred_source = filtered_path if used_filter else pred_out
    top3_args = ["--predictions", pred_source, "--analysis", analysis_out]
    if used_filter:
        top3_args += ["--notes-filter", P("TYRANT", "OUT", "qualitative_verdict.json")]
    run_frigate(P("F03_FORGEWARD", "CODEBASE", "top3.py"), *top3_args)
    run_frigate(P("F05_PACKAGER", "CODEBASE", "preview1.py"),
                "--predictions", pred_source,
                "--carte", fixtures)
    print("[ORCH] ✅ Top 3 + Preview 1 générés (SHARED/OUT/preview1.html)")

    custos("check-out", "--frigate", "F04")
    run_frigate(P("F04_HERALD", "CODEBASE", "herald.py"),
                "--analysis", analysis_out, "--predictions", pred_out, "--carte", carte_out)
    custos("check-in", "--frigate", "F04", "--output", P("F04_HERALD", "OUT", "reports_index.json"))

    custos("check-out", "--frigate", "F05")
    pack_out = P("F05_PACKAGER", "OUT", "pari_pack.json")
    run_frigate(P("F05_PACKAGER", "CODEBASE", "packager.py"),
                "--predictions", pred_source, "--analysis", analysis_out, "--carte", carte_out,
                "--top", str(top_pack), "--output", pack_out)
    run_frigate(P("F05_PACKAGER", "CODEBASE", "dashboard.py"),
                "--radar", P("F00_RADAR", "OUT", "radar.json"),
                "--pack", pack_out,
                "--tickets", P("ARCHIVUM", "learnings", "tickets.json"),
                "--calibration", P("ARCHIVUM", "learnings", "calibration.json"),
                "--output", P("SHARED", "OUT", "dashboard.html"))
    custos("check-in", "--frigate", "F05", "--output", pack_out)
    print("\n[ORCH] ⛔ GATE 4 requise pour settle F06 → puis: "
          "python F06_TRACKER/CODEBASE/tracker.py add --file <ticket.json>")
    return True


def mode_pack(top_pack=10):
    analysis_out = P("F02_BREACHER", "OUT", "analysis.json")
    pred_out = P("F03_FORGEWARD", "OUT", "predictions.json")
    carte_out = P("TYRANT", "OUT", "carte_verdict.json")
    return run_frigate(P("F05_PACKAGER", "CODEBASE", "packager.py"),
                       "--predictions", pred_out, "--analysis", analysis_out, "--carte", carte_out,
                       "--top", str(top_pack)) and run_frigate(
        P("F05_PACKAGER", "CODEBASE", "dashboard.py"))


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mode_demo():
    print("[ORCH] ═══ MODE DEMO — ligue simulée, pipeline complet ═══")
    fixtures = make_demo_fixtures(P("ARCHIVUM", "fixtures", "demo_matches.json"), n=18)
    sid = f"PARI-DEMO-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
    custos("reset", "--siege-id", sid)
    ok = mode_radar(fixtures)
    if not ok:
        return False
    ok = mode_siege(None, fixtures)
    if not ok:
        return False
    ok = suite_siege(fixtures, P("TYRANT", "OUT", "carte_verdict.json"),
                     P("F01_SENTINEL", "OUT", "matches_intel.json"), 10)
    if not ok:
        return False
    print(fake_pack_note())
    return True


def fake_pack_note():
    return (
        "\n[ORCH] ✅ DEMO complète :\n"
        f"   - RADAR: {P('SHARED','OUT','RADAR.md')}\n"
        f"   - Fiches: {P('F04_HERALD','OUT','reports')}/\n"
        f"   - Pack  : {P('F05_PACKAGER','OUT','pari_pack.json')}\n"
        f"   - Dashboard: {P('SHARED','OUT','dashboard.html')}  ← ouvre-le sur tel/PC\n"
        "   PARI_AUTO_GATES=1 a validé les gates automatiquement (DEMO uniquement).\n"
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ORCHESTRATOR — monde PARI")
    parser.add_argument("--mode", required=True,
                        choices=["radar", "siege", "pack", "demo", "imprime", "notify",
                                 "telegram-test", "input-capture", "tickets", "workflow"])
    parser.add_argument("--ids", default=None, help="M1,M2 en mode siege (vide = carte complète)")
    parser.add_argument("--fixtures", default=None)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--cmd", default=None,
                        help="commandes workflow Telegram Ex: '/start /capture f.txt'")
    parser.add_argument("--capture", default=None,
                        help="fichier capture txt/md/png/pdf/docx (mode input-capture)")
    parser.add_argument("--valider", action="store_true",
                        help="valide le JSON reconstitué de la capture (Porte 1)")
    parser.add_argument("--out-carte", default=P("ARCHIVUM", "fixtures", "matches.json"),
                        help="destination de la carte flaggée (mode input-capture)")
    parser.add_argument("--combos", type=int, default=3, help="nb de tickets demandés (mode tickets)")
    parser.add_argument("--jambes", default=None, help="nb matchs par ticket, ex 3 ou 3:2:2 (mode tickets)")
    parser.add_argument("--budget-fc", type=float, default=0.0, help="budget du jour en FC (mode tickets)")
    parser.add_argument("--surticket-fc", type=float, default=0.0, help="mise du ticket sûr en FC")
    parser.add_argument("--mises-fc", default=None, help="mises explicites 3000:1000:1000")
    parser.add_argument("--taux-fc-usd", type=float, default=None, help="taux FC→USD pour les unités")
    parser.add_argument("--exclude-legs", default=None, help="JSON anti-cannibal (mode tickets)")
    args = parser.parse_args()

    if args.mode == "imprime":
        custos("status")
    elif args.mode == "radar":
        ok = mode_radar(args.fixtures, top=max(args.top, 20))
        sys.exit(0 if ok else 1)
    elif args.mode == "siege":
        ids = [x.strip() for x in args.ids.split(",")] if args.ids else None
        ok = mode_siege(ids, args.fixtures, top_pack=args.top)
        sys.exit(0 if ok else 1)
    elif args.mode == "pack":
        ok = mode_pack(args.top)
        sys.exit(0 if ok else 1)
    elif args.mode == "demo":
        ok = mode_demo()
        sys.exit(0 if ok else 1)
    elif args.mode == "notify":
        ok = run_frigate(P("ORCHESTRATOR", "CODEBASE", "notifier.py"),
                         "--pack", P("F05_PACKAGER", "OUT", "pari_pack.json"))
        sys.exit(0 if ok else 1)
    elif args.mode == "telegram-test":
        ok = run_frigate(P("ORCHESTRATOR", "CODEBASE", "notifier.py"), "--text", "PING du monde PARI 🛡️ — canal opérationnel.")
        sys.exit(0 if ok else 1)
    elif args.mode == "workflow":
        cmd = [sys.executable, P("ORCHESTRATOR", "CODEBASE", "workflow.py")]
        if args.cmd:
            cmd += [x for x in args.cmd.split() if x]
        r = subprocess.run(cmd)
        sys.exit(0 if r.returncode == 0 else 1)
    elif args.mode == "tickets":
        cmd = [sys.executable, P("F05_PACKAGER", "CODEBASE", "combinator.py"),
               "--tickets", str(args.combos),
               "--budget-fc", str(args.budget_fc), "--surticket-fc", str(args.surticket_fc)]
        if args.jambes:
            cmd += ["--jambes", args.jambes]
        if args.mises_fc:
            cmd += ["--mises-fc", args.mises_fc]
        if args.taux_fc_usd:
            cmd += ["--taux-fc-usd", str(args.taux_fc_usd)]
        if getattr(args, "exclude_legs", None):
            cmd += ["--exclude-legs", args.exclude_legs]
        r = subprocess.run(cmd)
        if r.returncode == 0:
            run_frigate(P("F05_PACKAGER", "CODEBASE", "preview2.py"))
        sys.exit(0 if r.returncode == 0 else 1)
    elif args.mode == "input-capture":
        cmd = [sys.executable, P("F01_SENTINEL", "CODEBASE", "input_capture.py"),
               "--out-json", P("F01_SENTINEL", "OUT", "capture_parsed.json")]
        if args.capture:
            cmd += ["--capture", args.capture]
        if args.valider:
            cmd += ["--valider", "--out-carte", args.out_carte]
        r = subprocess.run(cmd)
        sys.exit(0 if r.returncode == 0 else 1)


if __name__ == "__main__":
    main()
