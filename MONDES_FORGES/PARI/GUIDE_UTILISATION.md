# 📖 GUIDE UTILISATION — MONDE PARI

Tout ce qu'il faut savoir pour opérer le monde, pas à pas. (Warsmith = toi.)

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

### 📮 Telegram — le canal principal privé

```bash
# 1. @BotFather → /newbot → copie le TOKEN
# 2. Envoie un message à ton bot puis ouvre:
#    https://api.telegram.org/bot<TOKEN>/getUpdates → copie chat.id
# 3. Mets les 2 clés : Settings → Keys (workspace) ET GitHub Secrets
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode telegram-test
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode notify   # pousse le pari pack
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
3. **Capture d'écran** (plus tard, clé Oracle vision) : via le bot Telegram, tu envoies
   la photo → OCR → JSON reconstitué à valider → puis cotes acceptées.

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

❌ Pari auto · ❌ martingale · ❌ mise ≥ 5% · ❌ données inventées ·
❌ pronostics YouTube dans le moteur · ❌ ledger filtré (gagnants seulement).

*Fer au-dedans, Fer au-dehors.*
