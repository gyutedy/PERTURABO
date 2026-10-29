# AUDIT CORPUS — DOCTRINE PARI vs TRANSCRIPTIONS

> Audit finalisé le 2026-10-29 (v2 — après dépôt des corpus advantage play / maths / trading).
> Objet : dire, thème par thème, ce que le corpus **confirme**, ce qu'il **n'apporte pas**
> dans notre périmètre, et ce qu'il **contredit** (hérésies).
>
> RAPPEL HÉRÉSIE : le moteur de probabilités (F02 BREACHER / F03 FORGEWARD) n'utilise
> JAMAIS le contenu des transcriptions — stats froides uniquement. Les transcriptions
> nourrissent la **doctrine**, les filtres TYRANT et le tracker.

## État du corpus au jour de l'audit
- 34/97 transcriptions archivées (`catalogue_videos.csv` maître, catégories RESOURCES/).
- 10 sources statut `TO_CONFIRM` : sans date de publication YouTube = source NON DATÉE =
  **non utilisable pour une décision** (règle `freshness_sources.md` Art. 1-2).
- 0 transcription de plus de 14 jours à recroiser avant usage.

## Tableau de conformité

| Thème / stratégie | Sources principales | Verdict | Statut dans le monde PARI |
|---|---|---|---|
| EV positive (payout > vraie proba), verdict long terme | advantage_beginners, lowrisk148, oddsjam_lecture, ev_11_steps | **Confirme la doctrine** | Moteur : F03 (seuils 3% / 8% exotique) |
| Kelly fractionné & ruine du parieur | kelly_criterion_deepdive, ev_11_steps, gambling_economics | **Confirme** — la fraction protège de la variance avant que l'edge se manifeste | Moteur : Kelly ¼ (⅛ combiné), 1u = 1% bankroll |
| De-marging (cote juste vs cote affichée) | oddsjam_lecture, advantage_beginners | **Confirme** — jamais de décision sur la cote brute | Moteur : F03 de-marging |
| Each-way + extra places (promotions définissables) | eachway_loophole, advantage_beginners, lowrisk148 | **Doctrine inspirante** — l'edge vient d'une promo calculable + couverture exchange | HORS MOTEUR : Winner Bet n'a pas ces promos. Lectures gardées ; filtre TYRANT si une promo équivalente apparaît |
| Arbitrage / surebet | arbitrage_30d | **Confirme l'audit 2026-10-27 : hors moteur** — opérationnel, dépend des limites, pas un modèle de proba | Hérésie listée |
| Systèmes de mise (1-3-2-6, chase, compounding) | test_1326, grow_bankroll_7d | **Rejeté** — la remontée de mise ruine avant que l'EV se manifeste | Hérésie — mise = Kelly ¼ uniquement, pas de martingale |
| Trading exchange / back-to-lay / latence | home_lay_betfair, home_win_betfair, under_25_goals_betfair, lay_away_betfair, courtsiding, horse_racing_latency | **Doctrine inspirante** — l'edge vient de la latence ou de l'infrastructure exchange. Pas applicable : Winner Bet sans API ni exchange | Archivé, hors moteur |
| Greyhounds & marchés lagging | banned_greyhounds, beat_bookies_greyhounds | **Hors périmètre** (sport hors PARI, infra exchange) | Archive consultable |
| Combinés 10+ / loterie | acca_goals_galore, challenge £50→£500 (en partie), lucky15_science, lucky15_value | **Confirme** : combiné long = budget divertissement séparé, jamais capital de chasse ; le compounding déguisé (challenge) est rejeté | Profil Warsmith `budget_loterie_pct: 0.02`, combiné ≤ 3 jambes |
| O/U 1.5 / 2.5 lissés par les buts | over25simple1, under25btf1, over15correctly1, goalavoid1, lategoalstrat1, bestleagues1 | **Confirme** : la proba vient de la distribution des buts (Poisson), pas du sens du pari | Moteur : F02 λ total + split mi-temps |
| Mi-temps prolifique | highest_scoring_half… | **Confirme** : 2e MT marque plus (fatigue, pénalités, remplacements) — marché signature | Moteur : MT_PROLIFIQUE |
| BTTS pré-match / in-game | BTTS Part 2/3/4, hot picks BTTS | **Confirme** : marché distinct de 1X2, issu de la matrice | Moteur : BTTS |
| Pronostics / "hot picks" / challenge compounding | shottarget1, lignes challenge £50→£500 | **Rejeté comme moteur** — biais de survie, sources souvent non datées | F06 tracker : notés, jamais calculés |

## Synthèse — 5 conclusions

1. **Le moteur PARI est aligné** sur ce que le corpus confirme : EV, cote juste (de-marging),
   Kelly fractionné, Poisson par mi-temps. Aucun thème ne contredit ces bases.
2. Les stratégies qui reposent sur une **infrastructure que Winner Bet n'offre pas**
   (promos extra-places, exchanges, latence, arbitrage, greyhounds) sont archivées comme
   doctrine inspirante — jamais moteur. Cohérent avec l'audit du 2026-10-27.
3. Les **systèmes de mise** (1-3-2-6, chase, challenges à compounding) sont hérétiques
   partout où le corpus les teste.
4. Les **pronostics hot picks** restent notés par F06 et n'entrent jamais dans les calculs.
5. Il **manque encore** : les fiches de dépouillement individuelles (`TPL_fiche.md`) par
   vidéo, à produire au fil des sessions ; l'audit de fraîcheur automatique sert de garde.

## Effet sur les règles
- Rien ne change dans les seuils moteur : l'audit confirme la configuration v1.2.
- Les 10 sources `TO_CONFIRM` restent bloquées pour toute décision tant qu'elles ne portent
  pas leur date de publication YouTube.
- La fraîcheur est re-vérifiable à tout moment :
  `python3 ingest_transcripts.py --freshness 14`
