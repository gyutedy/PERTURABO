# CONTINUATION — MONDE FORGE PARI

> Doc de continuité : état d'avancement, prochaine étape, décisions verrouillées.

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

## PROCHAINES ÉTAPES (à faire plus tard)

1. Connecteurs API live : Clé API-Football (Secret GitHub) → récupération auto du fixtures de la ligue au lieu du fichier manuel (F01 `--live`).
2. Alerte ilot/valeur en direct : deuxième Action à T-2h qui re-scanne les cotes collées et alerte Telegram si l'EV s'estompe.
3. Commandes bot avancées : `/radar`, `/pack`, `/roi`, `/match <id>` (webhook Telegram — nécessite un endpointalways-on, route Cloudflare Worker gratuite possible).
4. Backtest Football-Data.co.uk : charger 5 saisons CSV → calibrer les shares arrière-pensée réelle par ligue + poids Elo.
5. OCR winner bet : si clé Oracle vision disponible, mode capture d'écran complète dans le bot.
6. Learnings actifs : pondération du Top N du radar par les résultats du tracker (50+ tickets).

## DÉCISIONS VERROUILLÉES

| Décision | Choix | Raison |
|---|---|---|
| Devise de référence | **USD** (mises en unités, 1u = 1% bankroll) | ROI stable fc/USD ; le tracker convertit, ne divise jamais le % par la monnaie |
| Bookmaker | **Winner Bet** (cotes collées à la main) | Pas d'API ; txt/OA via bot ; capture via Oracle vision (plus tard) |
| Marchés actifs | MT2 prolifique (signature, cote ~2.10), O/U 2.5, 1N2, brit? BTTS | La même matricefique de scores produit tout |
| Moteur | Dixon-Coles + Poisson par mi-temps, pur Python | zéro dépendance, Replit/Action-ready; `penaltyblog` en option avancée |
| Seuils EV | 3% standard / 8% ligues exotiques (flag dans fixtures) | doctrine TYRANT ; auto-ajusté par calibration au fil des tickets |
| Mises | ou Kelly 1/4, max 5% bankroll ; combiné : Kelly 1/8, max 1u, toutes jambes +EV | protection against ruin |
| Frégates LLM | TYRANT + HERALD seulement, clé unique optionnelle `ORACLE_API_KEY` (OpenAI-compatible) | l'oracle n'interprète pas les chiffres — jamais |
| Canal | Telegram principal (privé) + dashboard Pages secondaire | discrétion + mobile |
| Données | whitelist : Football-Data.co.uk, ClubElo, API-Football, football-data.org, Understat | FBref xG retiré 01/2026 — source morte |
| Pronostics YouTube | collectés et notés, jamais dans le moteur | biais de survie |
| Tickets | ledger de TOUS les tickets (gagnants + perdants) | sans les pertes, no learning (survivorship bias) |
