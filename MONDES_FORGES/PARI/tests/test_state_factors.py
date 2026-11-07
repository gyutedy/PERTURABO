#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S13 — table effectifs + facteurs etat lambda. Zero reseau."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "TYRANT", "CODEBASE"))

from input_capture import parse_capture, to_carte  # noqa: E402
import breacher  # noqa: E402
import state_factors  # noqa: E402
import qualitative  # noqa: E402

CHECKS = []
state_factors._CONFIG_CACHE = None


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _flat(parsed):
    rows = []
    for b in parsed.get("captures") or []:
        for m in b.get("matchs") or []:
            rows.append(m)
    return rows


ODDS = (
    "| Compétition & Match | Horaire | 1 | X | 2 | Moins de 2.5 | Plus de 2.5 |\n"
    "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n"
    "| Angleterre - Premier League<br>Everton FC vs Coventry City | 06/11/26 21:00 | 1.73 | 3.90 | 4.40 | 1.44 | 2.25 |\n"
    "| Angleterre - Premier League<br>Auxerre vs Lens | 07/11/26 16:00 | 2.10 | 3.20 | 3.40 | 1.70 | 2.10 |\n"
)

EFF = (
    "| Match | Cote | att | def | gk | milieu | repos | rotation | derby | meteo | retour |\n"
    "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    "| Everton FC vs Coventry City | dom | 1 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |\n"
    "| Everton FC vs Coventry City | ext | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |\n"
)


def test_parse_two_row():
    p = parse_capture(ODDS + "\n" + EFF)
    rows = _flat(p)
    check("p.n", p.get("n_matchs") == 2, f"n={p.get('n_matchs')}")
    ev = next((m for m in rows if m.get("dom") == "Everton FC"), {})
    aux = next((m for m in rows if m.get("dom") == "Auxerre"), {})
    check("p.aux_cotes", (aux.get("cotes") or {}).get("1") == 2.10, f"cotes={aux.get('cotes')}")
    eff = ev.get("effectifs") or {}
    check("p.att_dom", (eff.get("dom") or {}).get("attaquants_titulaires_absents") == 1,
          f"eff={eff}")
    check("p.att_ext", (eff.get("ext") or {}).get("attaquants_titulaires_absents") == 0)
    check("p.repos", (eff.get("dom") or {}).get("jours_repos") == 6)
    check("p.pas_cotes_eff", "att" not in (ev.get("cotes") or {}), f"cotes={ev.get('cotes')}")
    carte = to_carte(p)
    c_ev = next((m for m in carte["matchs"] if m.get("dom") == "Everton FC"), {})
    check("p.carte", (c_ev.get("effectifs") or {}).get("dom", {}).get("attaquants_titulaires_absents") == 1)


def test_suffix_headers():
    table = ODDS + (
        "\n| Match | att_dom | att_ext | def_dom | def_ext | gk_dom | gk_ext |\n"
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| Everton FC vs Coventry City | 2 | 0 | 0 | 1 | 0 | 1 |\n"
    )
    ev = next(m for m in _flat(parse_capture(table)) if m.get("dom") == "Everton FC")
    d, e = (ev.get("effectifs") or {}).get("dom") or {}, (ev.get("effectifs") or {}).get("ext") or {}
    check("sx.att", d.get("attaquants_titulaires_absents") == 2)
    check("sx.def_ext", e.get("defenseurs_cles_absents") == 1)
    check("sx.gk_ext", e.get("gardien_1_absent") is True)


def test_apply_empty():
    out = state_factors.apply({"id": "M1"}, 1.4, 1.1)
    check("e.applied", out["applied"] is False)
    check("e.x1", out["lambda_dom"] == 1.4 and out["lambda_ext"] == 1.1)
    check("e.holes", "effectifs" in (out.get("holes") or []), str(out.get("holes")))


def _stub(effectifs=None):
    stats = {
        "dom": {"mj": 10, "marques": 15, "encaisses": 10, "marques_mt1": 6, "encaisses_mt1": 4},
        "ext": {"mj": 10, "marques": 12, "encaisses": 12, "marques_mt1": 5, "encaisses_mt1": 5},
    }
    m = {"id": "M1", "dom": "A", "ext": "B", "stats": stats, "cotes": {"1": 2.0, "X": 3.2, "2": 3.8, "o2.5": 1.9}}
    if effectifs is not None:
        m["effectifs"] = effectifs
    avg = {
        "buts_dom_moy": 1.5, "buts_ext_moy": 1.2, "part_mt1_ligue": 0.44,
        "bonus_domicile": 1.10, "bonus_exterieur": 0.95, "rho": -0.13,
    }
    return m, avg


def test_att_out_p_o25():
    m0, avg = _stub()
    a0 = breacher.analyse_match(m0, avg)
    m1, _ = _stub({
        "dom": {
            "attaquants_titulaires_absents": 1, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 6, "rotation_lourde": 0,
        },
        "ext": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 4, "rotation_lourde": 0,
        },
    })
    a1 = breacher.analyse_match(m1, avg)
    p0 = a0["probas"]["o2.5"]
    p1 = a1["probas"]["o2.5"]
    check("a.p_drop", p1 < p0, f"{p1} vs {p0}")
    check("a.factor", abs(a1["state_factors"]["factor_dom"] - 0.90) < 1e-6,
          str(a1["state_factors"]))
    check("a.raw", a1["lambdas"]["dom_raw"] == a0["lambdas"]["dom_total"])
    check("a.dq_haute", a1["data_quality"]["niveau"] in ("haute", "moyenne"))
    check("a.no_dq_hole", "effectifs" not in (a1["data_quality"].get("flags") or []))


def test_cap():
    m, avg = _stub({
        "dom": {
            "attaquants_titulaires_absents": 2, "defenseurs_cles_absents": 3,
            "gardien_1_absent": True, "milieu_createur_absent": True,
            "jours_repos": 3, "rotation_lourde": 0,
        },
        "ext": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 3, "rotation_lourde": 0,
        },
    })
    a = breacher.analyse_match(m, avg)
    sf = a["state_factors"]
    check("c.clip_lo", abs(sf["factor_dom"] - 0.8) < 1e-6, str(sf["factor_dom"]))
    check("c.clip_hi", abs(sf["factor_ext"] - 1.2) < 1e-6, str(sf["factor_ext"]))
    check("c.hit", sf["cap_hit"] is True, str(sf))
    check("c.flag", "cap_hit" in sf["flags"])


def test_rotation_flag():
    m, avg = _stub({
        "dom": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 3, "rotation_lourde": 4,
        },
        "ext": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 3, "rotation_lourde": 0,
        },
    })
    a = breacher.analyse_match(m, avg)
    check("r.flag", "rotation_lourde" in a["state_factors"]["flags"])
    check("r.x1", abs(a["state_factors"]["factor_dom"] - 1.0) < 1e-9)
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "o2.5", "marche": "O/U", "verdict": "VALUE", "ev": 0.12, "mise_units": 1},
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.08, "mise_units": 1},
        ],
    }]}
    analysis = {"analyses": [a]}
    notes = {"source": "f00_vote", "notes_count": 0, "notes": []}
    vq, filt = qualitative.apply_qualitative(pred, analysis, notes)
    o25 = [s for s in filt["predictions"][0]["selections"] if s["selection"] == "o2.5"][0]
    one = [s for s in filt["predictions"][0]["selections"] if s["selection"] == "1"][0]
    check("r.pas_veto", o25["verdict"] == "VALUE", o25["verdict"])
    check("r.raison", any("O/BTTS deconseilles" in x for x in (o25.get("notes_qualitatives") or {}).get("raisons") or []))
    check("r.1_intact", one["verdict"] == "VALUE")
    check("r.verdict_flag", (vq["verdicts"][0] or {}).get("o_btts_deconseilles") is True)


def test_derby_veto():
    m, avg = _stub({
        "dom": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 5, "rotation_lourde": 0, "derby": True,
        },
        "ext": {
            "attaquants_titulaires_absents": 0, "defenseurs_cles_absents": 0,
            "gardien_1_absent": False, "milieu_createur_absent": False,
            "jours_repos": 5, "rotation_lourde": 0,
        },
        "derby": True,
    })
    a = breacher.analyse_match(m, avg)
    check("d.flag", "derby" in a["state_factors"]["flags"])
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "o2.5", "marche": "O/U", "verdict": "VALUE", "ev": 0.12, "mise_units": 1},
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.08, "mise_units": 1},
        ],
    }]}
    vq, filt = qualitative.apply_qualitative(
        pred, {"analyses": [a]}, {"source": "f00_vote", "notes_count": 0, "notes": []})
    o25 = [s for s in filt["predictions"][0]["selections"] if s["selection"] == "o2.5"][0]
    one = [s for s in filt["predictions"][0]["selections"] if s["selection"] == "1"][0]
    check("d.veto", o25["verdict"] == "NO_BET", o25["verdict"])
    check("d.1_ok", one["verdict"] == "VALUE")
    check("d.exclus", "o2.5" in (vq["verdicts"][0].get("marches_exclus") or []))


def test_notes_zero_intact():
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "mt2", "marche": "MT2", "verdict": "VALUE", "ev": 0.12, "mise_units": 1},
        ],
    }]}
    analysis = {"analyses": [{"id": "M1", "data_quality": {"niveau": "haute"}}]}
    notes_zero = {"source": "f00_vote", "notes_count": 0, "notes": []}
    vq, filt = qualitative.apply_qualitative(pred, analysis, notes_zero)
    check("z.vide", vq["verdicts"] == [] and filt["predictions"][0]["selections"][0]["verdict"] == "VALUE")
    vq2, _ = qualitative.apply_qualitative(pred, [], notes_zero)
    check("z.list", vq2["verdicts"] == [])


def main():
    print("=" * 70)
    print("TEST S13 — state_factors + table effectifs")
    print("=" * 70)
    test_parse_two_row()
    test_suffix_headers()
    test_apply_empty()
    test_att_out_p_o25()
    test_cap()
    test_rotation_flag()
    test_derby_veto()
    test_notes_zero_intact()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S13 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
