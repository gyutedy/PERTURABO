#!/usr/bin/env python3
"""
CAPTURE LLM — photo Winner -> LLM vision -> tableau Winner -> input_capture.
============================================================================
Fusion de /capture et du lecteur LLM : une seule photo suffit. Ecrit
F01_SENTINEL/IN/capture_telegram.md (plus recent que la photo, donc choisi
par resolve_capture). Si le LLM echoue, aucun fichier n'est ecrit : l'OCR
reste le repli. Aucune cote inventee, aucun ticket, aucun pari automatique.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1]
for d in ("F01_SENTINEL", "F00_RADAR", "F03_FORGEWARD", "ORCHESTRATOR"):
    p = WORLD / d / "CODEBASE"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
sys.path.insert(0, str(HERE))

import inbox_capture  # noqa: E402
import llm_vision  # noqa: E402
import winner_vision  # noqa: E402


def sport_of(cmd):
    parts = (cmd or "").split()
    if len(parts) > 1 and parts[1].strip().lower() in ("foot", "basket"):
        return parts[1].strip().lower()
    state = WORLD / "ARCHIVUM" / "state" / "sport_actif.json"
    try:
        sport = json.loads(state.read_text(encoding="utf-8")).get("sport")
        if sport in ("foot", "basket"):
            return sport
    except (OSError, json.JSONDecodeError):
        pass
    return "foot"


def _day(raw):
    low = str(raw or "").lower()
    if "tomorrow" in low or "demain" in low:
        return "Demain"
    return "Aujourd'hui"


def markdown(slate, sport):
    """Slate v1 -> tableau Winner que input_capture sait parser."""
    if sport == "basket":
        head = ("| Compétition & Match | Horaire | 1 (ML) | 2 (ML) | 1 | X | 2 | Handicap | Total |\n"
                "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    else:
        lignes = []
        groupes = {}
        for m in slate.get("matches") or []:
            ligne = (m.get("odds") or {}).get("total_line")
            cle = str(ligne).replace(",", ".") if ligne is not None else None
            groupes.setdefault(cle, []).append(m)
        for cle, matchs in groupes.items():
            suff = (" %s" % cle) if cle else ""
            lignes.append(
                "| Compétition & Match | Horaire | 1 | X | 2 | Moins%s | Plus%s | 1st | Égal | 2nd |\n"
                "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
                % (suff, suff))
            for m in matchs:
                o = m.get("odds") or {}
                when = "%s %s" % (_day(m.get("kickoff_raw")), m.get("kickoff") or "")
                ident = m.get("source_event_id") or ""
                hour = "%s (#%s)" % (when, ident) if ident else when
                cell = "Winner FOOT<br>%s vs %s" % (m.get("home"), m.get("away"))
                cells = [cell, hour, str(o.get("home") or ""), str(o.get("draw") or ""),
                         str(o.get("away") or ""), str(o.get("under_2_5") or ""),
                         str(o.get("over_2_5") or ""), str(o.get("hsh_first") or ""),
                         str(o.get("hsh_equal") or ""), str(o.get("hsh_second") or "")]
                lignes.append("| " + " | ".join(cells) + " |")
        return "\n".join(lignes) + "\n"
    lignes = [head]
    for m in slate.get("matches") or []:
        o = m.get("odds") or {}
        when = "%s %s" % (_day(m.get("kickoff_raw")), m.get("kickoff") or "")
        ident = m.get("source_event_id") or ""
        cell = "Winner %s<br>%s vs %s" % (sport.upper(), m.get("home"), m.get("away"))
        hour = "%s (#%s)" % (when, ident) if ident else when
        if sport == "basket":
            cells = [cell, hour, str(o.get("ml_1") or ""), str(o.get("ml_2") or ""),
                     "", "", "", "", str(o.get("total_line") or "")]
        else:
            cells = [cell, hour, str(o.get("home") or ""), str(o.get("draw") or ""),
                     str(o.get("away") or ""), str(o.get("under_2_5") or ""),
                     str(o.get("over_2_5") or ""), str(o.get("hsh_first") or ""),
                     str(o.get("hsh_equal") or ""), str(o.get("hsh_second") or "")]
        lignes.append("| " + " | ".join(cells) + " |")
    return "\n".join(lignes) + "\n"


def run(cmd=None, file_id=None, images=None):
    cmd = cmd if cmd is not None else (os.environ.get("CMD") or "")
    file_id = file_id if file_id is not None else (os.environ.get("CAPTURE_FILE_ID")
                                                   or os.environ.get("WINNER_FILE_ID") or "")
    sport = sport_of(cmd)
    inbox = WORLD / "F01_SENTINEL" / "IN"
    inbox.mkdir(parents=True, exist_ok=True)
    photos = list(images or [])
    if not photos and file_id:
        inbox_capture.write_photo(inbox, file_id, prefix="winner_telegram")
        photos = [str(p) for p in sorted(inbox.glob("winner_telegram.*"))]
    if not photos:
        return {"sport": sport, "ok": False, "holes": ["photo_absente"]}
    a, b, holes = llm_vision.read_capture_twice(photos, sport)
    if not a and holes:
        return {"sport": sport, "ok": False, "holes": holes}
    slate = winner_vision.build(a, sport, text_b=b, extra_holes=holes)
    if not slate.get("matches"):
        return {"sport": sport, "ok": False, "holes": ["aucun_match_llm"]}
    if len(parts := (cmd or "").split()) > 1 and parts[1].strip().lower() in ("foot", "basket"):
        state = WORLD / "ARCHIVUM" / "state" / "sport_actif.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"sport": parts[1].strip().lower()}), encoding="utf-8")
    target = inbox / "capture_telegram.md"
    target.write_text(markdown(slate, sport), encoding="utf-8")
    return {"sport": sport, "ok": True, "path": str(target),
            "n_matchs": len(slate["matches"]), "holes": list(slate["holes"])}


def main():
    rec = run()
    print("[CAPTURE-LLM] " + json.dumps(
        {k: rec[k] for k in ("sport", "ok", "n_matchs", "holes")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
