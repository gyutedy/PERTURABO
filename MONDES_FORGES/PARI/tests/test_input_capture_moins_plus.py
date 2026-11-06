#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 — parseur Moins/Plus (pas de 2.5 invente) + cote_plate + whitelist E1/D2."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))

from input_capture import parse_capture, to_carte  # noqa: E402
import capteurs  # noqa: E402

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _flat(parsed):
    rows = []
    for b in parsed.get("captures") or []:
        for m in b.get("matchs") or []:
            rows.append(m)
    return rows


def test_moins_plus_sans_ligne():
    table = (
        "| Compétition & Match | Horaire | 1 | X | 2 | Moins | Plus | 1st | Égal | 2nd |\n"
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| Angleterre - Premier League<br>Everton FC vs Coventry City | 06/11/26 21:00 (#411) | 1.73 | 3.90 | 4.40 | 1.44 | 2.25 | 3.10 | 3.00 | 2.10 |\n"
        "| Angleterre - Premier League<br>Arsenal FC vs Hull City | 07/11/26 16.00 (#412) | 1.16 | 7.50 | 16.00 | 1.60 | 1.94 | 3.10 | 3.00 | 2.10 |\n"
        "| Angleterre - Premier League<br>Manchester City vs Fulham FC | 21/11/26 13:30 (#392) | 1.45 | 4.80 | 6.20 | 1.58 | 1.97 | 3.10 | 3.00 | 2.10 |\n"
        "| Angleterre - Premier League<br>Brentford FC vs Everton FC | Date non précisée | 1.82 | 3.80 | 4.00 | 1.46 | 2.20 | 3.10 | 3.00 | 2.10 |\n"
    )
    p = parse_capture(table)
    rows = _flat(p)
    everton = next((m for m in rows if m.get("dom") == "Everton FC"), {})
    cotes = everton.get("cotes") or {}
    check("mp.n", p.get("n_matchs") == 4, f"n={p.get('n_matchs')}")
    check("mp.keep_cotes", cotes.get("under") == 1.44 and cotes.get("plus") is None
          and cotes.get("over") == 2.25, f"cotes={cotes}")
    check("mp.pas_de_25", "o2.5" not in cotes and "u2.5" not in cotes, f"cotes={cotes}")
    check("mp.hole", "ligne_totale_Moins_Plus" in (everton.get("holes") or []),
          f"holes={everton.get('holes')}")
    check("mp.warn", any("pas de 2.5" in w for w in (everton.get("warnings") or [])),
          f"warn={everton.get('warnings')}")
    carte = to_carte(p)
    c_ev = next((m for m in carte["matchs"] if m.get("dom") == "Everton FC"), {})
    check("mp.carte_hole", "ligne_totale_Moins_Plus" in (c_ev.get("holes") or []),
          f"carte={c_ev.get('holes')}")
    check("mp.carte_cotes", (c_ev.get("cotes") or {}).get("under") == 1.44)


def test_ligne_colonne():
    table = (
        "| Compétition & Match | Horaire | 1 | X | 2 | Ligne (Total) | Moins | Plus |\n"
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| Angleterre - Premier League<br>Everton FC vs Coventry City | 06/11/26 21:00 | 1.73 | 3.90 | 4.40 | 2.5 | 1.44 | 2.25 |\n"
        "| Angleterre - Premier League<br>Kitchee vs Phnom | 06/11/26 13:15 | 1.79 | 3.65 | 3.60 | 1.5 | 1.51 | 2.10 |\n"
    )
    rows = _flat(parse_capture(table))
    ev = next(m for m in rows if m.get("dom") == "Everton FC")
    kit = next(m for m in rows if m.get("dom") == "Kitchee")
    check("ln.o25", (ev.get("cotes") or {}).get("o2.5") == 2.25
          and (ev.get("cotes") or {}).get("u2.5") == 1.44, f"cotes={ev.get('cotes')}")
    check("ln.o15", (kit.get("cotes") or {}).get("o1.5") == 2.10
          and (kit.get("cotes") or {}).get("u1.5") == 1.51, f"cotes={kit.get('cotes')}")
    check("ln.pas_hole", not (ev.get("holes") or []), f"holes={ev.get('holes')}")


def test_header_moins_de_x():
    table = (
        "| Compétition & Match | Horaire | 1 | X | 2 | Moins de 2.5 | Plus de 2.5 |\n"
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n"
        "| Angleterre - Championship<br>Leeds United vs Coventry City | 08/11/26 16:00 | 1.90 | 3.40 | 4.10 | 1.80 | 2.00 |\n"
    )
    m = _flat(parse_capture(table))[0]
    c = m.get("cotes") or {}
    check("hdr.u25", c.get("u2.5") == 1.80 and c.get("o2.5") == 2.00, f"cotes={c}")
    check("hdr.pas_hole", "ligne_totale_Moins_Plus" not in (m.get("holes") or []),
          f"holes={m.get('holes')}")


def test_cote_plate():
    rows = []
    rows.append("| Compétition & Match | Horaire | 1 | X | 2 | Moins | Plus | 1st | Égal | 2nd |")
    rows.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    teams = [
        ("Everton FC", "Coventry City"),
        ("Arsenal FC", "Hull City"),
        ("Manchester City", "Fulham FC"),
        ("Brentford FC", "Everton FC"),
        ("Chelsea FC", "Leeds United"),
        ("Liverpool FC", "West Ham"),
    ]
    for i, (d, e) in enumerate(teams):
        mt2 = "2.10" if i < 5 else "2.40"
        rows.append(
            f"| Angleterre - Premier League<br>{d} vs {e} | 06/11/26 21:00 | "
            f"1.70 | 3.80 | 4.50 | 1.50 | 2.20 | 3.10 | 3.00 | {mt2} |"
        )
    p = parse_capture("\n".join(rows) + "\n")
    ms = _flat(p)
    n_plate = sum(1 for m in ms if m.get("cote_plate"))
    check("cp.flag5", n_plate == 5, f"n_plate={n_plate} n={len(ms)}")
    last = next(m for m in ms if m.get("dom") == "Liverpool FC")
    check("cp.dernier_libre", not last.get("cote_plate"), f"cotes={last.get('cotes')}")
    check("cp.mt_garde", (ms[0].get("cotes") or {}).get("mt2") == 2.10)
    carte = to_carte(p)
    n_c = sum(1 for m in carte["matchs"] if m.get("cote_plate"))
    check("cp.carte", n_c == 5, f"n_c={n_c}")


def test_ligue_e1_d2():
    check("lg.e1", capteurs.ligue_code("Angleterre - Championship") == "E1")
    check("lg.e1_efl", capteurs.ligue_code("EFL Championship") == "E1")
    check("lg.d2", capteurs.ligue_code("Allemagne - Bundesliga 2") == "D2")
    check("lg.d2_dot", capteurs.ligue_code("Allemagne - 2. Bundesliga") == "D2")
    check("lg.d1", capteurs.ligue_code("Allemagne - Bundesliga") == "D1")
    check("lg.e0", capteurs.ligue_code("Angleterre - Premier League") == "E0")
    check("lg.laliga2", capteurs.ligue_code("Espagne - LaLiga 2") is None)
    check("lg.la_liga_2", capteurs.ligue_code("Espagne - La Liga 2") is None)
    check("lg.serie_b", capteurs.ligue_code("Italie - Serie B") is None)
    check("lg.e0_pas_e1", capteurs.ligue_code("Championship") != "E0")
    check("lg.d2_pas_d1", capteurs.ligue_code("Bundesliga 2") != "D1")


def main():
    print("=" * 70)
    print("TEST S1 — Moins/Plus + cote_plate + E1/D2")
    print("=" * 70)
    test_moins_plus_sans_ligne()
    test_ligne_colonne()
    test_header_moins_de_x()
    test_cote_plate()
    test_ligue_e1_d2()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S1 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
