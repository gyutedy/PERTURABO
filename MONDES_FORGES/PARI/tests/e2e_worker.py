#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E WORKER — parite parse.py / index.js + workflow deploy (zero reseau)."""

import os
import sys

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = os.path.normpath(os.path.join(WORLD, "..", ".."))
CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def main():
    js_p = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "src", "index.js")
    py_p = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "parse.py")
    wf_p = os.path.join(REPO, ".github", "workflows", "worker_deploy.yml")
    toml_p = os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "wrangler.toml")
    js = open(js_p, encoding="utf-8").read()
    py = open(py_p, encoding="utf-8").read()
    wf = open(wf_p, encoding="utf-8").read() if os.path.exists(wf_p) else ""
    toml = open(toml_p, encoding="utf-8").read()

    for cmd in ("bankroll", "surticket", "data", "budget", "roi", "vanus", "modele", "gel"):
        check(f"W.js_known_{cmd}", f'"{cmd}"' in js)
        check(f"W.py_known_{cmd}", f'"{cmd}"' in py)

    check("W.js_forward_extra", "canon === \"data\"" in js and "canon === \"bankroll\"" in js
          and "canon === \"surticket\"" in js and "canon === \"vanus\"" in js
          and "canon === \"gel\"" in js)
    check("W.py_forward_extra", '"data", "status", "roi"' in py and "bankroll" in py
          and '"gel", "vanus"' in py)
    check("W.help_vanus", "/vanus" in js and "/vanus" in py)
    check("W.help_data_n", "/data N" in js and "/data N" in py)
    check("W.help_budget_bankroll", "bankroll" in js and "bankroll" in py)
    check("W.gh_ref_xs4c", "pari-forge-perturabo-xs4c" in js and "pari-forge-perturabo-xs4c" in toml)
    check("W.deploy_workflow", "wrangler" in wf and "CLOUDFLARE_API_TOKEN" in wf and "env_pari" in wf)
    check("W.deploy_skip_sans_secret", "skip" in wf.lower() and "present" in wf)
    check("W.pas_github_secrets", "${{ secrets.CLOUDFLARE" not in wf)
    check("W.deploy_paths_listen", "ORCHESTRATOR/LISTEN" in wf)
    check("W.pas_webhook_telegram", "api.telegram.org" not in wf and "setWebhook" not in wf)

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"WORKER {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
