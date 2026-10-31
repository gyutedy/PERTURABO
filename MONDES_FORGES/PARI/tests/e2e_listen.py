#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E LISTEN — parseur Telegram + inbox capture (zero reseau)
===========================================================
Couvre le contrat schema_listen.json, le parseur ORCHESTRATOR/LISTEN/parse.py
et le fallback /capture de workflow.py vers F01_SENTINEL/IN/capture_telegram.md.

Aucun appel Telegram, aucun dispatch GitHub, aucun webhook.
"""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LISTEN = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN")
sys.path.insert(0, LISTEN)
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import parse  # noqa: E402
import workflow  # noqa: E402

CHECKS = []
CHAT = "7710898895"


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def upd(text, chat_id=CHAT, update_id=1, message_id=10):
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "chat": {"id": int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id, "type": "private"},
            "text": text,
        },
    }


def main():
    print("=" * 70)
    print("E2E LISTEN — parseur + inbox (zero reseau)")
    print("=" * 70)

    schema_path = os.path.join(WORLD, "CONTRACTS", "schema_listen.json")
    schema = json.load(open(schema_path, encoding="utf-8"))
    check("L0.schema_exists", "cmd" in schema.get("properties", {}) and "chat_id" in schema.get("required", []))

    r = parse.parse_update(upd("/start"), CHAT)
    check("L1.start_dispatch", r.get("ok") and r.get("action") == "dispatch" and r.get("cmd") == "/start", str(r.get("cmd")))

    r = parse.parse_update(upd("/start@Handleer_one_bot"), CHAT)
    check("L1.start_mention", r.get("ok") and r.get("cmd") == "/start", str(r.get("cmd")))

    r = parse.parse_update(upd("/start"), "999")
    check("L2.foreign_ignored", (not r.get("ok")) and r.get("action") == "ignore" and r.get("reason") == "foreign_chat")

    r = parse.parse_update(upd(""), CHAT)
    check("L2.empty_ignored", (not r.get("ok")) and r.get("action") == "ignore")

    r = parse.parse_update(upd("/capture"), CHAT)
    check("L3.capture_empty_refused", (not r.get("ok")) and r.get("reason") == "capture_empty", r.get("reason"))

    md = (
        "| Competition | Horaire | 1 | X | 2 |\n"
        "| :--- | :--- | :---: | :---: | :---: |\n"
        "| **Premier League**<br>Arsenal vs Chelsea | Aujourd'hui 18:00 | 1.85 | 3.60 | 4.20 |"
    )
    r = parse.parse_update(upd("/capture\n" + md), CHAT)
    check(
        "L3.capture_markdown",
        r.get("ok") and r.get("action") == "dispatch" and r.get("cmd") == "/capture" and "Arsenal vs Chelsea" in (r.get("capture_text") or ""),
        (r.get("cmd") or "") + " n=" + str(len(r.get("capture_text") or "")),
    )

    r = parse.parse_update(upd("/capture " + md.split("\n")[0]), CHAT)
    check("L3.capture_same_line", r.get("ok") and r.get("cmd") == "/capture" and "Competition" in (r.get("capture_text") or ""))

    too = "X" * 5000
    r = parse.parse_update(upd("/capture\n" + too), CHAT)
    check("L3.capture_too_long", (not r.get("ok")) and r.get("reason") == "capture_too_long")

    r = parse.parse_update(upd("/budget 6000"), CHAT)
    check("L4.budget", r.get("ok") and r.get("cmd") == "/budget 6000", str(r.get("cmd")))

    r = parse.parse_update(upd("/budget 3000 800"), CHAT)
    check("L4.budget_surticket", r.get("ok") and r.get("cmd") == "/budget 3000 800", str(r.get("cmd")))

    r = parse.parse_update(upd("/bankroll 50000"), CHAT)
    check("L4.bankroll", r.get("ok") and r.get("cmd") == "/bankroll 50000", str(r.get("cmd")))

    r = parse.parse_update(upd("/surticket 800"), CHAT)
    check("L4.surticket", r.get("ok") and r.get("cmd") == "/surticket 800", str(r.get("cmd")))

    r = parse.parse_update(upd("/combos 3:3:2:2"), CHAT)
    check("L4.combos", r.get("ok") and r.get("cmd") == "/combos 3:3:2:2", str(r.get("cmd")))

    r = parse.parse_update(upd("/valider-1"), CHAT)
    check("L4.valider1", r.get("ok") and r.get("cmd") == "/valider-1")

    r = parse.parse_update(upd("/valider1"), CHAT)
    check("L4.valider1_alias", r.get("ok") and r.get("cmd") == "/valider-1", str(r.get("cmd")))

    r = parse.parse_update(upd("/help"), CHAT)
    help_txt = r.get("reply") or ""
    check("L5.help_local", r.get("ok") and r.get("action") == "local"
          and "/start" in help_txt and "/bankroll" in help_txt and "/budget 3000 800" in help_txt)

    r = parse.parse_update(upd("/radar"), CHAT)
    check("L5.unknown_reply", (not r.get("ok")) and r.get("action") == "reply" and r.get("reason") == "unknown")

    r = parse.parse_update(upd("bonjour"), CHAT)
    check("L5.not_a_command", (not r.get("ok")) and r.get("action") == "reply")

    payload = parse.parse_update(upd("/capture\n" + md), CHAT)
    needed = {"cmd", "chat_id"}
    check("L6.contrat_champs", needed.issubset(payload.keys()) and payload.get("capture_text"))

    inbox_dir = tempfile.mkdtemp(prefix="pari-listen-")
    inbox = os.path.join(inbox_dir, "capture_telegram.md")
    with open(inbox, "w", encoding="utf-8") as f:
        f.write(md)
    old_inbox = workflow.INBOX_CAPTURE
    workflow.INBOX_CAPTURE = inbox
    try:
        got = workflow.resolve_capture("")
        check("L7.inbox_fallback", got == inbox, str(got))
        explicit = os.path.join(inbox_dir, "autre.md")
        with open(explicit, "w", encoding="utf-8") as f:
            f.write("x")
        got2 = workflow.resolve_capture(explicit)
        check("L7.explicit_path_gagne", got2 == explicit, str(got2))
        workflow.INBOX_CAPTURE = os.path.join(inbox_dir, "absent.md")
        got3 = workflow.resolve_capture("")
        check("L7.sans_inbox_none", got3 is None, str(got3))
    finally:
        workflow.INBOX_CAPTURE = old_inbox

    yml = os.path.join(WORLD, "..", "..", ".github", "workflows", "pari_listen.yml")
    yml = os.path.normpath(yml)
    raw = open(yml, encoding="utf-8").read() if os.path.exists(yml) else ""
    check("L8.workflow_exists", "name: pari-listen" in raw and "workflow.py" in raw)
    check("L8.concurrency", "group: pari-campagne" in raw and "cancel-in-progress: false" in raw)
    check("L8.inbox_write", "capture_telegram.md" in raw)
    check("L8.pages_non_bloquant", "continue-on-error: true" in raw)
    check("L8.auto_gates", "PARI_AUTO_GATES" in raw)

    wf_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "workflow.py"), encoding="utf-8").read()
    check(
        "L10.capture_passe_path",
        'run_orch("--mode", "input-capture", "--capture", path)' in wf_src
        and 'run_orch("--mode", "input-capture", "--capture", fichier)' not in wf_src,
    )
    check("L10.valider1_auto_gates", 'extra_env={"PARI_AUTO_GATES": "1"}' in wf_src)
    check("L10.valider1_fixtures_capture", '"--fixtures", carte_path' in wf_src)
    check("L10.valider2_refuse_nobet", "VALIDATION 2 refusee" in wf_src)
    check("L10.data_refuse_demo", "TOP3 desynchronise" in wf_src)
    check("L10.budget_exige_surticket", "JOUR SURTICKET" in wf_src and "cmd_bankroll" in wf_src)
    check("L10.bankroll_persiste", "bankroll_fc" in wf_src and "pot global" in wf_src)
    orch_src = open(os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE", "orchestrator.py"), encoding="utf-8").read()
    check("L10.siege_filtre_campagne",
          "used_filter" in orch_src and "filtered_path if used_filter" in orch_src)

    import notifier  # noqa: E402
    old_tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    old_chat = os.environ.get("TELEGRAM_CHAT_ID")
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    try:
        notifier._load_env_file()
        check("L9.env_pari_si_secret_vide", bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("TELEGRAM_CHAT_ID")))
    finally:
        if old_tok is None:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        else:
            os.environ["TELEGRAM_BOT_TOKEN"] = old_tok
        if old_chat is None:
            os.environ.pop("TELEGRAM_CHAT_ID", None)
        else:
            os.environ["TELEGRAM_CHAT_ID"] = old_chat

    tmp_state = tempfile.mkdtemp(prefix="pari-br-")
    old_state = workflow.STATE_PATH
    old_dir = workflow.STATE_DIR
    old_tell = workflow.tell
    workflow.STATE_DIR = tmp_state
    workflow.STATE_PATH = os.path.join(tmp_state, "campagne.json")
    workflow.tell = lambda t: print(t)
    try:
        st = workflow.state()
        workflow.cmd_bankroll(st, "50000")
        st = workflow.state()
        check("L11.bankroll_pose", st.get("bankroll_fc") == 50000, str(st.get("bankroll_fc")))
        st["campagne"] = "PARI-TEST"
        workflow.save(st)
        workflow.cmd_budget(st, "3000")
        st = workflow.state()
        check("L11.budget_sans_sur_refuse", (st.get("budget_fc") or 0) == 0 and (st.get("surticket_fc") or 0) == 0)
        workflow.cmd_budget(st, "3000 800")
        st = workflow.state()
        check("L11.budget_force_sur", st.get("budget_fc") == 3000 and st.get("surticket_fc") == 800,
              f"{st.get('budget_fc')}/{st.get('surticket_fc')}")
        workflow.cmd_budget(st, "3000 / 900")
        st = workflow.state()
        check("L11.budget_slash", st.get("budget_fc") == 3000 and st.get("surticket_fc") == 900)
        workflow.cmd_budget(st, "4000 9000")
        st = workflow.state()
        check("L11.sur_gt_jour_refuse", st.get("surticket_fc") == 900, str(st.get("surticket_fc")))
        workflow.cmd_budget(st, "bankroll 42000")
        st = workflow.state()
        check("L11.budget_bankroll_alias", st.get("bankroll_fc") == 42000
              and st.get("budget_fc") == 3000 and st.get("surticket_fc") == 900,
              str(st.get("bankroll_fc")))
        workflow.cmd_stop(st, "")
        st = workflow.state()
        check("L11.bankroll_survit_stop", st.get("campagne") is None and st.get("bankroll_fc") == 42000)
        workflow.cmd_start(st, "")
        st = workflow.state()
        check("L11.bankroll_survit_start", bool(st.get("campagne")) and st.get("bankroll_fc") == 42000,
              str(st.get("campagne")))
    finally:
        workflow.STATE_PATH = old_state
        workflow.STATE_DIR = old_dir
        workflow.tell = old_tell

    cap_dir = os.path.join(WORLD, "F00_RADAR", "CODEBASE")
    sys.path.insert(0, cap_dir)
    import capteurs  # noqa: E402

    check("L12.laliga_sans_espace", capteurs.ligue_code("Espagne - LaLiga") == "SP1")
    check("L12.la_liga_espace", capteurs.ligue_code("Espagne - La Liga") == "SP1")
    check("L12.laliga2_rejet", capteurs.ligue_code("Espagne - LaLiga 2") is None)
    check("L12.superlig_rejet", capteurs.ligue_code("Turkiye - Super Lig") is None)
    check("L12.serie_a", capteurs.ligue_code("Italie - Serie A") == "I1")
    check("L12.bundesliga", capteurs.ligue_code("Allemagne - Bundesliga") == "D1")
    check("L12.premier", capteurs.ligue_code("Angleterre - Premier League") == "E0")
    check("L12.ligue1", capteurs.ligue_code("France - Ligue 1") == "F1")

    check("L12.alias_ath_madrid", capteurs.team_key("Atletico Madrid") == capteurs.team_key("Ath Madrid"))
    check("L12.alias_gladbach", capteurs.team_key("Borussia Monchengladbach") == capteurs.team_key("M'Gladbach"))
    check("L12.alias_forest", capteurs.team_key("Nottingham Forest") == capteurs.team_key("Nott'm Forest"))
    check("L12.alias_leverkusen", capteurs.team_key("Bayer Leverkusen") == capteurs.team_key("Leverkusen"))
    check("L12.alias_monza", capteurs.team_key("AC Monza") == capteurs.team_key("Monza"))
    check("L12.alias_bournemouth", capteurs.team_key("AFC Bournemouth") == capteurs.team_key("Bournemouth"))

    stub = {
        "mj": 12, "marques": 18, "encaisses": 10,
        "marques_mt1": 8, "encaisses_mt1": 4, "marques_mt2": 10, "encaisses_mt2": 6,
    }
    stats_sp1 = {"Ath Madrid": {"dom": stub, "ext": stub}, "Levante": {"dom": stub, "ext": stub}}
    stats_e0 = {"Bournemouth": {"dom": stub, "ext": stub}, "Nott'm Forest": {"dom": stub, "ext": stub}}
    k, v = capteurs.fuzzy_stats_lookup(stats_sp1, "Atletico Madrid")
    check("L12.fuzzy_madrid", k == "Ath Madrid" and v is not None, str(k))
    k, v = capteurs.fuzzy_stats_lookup(stats_e0, "Nottingham Forest")
    check("L12.fuzzy_forest", k == "Nott'm Forest" and v is not None, str(k))
    k, v = capteurs.fuzzy_stats_lookup(stats_e0, "Coventry City")
    check("L12.fuzzy_hors_csv", k is None, str(k))

    inj_dir = tempfile.mkdtemp(prefix="pari-inj-")
    carte_path = os.path.join(inj_dir, "carte.json")
    carte = {
        "ligue": "Capture",
        "matchs": [
            {"id": "M1", "dom": "Levante UD", "ext": "Atletico Madrid", "ligue": "Espagne - LaLiga", "stats": {}},
            {"id": "M2", "dom": "AFC Bournemouth", "ext": "Leeds United", "ligue": "Angleterre - Premier League", "stats": {}},
            {"id": "M3", "dom": "Coventry City", "ext": "Sunderland AFC", "ligue": "Angleterre - Premier League", "stats": {}},
        ],
        "warnings": [],
    }
    json.dump(carte, open(carte_path, "w", encoding="utf-8"))
    sp1_path = os.path.join(inj_dir, "stats_inject_SP1.json")
    e0_path = os.path.join(inj_dir, "stats_inject_E0.json")
    json.dump({"league_code": "SP1", "teams": {
        "Levante": {"dom": stub, "ext": stub},
        "Ath Madrid": {"dom": stub, "ext": stub},
    }}, open(sp1_path, "w", encoding="utf-8"))
    json.dump({"league_code": "E0", "teams": {
        "Bournemouth": {"dom": stub, "ext": stub},
        "Leeds": {"dom": stub, "ext": stub},
        "Sunderland": {"dom": stub, "ext": stub},
    }}, open(e0_path, "w", encoding="utf-8"))

    class _Args:
        def __init__(self, stats, carte, elo=None):
            self.stats = stats
            self.carte = carte
            self.elo = elo

    capteurs.cmd_inject(_Args(sp1_path, carte_path))
    capteurs.cmd_inject(_Args(e0_path, carte_path))
    after = json.load(open(carte_path, encoding="utf-8"))
    m1 = next(m for m in after["matchs"] if m["id"] == "M1")
    m2 = next(m for m in after["matchs"] if m["id"] == "M2")
    m3 = next(m for m in after["matchs"] if m["id"] == "M3")
    check("L12.merge_sp1", bool((m1.get("stats") or {}).get("dom") and (m1.get("stats") or {}).get("ext")))
    check("L12.merge_e0_pas_ecrase", bool((m2.get("stats") or {}).get("dom") and (m2.get("stats") or {}).get("ext"))
          and bool((m1.get("stats") or {}).get("dom")))
    check("L12.skip_coventry", not (m3.get("stats") or {}).get("dom"), str(m3.get("stats")))

    check("L12.valider1_compte_go", "n_go == 0" in wf_src and "n_skip" in wf_src and "n_faible" in wf_src)
    check("L12.inject_merge_fichier", "stats_inject_" in wf_src and "n_filled" in wf_src)
    check("L12.ligue_code_capteurs", "ligue_code" in wf_src)

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"LISTEN {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
