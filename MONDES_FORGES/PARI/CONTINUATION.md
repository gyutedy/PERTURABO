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
- [x] **`pari_listen.yml` aussi sur default branch** `v2-live-vox-c` (GitHub n'indexe workflow_dispatch que depuis la default). Le job checkout `GH_REF=pari-forge-perturabo-xs4c`.
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
- [x] **Notes 3 voix** : SofaScore + Sportradar + WhoScored/Opta. Vote OUT si 3 upstreams indépendants / 48h. DOUTE ne touche pas λ. 3 wrappers RapidAPI du même upstream = 1 source. Ligues : E0/SP1/I1/D1/F1/N1. Turquie/Japon = trou si <3.
- [x] **Fatigue** = jours de repos calendrier (binaire dérivé). Météo / motivation hors v1.
- [x] **Gâchette** : `capteurs.py enrich` après parse `/capture` et après inject `/valider-1`. Cache 1 hit/équipe/jour. Timeout / 3 fails = voix morte.
- [x] **TYRANT** : items F00, OUT seulement → `themes`. `notes_count: 0` → pas de filtre. Oracle / HERALD : commentaire après coup si clé, **jamais** un OUT.
- [x] **`/data`** : préfixe `notes: N`. 0 = trou visible.
- [x] **E2E** : `tests/e2e_f00.py` (vote, cache, trou, TYRANT DOUTE, Oracle silence). `PARI_SKIP_INJECT=1` / `PARI_SKIP_F00=1` = offline.
- [x] **`FOOTBALL_DATA_ORG_KEY` LIVE** (2026-11-01) : jeton football-data.org pose dans `env_pari`. Header `X-Auth-Token`. Ping `/v4/competitions` HTTP 200 (13 comps). F00 `rest_days` au `/capture` et `/valider-1`. **Indépendant d'Oracle / modèle premium** : `workflow.py` charge `env_pari` à chaque commande Telegram, secret GitHub vide n'écrase pas.
- [x] **`API_FOOTBALL_KEY` LIVE** (2026-11-01) : jeton api-sports Free (100 req/jour) pose dans `env_pari`. Header `x-apisports-key`. Ping `/status` HTTP 200, plan active. Calendrier F00 (`fixtures-list`), **pas Oracle**. Sportradar / WhoScored / Oracle : encore vides = notes: 0.

## ETAT v2.3.1 — `/data` DEUX VUES (2026-10-31)

- [x] **Contrat** : `h2h.matches[]` (date, home, away, ft, ht) + `form.dom/ext` 10 lignes. `holes` peut contenir `form`, `h2h_scores`, `timing`. Notes qualitatives inchangees.
- [x] **Capteurs** : `football_data_uk.last_matches` / `h2h_matches` depuis le CSV deja telecharge (cache disque, zero reseau si `PARI_SKIP_*`). Club hors CSV = skip CE equipe, `holes += form`. Timing buts = TROU (pas de Sofa ici). Jamais injecte dans Poisson.
- [x] **Affichage** : `ORCHESTRATOR/CODEBASE/data_view.py`. `/data` table compacte HAUTE puis FAIBLE, 1 ligne / match, prefixe `notes: N`. `/data N` fiche (rang 1-based). `/data ledger` inchange.
- [x] **Cablage** : `workflow.cmd_data` ledger | digit → fiche | vide → compact. `parse.py` relais `/data 4` + help `/data N`. Worker JS stale jusqu'au merge.
- [x] **E2E** : compact Q/H2H/TROU, trou = `—`, fiche H2H+forme, timing TROU, `/data 99` refuse, `/data 4` parse, ledger inchange, final ne casse pas.

**Handoff prochain agent** : ne pas setWebhook, ne pas wrangler, pas scrape Winner. Ne pas toucher Dixon-Coles. Repo = `gyutedy/PERTURABO`, PAS `jfbjfojfonf`. `/bankroll` Telegram = refuse par Worker live — alias `/budget bankroll N`. F06 n'apprend pas. `FOOTBALL_DATA_ORG_KEY` + `API_FOOTBALL_KEY` dans `env_pari` (periode de test) — F00, PAS Oracle. FBref / Google / YouTube / RapidAPI search / 2e cerveau 1X2 : hors siege. Merge code vers `pari-forge-perturabo-xs4c` (Worker checkout). HELP Worker git aligne ; Worker deploye stale jusqu'au wrangler.

## PROCHAINES ETAPES (a faire plus tard)

1. ~~Connecteurs API live~~ ✅ **BRANCHÉS v1.1** : `capteurs.py` (F00) + 4 connecteurs whitelist — football-data.co.uk (stats Dom/Ext + split MT, **sans clé**, fenêtre glissante 12 matchs/équipe + fusion saisons antérieures), ClubElo (Elo, **sans clé**, gracieux si réseau fermé), API-Football + football-data.org (calendrier, clé). Testé LIVE sur Premier League 2627 (radar réel Arsenal-Man City).
2. ~~Alerte cotes/valeur en direct~~ 🟡 **MOITIÉ FAITE** : notificateur Telegram branché (`orchestrator.py --mode notify` + `--mode telegram-test`, messages du pari pack). Reste : l'analyse du mouvements de cotes (2e Action à T-2h qui re-scanne les cotes collées si l'EV s'estompe).
3. Commandes bot avancées : `/radar`, `/pack`, `/match <id>` (webhook de base **posé** Phase 8 — Worker + `pari_listen.yml` ; ces 3 commandes ne sont pas encore relayees). `/roi` deja dans le cycle.
4. Backtest Football-Data.co.uk : charger 5 saisons CSV → calibrer les shares arrière-pensée réelle par ligue + poids Elo.
5. OCR winner bet : si clé Oracle vision disponible, mode capture d'écran complète dans le bot.
6. Learnings actifs : pondération du Top N du radar par les résultats du tracker (50+ tickets).

## DÉCISIONS VERROUILLÉES

| Décision | Choix | Raison |
|---|---|---|
| Devise de référence | **USD** (mises en unités, 1u = 1% bankroll) | ROI stable fc/USD ; le tracker convertit, ne divise jamais le % par la monnaie |
| Bookmaker | **Winner Bet** (cotes collées à la main) | Pas d'API ; txt/OA via bot ; capture via Oracle vision (plus tard) |
| Marchés actifs | MT2 prolifique (signature, cote ~2.10), O/U 1.5, O/U 2.5, 1N2, brit? BTTS | La même matricefique de scores produit tout ; O/U 1.5 et O/U 2.5 sont des marchés distincts (cible le nombre total de buts) |
| Moteur | Dixon-Coles + Poisson par mi-temps, pur Python | zéro dépendance, Replit/Action-ready; `penaltyblog` en option avancée |
| Seuils EV | 3% standard / 8% ligues exotiques (flag dans fixtures) | doctrine TYRANT ; auto-ajusté par calibration au fil des tickets |
| Mises | ou Kelly 1/4, max 5% bankroll ; combiné : Kelly 1/8, max 1u, toutes jambes +EV | protection against ruin |
| Frégates LLM | TYRANT + HERALD seulement, clé unique optionnelle `ORACLE_API_KEY` (OpenAI-compatible) | l'oracle n'interprète pas les chiffres — jamais |
| Canal | Telegram privé **bidirectionnel** : Worker CF (webhook) → `pari_listen.yml` → `workflow.py` → notifier. 1 operateur (`chat_id`). Capture v1 = texte colle meme message. | discrétion + mobile ; GitHub n'est pas always-on |
| Données | whitelist : Football-Data.co.uk, ClubElo, API-Football, football-data.org, Understat | FBref xG retiré 01/2026 — source morte |
| Pronostics YouTube | collectés et notés, jamais dans le moteur | biais de survie |
| Tickets | ledger de TOUS les tickets (gagnants + perdants) | sans les pertes, no learning (survivorship bias) |
| Fraîcheur sources | toute source datée (pub + récupération) ; info d'une saison passée = recroisement obligatoire avant usage | doctrine figée de l'ancienneté = bug silencieux |
