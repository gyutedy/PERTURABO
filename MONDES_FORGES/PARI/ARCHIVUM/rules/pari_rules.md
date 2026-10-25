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
| Mise max (par siège) | 5% bankroll | 3% bankroll |
| Combinés max | 3 jambes, toutes +EV, ⅛ Kelly, max 1u | idem |
| Loterie (comb. 1M+ jambes) | budget séparé ≤ 2% bankroll | idem |

## Le verdict en 3 couleurs

- 🔥 **VALUE** : EV ≥ seuil → l'orchestre propose la mise Kelly.
- 🟡 **THIN** : 0 < EV < seuil → positive mais diluée par l'incertitude du modèle → passable, mise réduite ou SKIP.
- ⛔ **NO BET** : EV ≤ 0, données insuffisantes, ou proba correcte mais cote vidée. **Aucun contournement.**

## Zero Data, Zero Calc

Toute donnée manquante est **déclarée** (flag `estimate` + qualité data baissée), jamais comblée en silence. Si l'échantillon est insuffisant (< 6 matchs stats, < 5 matchs cotes) → NO BET obligatoire sur le marché concerné. Une EV calculée sur de la data pourrie est une perte sèche à retardement.

## Les tickets (F06 TRACKER)

- Le ledger prend **TOUT** : gagnants ET perdants. Le biais de survie est une hérésie.
- Chaque ticket : jambes, cotes, mise, marché, résultat, date. Après 50 tickets : calibration + pondération learnings.
- Les pronostics YouTube sont collectés et notés comme données testables — jamais entrés dans le moteur de calcul.
