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
  2. ``oracle``  — relais fichier SANS clé (``SHARED/oracle_relay.py``) :
     la question est écrite dans ``ORACLE/pending/``, l'opérateur/agent répond
     dans ``ORACLE/answers.json``, le run suivant consomme la réponse.
     S'active quand la clé premium est absente OU refusée (401/402/403/429/5xx).
  3. ``off``     — relais désactivé et aucune clé : on n'invente rien. Chaque
     frégate décide de sa dégradation gracieuse (score neutre, tri seul…).

État ``pending`` : une question attend une réponse. Le pipeline n'échoue pas,
il dégrade et expose ``question_id``. ``ORACLE_RELAY_STRICT=1`` transforme
``pending`` en ``error`` pour un arrêt net volontaire.

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

# ─── Oracle relais (fichiers, aucune clé, aucun réseau) ─────────────────────
try:  # import local : le relais vit dans le même dossier SHARED
    import oracle_relay as _relay
except Exception:  # pragma: no cover - relais absent : mode off
    _relay = None

RELAY_PROVIDER = "ORACLE_RELAY"
RELAY_MODEL = "sandbox-agent"

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
    """Vrai si le relais fichier est disponible et activé."""
    return _relay is not None and _relay.relay_enabled()


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
        retries: int = 2, source: str | None = None) -> dict:
    """Interroge le cerveau partagé : premium d'abord, relais oracle ensuite.

    ``source`` identifie la frégate émettrice (F00B/F00C/F04) dans la question.

    Retourne ::

        {
          "status": "ok" | "pending" | "error" | "off",
          "content": dict | str | None,   # dict si expect_json=True
          "mode": "premium" | "oracle" | "off",
          "provider": str | None,          # nom de la var, jamais sa valeur
          "model": str | None,
          "error": str | None,
          "question_id": str | None,       # si relais oracle
          "question_path": str | None,     # si relais oracle
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

    # 2. Oracle relais fichier (aucune clé, aucun réseau)
    if oracle_ready():
        qid = _relay.question_id(system_prompt, user_prompt, expect_json)
        entry = _relay.get_answer(qid)
        if entry:
            content = entry.get("content")
            if expect_json and isinstance(content, str):
                try:
                    content = extract_json(content)
                except json.JSONDecodeError as exc:
                    trace.append({"mode": "oracle", "provider": RELAY_PROVIDER,
                                  "error": f"réponse JSON invalide: {exc}"})
                    content = None
            if content is not None:
                return {"status": "ok", "content": content, "mode": "oracle",
                        "provider": RELAY_PROVIDER,
                        "model": entry.get("model") or RELAY_MODEL,
                        "error": None, "trace": trace,
                        "question_id": qid, "question_path": None}

        question = _relay.write_question(
            system_prompt, user_prompt, expect_json=expect_json, source=source)
        pending_msg = f"question en attente: {question['id']}"
        trace.append({"mode": "oracle", "provider": RELAY_PROVIDER,
                      "error": pending_msg})
        status = "error" if _relay.relay_strict() else "pending"
        return {"status": status, "content": None, "mode": "oracle",
                "provider": RELAY_PROVIDER, "model": RELAY_MODEL,
                "error": pending_msg, "trace": trace,
                "question_id": question["id"],
                "question_path": question["path"]}

    # 3. Aucun cerveau : état observable, jamais de crash
    last_error = trace[-1]["error"] if trace else "aucune clé premium, relais oracle désactivé"
    return {"status": "off" if not trace else "error", "content": None,
            "mode": "off", "provider": None, "model": None,
            "error": last_error, "trace": trace}


if __name__ == "__main__":  # pragma: no cover - diagnostic manuel
    import argparse

    parser = argparse.ArgumentParser(description="brain — diagnostic du cerveau partagé")
    parser.add_argument("--ping", action="store_true", help="Test de raisonnement réel")
    parser.add_argument("--prompt", default="Réponds uniquement: {\"ping\": \"pong\"}")
    args = parser.parse_args()
    diag = {"available_mode": available_mode()}
    if _relay is not None:
        diag["relay"] = _relay.status()
    print(json.dumps(diag, indent=2, ensure_ascii=False))
    if args.ping:
        res = ask("Tu es un test de connectivité.", args.prompt, max_tokens=32)
        print(json.dumps(res, indent=2, ensure_ascii=False))
