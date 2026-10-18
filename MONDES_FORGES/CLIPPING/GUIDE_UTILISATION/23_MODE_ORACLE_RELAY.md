# Mode ORACLE RELAY — raisonner sans clé, par fichiers

> Ce guide décrit le **relais oracle** : le cerveau partagé du CLIPPING peut
> raisonner **sans aucune clé API et sans aucun appel réseau**. La question est
> écrite dans `ORACLE/pending/`, l'opérateur (ou l'agent) répond dans
> `ORACLE/answers.json`, et le run suivant consomme la réponse.
>
> Motivation : le run `38831207071` a échoué en `Payment Required: Insufficient
> credits`, et une passerelle HTTP suppose encore une clé. Le relais supprime
> les deux problèmes : pas de clé, pas de dépendance à un provider.

---

## Le principe en 3 lignes

1. Une frégate (F00B, F00C, F04) a besoin de raisonner : elle appelle
   `brain.ask()`, jamais un provider directement.
2. `brain.ask()` essaie **`premium`** (clé NIM/CLIPPING_*), puis **`oracle`**
   (relais fichier), puis **`off`** (dégradation gracieuse).
3. En mode `oracle` sans réponse, l'état est **`pending`** : la question est
   persistée, le pipeline continue et dégrade. Il ne meurt jamais.

---

## Architecture

```
        F00B / F00C / F04
                │  brain.ask(system, user, source="F00x")
                ▼
        SHARED/brain.py
                │
     ┌──────────┴───────────┐
     ▼                      ▼
1. premium              2. oracle (relais fichier)
   clé NIM/CLIPPING_*       ORACLE/answers.json ?
   → HTTP direct              ├─ oui → status "ok"     (mode oracle)
   → 401/402/403/429/5xx      └─ non → écrit la question
     → repli oracle                    status "pending"
                                       (pipeline continue, dégradé)
     │                      │
     └──────────┬───────────┘
                ▼
            3. off
     relais désactivé + aucune clé
     (score neutre, tri plateforme seul)
```

---

## Cycle opérateur

```bash
# 1. Voir les questions en attente
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py list

# 2. Lire une question (prompts system + user + métadonnées)
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py show <id>

# 3. Écrire la réponse (JSON si expect_json=true)
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py answer <id> \
  --content '{"score": 7.5, "transformation": "neutre→dramatique", "reason": "hook fort"}' \
  --model sandbox --by agent

# 4. Commit + push : le run suivant consommera la réponse
git add MONDES_FORGES/CLIPPING/ORACLE && git commit -m "oracle: réponses <id>"
git push origin HEAD:v2-live-vox-c
```

En CI, la persistance est **automatique** : chaque workflow contenant une frégate
exécute `.github/scripts/persist_oracle_relay.sh` en `if: always()`. La question
est donc poussée même si le job échoue, et les réponses poussées localement sont
visibles au run suivant.

---

## Comportement par frégate

| Frégate | Mode `ok` | Mode `pending` | Mode `off` |
|---|---|---|---|
| F00B `vox_premium.py` | score de reframing réel | score neutre 5.0, `brain_status="pending"`, `oracle_question=<id>` | score neutre 5.0 |
| F00C `f00c_vox.py` | `brain.scores` rempli | `brain.note` liste les ids, `pending_questions=[...]` | `brain.note="cerveau indisponible"` |
| F04 `premium_client.py` | génération complète | `last_mode="oracle_pending"`, `last_question=<id>`, `PremiumClientError` explicite | `PremiumClientError` |

Un `pending` n'est pas une panne : c'est une **demande d'avis**. Relancer le
même run après réponse produit les mêmes ids de questions (l'id est le SHA-256
des prompts) et donc les mêmes réponses.

---

## Variables d'environnement

| Variable | Défaut | Effet |
|---|---|---|
| `ORACLE_RELAY_ENABLED` | `1` | `0` désactive le relais → `off` si pas de clé premium |
| `ORACLE_RELAY_DIR` | `CLIPPING/ORACLE` | emplacement des questions/réponses |
| `ORACLE_RELAY_STRICT` | `0` | `1` transforme `pending` en `error` (arrêt net volontaire) |

`ORACLE_RELAY_STRICT=1` est réservé aux cas où produire un artefact dégradé est
pire que ne rien produire (par exemple un export final).

---

## Contrat de données

- Question : `ORACLE/pending/<id>.json` — `id` = 16 premiers hex du SHA-256 de
  `{system, user, expect_json}` en JSON canonique.
- Réponse : `ORACLE/answers.json` — `answers.<id>.content`, `answered_at`,
  `answered_by`, `model`, `note`, `source`.
- Schéma public : `CONTRACTS/oracle_relay_schema.json`.
- Exemple : `ORACLE/answers.example.json` (jamais consommé).

---

## Diagnostic

```bash
# Mode disponible + compteurs du relais
python3 MONDES_FORGES/CLIPPING/SHARED/brain.py

# État seul
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py status

# Tests (stdlib, aucun réseau)
python3 -m unittest discover -s MONDES_FORGES/CLIPPING/SHARED/tests -v
```

---

## Règles verrouillées

1. **Aucune clé** dans le relais, aucun endpoint, aucun appel réseau.
2. Une question n'est jamais supprimée : elle passe `pending` → `answered`.
3. Le relais ne bloque jamais un run (`pending` est un succès dégradé).
4. `answers.json` est public dans Git : jamais de secret ni de donnée sensible
   dans une réponse.
5. Stdlib uniquement (`json`, `hashlib`, `pathlib`) — aucune dépendance pip.
6. Un `pending` doit être traité avant le prochain gate opérateur : c'est une
   décision de raisonnement, pas un détail.
