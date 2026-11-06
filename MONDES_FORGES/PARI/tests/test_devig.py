#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 — devig multiplicatif diagnostic. Triple 2.75/3.40/2.50. Zero reseau."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F03_FORGEWARD", "CODEBASE"))

import devig  # noqa: E402
import forgeward  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def test_triple():
    rec = devig.multiplicative({"1": 2.75, "X": 3.40, "2": 2.50})
    check("dv.ok", rec.get("ok") is True, str(rec.get("holes")))
    s = rec["S"]
    check("dv.S_gt1", s > 1, str(s))
    for k, cote in (("1", 2.75), ("X", 3.40), ("2", 2.50)):
        fo = rec["fair_odds"][k]
        check("dv.fair_gt_cote_" + k, fo > cote, f"fair={fo} cote={cote}")
    s_impl = 1 / 2.75 + 1 / 3.40 + 1 / 2.50
    check("dv.S_exact", abs(s - s_impl) < 1e-12, str(s))
    check("dv.p_somme", abs(sum(rec["p_fair"].values()) - 1) < 1e-12)


def test_cote_unique_hole():
    rec = devig.multiplicative({"o2.5": 1.85})
    check("dv.unique_fail", rec.get("ok") is False)
    holes = rec.get("holes") or []
    check("dv.unique_hole", "issue_manquante" in holes, str(holes))
    check("dv.unique_pas_fair", rec.get("p_fair") == {})


def test_vide():
    rec = devig.multiplicative({})
    check("dv.vide_fail", rec.get("ok") is False)
    check("dv.vide_hole", "issue_manquante" in (rec.get("holes") or []))


def test_double_confirmation():
    rec = devig.multiplicative({"1": 2.75, "X": 3.40, "2": 2.50})
    pf = rec["p_fair"]["1"]
    p_hi = pf + 0.05
    cote = 2.75
    dc = devig.double_confirmation(p_hi, cote, pf, bonus_pt=0.01)
    check("dv.dc_flag", dc.get("flag") is True, str(dc))
    check("dv.dc_ev", dc.get("ev_positif") is True)
    p_lo = pf - 0.05
    dc2 = devig.double_confirmation(p_lo, cote, pf, bonus_pt=0.01)
    check("dv.dc_pas_fair", dc2.get("flag") is False)
    dc3 = devig.double_confirmation(0.4, cote, None)
    check("dv.dc_trou_fair", dc3.get("ok") is False and "p_fair" in (dc3.get("holes") or []))


def test_edge_net_pas_ev():
    p, cote, pf = 0.40, 2.75, 0.35
    ev = p * cote - 1
    enet = devig.edge_net_devig(p, cote, pf)
    check("dv.ev_inchange", abs(ev - (0.40 * 2.75 - 1)) < 1e-12, str(ev))
    check("dv.enet_diag", abs(enet - (0.40 / 0.35 - 1)) < 1e-12, str(enet))
    check("dv.enet_ne_pas_ev", abs(enet - ev) > 1e-6)


def test_bonus_config():
    path = os.path.join(WORLD, "config", "devig.json")
    b = devig.load_bonus(path)
    check("dv.bonus_1pt", abs(b - 0.01) < 1e-12, str(b))


def test_forgeward_ev_tri():
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
    evs = [s["ev"] for s in out["selections"]]
    expected = [round(analysis["probas"][k] * m["cotes"][k] - 1, 4) for k in m["cotes"]]
    check("dv.fw_ev", evs == expected, str(evs))
    one = next(s for s in out["selections"] if s["selection"] == "1")
    check("dv.fw_edge_diag", one.get("edge_net_devig") is not None)
    check("dv.fw_dc", "double_confirmation" in one)


def main():
    print("=" * 70)
    print("TEST S4 — devig")
    print("=" * 70)
    test_triple()
    test_cote_unique_hole()
    test_vide()
    test_double_confirmation()
    test_edge_net_pas_ev()
    test_bonus_config()
    test_forgeward_ev_tri()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S4 devig : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
