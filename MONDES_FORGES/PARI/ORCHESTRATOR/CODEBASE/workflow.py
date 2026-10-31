"""
ORCHESTRATOR — WORKFLOW TELEGRAM (v2, Phase 6)
===============================================
Le cycle de campagne opérable **depuis Telegram** (PC et téléphone), avec une
commande à chaque étape et les deux previews servies sur GitHub Pages.

  /start           ouvre la campagne du jour (reset propre, garde bankroll + budget)
  /capture [file]  capture book (txt, md, png/jpg, pdf, docx) → JSON reconstitue (A_VALIDER)
                   sans chemin : lit F01_SENTINEL/IN/capture_telegram.md (inbox Telegram)
  /bankroll 50000  pot global FC (persiste /start /stop). Sans arg : affiche le pot.
  /budget 3000 800 budget du jour + mise FORCEE du ticket sur (reste divise)
  /surticket 800   force (ou corrige) la mise du ticket sur, sans retaper le jour
  valider-1        épingle le JSON capture → carte → siège → Top3 → PREVIEW 1
  /corriger-1      (rejoue /capture après correction de la capture OCR)
  /marches O/U2.5,MT2   choisit les marchés visés pour la carte (=livrer infos)
  /combos 3        nombre de tickets (option ^^ : 3:3:2:2 = jambes par ticket)
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
  python workflow.py /bankroll 50000 /budget 3000 800 /combos 3 /valider-1
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
    return {"campagne": None, "steps": {}, "bankroll_fc": 0, "budget_fc": 0,
            "surticket_fc": 0, "combos": 3, "jambes": None, "marches": None,
            "capture": None, "capturer_statut": None, "previews": {}}


def save(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False, default=str)


def tell(text):
    """Répond à l'opérateur : Telegram si les clés sont posées, sinon console."""
    print(text)
    subprocess.run([sys.executable, NOTIFIER, "--text", text], capture_output=True)


def run_orch(*args, extra_env=None):
    cmd = [sys.executable, os.path.join(HERE, "orchestrator.py")] + list(args)
    env = {**os.environ, **(extra_env or {})}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WORLD, env=env)
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
    br = st.get("bankroll_fc") or 0
    tell(f"Campagne **{st['campagne']}** ouverte.\n"
         + (f"Bankroll : **{br:.0f} FC** (persiste).\n" if br else
            "Bankroll absente — tape `/budget bankroll 50000` une fois (pot global, persiste).\n")
         + "1. Capture Winner Bet (txt, md, png/jpg, pdf, docx) → `/capture <fichier>`\n"
         "2. `/budget 3000 800` (plafond jour + mise FORCEE ticket sur) et `/combos 3`\n"
         "3. `/valider-1` → PREVIEW 1 (donnees brutes) → tu relis → `/valider-2`"
         " apres verif → PREVIEW 2 (ticket final)")


INBOX_CAPTURE = P("F01_SENTINEL", "IN", "capture_telegram.md")


def resolve_capture(fichier):
    """Chemin local si fourni et present, sinon inbox Telegram (texte colle)."""
    path = (fichier or "").strip()
    if path and os.path.exists(path):
        return path
    if os.path.exists(INBOX_CAPTURE):
        return INBOX_CAPTURE
    return None


def cmd_capture(st, fichier):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    path = resolve_capture(fichier)
    if not path:
        tell("Fichier capture introuvable — /capture <txt|md|png|pdf|docx> "
             "ou colle le tableau markdown dans le meme message Telegram "
             "(inbox F01_SENTINEL/IN/capture_telegram.md).")
        return
    st["capture"] = path
    st["steps"]["capture"] = _now()
    ok, _ = run_orch("--mode", "input-capture", "--capture", path)
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


def _parse_fc(text):
    """Extrait des montants FC : '3000 800', '3000 / 800', '3000/800'."""
    cleaned = (text or "").replace("/", " ").replace(",", ".")
    vals = []
    for tok in cleaned.split():
        try:
            vals.append(float(tok))
        except ValueError:
            continue
    return vals


def cmd_bankroll(st, text):
    """Pot global FC. Persiste /start et /stop. Sans arg : affiche."""
    vals = _parse_fc(text)
    if not vals:
        br = st.get("bankroll_fc") or 0
        if br <= 0:
            tell("Bankroll absente. Format : `/bankroll 50000` (pot global FC, persiste).")
            return
        tell(f"Bankroll : **{br:.0f} FC** (pot global, hors budget jour).")
        return
    br = vals[0]
    if br <= 0:
        tell("⛔ Bankroll doit etre > 0 FC."); return
    st["bankroll_fc"] = br
    st["steps"]["bankroll"] = _now()
    save(st)
    tell(f"Bankroll posee : **{br:.0f} FC** (pot global). "
         "Ne change pas a `/start` / `/stop`. "
         f"Telegram : `/budget bankroll {br:.0f}` (le Worker live ne connait pas encore /bankroll). "
         "Ensuite `/budget 3000 800` = plafond jour + mise FORCEE du ticket sur.")


def cmd_budget(st, text):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    raw = (text or "").strip()
    head = raw.split()[0].lower() if raw.split() else ""
    if head in ("bankroll", "pot", "br"):
        rest = raw.split(None, 1)[1] if len(raw.split()) > 1 else ""
        return cmd_bankroll(st, rest)
    vals = _parse_fc(text)
    if len(vals) < 2:
        tell("Format : `/budget 3000 800` — 3000 FC plafond du jour, "
             "**800 FC FORCES sur le ticket sur**. Le reste (2200) est divise "
             "entre les autres tickets. Alias : `/budget 3000 / 800`.\n"
             "Bankroll (pot global) : `/budget bankroll 50000` "
             "(pas `/bankroll` — le Worker live la refuse)."); return
    budget, sur = vals[0], vals[1]
    if budget <= 0 or sur <= 0:
        tell("⛔ Budget jour et ticket sur doivent etre > 0 FC."); return
    if sur > budget:
        tell(f"⛔ Ticket sur ({sur:.0f} FC) > budget jour ({budget:.0f} FC)."); return
    br = st.get("bankroll_fc") or 0
    if br and budget > br:
        tell(f"⛔ Budget jour ({budget:.0f} FC) > bankroll ({br:.0f} FC)."); return
    st["budget_fc"], st["surticket_fc"] = budget, sur
    st["steps"]["budget"] = _now()
    save(st)
    reste = budget - sur
    tell(f"Budget jour : **{budget:.0f} FC** — ticket sur FORCE a **{sur:.0f} FC**. "
         f"Reste **{reste:.0f} FC** a diviser. "
         + (f"Bankroll {br:.0f} FC." if br else "Bankroll non posee (`/bankroll`)."))


def cmd_surticket(st, text):
    if not st.get("campagne"):
        tell("⛔ Pas de campagne — `/start` d'abord."); return
    vals = _parse_fc(text)
    if not vals:
        tell("Format : `/surticket 800` (mise FORCEE du ticket sur, FC)."); return
    sur = vals[0]
    budget = st.get("budget_fc") or 0
    if sur <= 0:
        tell("⛔ Ticket sur doit etre > 0 FC."); return
    if budget and sur > budget:
        tell(f"⛔ Ticket sur ({sur:.0f} FC) > budget jour ({budget:.0f} FC). "
             "Retape `/budget JOUR SURTICKET`."); return
    st["surticket_fc"] = sur
    st["steps"]["surticket"] = _now()
    save(st)
    tell(f"Ticket sur FORCE a **{sur:.0f} FC**"
         + (f" (budget jour {budget:.0f} FC, reste {budget - sur:.0f} FC)." if budget else
            ". Pose aussi `/budget JOUR SURTICKET`."))


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


def _capteurs():
    cap_dir = P("F00_RADAR", "CODEBASE")
    if cap_dir not in sys.path:
        sys.path.insert(0, cap_dir)
    import capteurs as _cap
    return _cap


def inject_stats(carte_path):
    """Capteurs football-data.co.uk + ClubElo (sans clé) sur la carte validée.
    Merge multi-ligues (un JSON par code, jamais ecrase). Alias LaLiga/clubs.
    Club hors CSV = skip CE match, pas NO BET global. True si >=1 match avec stats."""
    if os.environ.get("PARI_SKIP_INJECT") == "1":
        return False
    try:
        cap = _capteurs()
        carte = load_json(carte_path) or {}
        codes = []
        skipped_ligues = []
        for m in carte.get("matchs") or []:
            lg = m.get("ligue") or carte.get("ligue") or ""
            code = cap.ligue_code(lg)
            if code:
                if code not in codes:
                    codes.append(code)
            elif lg and lg not in skipped_ligues:
                skipped_ligues.append(lg)
        if not codes:
            root = carte.get("ligue") or ""
            code = cap.ligue_code(root)
            if code:
                codes.append(code)
        any_ok = False
        teams_dir = P("ARCHIVUM", "teams")
        os.makedirs(teams_dir, exist_ok=True)
        for code in codes:
            tmp_stats = os.path.join(teams_dir, f"stats_inject_{code}.json")
            r1 = subprocess.run(
                [sys.executable, P("F00_RADAR", "CODEBASE", "capteurs.py"), "build-stats",
                 "--league", code, "--season", "2627", "--include-seasons", "2526",
                 "--last", "12", "--out", tmp_stats],
                capture_output=True, text=True, cwd=WORLD)
            sys.stdout.write(r1.stdout or "")
            sys.stdout.write(r1.stderr or "")
            if r1.returncode != 0:
                continue
            r2 = subprocess.run(
                [sys.executable, P("F00_RADAR", "CODEBASE", "capteurs.py"), "inject",
                 "--stats", tmp_stats, "--carte", carte_path],
                capture_output=True, text=True, cwd=WORLD)
            sys.stdout.write(r2.stdout or "")
            sys.stdout.write(r2.stderr or "")
            if r2.returncode == 0:
                any_ok = True
        after = load_json(carte_path) or {}
        n_filled = sum(
            1 for m in (after.get("matchs") or [])
            if (m.get("stats") or {}).get("dom") and (m.get("stats") or {}).get("ext")
        )
        if skipped_ligues:
            print(f"[WF] ligues hors whitelist skip: {skipped_ligues}")
        return any_ok and n_filled > 0
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
    stats_ok = inject_stats(carte_path)
    if not stats_ok:
        tell("⚠️ Stats historiques absentes (ligue hors whitelist E0/SP1/I1/D1/F1 ou réseau) — "
             "Zero Data, Zero Calc : le siège sort NO BET. Pas de ticket.")
    ok2, _ = run_orch("--mode", "siege", "--fixtures", carte_path,
                      extra_env={"PARI_AUTO_GATES": "1"})
    if not ok2:
        tell("⛔ Siège en échec — corrige la carte, puis `/valider-1`."); return
    st["previews"]["preview1"] = "SHARED/OUT/preview1.html"
    save(st)
    t3 = load_json(P("F03_FORGEWARD", "OUT", "top3.json")) or {}
    rows = t3.get("matchs") or []
    n_go = sum(1 for r in rows if r.get("top3") and not r.get("no_bet_recommande") and r.get("bucket") != "FAIBLE")
    n_skip = sum(1 for r in rows if not r.get("top3"))
    n_faible = sum(1 for r in rows if r.get("top3") and (r.get("no_bet_recommande") or r.get("bucket") == "FAIBLE"))
    names = ", ".join((r.get("match") or "?") for r in rows[:8]) or "aucun"
    counts = f"{len(rows)} match(s) : {n_go} GO / {n_faible} FAIBLE-qual / {n_skip} skip-stats"
    if n_go == 0:
        if not stats_ok:
            why = "stats absentes (ligue hors whitelist, alias club, ou reseau)"
        elif n_skip == len(rows):
            why = "data insuffisante (clubs hors CSV ligue / mj < 6)"
        else:
            why = "tous FAIBLE ou NO BET qualitatif"
        tell(f"VALIDATION 1 : JSON OK, siege **NO BET** ({why}).\n"
             f"{counts} — {names}\n"
             "PREVIEW 1 ecrasee (plus de demo). `/data` pour la liste.\n"
             "Ne pas `/valider-2` — aucun ticket a composer.")
        return
    tell("VALIDATION 1 : JSON VALIDE → carte → siege → Top 3.\n"
         f"{counts} — {names}\n"
         "PREVIEW 1 : SHARED/OUT/preview1.html\n"
         "→ relis ; si ok : `/combos <n>` `/budget JOUR SURTICKET` puis `/valider-2`.\n"
         "`/data` pour les rangs.")


def cmd_valider2(st, arg):
    if not st.get("steps", {}).get("valider1"):
        tell("⛔ Valider la Preview 1 d'abord (`/valider-1` puis relecture)."); return
    t3 = load_json(P("F03_FORGEWARD", "OUT", "top3.json")) or {}
    rows = t3.get("matchs") or []
    n_go = sum(1 for r in rows if r.get("top3") and not r.get("no_bet_recommande") and r.get("bucket") != "FAIBLE")
    if n_go == 0:
        tell("⛔ VALIDATION 2 refusee : aucun match eligible (NO BET / Zero Data). "
             "Pas de ticket. Recapture une ligue couverte (E0/SP1/I1/D1/F1) ou injecte les stats.")
        return
    budget = st.get("budget_fc") or 0
    sur = st.get("surticket_fc") or 0
    if budget <= 0 or sur <= 0:
        tell("⛔ VALIDATION 2 refusee : `/budget JOUR SURTICKET` obligatoire "
             "(ex. `/budget 3000 800` = 3000 FC aujourd hui, 800 FORCES sur le ticket sur).")
        return
    cmd = ["--mode", "tickets", "--combos", str(st.get("combos") or 3),
           "--budget-fc", str(budget),
           "--surticket-fc", str(sur)]
    if st.get("jambes"):
        cmd += ["--jambes", st["jambes"]]
    ok, _ = run_orch(*cmd)
    if not ok:
        tell("⛔ Echec de la composition des tickets."); return
    tj = load_json(P("F05_PACKAGER", "OUT", "tickets.json")) or {}
    n_tix = len(tj.get("tickets") or [])
    if n_tix == 0:
        tell("⛔ Aucun ticket compose (buckets FAIBLE / NO BET). Budget non engage.")
        return
    st["steps"]["valider2"] = _now()
    st["previews"]["preview2"] = "SHARED/OUT/preview2.html"
    st["previews"]["preview1"] = "SHARED/OUT/preview1.html"
    save(st)
    tmd = read_text(P("SHARED", "OUT", "TICKETS.md"))
    tell("VALIDATION 2 : TICKETS + BACKROLL poses.\n" + (tmd or "") +
         "\nPREVIEW 2 : SHARED/OUT/preview2.html — ticket final. "
         "Place chez Winner Bet, puis F06 tracker.py add --file ticket.json")


def cmd_data(st, arg):
    t3 = read_text(P("SHARED", "OUT", "TOP3.md"))
    if not t3:
        tell("⛔ Rien encore — /valider-1 pour générer le Top 3."); return
    carte = load_json(P("ARCHIVUM", "fixtures", "matches.json")) or {}
    names = [m.get("dom") or "" for m in carte.get("matchs") or []]
    demo = ("Cyclops vs Trench", "Lions vs Garrison", "Perturabo SC vs Rovers")
    if any(d in t3 for d in demo) and names and not any(n and n in t3 for n in names):
        tell("⛔ TOP3 desynchronise (demo). Relance `/valider-1`.")
        return
    tell(t3)


def cmd_status(st, arg):
    lines = [f"📋 Campagne : {st.get('campagne') or '— aucune —'}"]
    lines += [f"  • {k}: {v}" for k, v in (st.get("steps") or {}).items()]
    lines.append(f"  • bankroll: {st.get('bankroll_fc') or 0} FC (pot global)")
    lines.append(f"  • budget jour: {st.get('budget_fc')} FC · ticket sur FORCE: {st.get('surticket_fc')} FC"
                 f" · combos: {st.get('combos')} · jambes: {st.get('jambes')}")
    tell("\n".join(lines))


def cmd_roi(st, arg):
    ok, out = run_orch("--mode", "imprime")
    tell(out.strip() or "ROI : tracker F06 — python F06_TRACKER/CODEBASE/tracker.py roi")


def cmd_stop(st, arg):
    br = st.get("bankroll_fc") or 0
    tell(f"Campagne {st.get('campagne')} fermee. Bankroll **{br:.0f} FC** persiste. "
         "Ledgers et previews restent en SHARED/OUT — settles F06 quand les matchs sont joues.")
    st["campagne"] = None
    save(st)


CMDS = {
    "start": (cmd_start, "ouvre la campagne"),
    "capture": (cmd_capture, "capture txt/md/png/pdf/docx"),
    "bankroll": (cmd_bankroll, "pot global FC (persiste)"),
    "budget": (cmd_budget, "plafond jour + mise FORCEE ticket sur"),
    "surticket": (cmd_surticket, "force la mise du ticket sur"),
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
