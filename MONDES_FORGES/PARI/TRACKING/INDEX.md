# TRACKING — INDEX MONDE PARI

Cartographie des journaux du monde.

| Fichier | Contenu | Alimenté par |
|---|---|---|
| `IW_CAMPAIGN_LOG.md` | Journal général (check-out/check-in, gates, reset) | IW_CUSTOS.py |
| `IW_TRANSFER_LOG.md` | Transferts inter-frégates (source → dest, md5) | IW_CUSTOS.py |
| `TYRANT/TYRANT_LOG.md` | Verdicts de carte GO/NO-GO | TYRANT |
| `TYRANT/QUALITATIVE_LOG.md` | Verdicts du filtre non-binaire borné (exclusions, seuils, NO BET rec.) | TYRANT qualitative |
| `F05_TICKETS/F05_TICKETS_LOG.md` | Compositions de tickets + backroll par campagne (v2) | F05 combinator |
| `SHARED/STATE/campagne.json` | État du cycle de campagne Telegram (/start → /valider-2). v2.2.5 `bankroll_fc` persiste + `budget_fc`/`surticket_fc` forces. v2.2.4 siege ignore filtered stale | workflow.py |
| `ORCHESTRATOR/LISTEN/` | Relais webhook Telegram (Worker + parse.py) | Cloudflare / e2e_listen |
| `F01_SENTINEL/IN/capture_telegram.md` | Inbox capture texte colle depuis Telegram | pari_listen.yml |
| `CONTRACTS/schema_listen.json` | Contrat update Telegram → {cmd, capture_text, chat_id} | Worker + parse.py |
| Repo vivant | `gyutedy/PERTURABO` branche `pari-forge-perturabo-xs4c` | Worker GH_OWNER |
| Worker LIVE | `https://pari-listen.pari-listen.workers.dev` | wrangler deploy |
| `F00_RADAR/F00_LOG.md` | Scans de ligue (nombre matchs, top verdicts) | F00 RADAR |
| `F01_SENTINEL/F01_LOG.md` | Collectes + nettoyages de donnees | F01 |
| `F01_SENTINEL/OUT/capture_parsed.json` | JSON reconstitue de la capture (txt/md/png/pdf/docx) | F01 input_capture |
| `F02_BREACHER/F02_LOG.md` | Analyses (λ, matrices, probas) | F02 |
| `F03_FORGEWARD/F03_LOG.md` | EV, values, misa Kelly | F03 |
| `F04_HERALD/F04_LOG.md` | Fiches rédigées (+ usage Oracle) | F04 |
| `F05_PACKAGER/F05_LOG.md` | Packs + dashboards générés | F05 |
| `F06_TRACKER/F06_LOG.md` | Tickets loggés/settle, calibration | F06 |

Convention : chaque frégate ajoute une ligne `[TS] [mode] détail` dans son LOG.md ; le Warsmith écrit ses notes de décision dans les gates via `IW_CUSTOS.py --mode gate --notes "..."`.
