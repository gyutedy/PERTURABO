# PLAN PARI CONSOLIDE — v3.5 + v4 (execution par packs)

> Statut : **fige pour execution**. Pas de code tant que le Warsmith n a pas dit let go.
> Repo : `gyutedy/PERTURABO` branche `pari-forge-perturabo-xs4c`.
> Sous-arbre : `MONDES_FORGES/PARI`.
> Baseline GitHub : origin HEAD (pas un SHA snapshot odds). Plans v3/v4 absents du depot jusqu ici — ce fichier est la source unique.

## 0. Doctrine verrouillee (citer dans CONTINUATION.md des le pack S1)

1. Zero Data / Zero Calc. Trou = `holes: ["..."]`. Jamais de guess, jamais de defaut silencieux.
2. EV = `P_modele * cote_brute - 1`. Devig / scorer / Oracle = diagnostic ou veto, jamais un producteur de p.
3. Oracle / TYRANT / HERALD : lire `content`, jamais un chiffre.
4. Stdlib Python seulement. Secrets hors commit. `env_pari` ne recoit aucune cle nouvelle en clair dans un commit.
5. Tests existants verts (`e2e_*.py`). Chaque pack ajoute `tests/test_*.py` offline.
6. Telegram = unique cockpit. Toute commande nouvelle = `workflow.py` + `parse.py` + Worker `index.js` + `schema_listen.json` + `/help` + GUIDE.
7. Un commit/push **par pack** (2–3 unites), message `PARI vX.Y: <resume>`. CONTINUATION.md dans le meme commit.
8. Session courte : un pack = une session. Stop apres push. Reprise = lire CONTINUATION.md + ce plan, cocher le pack, enchainer.

## 1. Verrous Warsmith (session 2026-11-06) — non negociables

| Sujet | Decision |
|---|---|
| Verrou v2 "non-binaires hors maths" | **Casse a R4**. Facteurs lambda (table operateur). CONTINUATION le note. |
| Ligne Moins/Plus absente | **Pas de 2.5 invente.** `holes: ["ligne_totale_Moins_Plus"]`, cotes gardees. |
| `/marchés` | Commande Telegram reelle, relais complet. |
| Effectifs | **Option A** : 2e tableau colle par l operateur dans le meme `/capture`. Vide = x1.00 + holes. |
| Max 2 jambes / marche | **Supprime.** |
| Ticket mono-marche | **Ajoute.** L operateur exige un ticket dont toutes les jambes sont le meme marche. |
| Meme navire | **Interdit** : deux jambes du **meme match** sur le **meme ticket** (BTTS+Over du meme match = interdit). |
| Taille ticket | **1 a n+10 matchs** (jambes = matchs distincts). `/combos 3:3:2:2` reste valide. |
| Championship / Bundesliga 2 | **Plus hors carte.** Whitelist **E1 + D2**. CSV de **leur** ligue, jamais E0/D1. Club sans ligne = skip CE match. |
| Pre-requis PLAN_V210 / QUANT_V3 sur GitHub | **Absents.** On part de origin HEAD. Ce plan les absorbe. |
| Tests | `e2e_*.py` **et** `tests/test_*.py`. |

## 2. Architecture d empilement (un siege, pas deux)

```
Ph0 (Warsmith) → S1 parseur+ligues → S2-S3 evidence → S4-S5 marches+devig
→ S6-S7 fit+mesure → S8-S10 CLV+F06+Kelly → S11-S14 amiral (/marchés, scorer, lambda, pieges)
→ S15 flags API (pas de 2e lambda) → S16 Oracle + recalibrage scorer
```

v3.5 = le moteur voit et on mesure.
v4 = l amiral elit le type de tir ; le monde elit les navires ; 0 match au-dessus du seuil = 0 ticket.

## 3. Docs a toucher (chaque pack)

Toujours dans le meme commit que le code :

| Fichier | Quoi |
|---|---|
| `CONTINUATION.md` | Entree `ETAT vX.Y` format v2 (contexte, code, tests, handoff). Cocher le pack. |
| `GUIDE_UTILISATION.md` | Commandes, cycle Telegram, exemples `/marchés`, table effectifs, combos 1..n+10, meme match interdit. |
| `TRACKING/INDEX.md` | Nouveaux artefacts (doctor, bundle, market_profiles, election_log, state_factors, config/). |
| `TRACKING/IW_CAMPAIGN_LOG.md` | Decision horodatee du pack. |
| `README.md` | Si nouvelle commande ou nouveau marche. |
| `ORCHESTRATOR/LISTEN/README.md` | Si commande Telegram. |
| `CONTRACTS/schema_*.json` | Si contrat change (listen, ticket, intel, notes). |
| Ce fichier | Cocher `[x]` le pack livre. |

Ne pas creer de GUIDE parallele. Ne pas committer `F01_SENTINEL/OUT/e2e_*` ni secrets.

## 4. Packs d execution (2–3 unites, commit, push, stop)

Numerotation commits : `PARI v3.Y` pour le socle mesure/moteur, `PARI v4.Y` pour amiral/parseur. Un pack = un message de commit qui resume les unites.

### S0 — Ph0 cles (Warsmith, zero code agent)

- Rotation SPORTRADAR, SOFA/RAPIDAPI, ORACLE/ZRO, ODDS_API.
- Revoquer tout token GitHub expose.
- Agent : **ne pas** `git filter-branch` / rewrite history. Si `env_pari` versionne contient un secret, le Warsmith le rotate ; l agent n y touche pas.
- **Stop.** Aucun pack S1 tant que Ph0 n est pas dit GO par le Warsmith.

### S1 — Debloquer le live (v4 R1 + E1/D2 + docs verrous)

**Code**
- `F01_SENTINEL/CODEBASE/input_capture.py` : en-tetes `Moins de X` / `Plus de X` → `uX`/`oX` si la ligne est visible (colonne ou cellule au-dessus). Sinon holes `ligne_totale_Moins_Plus`, **ne pas dropper** les cotes, **ne pas** defaut 2.5.
- MT : 3 cotes identiques sur >= 5 matchs → garder + flag `cote_plate` (journal), pas jeter.
- `capteurs.py` : retirer Championship / Bundesliga 2 de `LIGUE_REJECT`. Ajouter `"championship": "E1"`, `"bundesliga 2": "D2"` (et alias). Inject CSV E1/D2. Relégué ≠ E0.

**Tests** : `tests/test_input_capture_moins_plus.py` (table Warsmith Everton–Coventry etc.). e2e_multiformat / e2e_listen non regressifs. Test ligue_code E1/D2 + rejet LaLiga 2 inchange.

**Docs** : CONTINUATION v4.0 + verrous section 0–1. GUIDE parseur Moins/Plus. INDEX.

**Commit** : `PARI v4.0: parseur Moins/Plus + whitelist E1 D2`
**Push. Stop session.**

### S2 — Evidence 1 (Ph1 doctor + Ph2 bundle)

**Code**
- `ORCHESTRATOR/CODEBASE/doctor.py --offline --json` : GO / CHECK / FAIL. Cles presentes (noms seulement), contrats vs champs, whitelist vs connecteurs, fraicheur cache. Gate 2 niveaux : `<300` bruit ; `300-499` observation ; `>=500` verdict moteur. Exception immediate : CLV median 30j < -3 pts = alerte.
- `research_bundle.py` : a `/valider-1`, dossier + `manifest.json` SHA-256. `--verify`. Gap declare, jamais comble. Token L-XXX reference le bundle.

**Tests** : `tests/test_doctor.py`, `tests/test_research_bundle.py`.

**Docs** : CONTINUATION v3.1 / v3.2. INDEX doctor + bundle. GUIDE : `/status` peut renvoyer le verdict doctor.

**Commit** : `PARI v3.1: doctor + research bundle hash`
**Push. Stop.**

### S3 — Evidence 2 (Ph3 one-writer + journal)

**Code**
- `notifier.py` = seul writer Telegram. Lint `tests/test_one_writer.py` (grep send hors notifier = fail).
- Journal F06 2 volets : (a) procedure a la creation (checks, trous, seuils, Kelly) ; (b) resultat au settle (mise, cote, G/P, pnl, CLV si connu). (a) immutable.
- Compteur churn `config/` : >2 changements / semaine hors calibration → `churn_suspect`.

**Docs** : CONTINUATION v3.3. INDEX journal. GUIDE settle.

**Commit** : `PARI v3.3: one-writer + journal proc/outcome`
**Push. Stop.**

### S4 — Moteur marches + devig (Ph4 + Ph4b)

**Code**
- Memes matrices Poisson : O/U 0.5, 1.5, 3.5, 4.5, DC 1X/X2/12, team totals, score exact (top N si cote fournie). Zero equation changee.
- `F03_FORGEWARD/CODEBASE/devig.py` multiplicatif. Issue manquante → holes, pas de devig cote unique.
- Invariant : S>1 => fair_odds_i > cote_i.
- Champ `edge_net_devig` diagnostic. Tri EV inchange.
- `double_confirmation` : P_modele > P_fair **et** P_modele * cote > 1. Bonus seuil en `config/` (init 1 pt).

**Tests** : `tests/test_markets.py`, `tests/test_devig.py` (triple 2.75/3.40/2.50).

**Docs** : CONTINUATION v3.4 / v3.5.4b. GUIDE marches elargis. README.

**Commit** : `PARI v3.4: marches elargis + devig diagnostic`
**Push. Stop.**

### S5 — Compose + priorite (Ph4c + Ph4d)

**Code**
- combinator : EV compose net = produit (1+edge_net) - 1, precision machine. `jambe_edge_net_negatif` info, pas rejet.
- `config.market_priority` : palier suivant si >= 30 tickets mesures. corners/cards fermes sans data → holes.
- Doctrine CONTINUATION : edge = modele calibre + news plus rapide que le book local ; pas d arbitrage.

**Tests** : 1.03*1.05-1 = 8.15%.

**Commit** : `PARI v3.5: facteur compose + priorite marches`
**Push. Stop.**

### S6 — Fit + baseline (Ph5 + Ph6)

**Code**
- Fit stdlib CSV football-data : rho, bonus domicile, part_mt1 → `ARCHIVUM/learnings/league_params.json` (ou `config/` versionne). Ligue absente → defaut + flag `params: default`.
- `league_averages` = saison complete cachee, pas l echantillon carte. Split att/def dom/ext. Recency EMA demi-vie `config` (defaut 45j). Saison absente → trou + fallback carte + flag.

**Tests** : `tests/test_league_fit.py`, `tests/test_baseline.py`.

**Commit** : `PARI v3.6: fit ligue + baseline saison recency`
**Push. Stop.**

### S7 — Garde-fou empirique + walk-forward (Ph6b + Ph7)

**Code**
- Taux O2.5 empirique /radar. |P_modele - empirique| >= 0.20 → flag TYRANT `incoherence_modele_empirique`.
- Backtest walk-forward, cut-off explicite, jamais in-sample. Metrics Brier / RPS / ECE, hit-rate EV>=3%, yield Kelly 1/4. `backtest_report.json`.
- Workflow ClubElo hebdo `pari_elo_fill.yml` si absent : CSV ClubElo → build-elo → shares elo_slope. Zero cle.

**Tests** : `tests/test_backtest.py` seede.

**Commit** : `PARI v3.8: empirique O2.5 + backtest walk-forward`
**Push. Stop.**

### S8 — Sensibilite devig + CLV T-0 (Ph7b + Ph8)

**Code**
- 2e passe devig additif, ecart journalise, multiplicatif reste defaut.
- Snapshot T-0 (kickoff) en plus T-2h. `/roi settle` stocke `book_odds_close`. Cloture absente = exclu CLV, jamais 0.

**Tests** : `tests/test_clv.py`.

**Commit** : `PARI v3.9: sensibilite devig + CLV T-0`
**Push. Stop.**

### S9 — Metrique CLV + F06 diagnostic (Ph8b + Ph9)

**Code**
- clv = cote_prise / cote_cloture - 1. Agregats : median, % >0, moyen pondere mise. Cibles config (55% / +0.5 pt). Doctor rappelle variance n=30.
- Platt 2 params, Beta-Binomial, P(EV>0) MC seede. **Verrou <50 tickets reels** : sorties = diagnostic `/data`, jamais verdict/mise.

**Tests** : `tests/test_f06_diag.py` bloque sous 50.

**Commit** : `PARI v3.10: CLV metrique + F06 diagnostic`
**Push. Stop.**

### S10 — Kelly (Ph9b)

**Code**
- config : fraction defaut 0.125, plafond 0.25, p_ev_positif 0.55, ece 0.03.
- `calibration_validee` = ECE_walk_forward <= seuil (sortie S7).
- 1/4 seulement si calibration OK **et** P(EV>0) >= 0.55. Sinon 1/8. P absent → 1/8 + holes.
- Combo : un tirage MC conjoint toutes jambes. Fraction journalisee (S3).

**Tests** : `tests/test_kelly_route.py`.

**Commit** : `PARI v3.10.9b: routage kelly 1/8 vers 1/4 gate ECE`
**Push. Stop.**

### S11 — Amiral /marchés + tickets (v4 R2, R6 modifie)

**Code**
- `cmd_marches` dans `workflow.py`. `st["marches"]` jusqu a `/valider-2`.
- Relais : `parse.py` KNOWN + Worker + `schema_listen.json` + help. Alias `/marches` ASCII si Telegram casse l accent, canon = `/marchés`.
- Table de couverture **avant** election (nb matchs au-dessus du seuil, meilleur EV, marge). 0 match → 0 ticket, message honnete.
- `ARCHIVUM/learnings/market_election_log.json` append-only. `/status` alerte si un marche >60% des elections.
- combinator `--markets` : tri EV desc **dans** les marches elus. **Pas** de plafond 2 jambes. **1 a n+10** matchs / ticket (param `/combos`).
- **Meme match = meme navire = interdit** sur un ticket (extension anti-cannibal intra-ticket).
- Flag operateur **ticket mono-marche** : toutes les jambes du ticket = un seul marche.
- EV_FLOOR 0.03 inviolable. EV combo plancher 0.05. Jamais jambe de remplissage. Baisser le floor = refuse.

**Tests** : e2e marches, 0 match → 0 ticket, meme match refuse, mono-marche, 10 jambes distinctes OK, floor refuse.

**Docs** : GUIDE cycle : `/valider-1` → table couverture → `/marchés O/U2.5,MT2` → `/combos` → `/valider-2`.

**Commit** : `PARI v4.1: /marches + tickets 1..n+10 + anti meme-navire`
**Push. Stop.**

### S12 — Scorer (v4 R3)

**Code**
- `ARCHIVUM/learnings/market_profiles.json` versionne.
- Module scorer dans **F03** (eligibilite, pas Poisson F02, pas fiches F04). Documenter le choix dans CONTINUATION.
- Portes A1–A4 binaires hors score (cotes groupe / praticable / historique / marge >20% → refus).
- B1 0.30, B2 0.20 (MT B2 0.25 / B1 0.25), B3 0.20 **asymetrie info seulement** (pas severite blessure), B4 0.15, B5 0.10, B6 0.05.
- Score 0–1, seuil 0.50–0.60 selon marche. Journaliser chaque contribution. Trou data → score reduit + holes.
- Poisson **inchange**.

**Tests** : `tests/test_market_scorer.py`.

**Commit** : `PARI v4.2: market_profiles + scorer eligibilite F03`
**Push. Stop.**

### S13 — Effectifs → lambda (v4 R4) — casse verrou v2

**Code**
- `input_capture.py` : 2e table canonique dans le meme `/capture` : `attaquants_titulaires_absents`, `defenseurs_cles_absents`, `gardien_1_absent`, `milieu_createur_absent`, `jours_repos`, `rotation_lourde`.
- `config/state_factors.json` : att x0.90 / unite (max 2) ; milieu x0.96 ; def adverse x1.06 ; gardien x1.05 ; vide x1.00 + holes. Cap cumule ±20%, journalise.
- `rotation_lourde` (>=4) : **pas** de facteur lambda ; flag TYRANT "O/BTTS deconseilles".
- Derby / meteo / retour 100% : TYRANT veto `marches_exclus` seulement.
- CONTINUATION : decision v2 "non-binaires hors maths" **cassee** pour cette table operateur seulement.

**Tests** : 1 att out → p_o25 baisse ; cap respecte ; absent data → x1.00 + holes.

**Docs** : GUIDE comment coller la table effectifs.

**Commit** : `PARI v4.3: facteurs etat lambda + table effectifs capture`
**Push. Stop.**

### S14 — Pieges + /data (v4 R5 + R8)

**Code**
- 3e lecture cotes : T-0 capture → T-2h → T-0 close. Mouvement / stagnation = donnee B3.
- Detecteurs : `cote_plate`, `marge_anomalique` (B5), `cote_figee_sur_news` (B3), `marche_vitrine` (marge >20% → A4).
- `/data` `/radar` `/match M1` : score correspondance + 6 criteres + flags pieges.
- Vocabulaire Warsmith aligne GUIDE + CONTINUATION.

**Tests** : MT plate x10 → flag ; marge 22% → marche retire.

**Commit** : `PARI v4.4: detecteurs pieges + /data scorer`
**Push. Stop.**

### S15 — Blessures API = flags (Ph10 + Ph10b)

**Code**
- `injuries.py` API-Football (cle existante). Holes si KO.
- 4 flags TYRANT : `double_motivation`, `satisfait_nul`, `buteur_manquant`, `defenseur_manquant`. **Jamais de P**. **Jamais un 2e facteur lambda** (anti-double-compte : severite deja dans S13 si table A ; ici veto / seuil seulement).

**Tests** : `tests/test_injuries.py` mock.

**Commit** : `PARI v3.11: injuries API flags TYRANT sans lambda`
**Push. Stop.**

### S16 — Oracle + recalibrage scorer (Ph11 + v4 R7)

**Code**
- Meta-review Oracle avant `/valider-2` : risques, trous, ranking qualitatif. Test : reponse sans digit.
- Ticket : fees + slippage dans le seuil. Approve L-XXX.
- R7 : backtest poids B1–B6 + seuils (ligue x marche) sur bundles + settles. **Une seule** maj `market_profiles.json`, journalisee. Jamais de poids a la main. Si <50 tickets reels : **ne pas** retuner, garder a priori.

**Tests** : `tests/test_oracle_metro.py` (zero chiffre), `tests/test_backtest_weights.py` seede.

**Commit** : `PARI v4.6: oracle meta + backtest poids scorer`
**Push. Stop. Plan clos.**

## 5. Checklist de reprise (chaque session)

1. `git fetch` + `git log -1` origin `pari-forge-perturabo-xs4c`.
2. Lire CONTINUATION.md derniere entree + pack suivant **non coche** ici.
3. Ne pas rebase. Ne pas committer secrets ni OUT e2e.
4. Coder le pack. Tests du pack + e2e concernes.
5. Docs (section 3) dans le meme commit.
6. Push. Cocher le pack. S arreter.

## 6. Interdits (rappel)

- Transcender Portes A → Score B → EV_FLOOR 0.03 → veto TYRANT.
- Baisser EV_FLOOR pour remplir un ticket.
- Deux jambes du meme match sur un ticket.
- Oracle producteur de chiffre.
- Devig / scorer dans Poisson (sauf S13 facteurs table A, capes, journalises).
- 2e lambda via API (S15 = flags only).
- Rewrite git history.
- Committer une cle.
- Enchainer 4+ unites dans une session.

## 7. Etat des packs

- [x] S0 Ph0 Warsmith (GO 2026-11-06 ; rotation cles reste Warsmith-side)
- [x] S1 v4.0 parseur + E1/D2
- [x] S2 doctor + bundle
- [x] S3 one-writer + journal
- [x] S4 marches + devig
- [x] S5 compose + priorite
- [x] S6 fit + baseline
- [x] S7 empirique + walk-forward
- [x] S8 sensibilite + CLV T-0
- [x] S9 CLV metrique + F06 diag
- [x] S10 Kelly
- [x] S11 /marchés + tickets
- [x] S12 scorer
- [ ] S13 lambda effectifs
- [ ] S14 pieges + /data
- [ ] S15 flags injuries
- [ ] S16 Oracle + poids

Reprise : premier pack non coche, apres S0 GO.
