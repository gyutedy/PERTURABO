"""
ORCHESTRATOR — WORKFLOW TELEGRAM (v2, Phase 6)
===============================================
Le cycle de campagne opérable **depuis Telegram** (PC et téléphone), avec une
commande à chaque étape et les deux previews servies sur GitHub Pages.

  /start           ouvre la campagne du jour (reset propre, garde le budget)
  /capture <file>  capture book (txt, md, png/jpg, pdf, docx) → JSON reconstitue (A_VALIDER)
  /budget 6000     budget du jour en FC (+reads optionnels /tau 2900 ...)
  valider-1        épingle le JSON capture → carte → siège → Top3 → PREVIEW 1
  /corriger-1      (rejoue /capture après correction de la capture OCR)
  /marches O/U2.5,MT2   choisit les marchés visés pour la carte (=livrer infos)
  /combos 3        nombre de tickets (option ^^ : 3:3:2:2 = jambes par ticket)
  /surticket 3000  mise du ticket sûr en FC
  valider-2        tickets + backroll → PREVIEW 2 (ticket final) + message /data
  /roi             tracker F06 : ROI cumulé
  /status          état de la campagne (gates, budgets, previews)
  /stop            ferme la campagne du jour

L'état vit dans SHARED/STATE/campagne.json — la conversation elle-même reste la
source de vérité côté Telegram ; GitHub Actions sont le chauffeur (chaque
commande = un run workflow_dispatch ou une ligne de terminal).

Usage:
  python workflow.py /start
  python workflow.py /capture capture.txt
  python workflow.py /budget 6000 /combos 3 /valider-1
  python workflow.py --mode status
"""

import sys
import json
import os
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
STATE_DIR = os.path.join(WORLD, "SHARED", "STATE")
STATE_PATH = os.path.join(STATE_DIR, "campagne.json")
NOTIFIER = os.path.join(HERE, "notifier.py")

P = lambda *a: os.path.join(WORLD, *a)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"campagne": None, "steps": {}, "budget_fc": 0, "surticket_fc": 0,
            "combos": 3, "jambes": None, "marches": None, "capture": None,
            "capturer_statut": None, "previews": {}}


def save(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False, default=str)


def tell(text):
    """Répond à l'opérateur : Telegram si les clés sont posées, sinon console."""
    print(text)
    subprocess.run([sys.executable, NOTIFIER, "--text", text], capture_output=True)


def run_orch(*args):
    cmd = [sys.executable, os.path.join(HERE, "orchestrator.py")] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WORLD)
    out = (r.stdout or "") + (r.stderr or "")
    sys.stdout.write(out)
    return r.returncode == 0, out


# — Commandes — —

def cmd_start(st, arg):
    st["campagne"] = f"PARI-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    st["steps"] = {"start": _now()}
    st["capture"] = None
    st["capturer_statut"] = None
    st["previews"] = {}
    save(st)
    tell(f"Campagne **{st['campagne']}** ouverte.\n"
         "1. Capture Winner Bet (txt, md, png/jpg, pdf, docx) → `/capture <fichier>`\n"
         "2. `/budget 6000` et `/combos 3`\n"
         "3. `/valider-1` → PREVIEW 1 (donnees brutes) → tu relis → `/valider-2`"
         " apres verif → PREVIEW 2 (ticket final)")


def cmd_capture(st, fichier):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    if not fichier or not os.path.exists(fichier):
        tell(f"Fichier capture introuvable : {fichier} — /capture <txt|md|png|pdf|docx>"); return
    st["capture"] = fichier
    st["steps"]["capture"] = _now()
    ok, _ = run_orch("--mode", "input-capture", "--capture", fichier)
    if not ok:
        tell("⛔ Echec du parsing de la capture — corrige le texte OCR / capture."); return
    jf = load_json(P("F01_SENTINEL", "OUT", "capture_parsed.json"))
    n = jf.get("n_matchs", 0) if jf else 0
    warn = len(jf.get("warnings", [])) if jf else 0
    st["capturer_statut"] = "A_VALIDER"
    save(st)
    fmt = (jf or {}).get("source_format") or "texte"
    tell(f"Capture parsee ({fmt}) : **{n} match(s)**, {warn} warning(s) — "
         "regle Zero Data, Zero Calc : **relis le JSON reconstitue** "
         "(F01_SENTINEL/OUT/capture_parsed.json) → si ok : `/valider-1`")


def cmd_budget(st, text):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    try:
        budget = float(text.split()[0])
    except (ValueError, IndexError):
        tell("Format : `/budget 6000` (FC)."); return
    sur = st.get("surticket_fc") or 0
    if "/" in text:
        sur = float(text.split("/")[1].strip().split()[0])
    st["budget_fc"], st["surticket_fc"] = budget, sur
    st["steps"]["budget"] = _now()
    save(st)
    tell(f"💰 Budget du jour : **{budget:.0f} FC**"
         + (f" — dont **{sur:.0f} FC** sur le ticket sûr" if sur else ""))


def cmd_combos(st, text):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    parts = [x for x in text.replace(":", " ").split() if x.strip()]
    tokens = []
    for p in parts:
        tokens.extend(p.split(":"))
    vals = [int(x) for x in tokens if x.strip().isdigit()]
    if not vals:
        tell("Format : `/combos 3` ou `/combos 3:3:2:2` (3 tickets, 3 matchs puis 2 puis 2)."); return
    st["combos"] = vals[0]
    if len(vals) > 1:
        st["jambes"] = ":".join(str(x) for x in vals[1:vals[0] + 1])
    st["steps"]["combos"] = _now()
    save(st)
    tell(f"🧩 Tickets : **{st['combos']}**"
         + (f" · jambes par ticket : {st['jambes']}" if st.get("jambes") else ""))


LIGUE_CODE = {"premier league": "E0", "la liga": "SP1", "liga santander": "SP1",
              "serie a": "I1", "bundesliga": "D1", "ligue 1": "F1"}


def inject_stats(carte_path):
    """Capteurs football-data.co.uk + ClubElo (sans clé) sur la carte validée.
    Gracieux : si le réseau ou la ligue ne matchent pas, on prévient et le
    siège reste possible avec les stats déjà présentes — Zero Data, Zero Calc sinon."""
    try:
        carte = load_json(carte_path) or {}
        ligue = (carte.get("matchs") or [{}])[0].get("ligue", "").lower()
        code = next((c for k, c in LIGUE_CODE.items() if k in ligue), None)
        tmp_stats = P("ARCHIVUM", "teams", "stats_inject.json")
        if code:
            run_orch_r = subprocess.run(
                [sys.executable, P("F00_RADAR", "CODEBASE", "capteurs.py"), "build-stats",
                 "--league", code, "--season", "2627", "--include-seasons", "2526",
                 "--last", "12", "--out", tmp_stats],
                capture_output=True, text=True, cwd=WORLD)
            run_orch_r = subprocess.run(
                [sys.executable, P("F00_RADAR", "CODEBASE", "capteurs.py"), "inject",
                 "--stats", tmp_stats,
                 "--carte", carte_path],
                capture_output=True, text=True, cwd=WORLD)
            if run_orch_r.returncode == 0:
                return True
        return False
    except Exception as e:
        print(f"[WF] inject_stats gracieux: {e}")
        return False


def cmd_valider1(st, arg):
    if not st.get("capture"):
        tell("⛔ Aucune capture (/capture <fichier> d'abord)."); return
    ok, _ = run_orch("--mode", "input-capture", "--capture", st["capture"],
                     "--valider", "--out-carte", P("ARCHIVUM", "fixtures", "matches.json"))
    if not ok:
        tell("⛔ Validation impossible."); return
    st["capturer_statut"] = "VALIDE"
    st["steps"]["valider1"] = _now()
    carte_path = P("ARCHIVUM", "fixtures", "matches.json")
    if not inject_stats(carte_path):
        tell("⚠️ Stats historiques absentes (ligue non couverte ou réseau) — "
             "Zero Data, Zero Calc : le siège sortira NO BET tant que la carte "
             "n'a pas ses mj/marques/encaisses (capteurs build-stats + inject, ou stats manuelles).")
    ok2, _ = run_orch("--mode", "siege")
    if not ok2:
        tell("⛔ Siège en échec — corrige la carte, puis `/valider-1`."); return
    save(st)
    tell("✅ VALIDATION 1 : JSON VALIDÉ → carte → siège → Top 3 marchés.\n"
         "📊 PREVIEW 1 : SHARED/OUT/preview1.html (données BRUTES : probas, EV, "
         "Top 3 + score commun, notes non binaires).\n"
         "→ relis-la ; si ok : `/combos <n>` `/budget <fc>` puis `/valider-2` "
         "pour le ticket final.\n💬 `/data` pour les rangs en message texte.")


def cmd_valider2(st, arg):
    if not st.get("steps", {}).get("valider1"):
        tell("⛔ Valider la Preview 1 d'abord (`/valider-1` puis relecture)."); return
    cmd = ["--mode", "tickets", "--combos", str(st.get("combos") or 3),
           "--budget-fc", str(st.get("budget_fc") or 0),
           "--surticket-fc", str(st.get("surticket_fc") or 0)]
    if st.get("jambes"):
        cmd += ["--jambes", st["jambes"]]
    ok, _ = run_orch(*cmd)
    if not ok:
        tell("⛔ Echec de la composition des tickets."); return
    st["steps"]["valider2"] = _now()
    st["previews"]["preview2"] = "SHARED/OUT/preview2.html"
    st["previews"]["preview1"] = "SHARED/OUT/preview1.html"
    save(st)
    tmd = read_text(P("SHARED", "OUT", "TICKETS.md"))
    tell("✅ VALIDATION 2 : TICKETS + BACKROLL posés.\n" + (tmd or "") +
         "\n🎯 PREVIEW 2 : SHARED/OUT/preview2.html — le ticket final. "
         "Place les tickets chez Winner Bet, puis log-ge chaque ticket (F06) : "
         "tracker.py add --file ticket.json")


def cmd_data(st, arg):
    t3 = read_text(P("SHARED", "OUT", "TOP3.md"))
    if not t3:
        tell("⛔ Rien encore — /valider-1 pour générer le Top 3."); return
    tell(t3)


def cmd_status(st, arg):
    lines = [f"📋 Campagne : {st.get('campagne') or '— aucune —'}"]
    lines += [f"  • {k}: {v}" for k, v in (st.get("steps") or {}).items()]
    lines.append(f"  • budget: {st.get('budget_fc')} FC · sur-ticket: {st.get('surticket_fc')} FC"
                 f" · combos: {st.get('combos')} · jambes: {st.get('jambes')}")
    tell("\n".join(lines))


def cmd_roi(st, arg):
    ok, out = run_orch("--mode", "imprime")
    tell(out.strip() or "ROI : tracker F06 — python F06_TRACKER/CODEBASE/tracker.py roi")


def cmd_stop(st, arg):
    tell(f"🏁 Campagne {st.get('campagne')} fermée. Ledgers et previews restent en"
         " SHARED/OUT — settles F06 quand les matchs sont joués.")
    st["campagne"] = None
    save(st)


CMDS = {
    "start": (cmd_start, "ouvre la campagne"),
        "capture": (cmd_capture, "capture txt/md/png/pdf/docx"),
    "budget": (cmd_budget, "budget du jour en FC"),
    "combos": (cmd_combos, "nb tickets (+jambes)"),
    "valider-1": (cmd_valider1, "valide preview 1 → siège"),
    "valider1": None,
    "valider-2": (cmd_valider2, "valide preview 2 → tickets"),
    "valider2": None,
    "data": (cmd_data, "rangs Top 3 en message"),
    "status": (cmd_status, "état de la campagne"),
    "roi": (cmd_roi, "ROI tracker F06"),
    "stop": (cmd_stop, "ferme la campagne"),
}


def load_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def main():
    # Reconstitution des commandes : un token est UNE commande s'il commence par
    # "/" ET que son premier mot est une commande connue — sinon il s'attache à
    # la commande précédente (cas des chemins absolus comme /workspace/...).txt).
    connu = {k.replace("-", "") for k, v in CMDS.items() if v and v[0]}
    args = []
    for tok in [a for a in sys.argv[1:] if not a.startswith("--")]:
        bits = tok.lstrip("/").split() if tok else []
        head = bits[0].lower().replace("-", "") if bits else ""
        if tok.startswith("/") and head in connu:
            args.append(tok)
        elif args:
            args[-1] = args[-1] + " " + tok
        else:
            args.append(tok)
    if not args:
        print(__doc__)
        return 0
    st = state()
    for arg in args:
        name = arg.lstrip("/").split()[0].lower()
        handled = False
        for key, entry in CMDS.items():
            if entry is None:
                continue
            if name in (key, key.replace("-", "")):
                parts = arg.split(None, 1)
                rest = parts[1].strip() if len(parts) > 1 else ""
                entry[0](st, rest)
                handled = True
                break
        if not handled:
            tell(f"❓ Commande inconnue : {arg}\nDISPONIBLES : " +
                 ", ".join(f"/{k}" for k, v in CMDS.items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
