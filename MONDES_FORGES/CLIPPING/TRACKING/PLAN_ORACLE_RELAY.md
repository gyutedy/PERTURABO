# Plan d'implémentation — ORACLE RELAY (sans clé, raisonnement sandbox)

> Décision d'architecture : le mode « oracle » n'appelle **aucune API externe** et
> ne câble **aucune clé**. Quand une frégate doit réfléchir et que la clé premium
> est absente/refusée, elle **écrit une question** dans `CLIPPING/ORACLE/pending/`.
> L'opérateur la transmet à l'agent (chat), l'agent répond, la réponse est
> commitée dans `CLIPPING/ORACLE/answers.json`, puis le run est relancé.
>
> Le pipeline ne meurt jamais : sans réponse il expose `status="pending"` et
> dégrade (score neutre / tri plateforme), exactement comme `off` aujourd'hui.

## Parties (une partie = un commit + push)

| # | Livrable | Fichiers principaux | État |
|---|---|---|---|
| P0 | Plan fragmenté + point de reprise | `TRACKING/PLAN_ORACLE_RELAY.md` | ✅ |
| P1 | Cœur du relais + tests | `SHARED/oracle_relay.py`, `SHARED/tests/test_oracle_relay.py` | ✅ |
| P2 | `brain.py` branché sur le relais (suppression passerelle HTTP) | `SHARED/brain.py` | ✅ |
| P3 | Contrats + exemples + README ORACLE | `CONTRACTS/oracle_relay_schema.json`, `CONTRACTS/premium_bus_schema.json`, `ORACLE/README.md`, `ORACLE/answers.example.json`, `ORACLE/answers.json` | ✅ |
| P4 | Frégates : état `pending` observable (F00B, F00C, F04) | `F00B_VOX/.../vox_premium.py`, `F00C_VOX/.../f00c_vox.py`, `F04_COPYWRITER/.../premium_client.py` | ✅ |
| P5 | CI : persistance des questions (commit/push auto) | `.github/workflows/perturabo_transcribe_matrix.yml`, `perturabo_vox_c_analysis.yml`, `perturabo_f04_copywriting.yml`, `perturabo_transcribe.yml` | ⬜ |
| P6 | Docs opérateur + tracking + continuité | `GUIDE_UTILISATION/23_MODE_ORACLE_RELAY.md`, `22_MODE_CERVEAU_PARTAGE.md`, `TRACKING/CLIPPING_LOG.md`, `CONTINUATION_F00.md` | ⬜ |

## Contrat de données

Question (`ORACLE/pending/<id>.json`) :

```json
{
  "id": "<sha256 tronqué 16>",
  "sha256": "<sha256 complet>",
  "status": "pending",
  "created_at": "2026-10-18T00:00:00Z",
  "source": "F00B|F00C|F04|cli",
  "expect_json": true,
  "system": "...",
  "user": "..."
}
```

Réponse (`ORACLE/answers.json`) :

```json
{
  "version": 1,
  "answers": {
    "<id>": {
      "content": {"score": 7.5, "transformation": "neutre→dramatique", "reason": "..."},
      "expect_json": true,
      "answered_at": "2026-10-18T00:00:00Z",
      "answered_by": "agent",
      "model": "sandbox",
      "note": null
    }
  }
}
```

## Résolution de mode (après P2)

1. `premium` : `NVIDIA_NIM_API_KEY` / `CLIPPING_F00B_API_KEY` / `CLIPPING_PREMIUM_API_KEY`
   présent → appel direct. En cas de refus (401/402/403/429/5xx/réseau), on passe au relais.
2. `oracle` : relais fichier activé (`ORACLE_RELAY_ENABLED`, défaut `1`).
   - réponse présente → `status="ok"`, `mode="oracle"`, `provider="ORACLE_RELAY"`.
   - réponse absente → question écrite, `status="pending"`, `question_id` exposé.
   - `ORACLE_RELAY_STRICT=1` → `status="error"` au lieu de `pending` (arrêt net).
3. `off` : relais désactivé et aucune clé premium.

## Règles verrouillées

- Aucune clé, aucun endpoint LLM, aucune dépendance pip : `urllib` n'est même plus
  nécessaire pour le relais (fichiers + `hashlib`/`json`).
- Les questions/réponses sont des fichiers versionnés : tout est auditable.
- Le relais ne supprime jamais une question : il la marque `answered`.
- Un run sans réponse reste un succès dégradé, jamais un crash.

## Reprise

En cas de coupure : lire ce tableau, reprendre à la première ligne `⬜`.
Chaque partie est poussée sur `v2-live-vox-c` immédiatement après validation locale.
