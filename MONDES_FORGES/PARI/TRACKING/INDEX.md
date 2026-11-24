# TRACKING — INDEX MONDE PARI

Cartographie des journaux du monde.

| Fichier | Contenu | Alimenté par |
|---|---|---|
| `IW_CAMPAIGN_LOG.md` | Journal général (check-out/check-in, gates, reset) | IW_CUSTOS.py |
| `IW_TRANSFER_LOG.md` | Transferts inter-frégates (source → dest, md5) | IW_CUSTOS.py |
| `TYRANT/TYRANT_LOG.md` | Verdicts de carte GO/NO-GO | TYRANT |
| `TYRANT/QUALITATIVE_LOG.md` | Verdicts du filtre non-binaire borné (exclusions, seuils, NO BET rec.) | TYRANT qualitative |
| `F05_TICKETS/F05_TICKETS_LOG.md` | Compositions de tickets + backroll par campagne (v2) | F05 combinator |
| `SHARED/STATE/campagne.json` | État du cycle de campagne Telegram (/start → /valider-2). v2.2.8 `consumed_legs`, `capture_id`, `current_token`, `budget_seq`. v2.2.5 `bankroll_fc` persiste + `budget_fc`/`surticket_fc` forces. v3.2 `bundle_id`. | workflow.py |
| `ORCHESTRATOR/CODEBASE/doctor.py` | Evidence GO/CHECK/FAIL (`--offline --json`). Cles = noms. Gate n<300 bruit / 300-499 observation / >=500 moteur. CLV median 30j < -3 pts = FAIL. n<30 variance (S9). | `/status` `/status doctor` |
| `ORCHESTRATOR/CODEBASE/research_bundle.py` | Dossier `ARCHIVUM/research/B-XXX` + `manifest.json` SHA-256 a `/valider-1`. `--verify`. Gap declare, jamais comble. | workflow.py `/valider-1` |
| `ARCHIVUM/research/` | Bundles hashés (gitignore). Token L-XXX porte `bundle_id`. | research_bundle.py |
| `F06_TRACKER/CODEBASE/journal.py` | Journal 2 volets : procedure (freeze, immutable) + outcome (settle). Holes, jamais 0. | ledger.py freeze_lot / settle_lot |
| `F06_TRACKER/CODEBASE/clv.py` | `clv = cote_prise / cote_cloture - 1`. Agregats median / % >0 / mean_w. Combo = produit closes. | ledger.settle_lot |
| `F06_TRACKER/CODEBASE/diag.py` | Platt + Beta-Binomial + P(EV>0) MC seede. n<50 = diagnostic, jamais verdict/mise. | `/data diag` |
| `F03_FORGEWARD/CODEBASE/kelly_route.py` | Kelly 1/8 defaut, 1/4 si ECE<=0.03 et P(EV>0)>=0.55 et n>=50. Combo MC conjoint. P/ECE absents = 1/8 + holes. | forgeward.py / combinator.py / ledger.freeze_lot |
| `config/kelly.json` | fraction_default 0.125, plafond 0.25, p_ev_positif 0.55, ece 0.03, n_lock 50. | kelly_route.py |
| `tests/test_kelly_route.py` | S10 : gate 1/4, n<50, absents + holes, MC conjoint, stamp sans toucher mise_fc | kelly_route.py |
| `F05_PACKAGER/CODEBASE/marches.py` | S11 : election, couverture EV>=3%, anti meme-navire, mono, floors. Canon `/marches` | workflow.py `/marches` / combinator.py |
| `ARCHIVUM/learnings/market_election_log.json` | Append-only elections marches. `/status` alerte >60% | marches.append_election |
| `tests/test_marches.py` | S11 : 0 match→0 ticket, meme navire, mono, 10 jambes, floor refuse | marches.py / combinator.py |
| `F03_FORGEWARD/CODEBASE/market_scorer.py` | S12 : portes A1-A4 hors score, B1-B6 0-1, veto F03. Jamais Poisson. v4.6.1 : `ligues` conservees dans load_profiles | forgeward.py |
| `ARCHIVUM/learnings/market_profiles.json` | Poids / seuils a priori (versionne). Ne pas retuner a la main. | market_scorer.load_profiles |
| `tests/test_market_scorer.py` | S12 : A1-A4, overround 24.6% vs 18.7%, MT poids, EV inchange | market_scorer.py / forgeward.py |
| `config/state_factors.json` | S13 : att x0.90 max 2, milieu x0.96, def adv x1.06, gk x1.05, cap ±20%. | state_factors.py |
| `F02_BREACHER/CODEBASE/state_factors.py` | Facteurs etat lambda table A. Vide = x1.00 + holes. | breacher.analyse_match |
| `tests/test_state_factors.py` | S13 : parseur 2e table, p_o25, cap, rotation flag, derby veto | input_capture + state_factors + qualitative |
| `F03_FORGEWARD/CODEBASE/market_scorer.py` pieges | S14 : cote_plate / marge_anomalique / cote_figee_sur_news / marche_vitrine. 3e lecture capture/T-2h/T-0 | forgeward.py / data_view.py |
| `tests/test_pieges.py` | S14 : MT plate x10, marge 22% retire, figee+news, /data SCORER+PIEGES | market_scorer.py / forgeward.py / data_view.py |
| `F01_SENTINEL/CODEBASE/connectors/injuries.py` | S15 : API-Football injuries → 4 flags TYRANT. Holes si KO. Jamais un P / jamais un 2e lambda | enrich.py / breacher.py / qualitative.py |
| `tests/test_injuries.py` | S15 mock, holes, anti-double-lambda, veto sans S13 | injuries.py + qualitative.py |
| `TYRANT/CODEBASE/metro.py` | S16 Oracle meta-review avant `/valider-2`. Zero digit. Cle absente = skip | workflow.py `/valider-2` |
| `config/ticket_friction.json` | S16 fees 0.005 + slippage 0.005. Seuil = EV_FLOOR + fees + slip. Jamais < 0.03 | ticket_friction.py |
| `F05_PACKAGER/CODEBASE/ticket_friction.py` | Charge friction, `effective_floor` | combinator `--ev-floor` |
| `F03_FORGEWARD/CODEBASE/backtest_weights.py` | R7 poids B1-B6. n<50 lock. Une maj journalisee. Seed 42. v4.6.1 : renorm somme 1.0 | market_profiles.json |
| `ARCHIVUM/learnings/scorer_weight_journal.json` | Journal unique maj poids (gitignore si vide) | backtest_weights.retune |
| `tests/test_oracle_metro.py` | S16 zero chiffre, mock HTTP, fees, `/approve` mismatch | metro.py + friction + workflow |
| `tests/test_backtest_weights.py` | S16 n<50 lock, write once, ligue x marche, seed 42 | backtest_weights.py |
| `config/clv.json` | Cibles 55% / +0.5 pt, n_lock 50, n_variance 30, mc_seed 42. | clv.py / diag.py |
| `ORCHESTRATOR/CODEBASE/churn.py` | Compteur `config/` : >2 changements / 7j hors calibration → `churn_suspect`. | config/churn.json |
| `F03_FORGEWARD/CODEBASE/devig.py` | Devig multiplicatif defaut + additif 2e passe. Gap journalise. Cote unique = hole. | forgeward.py |
| `config/devig.json` | `default_method: multiplicative`. Bonus double_confirmation (init 1 pt). Pas un producteur de p. | devig.py |
| `F05_PACKAGER/CODEBASE/compose.py` | EV compose net = produit (1+edge_net)-1. `jambe_edge_net_negatif` info, pas rejet. | combinator.py |
| `config/market_priority.json` | Paliers marches. Palier suivant si >= 30 tickets mesures. corners/cards fermes → holes. | market_priority.py |
| `F02_BREACHER/CODEBASE/league_fit.py` | Fit rho / bonus domicile / part_mt1 depuis CSV cache. n<4 → defaut. | capteurs.py `fit-league` |
| `F02_BREACHER/CODEBASE/baseline.py` | Moyennes ligue saison complete + EMA 45j. Split att/def. Saison absente = trou. | breacher.league_averages |
| `config/league_fit.json` | Demi-vie EMA, grille rho, clips, defauts (1.10 / -0.13 / 0.44). | league_fit.py / baseline.py |
| `ARCHIVUM/learnings/league_params.json` | Parametres fit (gitignore). Ligue absente → `params: default`. | league_fit.py |
| `F00_RADAR/CODEBASE/empirique.py` | Taux O2.5 saison vs P_modele. Ecart >= 0.20 → flag `incoherence_modele_empirique`. | radar.py / tyrant.py |
| `F00_RADAR/CODEBASE/walkforward.py` | Backtest cut-off explicite. Brier/RPS/ECE, hit EV>=3%, Kelly 1/4. Jamais in-sample. | capteurs.py `walk-forward` |
| `config/empirique.json` | Seuil gap 0.20, ev_min 0.03, kelly 0.25, ece_bins 10. | empirique.py / walkforward.py |
| `ARCHIVUM/learnings/backtest_report.json` | Rapport walk-forward (gitignore). Odds absentes = holes. | walkforward.py |
| `.github/workflows/pari_elo_fill.yml` | ClubElo hebdo → elo.json + shares elo_slope. Timeout = trou. Zero cle. | Actions lundi 05:00 UTC |
| `F05_PACKAGER/CODEBASE/market_priority.py` | Gate palier + holes sans_data. n = settle G/P seulement. | combinator.py |
| `config/` | Compteur churn versionne (`churn.json` au 1er record). Calibration exclue. | churn.py |
| `ARCHIVUM/learnings/lots.json` | Ledger F06 lots (token L-XXX = cle, snapshot T0). F06 n'apprend pas. | workflow.py `/valider-2`, ledger.py |
| `CONTRACTS/schema_ledger.json` | Contrat lot / jambes / snapshot T0 / settle G/P/EN_ATTENTE | F06 ledger.py |
| `ORCHESTRATOR/CODEBASE/data_view.py` | Vues `/data` compact + `/data N` fiche (affichage, jamais Poisson) | workflow.py `cmd_data` |
| `ORCHESTRATOR/LISTEN/` | Relais webhook Telegram (Worker + parse.py + inbox_capture.py v2.10.1) | Cloudflare / e2e_listen |
| `.github/workflows/pari_listen.yml` + `pari_daily.yml` | tesseract-ocr + fra (P4) avant siege. Inbox = script Python, plus de heredoc YAML. | Actions |
| `F01_SENTINEL/IN/capture_telegram.md` | Inbox capture texte colle depuis Telegram. Photo = capture_telegram.jpg / .png / .webp. `resolve_capture` prend le plus recent (v2.10). | pari_listen.yml |
| `CONTRACTS/schema_listen.json` | Contrat update Telegram → {cmd, capture_text, chat_id} | Worker + parse.py |
| Repo vivant | `gyutedy/PERTURABO` branche principale `pari-forge-perturabo-xs4c` (pas `v2-live-vox-c`) | Worker GH_REF |
| Worker LIVE | `https://pari-listen.pari-listen.workers.dev` | `.github/workflows/worker_deploy.yml` (CLOUDFLARE_* dans env_pari) |
| `F00_RADAR/CODEBASE/{capteurs,enrich,vote,cache,http_util,odds_watch}.py` | Enrich `/capture` : binaire + vote OUT/DOUTE/IGNORE. T-2h + T-0 = `odds_watch` | workflow.py `/capture` `/valider-1` ; `pari_odds_t2h.yml` `pari_odds_t0.yml` |
| `F01_SENTINEL/CODEBASE/connectors/odds_api.py` | The Odds API (h2h + totals 2.5). Matching nom + difflib 0.9. Cache 1 hit/ligue/jour | odds_watch.py |
| `ARCHIVUM/odds/` | Snapshots T-2h (`latest.json`, `t2h_*.json`) + T-0 (`latest_t0.json`, `t0_*.json`). T-0 n ecrase pas latest.json. | odds_watch.persist |
| `env_pari` | Cles operateur. **Plus versionne** depuis v6.5 : gitignored, reconstruit au runtime par `.github/scripts/write_env_pari.py` depuis 19 Secrets GitHub. F00 : `FOOTBALL_DATA_ORG_KEY`, `API_FOOTBALL_KEY` (calendrier + injuries S15), `SPORTRADAR_API_KEY`, `SOFASCORE_RAPIDAPI_KEY` / `WHOSCORED_KEY`. Odds : `ODDS_API_KEY`. Oracle : `ORACLE_*` / `ZRO_*`. Charge par `workflow.load_env_pari`. | 5 workflows + write_env_pari.py |
| `.github/scripts/write_env_pari.py` | Reconstruit `env_pari` depuis les Secrets GitHub, non-vides seulement, valeurs jamais affichees. | 5 workflows (daily, listen, odds_t0/t2h, worker_deploy) |
| `tests/test_write_env_pari.py` | Migration secrets : noms seulement, fichier ecrit, 7/7. | CI locale |
| `ARCHIVUM/cache/f00/` | Cache 1 hit / equipe / jour (gitignore) | F00 enrich |
| `ARCHIVUM/fixtures/notes_qualitatives.json` | Notes votees F00 (OUT → TYRANT) | enrich.py |
| `F00_RADAR/F00_LOG.md` | Scans de ligue (nombre matchs, top verdicts) | F00 RADAR |
| `F01_SENTINEL/F01_LOG.md` | Collectes + nettoyages de donnees | F01 |
| `F01_SENTINEL/OUT/capture_parsed.json` | JSON reconstitue de la capture (txt/md/png/pdf/docx). v4.0 : `holes` Moins/Plus, `cote_plate` | F01 input_capture |
| `TRACKING/PLAN_PARI_CONSOLIDE.md` | Plan d execution unique v3.5+v4 (packs S0–S16) fige | Warsmith / agent |
| `config/moteur.json` | Interrupteur tickets_enabled + engine dc_mle + gates RPS/ECE | moteur_flag.py |
| `F02_BREACHER/CODEBASE/moteur_flag.py` | Seul lecteur du drapeau. Illisible = GELE | workflow `/modele` `/gel` `/valider-2` |
| `F00_RADAR/CODEBASE/market_csv.py` | CSV football-data, trous declares, jamais invente | inventaire / fit_dc |
| `F02_BREACHER/CODEBASE/model_dc.py` | Dixon-Coles MLE : lambdas, log_pmf, priors, poids temporel | fit_dc.py |
| `F02_BREACHER/CODEBASE/fit_dc.py` | Fit ligue MLE. n<60 / equipe absente = holes. Elo jamais 1500 | dc_params.json |
| `tests/test_model_dc.py` | V2a : 0-0, None, n<60, ghost drop, stdlib, pas breacher | model_dc.py / fit_dc.py |
| `F02_BREACHER/CODEBASE/engine_dc.py` | Cablage MLE dans breacher. Equipe absente = Poisson + holes | breacher.analyse_match |
| `tests/test_engine_dc.py` | V2b : MLE vs Poisson, ghost, ligue absente, gel intact | engine_dc.py / breacher.py |
| `F00_RADAR/CODEBASE/backtest_market.py` | V2c : walk-forward RPS/ECE/logloss vs marche. n<300 = pas de GO | calibration_moteur.json |
| `tests/test_backtest_market.py` | V2c : gates, cutoff, cote<=1, 0-0, gel intact | backtest_market.py |
| `ARCHIVUM/learnings/calibration_moteur.json` | Blob calibration (gitignore). `/modele` `/gel off` | backtest_market.py |
| `F00_RADAR/CODEBASE/vanus_fetch.py` | VC : CSV Big 5 football-data. Timeout/HTML = hole. Pas de gate | cache f00 |
| `tests/test_vanus_fetch.py` | VC : skip, timeout, HTML, vide, hors_couverture, gel intact | vanus_fetch.py |
| `F00_RADAR/CODEBASE/vanus_gate.py` | V3 : greffe vanus.signal.v1. Jackpot veto, alarme info, isole pass. Jamais un p | ARCHIVUM/vanus |
| `tests/test_vanus_gate.py` | V3 : skip, contrat, match miss, jackpot/alarme/isole, stamp p intact, gel | vanus_gate.py |
| `F05_PACKAGER/CODEBASE/packager.py` | V4 : greffe vanus_gate. Jackpot drop, alarme flag, p/EV intacts | vanus_gate.py |
| `tests/test_vanus_packager.py` | V4 : jackpot veto, alarme keep, skip hole, combo drop, gel intact | packager.py |
| `ORCHESTRATOR/CODEBASE/workflow.py` `cmd_vanus` | V5 : `/vanus` `/vanus ID` lecture vanus.signal.v1. Jamais un p | vanus_gate.py |
| `tests/test_vanus_telegram.py` | V5 : skip, contrat, absent, jackpot/alarme/isole, id, gel intact | workflow.py / parse.py |
| `F06_TRACKER/CODEBASE/ledger.py` `stamp_vanus` | V6 : freeze T0 flags vanus. Jamais un p. 7 args intact | vanus_gate.py |
| `tests/test_vanus_ledger.py` | V6 : jackpot/alarme/isole/skip/miss, p intact, gel | ledger.py |
| `F00_RADAR/CODEBASE/vanus_calibrate.py` | VX : fetch CSV + fit_dc + backtest GO/NO-GO. n<300 = pas de GO | calibration_moteur.json |
| `tests/test_vanus_calibrate.py` | VX : skip/timeout/HTML, n<300, gel intact, BOM Div ; v6.6 verdict resume 47/47 | vanus_calibrate.py |
| `ARCHIVUM/learnings/verdict_foot.json` | Resume versionne `pari.verdict_foot.v1` (verdict n/seasons/cutoff/reasons/holes, jamais de donnees brutes). `/modele` en repli. | `vanus_calibrate.save_verdict` |
| `F00_RADAR/CODEBASE/backtest_scores_foot.py` | T5 : backtest 1X2 walk-forward, refit strictement anterieur, Brier/RPS/logloss/ECE/CLV, verdict via `apply_gates`. Sortie gitignore. | `calibration_scores_foot.json` |
| `tests/test_backtest_scores_foot.py` | T5 : 120 rows, n_oos=40, refit < cutoff, marche_absent, n<100, GO/NO-GO (21/21) | backtest_scores_foot.py |
| `vanus_fetch.fetch_signal` / `--sport basket --signal <url>` | V6 : export `vanus.signal.v1` sport=basket → `ARCHIVUM/vanus/signals_basket.json` ; URL via `PARI_VANUS_SIGNALS_URL` ; holes, jamais un p. CSV foot inchange. | `vanus_fetch.py` |
| `vanus_gate.VANUS_TO_PARI_BASKET` | V6 : mapping inverse (jackpot home → veto `2`, plus `away`) ; `packager.build_pack(sport=)`. | `vanus_gate.py` / `packager.py` |
| `tests/test_input_capture_moins_plus.py` | S1 : Moins/Plus sans 2.5, cote_plate, ligue_code E1/D2 | input_capture + capteurs |
| `tests/test_f06_diag.py` | S9 : CLV ratio, agregats, n<50 lock, Platt/Beta/MC seede | clv.py + diag.py |
| `F02_BREACHER/F02_LOG.md` | Analyses (λ, matrices, probas) | F02 |
| `F03_FORGEWARD/F03_LOG.md` | EV, values, misa Kelly | F03 |
| `F04_HERALD/F04_LOG.md` | Fiches rédigées (+ usage Oracle) | F04 |
| `F05_PACKAGER/F05_LOG.md` | Packs + dashboards générés | F05 |
| `F06_TRACKER/F06_LOG.md` | Tickets loggés/settle, calibration | F06 |

### BASKET — second organe (hors production, gelé)

| Fichier | Contenu | Alimenté par |
|---|---|---|
| `config/moteur_basket.json` | Interrupteur basket (`tickets_enabled=false`, engine `basket_mle`, gates brier/ece/n≥300). Indépendant du gel foot. | Warsmith / `moteur_flag.set_tickets(path)` |
| `ARCHIVUM/state/sport_actif.json` | Sport actif (`foot`/`basket`). Absent/cassé/inconnu = **foot**. | `moteur_sport.set_sport` via `/sport` `/basket` |
| `ARCHIVUM/cache/basket/*.csv` | Boxscores `game_id,date,team_home,team_away,pts_home,pts_away`. Absent = trous déclarés. | capteur F01 (jamais le moteur) |
| `ARCHIVUM/state/basket_params.json` | Params fit MLE ridge (`pari.basket_params.v1`). Gitignored. | `fit_basket.py` |
| `ARCHIVUM/learnings/calibration_basket.json` | Verdict OOS (`pari.calibration_basket.v1`) via `apply_gates`. Sans GO = gel. | `backtest_basket.py` |
| `ARCHIVUM/vanus/signals_basket.json` | Signal VANUS basket (`sport=basket`), jamais un p. Cible de `vanus_fetch.py --sport basket --signal <url>` (URL = `PARI_VANUS_SIGNALS_URL`). | VANUS `speculum-basket` → `vanus_fetch.fetch_signal` |
| `F00_RADAR/CODEBASE/market_basket.py` | Contrat CSV boxscores + cotes 2-way `odds_home`/`odds_away` (absentes = None, jamais 0). | `fit_basket`, `backtest_basket` |
| `F01_SENTINEL/CODEBASE/connectors/basket_feed.py` | Capteur : boxscores `nba_api` + cotes historiques The Odds API → CSV `ARCHIVUM/cache/basket/`. Cote absente = trou. | run manuel / capteur F01 |
| `ARCHIVUM/cache/basket/*.csv` | Cache gitignored : 2023_24.csv (1230), 2024_25.csv (1225). Cotes de cloture Yahoo remplies (2454/2455). | `basket_feed.py` + `closing_odds_yahoo.py` |
| `F01_SENTINEL/CODEBASE/connectors/closing_odds_yahoo.py` | Cotes MGM/Yahoo gratuites (depot public `csdurfee`). Jonction stricte date+équipes, trou si absent, jamais de cote estimée. | run manuel / capteur F01 |
| `F01_SENTINEL/CODEBASE/input_capture_basket.py` | Capture Telegram basket : **ML uniquement** (`1 (ML)`/`2 (ML)`), 1X2 et Handicap/Total = diag non utilisés, heure Kinshasa, `game_id` = `#xxx`. | `/sport basket` + `/capture` |
| `F01_SENTINEL/OUT/capture_basket.json` | JSON reconstitué basket (`A_VALIDER`) + résumé `match | ML | p | EV`. | `input_capture_basket.py` |
| `F02_BREACHER/CODEBASE/{model,fit,engine}_basket.py` | Normal + Monte-Carlo, MLE ridge, μ/σ sans probabilité. `fit.prepare` ancre l'âge sur la dernière date des rows (plus `datetime.now()`). | `backtest_basket` |
| `F02_BREACHER/CODEBASE/moteur_sport.py` | Sélecteur foot/basket, fail-safe foot. | `/sport` `/basket` `/modele` `/gel` `/valider-2` |
| `F00_RADAR/CODEBASE/backtest_basket.py` | Split OOS strict, Brier/ECE vs marche, portes uniques. v6.3 : vrai ECE biné + logloss réel (plus de MAE ni de `brier_gap` dupliqué). Verdict NO-GO (brier +0.049, logloss +0.109, ECE 0.006). | `calibration_basket.json` |
| `F05_PACKAGER/CODEBASE/combinator.py` | `build_system23` (S1 : 3 doubles, cote/p absente = `ValueError`). | `/combos systeme 2-3` |
| `F05_PACKAGER/CODEBASE/systemes.py` | S2 dutching, S3 corridor, S4 pivot couvert. Variance façonnée, jamais la marge. `ValueError` si cote/p absente. | `/systeme` |
| `ORCHESTRATOR/CODEBASE/workflow.py` `cmd_systeme` | Affichage S1-S4 avant `/approve` ; refus si moteur gelé ; CMDS 25 clés. Relais `parse.py` + `index.js`. | `/systeme 2-3\|dutching\|corridor\|pivot` |
| `tests/test_systemes.py` | S1 régression, S2/S3/S4, refus zero-data, pire cas corridor −255 FC, commande enregistrée (22/22). | CI locale |
| `docs/CAHIER_BASKET.md` | Guide opérateur basket (capture ML, portes, verdict, paper-trading CLV, limites connues). | Warsmith |
| `tests/test_*basket.py`, `test_moteur_sport.py`, `test_system23.py`, `test_workflow_basket.py`, `test_input_capture_basket.py`, `test_closing_odds_yahoo.py` | Suite unitaire PARI verts (offline) : 111/111 sur 6 fichiers basket. | CI locale |

| `ORCHESTRATOR/CODEBASE/workflow.py` `_systeme_marge` / `cmd_systeme` | v6.6 : affiche `Marge effective : X%` (moyenne des `overround`/`marge` de top3.json sur les jambes, `— (trou)` sinon) en plus du p_break_even et des pires cas, avant `/approve`. | `/systeme` |
| `tests/test_systemes.py` | v6.6 : marge effective 0.05 sur 2 jambes + trou, total 24/24. | CI locale |
| `F05_PACKAGER/CODEBASE/packager.py` `build_pack(sport=)` | v6.6 : sport transmis au gate VANUS (defaut foot) ; mapping veto basket inverse corrige (`home` → `2`). | `vanus_gate.py` |
| `tests/test_vanus_packager.py` | v6.6 : jackpot basket drop la selection `2`, 25/25. | CI locale |

| `F02_BREACHER/CODEBASE/basket_total.py` | v8.7 : marche Total = points des DEUX equipes, ridge stdlib, sigma_total OOS (19,17 sur 972 matchs). Cotes Under/Over Winner -> EV diagnostic. |
| `tests/test_basket_total.py` | v8.7 : state sans fuite, intercept non penalise, sigma OOS, p_over (7/7). |
| `F02_BREACHER/CODEBASE/baseline.py` `ht_u1.5_empirique` | v10.3 : taux empirique HT < 1.5 buts (E1 0,6674 / 1284 matchs), transpose dans `league_averages`. |
| `F03_FORGEWARD/CODEBASE/forgeward.py` `MT_OU_1.5` | v10.3 : groupe HT Under/Over 1.5, proba depuis la matrice mi-temps, EV vs cotes Winner. HSH reste diagnostic. |
| `tests/test_ht_market.py` | v10.3 : parsing capture, tableau, proba, EV, scorer (7/7). |
| `ORCHESTRATOR/CODEBASE/data_view.py` `marches_ecartes` | v10.4 : `/data N` liste les selections calculees mais non retenues avec cote + motif (EV/seuil/scorer/piege). |
| `tests/test_data_ecartes.py` | v10.4 : motifs EV negatif, seuil, scorer, section fiche (6/6). |
| `F06_TRACKER/CODEBASE/winner_watch.py` | v10.0 : etat same-book Winner (captures, devinage match, alertes 2h, CLV premiere/derniere cote). `ARCHIVUM/winner/watch_{sport}.json`. |
| `tests/test_winner_watch.py` | v10.0 : tokens, devinage, alertes 2h, anti-spam, stop, CLV same-book (12/12). |
| `ORCHESTRATOR/LISTEN/src/index.js` (scheduled) + `wrangler.toml` | v10.0 : rappels Telegram toutes les 2h via le Worker Cloudflare (cron GitHub indisponible sur le fork), arret kickoff/`stop`. |
| `F02_BREACHER/CODEBASE/basket_prior.py` | v9.0 : experience prior marche (correction de l'ecart vs implicite). OOS gap +0,0004 -> aucun edge, `enabled=false`, jamais producteur de p. |
| `tests/test_basket_phases.py` | v9.0 : fenetre fit, convergence visible, prior desactive, paper basket bloque (7/7). |
| `config/basket_prior.json` | v9.0 : resultat OOS du prior (desactive). |
| `F02_BREACHER/CODEBASE/basket_calib.py` | v8.6 : ridge stdlib ratings+repos+forme, OOS 744, brier 0,217 vs marche 0,195 -> NO-GO (aucun seuil baisse). |
| `tests/test_basket_calib.py` | v8.6 : features sans fuite, poids, verdict, zero ticket (8/8). |
| `F03_FORGEWARD/CODEBASE/winner_pmodel_basket.py` | v8.5 : `p_modele` ML via MLE NBA + devig Winner. Garde `fiable`/`ratio_dispersion` : EV artificiels si le moteur ne discrimine pas (cas reel, 0,135). Aucun ticket. |
| `tests/test_winner_pmodel_basket.py` | v8.5 : p, EV, total diagnostic, equipe inconnue, garde discrimination (9/9). |
| `ORCHESTRATOR/LISTEN/capture_llm.py` | v8.8 : fusion `/capture` photo -> LLM vision -> tableau Winner -> input_capture. Repli OCR si LLM en echec, aucun ticket. |
| `tests/test_capture_llm.py` | v8.8 : sport, tableaux foot/basket, jour relatif, repli (8/8). |
| `F06_TRACKER/CODEBASE/paper_trader.py` | v8.0 : journal des paris simules Winner (EV >= 3 %, cote prise, p_modele, EN_ATTENTE), aucun ticket ni mise. `ARCHIVUM/winner/paper_trades.json`. |
| `tests/test_paper_trader.py` | v8.0 : seuil EV, zero ticket, zero HSH, zero duplication, contrat (8/8). |
| `F03_FORGEWARD/CODEBASE/winner_pmodel.py` | v7.4 : `p_modele` calcule par `fit_dc` (CSV historiques), jamais lu dans la cote ; EV `p*cote-1` et `edge_net` vs devig Winner. Equipe absente = trou. Aucun ticket, HSH exclu. |
| `tests/test_winner_pmodel.py` | v7.4 : alias, EV formula, trou equipe/cote, zero ticket, stdlib (12/12). |
| `F01_SENTINEL/CODEBASE/llm_vision.py` | v7.0 : lecteur LLM vision **generique** (OpenAI-compatible). Cle/base/model depuis `env_pari` uniquement, deux lectures independantes, jamais un p ni un log de cle. | capture Telegram / `winner_vision.py` |
| `F01_SENTINEL/CODEBASE/winner_vision.py` | v7.0 : capture transcrite -> `vanus.slate.v1` avec gardes V1-V4 ; N matchs (>10) ; en-tete unique en haut. | `llm_vision.py` / `--in` |
| `F00_RADAR/CODEBASE/winner_ingest.py` | v7.0 : slate Winner -> vue indexee par match_key ; contrat faux/cross-sport/absent = vide + trou ; `diagnostic_only` marque. | `vanus_fetch.py --kind slate` |
| `vanus_fetch.py --kind slate` | v7.0 : facteur automatique, `vanus.slate.v1` + sport valides -> `ARCHIVUM/winner/slate_{sport}.json`. URL `PARI_WINNER_SLATE_URL`. | `winner_ingest.py` |
| `ORCHESTRATOR/CODEBASE/workflow.py` `cmd_winner` | v7.0 : `/winner foot\|basket`, lecture seule, cotes + trous + rappel devig F03, jamais un p. CMDS 27 cles. | `/winner` |
| `tests/test_winner*.py` | v7.0 : vision 18/18, ingest 9/9, telegram 9/9 ; VANUS `test_winner` 30/30. | CI locale |

Convention : chaque frégate ajoute une ligne `[TS] [mode] détail` dans son LOG.md ; le Warsmith écrit ses notes de décision dans les gates via `IW_CUSTOS.py --mode gate --notes "..."`.
