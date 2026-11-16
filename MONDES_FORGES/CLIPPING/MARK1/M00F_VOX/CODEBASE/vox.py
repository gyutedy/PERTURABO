"""M00F_VOX -- la voix : transcription d'un segment (EXC-2).

CONVENTION DE LA FORGE, QUE CE MODULE RESPECTE
    Le service de transcription est un endpoint OpenAI-compatible
    /audio/transcriptions exposé par Modal. Son URL ne vit PAS dans une
    variable d'environnement : elle est rangée dans
        CONTRACTS/f00b_secrets.json  ->  champ "base_url"
    fichier généré par le workflow .github/workflows/perturabo_transcribe.yml.
    Ce module lit CE fichier, comme le fait déjà F00B_VOX. Pas de seconde
    convention.

CE QUE LE SERVICE ATTEND (multipart/form-data)
    file      : le fichier audio du segment
    language  : "en", "fr", ...
    offset    : décalage du segment dans la VOD (secondes)

CE QU'IL REND
    {"words": [{word,start,end}...], "text": "..."}

CE QU'IL NE FAIT PAS
    Aucun ffmpeg, aucun découpage, aucun MP4. Si le service est absent, on
    rend une raison explicite : jamais d'exception qui tue le siège.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid

_RETRY_CODES = {408, 429, 500, 502, 503, 504}


def probe_duration(path):
    """Durée en secondes via ffprobe. None si ffprobe absent ou échec.

    ffprobe lit une durée, il ne produit rien : c'est le bornage d'EXC-2.
    """
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


def _secrets(cfg, root):
    """Lit CONTRACTS/f00b_secrets.json. Repli sur les variables d'env."""
    vox = cfg.get("vox") or {}
    rel = vox.get("secrets_path", "../CONTRACTS/f00b_secrets.json")
    path = os.path.normpath(os.path.join(root, rel))

    conf = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                conf = json.load(fh)
        except ValueError:
            conf = {}

    url = conf.get("base_url") or os.environ.get(vox.get("modal_url_env", "MODAL_URL"), "")
    token = os.environ.get(conf.get("env_var_name") or "MODAL_TOKEN_ID", "") \
        or os.environ.get("MODAL_TOKEN_ID", "")
    return {
        "url": (url or "").rstrip("/"),
        "token": token,
        "language": conf.get("language") or cfg.get("default_language", "en"),
        "piece_sec": int(vox.get("piece_sec", 480)),
        "timeout": int(vox.get("request_timeout", 900)),
        "secrets_path": path,
        "secrets_found": bool(url),
    }


def _multipart(fields, files):
    """Construit un corps multipart/form-data sans dépendance externe."""
    boundary = "----mark1" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(("--%s\r\n" % boundary).encode("utf-8"))
        parts.append(('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode("utf-8"))
        parts.append(str(value).encode("utf-8") + b"\r\n")
    for name, filename, content in files:
        parts.append(("--%s\r\n" % boundary).encode("utf-8"))
        parts.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                      % (name, filename)).encode("utf-8"))
        parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
        parts.append(content + b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def transcribe(audio_path, cfg, root=".", language=None, offset=0.0, retries=3):
    """Transcrit un fichier audio. Rend (texte, raison).

    raison vide == succès.
    """
    c = _secrets(cfg, root)
    if not c["url"]:
        return "", ("base_url absent de %s : deploie le service Modal "
                    "(workflow perturabo_transcribe) pour l'obtenir" % c["secrets_path"])
    if not os.path.exists(audio_path):
        return "", "fichier absent : %s" % audio_path

    # taille : le service refuse au-dela de max_audio_mb
    try:
        with open(c["secrets_path"], "r", encoding="utf-8") as fh:
            max_mb = float(json.load(fh).get("max_audio_mb") or 24)
    except (OSError, ValueError):
        max_mb = 24.0
    size_mb = os.path.getsize(audio_path) / (1024.0 * 1024.0)
    if size_mb > max_mb:
        return "", "segment %.1f Mo > %.0f Mo : decoupage requis (hors MARK1)" % (size_mb, max_mb)

    with open(audio_path, "rb") as fh:
        content = fh.read()
    fields = {"language": language or c["language"], "offset": "%.3f" % float(offset or 0.0)}
    body, ctype = _multipart(fields, [("file", os.path.basename(audio_path), content)])

    headers = {"Content-Type": ctype}
    if c["token"]:
        headers["Authorization"] = "Bearer " + c["token"]

    last = ""
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(c["url"] + "/audio/transcriptions",
                                     data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=c["timeout"]) as resp:
                data = json.load(resp)
            text = (data.get("text") or "").strip()
            if text:
                return text, ""
            words = data.get("words") or []
            if words:
                return " ".join(w.get("word", "") for w in words).strip(), ""
            return "", "reponse sans texte du service"
        except urllib.error.HTTPError as e:
            last = "HTTP %s" % e.code
            if e.code not in _RETRY_CODES:
                break
        except Exception as e:
            last = type(e).__name__

        if attempt + 1 < max(1, retries):
            time.sleep(2 ** attempt)

    return "", "echec transcription : %s" % last


def transcribe_segment(segment, cfg, root="."):
    """Transcrit un segment du pack.

    Ordre de priorité :
      1. transcript déjà fourni  -> on le garde (option B : fourni en amont)
      2. source_text fourni      -> rien à transcrire, la porte M5 le tolère
      3. audio_path fourni       -> appel au service
    Rend {asset_id, transcript, reason}.
    """
    aid = segment.get("id")

    if segment.get("transcript"):
        return {"asset_id": aid, "transcript": segment["transcript"], "reason": ""}

    if segment.get("source_text"):
        return {"asset_id": aid, "transcript": "",
                "reason": "aucun audio fourni (source_text du pack utilise)"}

    audio = segment.get("audio_path") or ""
    if not audio:
        return {"asset_id": aid, "transcript": "",
                "reason": "ni audio ni source_text : rien a transcrire"}

    dur = probe_duration(audio)
    if dur is not None:
        limit = _secrets(cfg, root)["piece_sec"]
        if dur > limit:
            return {"asset_id": aid, "transcript": "",
                    "reason": "segment %.0fs > %ds : decoupage requis (hors MARK1)"
                              % (dur, limit)}

    text, reason = transcribe(audio, cfg, root, offset=segment.get("start_sec") or 0.0)
    return {"asset_id": aid, "transcript": text, "reason": reason}
