# CONTINUATION — MONDE FORGE PARI

> Doc de continuité : état d'avancement, prochaine étape, décisions verrouillées.

## ÉTAT v2 — VERSION FONCTIONNELLE (2026-10-29)

- [x] **Phase 0** : AUDIT_CORPUS.md (conformité doctrine vs transcriptions, 34/97 archivées, TO_CONFIRM bloqués pour décision, 0 périmée).
- [x] **Phase 1** : flux capture officiel — `F01_SENTINEL/CODEBASE/input_capture.py` (ligue/coupe, date, heure, 1X2/O-U/MT/BTTS, JSON reconstitue, validation operateur avant tout calcul, Zero Data jamais devine) + contrat `schema_input_capture.json`.
- [x] **Phase A (multi-format)** : `extract_input.py` accepte txt, md, png/jpg, pdf, docx. Tableau markdown Winner Bet parse nativement (11 matchs de la capture type). Image sans tesseract = Zero Data, Zero Calc (pas de crash).
- [x] **Phase 2** : infos non binaires BORNÉES — `TYRANT/CODEBASE/qualitative.py` (exclusion de marchés, seuil EV relevé, NO BET recommandé ; jamais dans les maths). Contrat `schema_notes_qualitatives.json` avec table bornée.
- [x] **Phase 3** : **Top 3 marchés + score commun 01-10** — `F03_FORGEWARD/CODEBASE/top3.py` (tri EV puis p_modele ; score = 30% qualité data + 40% proba max + 30% edge EV ; buckets HAUTE ≥7 / MOYENNE ≥5 / FAIBLE) + **PREVIEW 1** `SHARED/OUT/preview1.html` (données brutes, menu déroulant, charte PERTURABO, responsive). TOP3.md = base du message /data.
- [x] **Phase 4** : combinaisons + **backroll** — `F05_PACKAGER/CODEBASE/combinator.py` (ticket sûr = classe A score le plus haut, reste réparti ; FAIBLE/NO BET exclus ; > 4 jambes → division en deux classes ; budget FC + sur-ticket + unités si taux fourni).
- [x] **Phase 5** : **PREVIEW 2** `SHARED/OUT/preview2.html` (ticket final hommage PERTURABO, cartes, budget, responsive).
- [x] **Phase 6** : workflow Telegram — `ORCHESTRATOR/CODEBASE/workflow.py` (/start, /capture, /bankroll, /budget JOUR SURTICKET, /surticket, /combos, /valider-1, /valider-2, /data, /status, /roi, /stop) + injection stats gracieuse à /valider-1.
- [x] **Phase 7** : contrat `schema_ticket_final.json`, docs à jour (GUIDE/README/TRACKING/CONTINUATION), workflow GH (previews + Pages), tests e2e par groupe (g1 9/9, g2 11/11, g3 11/11, final).

## DECISIONS VERROUILLÉES v2 (campagne)

| Décision | Choix | Raison |
|---|---|---|
| Input principal | **capture du book (txt/md/png/pdf/docx) → texte → JSON reconstitue → validation Porte 1** | l'operateur fournit ligue, date, heure, marches, cotes — rien de devine |
| Stats historiques | football-data.co.uk + ClubElo (sans clé), injectées à /valider-1 | pas de stats → Zero Data, Zero Calc → NO BET, jamais d'invention |
| Infos non binaires | **bornées** : exclusion marchés / seuil EV relevé / NO BET recommandé ; HORS maths | jamais de « +0,3 but » inventé par un LLM |
| Top 3 marchés | forgé par le monde (EV puis p_modele), opérateur choisit la cible après relecture | la chaîne propose, l'opérateur dispose |
| Score commun | 01-10 (30% qualité data + 40% proba + 30% edge), buckets HAUTE/MOYENNE/FAIBLE, comparable entre campagnes | scoring « à la clipping », sert à composer les tickets |
| Tickets | SÛR = classe A (score le plus haut) ; reste réparti ; FAIBLE/NO BET exclus ; > 4 jambes → division | complexité mathématique des combinés longs |
| Backroll | 3 couches : `/bankroll` pot global (persiste) ; `/budget JOUR SURTICKET` plafond jour + mise FORCEE ticket sur ; reste divise ; mise min 100 FC | gestion du pot sans martingale, ticket sur force |
| Previews | 2 : Preview 1 (brutes, début de campagne) + Preview 2 (ticket final, charte PERTURABO) ; GH Pages ; responsive | relecture opérateur aux 2 portes de campagne |
| Message /data | 2 vues : table compacte + `/data N` fiche. Affichage ≠ maths. HORS ticket final | séparation lecture d'analyse / ticket final |
| Oracle | clé premeum optionnelle (Secret), exécution HORS du job du monde forger, qualitatif seulement | jamais au centre, jamais dans les chiffres |

## ÉTAT AU DÉPÔT INITIAL (forge v1)

- [x] Squelette complet : 10 composants (F00-F06, TYRANT, ORCHESTRATOR, IW_CUSTOS)
- [x] Moteur math : Dixon-Coles (correction bas-scores), Poisson par mi-temps, λ par part
- [x] De-marging (normalisation overround), EV, Kelly 1/4, scanner combinés
- [x] Mode radar (scan ligue) + mode siège + pack + tracker + demo
- [x] Pari pack (TOP 10-20, NO BET list, loterie isolée)
- [x] Dashboard HTML statique (Chart.js CDN, charte Iron Warriors, mode discret, responsive)
- [x] Ledger tickets (prix gagnants ET perdants) + calibration + scoring pronostiqueurs
- [x] Meta-prompt quantitatif (CONTRACTS/quant_analyste_prompt.md)
- [x] Workflow GitHub Action cron + bot Telegram (squelette fonctionnel)
- [x] Pipeline testé de bout en bout sur ligue simulée (18 matchs)

## ÉTAT AU DÉPÔT v1.2 (27.10) — RESSOURCES transcriptions (knowledge_base)

- [x] `ARCHIVUM/knowledge_base/RESSOURCES/` : zone d'accueil complète pour les 64 vidéos de la chaîne The Football Bank (catalogue_videos.csv maître = id, titre, url, catégorie, upload_date, fichier, date_recuperation, statut).
- [x] Templates : `TPL_transcription.md` (id, dates pub/récupération, statut) + `TPL_fiche.md` (dépouillement avec **verdict d'âge obligatoire** par info).
- [x] Script `ingest_transcripts.py` : `--add` (ingestion auto par id détecté, classification auto par titre, 14 anciennes intèactes, doublons sautés), `--dates id=AAAA-MM-JJ` (pose les dates dans catalogue + en-têtes), `--status`, `--freshness` (vérification obsolète/je vieillissant), `--rebuild-catalogue`.
- [x] Règle de fraîcheur : `ARCHIVUM/rules/freshness_sources.md` — TOUTE source porte sa date de publication ; info d'une saison passée = à recroiser avant usage ; le moteur de probas n'utilise JAMAIS les transcriptions (hérésie).
- [ ] **EN ATTENTE WARSMITH** : stocker les transcriptions (outil externe du Warsmith) → `--add` → `--dates` après confirmation des dates YouTube → dépouillement fiches.

## ETAT v2.1 — MULTI-FORMAT (2026-10-29)

- [x] **Phase A** : entree flexible txt/md/png/pdf/docx (`extract_input.py`) + parseur tableau markdown Winner Bet (11 matchs de la capture type). Image sans tesseract = Zero Data, Zero Calc.
- [x] **Phase B** : previews 1 et 2 deja en place — revalidees e2e (groupe 2 = 11/11, groupe 3 = 11/11).
- [x] **Phase C** : workflow Telegram + GitHub Actions `pari-daily` deja en place (Pages + notifier). `/capture` accepte tous les formats.
- [x] **Phase D** : docs (GUIDE, README, CONTINUATION, contrat schema_input_capture) + e2e_multiformat 9/9 + regression groupe 1 9/9.

## ETAT v2.2 — ECOUTE TELEGRAM LIVE (2026-10-30)

- [x] **Phase 8** : relais Cloudflare Worker (`ORCHESTRATOR/LISTEN`) + Action `pari_listen.yml` + inbox `F01_SENTINEL/IN/capture_telegram.md` + contrat `schema_listen.json`. `/capture` Telegram = tableau markdown **dans le meme message**. e2e_listen 30/30 (zero reseau). png/pdf + KV hors v1.
- [x] **Worker deploye** : `https://pari-listen.pari-listen.workers.dev` — webhook Telegram pose avec `secret_token`.
- [x] **Repo vivant** : `gyutedy/PERTURABO` branche `pari-forge-perturabo-xs4c` (`GH_OWNER=gyutedy`). Ancien compte `jfbjfojfonf` = Actions desactive (`Actions has been disabled for this user`) — ne plus dispatcher la.
- [x] **Branche principale PARI** : `pari-forge-perturabo-xs4c` (Worker `GH_REF` + siege Telegram). `v2-live-vox-c` n'est plus la branche de travail PARI.
- [x] **Fix notifier** : GitHub injectait `TELEGRAM_*` vides → `setdefault` ignorait `env_pari`. `notifier.py` ecrase maintenant les secrets vides. Telegram recoit la reponse.
- [x] **Pages** : `deploy-pages` en `continue-on-error` (Pages pas active sur gyutedy → 404, ne doit plus faire echouer le run).
- [x] **Premier /start LIVE OK** (2026-10-30) : ACK Worker + message `Campagne **PARI-20261030** ouverte.` Campagne ouverte, en attente capture.
- [x] **v2.2.1 parseur markdown Telegram** (2026-10-30) : `_normalize_md_table` reassembles les rangs casses (`<br>` → newline). Prefix junk (`. |`) ignore. `Inde - IFL Equipe vs Equipe` separe competition/match. `workflow.py` passe le chemin inbox (plus `fichier` vide). Pas de scrape Winner.bet.
- [x] **v2.2.2 siege LIVE** (2026-10-30) : `/valider-1` force `PARI_AUTO_GATES=1` (workflow.py + `pari_listen.yml`) → F02/F03/top3 ecrasent la demo. `/data` refuse un TOP3 Cyclops. `/valider-2` refuse si 0 match eligible. `Aujourd'hui` → date UTC. `inject_stats` scanne toutes les ligues de la carte (whitelist E0/SP1/I1/D1/F1). forgeward emet NO_BET si analyse absente. Pas de scrape.
- [x] **v2.2.3 e2e_final aligne** (2026-10-30) : apres `/valider-1` le test copie la carte stats (`e2e_final_carte.json`) dans `matches.json` puis siege → `/valider-2` compose 3 tickets. Garde prod inchangee (carte live vs TOP3 demo = refuse). e2e_final 13/13, e2e_listen 30/30. Autre sandbox a plante sur credits au `git checkout` artefacts — termine ici.
- [x] **v2.2.4 siege ignore filtered stale** (2026-10-30) : `suite_siege` ne lit `predictions_filtered.json` / `qualitative_verdict.json` que si le filtre a tourne **sur cette carte** (notes presentes). Sinon Top 3 = `predictions.json` de la capture. Cause live : filtered demo Cyclops (29/10) relu apres siege Konyaspor (30/10) → Telegram 18 matchs demo. `/valider-1` passe `--fixtures matches.json`. e2e_listen plante un stale Cyclops cote source ; e2e_final plante un filtered stale avant `/valider-1`.
- [x] **v2.2.5 bankroll + budget JOUR SURTICKET force** (2026-10-30) : `/bankroll 50000` = pot global (persiste `/start` `/stop`). `/budget 3000 800` obligatoire = 3000 FC plafond jour + **800 FC FORCES sur le ticket sur** (reste 2200 divise). Alias `/budget 3000 / 800`. `/surticket 800` corrige la mise du sur sans retaper le jour. `/valider-2` refuse si sur-ticket absent. `/budget 3000` seul refuse. Sur > jour refuse. Jour > bankroll refuse. Worker + parse.py relaient `/bankroll` `/surticket`. e2e_listen + e2e_final couvrent persist + force.
- [x] **v2.2.6 alias `/budget bankroll N`** (2026-10-31) : Worker live refuse `/bankroll` (KNOWN stale, pas de wrangler). Alias relais deja deploye. `/start` guide vers cet alias.
- [x] **v2.2.7 inject stats alias ligues/clubs + merge** (2026-10-31) : `LaLiga` (sans espace) → SP1. Alias clubs football-data (`Ath Madrid`, `M'Gladbach`, `Nott'm Forest`). `stats_inject_{E0,SP1,…}.json` par ligue (plus d ecrasement). Club hors CSV (Paderborn/Coventry) = skip CE match, pas NO BET global. `/valider-1` distingue stats absentes / data insuffisante / tous FAIBLE et compte GO/FAIBLE/skip.
- [x] **v2.2.8 F06 lots token + anti-cannibal** (2026-10-31) : 1 `/valider-2` = 1 token `L-XXX` + snapshot T0 (append, n'ecrase pas). Mode A = meme capture, plusieurs lots (retaper `/budget` avant chaque lot). Mode B = `/stop` `/start` nouvelle capture. Anti-cannibal : exclusion `(match_id, marche, selection)` par capture, prochain marche Top 3 libre, plancher HAUTE/MOYENNE fixe, refus si pool vide. Aliases `/data ledger`, `/status ledger`, `/roi settle L-XXX` (CSV football-data, G/P/EN_ATTENTE, jamais invente). F06 n'apprend pas. Worker inchangé (args relais). e2e_listen 91/91.

**Campagne LIVE 2026-10-31** : `/valider-1` 10 GO, `/valider-2` a pose T$1–T$4 (budget 3000/800). Ce lot pre-v2.2.8 n'a **pas** de token. Apres ce commit : `/data ledger` (voir si un lot auto existe) **ou** Mode A : retaper `/budget 3000 800` puis `/valider-2` = lot 2 (autres marches, anti-cannibal). Mode B seulement si nouveau tableau / nouveau budget jour.

**Prochaine etape operateur** : attendre que `pari_listen.yml` checkout ce commit. Sans re-`/start` si la campagne 10 GO est encore ouverte : `/data ledger` puis éventuellement `/budget` retapé + `/valider-2` (lot 2). `/roi settle L-XXX` apres les matchs (CSV ligue). Pas de wrangler/setWebhook.

## ETAT v2.3 — F00 CAPTEURS AU `/capture` (2026-10-31)

- [x] **Contrats** : `schema_match_intel.json` (+ `xg`, `rest_days`, `h2h`, `holes`, `notes_count`). `schema_notes_qualitatives.json` v3 : vote `OUT|DOUTE|IGNORE`, `sources[]`, `notes_count`. Matching **par nom**.
- [x] **Binaire au `/capture`** : ClubElo (sans clé) + Understat xG (jamais dans Poisson) + football-data.org repos/H2H (clé optionnelle). Trou déclaré, jamais inventé.
- [x] **Notes 3 voix** : SofaScore + Sportradar + ESPN (WhoScored/Opta optionnel). Vote OUT si 3 upstreams indépendants / 48h. DOUTE ne touche pas λ. Ligues : E0/SP1/I1/D1/F1/N1/T1/J1.
- [x] **Fatigue** = jours de repos calendrier (binaire dérivé). Météo / motivation hors v1.
- [x] **Gâchette** : `capteurs.py enrich` après parse `/capture` et après inject `/valider-1`. Cache 1 hit/équipe/jour. Timeout / 3 fails = voix morte.
- [x] **TYRANT** : items F00, OUT seulement → `themes`. `notes_count: 0` → pas de filtre. Oracle / HERALD : commentaire après coup si clé, **jamais** un OUT.
- [x] **`/data`** : préfixe `notes: N`. 0 = trou visible.
- [x] **E2E** : `tests/e2e_f00.py` (vote, cache, trou, TYRANT DOUTE, Oracle silence). `PARI_SKIP_INJECT=1` / `PARI_SKIP_F00=1` = offline.
- [x] **`FOOTBALL_DATA_ORG_KEY` LIVE** (2026-11-01) : jeton football-data.org pose dans `env_pari`. Header `X-Auth-Token`. Ping `/v4/competitions` HTTP 200 (13 comps). F00 `rest_days` au `/capture` et `/valider-1`. **Indépendant d'Oracle / modèle premium** : `workflow.py` charge `env_pari` à chaque commande Telegram, secret GitHub vide n'écrase pas.
- [x] **`API_FOOTBALL_KEY` LIVE** (2026-11-01) : jeton api-sports Free (100 req/jour) pose dans `env_pari`. Header `x-apisports-key`. Ping `/status` HTTP 200, plan active. Calendrier F00 (`fixtures-list`), **pas Oracle**. WhoScored / Oracle : encore vides.
- [x] **`SPORTRADAR_API_KEY` LIVE** (2026-11-01) : jeton trial v4 pose dans `env_pari`. Ping `/competitions` + `/seasons/{id}/missing_players` HTTP 200. **Route trial differenciee** : pas de search equipe, `missing_players` est publie PAR SAISON -> connecteur reecrit (saison courante des 6 championnats, cache 1 hit/jour/competition, matching nom normalise + difflib 0.9). Voix 2 notes = DOUTE seule ; OUT exige 3 voix. **Pas Oracle.**
- [x] **`SOFASCORE_RAPIDAPI_KEY` LIVE** (2026-11-02) : meme X-RapidAPI-Key que WhoScored. Host `sofascore-sport-api.p.rapidapi.com`. Search + `/api/team/{id}/events/next/0` + `/api/event/{id}/lineups` → `missingPlayers`. Teste Arsenal (Saka, Saliba) + Chelsea (6). Direct `api.sofascore.com` = 403 ici. **Pas Oracle.**
- [x] **`WHOSCORED_KEY` POSEE** (2026-11-02) : injuries souvent trou. Voix 3 = ESPN public (v2.4), plus WhoScored. **Pas Oracle.**
- [x] **`ORACLE_API_KEY` LIVE** (2026-11-02) : Zro `https://zro.moonmath.ai/v1`, modele `glm-5.3-flash` (HTTP 200). `deepseek-v4.1-flash` aussi 200. `glm-5.3` = 403. Lire `content`, jamais `reasoning_content`. TYRANT/HERALD seulement. Siege tourne sans.

## ETAT v2.3.1 — `/data` DEUX VUES (2026-10-31)

- [x] **Contrat** : `h2h.matches[]` (date, home, away, ft, ht) + `form.dom/ext` 10 lignes. `holes` peut contenir `form`, `h2h_scores`, `timing`. Notes qualitatives inchangees.
- [x] **Capteurs** : `football_data_uk.last_matches` / `h2h_matches` depuis le CSV deja telecharge (cache disque, zero reseau si `PARI_SKIP_*`). Club hors CSV = skip CE equipe, `holes += form`. Timing buts = TROU (pas de Sofa ici). Jamais injecte dans Poisson.
- [x] **Affichage** : `ORCHESTRATOR/CODEBASE/data_view.py`. `/data` table compacte HAUTE puis FAIBLE, 1 ligne / match, prefixe `notes: N`. `/data N` fiche (rang 1-based). `/data ledger` inchange.
- [x] **Cablage** : `workflow.cmd_data` ledger | digit → fiche | vide → compact. `parse.py` relais `/data 4` + help `/data N`. Worker JS stale jusqu'au merge.
- [x] **E2E** : compact Q/H2H/TROU, trou = `—`, fiche H2H+forme, timing TROU, `/data 99` refuse, `/data 4` parse, ledger inchange, final ne casse pas.

## ETAT v2.4 — ESPN VOIX 3 (2026-11-02)

- [x] **Phase 1 ESPN** : `connectors/espn.py` public (sans cle). Fetch PAR LIGUE `site.api.espn.com/.../soccer/{slug}/injuries`. Mapping E0→eng.1 SP1→esp.1 I1→ita.1 D1→ger.1 F1→fra.1 N1→ned.1 T1→tur.1 J1→jpn.1. Matching nom + difflib 0.9. Cache 1 hit/ligue/jour + 1 hit/equipe/jour. Timeout / 3 fails = voix morte, jamais de devine.
- [x] **Vote** : Sofa + Sportradar + ESPN = 3 independants → OUT possible. WhoScored/Opta optionnel (4e). Jamais dans Poisson.
- [x] **Freshness** : ESPN soccer injuries peut etre vide / latence heures = trou declare, pas invente.
- [x] **Phase 2** Worker auto-deploy : `.github/workflows/worker_deploy.yml` (push LISTEN/** → wrangler). `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` lus depuis `env_pari` (pas GitHub Secrets). Absents = skip. Git `index.js` deja parite parse.py (`/data N` `/bankroll` `/surticket`).
- [x] **Phase 3** The Odds API T-2h : `connectors/odds_api.py` + `odds_watch.py` + cron `pari_odds_t2h.yml`. Cle `ODDS_API_KEY` (alias `THE_ODDS_API_KEY`) dans `env_pari` (pas GitHub Secrets). Absente = skip. Fenetre 3h. Recast EV avec `p_modele` deja calcule. ESTOMPE / AMINCI Telegram. Jamais Poisson, jamais scrape Winner. `PARI_SKIP_ODDS=1`.
- [x] **Phase 4** tesseract dans `pari_listen.yml` + `pari_daily.yml` (`tesseract-ocr` + `tesseract-ocr-fra`). Image sans binaire = Zero Data, Zero Calc (pas de crash). e2e_ocr.

**Handoff prochain agent** : branche `pari-forge-perturabo-xs4c` (`gyutedy/PERTURABO`). P1 ESPN + P2 worker_deploy + P3 Odds T-2h + P4 OCR POSES. Plan v2.4 ferme. Ne pas toucher au webhook Telegram, ne pas wrangler manuel, pas scrape Winner, pas Dixon-Coles, pas `v2-live-vox-c`. Cles = `env_pari` seulement (jamais GitHub Secrets). Operateur : coller `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` + `ODDS_API_KEY` dans `env_pari` sinon Worker stale / odds skip. F06 n'apprend pas. FBref hors siege.

## ETAT v2.5 — RADAR ROBUSTE + BACKTEST SHARES (2026-11-02)

- [x] **`/radar` robuste** : `orchestrator.mode_radar` filtre les matchs sans stats completes (`filter_radar_carte`) et ecrit une carte temporaire `F01_SENTINEL/OUT/radar_filtered.json` ; les ids sautes sont declares en `holes` (trou declare, jamais devine). Sentinel reste strict pour le siege.
- [x] **`radar.py`** : `stats_complete` / `split_complete` / `stamp_ligue` ; `run_radar` saute les trous, ne crashe plus sur `KeyError`. `RADAR.md` liste les trous.
- [x] **Tampon ligue** : `breacher.stamp_league_code` pose `league_code` sur chaque match (map `capteurs.ligue_code`), `analyse_fixtures(..., ligue, league_code)` et `radar.stamp_ligue` alignes.
- [x] **Part MT1 ligue** : `league_averages` priorise `PARI_SHARES_PATH` → part mesuree sur l'echantillon → `DEFAULT_PART_MT1` (0.44). `half_split_lambda(..., part_ligue)` utilise cette part pour les flags `mt_split_estimate`.
- [x] **Backtest offline** : `F00_RADAR/CODEBASE/backtest.py` lit les CSV football-data caches, mesure `part_mt1` (HT/FT) + pente Elo, ecrit `ARCHIVUM/learnings/shares.json`. Zero reseau, zero scrape.
- [x] **Commandes Telegram** : `/radar [N]`, `/pack [N]`, `/match ID` (id `M1` ou rang 1-based) cablees dans `workflow.py` (`cmd_radar`/`cmd_pack`/`cmd_match`), `parse.py` + Worker `index.js` + `schema_listen.json` alignes (`/help` mis a jour).
- [x] **Tests** : `tests/e2e_backtest.py` 25/25 (shares, merge 2 saisons, learnings identity/clip, tampon, holes, cmds). `e2e_listen` 99/99 (`L12.superlig_t1` : Turkiye Super Lig → T1).

## ETAT v2.6 — SHARES 5 SAISONS + LEARNINGS RADAR + SUPER LIG (2026-11-02)

- [x] **Super Lig T1** : alias `turkiye` dans `capteurs.LIGUE_CODE`. Doctrine : T1 whitelist (ESPN `tur.1`, Odds `soccer_turkey_super_league`, enrich NOTES_3_VOIX). `L12.superlig_t1` PASS. LaLiga 2 reste rejetee.
- [x] **Backtest multi-saisons** : `backtest.merge_recs` pondere `part_mt1` / `elo_slope` par `n` (plus d'ecrasement du dernier CSV). `scan_dir` fusionne par `league_code`. Fixture `uk_SP1_2526.csv` pour e2e.
- [x] **`shares.json` prod** : 7 ligues × 5 saisons (2122–2526) E0/SP1/I1/D1/F1/N1/T1. Cache gitignore. Parts : D1 0.4542, E0 0.4428, F1 0.4426, I1 0.4362, N1 0.4392, SP1 0.4322, T1 0.4461. Elo slope = trou (pas de carte Elo cachee).
- [x] **Learnings radar (item 6)** : `radar.load_learnings` / `apply_learnings`. Sous 50 tickets settle = identity (facteur 1.0, declare dans RADAR.md). 50+ = facteur `clip(1+ROI, 0.85, 1.15)` sur `radar_score` (`radar_score_raw` intact). F06 n'apprend pas. Poisson inchange.
- [x] **Tests** : e2e_backtest 25/25, e2e_listen 99/99.

- [x] **Pente Elo** : `load_elo` lit `elos` (schema ClubElo) + `teams`. Matching `team_key` / alnum. `scan_dir` concatene les lignes par ligue avant OLS (plus de moyenne de pentes). ClubElo live **trou** (api.clubelo.com timeout ici) — `shares.json` prod sans `elo_slope`. Fixture e2e = pente presente.
- [x] **Learnings par marche** : `by_comp` o2.5 / mt2_plus (min 8 jambes). Recompose le score radar (poids 0.55/0.30) — un facteur global ne reordonne pas. Identity < 50.

**Reste a faire** : (1) coller `elo.json` (ClubElo, reseau ouvert / Actions) puis `capteurs.py backtest-shares --elo` pour peupler `elo_slope` prod, (2) 50+ tickets **reels** pour activer learnings live. Trou `holes: ["elo"]` declare tant que la carte manque.

## ETAT v2.7 — /pack /match EXECUTES (2026-11-02)

- [x] **`/pack` live** : `cmd_pack` execute `orchestrator --mode pack` (packager + dashboard). Refuse sans predictions/analysis. EV cassee = 0, pas de crash. Pack vide + orch fail = message d'echec.
- [x] **`/match` live** : fiche Herald si presente, sinon analysis (λ / O2.5 / MT2, proba None = `—`), sinon refuse `introuvable`. Rang 1-based + id `M1`.
- [x] **packager** : `analyses` / `predictions` absents ou partiels = pack vide, jamais `KeyError` sur `data_quality`.
- [x] **e2e_backtest** : `B.pack_refuse_sans_pred` / `B.pack_run` / `B.pack_picks` / `B.match_sans_arg` / `B.match_inconnu` / `B.match_m1` / `B.match_rang` — execution reelle, plus un grep. Zero reseau.
- [x] **Docs** : GUIDE + README listent `/radar` `/pack` `/match` dans le cycle Telegram.

**Handoff** : branche `pari-forge-perturabo-xs4c`. Flux radar → pack → match **execute** (plus seulement cable). Suite : ClubElo `elo.json` (pente prod) + 50 tickets reels. Pas de wrangler, pas scrape Winner, pas Dixon-Coles, cles = `env_pari`.

## ETAT v2.8 — CLUBELO TROU DECLARE (2026-11-02)

- [x] **Connecteur** : `clubelo._fetch_csv` timeout / URLError / CSV vide = blob trou (`holes: ["elo"]`, `elos: {}`). Jamais de pente inventee.
- [x] **`build-elo`** : ecrit le fichier trou (plus un return silencieux). `backtest-shares` cable dans `capteurs.py`.
- [x] **`backtest.holes_for`** : trou si carte Elo absente **ou** aucune `elo_slope` mesurable. `shares.json` prod : `holes: ["elo"]`, parts MT1 intactes.
- [x] **Tests** : e2e_backtest 44/44 (timeout, CSV vide, parse OK, pas de pente sans carte, `cmd_build_elo` / `cmd_backtest_shares` ecrivent le trou). e2e_listen 99/99. Zero reseau.

**Handoff** : ClubElo live reste trou tant que `api.clubelo.com` timeout ici. Coller `elo.json` (Actions / reseau ouvert) puis `capteurs.py backtest-shares --elo` pour peupler `elo_slope` prod. 50+ tickets reels toujours requis pour learnings live. Pas de wrangler, pas scrape Winner, pas Dixon-Coles, cles = `env_pari`.

## ETAT v2.9 — /capture PHOTO TELEGRAM (2026-11-02)

- [x] **Worker + parse.py** : photo (plus grande taille) ou document image + caption `/capture` → `capture_file_id`. Markdown inchange. Photo sans caption = refuse (pas ignore).
- [x] **`pari_listen.yml`** : input `capture_file_id` → `getFile` Telegram → `F01_SENTINEL/IN/capture_telegram.jpg|png` → OCR tesseract deja pose. Token : secret GitHub ou `env_pari`. Echec download = trou, pas d'invention.
- [x] **`resolve_capture`** : inbox photo prioritaire sur `.md` (corrige v2.10 : mtime, plus une priorite fixe).
- [x] **Tests** : e2e_listen 104/104 (photo, document, sans caption, inbox png). e2e_ocr 12/12. Zero reseau. Deploy Worker auto au push `LISTEN/**`.

**Telegram** : `/capture` + tableau markdown **ou** photo avec caption `/capture`. Relis le JSON reconstitue avant `/valider-1`. OCR illisible = Zero Data, Zero Calc.

## ETAT v2.10 — INBOX LEFTOVER + DATES EU (2026-11-03)

- [x] **Cause live 0 match** : `Capture parsee (image)` alors que l'operateur a colle un tableau markdown. `resolve_capture` prenait `capture_telegram.png|jpg` **avant** le `.md`. Un jpg d'un essai photo restait dans `F01_SENTINEL/IN/` → OCR de l'ancienne image → 0 match, 1 warning. Ce n'etait **pas** le multi-jours.
- [x] **`resolve_capture`** : prend l'inbox `capture_telegram.*` la **plus recente** (mtime). Plus de priorite fixe photo > md.
- [x] **`pari_listen.yml`** : un `/capture` markdown retire les leftover photo ; un `/capture` photo retire le leftover `.md`.
- [x] **Dates EU** : `DD/MM/YY` et `DD/MM/YYYY` → ISO. Heure `HH.MM` seulement si une date est sur la **meme** cellule (un `1.16` n'est plus une heure). `Date non précisée` = warning, match garde, date None. Plus de date globale recopiee sur tous les rangs.
- [x] **Tests** : e2e_listen inbox mtime (md recent gagne, photo recente gagne) + leftover yml. e2e_multiformat dates EU multi-jours + inbox 19 matchs. Zero reseau. Pas de scrape.

**Telegram** : recolle le tableau markdown dans le meme message que `/capture`. Le siege doit repondre `Capture parsee (markdown_table)` (ou `texte+markdown_table`), **pas** `(image)`. Relis le JSON : dates `2026-11-06` … `2026-11-22` par match.

## ETAT v2.10.1 — INBOX YAML HORS HEREDOC (2026-11-03)

- [x] **Cause live ACK sans siege** : `/stop` 17:07 et `/start` 17:11 → Worker ACK OK, `pari-listen` **failure**. Etape `Inbox capture Telegram` : `IndentationError` (Python heredoc YAML, `except` mal indente, v2.10 leftover). `workflow.py` skipped → pas de notifier → pas de 2e message. Runs 41681058998 / 41681763423, SHA `c3fd6577`.
- [x] **Fix** : Python sorti du YAML vers `ORCHESTRATOR/LISTEN/inbox_capture.py`. YAML = `python3 ORCHESTRATOR/LISTEN/inbox_capture.py`. `/start` `/stop` = no-op (pas de capture), exit 0. Leftover photo/md inchange.
- [x] **Tests** : ast.parse du script, `/start` no-op, markdown retire leftover png. e2e_ocr pointe getFile dans le script. Zero reseau.

**Telegram** : retape `/start`. ACK puis `Campagne PARI-YYYYMMDD ouverte.` Si ACK seul : Actions → `pari-listen` (pas le Worker).

## ETAT v4.0 — PARSEUR MOINS/PLUS + WHITELIST E1/D2 (2026-11-06)

Pack S1 du `TRACKING/PLAN_PARI_CONSOLIDE.md` (v3.5+v4 empiles). Doctrine pack :

1. Zero Data / Zero Calc. Trou = `holes: ["..."]`. Jamais de guess, jamais de defaut silencieux.
2. EV = `P_modele * cote_brute - 1`. Devig / scorer / Oracle = diagnostic ou veto, jamais un producteur de p.
3. Oracle / TYRANT / HERALD : lire `content`, jamais un chiffre.
4. Stdlib Python seulement. Secrets hors commit.
5. Tests `e2e_*.py` verts + `tests/test_*.py` offline.
6. Telegram = unique cockpit.
7. Un commit/push par pack. Session = un pack.

Verrou casse a R4 (pas ce pack) : infos non-binaires hors maths. Moins/Plus sans ligne : **pas de 2.5 invente**. Championship / Bundesliga 2 : **E1 / D2**, CSV de leur ligue, jamais E0/D1.

- [x] **Parseur** `input_capture.py` : en-tete `Moins de X` / `Plus de X` ou colonne `Ligne (Total)` → tags `uX`/`oX`. Ligne absente → `holes: ["ligne_totale_Moins_Plus"]`, cotes `under`/`over` **gardees**. MT 3 cotes identiques sur >= 5 matchs → `cote_plate`, cotes conservees.
- [x] **Whitelist** `capteurs.py` : `"championship": "E1"`, `"bundesliga 2": "D2"` (+ alias). Retire Championship / Bundesliga 2 de `LIGUE_REJECT`. LaLiga 2 / Serie B / Ligue 2 restent rejetes. `ligue_code` matche la cle la plus longue (D2 avant D1).
- [x] **Tests** : `tests/test_input_capture_moins_plus.py`. e2e_listen L12 E1/D2. e2e_multiformat non regressif.
- [x] **Docs** : GUIDE, INDEX, schema_input_capture, IW_CAMPAIGN_LOG, PLAN S1 coche.

**Handoff** : pack S2 (doctor + research bundle). Operateur : `/roi settle L-DWG` apres les matchs. Ph0 rotation cles = Warsmith.

## ETAT v3.1 / v3.2 — DOCTOR + RESEARCH BUNDLE (2026-11-06)

Pack S2 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Evidence 1. Session = ce pack seulement.

- [x] **Doctor** `ORCHESTRATOR/CODEBASE/doctor.py --offline --json` : GO / CHECK / FAIL. Cles = **noms seulement** (jamais les valeurs). Contrats vs champs required. Whitelist vs connecteurs (E1/D2 ESPN = holes, pas invente). Cache fraicheur + trous. Gate : n<300 bruit ; 300-499 observation ; >=500 verdict moteur. Exception : CLV median 30j < -3 pts = FAIL. CLV absent = trou, pas 0.
- [x] **Research bundle** `research_bundle.py` : a `/valider-1`, dossier `ARCHIVUM/research/B-XXX` + `manifest.json` SHA-256. `--verify`. Gap declare, jamais comble. `freeze_lot(..., bundle_id=)` optionnel (kwargs, e2e freeze_lot 7 args intact).
- [x] **Telegram** : `/status` ligne doctor. `/status doctor` evidence complete. Relais parse.py + Worker (`status` extra deja cable). `/help` liste `/status doctor`.
- [x] **Tests** : `tests/test_doctor.py`, `tests/test_research_bundle.py`. e2e_listen L4.status_doctor. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, schema_ledger bundle_id, PLAN S2 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S3 (one-writer + journal proc/outcome). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S3 dans cette session.

## ETAT v3.3 — ONE-WRITER + JOURNAL PROC/OUTCOME (2026-11-06)

Pack S3 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Evidence 2. Session = ce pack seulement.

- [x] **One-writer** : `notifier.py` = seul `sendMessage` Python. Lint `tests/test_one_writer.py`. Worker ACK (`LISTEN/src/index.js`) et `inbox_capture.py` getFile autorises.
- [x] **Journal F06 2 volets** `F06_TRACKER/CODEBASE/journal.py` : (a) procedure a freeze (checks, trous, seuils, Kelly) **immutable** ; (b) outcome au settle (mise, cote, G/P, pnl, CLV si connu). CLV / Kelly / seuils absents = holes, jamais 0. `freeze_lot(..., procedure=)` kwargs (e2e 7 args intact).
- [x] **Churn** `ORCHESTRATOR/CODEBASE/churn.py` + `config/churn.json` : >2 changements / 7j hors calibration → `churn_suspect`. Calibration exclue du compteur.
- [x] **Tests** : `tests/test_one_writer.py`, `tests/test_journal.py`, `tests/test_churn.py`. e2e_listen freeze_lot 7 args. Zero reseau.
- [x] **Docs** : GUIDE settle, INDEX journal/churn, schema_ledger journal, PLAN S3 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S4 (marches elargis + devig). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S4 dans cette session.

## ETAT v3.4 / v3.5.4b — MARCHES ELARGIS + DEVIG DIAGNOSTIC (2026-11-06)

Pack S4 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph4 + Ph4b. Session = ce pack seulement.

- [x] **Marches** : memes matrices Poisson. O/U 0.5, 1.5, 3.5, 4.5, DC 1X/X2/12, team totals, score exact (top N + cote fournie). Zero equation changee. `o2.5` / 1X2 / BTTS inchanges.
- [x] **Devig** `F03_FORGEWARD/CODEBASE/devig.py` multiplicatif. Issue manquante / cote unique → holes, pas de fair. Invariant S>1 => fair_odds_i > cote_i.
- [x] **Diagnostic** : `edge_net_devig` = P_modele/P_fair - 1. Tri EV = `P_modele * cote - 1` inchange.
- [x] **double_confirmation** : P_modele > P_fair **et** P_modele * cote > 1. Bonus seuil `config/devig.json` (init 1 pt).
- [x] **Tests** : `tests/test_markets.py`, `tests/test_devig.py` (triple 2.75/3.40/2.50). Zero reseau.
- [x] **Docs** : GUIDE marches elargis, README, INDEX, schema analysis/predictions, PLAN S4 coche.

**Handoff** : pack S5 (facteur compose + priorite marches). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S5 dans cette session.

## ETAT v3.5 — FACTEUR COMPOSE + PRIORITE MARCHES (2026-11-06)

Pack S5 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph4c + Ph4d. Session = ce pack seulement.

- [x] **EV compose net** `F05_PACKAGER/CODEBASE/compose.py` : produit `(1+edge_net) - 1`, precision machine. `1.03*1.05-1 = 8.15%`.
- [x] **`jambe_edge_net_negatif`** : flag info, **pas rejet**. Ticket conserve la jambe. Trou `edge_net` = hole, jamais substitue par EV brute.
- [x] **combinator** : pose `ev_compose_net` / `compose_flags` / `compose_holes` sur chaque ticket. Tri EV brute inchange.
- [x] **`config/market_priority.json`** : palier suivant si >= 30 tickets mesures (G/P settle, EN_ATTENTE ignore). Palier 0 = 1X2/O2.5/BTTS/MT. Palier 1 a n>=30. Palier 2 a n>=60.
- [x] **corners / cards** fermes sans data → `holes: ["sans_data", "corners"|"cards"]`. Jamais ouverts. Jamais droppes.
- [x] **Doctrine** : edge = modele calibre + news plus rapide que le book local ; **pas d arbitrage**.
- [x] **Tests** : `tests/test_compose.py` (8.15%), `tests/test_market_priority.py`. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, schema_ticket_final, PLAN S5 coche.

**Handoff** : pack S6 (fit ligue + baseline saison recency). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S6 dans cette session.

## ETAT v3.6 — FIT LIGUE + BASELINE SAISON RECENCY (2026-11-06)

Pack S6 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph5 + Ph6. Session = ce pack seulement.

- [x] **Fit** `F02_BREACHER/CODEBASE/league_fit.py` : rho (grille log-vraisemblance stdlib), bonus domicile `1+(mh-ma)/(mh+ma)` clip [1.00, 1.25], part_mt1. Sortie `ARCHIVUM/learnings/league_params.json` (gitignore). Ligue absente / n<4 → defauts + flag `params: default`.
- [x] **Baseline** `F02_BREACHER/CODEBASE/baseline.py` : saison complete cachee, EMA demi-vie 45j (`config/league_fit.json`). Split att/def dom/ext par equipe (stocke, pas injecte dans Poisson). Saison absente → fallback carte + `holes: ["saison"]` + `baseline: carte`.
- [x] **Cablage** `breacher.league_averages` / `analyse_match` : rho et bonus_domicile depuis le fit si present, sinon 1.10 / 0.95 / RHO_DC inchanges (e2e siege intact). `part_mt1` : shares > fit > mesure carte > 0.44. CLI `capteurs.py fit-league`.
- [x] **Tests** : `tests/test_league_fit.py`, `tests/test_baseline.py`. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, PLAN S6 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S7 (empirique O2.5 + backtest walk-forward). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S7 dans cette session.

## ETAT v3.8 — EMPIRIQUE O2.5 + WALK-FORWARD (2026-11-06)

Pack S7 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph6b + Ph7. Session = ce pack seulement.

- [x] **Empirique** `F00_RADAR/CODEBASE/empirique.py` : taux O2.5 saison cachee. `|P_modele - empirique| >= 0.20` → flag TYRANT `incoherence_modele_empirique` (info, **pas NO BET**). Saison absente → `holes: ["o2.5_empirique"]`, jamais 0 invente. Cable radar + siege (stamp apres F02).
- [x] **Walk-forward** `F00_RADAR/CODEBASE/walkforward.py` : cut-off explicite, train < cutoff, test >= cutoff, `in_sample: false`. Metrics Brier / RPS / ECE, hit-rate EV>=3%, yield Kelly 1/4. Odds absentes = hole, jamais 0. Sortie `ARCHIVUM/learnings/backtest_report.json` (gitignore). CLI `capteurs.py walk-forward --cutoff`.
- [x] **ClubElo hebdo** `.github/workflows/pari_elo_fill.yml` : lundi 05:00 UTC. CSV ClubElo → `build-elo` → `backtest-shares` elo_slope. Timeout = trou. Zero cle.
- [x] **Tests** : `tests/test_backtest.py` seede. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, PLAN S7 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S8 (sensibilite devig + CLV T-0). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S8 dans cette session.

## ETAT v3.9 — SENSIBILITE DEVIG + CLV T-0 (2026-11-06)

Pack S8 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph7b + Ph8. Session = ce pack seulement.

- [x] **Devig additif** `F03_FORGEWARD/CODEBASE/devig.py` : 2e passe diagnostic. Multiplicatif reste defaut (`p_fair` / `edge_net_devig` / double_confirmation inchanges). Ecart `devig_gap` journalise (procedure check). Cote unique = hole des deux methodes. EV = `P_modele * cote - 1` inchange. Jamais dans Poisson / GO / NO_BET.
- [x] **Snapshot T-0** `odds_watch.py --close` : fenetre grace 15 min autour du kickoff. Persist `t0_*.json` + `latest_t0.json`. **N ecrase pas** `latest.json` (T-2h). Workflow `pari_odds_t0.yml` */15. Zero cle GitHub.
- [x] **Settle** `ledger.settle_lot` : `book_odds_close` depuis T-0. Absente = hole `book_odds_close`, exclu CLV, **jamais 0**. T-2h n est PAS la cloture. Metrique `clv = cote_prise / cote_cloture - 1` = S9.
- [x] **Tests** : `tests/test_clv.py`. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, PLAN S8 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S9 (metrique CLV + F06 diagnostic). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S9 dans cette session.

## ETAT v3.10 — CLV METRIQUE + F06 DIAGNOSTIC (2026-11-06)

Pack S9 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph8b + Ph9. Session = ce pack seulement.

- [x] **CLV** `F06_TRACKER/CODEBASE/clv.py` : `clv = cote_prise / cote_cloture - 1`. Combo = produit des `book_odds_close`. Absente = exclu, **jamais 0**. Agregats median / % >0 / mean pondere mise. Cibles `config/clv.json` (55% / +0.5 pt).
- [x] **Settle** pose `ticket.clv` + `settle.clv` agregat. Journal outcome recopie le ratio (S8 hole inchange si close absente).
- [x] **Doctor** : n<30 variance (note, pas un verdict). Alerte median 30j < -3 pts inchangee. Agregats beat / median_pt.
- [x] **F06 diag** `diag.py` : Platt 2 params, Beta-Binomial, P(EV>0) MC seede (seed 42). **Verrou n<50** : `locked`, `verdict=None`, `mise=None`. Sortie = `/data diag` seulement.
- [x] **Telegram** : `/data diag` (alias `/data f06` `/data clv`). Relais parse.py + Worker + help. F06 n'apprend pas.
- [x] **Tests** : `tests/test_f06_diag.py` bloque sous 50. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, schema_ledger, PLAN S9 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S10 (Kelly 1/8 vers 1/4 gate ECE). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S10 dans cette session.

## ETAT v3.10.9b — ROUTAGE KELLY 1/8 VERS 1/4 GATE ECE (2026-11-06)

Pack S10 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph9b. Session = ce pack seulement.

- [x] **Config** `config/kelly.json` : fraction defaut 0.125, plafond 0.25, p_ev_positif 0.55, ece 0.03, n_lock 50.
- [x] **Route** `F03_FORGEWARD/CODEBASE/kelly_route.py` : `calibration_validee` = ECE walk-forward <= 0.03. 1/4 seulement si calibration OK **et** P(EV>0) >= 0.55 **et** n>=50. Sinon 1/8. P/ECE absents = 1/8 + holes. n<50 jamais 1/4.
- [x] **Forgeward** : `build_predications` prend la fraction `route_global()` (plus le 0.25 profil). Combo = `route_ticket` MC conjoint toutes jambes.
- [x] **Combinator** : stamp `kelly_fraction` / `kelly_label` / `kelly_holes` / `kelly_p_ev` / `kelly_ece` / `kelly_calibration_validee` sur chaque ticket. **`mise_fc` intact** (budget operateur hors Kelly).
- [x] **Journal** : `freeze_lot` pose la procedure Kelly (fraction, ECE, P, holes, checks). Journal lit `kelly_fraction` des tickets.
- [x] **Tests** : `tests/test_kelly_route.py`. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, schema ticket/ledger, PLAN S10 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S11 (`/marchés` + tickets 1..n+10). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S11 dans cette session.

## ETAT v4.1 — /marches + TICKETS 1..n+10 + ANTI MEME-NAVIRE (2026-11-06)

Pack S11 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. v4 R2 + R6. Session = ce pack seulement.

- [x] **`/marches`** `workflow.cmd_marches`. `st["marches"]` jusqu a `/valider-2`. Canon ASCII `/marches`. Alias `/marchés` (parse.py + Worker + CMDS). Option `mono`.
- [x] **Relais** : parse.py KNOWN + extra, Worker `index.js`, `schema_listen.json`, `/help`.
- [x] **Couverture avant election** : n matchs EV>=3%, meilleur EV, marge (trou si absente). 0 match → 0 ticket, message honnete.
- [x] **`ARCHIVUM/learnings/market_election_log.json`** append-only. `/status` alerte si un marche >60% des elections.
- [x] **combinator `--markets`** : tri EV desc **dans** les marches elus. **Pas** de plafond 2 jambes. **1 a n+10** matchs / ticket (`/combos`).
- [x] **Meme match = meme navire = interdit** (intra-ticket). Flag **mono-marche** : toutes les jambes = un seul marche.
- [x] **EV_FLOOR 0.03 inviolable.** EV combo plancher 0.05. Jamais jambe de remplissage. Baisser le floor = refuse.
- [x] **Tests** : `tests/test_marches.py` 38/38. e2e_listen 117/117. compose 24/24. kelly 56/56. Zero reseau.
- [x] **Docs** : GUIDE cycle `/valider-1` → couverture → `/marches` → `/combos` → `/valider-2`. INDEX, README, PLAN S11 coche.

**Handoff** : pack S12 (scorer eligibilite F03). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S12 dans cette session.

## ETAT v4.2 — MARKET PROFILES + SCORER ELIGIBILITE F03 (2026-11-06)

Pack S12 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. v4 R3. Session = ce pack seulement.

Choix F03 : eligibilite apres EV, **pas** Poisson F02, **pas** fiches F04. Scorer = veto / score 0-1, jamais un producteur de p.

- [x] **`ARCHIVUM/learnings/market_profiles.json`** versionne. Poids a priori. Ne pas retuner a la main (S16 si n>=50).
- [x] **Module** `F03_FORGEWARD/CODEBASE/market_scorer.py`. Portes A1-A4 binaires hors score.
  - A1 groupe complet (cotes du marche).
  - A2 praticable cote >= 1.10.
  - A3 historique : `mj_insuffisant` / qualite basse = refus.
  - A4 vitrine : overround > 20% = refus. MT 2.10/3.40/2.10 (24.6%) refuse ; 2.20/3.60/2.20 (18.7%) passe. 1X2 2.10/3.40/3.50 (5.6%) passe.
- [x] **B1-B6** : B1 0.30, B2 0.20 (MT B1 0.25 / B2 0.25), B3 0.20 **asymetrie info seulement** (T-2h vs cote capture, pas severite blessure), B4 0.15, B5 0.10, B6 0.05. Score 0-1, seuil 0.50-0.60 selon marche. Trou data → score reduit + holes. Chaque contribution journalisee.
- [x] **forgeward** : stamp `scorer_*` + `overround`. Si ineligible et VALUE/THIN → NO_BET, `mise_units` None. **EV = P_modele * cote - 1 inchange.** p_modele inchange.
- [x] **Tests** : `tests/test_market_scorer.py` 81/81. kelly 56/56. compose 24/24. devig 23/23. e2e_listen 117/117. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, schema_predictions, PLAN S12 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S13 (facteurs etat lambda + table effectifs). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S13 dans cette session.

## ETAT v4.3 — FACTEURS ETAT LAMBDA + TABLE EFFECTIFS (2026-11-07)

Pack S13 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. v4 R4. Session = ce pack seulement.

Decision v2 "non-binaires hors maths" **cassee pour cette table operateur seulement**.
API blessures (S15) reste flags, jamais un 2e lambda.

- [x] **`input_capture.py`** : 2e table canonique dans le meme `/capture`.
  Colonnes `att` / `def` / `gk` / `milieu` / `repos` / `rotation` / derby / meteo / retour.
  Deux rangs `dom`/`ext` (colonne `Cote`) ou suffixes `_dom`/`_ext`. Rangs effectifs
  ignores cote cote. En-tete 1/X/2 jamais reecrit par un rang data (Auxerre).
- [x] **`config/state_factors.json`** : att x0.90 / unite (max 2) ; milieu x0.96 ;
  def adverse x1.06 ; gardien x1.05 ; vide x1.00 + holes. Cap cumule ±20%, journalise.
- [x] **`F02_BREACHER/CODEBASE/state_factors.py`** + stamp `analyse_match`.
  Lambdas brutes conservees `dom_raw`/`ext_raw`. Holes **hors** `data_quality` (A3 intact).
- [x] **`rotation_lourde` (>=4)** : pas de facteur lambda ; flag TYRANT "O/BTTS deconseilles".
- [x] **Derby / meteo / retour_100** : TYRANT veto `marches_exclus` seulement.
- [x] **Tests** : `tests/test_state_factors.py`. 1 att out → p_o25 baisse ; cap respecte ;
  absent data → x1.00 + holes. notes_zero intact.
- [x] **Docs** : GUIDE table effectifs, schema_input_capture / analysis / notes, INDEX, README, PLAN S13 coche.

**Handoff** : pack S14 (detecteurs pieges + /data scorer). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S14 dans cette session.

## ETAT v4.4 — DETECTEURS PIEGES + /DATA SCORER (2026-11-07)

Pack S14 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. v4 R5 + R8. Session = ce pack seulement.

- [x] **3e lecture cotes** : capture (T-0 book) → T-2h (`latest.json`) → T-0 close (`latest_t0.json`).
  Stamp `lecture_cotes` sur chaque selection. Trou = null, jamais 0. B3 lit T-2h, sinon T-0.
- [x] **Detecteurs** dans `market_scorer.py` (jamais un p) :
  - `cote_plate` : flag parseur S1, cotes conservees.
  - `marge_anomalique` (B5) : overround > 10%, info, pas veto.
  - `cote_figee_sur_news` (B3) : |move capture vs T-2h| < 1% **et** notes OUT >= 1.
  - `marche_vitrine` : overround > 20% → A4, marche retire (MT 2.10/3.40/2.10).
- [x] **forgeward** : stamp `pieges` / `piege_detail` / `lecture_cotes`. EV / p_modele inchanges.
  Snapshots T-2h / T-0 lus si absents du match.
- [x] **`/data` `/radar` `/match`** : score correspondance + 6 criteres (edge/bande/info/data/marge/confirm) + flags pieges. Compact = colonne PIEGES. Fiche = SCORER + COTES + PIEGES.
- [x] **Vocabulaire** GUIDE + CONTINUATION aligne (Warsmith).
- [x] **Tests** : `tests/test_pieges.py`. MT plate x10 → flag ; marge 22% → marche retire. Poisson inchange.
- [x] **Docs** : GUIDE, INDEX, README, schema_predictions / schema_top3, PLAN S14 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S15 (injuries API flags TYRANT, jamais un 2e lambda). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S15 dans cette session.

## ETAT v3.11 — INJURIES API FLAGS TYRANT (2026-11-07)

Pack S15 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph10 + Ph10b. Session = ce pack seulement.

- [x] **`injuries.py`** `F01_SENTINEL/CODEBASE/connectors/injuries.py`. Cle existante `API_FOOTBALL_KEY`. Cache 1 hit/ligue/jour. Timeout / 40x / cle absente = `holes: ["injuries"]`. Jamais SystemExit. Jamais un P.
- [x] **4 flags TYRANT** : `buteur_manquant` (veto O/BTTS), `defenseur_manquant` (seuil +2 pts), `double_motivation` (seuil +2 pts), `satisfait_nul` (veto 1/2). **Jamais un 2e facteur lambda.**
- [x] **Anti-double-compte** : si table A S13 a deja prix att/def, le flag reste un label (pas de veto/seuil extra). `stamp_state` append flags/holes, lambdas intactes.
- [x] **Pas une 4e voix** : `api_football` hors `vote.INDEPENDENT`. 3 wrappers du meme upstream ≠ OUT.
- [x] **Siege** : qualitative tourne si notes **ou** `state_factors.flags` (S13/S15). Notes absentes = fichier vide OK.
- [x] **Kill switch** `PARI_SKIP_INJURIES=1`. Skip aussi si `PARI_SKIP_F00` / `PARI_SKIP_BINARY`.
- [x] **Tests** : `tests/test_injuries.py`. Holes, mock HTTP, anti-double-lambda, veto sans S13. Zero reseau.
- [x] **Docs** : GUIDE, INDEX, README, schema notes/analysis, PLAN S15 coche, IW_CAMPAIGN_LOG.

**Handoff** : pack S16 (Oracle meta + backtest poids scorer). Operateur : `/roi settle L-DWG` apres les matchs. Ne pas enchainer S16 dans cette session.

## ETAT v4.6 — ORACLE METRO + BACKTEST POIDS SCORER (2026-11-07)

Pack S16 du `TRACKING/PLAN_PARI_CONSOLIDE.md`. Ph11 + v4 R7. Session = ce pack seulement. Plan clos.

- [x] **Metro** `TYRANT/CODEBASE/metro.py` avant `/valider-2`. Risques / trous / ranking qualitatif. Lit `content`, jamais un chiffre. Digit dans la reponse = hole `oracle_digit`, texte jete. Cle absente / skip env = skip, siege intact.
- [x] **Fees + slippage** `config/ticket_friction.json` (0.005 + 0.005). Seuil effectif = EV_FLOOR + fees + slippage. **Jamais sous 0.03.** Cable `--ev-floor` combinator via orchestrator.
- [x] **`/approve L-XXX`** : `/valider-2` pose un lot pending + token. `/approve L-XXX` fige T0 (freeze_lot 7 args intact). Token mismatch = refuse. `PARI_AUTO_GATES=1` (Actions / e2e) fige tout de suite.
- [x] **R7** `F03_FORGEWARD/CODEBASE/backtest_weights.py`. n<50 tickets reels G/P = locked, a priori intact. n>=50 : **une seule** maj `market_profiles.json` journalisee (`scorer_weight_journal.json`). Jamais a la main. Ligues x marches. Seed 42.
- [x] **Tests** : `tests/test_oracle_metro.py` (zero chiffre, mock HTTP), `tests/test_backtest_weights.py` seede. Relais parse.py + Worker + schema_listen `/approve`.
- [x] **Docs** : GUIDE cycle `/valider-2` → `/approve`, INDEX, README, PLAN S16 coche, IW_CAMPAIGN_LOG.

**Handoff** : plan S0–S16 clos. Operateur : `/roi settle L-DWG` apres les matchs. Pas de pack suivant dans ce plan.

## ETAT v4.6.1 — HOTFIX S16 (2026-11-07)

Session verification S16 (pas un nouveau pack). 4 tests rouges a HEAD v4.6.

- [x] **`load_profiles`** : `ligues` droppees → overlay ligue x marche jamais lu. Restaure. Scorer E0/OU_2.5 seuil 0.55 + B1 0.40.
- [x] **`_renorm`** : `round(_, 4)` par cle → somme 1.0001. Residu sur B6, somme = 1.0.
- [x] **metro docstring** : `reasoning_content` dans le commentaire cassait le garde `g.jamais_reasoning`. Code lit `content` seulement. Inchange.
- [x] **Tests** : metro 27/27, weights 18/18, scorer 81/81, pieges 56/56, e2e_listen 118/118.

**Handoff** : S16 operationnel. Plan clos. Operateur : `/roi settle L-DWG` apres les matchs.

## ETAT v4.6.2 — REDEPLOY WORKER CODEBOOK (2026-11-07)

Bump `LISTEN/src/index.js` pour declencher `pari-worker-deploy`. Git connaissait
`/marches` `/approve` depuis S11/S16 ; Worker live stale → `Commande inconnue : /marches`.
Pas de wrangler manuel. Operateur : attendre le job vert, puis retaper `/marches`.

- [x] Commentaire codebook dans `index.js` (KNOWN deja a jour : marches, approve, combos).
- [x] Docs CONTINUATION + IW_CAMPAIGN_LOG. Plan S0-S16 reste clos.

**Handoff** : attendre Actions `pari-worker-deploy`. Puis Telegram :
`/start` → `/budget bankroll N` → `/capture` → `/budget 3000 800` → `/valider-1`
→ `/marches` (hint = marches du jour) → `/combos 3:3:2:2` → `/valider-2` → `/approve L-XXX`.
`/roi settle` seulement apres les matchs.

## ETAT v4.6.3 — HINT MARCHES DU JOUR (2026-11-07)

Siege live 23 matchs : couverture 1X2 n=3 EV +175% (X-tank) + hint stub `/marches O/U2.5,MT2`.
Hint aveugle. Couverture compte encore un X non jouable.

- [x] `hint_marches(top3)` : `/marches` calque sur `coverage_rows` (jambes jouables).
- [x] `/valider-1` et `/marches` vide : hint du jour, plus le stub `O/U2.5,MT2`.
- [x] Tank-X hors n (deja `jambe_jouable`). `cote_plate` = flag, MT **reste jouable**.
- [x] Tests : `test_hint_du_jour` (PSG X hors n, Gala 1 in, MT plate in, pas de stub).

**Handoff** : attendre Actions. Operateur : `/data` puis coller le hint affiche, pas un stub.

## ETAT v4.7 — CYCLE OPERATEUR HINT DU JOUR (2026-11-07)

Phase C. Docs + `/help` alignes sur le hint. `cote_plate` reste flag, MT jouable.

- [x] `/help` (parse.py + Worker) : `/marches` = hint du jour, plus le stub `O/U2.5,MT2`.
- [x] GUIDE : apres `/valider-1` → `/data` → coller le hint. Table effectifs dans `/capture`. `/approve` seulement si pas de X-tank.
- [x] LISTEN README + schema_listen. Parse `/marches O/U2.5,MT2` reste valide (alias).

**Handoff** : attendre Actions vert `pari-worker-deploy`. Telegram :
`/stop` → `/start` → `/capture` (+ table effectifs) → `/budget 1000 300` → `/valider-1`
→ `/data` → coller le hint → `/combos` → `/valider-2` → `/approve`.
`/roi settle` apres les matchs.

## ETAT v5.0 pack V0 — GEL MOTEUR (2026-11-10)

Pack V0 seulement. Un pack = un commit. Tickets geles. Ledger F06 intact.

- [x] Pack V0 : `config/moteur.json` tickets_enabled=false + `moteur_flag.py`.
      `/valider-2` refuse. `/modele` `/gel`. `/gel off` refuse sans GO.
- [x] Pack V1 : `F00_RADAR/CODEBASE/market_csv.py`. Zero Data. `_num` refuse
      cote <= 1.0. Scores 0 autorises (`_score`). Inventaire : `n_lignes`,
      `columns` reelles, `hors_couverture` (I1/D1/… absents, jamais estimes).
      Cache `ARCHIVUM/cache/f00/` encore vide → inventaire n_lignes=0 tant
      que les CSV Big 5 ne sont pas poses (P0 manuel).
- [x] Pack V2a : `F02_BREACHER/CODEBASE/model_dc.py` + `fit_dc.py`.
      MLE stdlib. Equipe absente / n<60 = holes, jamais invente.
      Elo absent = prior 0 + hole `elo`, jamais 1500. Score 0-0 lu.
      Ne cable pas breacher (V2b). Sortie `dc_params.json` gitignore.
- [x] Pack V2b : `F02_BREACHER/CODEBASE/engine_dc.py` cable dans
      `breacher.analyse_match`. Params fitted + 2 equipes -> lambdas MLE.
      Sinon Poisson carte + holes (`params_absents` / `equipe_absente` /
      `ligue_absente`). Tickets toujours geles. Calibration = V2c.
- [x] Pack V2c : `F00_RADAR/CODEBASE/backtest_market.py`. Walk-forward
      cut-off, fit train seulement, jamais in-sample. RPS/ECE/logloss
      modele vs marche (cotes 1X2 ouvertes). Gates `config/moteur.json`
      (rps_gap_max=0.0, ece_max=0.03, logloss_gap_max=0.0, min_oos=300).
      n_oos < 300 = verdict None (pas de GO). Cote <= 1.0 = hole.
      Score 0-0 lu. `/gel off` refuse sans verdict GO. Sortie
      `calibration_moteur.json` gitignore. Tickets toujours geles.
- [x] Pack VC : `F00_RADAR/CODEBASE/vanus_fetch.py`. CSV Big 5
      (E0/SP1/I1/D1/F1) football-data.co.uk. Timeout / HTML / vide /
      skip = hole, jamais invente. Pas de gate. Pas cable capteurs.
      `PARI_SKIP_VANUS=1` = hors_couverture Big 5. Tickets geles.
- [x] Pack V3 : `F00_RADAR/CODEBASE/vanus_gate.py`. Lecture
      `vanus.signal.v1`. Jackpot = veto selections opposees.
      Alarme = flag info. Isole / aucun = pass. Timeout / skip /
      contrat faux / match absent = hole. Jamais un p. Pas cable
      capteurs / qualitative / workflow. Tickets geles.
- [x] Pack V4 : `F05_PACKAGER/CODEBASE/packager.py` greffe
      vanus_gate. Jackpot drop selection opposee + combo. Alarme =
      flag info. Skip / match absent = hole. p_modele / EV intacts.
      Pas cable Telegram / workflow. Tickets geles.
- [x] Pack V5 : Telegram relais `/vanus` `/vanus ID`. Lecture
      vanus.signal.v1. Jackpot = veto, alarme = info. Skip / absent /
      contrat faux / match miss = hole. Jamais un p. `/modele` `/gel`
      aussi KNOWN (Worker + parse). Tickets geles.
- [x] Pack V6 : ledger freeze greffe vanus_gate. Jackpot/alarme =
      flags T0. Skip / absent / match miss = hole. p/EV intacts.
      freeze_lot 7 args intact. F06 n'apprend pas. Tickets geles.
- [x] Pack VX : `vanus_calibrate.py` CSV Big 5 + fit_dc +
      backtest_market. BOM CSV strippe (utf-8-sig), jamais invente.
      Live 2425+2526 cutoff 2026-01-01 : n=950 verdict **NO-GO**
      (rps_gap + logloss_gap). ECE 0.008 OK. Elo = hole.
      n<300 = verdict None. Ne touche pas tickets_enabled.
      Sortie gitignore. Tickets geles.

**Handoff** : tickets GELES. Verdict mesure = NO-GO. Ne pas `/gel off`.
Ne pas `/valider-2` en live. `/modele` pour l'etat. Relancer
`python F00_RADAR/CODEBASE/vanus_calibrate.py --seasons 2425,2526 --cutoff 2026-01-01`
quand Elo pose / plus de saisons. Sans GO = gel. Signal VANUS a coller
dans `ARCHIVUM/vanus/latest.json`. Telegram : `/vanus` apres `/capture`.

## ETAT v6.0 — BASKET MLE + COMMUTATION SPORT (2026-11-16)

Cahier `cahiers-des-charges-PARI-BASKET (1).html` execute sur branche
`pari-forge-basket-m1`, puis fusionne dans `pari-forge-perturabo-xs4c`
(merge `7b95490`). Foot reste maitre, gaz intact.

- [x] **Phase 0** : `config/moteur_basket.json` (`tickets_enabled=false`, engine
      `basket_mle`) + `moteur_sport.py` (fail-safe foot, `ARCHIVUM/state/sport_actif.json`).
      14 tests.
- [x] **Phase 1** : `market_basket.py` + fixtures CSV. Valeur absente = `None` +
      trou, jamais 0. 16 tests.
- [x] **Phase 2** : `model_basket.py` (normal + Monte-Carlo, stdlib),
      `fit_basket.py` (MLE ridge, centro `<=1e-6`), `engine_basket.py` (μ/σ, jamais un p).
      49 tests.
- [x] **Phase 3** : `backtest_basket.py` OOS strict, portes via
      `backtest_market.apply_gates` (seule autorite). 25 tests. **Verdict = None**
      (n=4 sur fixtures, pas de cotes de cloture). Basket reste GELE.
- [x] **VANUS** : depot `gyutedy/VANUS` branche `speculum-basket` → master
      (`1150fc3`). Champ `sport` optionnel, `BASKET_INDEX_ORDER`,
      `vitibet_basket.py`, `SHARED/OUT/signals-basket/latest.json`. 144 tests verts.
      PARI `vanus_gate.py` sport-aware (`path(sport)`, mapping basket, pas de X).
- [x] **Cahier B** : `/sport` `/basket`, `/modele` 2 etats, `/gel` sur sport actif,
      `/valider-2` sur le drapeau actif, `build_system23` (3 doubles). Relais
      `parse.py` + `index.js` + `schema_listen.json` + `/help` alignes. 46 tests.
- [x] **Cahier C** : `docs/CAHIER_BASKET.md`, TRACKING/INDEX, GUIDE, ce fichier.
      `env_pari` laisse intact sur decision du Warsmith (C.1 non appliquee).
- [x] **Verification** : 43/43 scripts `test_*.py` PARI verts, 144/144 VANUS verts.
      7 e2e échouent mais **identiques sur base saine** (tesseract absent, donnees
      manquantes) = aucune regression.

**Handoff** : 3 ecarts au cahier notes — (1) `CMDS` avait 23 cles d'origine (pas 22)
→ 25, aucune cle retiree ; (2) CORRIGE (2026-11-16) : `market_basket.normalize` transporte desormais
`odds_home`/`odds_away` (colonnesoptionnelles, absentes = None + trou cote backtest)
et `backtest_basket` passe `brier_gap` comme 4e argument de `apply_gates` (plus de
trou `logloss` fantome). Verdict GO atteignable : verifie `n=300, brier_gap<=0,
ece<=0.03` → GO ; `brier_gap>0` → NO-GO. Trou `n_oos` propage dans la sortie ;
(3) affichage systeme 2/3 avant `/approve` documente mais non cable dans `workflow.py`.
Basket GELE, aucun `sport_actif.json`, aucun CSV, aucune calibration. Ne pas
`/gel off`. Ne pas `/valider-2` en basket. Paper-trading >= 100 paris et CLV > 0
requis apres GO.

## ETAT v6.1 — CAPTEUR BASKET + DONNEES PARTIELLES (2026-11-17)

- [x] **Capteur F01** `F01_SENTINEL/CODEBASE/connectors/basket_feed.py` : boxscores
      NBA via `nba_api` (stats.nba.com, sans cle) + cotes h2h historiques The Odds
      API. Ecrit `ARCHIVUM/cache/basket/<saison>.csv` (gitignored) avec les 8
      colonnes du contrat. Cote absente = cellule vide + trou `marche_absent`.
- [x] **Recuperation effectuee** : 2023-24 = 1230 matchs, 2024-25 = 1225 matchs
      (2455 au total). `fit_basket.py` tourne : `sigma=16.4964`, centre residu 0,
      `basket_params.json` ecrit (gitignore). **Correctif** : `fit_basket.py` ajoute
      `F00_RADAR/CODEBASE` au `sys.path` (import direct de `market_basket` repara).
- [x] **Backtest** `backtest_basket.py 2025-01-01` : `n_oos=744`, `brier_modele=
      0.248349`, `brier_marche=null`, `ece=0.495088`, **verdict `null`**. Trous
      `marche_absent` sur les 744 matchs + rps/logloss.
- [ ] **BLOQUANT** : la cle `ODDS_API_KEY` de `env_pari` est au **plan gratuit**.
      L'endpoint `/v4/historical/...` repond `401 HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN`
      (les endpoints de decouverte `/events` passent, mais ne donnent pas les cotes).
      Sans cotes de cloture : brier_gap null → **GO impossible** → basket reste GELE.
      Ne pas `/gel off`, ne pas parier.

**Handoff** : pour debloquer, passer `ODDS_API_KEY` au plan payant The Odds API
(historique `basketball_nba`, marche `h2h`, depuis mi-2020), relancer
`python F01_SENTINEL/CODEBASE/connectors/basket_feed.py --seasons 2023-24,2024-25`
puis `fit_basket.py` puis `backtest_basket.py 2025-01-01`. Verdict GO exige
n>=300, brier_gap<=0, ece<=0.03 — sinon gel conserve. Aucune estimation de cote.

## ETAT v6.2 — CAPTURE BASKET TELEGRAM + COTES GRATUITES + FIT ANCRE (2026-11-17)

- [x] **Cotes de cloture gratuites** : `F01_SENTINEL/CODEBASE/connectors/closing_odds_yahoo.py`
      recupere les cotes MGM/Yahoo du depot public `csdurfee/scrape_yahoo_odds`
      (2023 = 1318 matchs, 2024 = 1320). Jonction stricte (date, equipe domicile,
      equipe exterieure) sur les CSV de `basket_feed.py` : **2454/2455 cotes remplies**.
      1 trou declare (`0022300945`, absent de la source), jamais de cote estimee.
      Plus aucune dependance a `ODDS_API_KEY` payante pour le backtest.
- [x] **Capture basket Telegram** : `/sport basket` puis `/capture` + le tableau Winner Bet
      **dans le meme message**. `input_capture_basket.py` lit **uniquement** `1 (ML)` / `2 (ML)`.
      `1X2` (X ~9.60 = nul en fin de temps reglementaire) et `Handicap/Total` (prix sans
      ligne) sont stockes en `diag` avec `utilise: false` + trou `handicap_total_sans_ligne`.
      `game_id` = `#20071`, horaire **Africa/Kinshasa (UTC+1)**, `Demain` resolu au moment
      de la capture, doublons de copier-coller ignores. Reponse Telegram = `match | ML |
      p_modele | EV`. Sortie `F01_SENTINEL/OUT/capture_basket.json` (A_VALIDER).
      `/valider-1` reste foot-only ; moteur basket GELE, `/valider-2` refuse.
- [x] **Correctif fit — ancrage temporel** : `fit_basket.anchor_from_rows()` fixe l'age des
      matchs sur la **derniere date du jeu de donnees** (un `as_of` explicite reste possible).
      Avant : `datetime.now()` avec demi-vie 45j sur des donnees 2023-2025 → poids ~0 →
      ridge ecrasait les 30 ratings a `0.0` → p1 constant `0.557` pour tous les matchs.
      Apres : **30/30 ratings non nuls** (Boston `0.7693`), sigma `14.9516`, p1 variable
      `0.522`–`0.560` sur la capture type. C'etait la cause du "moteur qui ne bat pas le marche".
- [x] **Backtest reel** (cutoff `2025-01-01`) : n_oos=744, brier_modele=`0.244277`,
      brier_marche=`0.195320`, brier_gap=`+0.048957`, ece=`0.491989` → **verdict NO-GO**
      (rps_gap, ece, logloss_gap). Le modele reste moins precis que le marche : gel conserve.
- [x] **Tests** : 111/111 sur 6 fichiers (fit 19, backtest 32, engine 13, model 17,
      capture basket 15, closing odds 15). Compile OK. Aucun e2e lance.

**Ecart ouvert** : `backtest_basket.py:100` calcule `abs(p-y)` (MAE) et le compare au gate
`ece_max=0.03` prevu pour un vrai ECE bine (le foot utilise `walkforward.ece(..., bins=10)`)
— gate structurellement infranchissable. `apply_gates` recoit `brier_gap` deux fois
(rps_gap et logloss_gap). Non corrige : le cahier interdit de baisser un gate pour forcer un GO.
Le verdict NO-GO actuel est independant de ces deux points (gap positif suffit).

**Handoff** : basket GELE, aucun ticket, aucune mise. Cotes Yahoo = source gratuite,
aucune dependance API payante. Suite = ameliorer le modele (sigma ~15 face a des ecarts de
ratings ~1) et/ou corriger la metrique ECE avec accord Warsmith. Le plan gratuit
`ODDS_API_KEY` n'est plus bloquant.

## ETAT v6.3 — MESURE D'ECE CORRIGEE (Cahier V3 P0-2, 2026-11-18)

- [x] **Vrai ECE bine** : `backtest_basket.ece_binned()` remplace le MAE `abs(p-y)`.
      Poids par bin sur 10 bins. Verrouille par test : modele calibre -> 0.0,
      modele inverse -> 0.9. Le gate `ece_max 0.03` reste **identique** ; il est
      desormais mesurable au lieu d'etre structurellement infranchissable.
- [x] **Logloss reel** : `apply_gates(n, brier_gap, ece, ll_gap)` recoit maintenant
      `ll_gap = (logloss_modele - logloss_marche) / n` au lieu de `brier_gap` deux fois.
      Nouveaux champs de sortie : `logloss_modele`, `logloss_marche`, `logloss_gap`.
- [x] **Backtest reel apres correction** : n_oos=744, brier_gap=+0.048957,
      ece=0.005797 (OK), logloss_gap=+0.109056 -> **NO-GO** (rps_gap, logloss_gap).
      Le gel reste la regle : le modele est moins precis que le marche, point.
- [x] **Tests** : `test_backtest_basket` 38/38 (dont ece_vide, ece_calibre, ece_inverse,
      ece_pas_un_mae, logloss_gap_reel, ece_bine_dans_sortie).

**Handoff** : P0-2 du cahier V3 livre. L'ECE n'est plus un faux probleme ; le vrai travail
porte sur la qualite predictive (brier_gap > 0 et logloss_gap > 0). Aucun seuil abaisse,
aucun `/gel off`. P0-3 (`/systeme` S1-S4) a faire ensuite.

## ETAT v6.4 — SYSTEMES S1-S4 CABLES SUR TELEGRAM (Cahier V3 P0-3, 2026-11-18)

- [x] **S1 deja present** : `combinator.build_system23()` (3 doubles AB/AC/BC).
      L'ecart du cahier V2 (affichage non cable) est desormais resorbé.
- [x] **Nouveau** `F05_PACKAGER/CODEBASE/systemes.py` : S2 dutching egalise
      (2 matchs independants, `p_break_even` explicite), S3 corridor Over/Under
      (meme match, 2 lignes, au moins un gagnant), S4 pivot couvert
      (doubles Pivot-B/Pivot-C + simple Pivot x2, perte plafonnee si le pivot passe).
      Aucune cote n'est estimee, aucune proba inventee : `ValueError` si absent.
      Correctif : le pire cas du corridor prend la **plus petite** cote
      (over 1.83 / under 1.84 a 1500 FC chacun -> perte -255 FC, pas -240).
- [x] **Commande Telegram** `/systeme 2-3|dutching|corridor|pivot` : affichage
      complet (mises, pires cas, EV, `p_break_even` marge incluse) **avant**
      `/approve`. Refus si le moteur du sport actif est gele, si aucun ticket
      `/valider-2` n'existe ou si une donnee manque. Registre CMDS 24 -> 25 cles.
      Relais Worker + `parse.py` + `/help` alignes (`systeme` + argument).
- [x] **Tests** : `tests/test_systemes.py` 22/22 (S1 regression, S2/S3/S4,
      refus zero-data, pire cas corridor, commande enregistree). Suite basket
      complete 139/139. Compile OK.

**Handoff** : P0-3 du cahier V3 livre. Tous les systemes faconnent la **variance**,
jamais la marge du book — ils ne rendent pas un moteur NO-GO jouable. Le gel reste
intact : aucun `/systeme` ne construit de ticket tant que `tickets_enabled = false`.

## ETAT v6.5 — MIGRATION SECRETS GITHUB (Cahier V3 P0-1 étape 2, 2026-11-18)

- [x] **19 Secrets GitHub crees/mis a jour** via API chiffree (noms = cles de l'ancien
      `env_pari`). Valeurs = celles de l'ancien fichier : **a faire tourner cote
      fournisseurs, puis a remplacer dans Settings → Secrets**. Aucune valeur n'a ete
      affichee ni committee.
- [x] **`.github/scripts/write_env_pari.py`** reconstruit `MONDES_FORGES/PARI/env_pari`
      au runtime depuis les secrets non vides. Aucune valeur journalisee.
- [x] **5 workflows cables** : `pari_daily.yml`, `pari_listen.yml`, `pari_odds_t0.yml`,
      `pari_odds_t2h.yml`, `worker_deploy.yml` (etape « Ecrire env_pari depuis les Secrets
      GitHub »). Les commentaires « pas GitHub Secrets » ont ete corriges.
- [x] **`env_pari` retire du suivi git** (`git rm --cached`) et ajoute au `.gitignore`
      PARI avec `.env`. Le fichier local reste present pour le travail hors CI.
- [x] **Tests** : `tests/test_write_env_pari.py` 7/7 (noms seulement, valeurs non
      affichees, fichier ecrit depuis un environnement simule).

**Reste (P0-1 étape 3 — PREPAREE, NON EXECUTEE)** : l'historique git contient encore les
anciennes valeurs (15 occurrences). Procedure a lancer par le Warsmith **apres rotation** :

    git clone --mirror https://github.com/gyutedy/PERTURABO.git /tmp/perturabo-mirror
    cd /tmp/perturabo-mirror
    pip install git-filter-repo
    git filter-repo --path MONDES_FORGES/PARI/env_pari --invert-paths
    git remote add origin https://github.com/gyutedy/PERTURABO.git
    git push --force --all origin
    git push --force --tags origin

⚠️ Reecrit toutes les SHA, impose un force-push, un arret des Actions pendant l'operation
et un re-clonage par tous les collaborateurs. Aucune execution sans accord explicite.

**Handoff** : plus aucun secret versionne a partir de ce commit ; seul l'historique ancien
reste a purger. Le PAT GitHub partage en conversation doit etre revoque en priorite.
Gel et moteurs inchanges.

## ETAT v6.6 — CAHIER V3 COMPLETE (2026-11-19)

Packs T5 / V6 / F4 / B3. Doctrine intacte : aucun seuil abaisse, aucun pari automatique,
un seul producteur de nombre (`apply_gates`), stdlib seulement.

- [x] **T5 (cahier §5)** : `F00_RADAR/CODEBASE/backtest_scores_foot.py`. Walk-forward 1X2
      vs marche, refit Dixon-Coles tous les 30 jours sur `t < date` uniquement. Adapte aux
      vraies signatures du depot (`market_csv.load_dir` renvoie un dict, `score_matrix` une
      matrice, `parse_cutoff` un datetime — `[:10]` sinon fuite de cutoff,ouverte par le test).
      Brier / RPS / logloss / ECE bine / CLV. Verdict via `backtest_market.apply_gates`
      (seule autorite) sur `config/moteur.json`. Sortie `calibration_scores_foot.json` gitignore.
      `tickets_enabled=False` jamais touche. Test `tests/test_backtest_scores_foot.py` 21/21.
- [x] **V6 (cahier §6)** : `vanus_fetch.fetch_signal()` + `--sport basket --signal <url>`.
      Cible `ARCHIVUM/vanus/signals_basket.json`, URL aussi dans `PARI_VANUS_SIGNALS_URL`.
      Contrat `vanus.signal.v1` + `sport=basket` exiges ; timeout / http / vide / html /
      json / contrat / sport faux = hole, jamais de proba, jamais de fichier ecrit.
      CSV foot et CLI existante inchanges. `test_vanus_fetch` 41/41, `test_vanus_gate` 37/37.
- [x] **Correction liee** : `vanus_gate.veto_codes(..., sport="basket")` utilisait le mapping
      dans le mauvais sens (`"away"` au lieu de `"2"`). `VANUS_TO_PARI_BASKET` inverse.
      `packager.build_pack(..., sport=)` transmet le sport au gate (defaut foot).
      `test_vanus_packager` 25/25 (jackpot basket drop bien la selection `2`).
      Aucun pari basket ne se construit : `tickets_enabled=false`.
- [x] **F4 (cahier §4 critere ②)** : `/systeme` affiche desormais `Marge effective : X%`
      (moyenne des `overround`/`marge` de top3.json pour les jambes, `— (trou)` sinon),
      en plus de p_break_even et des pires cas, avant `/approve`. `test_systemes` 24/24.
- [x] **B3 (dette)** : `vanus_calibrate.save_verdict()` persiste un resume versionne
      `ARCHIVUM/learnings/verdict_foot.json` (`contract pari.verdict_foot.v1`) a chaque run
      CLI (`--verdict-out`), sans donnees brutes. `/modele` l'affiche en repli si
      `calibration_moteur.json` absent. Fichier initial = reconstruction documentee du run
      VX (n=950 NO-GO), desormais remplace par le run reel du 2026-11-22 (n=950 NO-GO, holes []). `test_vanus_calibrate` 47/47.

- [x] **Runs reels 2026-11-22** : 10 CSV Big 5 (2425+2526) telecharges dans
      `ARCHIVUM/cache/f00/` (gitignore). `vanus_calibrate.py --seasons 2425,2526
      --cutoff 2026-01-01 --skip-fetch` : n=950, verdict **NO-GO** (rps_gap +0.009378,
      ece 0.008296, logloss_gap +0.029895, holes []). `backtest_scores_foot.py --cutoff
      2026-01-01` : n_oos=950, rps_gap +0.011518, ece 0.027339, logloss_gap +0.036687,
      CLV -0.026119 sur n_clv=339 → **NO-GO**. Aucun seuil abaisse, gel conserve.

**Reste hors agent** : (1) **revoquer le PAT GitHub** (cahier P0-1) et purger l'historique
(`git filter-repo`) apres accord Warsmith ; (2) deployer VANUS sur PythonAnywhere et
fournir l'URL du export basket pour que `/vanus` montre un signal reel. Les CSV et runs
reels foot sont desormais faits (ci-dessus). Aucun `/gel off`, aucun `/valider-2` basket,
aucun seuil abaisse.

## ETAT v7.0 — CAPTEUR WINNER V5 / LLM VISION (2026-11-22)

Branches dediees : `pari-winner-sensor-m1` (PARI, depuis `ffc0785`) et `speculum-winner`
(VANUS, depuis `1150fc3`). Fork avant tout code, conformement a l'etape 0 du cahier.
Aucun moteur, gel, ledger ou registre existant n'est retouche hors ajout en fin de CMDS.

- [x] **VANUS (cahier A)** : `winner_common.py` (lecture seule, HTML archive avant parsing),
      `winner_basket.py` (2 Way + Total Spreads), `winner_foot.py` (1X2 + OU2.5 + HSH
      `diagnostic_only`), `winner_order.py` (VANUS **ordonne** les donnees : tri/dedupe par
      match_key, jamais un calcul), 2 fixtures, `tests/test_winner.py` **30/30** hors ligne.
- [x] **PARI (voie primaire)** : `llm_vision.py` — lecteur LLM **generique OpenAI-compatible**.
      Cle/base/model lus **uniquement dans `env_pari`** (`PARI_WINNER_LLM_KEY`,
      `PARI_WINNER_LLM_BASE_URL`, `PARI_WINNER_LLM_MODEL`), jamais dans un GitHub Secret,
      jamais dans le code ou un log. Deux lectures independantes (passage 1 temperature 0,
      passage 2 temperature 0.2) : divergence = trou, jamais une moyenne. Prompt : tous les
      matchs visibles (meme >10), en-tete du haut applique a toutes les lignes, rien invente.
      Le LLM est un **lecteur**, pas un producteur de p ni de verdict.
- [x] **PARI (parseur et gardes)** : `winner_vision.py` — V1 double transcription, V2 bornes
      (cote [1.01,50], ligne NBA [180,320]), V3 grille 1X2 [1.00,1.35], V4 absent = null +
      trou. `tests/test_winner_vision.py` **18/18** (dont 12 matchs d'un coup et config LLM
      lue depuis un `env_pari` temporaire — le vrai fichier n'est jamais ecrit par le test).
- [x] **Transport automatique** : `vanus_fetch.py --kind slate` (URL = `PARI_WINNER_SLATE_URL`)
      valide `vanus.slate.v1` + sport et ecrit `ARCHIVUM/winner/slate_{sport}.json` — le
      facteur livree quand PARI en a besoin. `tests/test_vanus_fetch.py` **46/46**.
- [x] **Consommation** : `winner_ingest.py` + `tests/test_winner_ingest.py` **9/9**. Contrat
      faux / cross-sport / slate absent = vide + trou, jamais de lecture partielle. Marches
      `diagnostic_only` (HSH) conserves et marques ; devig F03 s'applique comme partout.
- [x] **Telegram** : `/winner [foot|basket]` ajoute en fin de `CMDS` (26 -> **27 cles**),
      relais `parse.py` + `index.js` + `schema_listen.json` + `/help` alignes.
      `tests/test_winner_telegram.py` **9/9**, `test_workflow_basket` **18/18**.
      `cmd_winner` corrige le bug du cahier (defaut = sport actif, pas toujours basket).

**Non fait (depend de l'operateur)** : run reel sur une capture avec la cle LLM — le code est
pret, il suffit de poser les 3 variables dans `env_pari` puis
`python F01_SENTINEL/CODEBASE/winner_vision.py --images <captures> --sport basket`.
Aucun `/gel off`, aucun ticket, aucun seuil abaisse. `test_baseline` echoue en local parce
que les CSV foot reels sont presents dans le cache (comportement attendu hors CI vierge).

## ETAT v7.1 — RUN REEL LLM VISION (2026-11-22)

- [x] **Cle et fournisseur** : `env_pari` contient `PARI_WINNER_LLM_KEY`,
      `PARI_WINNER_LLM_BASE_URL=https://integrate.api.nvidia.com/v1` et
      `PARI_WINNER_LLM_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b` (les autres modeles
      testes timeout ; gemma-3-12b-it renvoie une 404 « function not found » sur ce compte).
      Fichier gitignore : aucune valeur dans un commit, aucun log, aucun GitHub Secret.
- [x] **Run reel `cap2.PNG`** : `winner_vision.py --images ... --sport basket` ->
      `ARCHIVUM/winner/slate_basket.json` : **3 matchs, 0 trou**, double transcription
      concordante. Toronto–NY `2.42/1.55`, total `214.5`, `1.84/1.83` ; San Antonio–Detroit
      `1.22/4.20`, total `221.5`, `1.86/1.81` ; Minnesota–Portland `1.68/2.16`, total
      `225.5`, `1.81/1.86`. `winner_ingest.py basket` -> `latest_basket.json`.
      `/winner basket` affiche les 3 matchs + rappel devig F03, jamais un p.
- [x] **Trace** : l'image est desormais copiee dans `ARCHIVUM/winner/images/` AVANT lecture
      LLM (horodatage). Ce dossier est gitignore ; les slates sontversionnes comme observations.
- [x] **Corrections suite au run** : prompt impose le tiret entre equipes (sans lui le parseur
      ne separait pas les equipes) et impose la colonne **2 Way (2 cotes)**, pas le FT 1X2
      (3 cotes) que le LLM lisait a tort sur `cap4.PNG`. Tests : vision 18/18, ingest 9/9,
      telegram 9/9, fetch 46/46.

**Reste** : capture **foot** (les 4 PNG ne contiennent que du basket) pour exercer
`/winner foot` et le HSH `diagnostic_only` en reel ; brancher le relais Telegram avec une
image reelle ; eventuellement second point de prix T-2h/T-0 via `vanus_fetch --kind slate`.
Tickets et gels inchanges.

## ETAT v7.2 — TEST REEL FOOT (2026-11-22)

- [x] **Capture foot reelle** : `t1.jpeg` + `t2.jpeg` (8 matchs : La Liga, La Liga 2,
      Serie A, HNL, Czech Liga) -> `winner_vision.py --sport foot` : **8 matchs, 0 trou**,
      double transcription concordante. 1X2 et U/O 2.5 conformes aux images sur les 8 matchs
      (ex. AC Milan `1.63/4.30/4.70`, U/O `2.60/1.48` ; Getafe–Atletico `6.50/3.90/1.55`,
      U/O `1.63/2.10`). HSH `3.10/3.00/2.02` identique sur les 8 matchs -> confirme le
      tarif template ; capture mais **diagnostic_only**, jamais un ticket.
- [x] `winner_ingest.py foot` -> `latest_foot.json`, `/winner foot` affiche les 8 matchs
      avec 1X2, U/O, HSH marque diagnostic, rappel devig F03, **jamais un p**.
- [x] Deux sports maintenant couverts en reel : basket (`cap2.PNG`, 3 matchs) et foot
      (`t1/t2.jpeg`, 8 matchs). Aucun ticket, aucun `/gel off`, aucun seuil abaisse.

**Reste** : cablage « photo Telegram -> LLM -> slate » automatique (aujourd'hui image locale
en `--images`, Telegram affiche avec `/winner`) ; second point de prix T-2h/T-0 si utile.

## ETAT v7.3 — VERIFICATION MOTEUR SUR COTES WINNER REELLES (2026-11-22)

Avant tout cablage Telegram, la chaine de math a ete exercee sur les slates reels :
`tests/test_winner_moteur.py` **10/10**. `devig.multiplicative` respecte l'invariant
`S>1 => fair_odds > cote` sur **tous** les marchs reels (foot 1X2 + OU2.5, basket ML +
Total) ; marges Winner mesurees : **1X2 foot 8,99 %**, **OU2.5 foot 8,61 %**,
**ML basket 5,81 %**, **Total basket 9,01 %**. Le HSH (`3.10/3.00/2.02`) est identique
sur les 8 matchs, sa marge est superieure a celle du 1X2, et il reste `diagnostic_only`.
Aucune probabilite produite, aucun ticket, moteurs toujours geles (`tickets_enabled=false`).

**Suite** : cablage « photo Telegram -> LLM -> slate » (input uniquement Telegram),
puis verification e2e avant toute decision. Rien n'est ouvert automatiquement.

## ETAT v7.4 — P_MODELE SUR LES COTES WINNER (2026-11-22)

`F03_FORGEWARD/CODEBASE/winner_pmodel.py` : le `p_modele` n'est **pas** lu dans les cotes.
Il est calcule par le moteur Dixon-Coles deja entraine (`dc_params.json`, CSV 2425+2526,
cutoff 2026-01-01) : normalisation des noms Winner (`Getafe CF` -> `Getafe`,
`Atletico Madrid` -> `Ath Madrid`), `lambdas_for`, matrice de scores -> `P(1/X/2)`, puis
comparaison aux cotes Winner deviguees : `EV = p_modele * cote - 1`, `edge_net = p/p_fair - 1`.
`tests/test_winner_pmodel.py` **12/12**.

Run reel sur `latest_foot.json` : **8 analyses, 1 seul `p_modele` disponible** — Getafe–Atletico
(`SP1`) : `P(1)=21,9 %`, `P(X)=29,8 %`, `P(2)=48,3 %` ; cote `6.50/3.90/1.55` ->
**EV `+42,4 % / +16,4 % / −25,2 %** (edge net positif sur Getafe et le nul). Les 7 autres
matchs sont des **trous `equipe_absente`** : Frosinone, Sparta Praga, HNK, Osasuna, Eibar,
Celta Fortuna, Burgos ne sont pas dans les CSV telecharges (Big 5 seulement) — Zero Data,
Zero Calc, aucun EV invente. `tickets_enabled=false`, aucun ticket, HSH jamais utilise.

**Pourquoi 1 seul** : nos CSV couvrent E0/SP1/I1/D1/F1 ; il faut ajouter lesligues manquantes
(La Liga 2, HNL, Czech Liga) pour couvrir les 8 matchs. Ce n'est pas un bug de calcul.

## ETAT v7.5 — LIGUES SP2/I2 AJOUTEES (2026-11-22)

- [x] **Whitelist** : `market_csv.COVERED` + `capteurs.LIGUE_CODE` acceptent `SP2` (La Liga 2)
      et `I2` (Serie B). 4 CSV telecharges (2425+2526) dans `ARCHIVUM/cache/f00` (gitignore).
      Croatie HNL et Czech Liga **absentes** de football-data.co.uk (verifie sur la page
      `data.php`) : aucun CSV invente, ces matchs restent des trous `equipe_absente`.
- [x] **Refit propre** : `fit_dc.py --as-of 2026-01-01` (meme cutoff que le backtest, sinon
      les poids recent changent le p_modele). `dc_params.json` contient maintenant **12 ligues**
      dont SP2/I2 ; 5188 lignes.
- [x] **Run reel** : `winner_pmodel.py --sport foot` -> **2 matchs avec p_modele sur 8** :
      Getafe–Atletico (SP1) `P=21,9/29,8/48,3 %`, EV `+42,4/+16,4/−25,2 %` ;
      Burgos–Albacete (SP2) `P=44,9/28,3/26,8 %`, EV tous negatifs -> **aucun bet**.
      AC Milan–Frosinone = `ligue_differente` (I1 vs I2) : jamais de comparaison跨-ligues.
      Les 5 autres = `equipe_absente`. Aucun ticket, moteurs geles.
- [x] **Tests** : 50/53 verts ; les 3 echecs restent environnementaux (CSV foot reels en
      cache pour `test_baseline`, `sport_actif=basket` en local pour les 2 autres) et sont
      identiques sur une base propre.

## ETAT v7.6 — COMPLETION DES LIGUES DE COUPE (2026-11-22)

- [x] Premier League (`E0`), Ligue 1 (`F1`), Bundesliga (`D1`) etaient deja en cache ;
      **Championship (`E1`)** et **Bundesliga 2 (`D2`)** ajoutes (CSV 2425+2526, gitignore).
      `market_csv.COVERED` et `capteurs.LIGUE_CODE` les couvraient deja.
- [x] **Ligue des champions : indisponible** — `.../2526/CL.csv` renvoie une page HTML, pas un
      CSV ; football-data.co.uk ne couvre pas les coupes d'Europe. Aucun CSV invente ; les
      matchs de C1 resteront des trous tant qu'une source whitelistee n'est pas ajoutee.
- [x] Refit `fit_dc --as-of 2026-01-01` : 14 ligues, **6904 lignes**. Les 2 matchs deja analysés
      gardent exactement les memes chiffres (fit independant par ligue) :
      Getafe–Atletico `p 21,9/29,8/48,3 %`, `fair 14,6/24,3/61,1 %`,
      `EV +42,4/+16,4/−25,2 %` ; Burgos–Albacete `p 44,9/28,3/26,8 %`,
      `fair 45,8/29,1/25,1 %`, `EV −11,5/−12,4/−3,5 %`.

## ETAT v7.7 — OU2.5 BRANCHE SUR LE P_MODELE (2026-11-22)

- [x] `winner_pmodel.py` calcule aussi **Over/Under 2.5** depuis **la meme matrice de scores**
      (`p_ou25`, ligne 2.5, `P(over) + P(under) = 1`) puis devig les cotes Winner
      `under_2_5`/`over_2_5` -> EV et edge_net. Le HSH reste `diagnostic_only`, jamais utilise.
      `tests/test_winner_pmodel.py` **16/16** (dont OU absent = trou, EV et somme des probas).
- [x] **Reponse CSV** : un fichier football-data.co.uk n'est **pas** par marche. Les **18 CSV**
      (14 ligues x 2425/2526) contiennent tous `FTHG/FTAG`, `B365H/D/A` **et**
      `B365>2.5 / B365<2.5` (verifie colonne par colonne). Donc partout ou le 1X2 est
      calculable, l'OU2.5 l'est aussi — aucun CSV supplementaire a telecharger.
- [x] **Run reel** : Getafe–Atletico OU `P=62,5/37,5 %`, cotes `1.63/2.10` ->
      **EV under +1,8 %**, over −21,2 %. Burgos–Albacete OU `P=58,2/41,8 %`,
      cotes `1.62/2.12` -> EV under −5,7 %, over −11,5 %. Aucun ticket, moteurs geles.

## ETAT v7.8 — CABLAGE PHOTO TELEGRAM -> LLM (2026-11-22)

- [x] **Secrets GitHub** : `PARI_WINNER_LLM_KEY`, `PARI_WINNER_LLM_BASE_URL`,
      `PARI_WINNER_LLM_MODEL` crees via API chiffree (SealedBox), valeurs jamais affichees.
      `write_env_pari.py` les ecrit dans `env_pari` au runtime des Actions.
- [x] **Relais** : `parse.py` + `index.js` transmettent `capture_file_id` pour `/winner` avec
      photo (caption `/winner foot` ou `/winner basket`, defaut basket).
- [x] **pipeline** : `ORCHESTRATOR/LISTEN/winner_telegram.py` telecharge la photo, appelle
      `llm_vision` en **double lecture**, ecrit `ARCHIVUM/winner/slate_{sport}.json` et la vue
      `latest_{sport}.json`. `pari_listen.yml` l'execute avant `workflow.py`, qui affiche ensuite
      `/winner` avec cotes, trous et rappel devig F03. Image archivee avant lecture.
- [x] **Tests** : `test_winner_telegram` **13/13** (photo transmise, sport depuis cmd, yml,
      cles secrets). Suite unitaire 50/53 ; les 3 echecs restent environnementaux et identiques
      sur base propre.
- [ ] **Verification en ligne** : necessitates un vrai envoi photo dans Telegram + un run Actions
      (non executable ici). Le chemin local `--images` reste disponible en repli.

## ETAT v7.9 — ETANCHEITE DES BRANCHES (2026-11-22)

- [x] Les fusions dans `pari-forge-perturabo-xs4c` et `master` (VANUS) ont ete **annulees**
      par `git revert` (sans重写 de l'historique). Les branches live sont revenues exactement
      au point de sauvegarde (`git diff 7e6fa0a origin/...` = vide). Le capteur Winner reste
      **exclusivement** dans `pari-winner-sensor-m1` et `speculum-winner`.
- [x] `index.js` : `GH_REF` par defaut = **`pari-winner-sensor-m1`** au lieu de la branche live.
      `worker_deploy.yml` (copie du fork) ne se declenche que sur `pari-winner-sensor-m1`, donc
      le Worker deploie le code du fork et envoie les commandes a cette branche.
- [ ] Aucun test en ligne encore fait (necessite le run `pari-worker-deploy` vert puis un vrai
      envoi photo `/winner`). Repli local `--images` toujours disponible.

## ETAT v8.0 — VALIDATION SAISON COURIANTE + PAPER-TRADING (2026-11-22)

- [x] **Refit 2627** : 9 ligues x 3 saisons (2425, 2526, 2627) = **27 CSV**, 7944 lignes,
      `fit_dc --as-of 2026-11-01` (cutoff avant les captures du 22/11, zero fuite). Le grand EV
      n'etait **pas** un artefact de vieilles donnees : Getafe passe de `21,9 %` a `22,3 %`
      (EV 1X2 `+44,7 %` au lieu de `+42,4 %`) ; Burgos passe a `60,6 %` (EV `+19,4 %`).
      L'ecart avec Winner est stable — toujours a traiter comme **hypothese**, pas comme pari.
- [x] **Paper-trading** : `F06_TRACKER/CODEBASE/paper_trader.py` enregistre dans
      `ARCHIVUM/winner/paper_trades.json` les seules jambes a **EV >= 3 %** (cote Winner prise,
      p_modele, EV, mise 1 FC, `resultat: EN_ATTENTE`, `ticket: false`). HSH jamais inclus,
      aucune mise reelle. Run reel : **3 paris simules** (Burgos 1 a 1.97 EV +19,4 % ;
      Getafe 1 a 6.50 EV +44,7 % ; Getafe X a 3.90 EV +18,7 %). `tests/test_paper_trader.py`
      **8/8** (seuil, zero ticket, zero HSH, zero duplication).
- [ ] **Reglement** : des que les resultats 2627 contiennent ces matchs, registrar G/P et CLV
      (cote prise vs `B365C*`), puis ECE/hit-rate. Objectif **>= 100 paris** avant toute mise.
      Branches live intactes : ce travail reste sur `pari-winner-sensor-m1`.

## ETAT v8.1 — AFFICHAGE DES EV SOUS LE SEUIL (2026-11-22)

- [x] `/winner foot|basket` affiche desormais **tous** les marches, y compris ceux dont l'EV est
      positif mais **< 3 %**, dans une section `DIAGNOSTIC (EV positif < 3% — affiche pour trace,
      JAMAIS un pari)`. Exemple reel : Burgos over 2.5 a 2.12 EV +1,43 %, Getafe under 2.5 a
      1.63 EV +0,85 %. Aucune mise, aucun ticket : le `EV_FLOOR 0.03` reste inviolable.
- [x] Le journal `paper_trades.json` porte une section `diagnostic` (`pari: false`) avec ces
      memes jambes. `test_paper_trader` 8/8, `test_winner_telegram` 13/13.
- [x] Origine du seuil (pour trace) : `TRACKING/PLAN_PARI_CONSOLIDE.md:209`,
      `CONTINUATION.md:985` — decision Warsmith, pas une norme invente par l'agent.

## ETAT v8.2 — REGLEMENT DES PARIS SIMULES (2026-11-22)

- [x] `paper_trader.py --settle` lit les CSV `ARCHIVUM/cache/f00/` via `market_csv.load_dir`,
      retrouve le match par noms normalises (alias `Getafe CF` -> `Getafe`,
      `Atletico Madrid` -> `Ath Madrid`), lit **FTHG/FTAG** et decide G/P :
      `1X2` selon `h>a / h=a / h<a`, `OU_2.5` selon `h+a < 3 / > 3`. Ecrit `score`, `date_csv`,
      et un **CLV proxy** = `cote_prise / cote_cloture_football_data - 1` (marque
      `clv_source: proxy_football_data` : la cloture vient d'un autre book que Winner).
- [x] Match introuvable = trou `match_csv_absent`/`match_csv_ambiguous`, jamais un resultat invente.
      `tests/test_paper_trader.py` **12/12** (dont reglement 1-0, CLV, score).
- [x] Run reel : **0 regle** — les 3 matchs simules sont du 22/11 et les CSV s'arrevent avant.
      On relancera `--settle` quand `B365C*` et FTHG/FTAG seront presents pour ces dates.

## ETAT v8.3 — REGLEMENT REEL DES 3 PARIS (2026-11-23)

- [x] **Resultats** : les CSV football-data etaient encore en retard (dernier match SP1 au 08/11).
      Recuperes via **API-Football** (source whitelistee, cle `env_pari`) :
      `Burgos 1-0 Albacete`, `Getafe 0-3 Atletico Madrid` (statut FT, 22/11).
- [x] **Journal regle** : Burgos 1 a 1.97 = **G** ; Getafe 1 a 6.50 = **P** ; Getafe X a 3.90 = **P**.
      Bilan : **1G/3P**, retour `1.97 - 1 - 1 = -0,03 FC` sur 3 mises de 1 FC (-1 %).
      Echantillon trop petit pour conclure ; un EV positif ne promet pas la victoire (Getafe
      avait ~22 % de chances : perdre etait l'issue la plus probable).
- [x] **CLV absent** : l'API gratuite n'expose pas les cotes de cloture et les CSV ne sont pas a
      jour — trou `clv_absent_close_api`, jamais un CLV invente. Quota API journalier epuise
      (429) en cours de route ; `settle_api` gere maintenant le 429 sans crash.
- [x] Run reel `--settle` : **0 en attente**, 3 regles. `test_paper_trader` 12/12.

## ETAT v8.4 — TEST REEL BASKET (2026-11-23)

- [x] `cap1.PNG` + `cap2.PNG` -> LLM vision : **8 matchs, 0 trou**, double lecture concordante.
      Colonne **2 Way** (2 cotes) bien separee du FT 1X2 (3 cotes) — la correction du prompt
      fonctionne. Exemples : Charlotte–Memphis `2.33/1.58`, total `216.5`, `1.81/1.86` ;
      Chicago–Cleveland `3.55/1.28`, total `240.5`, `1.83/1.84`.
- [x] `winner_ingest.py basket` -> `latest_basket.json`, `/winner basket` affiche les 8 matchs.
      Bug corrige : `_winner_diag` importait `winner_pmodel` sans ajouter `F03_FORGEWARD/CODEBASE`
      au `sys.path` quand `workflow.py` est lance directement (cas Actions) -> ImportError.
      `test_winner_telegram` 13/13.
- [ ] `p_modèle` basket toujours non branche : cotes et marches lisibles, mais pas encore d'EV
      (parametres MLE NBA presents dans `basket_params.json`).

## ETAT v8.5 — P_MODELE BASKET (2026-11-23)

- [x] `basket_params.json` regenere (`fit_basket.py` : 2455 matchs NBA, sigma **16.1145**,
      centre residu 0). `F03_FORGEWARD/CODEBASE/winner_pmodel_basket.py` calcule le
      `p_modele` ML via `engine_basket.predict` + `model_basket.p_home_win`, compare aux cotes
      Winner deviguees et ecrit `ARCHIVUM/winner/pmodel_basket.json`. `tests/test_winner_pmodel_basket.py`
      **9/9**.
- [ ] **RESULTAT IMPORTANT** : le modele **ne discriminent pas** les matchs. Sur les 8 matchs
      reels, `p_home` va de 0,498 a 0,574 (dispersion **0,076**) alors que le marche Winner va
      de 0,234 a 0,801 (dispersion **0,566**) — ratio **0,135**. Les EV calcules (jusqu'a +156 %)
      sont donc **artificiels** et non exploitables. Garde-fou ajoute : `fiable: false`,
      trou `discrimination_faible` sur chaque ligne. Aucun pari basket ne doit etre journalise.
- [ ] Suite = cahier V3 P2 : ameliorer la discrimination (fenetre, hierarchie, home_adv,
      features repos/blessures), en mesurant le `brier_gap` apres CHAQUE changement, sans
      baisser de seuil. Le marche Total reste diagnostic (`sigma_total_non_calibre`).

## PROCHAINES ETAPES (a faire plus tard)

1. ~~Connecteurs API live~~ ✅ **BRANCHÉS v1.1** : `capteurs.py` (F00) + 4 connecteurs whitelist — football-data.co.uk (stats Dom/Ext + split MT, **sans clé**, fenêtre glissante 12 matchs/équipe + fusion saisons antérieures), ClubElo (Elo, **sans clé**, gracieux si réseau fermé), API-Football + football-data.org (calendrier, clé). Testé LIVE sur Premier League 2627 (radar réel Arsenal-Man City).
2. ~~Alerte cotes/valeur en direct~~ ✅ **P3** : cron `pari_odds_t2h.yml` (30 min) + `odds_watch.py`. Recast EV T-2h. Cle absente = skip.
3. ~~Commandes bot avancées `/radar` `/pack` `/match`~~ ✅ **v2.5** cablees (Worker + parse.py + workflow). `/roi` deja dans le cycle.
4. ~~Backtest Football-Data.co.uk 5 saisons~~ ✅ **v2.6** `shares.json` 7 ligues. Pente Elo encore trou (pas de carte Elo).
5. ~~OCR winner bet~~ ✅ **P4** tesseract dans Actions. Image sans binaire = Zero Data. Oracle vision hors siege.
6. ~~Learnings actifs Top N radar~~ ✅ **v2.6** identity < 50 tickets ; clip ROI 50+. Pondération par marché = plus tard (50+ tickets reels).

## DÉCISIONS VERROUILLÉES

| Décision | Choix | Raison |
|---|---|---|
| Devise de référence | **USD** (mises en unités, 1u = 1% bankroll) | ROI stable fc/USD ; le tracker convertit, ne divise jamais le % par la monnaie |
| Bookmaker | **Winner Bet** (cotes collées à la main) | Pas d'API ; txt/OA via bot ; capture via Oracle vision (plus tard) |
| Marchés actifs | MT2 prolifique (signature, cote ~2.10), O/U 1.5, O/U 2.5, 1N2, brit? BTTS | La même matricefique de scores produit tout ; O/U 1.5 et O/U 2.5 sont des marchés distincts (cible le nombre total de buts) |
| Moteur | Dixon-Coles + Poisson par mi-temps, pur Python | zéro dépendance, Replit/Action-ready; `penaltyblog` en option avancée |
| Seuils EV | 3% standard / 8% ligues exotiques (flag dans fixtures) | doctrine TYRANT ; auto-ajusté par calibration au fil des tickets |
| Mises | Kelly 1/8 defaut, 1/4 si ECE walk-forward <= 0.03 et P(EV>0) >= 0.55 et n>=50 ; max 5% bankroll ; combiné : MC conjoint, max 1u ; budget FC operateur intact | protection against ruin |
| Frégates LLM | TYRANT + HERALD seulement, clé unique optionnelle `ORACLE_API_KEY` (OpenAI-compatible) | l'oracle n'interprète pas les chiffres — jamais |
| Canal | Telegram privé **bidirectionnel** : Worker CF (webhook) → `pari_listen.yml` → `workflow.py` → notifier. 1 operateur (`chat_id`). Capture v1 = texte colle meme message. | discrétion + mobile ; GitHub n'est pas always-on |
| Données | whitelist : Football-Data.co.uk, ClubElo, API-Football, football-data.org, Understat | FBref xG retiré 01/2026 — source morte |
| Pronostics YouTube | collectés et notés, jamais dans le moteur | biais de survie |
| Tickets | ledger de TOUS les tickets (gagnants + perdants) | sans les pertes, no learning (survivorship bias) |
| Fraîcheur sources | toute source datée (pub + récupération) ; info d'une saison passée = recroisement obligatoire avant usage | doctrine figée de l'ancienneté = bug silencieux |
