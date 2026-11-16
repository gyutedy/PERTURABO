#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2 — engine basket : mu/sigma uniquement, jamais un p."""

import os
import sys
import tempfile
from datetime import datetime

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("F00_RADAR", "F02_BREACHER"):
    sys.path.insert(0, os.path.join(WORLD, d, "CODEBASE"))

import market_basket as mkb  # noqa: E402
import fit_basket as fb  # noqa: E402
import engine_basket as eb  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "basket_ok")
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[T] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    print("=" * 70)
    print("TEST Phase 2 — engine_basket")
    print("=" * 70)

    rows, _ = mkb.load_dir(FIX)
    blob = fb.fit(fb.prepare(rows, as_of=datetime(2025, 6, 1)))

    r = eb.predict({"home": "Lakers", "away": "Celtics"}, blob=blob)
    check("eng.mu_present", r["mu_home"] is not None and r["mu_away"] is not None, str(r))
    check("eng.sigma_present", r["sigma"] == blob["sigma"])
    check("eng.pas_de_p", not any(k in r for k in ("prob", "p_home", "p1", "proba")))
    check("eng.engine", r["engine"] == "basket_mle")
    check("eng.margin_edge", isinstance(r.get("margin_edge"), float))

    r2 = eb.predict({"dom": "Celtics", "ext": "Lakers"}, blob=blob)
    check("eng.alias_dom_ext", r2["mu_home"] is not None and r2["mu_away"] is not None)

    unknown = eb.predict({"home": "Inconnus", "away": "Lakers"}, blob=blob)
    check("eng.equipe_inconnue", unknown["mu_home"] is None and unknown["mu_away"] is None)
    check("eng.hole_inconnu", any(h.startswith("equipe_inconnue") for h in unknown["holes"]),
          str(unknown["holes"]))
    check("eng.pas_estime", "p" not in unknown and "prob" not in unknown)

    absent = eb.predict({"home": "Lakers", "away": "Celtics"}, blob=None,
                        path=os.path.join(tempfile.gettempdir(), "pari-params-absents.json"))
    check("eng.params_absents", absent["holes"] == ["params_absents"])
    check("eng.mu_none_params", absent["mu_home"] is None and absent["mu_away"] is None)

    vide = eb.predict({}, blob=blob)
    check("eng.equipe_absente", "equipe_absente" in vide["holes"])

    tmp = os.path.join(tempfile.mkdtemp(prefix="pari-eng-"), "params.json")
    fb.save_params(blob, tmp)
    env_old = os.environ.get(eb.ENV_PATH)
    try:
        os.environ[eb.ENV_PATH] = tmp
        loaded = eb.load()
        check("eng.env_path", loaded is not None and loaded["base"] == blob["base"])
    finally:
        if env_old is None:
            os.environ.pop(eb.ENV_PATH, None)
        else:
            os.environ[eb.ENV_PATH] = env_old

    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print("=" * 70)
    print(f"Phase 2 engine : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
