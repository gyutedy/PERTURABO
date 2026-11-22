#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VC — vanus_fetch CSV Big 5. Zero reseau. Timeout/HTML = hole. Pas de gate."""

import ast
import json
import os
import sys
import tempfile
import urllib.error

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(WORLD, "F00_RADAR", "CODEBASE"))
sys.path.insert(0, os.path.join(WORLD, "F02_BREACHER", "CODEBASE"))

import moteur_flag  # noqa: E402
import vanus_fetch as vf  # noqa: E402

CHECKS = []

CSV_E0 = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,B365H,B365D,B365A\n"
    "E0,09/08/2025,Arsenal,Chelsea,0,0,0,0,1.85,3.60,4.20\n"
    "E0,10/08/2025,Liverpool,Everton,2,1,1,0,1.70,3.80,5.00\n"
)
CSV_SP1 = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,B365H,B365D,B365A\n"
    "SP1,11/08/2025,Barca,Madrid,3,1,2,0,2.10,3.40,3.50\n"
)


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def _src():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "vanus_fetch.py"), encoding="utf-8").read()


def _capteurs():
    return open(os.path.join(WORLD, "F00_RADAR", "CODEBASE", "capteurs.py"), encoding="utf-8").read()


def _getter(mapping):
    def g(url, timeout=None):
        for code, body in mapping.items():
            if url.endswith("/%s.csv" % code):
                if isinstance(body, BaseException):
                    raise body
                return body
        raise TimeoutError("timeout")
    return g


def t_signal():
    tmp = tempfile.mkdtemp(prefix="pari-vc-signal-")
    target = os.path.join(tmp, "signals_basket.json")
    blob = {"contract": "vanus.signal.v1", "sport": "basket", "source": "speculum-basket",
            "generated_at": "2026-11-18T00:00:00Z", "matches": {"a": {"consensus": {}}}}
    body = json.dumps(blob)
    ok = vf.fetch_signal(url="https://example.invalid/latest.json", path=target, getter=lambda *a, **k: body)
    check("vc.signal_ok", ok["ok"] and ok["n_matchs"] == 1 and ok["holes"] == [], str(ok))
    written = json.load(open(target, encoding="utf-8"))
    check("vc.signal_contenu", written == blob and written.get("sport") == "basket")
    check("vc.signal_pas_p", "p_modele" not in written and "proba" not in written)

    bad = tempfile.mkdtemp(prefix="pari-vc-signalbad-")
    cases = [
        ("timeout", TimeoutError("t"), ["timeout"]),
        ("http", urllib.error.URLError("x"), ["http"]),
        ("html", "<html>x</html>", ["html"]),
        ("vide", None, ["vide"]),
        ("json", "{", ["json"]),
        ("contrat", json.dumps({"contract": "autre", "sport": "basket", "matches": {}}), ["contrat"]),
        ("sport", json.dumps({"contract": "vanus.signal.v1", "sport": "foot", "matches": {}}), ["sport"]),
    ]
    for name, payload, holes in cases:
        p = os.path.join(bad, name + ".json")
        if isinstance(payload, BaseException):
            def g(url, timeout=None, _e=payload):
                raise _e
        else:
            def g(url, timeout=None, _b=payload):
                return _b
        rec = vf.fetch_signal(url="https://example.invalid/latest.json", path=p, getter=g)
        check("vc.signal_" + name, rec["holes"] == holes and not rec["ok"] and not os.path.exists(p), str(rec))

    abs_rec = vf.fetch_signal(url=None, path=os.path.join(bad, "absent.json"), getter=lambda *a, **k: body)
    check("vc.signal_url_absente", abs_rec["holes"] == ["url_absente"])

    old_env = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    try:
        skip = vf.fetch_signal(url="https://example.invalid/latest.json", path=os.path.join(bad, "skip.json"),
                               getter=lambda *a, **k: body)
    finally:
        if old_env is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_env
    check("vc.signal_skip", skip["holes"] == ["skip"])

    old_url = os.environ.get(vf.SIGNAL_URL_ENV)
    os.environ[vf.SIGNAL_URL_ENV] = "https://example.invalid/env.json"
    try:
        env_rec = vf.fetch_signal(path=os.path.join(tmp, "env.json"), getter=lambda *a, **k: body)
    finally:
        if old_url is None:
            os.environ.pop(vf.SIGNAL_URL_ENV, None)
        else:
            os.environ[vf.SIGNAL_URL_ENV] = old_url
    check("vc.signal_env_url", env_rec["ok"] and env_rec["url"].endswith("/env.json"))

    old_argv = sys.argv
    import io as _io
    buf = _io.StringIO()
    sys.argv = ["vanus_fetch.py", "--sport", "basket"]
    try:
        old_stdout = sys.stdout
        sys.stdout = buf
        vf.main()
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv
    cli = json.loads(buf.getvalue())
    check("vc.signal_cli", cli["sport"] == "basket" and "url_absente" in cli["holes"], str(cli))


def t_slate():
    tmp = tempfile.mkdtemp(prefix="pari-vc-slate-")
    target = os.path.join(tmp, "slate_basket.json")
    slate = {"contract": "vanus.slate.v1", "index": "winner_vision", "sport": "basket",
             "matches": [{"match_key": "a_b", "odds": {"ml_1": 2.08}}], "holes": []}
    ok = vf.fetch_slate(url="https://example.invalid/slate.json", path=target,
                        getter=lambda *a, **k: json.dumps(slate))
    check("vc.slate_ok", ok["ok"] and ok["n_matchs"] == 1 and ok["holes"] == [], str(ok))
    check("vc.slate_contenu", json.load(open(target, encoding="utf-8")) == slate)
    wrong = vf.fetch_slate(url="https://example.invalid/slate.json", path=os.path.join(tmp, "x.json"),
                           getter=lambda *a, **k: json.dumps({**slate, "contract": "vanus.signal.v1"}))
    check("vc.slate_contrat_refuse", wrong["holes"] == ["contrat"] and not wrong["ok"])
    cross = vf.fetch_slate(url="https://example.invalid/slate.json", path=os.path.join(tmp, "y.json"),
                           sport="foot", getter=lambda *a, **k: json.dumps(slate))
    check("vc.slate_cross_sport_refuse", cross["holes"] == ["sport"])
    no_url = vf.fetch_slate(url=None, path=os.path.join(tmp, "z.json"),
                            getter=lambda *a, **k: json.dumps(slate))
    check("vc.slate_url_absente", no_url["holes"] == ["url_absente"])


def main():
    print("=" * 70)
    print("TEST VC — vanus_fetch")
    print("=" * 70)
    t_signal()

    src = _src()
    check("vc.pas_gate", "verdict" not in src)
    check("vc.pas_apply_gates", "apply_gates" not in src)
    check("vc.stdlib", "import numpy" not in src and "import scipy" not in src)
    check("vc.pas_capteurs", "vanus_fetch" not in _capteurs())
    check("vc.pas_tickets", "set_tickets" not in src and "tickets_enabled" not in src)
    ast.parse(src)
    check("vc.ast", True)

    old_skip = os.environ.get("PARI_SKIP_VANUS")
    os.environ["PARI_SKIP_VANUS"] = "1"
    tmp_skip = tempfile.mkdtemp(prefix="pari-vc-skip-")
    try:
        blob = vf.fetch(season="2526", cache_dir=tmp_skip, getter=lambda *a, **k: CSV_E0)
        check("vc.skip_hors", blob["hors_couverture"] == list(vf.BIG5), str(blob["hors_couverture"]))
        check("vc.skip_n", blob["n_lignes"] == 0)
        check("vc.skip_files", blob["files"] == [])
        one = vf.fetch_one("E0", season="2526", cache_dir=tmp_skip, getter=lambda *a, **k: CSV_E0)
        check("vc.skip_fetch_one", one["holes"] == ["skip"] and one["n_lignes"] == 0, str(one))
        check("vc.skip_pas_ecrit", not os.path.exists(vf.cache_path("E0", "2526", tmp_skip)))
    finally:
        if old_skip is None:
            os.environ.pop("PARI_SKIP_VANUS", None)
        else:
            os.environ["PARI_SKIP_VANUS"] = old_skip

    tmp = tempfile.mkdtemp(prefix="pari-vc-")
    getter = _getter({
        "E0": CSV_E0,
        "SP1": CSV_SP1,
        "I1": TimeoutError("timeout"),
        "D1": "<html><body>Not Found</body></html>",
        "F1": None,
    })
    blob = vf.fetch(season="2526", cache_dir=tmp, getter=getter)
    check("vc.csv_ok", blob["divisions"].get("E0") == 2 and blob["divisions"].get("SP1") == 1, str(blob["divisions"]))
    check("vc.csv_n", blob["n_lignes"] == 3, str(blob["n_lignes"]))
    check("vc.hors_partial", blob["hors_couverture"] == ["I1", "D1", "F1"], str(blob["hors_couverture"]))
    check("vc.e0_pas_hors", "E0" not in blob["hors_couverture"] and "SP1" not in blob["hors_couverture"])
    check("vc.cache_name", os.path.isfile(os.path.join(tmp, "uk_E0_2526.csv")))
    check("vc.timeout_hole", any(h.startswith("I1:timeout") for h in blob["holes"]), str(blob["holes"]))
    check("vc.html_hole", any(h.startswith("D1:html") for h in blob["holes"]), str(blob["holes"]))
    check("vc.html_pas_ecrit", not os.path.exists(os.path.join(tmp, "uk_D1_2526.csv")))
    check("vc.vide_hole", any(h.startswith("F1:vide") for h in blob["holes"]), str(blob["holes"]))
    check("vc.timeout_pas_ecrit", not os.path.exists(os.path.join(tmp, "uk_I1_2526.csv")))

    one_html = vf.fetch_one("D1", season="2526", cache_dir=tmp, getter=getter)
    check("vc.fetch_one_html", one_html["holes"] == ["html"] and one_html["ok"] is False, str(one_html))
    one_to = vf.fetch_one("I1", season="2526", cache_dir=tmp, getter=getter)
    check("vc.fetch_one_timeout", one_to["holes"] == ["timeout"], str(one_to))

    err = _getter({"E0": urllib.error.URLError("boom")})
    one_http = vf.fetch_one("E0", season="2526", cache_dir=tempfile.mkdtemp(prefix="pari-vc-http-"), getter=err)
    check("vc.http_hole", one_http["holes"] == ["http"] and one_http["n_lignes"] == 0, str(one_http))

    check("vc.url_season", vf.url_for("E0", "2526").endswith("/mmz4281/2526/E0.csv"), vf.url_for("E0", "2526"))
    check("vc.gel", moteur_flag.tickets_enabled() is False)

    rec_path = os.path.join(tmp, "inventaire.json")
    old_argv = sys.argv
    import io as _io
    buf = _io.StringIO()
    sys.argv = ["vanus_fetch.py", "--season", "2526", "--dir", tmp, "--out", rec_path]
    os.environ["PARI_SKIP_VANUS"] = "1"
    try:
        old_stdout = sys.stdout
        sys.stdout = buf
        vf.main()
    finally:
        sys.stdout = old_stdout
        sys.argv = old_argv
        os.environ.pop("PARI_SKIP_VANUS", None)
    rec = json.load(open(rec_path, encoding="utf-8"))
    check("vc.cli_skip", rec["n_lignes"] == 0 and rec["hors_couverture"] == list(vf.BIG5), str(rec))

    t_slate()

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"VC vanus_fetch : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
