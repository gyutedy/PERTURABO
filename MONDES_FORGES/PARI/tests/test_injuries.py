#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S15 — injuries API flags TYRANT. Zero reseau. Jamais un 2e lambda."""

import os
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors"))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "TYRANT", "CODEBASE"))

os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-inj-")
os.environ.pop("PARI_SKIP_INJURIES", None)

import injuries  # noqa: E402
import vote  # noqa: E402
import state_factors  # noqa: E402
import qualitative  # noqa: E402
import breacher  # noqa: E402

CHECKS = []
state_factors._CONFIG_CACHE = None


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _match(**kw):
    m = {
        "id": "M1", "dom": "Arsenal", "ext": "Chelsea",
        "date": "2026-11-07", "league_code": "E0",
    }
    m.update(kw)
    return m


def _inj_payload(rows):
    return {"response": rows, "errors": {}}


def _standings(pairs):
    table = []
    for i, (name, played) in enumerate(pairs, 1):
        table.append({
            "rank": i,
            "team": {"name": name},
            "all": {"played": played},
        })
    return {"response": [{"league": {"standings": [table]}}], "errors": {}}


PL20 = [
    ("Arsenal", 12), ("Man City", 12), ("Liverpool", 12), ("Chelsea", 12),
    ("Tottenham", 12), ("Newcastle", 12), ("Aston Villa", 12), ("Brighton", 12),
    ("West Ham", 12), ("Fulham", 12), ("Brentford", 12), ("Crystal Palace", 12),
    ("Everton", 12), ("Bournemouth", 12), ("Wolves", 12), ("Nottm Forest", 12),
    ("Leicester", 12), ("Ipswich", 12), ("Southampton", 12), ("Luton", 12),
]


def _patch_get(fn):
    old = injuries.http_util.get_json
    injuries.http_util.get_json = fn
    injuries.http_util._FAILS.clear()
    return old


def _restore(old):
    injuries.http_util.get_json = old
    injuries.http_util._FAILS.clear()


def _router(inj=None, stand=None):
    def _get(url, headers=None, timeout=None):
        if "/injuries" in (url or ""):
            return inj
        if "/standings" in (url or ""):
            return stand
        return None
    return _get


def test_no_key_holes():
    old_key = os.environ.pop("API_FOOTBALL_KEY", None)
    try:
        blob = injuries.flags_for(_match())
        check("k.holes", "injuries" in (blob.get("holes") or []), str(blob))
        check("k.flags", blob.get("flags") == [])
        check("k.no_crash", blob.get("detail", {}).get("reason") == "no_key")
    finally:
        if old_key is not None:
            os.environ["API_FOOTBALL_KEY"] = old_key


def test_skip_env():
    os.environ["API_FOOTBALL_KEY"] = "test-key"
    os.environ["PARI_SKIP_INJURIES"] = "1"
    try:
        blob = injuries.flags_for(_match())
        check("s.holes", "injuries" in blob["holes"])
        check("s.flags", blob["flags"] == [])
        check("s.reason", blob["detail"].get("reason") == "PARI_SKIP_INJURIES")
    finally:
        os.environ.pop("PARI_SKIP_INJURIES", None)


def test_http_none_holes():
    os.environ["API_FOOTBALL_KEY"] = "test-key"
    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-inj-dead-")
    old = _patch_get(lambda *a, **k: None)
    try:
        blob = injuries.flags_for(_match())
        check("h.flags", blob["flags"] == [], str(blob))
        check("h.inj", "injuries" in blob["holes"])
        check("h.stand", "standings" in blob["holes"])
    finally:
        _restore(old)


def test_buteur_defenseur():
    os.environ["API_FOOTBALL_KEY"] = "test-key"
    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-inj-bd-")
    inj = _inj_payload([
        {"player": {"name": "Saka", "position": "Attacker"},
         "team": {"name": "Arsenal"}},
        {"player": {"name": "Saliba", "position": "Defender"},
         "team": {"name": "Arsenal"}},
    ])
    old = _patch_get(_router(inj=inj, stand=_standings(PL20)))
    try:
        blob = injuries.flags_for(_match())
        check("bd.buteur", "buteur_manquant" in blob["flags"], str(blob["flags"]))
        check("bd.def", "defenseur_manquant" in blob["flags"], str(blob["flags"]))
        check("bd.no_hole_inj", "injuries" not in blob["holes"], str(blob["holes"]))
    finally:
        _restore(old)


def test_double_motivation():
    os.environ["API_FOOTBALL_KEY"] = "test-key"
    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-inj-dm-")
    old = _patch_get(_router(inj=_inj_payload([]), stand=_standings(PL20)))
    try:
        blob = injuries.flags_for(_match())
        check("dm.flag", "double_motivation" in blob["flags"], str(blob["flags"]))
        check("dm.pas_satisfait", "satisfait_nul" not in blob["flags"])
    finally:
        _restore(old)


def test_satisfait_nul():
    os.environ["API_FOOTBALL_KEY"] = "test-key"
    os.environ["PARI_F00_CACHE"] = tempfile.mkdtemp(prefix="pari-inj-sn-")
    mid = list(PL20)
    mid[0] = ("West Ham", 32)
    mid[9] = ("Arsenal", 32)
    mid[10] = ("Chelsea", 32)
    mid[1] = ("Fulham", 32)
    old = _patch_get(_router(inj=_inj_payload([]), stand=_standings(mid)))
    try:
        blob = injuries.flags_for(_match())
        check("sn.flag", "satisfait_nul" in blob["flags"], str(blob["flags"]))
        check("sn.pas_double", "double_motivation" not in blob["flags"])
    finally:
        _restore(old)


def test_vote_api_football_pas_out():
    hits = [
        {"source": "api_football", "ts": "2026-11-07T10:00:00Z", "fact": "Saka out"},
        {"source": "api-sports", "ts": "2026-11-07T10:00:00Z", "fact": "Saka out"},
        {"source": "sofascore", "ts": "2026-11-07T10:00:00Z", "fact": "Saka out"},
    ]
    v = vote.vote_theme(hits)
    check("v.pas_out", v["verdict"] != "OUT", v["verdict"])
    check("v.api_ignore", "api_football" not in (v.get("sources") or [])
          and "api-sports" not in (v.get("sources") or []))


def test_stamp_jamais_lambda():
    sf = {
        "lambda_dom": 1.4, "lambda_ext": 1.1,
        "lambda_dom_raw": 1.4, "lambda_ext_raw": 1.1,
        "factor_dom": 0.90, "factor_ext": 1.0,
        "applied": True, "flags": [], "holes": [], "cap_hit": False, "journal": ["dom att x0.9000 (1u)"],
    }
    s15 = {"flags": ["buteur_manquant"], "holes": []}
    out = injuries.stamp_state(sf, s15)
    check("st.lambda", out["lambda_dom"] == 1.4 and out["factor_dom"] == 0.90)
    check("st.flag", "buteur_manquant" in out["flags"])
    check("st.raw", sf["lambda_dom"] == 1.4)


def _avg():
    return {
        "buts_dom_moy": 1.4, "buts_ext_moy": 1.1,
        "bonus_domicile": 1.10, "bonus_exterieur": 0.95,
        "rho": -0.13, "part_mt1_ligue": 0.44,
    }


def _stats():
    return {
        "mj": 10, "marques": 14, "encaisses": 10,
        "marques_mt1": 6, "encaisses_mt1": 4,
    }


def test_anti_double_compte():
    m = {
        "id": "M1", "dom": "A", "ext": "B",
        "stats": {"dom": _stats(), "ext": _stats()},
        "effectifs": {
            "dom": {
                "attaquants_titulaires_absents": 1,
                "defenseurs_cles_absents": 0,
                "gardien_1_absent": False,
                "milieu_createur_absent": False,
                "jours_repos": 6, "rotation_lourde": 0,
            },
            "ext": {
                "attaquants_titulaires_absents": 0,
                "defenseurs_cles_absents": 0,
                "gardien_1_absent": False,
                "milieu_createur_absent": False,
                "jours_repos": 5, "rotation_lourde": 0,
            },
        },
        "s15": {"flags": ["buteur_manquant"], "holes": []},
    }
    a = breacher.analyse_match(m, _avg())
    sf = a["state_factors"]
    check("ad.factor", abs(sf["factor_dom"] - 0.90) < 1e-6, str(sf["factor_dom"]))
    check("ad.flag", "buteur_manquant" in sf["flags"])
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "o2.5", "marche": "O/U", "verdict": "VALUE", "ev": 0.12, "mise_units": 1, "p": 0.55},
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.08, "mise_units": 1, "p": 0.42},
        ],
    }]}
    vq, filt = qualitative.apply_qualitative(
        pred, {"analyses": [a]}, {"source": "f00_vote", "notes_count": 0, "notes": []})
    o25 = [s for s in filt["predictions"][0]["selections"] if s["selection"] == "o2.5"][0]
    check("ad.pas_veto", o25["verdict"] == "VALUE", o25["verdict"])
    check("ad.p_intact", o25.get("p") == 0.55)
    check("ad.label", any("S13 deja prix" in x for x in (o25.get("notes_qualitatives") or {}).get("raisons") or []))


def test_veto_sans_s13():
    a = {
        "id": "M1",
        "data_quality": {"niveau": "haute"},
        "state_factors": {
            "applied": False, "factor_dom": 1.0, "factor_ext": 1.0,
            "flags": ["buteur_manquant", "satisfait_nul"],
            "holes": ["effectifs"], "cap_hit": False, "journal": [],
        },
    }
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "o2.5", "marche": "O/U", "verdict": "VALUE", "ev": 0.12, "mise_units": 1, "p": 0.55},
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.08, "mise_units": 1, "p": 0.42},
            {"selection": "x", "marche": "1X2", "verdict": "VALUE", "ev": 0.09, "mise_units": 1, "p": 0.30},
        ],
    }]}
    vq, filt = qualitative.apply_qualitative(
        pred, {"analyses": [a]}, {"source": "f00_vote", "notes_count": 0, "notes": []})
    by = {s["selection"]: s for s in filt["predictions"][0]["selections"]}
    check("vt.o25", by["o2.5"]["verdict"] == "NO_BET")
    check("vt.1", by["1"]["verdict"] == "NO_BET")
    check("vt.x", by["x"]["verdict"] == "VALUE")
    check("vt.p", by["o2.5"].get("p") == 0.55 and by["x"].get("p") == 0.30)
    check("vt.s15", "buteur_manquant" in (vq["verdicts"][0].get("s15_flags") or []))


def test_defenseur_seuil():
    a = {
        "id": "M1",
        "data_quality": {"niveau": "haute"},
        "state_factors": {
            "applied": False, "factor_dom": 1.0, "factor_ext": 1.0,
            "flags": ["defenseur_manquant"],
            "holes": ["effectifs"], "cap_hit": False, "journal": [],
        },
    }
    pred = {"seuil_ev_applique": 0.03, "predictions": [{
        "id": "M1", "match": "A vs B", "verdict": "GO", "meilleure_ev": 0.1,
        "selections": [
            {"selection": "1", "marche": "1X2", "verdict": "VALUE", "ev": 0.04, "mise_units": 1},
        ],
    }]}
    _, filt = qualitative.apply_qualitative(
        pred, {"analyses": [a]}, {"source": "f00_vote", "notes_count": 0, "notes": []})
    one = filt["predictions"][0]["selections"][0]
    check("df.seuil", one["verdict"] == "NO_BET", f"ev={one.get('ev')} seuil={one.get('seuil_ev_effectif')}")


def test_marches_exclus_skip_s15():
    out = state_factors.marches_exclus(["buteur_manquant", "derby"])
    check("me.derby", "o2.5" in out)
    check("me.s15_skip", out == {"o2.5", "o3.5", "btts"} or "1" not in out)


def main():
    print("=" * 70)
    print("TEST S15 — injuries API flags TYRANT")
    print("=" * 70)
    test_no_key_holes()
    test_skip_env()
    test_http_none_holes()
    test_buteur_defenseur()
    test_double_motivation()
    test_satisfait_nul()
    test_vote_api_football_pas_out()
    test_stamp_jamais_lambda()
    test_anti_double_compte()
    test_veto_sans_s13()
    test_defenseur_seuil()
    test_marches_exclus_skip_s15()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"S15 : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
