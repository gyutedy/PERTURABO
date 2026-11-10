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
| `env_pari` | Cles operateur (periode de test, versionne). F00 : `FOOTBALL_DATA_ORG_KEY`, `API_FOOTBALL_KEY` (calendrier + injuries flags S15), `SPORTRADAR_API_KEY`, `SOFASCORE_RAPIDAPI_KEY` / `WHOSCORED_KEY`. ESPN voix 3 = public sans cle. Odds T-2h : `ODDS_API_KEY` (optionnelle). Oracle : `ORACLE_API_KEY` + `ORACLE_BASE_URL` + `ORACLE_MODEL` (Zro glm-5.3-flash). Charge par `workflow.load_env_pari`. | workflow.py, football_data_org.py, api_football.py, injuries.py, sportradar.py, sofascore.py, espn.py, whoscored.py, odds_api.py, tyrant.py, herald.py, notifier.py |
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
| `tests/test_input_capture_moins_plus.py` | S1 : Moins/Plus sans 2.5, cote_plate, ligue_code E1/D2 | input_capture + capteurs |
| `tests/test_f06_diag.py` | S9 : CLV ratio, agregats, n<50 lock, Platt/Beta/MC seede | clv.py + diag.py |
| `F02_BREACHER/F02_LOG.md` | Analyses (λ, matrices, probas) | F02 |
| `F03_FORGEWARD/F03_LOG.md` | EV, values, misa Kelly | F03 |
| `F04_HERALD/F04_LOG.md` | Fiches rédigées (+ usage Oracle) | F04 |
| `F05_PACKAGER/F05_LOG.md` | Packs + dashboards générés | F05 |
| `F06_TRACKER/F06_LOG.md` | Tickets loggés/settle, calibration | F06 |

Convention : chaque frégate ajoute une ligne `[TS] [mode] détail` dans son LOG.md ; le Warsmith écrit ses notes de décision dans les gates via `IW_CUSTOS.py --mode gate --notes "..."`.
