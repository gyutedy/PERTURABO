# RÈGLES DU MONDE PARI

## La mathématique du siège

1. **La statistique crée la vérité, la cote dicte la rentabilité.** Un match probable à cote pourrie = NO BET. Un match improbable mais mal coté = à étudier.
2. **P(MT2 > MT1) ≠ part des buts en MT2.** La part des buts (~56% en 2e MT) mesures l'intensité, pas la probabilité de gagner le marché "MT2 prolifique". Chaque 0-0/0-0, 1-0/0-0 ou 1-1/1-1 tue le pari MT2. Le moteur calcul la vraie proba depuis la matrice par mi-temps.
3. **Dixon-Coles obligatoire** sur les bas scores : Pool Poisson brut sous-estime systématiquement 0-0, 1-0, 0-1, 1-1.
4. **Forces relatives à la ligue, jamais brutes** : α_att et β_def se calculent rapports à la moyenne du championnat (baseline).
5. **Décadence temporelle** : les matchs récents pèsent plus (10-15 derniers). Un match d'il y a 4 mois compte moins qu'un de la semaine passée.
6. **Split Domicile/Extérieur strict** : forme à domicile pour l'équipe A, à l'extérieur pour l'équipe B. Une équipe n'a pas le même rendement selon le terrain.
7. **Time-decay et split absent = flag `estimate`** : part ligue par défaut (~42-44% MT1), qualité data baissée, seuil EV durci.

## Les seuils

| Paramètre | Standard | Ligue exotique / secondaire |
|---|---|---|
| Seuil EV minimum | **+3%** | **+8%** |
| Seuil Kelly | ¼ Kelly | ¼ Kelly |
| Mise max (par siège) | **3% bankroll** (audit corpus 2026-10 : le corpus pro retient 1–2% avant Kelly) | 3% bankroll |
| Combinés max | 3 jambes, toutes +EV, ⅛ Kelly, max 1u | idem |
| Loterie (comb. 1M+ jambes) | budget séparé ≤ 2% bankroll | idem |

## Le verdict en 3 couleurs

- 🔥 **VALUE** : EV ≥ seuil → l'orchestre propose la mise Kelly.
- 🟡 **THIN** : 0 < EV < seuil → positive mais diluée par l'incertitude du modèle → passable, mise réduite ou SKIP.
- ⛔ **NO BET** : EV ≤ 0, données insuffisantes, ou proba correcte mais cote vidée. **Aucun contournement.**

## Zero Data, Zero Calc

Toute donnée manquante est **déclarée** (flag `estimate` + qualité data baissée), jamais comblée en silence. Si l'échantillon est insuffisant (< 6 matchs stats, < 5 matchs cotes) → NO BET obligatoire sur le marché concerné. Une EV calculée sur de la data pourrie est une perte sèche à retardement.

## Moteur vs doctrine — le scope (audit corpus 2026-10-27)

Rappel de freshness_sources Art. 4 : le moteur n'écoute pas les contenus. Audit des 26 transcriptions, précision de scope :

**Moteur (données autorisées)** : stats froides (football-data.co.uk, ClubElo), cotes Winner Bet. Elo / xG Understat / H2H / forme 10 / scores H2H = **métadonnées d'affichage** (`/data`, jamais dans Poisson / Dixon-Coles). FBref retiré.

**F00 notes (non binaires)** : SofaScore + Sportradar + WhoScored. Vote OUT si 3 sources indépendantes / 48h. DOUTE / IGNORE = trou, ne touche pas λ. Oracle jamais un OUT.

**Doctrine / données testables — JAMAIS moteur :**
- **Exchanges & trading Betfair** (lay, home lay, lay away, scalping over/under) : le monde parie chez un bookmaker, pas sur un exchange. Ces transcriptions = doctrine de discipline (variance, gestion du risque), pas des marchés ouverts au siège.
- **Arbitrage, latence, courtsiding** : exploits d'exécution et d'infrastructure, hors scope du siège quantitatif.
- **Bonus, free bets, promos** (extra places, 2-up early payout, boosts, goals galore bonus) : la doctrine advantage play ne s'applique pas chez Winner Bet. Si une offre équivalente existe un jour → addendum de règles AVANT usage, jamais improvisé.
- **Systèmes de mise alternatifs** (1-3-2-6, martingale, parlays dégradés) : le test 1-3-2-6 de 30 jours (−40 £ contre flat staking +9,30 £) confirme l'hérésie. Seuls EV + Kelly fractionnel gouvernent la mise.
- **Pronostics YouTube / fiches d'analyse** : données testables (déjà verrouillé par freshness Art. 4).

## Les tickets (F06 TRACKER)

- Le ledger prend **TOUT** : gagnants ET perdants. Le biais de survie est une hérésie.
- Chaque ticket : jambes, cotes, mise, marché, résultat, date. Après 50 tickets : calibration + pondération learnings.
- Les pronostics YouTube sont collectés et notés comme données testables — jamais entrés dans le moteur de calcul.

## Input cotes : capture screenshot / OCR

- Le flux capture screenshot → OCR → texte est **autorisé comme input de cotes** (parallèle TXT brut / JSON direct).
- Il ne doit jamais servir de source de probabilité directe ni de stats.
- La ligue dans une capture propre ton bookmaker est **donnée affichée par le livreur**, pas devinée.
- Si la capture ne donne pas les champs minimums (équipes, ligue, cotes), on ne devine pas : on bloque en Porte 1 (Zero Data, Zero Calc).
- Le résultat OCR reconstitué doit être **validé par l'utilisateur (parseur visible) avant tout calcul**.
