# 📖 GUIDE UTILISATION — MONDE PARI

Tout ce qu'il faut savoir pour opérer le monde, pas à pas. (Warsmith = toi.)

---

## 0. LE CYCLE DE CAMPAGNE v2 (Telegram → GitHub Actions → Pages)

Le flux de campagne officiel. Tout est opérable **depuis Telegram** (PC et tel),
avec une commande à chaque étape et les deux previews servies sur GitHub Pages.

**Ecoute Telegram (Phase 8) LIVE depuis 2026-10-30** : Cloudflare Worker
(`ORCHESTRATOR/LISTEN`, URL `https://pari-listen.pari-listen.workers.dev`) recoit
le webhook, filtre `chat_id`, ACK, puis `workflow_dispatch` `pari_listen.yml`
sur **`gyutedy/PERTURABO`** (branche `pari-forge-perturabo-xs4c`). GitHub execute
`workflow.py` et `notifier.py` repond via `env_pari` (secrets GitHub vides
ignores). Runbook : `ORCHESTRATOR/LISTEN/README.md`. `/start` Telegram a deja
ouvert `PARI-20261030`.

```
Telegram /start → Worker → pari_listen.yml → workflow.py → notifier
/start → /capture (tableau markdown DANS le meme message)
     → /budget 6000 → /combos 3:3:2:2
     → /valider-1 → PREVIEW 1 (données brutes) → relecture
     → /valider-2 → PREVIEW 2 (ticket final) → /data → tickets posés → F06
```

### Les commandes de campagne

| Commande | Ce que ça fait |
|---|---|
| `/start` | Ouvre la campagne du jour (reset propre) |
| `/capture` | Telegram v1 : colle le tableau markdown Winner Bet **dans le meme message**. CLI : `/capture <fichier>` (txt/md/png/pdf/docx). JSON reconstitue = Porte 1 |
| `/budget 6000 / 3000` | Budget du jour (FC) + mise du ticket sûr (optionnel) |
| `/combos 3` ou `/combos 3:3:2:2` | Nb de tickets (+ nb de matchs par ticket) |
| `/valider-1` | Valide le JSON → carte → injection stats (si ligue couverte) → siège → **Top 3 + PREVIEW 1** |
| `/data` | Les rangs du **Top 3 + score commun** en message spécial (hors ticket final) |
| `/valider-2` | Compose les tickets + backroll → **PREVIEW 2 (ticket final)** |
| `/status`, `/roi`, `/stop` | État de campagne, ROI F06, clôture |

Équivalent terminal (si tu bosses depuis un PC sans bot) :
```bash
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode workflow --cmd "/start /capture c.txt /budget 6000 /combos 3"
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode tickets --combos 3 --jambes 3:2:2 --budget-fc 6000 --surticket-fc 3000
```

### Ce que le monde fait exactement à chaque étape

1. **/capture** : extracteur multi-format (txt/md direct, PDF/DOCX texte, image OCR si
   tesseract est installe) puis parseur (tableau markdown Winner Bet ou lignes OCR).
   Capte ligue/coupe, date, heure, matchs, tous les marches affiches (1X2, O/U toutes
   lignes, MT1/MTE/MT2, BTTS). Cellules "Verrouille" ignorees. Champs manquants → warning,
   jamais devine (Zero Data, Zero Calc). JSON reconstitue = a relire avant tout calcul.
2. **/valider-1** : carte validée → tentative d'injection des **stats historiques**
   (football-data.co.uk + ClubElo, sans clé) ; si la ligue n'est pas couverte → avertissement
   explicite, le siège sortira NO BET tant que les mj/marques/encaisses manquent.
   Puis F02 (Poisson/Dixon-Coles) → F03 (de-marging, EV, Kelly) → filtre qualitatif
   (si notes) → **Top 3 marchés + score commun 01-10** → PREVIEW 1 (SHARED/OUT/preview1.html).
3. **/valider-2** : tickets depuis la classe de fiabilité (ticket sûr = scores les plus
   hauts, reste réparti ; match FAIBLE et NO BET/qualitatif exclus) + **backroll**
   (budget jour, sur-ticket, division si > 4 jambes) → PREVIEW 2 (SHARED/OUT/preview2.html).
4. **Placement** : tu poses les tickets chez Winner Bet, puis loggens F06
   (`tracker.py add --file ticket.json`) — TOUS les tickets, gagnants comme perdants.

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
chiffres. Sans clé : le monde tourne à 100 %.

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

### 🗓️ Le calendrier automatique (clés optionnelles)

```bash
# API-Football (100 req/jour gratis — API_FOOTBALL_KEY en Secret) :
python F00_RADAR/CODEBASE/capteurs.py fixtures-list --source api-football \
    --league-id 39 --date 2026-10-25 --out ARCHIVUM/fixtures/calendrier.json

# ou football-data.org (12 compétitions gratis — FOOTBALL_DATA_ORG_KEY) :
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
`/capture` = tableau markdown dans le **meme** message (plafond 4096). png/pdf plus tard.

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

Sources pour remplir la carte (whitelist) : FBref, FootyStats, SoccerSTATS,
Flashscore, Transfermarkt, ClubElo. **Zero Data, Zero Calc** : si tu ne
trouves pas, ne devine pas — marque `"cotes": null` et attends.

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
   - `API_FOOTBALL_KEY` = (option) ta clé API-Football (100 req/jour)
   - `ORACLE_API_KEY` = (option) ta clé LLM (TYRANT/HERALD)
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
