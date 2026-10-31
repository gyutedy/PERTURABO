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

## LES MODES

| Mode | Commande | Ce que ça fait |
|---|---|---|
| `input-capture` | `orchestrator.py --mode input-capture --capture c.md [--valider]` | **Capture Winner Bet (txt/md/png/pdf/docx) → JSON reconstitue** (ligue, date, heure, marches, cotes). v2.2.1 recoud les rangs markdown casses par Telegram. → validation Porte 1 → carte |
| `workflow` | `orchestrator.py --mode workflow --cmd "/start ..."` | **Cycle de campagne Telegram** : /start, /capture, /bankroll, /budget JOUR SURTICKET (v2.2.5 force ticket sur), /combos, /valider-1 (inject alias LaLiga/clubs + merge ligues v2.2.7), /valider-2 v2.2.8 (lots token L-XXX + anti-cannibal + snapshot T0 ; refuse si 0 GO, budget non retape, pool vide), /data ledger, /status ledger, /roi settle L-XXX, /stop |
| `radar` | `orchestrator.py --mode radar` | Scan de **toute la ligue** : classement de tous les matchs du jour (buts attendus, P(O2.5), P(MT2 > MT1)) → TOP 20 |
| `siege` | `orchestrator.py --mode siege --ids M1,M2` | Analyse fine des matchs choisis : cotes Winner Bet → de-marging → EV → Kelly → verdict PARIER / NO BET (+ filtre qualitatif + Top 3 + Preview 1) |
| `tickets` | `orchestrator.py --mode tickets --combos 3 --jambes 3:2:2 --budget-fc 6000 --surticket-fc 3000` | **Combinés + backroll** (ticket sûr + reste divisé) → tickets.json + PREVIEW 2 |
| `pack` | `orchestrator.py --mode pack` | Assemblage du pari pack final + dashboard HTML |
| `demo` | `orchestrator.py --mode demo` | Pipeline complet sur une ligue simulée (test, incl. Top 3 + previews v2) |

### Les deux previews (v2)

| | Fichier | Contenu |
|---|---|---|
| PREVIEW 1 | `SHARED/OUT/preview1.html` | données brutes : cotes, probas froides, EV, **Top 3 marchés + score commun 01-10** (buckets HAUTE/MOYENNE/FAIBLE), notes non binaires, qualité data — menu déroulant par match, responsive |
| PREVIEW 2 | `SHARED/OUT/preview2.html` | **ticket final** : cartes de tickets (sur-ticket = matchs au score le plus haut), backroll (budget alloué/reste) — charte PERTURABO, responsive |

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
| F00 | RADAR/CAPTEURS | Scan ligue + **enrich `/capture`** (Elo, xG, repos/H2H, vote notes 3 voix) | `radar.json` + `notes_qualitatives.json` |
| F01 | SENTINEL | Collecte + nettoyage des données (fixtures, stats, cotes txt/capture) | `matches_intel.json` |
| F02 | BREACHER | Le moteur math : Dixon-Coles, Poisson bivarié, Elo, λ par mi-temps | `analysis.json` |
| F03 | FORGEWARD | De-marging (overround/Shin), EV, Kelly 1/4, scanner combinés | `predictions.json` |
| F04 | HERALD | **Frégate lourde (Oracle)** : fiches de siège lisibles + meta-prompt | `reports/*.md` |
| F05 | PACKAGER | Pari pack final (TOP N=10-20) + dashboard HTML (charte IW) | `pari_pack.json` + `dashboard.html` |
| F06 | TRACKER | Ledger des lots tokenises (`lots.json`, v2.2.8) + tickets, ROI. Settle CSV football-data. **N'apprend pas.** | `learnings/*` |
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
| `learnings/` | `lots.json` (token = cle, snapshot T0), `tickets.json` (TOUS gagnants ET perdants), `calibration.json` |

---

## HÉRÉSIES INTERDITES

- ❌ Pari automatique (l'opérateur place — toujours)
- ❌ Martingale / surebet cruel / mise ≥ 5% bankroll (hors loterie dédiée à 2% budget séparé)
- ❌ Promesse de gain — on livre des probabilités, pas des certitudes
- ❌ Chasse externe sources non-whitelistées (hérésie)
- ❌ Pronostics YouTube dans le moteur de calcul (biais de survie) — le tracker les note, period
- ❌ Donnée manquante comblée par une estimation silencieuse → **Zero Data, Zero Calc → NO BET**
- ❌ Note OUT sans 3 sources independantes / LLM qui invente un OUT / FBref / scrape Winner
- ❌ Collecter seulement les tickets gagnants (survivorship bias) — le ledger prend tout

---

## STACK

- **Moteur** : Python pur (stdlib), tournant partout — GitHub Actions, Replit, terminal
- **Dashboard** : HTML statique + Chart.js CDN, charte Iron Warriors (bleu/or/acier), mode discret
- **Canal** : Telegram privé bidirectionnel LIVE (Worker `https://pari-listen.pari-listen.workers.dev` → `pari_listen.yml` sur `gyutedy/PERTURABO` → `workflow.py` → `notifier.py` via `env_pari`). Capture v1 = texte colle. Pages pas encore active (non bloquant).
- **Sources** : whitelist — Football-Data.co.uk, ClubElo, API-Football, football-data.org, Understat. FBref xG = MORT (donnée retirée 01/2026) — donc non utilisée.

*Fer au-dedans, Fer au-dehors. Aucune hérésie ne survivra au siège.*
