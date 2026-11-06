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
