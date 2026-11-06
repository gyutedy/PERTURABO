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
| `ORCHESTRATOR/CODEBASE/doctor.py` | Evidence GO/CHECK/FAIL (`--offline --json`). Cles = noms. Gate n<300 bruit / 300-499 observation / >=500 moteur. CLV median 30j < -3 pts = FAIL. | `/status` `/status doctor` |
| `ORCHESTRATOR/CODEBASE/research_bundle.py` | Dossier `ARCHIVUM/research/B-XXX` + `manifest.json` SHA-256 a `/valider-1`. `--verify`. Gap declare, jamais comble. | workflow.py `/valider-1` |
| `ARCHIVUM/research/` | Bundles hashés (gitignore). Token L-XXX porte `bundle_id`. | research_bundle.py |
| `ARCHIVUM/learnings/lots.json` | Ledger F06 lots (token L-XXX = cle, snapshot T0). F06 n'apprend pas. | workflow.py `/valider-2`, ledger.py |
| `CONTRACTS/schema_ledger.json` | Contrat lot / jambes / snapshot T0 / settle G/P/EN_ATTENTE | F06 ledger.py |
| `ORCHESTRATOR/CODEBASE/data_view.py` | Vues `/data` compact + `/data N` fiche (affichage, jamais Poisson) | workflow.py `cmd_data` |
| `ORCHESTRATOR/LISTEN/` | Relais webhook Telegram (Worker + parse.py + inbox_capture.py v2.10.1) | Cloudflare / e2e_listen |
| `.github/workflows/pari_listen.yml` + `pari_daily.yml` | tesseract-ocr + fra (P4) avant siege. Inbox = script Python, plus de heredoc YAML. | Actions |
| `F01_SENTINEL/IN/capture_telegram.md` | Inbox capture texte colle depuis Telegram. Photo = capture_telegram.jpg / .png / .webp. `resolve_capture` prend le plus recent (v2.10). | pari_listen.yml |
| `CONTRACTS/schema_listen.json` | Contrat update Telegram → {cmd, capture_text, chat_id} | Worker + parse.py |
| Repo vivant | `gyutedy/PERTURABO` branche principale `pari-forge-perturabo-xs4c` (pas `v2-live-vox-c`) | Worker GH_REF |
| Worker LIVE | `https://pari-listen.pari-listen.workers.dev` | `.github/workflows/worker_deploy.yml` (CLOUDFLARE_* dans env_pari) |
| `F00_RADAR/CODEBASE/{capteurs,enrich,vote,cache,http_util,odds_watch}.py` | Enrich `/capture` : binaire + vote OUT/DOUTE/IGNORE. T-2h = `odds_watch` | workflow.py `/capture` `/valider-1` ; `pari_odds_t2h.yml` |
| `F01_SENTINEL/CODEBASE/connectors/odds_api.py` | The Odds API (h2h + totals 2.5). Matching nom + difflib 0.9. Cache 1 hit/ligue/jour | odds_watch.py |
| `ARCHIVUM/odds/` | Snapshots T-2h (`latest.json`, `t2h_*.json`) | odds_watch.persist |
| `env_pari` | Cles operateur (periode de test, versionne). F00 : `FOOTBALL_DATA_ORG_KEY`, `API_FOOTBALL_KEY`, `SPORTRADAR_API_KEY`, `SOFASCORE_RAPIDAPI_KEY` / `WHOSCORED_KEY`. ESPN voix 3 = public sans cle. Odds T-2h : `ODDS_API_KEY` (optionnelle). Oracle : `ORACLE_API_KEY` + `ORACLE_BASE_URL` + `ORACLE_MODEL` (Zro glm-5.3-flash). Charge par `workflow.load_env_pari`. | workflow.py, football_data_org.py, api_football.py, sportradar.py, sofascore.py, espn.py, whoscored.py, odds_api.py, tyrant.py, herald.py, notifier.py |
| `ARCHIVUM/cache/f00/` | Cache 1 hit / equipe / jour (gitignore) | F00 enrich |
| `ARCHIVUM/fixtures/notes_qualitatives.json` | Notes votees F00 (OUT → TYRANT) | enrich.py |
| `F00_RADAR/F00_LOG.md` | Scans de ligue (nombre matchs, top verdicts) | F00 RADAR |
| `F01_SENTINEL/F01_LOG.md` | Collectes + nettoyages de donnees | F01 |
| `F01_SENTINEL/OUT/capture_parsed.json` | JSON reconstitue de la capture (txt/md/png/pdf/docx). v4.0 : `holes` Moins/Plus, `cote_plate` | F01 input_capture |
| `TRACKING/PLAN_PARI_CONSOLIDE.md` | Plan d execution unique v3.5+v4 (packs S0–S16) | Warsmith / agent |
| `tests/test_input_capture_moins_plus.py` | S1 : Moins/Plus sans 2.5, cote_plate, ligue_code E1/D2 | input_capture + capteurs |
| `F02_BREACHER/F02_LOG.md` | Analyses (λ, matrices, probas) | F02 |
| `F03_FORGEWARD/F03_LOG.md` | EV, values, misa Kelly | F03 |
| `F04_HERALD/F04_LOG.md` | Fiches rédigées (+ usage Oracle) | F04 |
| `F05_PACKAGER/F05_LOG.md` | Packs + dashboards générés | F05 |
| `F06_TRACKER/F06_LOG.md` | Tickets loggés/settle, calibration | F06 |

Convention : chaque frégate ajoute une ligne `[TS] [mode] détail` dans son LOG.md ; le Warsmith écrit ses notes de décision dans les gates via `IW_CUSTOS.py --mode gate --notes "..."`.
