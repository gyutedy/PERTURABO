# CONTRACTS — MONDE PARI

Contrats d'interface entre frégates. Adossé au pattern des mondes existants :
chaque frégate lit l'OUT de la précédente et écrit son propre OUT selon son schéma.

| Schéma | Frégate productrice | Frégate(s) consommatrice(s) |
|---|---|---|
| `schema_match_intel.json` | F01 SENTINEL | TYRANT, F02, F00 |
| `schema_analysis.json` | F02 BREACHER | F03, F00, F05 |
| `schema_predictions.json` | F03 FORGEWARD | F04, F05 |
| `schema_pari_pack.json` | F05 PACKAGER | Warsmith, dashboard, bot Telegram |

## Règles communes

1. **Zero Data, Zero Calc** : tout champ computed=`estimate` est signalé ; marché sans donnée = NO BET obligatoire, jamais estimé.
2. **Traçabilité** : chaque artefact porte `generated_at`, `source`, `siege_id`.
3. **Unités** : mises en unités (1u = 1% bankroll), jamais en devise brute.
4. **Cotes** : toujours validées par le Warsmith avant EV (le parser montre le JSON reconstitué).
