"""
libs/premium_client.py — Phase B de F04_COPYWRITER
==================================================

Client du modèle premium — la frégate parle DIRECT au modèle premium,
sans IRON intermédiaire pour la génération.

Config : CONTRACTS/copywriter_secrets.json (gitignored, ne contient que
la référence env + le model_id). Fallback sur l'example public.

  {
    "env_var_name": "CLIPPING_PREMIUM_API_KEY",
    "model_id": "<model_premium_id>",
    "provider": "openai|openrouter|baseten|anthropic|other",
    "base_url": "...",           // si provider = "other"
    "max_tokens_per_call": 4096,
    "temperature_default": 0.7
  }

La clé réelle est lue depuis la variable d'env (jamais dans les fichiers).

Protocole OpenAI (chat/completions) : providers openai, openrouter, other.
Protocole Anthropic (messages) : provider anthropic.

Implémentation stdlib (urllib) — aucune dépendance SDK obligatoire,
compatible avec le poste faible du Warsmith.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))), "SHARED")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:  # cerveau partagé : repli oracle si la clé premium est absente/refusée
    from brain import ask as _brain_ask, available_mode as _brain_mode
except Exception:  # pragma: no cover - cerveau indisponible : mode premium seul
    _brain_ask = None

    def _brain_mode():
        return "off"

CONTRACTS_DIR = "CONTRACTS"
DEFAULT_ENV_VAR = "CLIPPING_PREMIUM_API_KEY"

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "baseten": "https://inference.baseten.co/v1",
    "anthropic": "https://api.anthropic.com/v1",
}


class PremiumClientError(Exception):
    pass


class PremiumClient:
    def __init__(self, forge_root: str):
        self._forge_root = forge_root
        self._load_env_local()
        self.config = self._load_config()
        # Renseigné à chaque appel : "premium" | "oracle" | "oracle_pending" | "off".
        self.last_mode: str | None = None
        # Id de la question oracle si le raisonnement attend une réponse.
        self.last_question: str | None = None

    def _load_env_local(self):
        """Charge un .env.local OU .env (repo ou forge) si présent — stdlib,
        aucune dépendance. Les variables déjà présentes dans os.environ priment
        (ordre : .env.local d'abord, .env ensuite, jamais l'inverse).
        (Freebuff injecte les clés API Keys via .env/.env.local / env du workspace.)"""
        candidates = []
        base = self._forge_root
        for _ in range(4):  # forge_root, MONDES_FORGES, repo root, +1
            candidates.append(os.path.join(base, ".env.local"))
            candidates.append(os.path.join(base, ".env"))
            base = os.path.dirname(base)
        seen = set()
        for path in candidates:
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and not os.environ.get(key):
                            os.environ[key] = val
            except OSError:
                continue

    # ------------------------------------------------------------------
    def _load_config(self) -> dict:
        secrets = os.path.join(self._forge_root, CONTRACTS_DIR, "copywriter_secrets.json")
        if os.path.exists(secrets):
            with open(secrets, "r", encoding="utf-8") as f:
                return json.load(f)
        example = os.path.join(self._forge_root, CONTRACTS_DIR,
                               "copywriter_secrets.example.json")
        if os.path.exists(example):
            with open(example, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _env_var_name(self) -> str:
        return self.config.get("env_var_name") or DEFAULT_ENV_VAR

    def _api_key(self) -> str:
        # 1) env (recommandé). 2) fallback local : champ "api_key" de la config
        #    gitignored (CONTRACTS/copywriter_secrets.json) — le sandbox peut
        #    bloquer la lecture des fichiers .env*, la config reste lisible.
        env_val = os.environ.get(self._env_var_name(), "").strip()
        if env_val:
            return env_val
        return str(self.config.get("api_key", "")).strip()

    def _base_url(self) -> str:
        provider = self.config.get("provider", "other")
        return self.config.get("base_url") or BASE_URLS.get(provider, "")

    # ------------------------------------------------------------------
    def require_config(self):
        """Valide qu'un cerveau est joignable — premium OU oracle.

        Important : l'absence de clé premium n'est plus une erreur fatale
        (repli oracle). On ne lève que si AUCUN mode n'est disponible."""
        if self._premium_ready():
            return
        if _brain_ask is not None and _brain_mode() != "off":
            return
        details = []
        if not self._api_key():
            details.append(f"clé '{self._env_var_name()}' absente")
        if not self.config.get("model_id"):
            details.append("model_id manquant")
        if not self._base_url():
            details.append("base_url manquante")
        raise PremiumClientError(
            "Aucun cerveau disponible — premium incomplet ("
            + ", ".join(details)
            + ") et relais oracle indisponible "
            "(ORACLE_RELAY_ENABLED=1, ORACLE/answers.json).")

    def extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            return text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
        return text

    # ------------------------------------------------------------------
    def _premium_ready(self) -> bool:
        model_id = str(self.config.get("model_id") or "")
        base_url = str(self._base_url() or "")
        return bool(self._api_key() and model_id and base_url
                    and "<" not in model_id and "<" not in base_url)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Génère une réponse via le cerveau partagé.

        Ordre : premium direct (config complète) → relais oracle fichier
        (``ORACLE/pending`` → ``answers.json``) → erreur explicite si aucun
        cerveau. Le mode réellement utilisé est exposé dans ``self.last_mode``
        (jamais la clé) ; ``self.last_question`` porte l'id à répondre."""
        if self._premium_ready():
            try:
                provider = self.config.get("provider", "other")
                if provider == "anthropic":
                    out = self._chat_anthropic(system_prompt, user_prompt)
                else:
                    out = self._chat_openai_compatible(system_prompt, user_prompt)
                self.last_mode = "premium"
                return out
            except PremiumClientError:
                # clé refusée/absente en pratique (401/402/403/429/5xx/réseau)
                # → on ne bloque pas : le repli oracle prend la main ci-dessous.
                pass
        if _brain_ask is not None:
            res = _brain_ask(system_prompt, user_prompt, temperature=0.7,
                             max_tokens=self.config.get("max_tokens_per_call", 4096),
                             expect_json=False, retries=1,
                             timeout=float(self.config.get("timeout_seconds", 240)),
                             source="F04")
            if res.get("status") == "ok":
                self.last_mode = res.get("mode")
                self.last_question = None
                return res.get("content") or ""
            if res.get("status") == "pending":
                self.last_mode = "oracle_pending"
                self.last_question = res.get("question_id")
                raise PremiumClientError(
                    "Question oracle en attente "
                    f"({self.last_question}) — répondre via "
                    "SHARED/oracle_relay.py answer puis relancer le run.")
        self.last_mode = "off"
        raise PremiumClientError(
            "Aucun cerveau disponible — configurer la clé premium "
            f"('{self._env_var_name()}') ou activer le relais oracle "
            "(ORACLE_RELAY_ENABLED=1, questions dans ORACLE/pending/).")

    def _chat_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        url = self._base_url().rstrip("/") + "/chat/completions"
        body = {
            "model": self.config["model_id"],
            "temperature": self.config.get("temperature_default", 0.7),
            "max_tokens": self.config.get("max_tokens_per_call", 4096),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.config.get("request_json_mode", False):
            body["response_format"] = {"type": "json_object"}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "PERTURABO-F04-COPYWRITER",
        })
        response = self._fetch(req)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            raise PremiumClientError(f"Réponse API non-JSON: {e}") from e
        try:
            return parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise PremiumClientError(f"Structure réponse inattendue: {parsed}") from e

    def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        url = self._base_url().rstrip("/") + "/messages"
        body = {
            "model": self.config["model_id"],
            "max_tokens": self.config.get("max_tokens_per_call", 4096),
            "temperature": self.config.get("temperature_default", 0.7),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "x-api-key": self._api_key(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": "PERTURABO-F04-COPYWRITER",
        })
        response = self._fetch(req)
        try:
            parsed = json.loads(response)
            parts = parsed.get("content", [])
            return "".join(p.get("text", "") for p in parts)
        except (json.JSONDecodeError, AttributeError) as e:
            raise PremiumClientError(f"Réponse Anthropic invalide: {e}") from e

    def _fetch(self, req: urllib.request.Request) -> str:
        timeout = self.config.get("timeout_seconds", 240)
        max_retries = int(self.config.get("max_retries", 3))
        retry_base_delay = float(self.config.get("retry_base_delay", 2.0))
        last_err = "inconnue"
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                snippet = e.read().decode("utf-8", errors="replace")[:500]
                if e.code < 500 or attempt == max_retries:
                    raise PremiumClientError(
                        f"HTTP {e.code} de {req.full_url}: {snippet}") from e
                last_err = f"HTTP {e.code}"
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                reason = getattr(e, "reason", e)
                if attempt == max_retries:
                    raise PremiumClientError(
                        f"Réseau vers {req.full_url}: {reason}") from e
                last_err = f"réseau: {reason}"
            # backoff exponentiel (2s, 4s, ...) avant la tentative suivante
            if attempt < max_retries:
                time.sleep(retry_base_delay * (2 ** (attempt - 1)))
        raise PremiumClientError(
            f"Échec après {max_retries} tentatives vers {req.full_url} ({last_err})")
