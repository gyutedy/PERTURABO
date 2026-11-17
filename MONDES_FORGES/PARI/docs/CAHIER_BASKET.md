# CAHIER BASKET — guide opérateur (PARI)

> Un second organe, la même coque. Foot maître par défaut. Gels indépendants.
> Le basket naît gelé et le reste sans `verdict: "GO"` sur `calibration_basket.json`.

## Sport actif

| Commande | Effet |
|---|---|
| `/sport` | Affiche le sport actif et l'état des deux moteurs (jamais fusionnés). |
| `/sport foot` | Repasse sur le moteur foot `dc_mle`. |
| `/sport basket` | Passe sur le moteur basket `basket_mle`. |
| `/basket` | Bascule vers basket + état détaillé (params, n_matchs, verdict calibration, gates). |

L'état vit dans `ARCHIVUM/state/sport_actif.json`. Fichier absent, cassé ou valeur
inconnue = **foot** (fail-safe, jamais basket par surprise). Basculer de sport
n'écrit **que** ce fichier : aucun `tickets_enabled` n'est modifié.

## Gel et moteur

- `/modele` affiche les deux moteurs avec leurs drapeaux respectifs.
- `/gel on|off` agit sur le **sport actif** via `moteur_sport.cfg_path()`.
- `/gel off` basket exige `ARCHIVUM/learnings/calibration_basket.json` avec
  `verdict == "GO"` (n_oos ≥ 300, brier_gap ≤ 0, ECE ≤ 0.03). Sans GO : refus explicite.
- `/valider-2` lit le drapeau du sport actif : basket gelé = aucun ticket basket,
  même si le foot est ouvert. NE PAS basculer vers le basket pour contourner le gel foot.

## Chaîne de production basket

1. Déposer les boxscores CSV (`game_id,date,team_home,team_away,pts_home,pts_away`)
   dans `ARCHIVUM/cache/basket/`, **avec** les colonnes de clôture 2-way
   `odds_home,odds_away` (cotes > 1.0). Valeur absente = `None` + trou déclaré,
   jamais 0. Sans cotes, le backtest déclare `marche_absent` et ne peut pas rendre GO.
2. `python F02_BREACHER/CODEBASE/fit_basket.py` → `ARCHIVUM/state/basket_params.json`.
3. `python F00_RADAR/CODEBASE/backtest_basket.py 2025-01-01` →
   `ARCHIVUM/learnings/calibration_basket.json`. Split OOS strict. Portes via
   `backtest_market.apply_gates` (seule autorité). Pas de cote de clôture =
   `brier_gap: null` + trou `marche_absent`, jamais estimé.
4. Verdict GO ⇒ `/gel off` basket. **Puis** paper-trading : ≥ 100 paris publiés
   sans mise, CLV moyen > 0 requis avant le premier pari réel.

Le capteur `F01_SENTINEL/CODEBASE/connectors/basket_feed.py` fait la récupération :
`python basket_feed.py --seasons 2023-24,2024-25` écrit les CSV dans
`ARCHIVUM/cache/basket/`. Boxscores via `nba_api` (gratuit) ; cotes de clôture via
l'endpoint historique The Odds API (`basketball_nba`, marché `h2h`) — **plan payant
requis**. Au 2026-11-17 la clé du dépôt est au plan gratuit (401
`HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN`) : 2 455 matchs récupérés, 0 cote,
verdict `null`, basket toujours gelé. Au moins 300 matchs OOS et `brier_gap ≤ 0`,
`ece ≤ 0.03` sont exigés pour GO.
5. Un GO n'ouvre pas le robinet : Kelly ¼, ≤ 5 % de bankroll par jour,
   ledger F06 juge unique (les perdants restent écrits).

## VANUS basket

Un seul VANUS, branche `speculum-basket` depuis `master`. Signal :
`vanus.signal.v1` avec `"sport": "basket"` dans
`SHARED/OUT/signals-basket/latest.json`. Côté PARI, le gate lit
`ARCHIVUM/vanus/signals_basket.json` (ou `PARI_VANUS_SIGNALS_PATH`).
Consensus : 2 index alignés = alarme, 1 seul = isole, jamais une probabilité
produite. Pas de `X` au basket (prolongation). `/vanus` affiche le signal du
sport actif.

## Ticket système 2/3

`build_system23(jambes, mise_par_double, corr_decote=1.0)` construit les 3 doubles
AB, AC, BC depuis exactement 3 sélections validées. Cote absente ou `p_modele`
absente = `ValueError` (jamais de valeur inventée). Affichage avant `/approve` :

```
SYSTEME 2/3 — 3 doubles, mise X par double (total 3X)
  AB  cote a×b   |  AC  cote a×c   |  BC  cote b×c
P(les 3 passent) : p1×p2×p3 = XX.X %
Si 2/3 : retour ≈ un double (quasi rembourse) — jamais garanti
Si 1/3 ou 0/3 : perte sèche 3X
Marge effective : 3 doubles = 3x la marge d'un simple
```

Le système 2/3 lisse la variance, il ne crée pas d'edge. Aucun système n'est
construit si le moteur du sport actif est gelé.

## Interdits

Estimer score/rating/proba/cote absents · baisser un gate pour forcer un GO ·
bascule de sport pour contourner un gel · renommer/réordonner `CMDS` · purger le
ledger F06 · dupliquer une autorité (μ → `engine_basket`, probas → `model_basket`,
portes → `apply_gates`, gel → `moteur_flag`) · numpy/scipy/réseau dans F02 ou le
backtest · commit de clé.

*Fer au-dedans, Fer au-dehors.*
