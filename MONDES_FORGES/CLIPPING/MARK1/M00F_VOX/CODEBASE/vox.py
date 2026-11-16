"""M00F_VOX -- la voix : transcription du segment (EXC-2).

EXC-2 : ce module est le SEUL de MARK1 autorise a appeler ffprobe et le
service de transcription. Le bornage est strict :
  - ffprobe sert uniquement a lire la duree d'un fichier local ;
  - le service Modal (faster-whisper) sert uniquement a transcrire ;
  - aucun autre module de MARK1 ne fait de reseau ni de ffprobe.

CE QUE LA FORGE F00B_VOX FAISAIT, et que l'on copie
    POST <MODAL_URL> avec l'audio du segment, retries sur 408/429/5xx.
    On ne l'appelle jamais : on reprend la logique (doctrine du plan).

CE QU'IL NE FAIT PAS
    Pas de ffmpeg (aucun decoupage, aucun MP4). Pas de montage. Si le service
    est absent, on rend une transcription vide et une raison explicite.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

_RETRY_CODES = {408, 429, 500, 502, 503, 504}


def probe_duration(path):
    """Duree en secondes via ffprobe. Rend None si ffprobe absent ou echec."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def _config(cfg):
    v = cfg.get("vox") or {}
    return {
        "url": os.environ.get(v.get("modal_url_env", "MODAL_URL"), ""),
        "token_id": os.environ.get(v.get("modal_token_env", "MODAL_TOKEN_ID"), ""),
        "piece_sec": int(v.get("piece_sec", 480)),
        "timeout": int(v.get("request_timeout", 900)),
    }


def transcribe(audio_path, cfg, retries=3):
    """Transcrit un fichier audio via le service Modal. Rend (texte, raison)."""
    c = _config(cfg)
    if not c["url"]:
        return "", "service de transcription non configure (MODAL_URL absent)"
    if not os.path.exists(audio_path):
        return "", "fichier absent : %s" % audio_path

    with open(audio_path, "rb") as fh:
        payload = json.dumps({"audio_b64": base64.b64encode(fh.read()).decode("ascii")}).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if c["token_id"]:
        headers["Authorization"] = "Bearer " + c["token_id"]

    last = ""
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(c["url"], data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=c["timeout"]) as resp:
                data = json.load(resp)
            text = data.get("text") or data.get("transcript") or ""
            if text:
                return text.strip(), ""
            return "", "reponse vide du service"
        except urllib.error.HTTPError as e:
            last = "HTTP %s" % e.code
            if e.code not in _RETRY_CODES:
                break
        except Exception as e:  # reseau, timeout
            last = type(e).__name__

        if attempt + 1 < max(1, retries):
            time.sleep(2 ** attempt)

    return "", "echec transcription : %s" % last


def transcribe_segment(segment, cfg):
    """Transcrit un segment si le pack fournit un chemin audio.

    Rend {asset_id, transcript, reason}. Un transcript vide n'est pas une
    erreur fatale : le pack peut deja porter source_text.
    """
    aid = segment.get("id")
    audio = segment.get("audio_path") or ""
    if segment.get("transcript"):
        return {"asset_id": aid, "transcript": segment["transcript"], "reason": ""}
    if segment.get("source_text"):
        return {"asset_id": aid, "transcript": "",
                "reason": "aucun audio fourni (source_text du pack utilise)"}
    if not audio:
        return {"asset_id": aid, "transcript": "",
                "reason": "ni audio ni source_text : rien a transcrire"}

    dur = probe_duration(audio)
    if dur is not None:
        limit = _config(cfg)["piece_sec"]
        if dur > limit:
            return {"asset_id": aid, "transcript": "",
                    "reason": "segment %.0fs > %ds : decoupage requis (hors MARK1)" % (dur, limit)}

    text, reason = transcribe(audio, cfg)
    return {"asset_id": aid, "transcript": text, "reason": reason}
