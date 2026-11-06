#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S8 — sensibilite devig additif + CLV T-0. Zero reseau. Jamais clv=0."""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = os.path.normpath(os.path.join(WORLD, "..", ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F06_TRACKER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))

import devig  # noqa: E402
import forgeward  # noqa: E402
import journal  # noqa: E402
import ledger  # noqa: E402
import odds_watch  # noqa: E402

CHECKS = []
NOW = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


TRIPLE = {"1": 2.75, "X": 3.40, "2": 2.50}


def test_additive_vs_multi():
    m = devig.multiplicative(TRIPLE)
    a = devig.additive(TRIPLE)
    check("cl.multi_ok", m.get("ok") is True)
    check("cl.add_ok", a.get("ok") is True)
    check("cl.multi_method", m.get("method") == "multiplicative")
    check("cl.add_method", a.get("method") == "additive")
    check("cl.add_p_somme", abs(sum(a["p_fair"].values()) - 1) < 1e-12, str(sum(a["p_fair"].values())))
    gp = devig.gap(m, a)
    check("cl.gap_ok", gp.get("ok") is True)
    check("cl.gap_keys", set(gp["gap_p"]) == {"1", "X", "2"}, str(gp.get("gap_p")))
    check("cl.p_fair_differe", any(abs(m["p_fair"][k] - a["p_fair"][k]) > 1e-12 for k in TRIPLE))
    impl = {k: 1.0 / v for k, v in TRIPLE.items()}
    s = sum(impl.values())
    over = (s - 1.0) / 3
    for k in TRIPLE:
        check("cl.add_formule_" + k, abs(a["p_fair"][k] - (impl[k] - over)) < 1e-12)


def test_cote_unique_both():
    m = devig.multiplicative({"o2.5": 1.85})
    a = devig.additive({"o2.5": 1.85})
    check("cl.unique_multi", m.get("ok") is False and "issue_manquante" in (m.get("holes") or []))
    check("cl.unique_add", a.get("ok") is False and "issue_manquante" in (a.get("holes") or []))
    gp = devig.gap(m, a)
    check("cl.unique_gap_fail", gp.get("ok") is False)


def test_forgeward_default_multi_ev_inchange():
    analysis = {
        "probas": {"1": 0.50, "X": 0.25, "2": 0.25, "o2.5": 0.55, "u2.5": 0.45},
        "cs": {},
        "data_quality": {"niveau": "haute", "flags": []},
    }
    m = {
        "id": "M1", "dom": "A", "ext": "B",
        "cotes": {"1": 2.10, "X": 3.40, "2": 3.80, "o2.5": 1.90, "u2.5": 2.00},
    }
    pool = {
        "seuil_ev_top5": 0.03, "seuil_ev_exotique": 0.08,
        "kelly_fraction": 0.25, "mise_max_pct_bankroll": 0.05, "mise_max_pct_exotique": 0.03,
    }
    out = forgeward.predict_match(m, analysis, pool, "top5")
    one = next(s for s in out["selections"] if s["selection"] == "1")
    expected_ev = round(0.50 * 2.10 - 1, 4)
    check("cl.fw_ev", one["ev"] == expected_ev, str(one["ev"]))
    multi = devig.multiplicative({"1": 2.10, "X": 3.40, "2": 3.80})
    add = devig.additive({"1": 2.10, "X": 3.40, "2": 3.80})
    check("cl.fw_p_fair_multi", abs(one["p_fair"] - round(multi["p_fair"]["1"], 4)) < 1e-9, str(one.get("p_fair")))
    check("cl.fw_p_add", one.get("p_fair_additif") == round(add["p_fair"]["1"], 4), str(one.get("p_fair_additif")))
    check("cl.fw_gap", one.get("devig_gap") is not None)
    check("cl.fw_verdict_go", out["verdict"] in ("GO", "THIN"), str(out["verdict"]))
    check("cl.fw_edge_multi", one.get("edge_net_devig") is not None)


def test_t0_window_et_persist():
    ko = NOW
    check("cl.t2h_at_ko", odds_watch.in_window(ko, now=NOW, horizon_h=3) is True)
    check("cl.t2h_passe", odds_watch.in_window(NOW - timedelta(minutes=5), now=NOW, horizon_h=3) is False)
    check("cl.t0_at_ko", odds_watch.in_close_window(ko, now=NOW, grace_min=15) is True)
    check("cl.t0_plus5", odds_watch.in_close_window(NOW - timedelta(minutes=5), now=NOW, grace_min=15) is True)
    check("cl.t0_hors", odds_watch.in_close_window(NOW - timedelta(hours=1), now=NOW, grace_min=15) is False)
    tmp = tempfile.mkdtemp(prefix="pari_clv_odds_")
    try:
        t2h = {
            "snapshot": {
                "generated_at": "2026-11-06T16:00:00Z",
                "kind": "t2h",
                "horizon_h": 3,
                "scanned": [{"id": "M1", "cotes_marche": {"1": 1.95}}],
                "skipped": [], "alerts": [],
            },
            "kind": "t2h",
        }
        t0 = {
            "snapshot": {
                "generated_at": "2026-11-06T18:00:00Z",
                "kind": "t0",
                "horizon_h": 0,
                "scanned": [{"id": "M1", "cotes_marche": {"1": 1.88}}],
                "skipped": [], "alerts": [],
            },
            "kind": "t0",
        }
        p2 = odds_watch.persist(t2h, odds_dir=tmp)
        latest = os.path.join(tmp, "latest.json")
        with open(latest, encoding="utf-8") as f:
            before = json.load(f)
        p0 = odds_watch.persist(t0, odds_dir=tmp)
        with open(latest, encoding="utf-8") as f:
            after = json.load(f)
        check("cl.persist_t2h", p2 and os.path.basename(p2).startswith("t2h_"), str(p2))
        check("cl.persist_t0", p0 and os.path.basename(p0).startswith("t0_"), str(p0))
        check("cl.t0_pas_ecrase_latest", after.get("kind") == "t2h" and after == before)
        check("cl.latest_t0", os.path.exists(os.path.join(tmp, "latest_t0.json")))
        cmap = odds_watch.load_close_cotes(tmp)
        check("cl.close_map", cmap.get("M1", {}).get("1") == 1.88, str(cmap))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tix(gap=0.012, mid="M1"):
    return {
        "generated_at": "2026-11-06T00:00:00Z",
        "tickets": [{
            "rang_ticket": 1,
            "cote_totale": 1.7,
            "mise_fc": 100,
            "jambes": [{
                "match_id": mid,
                "match": "Arsenal vs Chelsea",
                "marche": "1X2",
                "selection": "1",
                "selection_label": "Victoire Domicile",
                "cote": 1.7,
                "devig_gap": gap,
            }],
        }],
        "budget": {"budget_fc": 300, "alloue_fc": 100, "reste_fc": 200},
        "warnings": [],
        "regles": {"jambes_max": 4, "mise_min_fc": 100.0},
    }


def test_procedure_gap_journalise():
    proc = journal.build_procedure(_tix())
    check("cl.proc_gap_check", "devig_gap" in (proc.get("checks") or []), str(proc.get("checks")))
    tix = _tix()
    tix["tickets"][0]["jambes"][0].pop("devig_gap")
    proc2 = journal.build_procedure(tix)
    check("cl.proc_sans_gap", "devig_gap" not in (proc2.get("checks") or []), str(proc2.get("checks")))


def test_freeze_7args():
    tix = _tix()
    lot = ledger.freeze_lot(
        "L-CLV", "PARI-TEST", "C-ZZZ", tix,
        ledger.legs_from_tickets(tix["tickets"]), 300, 100)
    check("cl.freeze_7args", lot.get("token") == "L-CLV")
    check("cl.freeze_proc", "devig_gap" in ((lot.get("journal") or {}).get("procedure") or {}).get("checks", []))


def test_settle_close_et_trou():
    tmp = tempfile.mkdtemp(prefix="pari_clv_set_")
    old_lots = ledger.LOTS_PATH
    try:
        lots_path = os.path.join(tmp, "lots.json")
        ledger.LOTS_PATH = lots_path
        tix = _tix()
        lot = ledger.freeze_lot(
            "L-CLO", "PARI-TEST", "C-ZZZ", tix,
            ledger.legs_from_tickets(tix["tickets"]), 300, 100)
        ledger.append_lot(lot, lots_path)
        csv_path = os.path.join(tmp, "settle.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("HomeTeam,AwayTeam,FTR\nArsenal,Chelsea,H\n")

        got, err = ledger.settle_lot("L-CLO", csv_path, lots_path, odds_dir=tmp)
        check("cl.settle_err", err is None, str(err))
        jambe = (((got.get("settle") or {}).get("tickets") or [{}])[0].get("jambes") or [{}])[0]
        check("cl.trou_close", jambe.get("book_odds_close") is None, str(jambe.get("book_odds_close")))
        check("cl.trou_hole", "book_odds_close" in (jambe.get("holes") or []), str(jambe.get("holes")))
        out = (got.get("journal") or {}).get("outcome") or {}
        rec = (out.get("tickets") or [{}])[0]
        check("cl.clv_none", rec.get("clv") is None)
        check("cl.clv_hole", "clv" in (out.get("holes") or []), str(out.get("holes")))
        check("cl.clv_pas_zero", rec.get("clv") != 0)
        check("cl.exclu_clv", rec.get("clv") is None)

        odds_dir = os.path.join(tmp, "odds")
        os.makedirs(odds_dir, exist_ok=True)
        with open(os.path.join(odds_dir, "latest_t0.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "t0",
                "scanned": [{"id": "M1", "cotes_marche": {"1": 1.88, "X": 3.50, "2": 4.10}}],
            }, f)
        with open(os.path.join(odds_dir, "latest.json"), "w", encoding="utf-8") as f:
            json.dump({
                "kind": "t2h",
                "scanned": [{"id": "M1", "cotes_marche": {"1": 1.99}}],
            }, f)
        tix2 = _tix()
        lot2 = ledger.freeze_lot(
            "L-CL1", "PARI-TEST", "C-AAA", tix2,
            ledger.legs_from_tickets(tix2["tickets"]), 300, 100)
        ledger.append_lot(lot2, lots_path)
        got2, err2 = ledger.settle_lot("L-CL1", csv_path, lots_path, odds_dir=odds_dir)
        check("cl.settle2_err", err2 is None, str(err2))
        j2 = (((got2.get("settle") or {}).get("tickets") or [{}])[0].get("jambes") or [{}])[0]
        check("cl.close_pose", j2.get("book_odds_close") == 1.88, str(j2.get("book_odds_close")))
        check("cl.close_pas_t2h", j2.get("book_odds_close") != 1.99)
        check("cl.close_pas_zero", j2.get("book_odds_close") != 0)
        out2 = (got2.get("journal") or {}).get("outcome") or {}
        rec2 = (out2.get("tickets") or [{}])[0]
        expected_clv = 1.7 / 1.88 - 1.0
        check("cl.s9_clv_ratio", rec2.get("clv") is not None
              and abs(rec2.get("clv") - expected_clv) < 1e-12, str(rec2.get("clv")))
        msg = ledger.format_settle(got2)
        check("cl.fmt_close", "close 1.88" in msg, msg[:200])
        msg_trou = ledger.format_settle(got)
        check("cl.fmt_trou", "close trou" in msg_trou, msg_trou[:200])
    finally:
        ledger.LOTS_PATH = old_lots
        shutil.rmtree(tmp, ignore_errors=True)


def test_cfg_default_multi():
    path = os.path.join(WORLD, "config", "devig.json")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    check("cl.cfg_method", cfg.get("default_method") == "multiplicative")
    check("cl.cfg_bonus", abs(float(cfg.get("double_confirmation_bonus_pt")) - 0.01) < 1e-12)


def test_workflow_t0():
    wf = os.path.join(REPO, ".github", "workflows", "pari_odds_t0.yml")
    check("cl.wf_exists", os.path.exists(wf))
    src = open(wf, encoding="utf-8").read() if os.path.exists(wf) else ""
    check("cl.wf_close", "--close" in src)
    check("cl.wf_pas_secrets", "${{ secrets." not in src)
    check("cl.wf_pas_poisson", "import breacher" not in src and "dixon" not in src.lower())
    cap = open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "capteurs.py"), encoding="utf-8").read()
    check("cl.cli_close", "--close" in cap)


def main():
    print("=" * 70)
    print("TEST S8 — sensibilite devig + CLV T-0")
    print("=" * 70)
    test_additive_vs_multi()
    test_cote_unique_both()
    test_forgeward_default_multi_ev_inchange()
    test_t0_window_et_persist()
    test_procedure_gap_journalise()
    test_freeze_7args()
    test_settle_close_et_trou()
    test_cfg_default_multi()
    test_workflow_t0()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S8 clv : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
