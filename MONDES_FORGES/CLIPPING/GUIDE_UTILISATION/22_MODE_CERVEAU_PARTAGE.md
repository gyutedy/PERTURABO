# Mode CERVEAU PARTAGÉ — premium → oracle → off

> Ce guide décrit le **cerveau partagé** du CLIPPING : un seul point d'entrée IA
> (`SHARED/brain.py`) pour tout le tronc. Motivation réelle : le run
> `38831207071` a échoué avec `[EXECUTION_FAILED] Payment Required: Insufficient
> credits`. Une clé premium qui tombe ne doit **plus jamais** arrêter le pipeline.

---

## Le principe en 3 lignes

1. Les frégates (F00B arbitrage, F00C tri sémantique, F04 copywriter) ne parlent
   **jamais** directement à un provider : elles importent `SHARED/brain.py`.
2. `brain.ask()` résout un mode tout seul, dans cet ordre :
   **`premium`** (clé NIM/CLIPPING_*) → **`oracle`** (passerelle `AI_GATEWAY_*`)
   → **`off`** (aucune clé : dégradation gracieuse, jamais un crash).
3. `off` est un **état observable** (exposé dans les manifestes), pas une erreur.

---

## Architecture

```
                 ┌──────────────────────────────────────────┐
   F00B  ───────►│                                          │
   F00C  ───────►│   SHARED/brain.py   ask(system, user)     │
   F04   ───────►│                                          │
                 └───────────────┬──────────────────────────┘
                                 │
              ┌──────────────────┼───────────────────┐
              ▼                  ▼                   ▼
        1. premium          2. oracle           3. off
     NVIDIA NIM kimi-k3   AI_GATEWAY_*      dégradation gracieuse
     (clé CLIPPING_*)     (CORE/ai_gateway)  (score neutre / tri
                                               plateforme seul)
```

Le repli `oracle` s'active quand la clé premium est **absente** OU **refusée**
(401/402/403/429/5xx/réseau). Le raisonnement réel continue : tri sémantique,
sélection de segments, copywriter.

---

## Variables d'environnement

| Mode | Variables | Rôle |
|---|---|---|
| premium | `NVIDIA_NIM_API_KEY` → `CLIPPING_F00B_API_KEY` → `CLIPPING_PREMIUM_API_KEY` | voie rapide (lue en premier) |
| premium | `NVIDIA_NIM_BASE_URL`, `NVIDIA_NIM_MODEL` | surcharge base/modèle (défauts : `integrate.api.nvidia.com/v1`, `moonshotai/kimi-k3`) |
| oracle | `AI_GATEWAY_API_KEY` + `AI_GATEWAY_BASE_URL` | passerelle partagée (obligatoires pour le repli) |
| oracle | `AI_GATEWAY_MODEL` | surcharge modèle (défaut : `anthropic/claude-sonnet-4.6`) |

> Aucune clé n'est **jamais** écrite en dur, journalisée ou renvoyée. Seul le
> **nom** de la variable est exposé (`provider` dans le retour d'`ask`).

---

## Diagnostic

```bash
# Quel mode est disponible dans l'environnement courant ?
python3 MONDES_FORGES/CLIPPING/SHARED/brain.py

# Test de raisonnement réel (premium sinon oracle)
python3 MONDES_FORGES/CLIPPING/SHARED/brain.py --ping
```

Le retour d'`ask()` est toujours :

```json
{
  "status": "ok | error | off",
  "content": {"...": "..."},
  "mode": "premium | oracle | off",
  "provider": "NOM_DE_VAR",
  "model": "...",
  "error": null,
  "trace": [{"mode": "premium", "error": "HTTP 402: ..."}]
}
```

`trace` documente les échecs avant le succès (ex : premium 402 → oracle ok).

---

## Contrats

- Schéma public du bus : `MONDES_FORGES/CLIPPING/CONTRACTS/premium_bus_schema.json`.
- Le bus ne contient **que des noms de variables**, jamais de valeur.
- Exemples de secrets : `f00b_secrets.example.json`,
  `copywriter_secrets.example.json` (le fichier réel est gitignored).

---

## Dégradation par frégate

| Frégate | premium/oracle | off |
|---|---|---|
| F00B `vox_premium.py` | score de reframing + verdict réel | score neutre 5.0, `used_premium=false` |
| F00C `f00c_vox.py` | `brain.scores` (bloc `brain` du manifeste) | `brain.note = "cerveau indisponible"` |
| F04 `premium_client.py` | génération premium puis repli oracle | `PremiumClientError` explicite |

---

## Règles verrouillées

1. Un seul point d'entrée IA : `SHARED/brain.py`.
2. `stdlib` uniquement (`urllib`) — aucune dépendance pip.
3. `off` ne lève jamais d'exception fatale.
4. Jamais de clé dans les fichiers, les logs ou les manifestes.
