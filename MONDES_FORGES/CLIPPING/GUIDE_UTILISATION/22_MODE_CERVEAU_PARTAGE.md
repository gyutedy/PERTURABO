# Mode CERVEAU PARTAGÉ — premium → oracle (relais) → off

> Ce guide décrit le **cerveau partagé** du CLIPPING : un seul point d'entrée IA
> (`SHARED/brain.py`) pour tout le tronc. Motivation réelle : le run
> `38831207071` a échoué avec `[EXECUTION_FAILED] Payment Required: Insufficient
> credits`. Une clé premium qui tombe ne doit **plus jamais** arrêter le pipeline.
>
> Depuis le 2026-10-18, le repli `oracle` n'est plus une passerelle HTTP : c'est
> un **relais fichier sans clé**. Voir `23_MODE_ORACLE_RELAY.md` pour le détail
> opérateur.

---

## Le principe en 3 lignes

1. Les frégates (F00B arbitrage, F00C tri sémantique, F04 copywriter) ne parlent
   **jamais** directement à un provider : elles importent `SHARED/brain.py`.
2. `brain.ask()` résout un mode tout seul, dans cet ordre :
   **`premium`** (clé NIM/CLIPPING_*) → **`oracle`** (relais fichier
   `ORACLE/pending` → `answers.json`) → **`off`** (dégradation gracieuse).
3. `off` et `pending` sont des **états observables** (exposés dans les
   manifestes), pas des erreurs fatales.

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
  NVIDIA NIM gpt-oss-20b  relais fichier      dégradation gracieuse
     (clé CLIPPING_*)     ORACLE/answers.json (score neutre / tri
                          (aucune clé,         plateforme seul)
                           aucun réseau)
```

Le repli `oracle` s'active quand la clé premium est **absente** OU **refusée**
(401/402/403/429/5xx/réseau). Le raisonnement réel continue dès qu'une réponse
existe : tri sémantique, sélection de segments, copywriter.

---

## Variables d'environnement

| Mode | Variables | Rôle |
|---|---|---|
| premium | `NVIDIA_NIM_API_KEY` → `CLIPPING_F00B_API_KEY` → `CLIPPING_PREMIUM_API_KEY` | voie rapide (lue en premier) |
| premium | `NVIDIA_NIM_BASE_URL`, `NVIDIA_NIM_MODEL` | surcharge base/modèle (défauts : `integrate.api.nvidia.com/v1`, `openai/gpt-oss-20b`) |
| oracle | `ORACLE_RELAY_ENABLED` (`1`) | active/désactive le relais fichier |
| oracle | `ORACLE_RELAY_DIR` | dossier du relais (défaut : `CLIPPING/ORACLE`) |
| oracle | `ORACLE_RELAY_STRICT` (`0`) | `1` transforme `pending` en `error` |

> Aucune clé n'est **jamais** écrite en dur, journalisée ou renvoyée. Seul le
> **nom** de la variable est exposé (`provider` dans le retour d'`ask`).
> Le relais oracle n'a **aucune** variable de clé : il n'en a pas besoin.

---

## Diagnostic

```bash
# Quel mode est disponible + compteurs du relais ?
python3 MONDES_FORGES/CLIPPING/SHARED/brain.py

# Test de raisonnement réel (premium sinon relais)
python3 MONDES_FORGES/CLIPPING/SHARED/brain.py --ping

# Questions en attente / état du relais
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py list
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py status
```

Le retour d'`ask()` est toujours :

```json
{
  "status": "ok | pending | error | off",
  "content": {"...": "..."},
  "mode": "premium | oracle | off",
  "provider": "NOM_DE_VAR | ORACLE_RELAY",
  "model": "...",
  "error": null,
  "question_id": null,
  "question_path": null,
  "trace": [{"mode": "premium", "error": "HTTP 402: ..."}]
}
```

`trace` documente les échecs avant le succès (ex : premium 402 → oracle ok).
`question_id` n'est renseigné qu'en mode oracle (réponse consommée ou en attente).

---

## Contrats

- Schéma public du bus : `MONDES_FORGES/CLIPPING/CONTRACTS/premium_bus_schema.json`.
- Schéma du relais : `MONDES_FORGES/CLIPPING/CONTRACTS/oracle_relay_schema.json`.
- Le bus ne contient **que des noms de variables**, jamais de valeur.
- Exemples de secrets : `f00b_secrets.example.json`,
  `copywriter_secrets.example.json` (le fichier réel est gitignored).

---

## Dégradation par frégate

| Frégate | premium | oracle (réponse) | pending | off |
|---|---|---|---|---|
| F00B `vox_premium.py` | score de reframing + verdict réel | idem, `brain_mode="oracle"` | score neutre 5.0 + `oracle_question` | score neutre 5.0 |
| F00C `f00c_vox.py` | `brain.scores` | `brain.scores` | `pending_questions=[...]` | `brain.note="cerveau indisponible"` |
| F04 `premium_client.py` | génération premium | génération oracle | `last_mode="oracle_pending"` | `PremiumClientError` explicite |

---

## Règles verrouillées

1. Un seul point d'entrée IA : `SHARED/brain.py`.
2. `stdlib` uniquement — aucune dépendance pip.
3. `off` et `pending` ne lèvent jamais d'exception fatale dans les frégates.
4. Jamais de clé dans les fichiers, les logs ou les manifestes.
5. Le relais oracle ne fait **aucun** appel réseau et ne lit **aucune** clé.
