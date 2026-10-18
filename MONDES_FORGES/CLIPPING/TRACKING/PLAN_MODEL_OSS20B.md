# Plan fragmenté — Bascule modèle premium vers `openai/gpt-oss-20b`

> Contexte : le relais oracle sans clé est livré (P0→P6 de
> `PLAN_ORACLE_RELAY.md`). Reste la bascule du modèle premium opérationnel,
> interrompue par une coupure de session. Chaque partie = un commit local
> atomique, poussé dès que les identifiants Git sont disponibles.

## Parties

| # | Livrable | Fichiers | État |
|---|---|---|---|
| M0 | Plan fragmenté + point de reprise | `TRACKING/PLAN_MODEL_OSS20B.md` | ✅ |
| M1 | Bascule dans le code et la CI | `SHARED/brain.py`, 4 workflows | ⬜ |
| M2 | Contrats et documentation opérateur | `CONTRACTS/premium_bus_schema.json`, `README_V2.md`, `GUIDE_UTILISATION/22_MODE_CERVEAU_PARTAGE.md` | ⬜ |
| M3 | Garde-fou anti-dérive + validation | `SHARED/tests/test_model_config.py`, suite `SHARED/tests` | ⬜ |

## Périmètre exact

Remplacer `moonshotai/kimi-k3` par `openai/gpt-oss-20b` **uniquement** dans la
configuration opérationnelle :

- `SHARED/brain.py` : `DEFAULT_PREMIUM_MODEL`.
- CI : `perturabo_vox_c_analysis.yml`, `perturabo_f04_copywriting.yml`,
  `perturabo_transcribe.yml`, `perturabo_transcribe_matrix.yml`
  (`NVIDIA_NIM_MODEL`, `model_id`, libellés d'écho).
- `CONTRACTS/premium_bus_schema.json` : `model_default`.
- `README_V2.md` et `GUIDE_UTILISATION/22_MODE_CERVEAU_PARTAGE.md` : défauts
  documentés.

## Hors périmètre (ne pas réécrire l'histoire)

- `CONTINUATION_F00.md`, `TRACKING/CLIPPING_LOG.md`, `*_LOG.md`, `EXPORT/`,
  `F05_PACKAGER/OUT/`, `production_pack_*.json` : ces fichiers racontent des runs
  passés avec `kimi-k3` et doivent rester factuels.
- Aucune clé, aucun endpoint, aucune dépendance ajoutée.
- Le relais oracle reste inchangé : fichier, sans réseau.

## Reprise

En cas de coupure : reprendre à la première ligne `⬜`. Vérifier
`git status --short` avant de continuer ; ne jamais réinitialiser un travail
déjà commité.
