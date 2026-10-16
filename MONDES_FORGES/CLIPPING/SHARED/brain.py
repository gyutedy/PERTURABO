#!/usr/bin/env python3
"""
brain.py — Le cerveau partagé du CLIPPING (double mode premium / oracle).
==========================================================================

Un seul point d'entrée pour tout appel IA du tronc CLIPPING. Les frégates
(F00B arbitrage, F00C tri sémantique, F04 copywriter) parlent ICI, jamais
directement à un provider. C'est le « cerveau partagé » : brancher une frégate
au raisonnement = importer ce module.

Modes, résolus automatiquement par ordre de préférence :

  1. ``premium`` — clé directe d'un provider NVIDIA NIM / CLIPPING_*
     (``NVIDIA_NIM_API_KEY`` → ``CLIPPING_F00B_API_KEY``
     → ``CLIPPING_PREMIUM_API_KEY``).
  2. ``oracle``  — passerelle partagée PERTURABO (``CORE/ai_gateway.py``) :
     ``AI_GATEWAY_API_KEY`` + ``AI_GATEWAY_BASE_URL``. Sert de repli quand la
     clé premium est absente OU refusée (401/403/429/5xx/réseau).
  3. ``off``     — aucune clé disponible : on n'invente rien. Chaque frégate
     décide de sa dégradation gracieuse (score neutre, tri plateforme seul…).

Doctrine de sécurité (non négociable) :

  * Aucune clé n'est jamais écrite en dur, journalisée ou renvoyée.
    On lit sa VALEUR via ``os.environ`` au moment de l'appel, et rien d'autre.
  * Aucune dépendance pip : ``urllib`` pur (le poste faible du Warsmith doit
    pouvoir exécuter ce module comme les autres).
  * ``off`` n'est jamais une erreur fatale : c'est un état observable
    (``mode``) que les appelants exposent dans leurs manifestes.

Usage :

    import sys
    sys.path.insert(0, "<CLIPPING>/SHARED")
    from brain import ask, available_mode

    res = ask("Tu es l'arbitre...", "Extrait: \"...\"", expect_json=True)
    if res["status"] == "ok":
        score = res["content"]["score"]   # dict si expect_json
        mode  = res["mode"]               # "premium" | "oracle"
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

# ─── Clés premium (ordre de préférence) ─────────────────────────────────────
PREMIUM_ENV_VARS = (
    "NVIDIA_NIM_API_KEY",
    "CLIPPING_F00B_API_KEY",
    "CLIPPING_PREMIUM_API_KEY",
)
DEFAULT_PREMIUM_BASE = "https://integrate.api.nvidia.com/v1"
DEFAULT_PREMIUM_MODEL = "moonshotai/kimi-k3"

# ─── Oracle partagé (passerelle CORE/ai_gateway.py) ─────────────────────────
GATEWAY_KEY_VAR = "AI_GATEWAY_API_KEY"
GATEWAY_BASE_VAR = "AI_GATEWAY_BASE_URL"
GATEWAY_MODEL_VAR = "AI_GATEWAY_MODEL"
DEFAULT_GATEWAY_MODEL = "anthropic/claude-sonnet-4.6"

USER_AGENT = "PERTURABO-BRAIN/1.0"


def _clean(value) -> str:
    return (value or "").strip()


# ─── Résolution de mode (jamais d'effet de bord, jamais de réseau) ──────────

def premium_env_var() -> str | None:
    """Nom de la variable premium non vide (sans révéler sa valeur)."""
    for name in PREMIUM_ENV_VARS:
        if _clean(os.environ.get(name)):
            return name
    return None


def premium_ready() -> bool:
    return premium_env_var() is not None


def oracle_ready() -> bool:
    return bool(_clean(os.environ.get(GATEWAY_KEY_VAR))
                and _clean(os.environ.get(GATEWAY_BASE_VAR)))


def available_mode() -> str:
    """Retourne ``premium`` | ``oracle`` | ``off`` selon l'environnement."""
    if premium_ready():
        return "premium"
    if oracle_ready():
        return "oracle"
    return "off"


# ─── Helpers HTTP (stdlib uniquement) ───────────────────────────────────────

def _premium_base() -> str:
    return (_clean(os.environ.get("NVIDIA_NIM_BASE_URL"))
            or _clean(os.environ.get(GATEWAY_BASE_VAR))
            or DEFAULT_PREMIUM_BASE)


def _premium_model() -> str:
    return _clean(os.environ.get("NVIDIA_NIM_MODEL")) or DEFAULT_PREMIUM_MODEL


def _gateway_chat_url() -> str:
    base = _clean(os.environ.get(GATEWAY_BASE_VAR)).rstrip("/")
    if base.endswith("/api/v1"):
        return base + "/chat/completions"
    return base + "/api/v1/chat/completions"


def _post_chat(url: str, key: str, payload: dict, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:  # nosec B310
        return resp.read().decode("utf-8")


def extract_json(text: str) -> dict:
    """Extrait un objet JSON d'une réponse LLM (pur, ```json, texte autour)."""
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    if "```" in raw:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("Aucun JSON exploitable dans la réponse", raw, 0)


# ─── Appel d'un backend OpenAI-compatible (une tentative, avec retries) ─────

def _chat_openai_compatible(url: str, key: str, model: str, system_prompt: str,
                            user_prompt: str, temperature: float, max_tokens: int,
                            expect_json: bool, timeout: float,
                            retries: int) -> dict:
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    last_error = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            body = _post_chat(url, key, payload, timeout)
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
            if expect_json:
                try:
                    parsed = extract_json(content)
                except json.JSONDecodeError as exc:
                    last_error = f"json_invalide: {exc}"
                    if attempt < retries:
                        time.sleep(2 ** (attempt - 1))
                        continue
                    return {"status": "error", "content": None, "error": last_error}
                return {"status": "ok", "content": parsed, "error": None}
            return {"status": "ok", "content": content, "error": None}
        except urllib.error.HTTPError as exc:
            snippet = ""
            try:
                snippet = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001 - le message d'erreur n'est pas critique
                pass
            last_error = f"HTTP {exc.code}: {snippet}"
            if exc.code < 500 and exc.code != 429:
                return {"status": "error", "content": None, "error": last_error}
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            last_error = f"réseau: {reason}"
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error = f"réponse inattendue: {type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    return {"status": "error", "content": None, "error": last_error}


# ─── ask — le seul appel public ─────────────────────────────────────────────

def ask(system_prompt: str, user_prompt: str, *, model: str | None = None,
        temperature: float = 0.2, max_tokens: int = 256,
        expect_json: bool = True, timeout: float = 25.0,
        retries: int = 2) -> dict:
    """Interroge le cerveau partagé : premium d'abord, oracle en repli.

    Retourne ::

        {
          "status": "ok" | "error" | "off",
          "content": dict | str | None,   # dict si expect_json=True
          "mode": "premium" | "oracle" | "off",
          "provider": str | None,          # nom de la var, jamais sa valeur
          "model": str | None,
          "error": str | None,
          "trace": [ {"mode": ..., "error": ...}, ... ]  # échecs avant succès
        }
    """
    trace: list[dict] = []

    # 1. Premium direct
    prem_var = premium_env_var()
    if prem_var:
        result = _chat_openai_compatible(
            _premium_base().rstrip("/") + "/chat/completions",
            os.environ[prem_var], model or _premium_model(),
            system_prompt, user_prompt, temperature, max_tokens,
            expect_json, timeout, retries,
        )
        if result["status"] == "ok":
            return {"status": "ok", "content": result["content"], "mode": "premium",
                    "provider": prem_var, "model": model or _premium_model(),
                    "error": None, "trace": trace}
        trace.append({"mode": "premium", "provider": prem_var, "error": result["error"]})

    # 2. Oracle partagé (cerveau du sandbox / passerelle)
    if oracle_ready():
        gmodel = model or _clean(os.environ.get(GATEWAY_MODEL_VAR)) or DEFAULT_GATEWAY_MODEL
        result = _chat_openai_compatible(
            _gateway_chat_url(), _clean(os.environ[GATEWAY_KEY_VAR]), gmodel,
            system_prompt, user_prompt, temperature, max_tokens,
            expect_json, timeout, retries,
        )
        if result["status"] == "ok":
            return {"status": "ok", "content": result["content"], "mode": "oracle",
                    "provider": GATEWAY_KEY_VAR, "model": gmodel,
                    "error": None, "trace": trace}
        trace.append({"mode": "oracle", "provider": GATEWAY_KEY_VAR, "error": result["error"]})

    # 3. Aucun cerveau : état observable, jamais de crash
    last_error = trace[-1]["error"] if trace else "aucune clé (premium/oracle) configurée"
    return {"status": "off" if not trace else "error", "content": None,
            "mode": "off", "provider": None, "model": None,
            "error": last_error, "trace": trace}


if __name__ == "__main__":  # pragma: no cover - diagnostic manuel
    import argparse

    parser = argparse.ArgumentParser(description="brain — diagnostic du cerveau partagé")
    parser.add_argument("--ping", action="store_true", help="Test de raisonnement réel")
    parser.add_argument("--prompt", default="Réponds uniquement: {\"ping\": \"pong\"}")
    args = parser.parse_args()
    print(json.dumps({"available_mode": available_mode()}, indent=2))
    if args.ping:
        res = ask("Tu es un test de connectivité.", args.prompt, max_tokens=32)
        print(json.dumps(res, indent=2, ensure_ascii=False))
