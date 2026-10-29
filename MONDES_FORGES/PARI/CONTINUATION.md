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
- [x] **Phase 6** : workflow Telegram — `ORCHESTRATOR/CODEBASE/workflow.py` (/start, /capture, /budget, /combos, /valider-1, /valider-2, /data, /status, /roi, /stop) + injection stats gracieuse à /valider-1.
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
| Backroll | budget jour + sur-ticket + reste divisé ; mise min 100 FC ; unités si taux FC fourni | gestion du bankroll sans martingale |
| Previews | 2 : Preview 1 (brutes, début de campagne) + Preview 2 (ticket final, charte PERTURABO) ; GH Pages ; responsive | relecture opérateur aux 2 portes de campagne |
| Message /data | rangs Top 3 + score en message dédié, HORS ticket final | séparation lecture d'analyse / ticket final (analyses dans data, rangs dans le ticket final) |
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

## ETAT v2.2 — ECOUTE TELEGRAM (2026-10-29)

- [x] **Phase 8** : relais Cloudflare Worker (`ORCHESTRATOR/LISTEN`) + Action `pari_listen.yml` + inbox `F01_SENTINEL/IN/capture_telegram.md` + contrat `schema_listen.json`. `/capture` Telegram = tableau markdown **dans le meme message**. e2e_listen 23/23 (zero reseau). png/pdf + KV hors v1.
- [ ] **A LA MAIN (Warsmith)** : `wrangler deploy` + 4 secrets Worker + `setWebhook`. Tant que ce n'est pas fait, `/start` dans Telegram n'atteint pas le siege.

Pret pour le **premier test reel** une fois le webhook pose : `/start` puis coller le markdown Winner Bet sous `/capture`, puis `/budget` `/combos` `/valider-1`. Sans stats historiques le siege sort NO BET — c'est la doctrine, pas un bug. CLI fichier (`/capture F01_SENTINEL/OUT/capture_winnerbet.md`) reste valide.

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
