#!/usr/bin/env python3
"""
WINNER TELEGRAM — photo /winner -> LLM vision -> slate -> vue ingest.
=====================================================================
Appele par pari_listen.yml AVANT workflow.py. La cle LLM vient des
Secrets GitHub injectes dans env_pari par write_env_pari.py ; jamais
de valeur dans le code, un log ou un commit.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1]
for d in ("F00_RADAR", "F01_SENTINEL", "F03_FORGEWARD", "ORCHESTRATOR"):
    p = WORLD / d / "CODEBASE"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
sys.path.insert(0, str(HERE))

import inbox_capture  # noqa: E402
import llm_vision  # noqa: E402
import winner_vision  # noqa: E402
import winner_ingest  # noqa: E402


def sport_of(cmd):
    parts = (cmd or "").split()
    if len(parts) > 1 and parts[1].strip().lower() in ("foot", "basket"):
        return parts[1].strip().lower()
    return "basket"


def run(cmd=None, file_id=None):
    cmd = cmd if cmd is not None else (os.environ.get("CMD") or "")
    file_id = file_id if file_id is not None else (os.environ.get("WINNER_FILE_ID")
                                                   or os.environ.get("CAPTURE_FILE_ID") or "")
    sport = sport_of(cmd)
    if not file_id:
        return {"sport": sport, "ok": False, "holes": ["photo_absente"]}
    inbox = WORLD / "F01_SENTINEL" / "IN"
    inbox.mkdir(parents=True, exist_ok=True)
    inbox_capture.write_photo(inbox, file_id, prefix="winner_telegram")
    photos = sorted(inbox.glob("winner_telegram.*"))
    if not photos:
        return {"sport": sport, "ok": False, "holes": ["photo_introuvable"]}
    a, b, holes = llm_vision.read_capture_twice([str(p) for p in photos], sport)
    if not a and holes:
        return {"sport": sport, "ok": False, "holes": holes}
    blob = winner_vision.build(a, sport, text_b=b, extra_holes=holes)
    target = WORLD / "ARCHIVUM" / "winner" / ("slate_%s.json" % sport)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    view = winner_ingest.ingest(sport, path=str(target))
    winner_ingest.save(view, sport, path=str(target))
    return {"sport": sport, "ok": True, "path": str(target),
            "n_matchs": len(blob["matches"]), "holes": list(blob["holes"])}


def main():
    rec = run()
    print("[WINNER-TELEGRAM] " + json.dumps(
        {k: rec[k] for k in ("sport", "ok", "n_matchs", "holes")},
        ensure_ascii=False))
    return 0 if rec["ok"] or rec["holes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
