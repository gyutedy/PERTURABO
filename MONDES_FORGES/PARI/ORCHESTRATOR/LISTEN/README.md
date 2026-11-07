# LISTEN — Relais Telegram (Cloudflare Worker)

Webhook Telegram → allowlist 1 operateur → ACK → `workflow_dispatch` `pari_listen.yml`.
Zero calcul ici. Le siege tourne sur GitHub Actions (`workflow.py`).

## 1. Deploy auto (v2.4 P2)

Push sur `MONDES_FORGES/PARI/ORCHESTRATOR/LISTEN/**` (branche `pari-forge-perturabo-xs4c`)
declenche `.github/workflows/worker_deploy.yml` → `wrangler deploy`.

Creds dans `MONDES_FORGES/PARI/env_pari` (pas GitHub Secrets) :

- `CLOUDFLARE_API_TOKEN` (permission Edit Cloudflare Workers)
- `CLOUDFLARE_ACCOUNT_ID`

Absents = skip, Worker live reste stale, job vert. Ne pas wrangler depuis un sandbox.
Ne pas toucher au webhook Telegram ici.

URL LIVE : `https://pari-listen.pari-listen.workers.dev`

Deploy manuel (une fois, hors sandbox) seulement si les secrets Actions ne sont pas poses :

```bash
cd MONDES_FORGES/PARI/ORCHESTRATOR/LISTEN
npx wrangler deploy
```

## 2. Secrets Worker (jamais dans git)

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put GITHUB_DISPATCH_TOKEN
```

`GITHUB_DISPATCH_TOKEN` = PAT du compte **gyutedy** (scopes `repo` + `workflow`).
`TELEGRAM_WEBHOOK_SECRET` = chaine aleatoire (header `X-Telegram-Bot-Api-Secret-Token`).
Repo cible : `gyutedy/PERTURABO` (`GH_OWNER` dans wrangler.toml).

## 3. Secrets GitHub (repo) — optionnels

`notifier.py` charge `MONDES_FORGES/PARI/env_pari` si `TELEGRAM_*` sont vides.
Ne PAS creer de secrets GitHub vides (ils masquaient `env_pari` avant le fix
2026-10-30). Secrets Worker restent obligatoires (TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID, TELEGRAM_WEBHOOK_SECRET, GITHUB_DISPATCH_TOKEN = PAT gyutedy).

## 4. Brancher le webhook Telegram

```bash
# TOKEN = TELEGRAM_BOT_TOKEN, SECRET = TELEGRAM_WEBHOOK_SECRET
curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://pari-listen.pari-listen.workers.dev" \
  -d "secret_token=${SECRET}"
```

Verif :

```bash
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

## 5. Test

Commandes v2.2.8 : Telegram live tape `/budget bankroll 50000` (pot global)
puis `/budget 3000 800` (plafond lot + mise FORCEE ticket sur).
`/bankroll` est dans git (`index.js` KNOWN). Worker Cloudflare stale jusqu'au
premier run `pari-worker-deploy` (secrets CF poses). `/budget 3000` seul est
refuse par `workflow.py`.
`/valider-1` injecte stats E0/SP1/I1/D1/F1/E1/D2 avec alias `LaLiga` + clubs
football-data ; un club hors CSV skip CE match (pas NO BET global).
`/valider-2` = tickets + metro Oracle + pending `L-XXX` ; `/approve L-XXX` fige T0
(retaper `/budget` avant chaque lot Mode A). `/marches O/U2.5,MT2` (alias `/marchés`, option `mono`)
relais parse.py + index.js. Aliases deja live : `/data ledger`,
`/status ledger`, `/status doctor`, `/roi settle L-XXX`. `/data` = table compacte, `/data N` = fiche, `/data diag` = F06 CLV/Platt (n<50 jamais mise)
(parse.py + index.js alignes ; deploy auto via `worker_deploy.yml`). Relais `/data N` dans git.
`FOOTBALL_DATA_ORG_KEY` (F00 rest_days), `API_FOOTBALL_KEY` (F00 calendrier) et
`SPORTRADAR_API_KEY` (F00 notes voix 2) vivent dans `env_pari`. `workflow.py` les charge a chaque commande.
**Pas Oracle, pas modele premium.** Secret GitHub vide n ecrase pas.

Dans Telegram, envoie `/start`. Tu dois voir :

1. ACK Worker : `Recu /start — siege en cours (~1 min).`
2. Reponse `workflow.py` : `Campagne PARI-YYYYMMDD ouverte.`

Si 1 sans 2 : Actions → `pari-listen` (workflow_dispatch). v2.10.1 : etape Inbox = `inbox_capture.py` (plus de Python dans le YAML). Si rien : webhook / secrets Worker.

## Hors v1

pdf / KV multi-messages / polling. Photo `/capture` = v2.9 (file_id → getFile → OCR).
v2.10 : inbox = fichier le plus recent ; leftover photo/md retire a chaque `/capture`.
Dates markdown `JJ/MM/AA` lues par rang. `/radar` `/pack` `/match` relays. Pas de scrape bookmaker.
