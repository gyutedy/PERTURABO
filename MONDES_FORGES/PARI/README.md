# MONDE FORGE PARI

> *"Le pari est un siège. La probabilité est ton plan de forteresse. La cote, c'est le mur — tu attaques seulement là où elle est plus faible que la vérité."*
> — Fer au-dedans, Fer au-dehors.

---

## POSITIONNEMENT

PERTURABO/PARI = le QG de l'**analyse quantitative des matchs de football** (paris sportifs).

```
PERTURABO/PARI            analyse : probabilités, EV, value bets, pari packs (JSON/MD/dashboard)
         │
         ▼
Warsmith (opérateur)      décide : valide les portes, place les paris chez Winner Bet
         │
         ▼
F06 TRACKER               mesure : résultats réels, ROI, calibration → learnings
```

La séparation des rôles est sacrée :
- PARI = **calculer** (probabilités froides, EV, Kelly — zéro intuition)
- L'Oracle (LLM optionnel) = **interpréter le qualitatif** (contexte, enjeux, rédaction) — jamais les chiffres
- Le Warsmith = le **dernier mot** (validation des portes + placement des paris)

Ce monde ne place **jamais** de pari automatiquement. L'opérateur humain est la dernière porte.

---

## LES 2 MODES

| Mode | Commande | Ce que ça fait |
|---|---|---|
| `radar` | `orchestrator.py --mode radar` | Scan de **toute la ligue** : classement de tous les matchs du jour (buts attendus, P(O2.5), P(MT2 > MT1)) → TOP 20 |
| `siege` | `orchestrator.py --mode siege --ids M1,M2` | Analyse fine des matchs choisis : cotes Winner Bet → de-marging → EV → Kelly → verdict PARIER / NO BET |
| `pack` | `orchestrator.py --mode pack` | Assemblage du pari pack final + dashboard HTML |
| `tracker` | `orchestrator.py --mode ticket ...` | Ledger : tickets (gagnants ET perdants), ROI, calibration, pronostiqueurs |
| `demo` | `orchestrator.py --mode demo` | Pipeline complet sur une ligue simulée (test) |

---

## LES 4 PORTES

| Porte | Frégate | Produit | Validateur |
|---|---|---|---|
| 1 | TYRANT | `carte_verdict.json` (GO/NO-GO sur la carte de matchs, seuil EV ligue) | Warsmith |
| 2 | F02 BREACHER | `analysis.json` (matrice de scores, probas 1X2 / O-U / mi-temps) | Warsmith |
| 3 | F03 forgeWARD | `predictions.json` (EV par marché, Kelly, combinés) | Warsmith |
| 4 | F05 PACKAGER | `pari_pack.json` + `dashboard.html` → Telegram/dash | Warsmith |

`F01 SENTINEL` alimente les portes 1-2. `F00 RADAR` s'exécute avant Porte 1. `F06 TRACKER` après Porte 4 et nourrit `learnings/`.

---

## LES FRÉGATES ET AUTORITÉS

| Code | Nom | Rôle | Output |
|---|---|---|---|
| F00 | RADAR/CAPTEURS | Scan ligue complète + veille (marge Winner Bet, pronostiqueurs) | `radar.json` + `RADAR.md` |
| F01 | SENTINEL | Collecte + nettoyage des données (fixtures, stats, cotes txt/capture) | `matches_intel.json` |
| F02 | BREACHER | Le moteur math : Dixon-Coles, Poisson bivarié, Elo, λ par mi-temps | `analysis.json` |
| F03 | FORGEWARD | De-marging (overround/Shin), EV, Kelly 1/4, scanner combinés | `predictions.json` |
| F04 | HERALD | **Frégate lourde (Oracle)** : fiches de siège lisibles + meta-prompt | `reports/*.md` |
| F05 | PACKAGER | Pari pack final (TOP N=10-20) + dashboard HTML (charte IW) | `pari_pack.json` + `dashboard.html` |
| F06 | TRACKER | Ledger des tickets, ROI, calibration, scoring des pronostiqueurs | `learnings/*` |
| TYRANT | Le Tyrant | Vision stratégique : GO/NO-GO carte, seuils EV, filtre ligues exotiques | `carte_verdict.json` |
| ORCHESTRATOR | Le Nerf | Modes radar/siège/pack/tracker/demo, enchaîne les frégates | — |
| IW_CUSTOS | Le Gardien | check-out/check-in/gate/validate — seul accès à `liber_pari.json` | — |

**Partage Oracle** : `TYRANT` + `HERALD` utilisent la clé `ORACLE_API_KEY` (OpenAI-compatible, GitHub Secret). Sans clé → fiches en template, TYRANT se limite au filtre froid. Le monde tourne à 100% sans clé.

---

## ARCHIVUM — LES ZONES

| Zone | Contenu |
|---|---|
| `rules/` | Doctrine des paris (EV/Kelly/NO BET), jeu responsable, **profil Warsmith** (bankroll, devise, seuils) |
| `fixtures/` | La carte de matchs du cours (**une campagne à la fois**) |
| `teams/` | Profils d'équipes (Elo, forme Dom/Ext, xG par MT) |
| `demons/` | **Les bookmakers** — `winner_bet.json` : marges par marché (le 2.10 MT2 !) |
| `odds/` | Historique des cotes collées |
| `knowledge_base/` | Transcriptions YouTube, trading — savoir, séparé des faits |
| `pronostics/` | Tracker des pronostiqueurs YouTube (données testables, pas des oracles) |
| `learnings/` | `tickets.json` (TOUS les tickets gagnants ET perdants), `calibration.json` |

---

## HÉRÉSIES INTERDITES

- ❌ Pari automatique (l'opérateur place — toujours)
- ❌ Martingale / surebet cruel / mise ≥ 5% bankroll (hors loterie dédiée à 2% budget séparé)
- ❌ Promesse de gain — on livre des probabilités, pas des certitudes
- ❌ Chasse externe sources non-whitelistées (hérésie)
- ❌ Pronostics YouTube dans le moteur de calcul (biais de survie) — le tracker les note, period
- ❌ Donnée manquante comblée par une estimation silencieuse → **Zero Data, Zero Calc → NO BET**
- ❌ Collecter seulement les tickets gagnants (survivorship bias) — le ledger prend tout

---

## STACK

- **Moteur** : Python pur (stdlib), tournant partout — GitHub Actions, Replit, terminal
- **Dashboard** : HTML statique + Chart.js CDN, charte Iron Warriors (bleu/or/acier), mode discret
- **Canal** : Telegram (canal principal, privé) + GitHub Pages (dashboard)
- **Sources** : whitelist — Football-Data.co.uk, ClubElo, API-Football, football-data.org, Understat. FBref xG = MORT (donnée retirée 01/2026) — donc non utilisée.

*Fer au-dedans, Fer au-dehors. Aucune hérésie ne survivra au siège.*
