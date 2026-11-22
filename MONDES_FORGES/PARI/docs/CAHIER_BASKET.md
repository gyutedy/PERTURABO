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

## Capture Telegram (ML uniquement)

`/sport basket` puis `/capture` + le tableau Winner Bet **dans le même message** (ou
photo avec caption `/capture`). Le parseur `input_capture_basket.py` ne lit que les
colonnes `1 (ML)` / `2 (ML)` — la moneyline 2-way domicile/extérieur, sans nul.

- `1X2` (avec `X ≈ 9.60` = nul en fin de temps réglementaire) est un **autre pari** :
  stocké en `diag["1x2"]` avec `utilise: false`, jamais utilisé dans le calcul.
- `Handicap / Total 1` et `2` ne donnent que des prix, **sans la ligne** (`-4.5`, `228.5`) :
  stockés en `diag["handicap_total"]`, `utilise: false`, avec le trou
  `handicap_total_sans_ligne`. Aucune ligne inventée.
- `game_id` = le `#20071` du book ; `Demain 01:30` est résolu au moment de la capture
  dans le fuseau **Africa/Kinshasa (UTC+1)**. Les doublons de copier-coller sont ignorés.
- Réponse Telegram : `match | ML | p_modèle | EV`. JSON reconstitué :
  `F01_SENTINEL/OUT/capture_basket.json` (`A_VALIDER`). `/valider-1` reste foot-only.

Le moteur basket reste **gelé** : `/capture` produit une analyse, jamais un ticket.
`/valider-2` refuse tant que `calibration_basket.json` n'a pas `verdict: "GO"`.

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
   Le capteur gratuit `closing_odds_yahoo.py` remplit ces colonnes depuis les CSV publics
   MGM/Yahoo (`csdurfee/scrape_yahoo_odds`) : 2 454 / 2 455 matchs joints, sans clé API
   ni plan payant. Le plan gratuit `ODDS_API_KEY` n'est plus un blocage.
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

Récupération locale (v6.6) : `python F00_RADAR/CODEBASE/vanus_fetch.py --sport basket
--signal <url-de-l-export>` (URL aussi dans `PARI_VANUS_SIGNALS_URL`) écrit
`ARCHIVUM/vanus/signals_basket.json`. Sans URL ou sur hole (timeout / HTML / vide /
contrat ou sport faux), aucun fichier n'est écrit : le gate lit alors un trou.
Le veto basket est converti en code PARI (`home` → `2`, `away` → `1`) par
`vanus_gate.veto_codes(..., sport="basket")` ; `packager.build_pack(sport="basket")`
le transmet au gate. Le signal ne produit jamais de probabilité et aucun ticket
n'est construit tant que `tickets_enabled=false`.

## Systemes S1-S4 (via `/systeme`)

`/systeme 2-3|dutching|corridor|pivot` affiche le ticket avant `/approve`, depuis les
jambes du ticket produit par `/valider-2` (mise retenue = sur-ticket, sinon budget du jour).

| Systeme | Nature | Source |
|---|---|---|
| S1 2/3 | 3 doubles AB/AC/BC | `combinator.build_system23` |
| S2 dutching | 2 matchs independants, retour identique quelle que soit la jambe gagnante | `systemes.build_dutching2` |
| S3 corridor | Over L1 + Under L2 sur le **meme** match, au moins un gagnant (hors push) | `systemes.build_corridor` |
| S4 pivot couvert | Doubles Pivot-B/Pivot-C + simple Pivot x2, perte plafonnee si le pivot passe | `systemes.build_tri_lettre` |

Le corridor exige `p_corridor` calculee par le moteur (jamais estimee) et refuse L1 ≥ L2.
Le pire cas est calcule sur la **plus petite** cote : over 1.83 / under 1.84 à 1 500 FC
chacun donne −255 FC. Aucun systeme ne se construit si le sport actif est gele, si une
cote ou une probabilite manque (`ValueError`), ou si le resultat n'a pas ete montre avant
`/approve`. Ces systemes façonnent la variance — **jamais la marge** du bookmaker.

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

## Limites connues (2026-11-17)

- `fit_basket.prepare()` ancre désormais le poids temporel sur la **dernière date du jeu
  de données** (`anchor_from_rows`), plus sur `datetime.now()`. Avec une demi-vie de 45 j
  évaluée en 2026 sur des données 2023-2025, les poids tombaient à ~0 et la régularisation
  écrasait les 30 ratings à `0.0` (probabilité constante, backtest faussé).
- Le modèle reste **moins précis que le marché** : brier `0.244` vs `0.196`, gap `+0.049`
  sur 744 matchs OOS → verdict `NO-GO`, gel conservé. L'écart de ratings (~1 pt) reste
  faible face à sigma (~15) : les probabilités varient peu d'un match à l'autre.
- ~~ECE = MAE + `brier_gap` dupliqué~~ **CORRIGÉ (ETAT v6.3)** : `ece_binned()` calcule un
  vrai ECE biné (10 bins pondérés) et `apply_gates` reçoit un `logloss_gap` réel. Le gate
  `ece_max=0.03` est inchangé et désormais mesurable : ECE observé `0.005797`. Le verdict
  reste `NO-GO` sur `rps_gap` (`+0.049`) et `logloss_gap` (`+0.109`) — c'est la qualité
  prédictive, et non plus la mesure, qui est en cause. Aucun seuil n'a été assoupli.

## Interdits

Estimer score/rating/proba/cote absents · baisser un gate pour forcer un GO ·
bascule de sport pour contourner un gel · renommer/réordonner `CMDS` · purger le
ledger F06 · dupliquer une autorité (μ → `engine_basket`, probas → `model_basket`,
portes → `apply_gates`, gel → `moteur_flag`) · numpy/scipy/réseau dans F02 ou le
backtest · commit de clé.

*Fer au-dedans, Fer au-dehors.*
