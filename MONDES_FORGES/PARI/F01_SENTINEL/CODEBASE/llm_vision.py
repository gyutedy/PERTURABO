#!/usr/bin/env python3
"""
LLM VISION — lecture GENERIQUE d'une capture Winner (stdlib uniquement).
=======================================================================
Fournisseur OpenAI-compatible : base_url + model + cle lus dans env_pari
(PARI_WINNER_LLM_BASE_URL / _MODEL / _KEY). Jamais de cle dans le code,
jamais de cle dans un log, jamais dans les GitHub Secrets.

Le LLM est un LECTEUR : il recopie des cotes visibles sur l'image. Il ne
calcule aucune probabilite, ne donne aucun verdict, n'invente aucune cote.
Deux lectures independantes sont faites ; la garde V1 de winner_vision
compare les resultats et declare un trou si elles divergent.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
KEY_VAR = "PARI_WINNER_LLM_KEY"
URL_VAR = "PARI_WINNER_LLM_BASE_URL"
MODEL_VAR = "PARI_WINNER_LLM_MODEL"


def load_env():
    """Charge env_pari / .env sans ecraser l'environnement existant."""
    for name in (".env", "env_pari"):
        path = os.path.join(WORLD, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k.strip() and v.strip() and not os.environ.get(k.strip()):
                        os.environ[k.strip()] = v.strip()
        except OSError:
            pass


def config():
    """(base_url, model, key, holes). Les valeurs ne sont jamais journalisees."""
    load_env()
    url = (os.environ.get(URL_VAR) or "").strip().rstrip("/")
    model = (os.environ.get(MODEL_VAR) or "").strip()
    key = (os.environ.get(KEY_VAR) or "").strip()
    holes = []
    if not key:
        holes.append("llm_key_absent")
    if not url:
        holes.append("llm_url_absent")
    if not model:
        holes.append("llm_model_absent")
    return url, model, key, holes


def _system_prompt(sport, passage):
    if sport == "basket":
        fmt = ("Atlanta Hawks - Detroit Pistons\n"
               "Today 21:30 | #20064\n"
               "ML 2.08/1.73\n"
               "Total 226.5\n"
               "Under 1.80 / Over 1.87")
        cols = "ML (2 cotes), Total (ligne), Under/Over (2 cotes)"
    else:
        fmt = ("Erzurumspor FK - Goztepe Izmir\n"
               "Today 11:30 | #401\n"
               "1X2 2.57/3.00/2.57\n"
               "2.5: 1.60/2.15\n"
               "HSH 3.10/3.00/2.02")
        cols = "1X2 (3 cotes), 2.5 Under/Over, HSH (3 cotes)"
    return (
        "Tu es un lecteur de capture d'ecran d'un site de paris. "
        "Transcris EXACTEMENT les cotes visibles, sans calcul, sans correction, "
        "sans invention. Si une valeur est illisible, omets la ligne ou ecris '?'. "
        "Reproduis TOUS les matchs visibles, meme s'il y en a plus de 10. "
        "Sur la premiere ligne de CHAQUE bloc, ecris TOUJOURS les deux equipes "
        "separees par un tiret entoure d'espaces (ex: 'Team A - Team B'), "
        "sinon le parseur ne peut pas les separer. "
        "L'en-tete de colonnes n'apparait qu'une fois en haut de l'image : "
        "il s'applique a TOUS les matchs suivants. "
        f"Pour le sport {sport}, ecris un bloc par match avec {cols}, "
        "en separant les matchs par une ligne vide, exactement comme ceci :\n"
        + fmt + "\n"
        "Reponds uniquement avec ces blocs, sans commentaire. "
        f"Passage {passage} : lecture independante, ne devine rien."
    )


def _image_part(path):
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    suffix = Path(path).suffix.lower().replace(".jpg", ".jpeg") or ".png"
    return {"type": "image_url", "image_url": {"url": f"data:image/{suffix[1:]};base64,{data}"}}


def read_capture(paths, sport="basket", passage=1):
    """(texte transcrit, trous). Aucune exception remontee a l'appelant."""
    url, model, key, holes = config()
    if holes:
        return "", holes
    images = [p for p in (paths or []) if p and os.path.exists(p)]
    if not images:
        return "", ["capture_absente"]
    content = [{"type": "text", "text": "Transcris cette capture (" + sport + ")." }]
    content.extend(_image_part(p) for p in images)
    body = {
        "model": model,
        "temperature": 0.0 if passage == 1 else 0.2,
        "messages": [
            {"role": "system", "content": _system_prompt(sport, passage)},
            {"role": "user", "content": content},
        ],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url + "/chat/completions", data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return "", ["llm_http:" + type(exc).__name__]
    try:
        text = raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return "", ["llm_reponse_inattendue"]
    if not text.strip():
        return "", ["llm_vide"]
    return text, []


def read_capture_twice(paths, sport="basket"):
    """Deux lectures independantes (V1)."""
    a, ha = read_capture(paths, sport, passage=1)
    b, hb = read_capture(paths, sport, passage=2)
    return a, b, list(dict.fromkeys(ha + hb))
