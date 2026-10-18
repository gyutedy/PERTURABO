# ORACLE — relais de raisonnement sans clé

Ce dossier est le **bus de questions/réponses** du mode oracle. Aucune clé API,
aucun appel réseau : tout passe par des fichiers versionnés et auditables.

## Cycle

```
frégate (F00B/F00C/F04)
        │  besoin de raisonner, clé premium absente/refusée
        ▼
brain.ask()  ──►  ORACLE/pending/<id>.json     (status: pending)
        │
        │  le run continue en dégradé (score neutre / tri seul)
        ▼
opérateur ──► agent (chat) ──► oracle_relay.py answer <id>
        │
        ▼
ORACLE/answers.json  (status: answered)  ──►  commit + push
        │
        ▼
run suivant : brain.ask() trouve la réponse → raisonnement réel
```

## Commandes

```bash
# Voir les questions en attente
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py list

# Lire une question complète (prompts inclus) + réponse éventuelle
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py show <id>

# Enregistrer une réponse JSON (la question passe en answered)
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py answer <id> \
  --content-file reponse.json --model sandbox --by agent

# Réponse texte libre
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py answer <id> \
  --text --content-file reponse.txt

# État global
python3 MONDES_FORGES/CLIPPING/SHARED/oracle_relay.py status
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `pending/<id>.json` | question en attente (id = sha256 tronqué des prompts) |
| `answers.json` | réponses indexées par id (commité) |
| `answers.example.json` | exemple de structure, jamais consommé |

## Variables

| Variable | Défaut | Effet |
|---|---|---|
| `ORACLE_RELAY_DIR` | ce dossier | emplacement du relais |
| `ORACLE_RELAY_ENABLED` | `1` | `0` désactive le relais (mode `off` si pas de clé) |
| `ORACLE_RELAY_STRICT` | `0` | `1` transforme `pending` en `error` |

## Règles

- Une question n'est **jamais supprimée** : elle passe de `pending` à `answered`.
- L'id dépend des prompts exacts (system + user + `expect_json`). Même entrée =
  même id ; une entrée différente crée une nouvelle question.
- Ne jamais mettre de secret dans `answers.json` : il est public dans Git.
- Les questions peuvent contenir des extraits de transcript : vérifier avant de
  pousser si le dépôt est public.
