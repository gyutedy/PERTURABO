#!/usr/bin/env python3
"""
F00C_VOX — La Voix des Plateformes (YouTube / Twitch / local).
Sous-frégate de F00_CAPTEURS, aux côtés de F00A (scan de prospection)
et F00B (l'Oreille Absolue, chat Twitch).

La plateforme sait déjà ce qui est viral. F00C lit cette mémoire :
heatmap d'attention, segments viraux, données brutes — live EN COURS
ou vidéo FINIE, même pipeline, même manifeste, même schéma.

Origine : porté depuis LACRIMAE dev10-v3-live (f00_live.py, commit d1b182c,
8/8 tests verts) et adapté aux conventions F00B de PERTURABO.

Pipeline : resolve → metadata → (heat) → manifest [→ candidats canoniques]
Sortie : OUT/live_analysis.json — schéma `perturabo.voxc.v1` — prêt pour l'Oracle
         et le gate hybride (même chaîne de décision que F00B).
         Avec --to-candidats : OUT/candidats.json au schéma canonique PUR
         (clé `candidates`, signal_type=platform_heat) — pont vers le tronc.

Hérésies interdites :
❌ Jamais de téléchargement complet de VOD (--download-sections uniquement)
❌ Jamais de recompression (stream copy / merge mp4 natif)
❌ Jamais de manifeste vide : même en metadata_only, l'Oracle reçoit un livrable
❌ Jamais de dépendance réseau pour la heatmap (elle vit sur le fichier local)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:  # numpy sert à la heatmap ; sans lui : dégradation propre en metadata_only
    import numpy as np
except Exception:  # pragma: no cover - environnement sans numpy
    np = None


SCHEMA_VERSION = "perturabo.voxc.v1"

# ─── Paths (gabarit F00B) ────────────────────────────────────────────────────
CODEBASE_DIR = Path(__file__).resolve().parent
BASE = CODEBASE_DIR.parent          # F00C_VOX/
IN_DIR = BASE / "IN"
OUT_DIR = BASE / "OUT"
INGEST_DIR = BASE / "vox_ingest"
CLIPPING_ROOT = CODEBASE_DIR.parents[2]  # MONDES_FORGES/CLIPPING

sys.path.insert(0, str(CLIPPING_ROOT / "SHARED"))
try:
    from candidates_reader import viral_segments_to_candidates  # noqa: E402
except Exception:  # pragma: no cover - path fallback if SHARED is elsewhere
    viral_segments_to_candidates = None

try:  # cerveau partagé (premium → oracle → off) — jamais bloquant
    from brain import ask as _brain_ask, available_mode as _brain_mode  # noqa: E402
except Exception:  # pragma: no cover - cerveau indisponible : tri sémantique désactivé
    _brain_ask = None

    def _brain_mode():
        return "off"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ─────────────────────────────────────────────────────────────────────────────
# Résolution de source
# ─────────────────────────────────────────────────────────────────────────────

YOUTUBE_PATTERNS = (
    re.compile(r"youtu\.be/([\w-]{11})"),
    re.compile(r"youtube\.com/watch\?v=([\w-]{11})"),
    re.compile(r"youtube\.com/live/([\w-]{11})"),
    re.compile(r"youtube\.com/shorts/([\w-]{11})"),
    re.compile(r"youtube\.com/embed/([\w-]{11})"),
)
TWITCH_VOD_PATTERN = re.compile(r"twitch\.tv/videos/(\d+)")
TWITCH_CHANNEL_PATTERN = re.compile(r"twitch\.tv/([\w]{3,25})/?$")


def resolve_source(reference: str) -> dict:
    """Classifie la référence et retourne {kind, platform, ...}.

    kind : ``local`` | ``youtube_video`` | ``twitch_video`` | ``twitch_channel``
    """
    ref = (reference or "").strip()
    if not ref:
        raise ValueError("Référence de source vide (chemin local ou URL attendu)")
    candidate = Path(ref)
    if "://" not in ref:
        if candidate.exists() and candidate.is_file():
            return {"kind": "local", "platform": "local", "path": str(candidate), "id": candidate.stem}
        raise FileNotFoundError(f"Fichier introuvable : {ref}")
    lowered = ref.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        for pattern in YOUTUBE_PATTERNS:
            match = pattern.search(ref)
            if match:
                return {"kind": "youtube_video", "platform": "youtube", "id": match.group(1), "url": ref}
        raise ValueError(f"URL YouTube sans ID de vidéo exploitable : {ref}")
    if "twitch.tv" in lowered:
        vod = TWITCH_VOD_PATTERN.search(ref)
        if vod:
            return {"kind": "twitch_video", "platform": "twitch", "id": vod.group(1), "url": ref}
        channel = TWITCH_CHANNEL_PATTERN.search(ref)
        if channel:
            return {"kind": "twitch_channel", "platform": "twitch", "id": channel.group(1), "url": ref}
        raise ValueError(f"URL Twitch non reconnue : {ref}")
    raise ValueError(f"Plateforme non supportée par F00C_VOX : {ref}")


# ─────────────────────────────────────────────────────────────────────────────
# Métadonnées plateforme (sans clé API : pages publiques)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: float = 15.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        return response.read()


def fetch_youtube_metadata(video_id: str) -> dict:
    """Lit la page watch publique — suffit pour is_live, titre, durée, stats."""
    html = _http_get(f"https://www.youtube.com/watch?v={video_id}").decode("utf-8", "replace")
    meta: dict = {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
    match_title = re.search(r'<meta name="title" content="([^"]*)"', html)
    if match_title:
        meta["title"] = match_title.group(1)
    # ytInitialPlayerResponse contient videoDetails (l'ordre des clés est stable)
    player = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var\s|</script>)", html, re.S)
    if player:
        try:
            data = json.loads(player.group(1))
            details = data.get("videoDetails") or {}
            meta.setdefault("title", details.get("title"))
            meta["author"] = details.get("author")
            meta["duration_seconds"] = details.get("lengthSeconds")
            meta["view_count"] = details.get("viewCount")
            meta["is_live"] = bool(details.get("isLiveContent"))
            status = ((data.get("playabilityStatus") or {}).get("status") or "").upper()
            meta["playable"] = status == "OK"
        except json.JSONDecodeError:
            pass
    match_live = re.search(r'"isLive":\s*(true|false)', html) or re.search(
        r"itemprop=\"isLiveBroadcast\"\s+content=\"(True|False)\"", html
    )
    if match_live:
        raw = match_live.group(1)
        meta["is_live"] = raw in ("true", "True")
    meta.setdefault("is_live", False)
    meta.setdefault("playable", None)
    return meta


TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
TWITCH_GQL_CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"  # client_id web public


def fetch_twitch_metadata(kind: str, resource_id: str) -> dict:
    """Métadonnées publiques Twitch via GQL (client_id web public, sans OAuth)."""
    if kind == "twitch_video":
        payload = {
            "query": "query($id:ID!){user:video(id:$id){id title lengthSeconds viewCount "
                     "owner{login displayName} game{displayName} createdAt}}",
            "variables": {"id": resource_id},
        }
    else:
        payload = {
            "query": "query($login:String!){user(login:$login){login displayName "
                     "stream{id title viewersCount game{displayName} createdAt} "
                     "followers{totalCount}}}",
            "variables": {"login": resource_id},
        }
    request = urllib.request.Request(
        TWITCH_GQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Client-ID": TWITCH_GQL_CLIENT_ID, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310
        body = json.loads(response.read().decode("utf-8"))
    user = (body.get("data") or {}).get("user") or {}
    meta: dict = {"id": resource_id, "is_live": False}
    if kind == "twitch_video":
        meta.update({"title": user.get("title"), "duration_seconds": user.get("lengthSeconds"),
                     "view_count": user.get("viewCount"), "channel": (user.get("owner") or {}).get("login"),
                     "game": (user.get("game") or {}).get("displayName")})
    else:
        stream = user.get("stream") or {}
        meta.update({"title": stream.get("title") or user.get("displayName"),
                     "channel": user.get("login"),
                     "is_live": bool(stream), "viewers_count": stream.get("viewersCount"),
                     "game": (stream.get("game") or {}).get("displayName"),
                     "followers": (user.get("followers") or {}).get("totalCount")})
    return meta


# ─────────────────────────────────────────────────────────────────────────────
# Heatmap d'attention (fichier local) — équivalent de la barre rouge YouTube
# ─────────────────────────────────────────────────────────────────────────────

def compute_attention_heatmap(path: Path, buckets: int = 120) -> list[dict]:
    """Échantillonne la vidéo et produit une heatmap d'attention par bucket.

    Score par bucket = variation visuelle (mouvement) + contraste. Les pics
    marquent les moments forts — même sémantique que la barre rouge YouTube,
    mais calculée depuis la source pour rester disponible sur toute vidéo.
    """
    if np is None:
        raise RuntimeError("numpy indisponible : heatmap impossible")
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=duration,avg_frame_rate",
        "-of", "json", str(path),
    ]
    probe = json.loads(subprocess.check_output(probe_cmd, text=True))["streams"][0]
    duration = float(probe.get("duration") or 0)
    if duration <= 0:
        raise ValueError("Durée média inconnue : heatmap impossible")
    buckets = max(10, min(int(buckets), int(duration) or 1))
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path), "-vf",
        f"fps={max(1.0, buckets / duration):.4f},scale=64:36,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frame_bytes = 64 * 36
    scores: list[float] = []
    previous: "np.ndarray | None" = None
    assert proc.stdout is not None
    while True:
        raw = proc.stdout.read(frame_bytes)
        if len(raw) != frame_bytes:
            break
        frame = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255.0
        motion = float(0.0) if previous is None else float(np.abs(frame - previous).mean())
        scores.append(motion + float(frame.std()) * 0.5)
        previous = frame
    proc.wait()
    if not scores:
        raise RuntimeError("Aucune frame échantillonnée : ffmpeg a échoué")
    per_bucket = max(1, len(scores) // buckets)
    heatmap: list[dict] = []
    for index in range(buckets):
        chunk = scores[index * per_bucket:(index + 1) * per_bucket]
        if not chunk:
            chunk = [0.0]
        heatmap.append({
            "bucket": index,
            "start_sec": round(index * duration / buckets, 3),
            "end_sec": round((index + 1) * duration / buckets, 3),
            "attention": round(sum(chunk) / len(chunk), 6),
        })
    return _normalize_heatmap(heatmap)


def _normalize_heatmap(heatmap: list[dict]) -> list[dict]:
    max_attention = max((row["attention"] for row in heatmap), default=0.0) or 1.0
    for row in heatmap:
        row["attention_norm"] = round(row["attention"] / max_attention, 6)
    return heatmap


def top_viral_segments(heatmap: list[dict], count: int = 5, min_gap_seconds: float = 5.0) -> list[dict]:
    """Retourne les `count` pics d'attention espacés d'au moins min_gap_seconds."""
    ranked = sorted(heatmap, key=lambda row: row["attention"], reverse=True)
    picked: list[dict] = []
    for row in ranked:
        if all(abs(row["start_sec"] - other["start_sec"]) >= min_gap_seconds for other in picked):
            picked.append(row)
        if len(picked) >= count:
            break
    picked.sort(key=lambda row: row["start_sec"])
    return [{
        "start_sec": row["start_sec"],
        "end_sec": row["end_sec"],
        "attention_norm": row["attention_norm"],
        "rank": index + 1,
    } for index, row in enumerate(picked)]


# ─────────────────────────────────────────────────────────────────────────────
# Cerveau partagé — tri sémantique optionnel des segments (premium/oracle)
# ─────────────────────────────────────────────────────────────────────────────

BRAIN_SYSTEM = (
    "Tu es le tri sémantique de PERTURABO (F00C, plateformes). Pour chaque pic "
    "d'attention d'un stream, juge le POTENTIEL VIRAL court (hook, tension, "
    "payoff) sur 0..10. Réponds UNIQUEMENT en JSON : "
    "{\"score\": <0..10>, \"reason\": \"<8 mots max>\"}"
)


def load_transcript_words(path: Path | None) -> list:
    """Charge les mots d'un transcript.json (merge_transcripts) ; [] si absent."""
    if not path:
        return []
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return doc.get("words") or []


def _window_text(words: list, start: float, end: float, limit: int = 1200) -> str:
    chunk = [str(w.get("word", "")).strip() for w in words
             if start <= _as_float(w.get("start")) < end]
    return " ".join(chunk)[:limit].strip()


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def brain_rank_segments(segments: list, words: list, depth: int = 5,
                        timeout: float = 25.0) -> dict:
    """Score sémantique des `depth` meilleurs segments via le cerveau partagé.

    Retourne un bloc observable ``{mode, scores, note}`` :
      * ``off`` (aucune clé premium/oracle) → scores vides, note explicite ;
      * pas de transcript textuel → le tri plateforme reste seul juge ;
      * sinon → un score de reframing par segment (clé = start_sec).

    Ne mute JAMAIS les segments (le manifeste reste le contrat F00C intact).
    """
    mode = _brain_mode()
    if not segments:
        return {"mode": mode, "scores": [], "note": "aucun segment"}
    if _brain_ask is None or mode == "off":
        return {"mode": "off", "scores": [],
                "note": "cerveau indisponible (clés premium/oracle absentes)"}
    if not words:
        return {"mode": mode, "scores": [],
                "note": "pas de transcript textuel : tri sémantique ignoré"}
    ordered = sorted(segments, key=lambda s: _as_float(s.get("attention_norm")),
                     reverse=True)[:max(1, depth)]
    scores = []
    for seg in ordered:
        start = _as_float(seg.get("start_sec"))
        text = _window_text(words, start, _as_float(seg.get("end_sec")))
        if not text:
            continue
        res = _brain_ask(BRAIN_SYSTEM, f'Extrait: "{text}"', temperature=0.2,
                         max_tokens=60, expect_json=True, timeout=timeout)
        if res.get("status") != "ok":
            continue
        obj = res.get("content") or {}
        score = max(0.0, min(10.0, _as_float(obj.get("score"))))
        scores.append({
            "start_sec": start,
            "attention_norm": seg.get("attention_norm"),
            "brain_score": round(score, 2),
            "reason": str(obj.get("reason", ""))[:80],
        })
    return {"mode": mode, "scores": scores,
            "note": None if scores else "aucun score produit (texte vide)"}


# ─────────────────────────────────────────────────────────────────────────────
# Téléchargement média optionnel (yt-dlp) pour analyse locale d'une URL
# ─────────────────────────────────────────────────────────────────────────────

def download_media(url: str, out_dir: Path, max_duration_seconds: float = 0,
                   cookies_path: Path | None = None,
                   player_clients: str = "ios,mweb",
                   max_height: int = 144) -> Path | None:
    """Télécharge via yt-dlp si disponible. Retourne None sinon (metadata_only).

    Escalier anti-anti-bot (PLAN_SALLE_DE_GUERRE, Livraison A) :
      1. Essais ``player_client=ios,mweb`` (gratuits, parfois suffisants) ;
      2. Nouvel essai sans extractor-args (comportement yt-dlp courant) ;
      3. Si cookies fournis : essai avec session autorisée (--cookies).
    Sans succès : None → metadata_only — le garde-fou du CLI transforme
    ce cas en échec explicite (succès technique ≠ succès réel).

    Formats : video-only ``height<=max_height`` (défaut 144p) — la heatmap
    réduit à 64x36 et l'audio est inutile : le fichier pèse ~30-60 Mo/h au
    lieu de Go (doctrine : jamais de VOD complète).
    """
    if shutil.which("yt-dlp") is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = f"bv*[height<={max_height}]/b[height<={max_height}]/b"
    base = ["yt-dlp", "--no-playlist", "-q", "-f", fmt, "--no-part",
            "--merge-output-format", "mp4", "-o", str(out_dir / "%(id)s.%(ext)s")]
    cookie_args = ["--cookies", str(cookies_path)] if cookies_path and Path(cookies_path).is_file() else []
    attempts = [
        base + ["--extractor-args", f"youtube:player_client={player_clients}"] + cookie_args,
        base + cookie_args,
    ]
    if max_duration_seconds > 0:
        for attempt in attempts:
            attempt += ["--download-sections", f"*0-{int(max_duration_seconds)}"]
    for attempt in attempts:
        attempt.append(url)
        if subprocess.call(attempt) == 0:
            files = sorted(out_dir.glob("*.mp4"))
            if files:
                return files[-1]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Livraison B — barre rouge (Most Replayed), fusion, webhook Salle de Guerre
# ─────────────────────────────────────────────────────────────────────────────

FUSION_WEIGHTS = {"video": 0.6, "replayed": 0.4}


def _yt_dlp_json(url: str, cookies_path: Path | None = None,
                 player_clients: str = "ios,mweb") -> dict | None:
    """JSON yt-dlp (--dump-json : AUCUN média téléchargé) via l'escalier habituel."""
    if shutil.which("yt-dlp") is None:
        return None
    cookie_args = ["--cookies", str(cookies_path)] if cookies_path and Path(cookies_path).is_file() else []
    attempts = [
        ["yt-dlp", "--no-playlist", "--dump-json",
         "--extractor-args", f"youtube:player_client={player_clients}"] + cookie_args,
        ["yt-dlp", "--no-playlist", "--dump-json"] + cookie_args,
    ]
    for attempt in attempts:
        attempt.append(url)
        try:
            proc = subprocess.run(attempt, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout.strip().splitlines()[-1])
            except json.JSONDecodeError:
                continue
    return None


def fetch_replayed_curve(url: str, cookies_path: Path | None = None) -> tuple[list[dict], str | None]:
    """Barre rouge YouTube (Most Replayed) via yt-dlp --dump-json.

    La seule courbe d'attention basée sur le comportement RÉEL de millions de
    spectateurs. Retourne (curve, note) : curve = [{start, end, value}] (peut
    être vide), note = raison humaine si vide (jamais de silence).
    """
    data = _yt_dlp_json(url, cookies_path)
    if data is None:
        return [], ("yt-dlp n'a pas pu lire les métadonnées (anti-bot ou absent) "
                    "— barre rouge indisponible")
    raw = data.get("heatmap") or []
    curve = []
    for seg in raw:
        if not isinstance(seg, dict):
            continue
        try:
            curve.append({
                "start": round(float(seg.get("start_time", 0)), 3),
                "end": round(float(seg.get("end_time", 0)), 3),
                "value": round(float(seg.get("value", 0)), 6),
            })
        except (TypeError, ValueError):
            continue
    if not curve:
        return [], "pas de Most Replayed exposé (live en cours, vidéo trop récente ou non supportée)"
    return curve, None


def fuse_heatmaps(video_heatmap: list[dict], replayed_curve: list[dict],
                  weights: dict | None = None) -> list[dict]:
    """Fusionne le capteur F00C (heatmap vidéo) et le comportement humain réel (barre rouge).

    fused = w_video * attention_norm + w_replayed * replayed_norm, où
    replayed_norm = moyenne des segments Most Replayed chevauchant le bucket
    (normalisée au max de la courbe). Sans barre rouge : dégradation propre,
    fused_norm = attention_norm, replayed_applied = False.
    """
    weights = weights or FUSION_WEIGHTS
    fused: list[dict] = []
    if not replayed_curve:
        for row in video_heatmap:
            out = dict(row)
            out["fused_norm"] = out.get("attention_norm", 0.0)
            out["replayed_applied"] = False
            fused.append(out)
        return fused
    max_value = max((seg.get("value", 0.0) for seg in replayed_curve), default=0.0) or 1.0
    for row in video_heatmap:
        start, end = row.get("start_sec", 0.0), row.get("end_sec", 0.0)
        overlaps = [seg.get("value", 0.0) / max_value for seg in replayed_curve
                    if seg.get("start", 0.0) < end and seg.get("end", 0.0) > start]
        replayed_norm = (sum(overlaps) / len(overlaps)) if overlaps else 0.0
        fused_norm = (weights.get("video", 0.6) * row.get("attention_norm", 0.0)
                      + weights.get("replayed", 0.4) * replayed_norm)
        fused.append({**row,
                      "replayed_norm": round(replayed_norm, 6),
                      "fused_norm": round(fused_norm, 6),
                      "replayed_applied": True})
    return fused


def _fmt_clock(seconds: float | None) -> str:
    """453.84 → '7:34' ; 3661 → '1:01:01'. Labels lisibles pour la Salle de Guerre."""
    if seconds is None:
        return "?"
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_webhook_payload(manifest: dict, candidates: list[dict] | None = None,
                          run_id: str | None = None) -> dict:
    """Contrat Salle de Guerre (PLAN_SALLE_DE_GUERRE §4) : le Prince voit tout.

    V2 (audit 2026-09-13) : le dashboard ne doit plus jamais deviner.
    Chaque candidat part avec id/rank/score/labels/vs_mean/plateformes ; le run
    porte duration_total_sec, analyzed_duration_sec et coverage_pct — la durée
    analysée est vérifiable d'un coup d'œil (fini le doute « 8 min sur plus »).
    """
    source = manifest.get("source") or {}
    heat = manifest.get("attention_heatmap") or []
    analyzed = heat[-1].get("end_sec") if heat else None
    raw_meta = (manifest.get("raw_data") or {}).get("metadata_raw") or {}
    duration_total = raw_meta.get("duration") or analyzed
    atts = [float(b.get("attention_norm") or 0) for b in heat]
    mean_att = (sum(atts) / len(atts)) if atts else 0.0

    enriched: list[dict] = []
    for i, cand in enumerate(candidates or [], 1):
        item = dict(cand)
        item.setdefault("id", cand.get("candidate_id") or f"voxc-{i}")
        item.setdefault("rank", cand.get("rank") or i)
        score = cand.get("score")
        if score is None:
            score = round(float(cand.get("signal_intensity") or 0) * 100, 2)
        item.setdefault("score", score)
        item.setdefault("duration_sec", cand.get("duration_sec"))
        item.setdefault("start_label", _fmt_clock(cand.get("start_sec")))
        item.setdefault("end_label", _fmt_clock(cand.get("end_sec")))
        inten = float(cand.get("signal_intensity") or 0)
        item.setdefault("vs_mean_pct",
                        round((inten - mean_att) / mean_att * 100, 1) if mean_att else None)
        item.setdefault("platforms", ["shorts", "tiktok", "reels", "x"])
        enriched.append(item)

    coverage = None
    if analyzed and duration_total:
        coverage = round(float(analyzed) / float(duration_total) * 100, 1)

    return {
        "run_id": run_id or os.environ.get("GH_RUN_ID")
                  or f"f00c_{(manifest.get('generated_at') or '').replace(':', '')}",
        "siege_id": source.get("reference") or source.get("id") or "",
        "title": raw_meta.get("title"),
        "channel": raw_meta.get("channel") or raw_meta.get("uploader"),
        "mode": "live" if source.get("content_type") == "live_ongoing" else "vod",
        "status": manifest.get("status"),
        "source": source,
        "duration_total_sec": duration_total,
        "analyzed_duration_sec": analyzed,
        "coverage_pct": coverage,
        "mean_attention": round(mean_att, 4) if atts else None,
        "heatmap": heat,
        "replayed_curve": manifest.get("replayed_curve") or [],
        "replayed_note": manifest.get("replayed_note"),
        "fused_heatmap": manifest.get("fused_heatmap") or [],
        "candidates": enriched,
        "pushed_at": datetime.now(timezone.utc).isoformat(),
    }


def push_webhook(url: str, payload: dict, token: str | None = None,
                 timeout: float = 15.0) -> bool:
    """POST HTTPS vers la Salle de Guerre. Auth : en-tête X-Siege-Token."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "PERTURABO-F00C/1.1"}
    if token:
        headers["X-Siege-Token"] = token
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        return response.status in (200, 201, 202, 204)


# ─────────────────────────────────────────────────────────────────────────────
# Analyse unifiée
# ─────────────────────────────────────────────────────────────────────────────

def emit_candidats(manifest: dict, out_path: Path, top: int | None = None) -> dict:
    """Pont F00C → tronc PUR : viral_segments → schéma canonique {candidates: [...]}.

    Le manifeste reste inchangé (l'Oracle garde ses données brutes).
    """
    if viral_segments_to_candidates is None:
        raise RuntimeError("candidates_reader indisponible — SHARED/candidates_reader.py manquant")
    source = ""
    src = manifest.get("source") or {}
    if isinstance(src, dict):
        source = src.get("reference") or src.get("id") or ""
    doc = viral_segments_to_candidates(
        manifest.get("viral_segments") or [],
        generated_at=manifest.get("generated_at"),
        source=source,
        engine="f00c_vox",
        top=top,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def analyze(reference: str, out_path: Path, work_dir: Path | None = None,
            heatmap_buckets: int = 120, download_budget_seconds: float = 0,
            cookies_path: Path | None = None, media_source: str | None = None,
            fetch_replayed: bool = False, transcript_path: Path | None = None,
            use_brain: bool = True) -> dict:
    started = datetime.now(timezone.utc)
    work_dir = Path(work_dir or out_path.parent / "live_media")
    resolved = resolve_source(reference)
    kind = resolved["kind"]
    platform = resolved["platform"]

    metadata: dict = {}
    source_kind = "remote"
    if kind == "local":
        source_kind = "local"
        metadata = {"file": resolved["path"], "id": resolved["id"]}
    elif kind == "youtube_video":
        metadata = fetch_youtube_metadata(resolved["id"])
    elif kind in ("twitch_video", "twitch_channel"):
        metadata = fetch_twitch_metadata(kind, resolved["id"])
        metadata["url"] = resolved["url"]

    content_type = "video"
    if metadata.get("is_live"):
        content_type = "live_ongoing"

    replayed_curve: list[dict] = []
    replayed_note: str | None = None
    if fetch_replayed and platform == "youtube":
        replayed_curve, replayed_note = fetch_replayed_curve(resolved.get("url"), cookies_path)

    media_path: Path | None = Path(resolved["path"]) if kind == "local" else None
    if media_source:
        # Contrat découplé (Livraison A) : la source porte les métadonnées,
        # le média peut venir d'ailleurs (fichier local ou URL directe).
        media_resolved = resolve_source(media_source)
        if media_resolved["kind"] != "local":
            raise ValueError("--media-source doit être un fichier local ou une URL directe vers le média")
        media_path = Path(media_resolved["path"])
        metadata["media_source"] = media_source
    if media_path is None and download_budget_seconds > 0:
        media_path = download_media(resolved.get("url"), work_dir,
                                    download_budget_seconds, cookies_path)

    heatmap: list[dict] = []
    segments: list[dict] = []
    media_error = None
    if media_path is not None:
        try:
            heatmap = compute_attention_heatmap(media_path, heatmap_buckets)
            segments = top_viral_segments(heatmap)
        except Exception as exc:  # noqa: BLE001 - l'analyse média ne doit jamais bloquer le livrable
            media_error = str(exc)

    status = "full" if heatmap else ("metadata_only" if not media_error else "metadata_only_media_error")
    fused_heatmap = fuse_heatmaps(heatmap, replayed_curve)
    brain_block = {"mode": _brain_mode(), "scores": [], "note": "désactivé (--no-brain)"}
    if use_brain:
        brain_block = brain_rank_segments(segments, load_transcript_words(transcript_path))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": started.isoformat(),
        "status": status,
        "source": {
            "reference": reference,
            "kind": kind,
            "platform": platform,
            "content_type": content_type,
            "source_kind": source_kind,
            "id": resolved.get("id"),
        },
        "metadata": metadata,
        "attention_heatmap": heatmap,
        "replayed_curve": replayed_curve,
        "replayed_note": replayed_note,
        "fused_heatmap": fused_heatmap,
        "fusion_weights": FUSION_WEIGHTS,
        "viral_segments": segments,
        "raw_data": {
            "note": "Données brutes plateforme pour l'Oracle (aucune valeur calculée).",
            "metadata_raw": metadata,
        },
        "media_error": media_error,
        "brain": brain_block,
        "pipeline": {
            "name": "F00C_VOX",
            "version": "1.0.0",
            "same_branch_preview": True,  # décision v3 : live ET vidéo finie, même manifeste
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F00C_VOX — analyse live/vidéo YouTube-Twitch-local")
    parser.add_argument("source", help="URL YouTube/Twitch ou chemin local")
    parser.add_argument("--out", default=str(OUT_DIR / "live_analysis.json"))
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--heatmap-buckets", type=int, default=120)
    parser.add_argument("--download-budget-seconds", type=float, default=0,
                        help="Si > 0, tente yt-dlp pour analyser le média localement")
    parser.add_argument("--cookies-file", default=None,
                        help="Fichier cookies Netscape d'une session autorisée (yt-dlp --cookies)")
    parser.add_argument("--media-source", default=None,
                        help="Média séparé de la source : chemin local ou URL directe (métadonnées = source)")
    parser.add_argument("--fetch-replayed", action="store_true",
                        help="Récupérer la barre rouge YouTube (Most Replayed via yt-dlp --dump-json)")
    parser.add_argument("--transcript", default=None,
                        help="transcript.json (words) pour le tri sémantique du cerveau partagé")
    parser.add_argument("--no-brain", action="store_true",
                        help="Désactiver le cerveau partagé (tri plateforme seul)")
    parser.add_argument("--webhook-url", default=None,
                        help="URL du webhook Salle de Guerre (POST du payload complet)")
    parser.add_argument("--webhook-token", default=None,
                        help="Token X-Siege-Token (défaut : env SIEGE_WEBHOOK_TOKEN)")
    parser.add_argument("--to-candidats", action="store_true",
                        help="Émet OUT/candidats.json au schéma canonique PUR (pont vers le tronc)")
    parser.add_argument("--candidats-out", default=str(OUT_DIR / "candidats.json"),
                        help="Chemin du candidats.json (avec --to-candidats)")
    parser.add_argument("--top", type=int, default=0,
                        help="Limiter aux N meilleurs segments (0 = tous)")
    args = parser.parse_args(argv)
    try:
        manifest = analyze(
            args.source, Path(args.out), Path(args.work_dir) if args.work_dir else None,
            args.heatmap_buckets, args.download_budget_seconds,
            cookies_path=Path(args.cookies_file) if args.cookies_file else None,
            media_source=args.media_source,
            fetch_replayed=args.fetch_replayed,
            transcript_path=Path(args.transcript) if args.transcript else None,
            use_brain=not args.no_brain,
        )
        summary = {"status": manifest["status"], "out": str(args.out)}
        if args.to_candidats:
            top = args.top if args.top and args.top > 0 else None
            doc = emit_candidats(manifest, Path(args.candidats_out), top=top)
            summary["candidats"] = str(args.candidats_out)
            summary["n_candidates"] = len(doc.get("candidates") or [])
            if summary["n_candidates"] == 0:
                print(
                    "F00C_VOX: WARNING — 0 candidat (heatmap absente ou plate). "
                    "Relancer avec --download-budget-seconds > 0. Pas de silence : le fichier est vide.",
                    file=sys.stderr,
                )
    except (ValueError, FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"F00C_VOX: erreur — {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    if args.webhook_url:
        payload = build_webhook_payload(
            manifest,
            candidates=(doc.get("candidates") or []) if args.to_candidats else [],
        )
        token = args.webhook_token or os.environ.get("SIEGE_WEBHOOK_TOKEN")
        try:
            pushed = push_webhook(args.webhook_url, payload, token)
            summary["webhook"] = "pushed" if pushed else "push_failed"
            print(f"F00C_VOX: SALLE DE GUERRE — {summary['webhook']}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - le webhook ne doit jamais bloquer le livrable
            summary["webhook"] = f"push_failed: {exc}"
            print(f"F00C_VOX: webhook échec — {exc} (le manifeste local reste le livrable)", file=sys.stderr)
    if args.download_budget_seconds > 0:
        guard_problems = []
        if not args.media_source and manifest["status"] != "full":
            guard_problems.append(
                f"budget > 0 mais status={manifest['status']} — média non obtenu "
                "(anti-bot YouTube) : fournir YT_COOKIES_BASE64 ou --media-source."
            )
        if args.to_candidats and summary.get("n_candidates", 0) == 0:
            guard_problems.append("budget > 0 mais 0 candidat produit (heatmap absente ou plate).")
        if guard_problems:
            for problem in guard_problems:
                print(f"F00C_VOX: GUARD-FAIL — {problem}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
