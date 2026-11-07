#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S11 — /marches + tickets 1..n+10 + anti meme-navire. Zero reseau."""

import json
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F05_PACKAGER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "LISTEN"))
sys.path.insert(0, os.path.join(WORLD, "ORCHESTRATOR", "CODEBASE"))

import combinator  # noqa: E402
import marches  # noqa: E402
import parse  # noqa: E402
import workflow  # noqa: E402

CHECKS = []
CHAT = "7710898895"


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def ev(mid, match, marche, selection, evv, cote=1.8, score=8.0, bucket="HAUTE"):
    return {
        "id": mid, "match": match, "score_commun": score, "rang_global": int(mid[1:] or 1),
        "bucket": bucket, "no_bet_recommande": False,
        "top3": [{
            "marche": marche, "selection": selection, "selection_label": selection,
            "cote": cote, "p_modele": 0.62, "ev": evv,
        }],
    }


def ev_multi(mid, match, tops, score=8.0):
    return {
        "id": mid, "match": match, "score_commun": score, "rang_global": int(mid[1:] or 1),
        "bucket": "HAUTE", "no_bet_recommande": False,
        "top3": tops,
    }


def test_parse_aliases():
    c, mono, unk = marches.parse_marches_arg("O/U2.5,MT2")
    check("m.alias_ou", c == ["OU_2.5", "MT_PROLIFIQUE"], str(c))
    check("m.alias_pas_mono", mono is False)
    c2, mono2, _ = marches.parse_marches_arg("1X2 mono")
    check("m.mono", mono2 is True and c2 == ["1X2"], str((c2, mono2)))
    c3, _, unk3 = marches.parse_marches_arg("xyzzy")
    check("m.inconnu", unk3 == ["xyzzy"] or c3 == ["XYZZY"], str((c3, unk3)))


def test_parse_telegram():
    def upd(text):
        return {"update_id": 1, "message": {
            "message_id": 1, "chat": {"id": int(CHAT), "type": "private"}, "text": text}}

    r = parse.parse_update(upd("/marches O/U2.5,MT2"), CHAT)
    check("m.parse_ascii", r.get("ok") and r.get("cmd") == "/marches O/U2.5,MT2", str(r.get("cmd")))
    r2 = parse.parse_update(upd("/marchés O/U2.5,MT2"), CHAT)
    check("m.parse_accent", r2.get("ok") and r2.get("cmd") == "/marches O/U2.5,MT2", str(r2.get("cmd")))
    r3 = parse.parse_update(upd("/marches 1X2 mono"), CHAT)
    check("m.parse_mono", r3.get("ok") and "mono" in (r3.get("cmd") or ""), str(r3.get("cmd")))
    help_txt = parse.parse_update(upd("/help"), CHAT).get("reply") or ""
    check("m.help", "/marches" in help_txt, help_txt[:80])


def test_zero_match_zero_ticket():
    events = [ev("M1", "A vs B", "1X2", "1", 0.20)]
    res, wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[2],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        markets=["OU_2.5"], n_mesures=0)
    check("m.zero_tickets", res["tickets"] == [], str(res["tickets"]))
    check("m.zero_msg", any("0 match" in w or "0 ticket" in w for w in wrn), str(wrn))
    check("m.zero_budget", res["budget"]["alloue_fc"] == 0)


def test_meme_navire():
    e = ev_multi("M1", "A vs B", [
        {"marche": "OU_2.5", "selection": "o2.5", "selection_label": "O2.5",
         "cote": 1.9, "p_modele": 0.60, "ev": 0.14},
        {"marche": "BTTS", "selection": "btts", "selection_label": "BTTS",
         "cote": 1.8, "p_modele": 0.58, "ev": 0.044},
    ])
    e2 = ev("M2", "C vs D", "OU_2.5", "o2.5", 0.12)
    res, _ = combinator.allocate(
        [e, e2], tickets=1, jambes_by_ticket=[2],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        markets=["OU_2.5", "BTTS"], n_mesures=0)
    check("m.navire_un_ticket", len(res["tickets"]) == 1, str(len(res["tickets"])))
    ids = [j["match_id"] for j in res["tickets"][0]["jambes"]]
    check("m.navire_distinct", len(ids) == len(set(ids)), str(ids))
    check("m.navire_pas_double_m1", ids.count("M1") == 1, str(ids))


def test_mono_marche():
    events = [
        ev("M1", "A vs B", "OU_2.5", "o2.5", 0.12),
        ev("M2", "C vs D", "1X2", "1", 0.20),
        ev("M3", "E vs F", "OU_2.5", "u2.5", 0.10),
    ]
    res, _ = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[3],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        markets=["OU_2.5", "1X2"], mono=True, n_mesures=0)
    t = res["tickets"][0]
    ms = {marches.canon_marche(j["marche"]) for j in t["jambes"]}
    check("m.mono_un_marche", len(ms) == 1, str(ms))
    check("m.mono_ou", ms == {"OU_2.5"} or ms == {"1X2"}, str(ms))


def test_dix_jambes():
    events = [ev(f"M{i}", f"T{i} vs U{i}", "OU_2.5", "o2.5", 0.10, score=9.0 - i * 0.01)
              for i in range(1, 12)]
    res, wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[10],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        markets=["OU_2.5"], jambes_max=4, n_mesures=0)
    check("m.dix_un_ticket", len(res["tickets"]) == 1, str(len(res["tickets"])))
    t = res["tickets"][0]
    check("m.dix_jambes", t["nb_jambes"] == 10, str(t["nb_jambes"]))
    ids = [j["match_id"] for j in t["jambes"]]
    check("m.dix_distincts", len(set(ids)) == 10, str(ids))
    check("m.dix_pas_diviser", not any("division" in w.lower() and "deux classes" in w.lower() for w in wrn), str(wrn))


def test_floor_refuse():
    events = [ev("M1", "A vs B", "OU_2.5", "o2.5", 0.20)]
    res, wrn = combinator.allocate(
        events, tickets=1, jambes_by_ticket=[1],
        surticket_fc=800, budget_fc=3000, mises_free=None,
        markets=["OU_2.5"], ev_floor=0.01, n_mesures=0)
    check("m.floor_zero_ticket", res["tickets"] == [], str(res["tickets"]))
    check("m.floor_msg", any("inviolable" in w or "floor" in w.lower() for w in wrn), str(wrn))
    check("m.refuse_fn", marches.refuse_floor(0.02) is True)
    check("m.refuse_ok", marches.refuse_floor(0.03) is False)


def test_combo_floor_pas_remplissage():
    events = [
        ev("M1", "A vs B", "OU_2.5", "o2.5", 0.03, cote=1.5),
        ev("M2", "C vs D", "OU_2.5", "o2.5", 0.01, cote=1.5),
    ]
    picked = combinator._pick_jambes(events, 2, ev_floor=0.0, combo_floor=0.05)
    check("m.combo_pas_remplir", len(picked) == 1, str([j.get("match_id") for j in picked]))
    cev = marches.combo_ev([{"ev": 0.03}, {"ev": 0.01}])
    check("m.combo_sous_plancher", cev is not None and cev < 0.05, str(cev))


def test_couverture_et_log():
    top3 = {"matchs": [
        ev("M1", "A vs B", "OU_2.5", "o2.5", 0.12),
        ev("M2", "C vs D", "OU_2.5", "u2.5", 0.04),
        ev("M3", "E vs F", "1X2", "1", 0.01),
    ]}
    rows = marches.coverage_rows(top3)
    ou = [r for r in rows if r["marche"] == "OU_2.5"]
    check("m.cov_ou_n", ou and ou[0]["n"] == 2, str(rows))
    check("m.cov_1x2_sous_seuil", not any(r["marche"] == "1X2" for r in rows), str(rows))
    n = marches.coverage_n(top3, ["OU_2.5"])
    check("m.cov_n", n == 2, str(n))
    n0 = marches.coverage_n(top3, ["MT_PROLIFIQUE"])
    check("m.cov_zero", n0 == 0)
    txt = marches.format_coverage(top3, markets=["MT_PROLIFIQUE"])
    check("m.cov_txt_zero", "0 match" in txt or "aucun" in txt.lower(), txt)

    fd = tempfile.mkdtemp(prefix="pari-s11-")
    path = os.path.join(fd, "market_election_log.json")
    marches.append_election(["OU_2.5"], campagne="PARI-TEST", path=path)
    marches.append_election(["OU_2.5"], campagne="PARI-TEST", path=path)
    marches.append_election(["1X2"], campagne="PARI-TEST", path=path)
    conc = marches.concentration(path=path)
    check("m.conc_alerte", conc["alerte"] is True, str(conc))
    check("m.conc_ou", conc["max_marche"] == "OU_2.5", str(conc.get("max_marche")))
    blob = json.load(open(path, encoding="utf-8"))
    check("m.log_append", len(blob.get("elections") or []) == 3)


def test_workflow_cmd():
    fd = tempfile.mkdtemp(prefix="pari-s11-wf-")
    old_state = workflow.STATE_PATH
    old_dir = workflow.STATE_DIR
    old_tell = workflow.tell
    old_load = workflow.load_json
    old_log = marches.LOG_PATH
    told = []
    workflow.STATE_DIR = fd
    workflow.STATE_PATH = os.path.join(fd, "campagne.json")
    workflow.tell = lambda t: told.append(t)
    marches.LOG_PATH = os.path.join(fd, "election.json")
    top3 = {"matchs": [
        ev("M1", "A vs B", "OU_2.5", "o2.5", 0.12),
        ev("M2", "C vs D", "MT_PROLIFIQUE", "mt2", 0.08),
    ]}
    workflow.load_json = lambda p: top3
    st = {"campagne": "PARI-TEST", "steps": {"valider1": "x"}}
    try:
        told.clear()
        workflow.cmd_marches(st, "O/U2.5,MT2")
        check("m.wf_elus", st.get("marches") == ["OU_2.5", "MT_PROLIFIQUE"], str(st.get("marches")))
        check("m.wf_msg", told and "Marches elus" in told[-1], (told[-1] if told else "")[:80])
        told.clear()
        workflow.cmd_marches(st, "BTTS")
        check("m.wf_zero", "0 match" in (told[-1] if told else ""), (told[-1] if told else "")[:80])
    finally:
        workflow.STATE_PATH = old_state
        workflow.STATE_DIR = old_dir
        workflow.tell = old_tell
        workflow.load_json = old_load
        marches.LOG_PATH = old_log


def test_hint_du_jour():
    top3 = {"matchs": [
        ev("M1", "A vs B", "1X2", "1", 0.20),
        ev("M2", "C vs D", "OU_2.5", "o2.5", 0.12),
    ]}
    h = marches.hint_marches(top3)
    check("m.hint_1x2_ou", h == "/marches 1X2,O/U2.5" or h == "/marches O/U2.5,1X2", h)
    empty = marches.hint_marches({"matchs": [ev("M1", "A vs B", "1X2", "1", 0.01)]})
    check("m.hint_vide", empty == "", empty)
    tank_x = {
        "id": "M1", "match": "PSG vs Troyes", "score_commun": 8.0, "rang_global": 1,
        "bucket": "HAUTE", "no_bet_recommande": False,
        "top3": [{
            "marche": "1X2", "selection": "X", "selection_label": "X",
            "cote": 7.7, "p_modele": 0.21, "ev": 1.75, "verdict": "VALUE",
            "scorer_eligible": True, "p_fav": 0.81, "vestiaire_ok": False,
        }],
    }
    gala_1 = {
        "id": "M8", "match": "Gala vs Amed", "score_commun": 8.0, "rang_global": 2,
        "bucket": "HAUTE", "no_bet_recommande": False,
        "top3": [{
            "marche": "1X2", "selection": "1", "selection_label": "1",
            "cote": 1.37, "p_modele": 0.81, "ev": 0.11, "verdict": "VALUE",
            "scorer_eligible": True, "p_fav": 0.81, "vestiaire_ok": False,
        }],
    }
    mt_plate = {
        "id": "M3", "match": "A vs B", "score_commun": 8.0, "rang_global": 3,
        "bucket": "HAUTE", "no_bet_recommande": False,
        "top3": [{
            "marche": "MT_PROLIFIQUE", "selection": "mt2", "selection_label": "MT2",
            "cote": 2.10, "p_modele": 0.55, "ev": 0.15, "verdict": "VALUE",
            "scorer_eligible": True, "pieges": ["cote_plate"],
        }],
    }
    blob = {"matchs": [tank_x, gala_1, mt_plate]}
    rows = marches.coverage_rows(blob)
    by_m = {r["marche"]: r for r in rows}
    check("m.cov_pas_tank_x", by_m.get("1X2", {}).get("n") == 1, str(rows))
    check("m.cov_mt_plate_in", "MT_PROLIFIQUE" in by_m, str(rows))
    h2 = marches.hint_marches(blob)
    check("m.hint_pas_stub", "O/U2.5,MT2" not in h2, h2)
    check("m.hint_1x2", "1X2" in h2, h2)
    check("m.hint_mt", "MT2" in h2, h2)
    check("m.plate_jouable", marches.jambe_jouable(mt_plate["top3"][0]) is True)
    check("m.tank_x_hors", marches.jambe_jouable(tank_x["top3"][0]) is False)


def test_schema_listen():
    schema = json.load(open(os.path.join(WORLD, "CONTRACTS", "schema_listen.json"), encoding="utf-8"))
    pat = schema["properties"]["cmd"]["pattern"]
    check("m.schema_marches", "marches" in pat, pat)


def main():
    print("=" * 70)
    print("TEST S11 — marches")
    print("=" * 70)
    test_parse_aliases()
    test_parse_telegram()
    test_zero_match_zero_ticket()
    test_meme_navire()
    test_mono_marche()
    test_dix_jambes()
    test_floor_refuse()
    test_combo_floor_pas_remplissage()
    test_couverture_et_log()
    test_workflow_cmd()
    test_hint_du_jour()
    test_schema_listen()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S11 marches : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
