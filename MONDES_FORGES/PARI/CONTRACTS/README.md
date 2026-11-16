# CONTRACTS — MONDE PARI

Contrats d'interface entre frégates. Adossé au pattern des mondes existants :
chaque frégate lit l'OUT de la précédente et écrit son propre OUT selon son schéma.

| Schéma | Frégate productrice | Frégate(s) consommatrice(s) |
|---|---|---|
| `schema_match_intel.json` | F01 SENTINEL | TYRANT, F02, F00 |
| `schema_analysis.json` | F02 BREACHER | F03, F00, F05 |
| `schema_predictions.json` | F03 FORGEWARD | F04, F05 |
| `schema_pari_pack.json` | F05 PACKAGER | Warsmith, dashboard, bot Telegram |
| `schema_notes_qualitatives.json` | F00 vote (`/capture`) / opérateur | TYRANT qualitative |
| `schema_input_capture.json` | F01 SENTINEL | workflow.py Porte 1 |
| `schema_listen.json` | ORCHESTRATOR LISTEN (Worker) | pari_listen.yml, workflow.py |
| `schema_ledger.json` | F06 TRACKER (lots tokenises v2.2.8, `bundle_id` v3.2) | workflow.py `/valider-2`, `/data ledger`, `/roi settle` |
| `schema_listen.json` | Relais Telegram (v1) — `cmd` accepte `/sport`, `/sport foot\|basket`, `/basket` (codebook v6) | Worker `index.js`, `parse.py`, workflow.py |

### BASKET — contrats du second organe

| Contrat | Producteur | Consommateur |
|---|---|---|
| `pari.basket_params.v1` | `fit_basket.py` → `ARCHIVUM/state/basket_params.json` | `engine_basket.py`, `backtest_basket.py` |
| `pari.calibration_basket.v1` | `backtest_basket.py` → `ARCHIVUM/learnings/calibration_basket.json` | `/gel off` basket, `/basket` |
| `vanus.signal.v1` + `"sport": "basket"` | VANUS `speculum-basket` → `signals-basket/latest.json` | `vanus_gate.path("basket")`, `/vanus` |
| `pari.telegram.listen.v1` (v6) | Worker + `parse.py` | `workflow.py` `cmd_sport` / `cmd_basket` |

## Règles communes

1. **Zero Data, Zero Calc** : tout champ computed=`estimate` est signalé ; marché sans donnée = NO BET obligatoire, jamais estimé.
2. **Traçabilité** : chaque artefact porte `generated_at`, `source`, `siege_id`.
3. **Unités** : mises en unités (1u = 1% bankroll), jamais en devise brute.
4. **Cotes** : toujours validées par le Warsmith avant EV (le parser montre le JSON reconstitué).
