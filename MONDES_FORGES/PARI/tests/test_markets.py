#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 — marches elargis depuis la meme matrice Poisson. Zero equation changee."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import breacher  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _close(a, b, eps=1e-9):
    return abs(float(a) - float(b)) < eps


def test_same_matrix():
    m = breacher.score_matrix(1.4, 1.1)
    st = breacher.matrix_stats(m)
    scores = st.pop("_scores")
    old_o25 = 0.0
    old_p1 = old_px = old_p2 = old_btts = 0.0
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            if i > j:
                old_p1 += p
            elif i == j:
                old_px += p
            else:
                old_p2 += p
            if i + j >= 3:
                old_o25 += p
            if i >= 1 and j >= 1:
                old_btts += p
    check("mk.o25_inchange", _close(st["o2.5"], old_o25), str(st["o2.5"]))
    check("mk.u25_inchange", _close(st["u2.5"], 1 - old_o25))
    check("mk.1x2_inchange", _close(st["1"], old_p1) and _close(st["X"], old_px) and _close(st["2"], old_p2))
    check("mk.btts_inchange", _close(st["btts"], old_btts))
    check("mk.btts_no", _close(st["btts"] + st["btts_no"], 1.0))
    check("mk.ou05", _close(st["o0.5"] + st["u0.5"], 1.0))
    check("mk.ou15", _close(st["o1.5"] + st["u1.5"], 1.0))
    check("mk.ou35", _close(st["o3.5"] + st["u3.5"], 1.0))
    check("mk.ou45", _close(st["o4.5"] + st["u4.5"], 1.0))
    check("mk.dc_1x", _close(st["dc_1x"], st["1"] + st["X"]))
    check("mk.dc_x2", _close(st["dc_x2"], st["X"] + st["2"]))
    check("mk.dc_12", _close(st["dc_12"], st["1"] + st["2"]))
    check("mk.tt_h", _close(st["tt_h_o0.5"] + st["tt_h_u0.5"], 1.0))
    check("mk.tt_a", _close(st["tt_a_o1.5"] + st["tt_a_u1.5"], 1.0))
    tot_scores = sum(scores.values())
    check("mk.scores_somme", _close(tot_scores, 1.0, 1e-6), str(tot_scores))


def test_cs_top_n_and_cote():
    m = breacher.score_matrix(1.6, 1.2)
    st = breacher.matrix_stats(m)
    scores = st["_scores"]
    top = breacher.top_scores(scores, n=5)
    check("mk.cs_n5", len(top) == 5, str(len(top)))
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    check("mk.cs_best", ranked[0][0] in top)
    extra = breacher.top_scores(scores, n=3, extra_keys=["cs_8-8", "0-0"])
    check("mk.cs_extra_00", "0-0" in extra)
    check("mk.score_key_cs", breacher.score_key("cs_2-1") == "2-1")
    check("mk.score_key_bad", breacher.score_key("o2.5") is None)


def test_poisson_pmf_inchange():
    p0 = breacher.poisson_pmf(0, 1.0)
    check("mk.pmf_e", abs(p0 - 0.3678794411714423) < 1e-12, str(p0))
    t00 = breacher.tau_dc(1.2, 0.9, -0.13, 0, 0)
    check("mk.tau00", abs(t00 - (1.0 - 1.2 * 0.9 * -0.13)) < 1e-12, str(t00))


def main():
    print("=" * 70)
    print("TEST S4 — markets")
    print("=" * 70)
    test_same_matrix()
    test_cs_top_n_and_cote()
    test_poisson_pmf_inchange()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S4 markets : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
