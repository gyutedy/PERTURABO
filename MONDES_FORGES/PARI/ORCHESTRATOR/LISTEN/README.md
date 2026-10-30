# LISTEN — Relais Telegram (Cloudflare Worker)

Webhook Telegram → allowlist 1 operateur → ACK → `workflow_dispatch` `pari_listen.yml`.
Zero calcul ici. Le siege tourne sur GitHub Actions (`workflow.py`).

## 1. Deploy (une fois)

```bash
# Compte Cloudflare + wrangler (npm i -g wrangler)
cd MONDES_FORGES/PARI/ORCHESTRATOR/LISTEN
npx wrangler login
npx wrangler deploy
```

Note l'URL : `https://pari-listen.<compte>.workers.dev`

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

## 3. Secrets GitHub (repo)

Settings → Secrets and variables → Actions :

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

(deja prevus par `pari_daily.yml`)

## 4. Brancher le webhook Telegram

```bash
# TOKEN = TELEGRAM_BOT_TOKEN, SECRET = TELEGRAM_WEBHOOK_SECRET
curl -s "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://pari-listen.<compte>.workers.dev" \
  -d "secret_token=${SECRET}"
```

Verif :

```bash
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

## 5. Test

Dans Telegram, envoie `/start`. Tu dois voir :

1. ACK Worker : `Recu /start — siege en cours (~1 min).`
2. Reponse `workflow.py` : `Campagne PARI-YYYYMMDD ouverte.`

Si 1 sans 2 : Actions → `pari-listen` (workflow_dispatch). Si rien : webhook / secrets Worker.

## Hors v1

png/pdf, KV multi-messages, `/radar` `/pack` `/match`, polling.
