#!/usr/bin/env python3
"""
pur_montage_pipeline.py — Pipeline de montage PUR (VOX + F04 -> pack complet)
============================================================================
Flux (Mode PUR) : F00B_VOX (candidats) + F04 (overlay) -> F06_DIRECTOR -> pack complet.

En Mode PUR le flux va directement de VOX (deja detecte/score/selectionne) au
copywriting F04 (deja genere/valide). Cette frégate recolle LE MONTAGE VIRAL :
chaque pack contient TOUT (source + segment + copywriting + instructions de
montage + anti-detection) dans le bloc "montage_instructions" — c'est exactement
ce qu'OMNIS_WATCH consomme pour le rendu. Plus de fichier separe perdu.

Sorties (git-trackees car OUT/ est gitignored) :
  ARCHIVUM/montage/packs/production_pack_<angle>.json
  ARCHIVUM/montage/packs/montage_pack_index.json

Usage :
  python pur_montage_pipeline.py --candidats <...> --vod <url> --nb-videos 3 --asset-mode overlay_only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "SHARED"))
from candidates_reader import CandidatesReadError, load_candidates_document  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))  # MONDES_FORGES/CLIPPING
sys.path.insert(0, os.path.join(HERE, "F06_DIRECTOR", "CODEBASE"))
from director import generate_montage_instructions  # noqa: E402

F04_OUT = os.path.join(HERE, "F04_COPYWRITER", "OUT")
PACKS_DIR = os.path.join(HERE, "ARCHIVUM", "montage", "packs")
COPYWRITING_DIR = os.path.join(HERE, "ARCHIVUM", "copywriting")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _angle_id(idx):
    return "A%02d" % (idx + 1)


def _derive_transcript_path(candidats_path):
    for suffix in ("_candidats_selected.json", "_candidats.json"):
        if candidats_path.endswith(suffix):
            return candidats_path[: -len(suffix)] + "_transcript.json"
    base, _ext = os.path.splitext(candidats_path)
    return base + "_transcript.json"


def _word_window(all_words, start_sec, end_sec):
    out = []
    for w in all_words:
        try:
            s = float(w["start"]); e = float(w.get("end", s))
        except (KeyError, TypeError, ValueError):
            continue
        if s >= start_sec and e <= end_sec:
            out.append({"word": w.get("word", ""), "start": round(s - start_sec, 2),
                        "end": round(e - start_sec, 2)})
    return out


def load_overlay(angle_id):
    """Charge l'overlay F04 (F04_OUT en runtime, sinon ARCHIVUM/copywriting commité)."""
    for p in [
        os.path.join(F04_OUT, "overlay_payload_%s.json" % angle_id),
        os.path.join(COPYWRITING_DIR, "overlay_payload_%s.json" % angle_id),
    ]:
        if os.path.exists(p):
            return load_json(p)
    return {}


def build_pack(cand, overlay, angle_id, idx, total, camp_id, vod, platform, market, mode,
               word_timings=()):
    text_payload = overlay or {
        "overlay_title": " ".join((cand.get("top_words") or "").split()[:8]),
        "overlay_lines": 2,
        "rationale": "",
    }
    segment = {
        "id": cand.get("candidate_id") or angle_id,
        "angle_id": angle_id,
        "vod_url": vod,
        "start_sec": cand.get("start_sec"),
        "end_sec": cand.get("end_sec"),
        "duration_sec": cand.get("duration_sec"),
        "signal_type": cand.get("signal_type", "mixed"),
        "signal_intensity": cand.get("signal_intensity", 0.5),
        "top_words": cand.get("top_words", ""),
        "word_timings": word_timings,
    }
    context = {"campaign_id": camp_id, "angle_id": angle_id,
               "platform": platform, "market": market, "mode": "pur"}
    montage = generate_montage_instructions(segment, text_payload, context)
    return {
        "pack_id": "%s-%s" % (camp_id or "PUR", angle_id),
        "generated_at": _now_iso(),
        "mode": "pur",
        "asset_mode": mode,
        "identite": {"campaign_id": camp_id, "angle_id": angle_id,
                     "pack_index": idx, "pack_total": total},
        "cibles": {"target_platform": platform, "target_market": market},
        "source": {
            "vod_url": vod,
            "start_sec": cand.get("start_sec"), "end_sec": cand.get("end_sec"),
            "duration_sec": cand.get("duration_sec"),
            "signal_type": cand.get("signal_type"),
            "signal_intensity": cand.get("signal_intensity"),
            "source_permission": "campaign_provided",
        },
        "copywriting": {
            "overlay_title": text_payload.get("overlay_title", ""),
            "overlay_lines": text_payload.get("overlay_lines", 2),
            "rationale": text_payload.get("rationale", ""),
        },
        "montage_instructions": montage,
        "compliance": {"disclosure": "#ad", "submit_deadline_min": 60,
                       "anti_detection_applied": True},
    }


def main():
    ap = argparse.ArgumentParser(description="Pipeline montage PUR (VOX + F04 -> pack complet)")
    ap.add_argument("--candidats", required=True)
    ap.add_argument("--vod", required=True)
    ap.add_argument("--platform", default="youtube_shorts")
    ap.add_argument("--market", default="us_young_english")
    ap.add_argument("--nb-videos", type=int, default=1)
    ap.add_argument("--asset-mode", default="overlay_only")
    ap.add_argument("--transcript", default=None)
    args = ap.parse_args()

    nb = max(1, min(10, int(args.nb_videos or 1)))
    try:
        cands = load_candidates_document(args.candidats)
    except CandidatesReadError as exc:
        print("[PUR_MONTAGE] ERREUR: {}".format(exc), file=sys.stderr)
        sys.exit(1)
    transcript_path = args.transcript or _derive_transcript_path(args.candidats)
    transcript_words = []
    if transcript_path and os.path.exists(transcript_path):
        transcript_words = load_json(transcript_path).get("words") or []
    else:
        print("[PUR_MONTAGE] ATTENTION: transcript introuvable (%s) — captions mot-à-mot vides"
              % transcript_path, file=sys.stderr)
    camp_id = cands.get("campaign_id") or cands.get("campaign") or "pur"
    candidates = cands.get("candidates", [])
    candidates = candidates[:nb]

    packs = []
    for i, c in enumerate(candidates):
        aid = _angle_id(i)
        overlay = load_overlay(aid)
        wt = _word_window(transcript_words, c.get("start_sec") or 0, c.get("end_sec") or 0)
        pack = build_pack(c, overlay, aid, i + 1, len(candidates),
                          camp_id, args.vod, args.platform, args.market, args.asset_mode,
                          word_timings=wt)
        out_p = os.path.join(PACKS_DIR, "production_pack_%s.json" % aid)
        save_json(out_p, pack)
        packs.append({"angle_id": aid, "file": os.path.basename(out_p)})
        m = pack["montage_instructions"]
        print("[PUR_MONTAGE] %s : emotion=%s cuts=%d zooms=%d anti_detection=%d -> %s"
              % (aid, m["segment"]["emotion"], len(m["body"]["cuts"]),
                 len(m["body"]["zooms"]), len(m["anti_detection"]["techniques"]),
                 os.path.basename(out_p)))

    save_json(os.path.join(PACKS_DIR, "montage_pack_index.json"), {
        "campaign_id": camp_id, "mode": "pur", "asset_mode": args.asset_mode,
        "pack_count": len(packs), "generated_at": _now_iso(), "packs": packs,
    })
    print("[PUR_MONTAGE] index -> montage_pack_index.json (%d packs)" % len(packs))


if __name__ == "__main__":
    main()
