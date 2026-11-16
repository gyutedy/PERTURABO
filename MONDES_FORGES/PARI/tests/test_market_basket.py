#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 — contrat boxscores basket. Zero reseau. Zero estimation."""

import contextlib
import io
import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))

import market_basket as mk  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 1 — market_basket")
    print("=" * 70)

    check("mk.zero_autorise", mk._num("0") == 0)
    check("mk.vide_none", mk._num("") is None and mk._num("  ") is None)
    check("mk.decimal", mk._num("108.0") == 108)
    check("mk.score_absent", "score_absent" in mk.normalize({
        "game_id": "G1", "team_home": "A", "team_home_": "", "team_away": "B",
        "pts_home": "", "pts_away": "107"})["holes"])

    rows, holes = mk.load_dir(os.path.join(FIX, "basket_ok"))
    check("mk.ok_12_matchs", len(rows) == 12, str(len(rows)))
    check("mk.ok_sans_trou", holes == [], str(holes[:3]))
    check("mk.ok_score_lu", rows[0]["pts_home"] == 110 and rows[0]["pts_away"] == 105)
    check("mk.odds_absentes_none", rows[0]["odds_home"] is None and rows[0]["odds_away"] is None)
    check("mk.odds_invalides", mk._odds_num("1.0") is None and mk._odds_num("0") is None
          and mk._odds_num("") is None and mk._odds_num("x") is None)
    check("mk.odds_decimale", mk._odds_num("1,85") == 1.85)

    rows_o, holes_o = mk.load_dir(os.path.join(FIX, "basket_odds"))
    check("mk.odds_lues", len(rows_o) == 12 and holes_o == []
          and rows_o[0]["odds_home"] == 1.8 and rows_o[0]["odds_away"] == 2.1,
          str(rows_o[0]) if rows_o else str(holes_o))

    rows, holes = mk.load_dir(os.path.join(FIX, "basket_holes"))
    check("mk.trous_ecartes", len(rows) == 0, str(len(rows)))
    joined = ",".join(holes)
    check("mk.trou_score", "score_absent" in joined)
    check("mk.trou_equipe", "equipe_absente" in joined)
    check("mk.trou_game_id", "game_id_absent" in joined)

    rows, holes = mk.load_dir(os.path.join(FIX, "basket_badheader"))
    check("mk.colonnes_absentes", len(rows) == 0 and any("colonnes_absentes" in h for h in holes),
          str(holes[:2]))

    absent = os.path.join(tempfile.gettempdir(), "pari-dir-inexistant-basket")
    rows, holes = mk.load_dir(absent)
    check("mk.dossier_absent", rows == [] and holes and holes[0].startswith("dossier_absent:"),
          str(holes[:1]))

    vid = os.path.join(tempfile.mkdtemp(prefix="pari-mk-"), "vide.csv")
    open(vid, "w", encoding="utf-8").close()
    h = mk.read_rows(vid)[1]
    check("mk.entete_absente", h == ["entete_absente"], str(h))

    old = mk.DEFAULT_DIR
    try:
        mk.DEFAULT_DIR = os.path.join(FIX, "basket_ok")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mk.main()
        check("mk.main_affiche_holes", "holes: 0" in buf.getvalue())
        mk.DEFAULT_DIR = os.path.join(FIX, "basket_holes")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mk.main()
        check("mk.main_compte_trous", "holes: 0" not in buf.getvalue(),
              buf.getvalue().splitlines()[1] if len(buf.getvalue().splitlines()) > 1 else "")
    finally:
        mk.DEFAULT_DIR = old

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 1 market : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
