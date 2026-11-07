# 📖 GUIDE UTILISATION — MONDE PARI

Tout ce qu'il faut savoir pour opérer le monde, pas à pas. (Warsmith = toi.)

---

## 0. LE CYCLE DE CAMPAGNE v2 (Telegram → GitHub Actions → Pages)

Le flux de campagne officiel. Tout est opérable **depuis Telegram** (PC et tel),
avec une commande à chaque étape et les deux previews servies sur GitHub Pages.

**Ecoute Telegram (Phase 8) LIVE depuis 2026-10-30** : Cloudflare Worker
(`ORCHESTRATOR/LISTEN`, URL `https://pari-listen.pari-listen.workers.dev`) recoit
le webhook, filtre `chat_id`, ACK, puis `workflow_dispatch` `pari_listen.yml`
sur **`gyutedy/PERTURABO`** (branche principale `pari-forge-perturabo-xs4c`). GitHub execute
`workflow.py` et `notifier.py` repond via `env_pari` (secrets GitHub vides
ignores). Runbook : `ORCHESTRATOR/LISTEN/README.md`. `/start` Telegram a deja
ouvert `PARI-20261030`.

```
Telegram /start → Worker → pari_listen.yml → workflow.py → notifier
/start → /budget bankroll 50000 (une fois, pot global — PAS /bankroll tant que Worker stale)
     → /capture (tableau markdown DANS le meme message)
     → /budget 3000 800 (plafond lot + mise FORCEE ticket sur)  ← retaper avant CHAQUE lot
      → /valider-1 → PREVIEW 1 + table couverture (jambes jouables) → /data
       → coller le hint `/marches …` affiche (pas un stub). Table effectifs dans /capture sinon X-tank bloque.
       → /combos 3:3:2:2
      → /valider-2 → PREVIEW 2 + pending L-XXX → /approve L-XXX seulement si /data n a pas de X sous tank
      Mode A (meme capture, lot suivant) : /budget retapé → /valider-2 → /approve (autre token, autres marches)
Mode B (nouveau pari) : /stop → /start → /capture → /budget → /combos → /valider-1 → /valider-2
```

### Les commandes de campagne

| Commande | Ce que ça fait |
|---|---|
| `/start` | Ouvre la campagne du jour (reset propre, **garde la bankroll**) |
| `/capture` | Telegram : colle le tableau markdown **dans le meme message**, **ou** envoie une **photo** avec caption `/capture` (OCR tesseract). CLI : `/capture <fichier>` (txt/md/png/pdf/docx). Inbox = fichier `capture_telegram.*` le **plus recent** (un markdown neuf ecrase une vieille photo). Dates `JJ/MM/AA` lues par rang. OCR vide = Zero Data. Moins/Plus : ligne lue (`Ligne (Total)` ou `Moins de X`) → `uX`/`oX` ; **pas de 2.5 invente** si la ligne manque (`holes` + cotes gardees). **S13** : 2e table effectifs (meme message) optionnelle — vide = x1.00 + holes. |
| `/budget bankroll 50000` | Pot global FC. Une fois. Persiste `/start` et `/stop`. **Telegram live : ne pas taper `/bankroll`** (Worker stale = commande inconnue). Alias CLI : `/bankroll 50000`. |
| `/budget 3000 800` | **Obligatoire 2 nombres** : 3000 FC plafond du jour + **800 FC FORCES sur le ticket sur**. Reste (2200) divise. Alias `/budget 3000 / 800`. |
| `/surticket 800` | Corrige la mise du ticket sur sans retaper le jour. |
| `/combos 3` ou `/combos 3:3:2:2` | Nb de tickets + jambes (1 a n+10 matchs distincts). Meme match interdit sur un ticket. |
| `/marches 1X2` | Elit les marches (canon `/marches`, alias `/marchés`). Table couverture = jambes **jouables** (tank-X hors n). Apres `/valider-1` le hint est `/marches` calque sur cette table — pas le stub `O/U2.5,MT2`. `mono` = ticket mono-marche. 0 match → 0 ticket. THIN hors combo. `cote_plate` = flag, jambe MT reste. |
| `/valider-1` | Valide le JSON → carte → injection stats (E0/SP1/I1/D1/F1/E1/D2) → siège **complet** (AUTO_GATES) → **Top 3 ecrase** (plus de demo) + table couverture |
| `/valider-2` | Compose les tickets + metro Oracle + fees/slippage dans le seuil + pending `L-XXX`. **Refuse** si NO BET / Zero Data, `/budget` absent, `/budget` non retapé (Mode A), pool HAUTE vide, 0 match elu. Live : `/approve L-XXX` fige T0. Actions `PARI_AUTO_GATES=1` fige tout de suite. |
| `/approve L-XXX` | Fige le lot pending (snapshot T0). Token mismatch = refuse. |
| `/data` | Prefixe `notes: N` puis **table compacte** (HAUTE puis FAIBLE). Colonnes Q/SC/ELO/xG/REPOS/H2H/TROU/OUT/TOP/PIEGES. `—` = trou, jamais 0.0 invente. S14 : flags pieges (cote_plate, marge_anomalique, cote_figee_sur_news, marche_vitrine). |
| `/data N` | Fiche exhaustive du rang N (1-based, ordre compact). H2H scores+MT, forme 10, TROU timing, notes OUT/DOUTE/IGNORE, **SCORER 6 criteres** (edge/bande/info/data/marge/confirm) + lecture cotes capture/T-2h/T-0 + PIEGES. Hors liste = erreur courte. |
| `/data ledger` | Token + lots du jour (inchange). |
| `/data diag` | F06 diagnostic CLV / Platt / Beta-Binomial / P(EV>0). **n<50 = LOCKED**, jamais verdict/mise. Alias `/data f06` `/data clv`. |
| `/radar [N]` | Scan carte courante. Matchs sans stats = trous declares, pas de crash. Defaut N=20. v3.8 : flag `incoherence_modele_empirique` si \|P(O2.5) - taux saison\| >= 0.20 (info, pas NO BET). Saison absente = trou. S14 : ligne PIEGES + SCORER si predictions presentes. |
| `/pack [N]` | Assemble le pari pack TOP N (defaut 10) depuis predictions + analysis. Refuse si `/valider-1` pas fait. |
| `/match ID` | Fiche siege d'un match (`M1` ou rang 1-based). Carte puis radar puis analysis. S14 : SCORER 6 criteres + PIEGES. Inconnu = refuse, pas crash. |
| `/status` | État campagne + ligne doctor (GO/CHECK/FAIL, gate n). `/status ledger` = lots. `/status doctor` = evidence complete (cles **noms seulement**, contrats, whitelist, cache, CLV). |

Exemple compact (`/data`) :

```
notes: 0
#  MATCH            Q   SC  ELO   xG      REPOS  H2H    TROU      OUT TOP PIEGES
1  Milan-Inter      H 10.0  +12  1.8/1.4  6/4    4-3-5  —         0   1 @3.45 —
11 Delfin-Cuenca    F  2.9   —    —/—     —/—    —      elo,xg    0   NO BET —
```

Exemple fiche (`/data 1`) : identite + Q + score + TOP, Elo/xG/repos, H2H scores+MT, forme D 10, forme E 10, TROU timing, notes, SCORER 6 criteres, COTES capture/T-2h/T-0, PIEGES.
| `/roi` | ROI cumulé. `/roi settle L-XXX` = scores football-data (G/P/EN_ATTENTE, jamais invente). v3.9 : stocke `book_odds_close` (T-0 kickoff). v3.10 : `clv = cote_prise / cote_cloture - 1` (ratio). Cloture absente = hole, exclu CLV, jamais 0. Journal F06 : procedure (freeze, immutable) + outcome (mise, cote, G/P, pnl, CLV si connu — absent = hole, jamais 0). |
| `/stop` | Ferme la campagne. Bankroll survit. Lots F06 intacts. `consumed_legs` reset. |

Équivalent terminal (si tu bosses depuis un PC sans bot) :
```bash
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode workflow --cmd "/start /capture c.txt /bankroll 50000 /budget 3000 800 /combos 3"
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode tickets --combos 3 --jambes 3:2:2 --budget-fc 3000 --surticket-fc 800
```

### Ce que le monde fait exactement à chaque étape

1. **/capture** : extracteur multi-format (txt/md direct, PDF/DOCX texte, image OCR si
    tesseract est installe — **P4** : `tesseract-ocr` + `tesseract-ocr-fra` dans
    `pari_listen.yml` et `pari_daily.yml`) puis parseur (tableau markdown Winner Bet ou lignes OCR).
   Telegram qui casse `<br>` en saut de ligne est reassembled (v2.2.1). Capte ligue/coupe,
   date, heure, matchs, tous les marches affiches (1X2, O/U toutes lignes, MT1/MTE/MT2,
   BTTS). Cellules "Verrouille" ignorees. Champs manquants → warning, jamais devine
    (Zero Data, Zero Calc). JSON reconstitue = a relire avant tout calcul.
     **F00** enchaine : Elo ClubElo + xG Understat + repos/H2H football-data.org + vote
     notes (Sofa / Sportradar / ESPN) + **S15 injuries API** (flags TYRANT, jamais un
     2e lambda). Message : `notes: N` (0 = trou, jamais invente). OUT = 3 voix.
     Flags S15 : `buteur_manquant` / `defenseur_manquant` / `double_motivation` /
     `satisfait_nul` (veto ou seuil, pas un P). `PARI_SKIP_F00=1` coupe l enrichissement (CI).
     `PARI_SKIP_INJURIES=1` coupe S15 seulement.
    `FOOTBALL_DATA_ORG_KEY` (env_pari) = repos F00, **pas Oracle, pas modele premium**.
    Sportradar absent = DOUTE max. ESPN public (sans cle, latence heures possible).
2. **/valider-1** : carte validée → injection **stats** (football-data.co.uk, ligues
    E0/SP1/I1/D1/F1/**E1 Championship**/**D2 Bundesliga 2**). Alias ligues v2.2.7 :
    `LaLiga` (sans espace) = SP1. v4.0 : Championship = E1, Bundesliga 2 = D2
    (CSV de **leur** ligue, jamais E0/D1). `LaLiga 2` / Serie B / Ligue 2 restent
    rejetes. Alias clubs (`Ath Madrid`, `M'Gladbach`, `Nott'm Forest`…). Merge
    multi-ligues (`stats_inject_E0.json` + `SP1` + `E1`…) : un club hors CSV =
    **skip CE match**, pas NO BET sur toute la slate. Le message compte
    `GO / FAIBLE-qual / skip-stats`. Puis siège complet (F02→F03→top3) même sur
    GitHub Actions. Parseur Moins/Plus : sans ligne totale, cotes gardees +
    `holes: ["ligne_totale_Moins_Plus"]` — jamais de 2.5 par defaut.
      Ligue hors whitelist (IFL, Iran, Israël…) → TOP3 **NO BET** pour CES matchs, jamais
      la demo Cyclops/Lions. `/valider-2` est refuse seulement si 0 GO. v2.2.4 : le siege
      n'utilise `predictions_filtered.json` que si des notes qualitatives ont tourne
      **cette** campagne (plus de Top 3 Cyclops stale). e2e_final (v2.2.3) aligne la
      carte stats dans `matches.json` apres le siege de test ; la garde prod reste.
    Puis F02 (Poisson/Dixon-Coles, **memes matrices** : O/U 0.5/1.5/3.5/4.5, DC 1X/X2/12,
    team totals, score exact top N si cote. v3.6 : rho / bonus domicile fit sur CSV
    saison si `league_params.json` present, sinon 1.10 / RHO_DC. Baseline = saison
    EMA 45j, fallback carte si CSV absent. Equations inchangees.) → F03 (EV = P_modele * cote - 1 inchange ;
    `edge_net_devig` diagnostic seulement ; cote unique = hole, pas de fair ;
    **scorer S12** : portes A1-A4 hors score (groupe / praticable cote>=1.10 / historique /
    marge>20% = refus vitrine). Score B1-B6 0-1, seuil 0.50-0.60. B3 = asymetrie info
    (T-2h / T-0), pas severite blessure. Trou = score reduit + holes. Ineligible → NO_BET.
    Jamais un p. **S14 pieges** : `cote_plate` (MT identiques >=5, cotes gardees),
    `marge_anomalique` (overround >10%, B5), `cote_figee_sur_news` (B3, |move|<1% + notes OUT),
    `marche_vitrine` (marge >20% → A4, marche retire). 3e lecture capture → T-2h → T-0.
    Affichage `/data` `/radar` `/match`.) → filtre qualitatif
     (si notes **ou** flags S13) → **Top 3 marchés + score commun 01-10** → PREVIEW 1 (SHARED/OUT/preview1.html)
    + **research bundle** SHA-256 (`ARCHIVUM/research/B-XXX`, gaps declares). `/status doctor`
    pour l evidence GO/CHECK/FAIL (cles = noms, jamais les valeurs).
3. **/marches** (v4.1 + hint du jour) : table couverture (n matchs VALUE F03 **jouables**,
   meilleur EV, marge). X sous tank (`p_fav>=0.55`, vestiaire vide) hors n.
   Le hint post `/valider-1` recopie cette table (`/marches 1X2` si seul 1X2 couvert).
   Alias `/marchés`. `cote_plate` = flag, jambe MT **reste**. `mono` = toutes les jambes d un ticket
   = un seul marche. 0 match → 0 ticket, message honnete. Tickets = VALUE seulement
   (THIN hors combo). EV_FLOOR 0.03 reste le plancher numerique (baisser = refuse).
   Combo plancher 0.05. Jamais jambe de remplissage. Meme match
   = meme navire = interdit. 1 a n+10 jambes (`/combos 3:3:2:2` reste valide).
   Log append-only ; `/status` alerte si un marche >60% des elections.
3b. **/valider-2** (v4.6) : tickets depuis la classe de fiabilité (ticket sûr = scores
    les plus hauts, reste réparti ; FAIBLE / NO BET exclus) + **anti-cannibal**
    (exclusion `(match_id, marche, selection)` deja sortis sur cette capture ; prochain
    marche Top 3 libre ; plancher qualite fixe) + **backroll** (`/budget` retape avant
    chaque lot Mode A) + **metro Oracle** (risques/trous/ranking, zero chiffre) +
    **fees+slippage** dans le seuil (jamais sous 0.03) → PREVIEW 2 + pending `L-XXX`.
    `/approve L-XXX` fige snapshot T0 dans `ARCHIVUM/learnings/lots.json`.
    Refuse si le sur-ticket n est pas pose, si `/budget` n a pas ete retape, si 0 jambe HAUTE,
    si 0 match elu, si token approve mismatch. `/combos 4` n est pas un quota : mieux 2 tickets HAUTE que 4 reliquats.
   v3.5 : chaque ticket porte `ev_compose_net` = produit `(1+edge_net)-1` (precision
   machine, `1.03*1.05-1 = 8.15%`). `jambe_edge_net_negatif` = info, **pas rejet**.
    Priorite marches : palier suivant si >= 30 tickets mesures (G/P). corners/cards
    fermes sans data → holes, jamais ouverts. Edge = modele calibre + news plus rapide
    que le book local ; **pas d arbitrage**. Tri EV brute inchange.
    v3.10.9b : Kelly **1/8** defaut. **1/4** seulement si ECE walk-forward <= 0.03
    **et** P(EV>0) >= 0.55 **et** n>=50. P/ECE absents = 1/8 + holes. n<50 jamais 1/4.
    Combo = un tirage MC conjoint toutes jambes. Fraction journalisee
    (`kelly_fraction`). Le budget operateur (`mise_fc`) n est **pas** Kelly.
4. **Placement** : tu poses les tickets chez Winner Bet. F06 a deja fige le lot
   (token) + **journal.procedure** (checks, trous, seuils, Kelly — immutable).
   Apres les matchs : `/roi settle L-XXX` pose **journal.outcome** (mise, cote,
    G/P, pnl, CLV si connu) et `book_odds_close` (T-0). Cloture absente = hole,
    exclu CLV, jamais 0. T-2h n est PAS la cloture. v3.10 : `clv = cote_prise /
    cote_cloture - 1`. Combo = produit des closes. Agregats median / % >0 /
    mean_w (cibles 55% / +0.5 pt). n<50 tickets reels = `/data diag` seulement,
    jamais verdict/mise. Doctor n<30 = variance, pas un verdict. F06 n'apprend pas.

### Les infos non binaires (blessures, fatigue, enjeux…)

Fichiers `ARCHIVUM/fixtures/notes_qualitatives.json` (contrat schema_notes_qualitatives.json).
Effets **bornés** — jamais dans les maths : exclusion de marchés, seuil EV relevé,
NO BET recommandé. Détail dans la section TYRANT ci-dessous (contrat + table).

### Les deux previews

| | Fichier | Contenu |
|---|---|---|
| PREVIEW 1 | `SHARED/OUT/preview1.html` | données BRUTES : cotes reconstituées, probas froides, EV, Top 3 + score + bucket, notes non binaires, qualité data — menu déroulant par match |
| PREVIEW 2 | `SHARED/OUT/preview2.html` | le TICKET FINAL : cartes de tickets, sur-ticket en or, budget alloué/reste, cotes et probas — hommage graphique PERTURABO |

Les deux sont responsive (PC/téléphone). Sur GitHub Pages, le workflow `pari-daily`
push `SHARED/OUT` dans le dossier Pages — les liens arrivent dans Telegram.

### Oracle (clé premium, optionnel)

`ORACLE_API_KEY` (Secret GitHub, OpenAI-compatible) est utilisé par TYRANT/HERALD
**hors du job du monde forger**, pour le qualitatif et la rédaction — jamais pour les
chiffres. S16 : **metro** avant `/valider-2` (risques, trous, ranking). Reponse avec
un digit = jete (`oracle_digit`). Sans clé : skip, le monde tourne à 100 %.

---

## 1. Le premier lancé en 5 minutes (mode DEMO)

```bash
cd MONDES_FORGES/PARI
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode demo
```

Le mode démo construit une **ligue simulée** (18 matchs, stats + cotes), lance
radar → siège → pack → dashboard, et valide les gates automatiquement
(`PARI_AUTO_GATES=1` interne).

Ouvre ensuite :
- `SHARED/OUT/RADAR.md` — le classement de ligue
- `SHARED/OUT/dashboard.html` — le dashboard (ouvre-le dans un navigateur, sur tel aussi)
- `F05_PACKAGER/OUT/pari_pack.json` — le pack final
- `F04_HERALD/OUT/reports/` — les fiches de siège

---

## 2. Scanner une VRAIE ligue (mode radar)

### ⚡ La voie CAPTEURS (recommandée — 90% auto)

**Étape 1 — la bibliothèque de stats** (football-data.co.uk, **sans aucune clé**) :

```bash
cd MONDES_FORGES/PARI
# E0 = Premier League · SP1 = La Liga · I1 = Serie A · D1 = Bundesliga · F1 = Ligue 1
python F00_RADAR/CODEBASE/capteurs.py build-stats --league E0 --season 2627 \
    --include-seasons 2526 --last 12 --out ARCHIVUM/teams/E0_2627.json
```

`--include-seasons` fusionne la saison précédente — **indispensable en début de
saison** (< 6 matchs/équipe sinon NO BET d'office). Fenêtre glissante : les
12 derniers matchs **par équipe**, split Domicile/Extérieur + split mi-temps.

**Étape 2 — les Elo** (ClubElo, sans clé — fonctionne mieux depuis GitHub Actions) :

```bash
python F00_RADAR/CODEBASE/capteurs.py build-elo --date 2026-10-25 \
    --out ARCHIVUM/teams/elo_2026-10-25.json
```

**Étape 3 — ta carte de matchs** (tu ne colles QUE les paires de noms) :

```json
{"ligue": "Premier League", "horizon": "journée du 25-10",
 "matchs": [
   {"id": "M1", "dom": "Arsenal", "ext": "Man City", "cotes": null},
   {"id": "M2", "dom": "Liverpool", "ext": "Chelsea", "cotes": null}
 ]}
```

**Étape 4 — l'injection** (stats + Elo auto dans la carte) :

```bash
python F00_RADAR/CODEBASE/capteurs.py inject --stats ARCHIVUM/teams/E0_2627.json \
    --carte ARCHIVUM/fixtures/matches.json --elo ARCHIVUM/teams/elo_2026-10-25.json
```

Les équipes manquantes sont signalées « Zero Data, Zero Calc » — corrige le nom
ou remplit à la main, jamais d'invention.

**Étape 5 — le radar** : `python ORCHESTRATOR/CODEBASE/orchestrator.py --mode radar --fixtures ARCHIVUM/fixtures/matches.json`

**Étape 6 — walk-forward** (cut-off explicite, jamais in-sample) :

```bash
python F00_RADAR/CODEBASE/capteurs.py walk-forward --cutoff 2026-01-01 \
    --csv-dir ARCHIVUM/cache/f00 --out ARCHIVUM/learnings/backtest_report.json
```

Odds absentes = trou, jamais 0. Rapport gitignore. Fit ligue (S6) :

```bash
python F00_RADAR/CODEBASE/capteurs.py fit-league \
    --csv-dir ARCHIVUM/cache/f00 --out ARCHIVUM/learnings/league_params.json
```

### 🗓️ Le calendrier automatique (clés optionnelles)

```bash
# Sportradar (trial v4 — SPORTRADAR_API_KEY dans env_pari).
# missing_players est PAR SAISON : le connecteur resout la saison courante
# des 6 championnats (E0/SP1/I1/D1/F1/N1), cache 1 hit/jour/competition.
# Voix 2 des notes : seul, il ne peut produire que DOUTE (OUT = 3 voix).

# SofaScore RapidAPI (SOFASCORE_RAPIDAPI_KEY = meme X-RapidAPI-Key).
# Host sofascore-sport-api.p.rapidapi.com. missingPlayers via lineups
# du prochain event. Voix 1 notes. Pas Oracle.

# ESPN public (sans cle) — voix 3 notes. Fetch PAR LIGUE injuries.
# Mapping E0/SP1/I1/D1/F1/N1/T1/J1. Matching nom + difflib 0.9.
# Cache 1 hit/ligue/jour. Timeout / 3 fails = voix morte. Pas Oracle.
# WhoScored RapidAPI optionnel (injuries souvent trou).

# Cloudflare Worker deploy (CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID
# dans env_pari, PAS GitHub Secrets). Absents = skip, Worker live stale.

# The Odds API T-2h + T-0 (ODDS_API_KEY dans env_pari, PAS GitHub Secrets).
# Absente = skip. Fenetre 3h avant kickoff (T-2h). T-0 = grace 15 min autour
# du coup d envoi. Recast EV (p_modele F03). ESTOMPE si VALUE devient EV<=0.
# Jamais Poisson, jamais scrape Winner. Kill switch PARI_SKIP_ODDS=1.
# T-0 n ecrase pas latest.json.
# python F00_RADAR/CODEBASE/capteurs.py odds-watch [--force] [--notify]
# python F00_RADAR/CODEBASE/capteurs.py odds-watch --close [--notify]

# API-Football (100 req/jour Free — API_FOOTBALL_KEY dans env_pari).
# Pas Oracle / pas modele premium. Header x-apisports-key. Ping /status.
# S15 injuries : meme cle, flags TYRANT (jamais un 2e lambda). Holes si KO.
# Cache 1 hit/ligue/jour. Kill switch PARI_SKIP_INJURIES=1.
python F00_RADAR/CODEBASE/capteurs.py fixtures-list --source api-football \
    --league-id 39 --date 2026-10-25 --out ARCHIVUM/fixtures/calendrier.json

# football-data.org (F00 rest_days, 12 comps gratis — FOOTBALL_DATA_ORG_KEY dans env_pari).
# Pas Oracle / pas modele premium. Header X-Auth-Token. Quota : lire X-Requests-Available-Minute.
python F00_RADAR/CODEBASE/capteurs.py fixtures-list --source football-data-org \
    --competition PL --date-from 2026-10-24 --date-to 2026-10-27 \
    --out ARCHIVUM/fixtures/calendrier.json
```

Le calendrier donne les paires + ids + horaires ; fusionne-la avec ta carte
puis inject. Sans clé : les paires se collent à la main (2 minutes).

### Telegram — le canal principal privé (écoute + envoi)

Sans Worker, le bot **envoie** (notifier) mais **n'écoute pas**. `/start` dans
le chat n'atteint pas GitHub.

```bash
# 1. @BotFather → /newbot → TOKEN
# 2. Ecris au bot → getUpdates → chat.id
# 3. Secrets GitHub : TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
# 4. Deploy Worker (une fois) — detail : ORCHESTRATOR/LISTEN/README.md
cd MONDES_FORGES/PARI/ORCHESTRATOR/LISTEN
npx wrangler deploy
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put GITHUB_DISPATCH_TOKEN
# 5. Brancher le webhook
curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://pari-listen.<compte>.workers.dev" \
  -d "secret_token=${SECRET}"
```

Puis dans Telegram : `/start`. ACK Worker (~1 s) puis reponse campagne (~1 min).
`/capture` = tableau markdown dans le **meme** message (plafond 4096) **ou** photo
avec caption `/capture`. Si Telegram casse les `<br>` en retours a la ligne, le
parseur recoud les rangs. Dates `JJ/MM/AA` (ex. `21/11/26 16:00`) sont lues **par
rang** — plusieurs jours dans un seul tableau = OK. La reponse doit dire
`(markdown_table)` et pas `(image)` : `(image)` = leftover photo d'un essai
precedent, recolle le markdown.

**S13 — 2e table effectifs** (optionnelle, meme `/capture`). Deux rangs par match
(`dom` / `ext`). Vide = lambdas x1.00 + holes. `rotation_lourde` (>=4) = flag
TYRANT "O/BTTS deconseilles", **pas** de facteur lambda. Derby / meteo /
retour_100 = veto `marches_exclus` seulement. Cap cumule ±20%, journalise.
Jamais un 2e lambda via API. S15 (`buteur_manquant` / `defenseur_manquant` /
`double_motivation` / `satisfait_nul`) = flags TYRANT (veto / seuil) : ils ne
remplissent **pas** cette table. Si la table A a deja prix att/def, le flag
API reste un label (anti-double-compte).

```
| Match | Cote | att | def | gk | milieu | repos | rotation | derby | meteo | retour |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Everton FC vs Coventry City | dom | 1 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| Everton FC vs Coventry City | ext | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
```

Colonnes : `att` = attaquants titulaires absents (x0.90 / unite, max 2) ;
`def` = defenseurs cles absents (x1.06 sur lambda adverse) ; `gk` = gardien 1
absent (x1.05 adverse) ; `milieu` = createur absent (x0.96) ; `repos` =
`jours_repos` (stocke, fatigue deja F00) ; `rotation` >= 4 = flag.
Suffixes `att_dom` / `att_ext` acceptes sur un seul rang.

Test envoi seul (sans webhook) :

```bash
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode telegram-test
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode notify
```

Sans clés, la commande affiche les instructions et ne casse jamais rien.

### Étape manuelle — La carte des matchs (sans capteurs)
Crée `ARCHIVUM/fixtures/matches.json` :

```json
{
  "ligue": "Premier League",
  "horizon": "journée du 25-10",
  "matchs": [
    {
      "id": "M1",
      "dom": "Arsenal", "ext": "Chelsea",
      "date": "2026-10-25",
      "stats": {
        "dom": {"mj": 8, "marques": 18, "encaisses": 6},
        "ext": {"mj": 8, "marques": 12, "encaisses": 11}
      },
      "cotes": null,
      "notes": "derby, penalty incertain"
    }
  ]
}
```

Champs **requis** par équipe : `mj`, `marques`, `encaisses` (saisons/10 derniers matchs).
Optionnels (fortement conseillés pour le marché mi-temps) : `marques_mt1/mt2`,
`encaisses_mt1/mt2`. Absents → part ligue par défaut + flag `estimate`.

Sources pour remplir la carte (whitelist) : football-data.co.uk, ClubElo,
Understat xG (metadonnee, jamais Poisson), football-data.org (repos/H2H).
FBref = mort. **Zero Data, Zero Calc** : si tu ne trouves pas, ne devine pas
— marque `"cotes": null` et attends.

### Puis — Lancer
```bash
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode radar
```
→ `SHARED/OUT/RADAR.md` : les matchs classés, TOP 20 en 🔥.

### Étape 3 — Valider la Porte 1 (Le Warsmith a le dernier mot)
```bash
python IW_CUSTOS.py --mode gate --gate 1 --decision yes --notes "carte vérifiée"
```

---

## 3. Analyser un match avec les cotes Winner Bet (mode siège)

### Les cotes d'où ?
Trois façons — c'est toi qui choisis :
1. **TXT brut** (aucune clé) : écris `cotes.txt` →
   `Arsenal vs Chelsea : 1.85 / 3.60 / 4.20 | O2.5 1.70 | MT2 2.10`
   puis : `python F01_SENTINEL/CODEBASE/sentinel.py --input <carte> --cotes-txt cotes.txt`
2. **JSON direct** : colle les cotes dans la carte (`m["cotes"] = {"1":…}`) — idéal quand
   tu as tout sous la main.
3. **Capture screenshot → OCR → texte** (flux officiel, documenté à part via `TPL_capture_ocr.md`) :
   tu capturas une page bookmaker qui affiche ligue, compétition, équipes, cotes, heure → OCR produit le texte → parseur reconstitut le JSON → tu valides avant calcul.

> ⚠️ Règle de non-implication : la ligue d'une capture propre ton bookmaker est **affichée par le livreur**, pas devinée. Si la capture ne donne pas les champs minimums (équipes, ligue, cotes), on ne devine pas → on bloque en Porte 1 (Zero Data, Zero Calc).

⚠️ **Contrat** : peu importe le mode, le parseur affiche le JSON reconstitué
et tu valides AVANT le calcul d'EV. Une cote mal lue = une EV mensongère.

### Lancer l'analyse fine
```bash
# Tous les matchs de la carte qui ont des cotes:
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode siege
# Seulement 2 matchs:
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode siege --ids M1,M3
```

### Gérer les Portes
```bash
python IW_CUSTOS.py --mode gate --gate 2 --decision yes  # après analyses BREACHER
python IW_CUSTOS.py --mode gate --gate 3 --decision yes  # après verdicts FORGEWARD
python IW_CUSTOS.py --mode status                        # où en est le moyen
```
En mode siegette, ajouter `PARI_AUTO_GATES=1` verrouille les validations
(démo/test seulement — jamais en应用的).

Sources :
- `F04_HERALD/OUT/reports/M1_fiche.md` — la fiche lisible
- `F03_FORGEWARD/OUT/predictions.json` — EV et mises par marché
- `F05_PACKAGER/OUT/pari_pack.json` — le pack final (Top 10)

---

## 4. Log-ger un ticket après l'avoir posé chez Winner Bet (F06)

Crée `ticket.json` (exemple, 1 unité = 1% de bankroll) :

```json
{
  "id": "TICKET_0002",
  "date": "2026-10-25",
  "type": "siege",
  "nb_jambes": 1,
  "jambes": [{"match": "Arsenal vs Chelsea", "marche": "MT_PROLIFIQUE",
              "selection": "MT2", "cote": 2.10, "p_modele": 0.52}],
  "cote_totale": 2.10,
  "mise_units": 1.0,
  "score_predit": 0.52
}
```

```bash
python F06_TRACKER/CODEBASE/tracker.py add --file ticket.json
# après le match :
python F06_TRACKER/CODEBASE/tracker.py settle --id TICKET_0002 --resultat gagne
python F06_TRACKER/CODEBASE/tracker.py roi            # ROI cumulé
python F06_TRACKER/CODEBASE/tracker.py calibration    # prédit vs réalisé
```

**Règle d'or : le ledger prend TOUS les tickets.** Ne filtre pas — les pertes
sont la matière première de la calibration.

---

## 5. Brancher le bot Telegram (canal principal,的通知 push)

1. Sur Telegram : parle à **@BotFather** → `/newbot` → sauvegarde le **token**.
2. Envoie un message à ton bot, puis récupère ton `chat_id` via
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Sur GitHub (repo) : **Settings → Secrets and variables → Actions** → ajoute :
    - `TELEGRAM_BOT_TOKEN` = le token du bot
    - `TELEGRAM_CHAT_ID` = ton chat_id
    - `FOOTBALL_DATA_ORG_KEY` = (F00 rest_days) aussi dans `env_pari` — **pas Oracle**
    - `API_FOOTBALL_KEY` = (F00 calendrier) aussi dans `env_pari` — **pas Oracle**
    - `SPORTRADAR_API_KEY` = (F00 notes voix 2) aussi dans `env_pari` — **pas Oracle**
    - `ORACLE_API_KEY` = (option) LLM TYRANT/HERALD seulement. Sans elle le siege tourne 100 %.
4. Le workflow `.github/workflows/pari_daily.yml` tourne au cron quotidien :
   scan radar → pack → dashboard → **push Telegram** + commit des artefacts.
5. Test manuel : onglet **Actions** → run manual `pari_daily`.

Le sendMessage est en markdown : synthèse du radar + top picks + avertissement.

---

## 6. Charte Iron Warriors & Mode Discret

- **Charte** : fond acier `#14161b`, bleu Perturabo `#24507e`, or `#d4a017`,
  bandes hazard noir/jaune. Shoulder chart des titres : stencil (`Saira Stencil One`).
- **Mode Discret** : bouton 🔕 en haut du dashboard — police réduite (16px → 12px),
  titres camouflés (« classement » au lieu de « radar », etc.), sauvegardé dans
  `localStorage`. Personne à côté de ton tel ne voit quoi que ce soit.

---

## 7. Le méta-prompt (mode discussion partout)

`CONTRACTS/quant_analyste_prompt.md` — copie-collable dans n'importe quelle IA
pour faire l'analyse d'un match à la mano (3 compartiments, gardes-fous,
format de verdet). Là aussi : `PARI connect` — mode pipeline quand le repo tourne,
mode prompt quand tu discutes. N'utilises jamais les deux sans validation Warsmith.

---

## 8. Hérésies — mémo

❌ Pari auto · ❌ martingale · ❌ mise ≥ 3% · ❌ données inventées ·
❌ pronostics YouTube dans le moteur · ❌ ledger filtré (gagnants seulement).

*Fer au-dedans, Fer au-dehors.*
