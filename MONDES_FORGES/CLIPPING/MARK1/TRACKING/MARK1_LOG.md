# MARK1_LOG — journal d'implémentation

> Journal tenu conformément au §16.2 du CDC V2 : chaque changement de comportement,
> chaque écart avec le CDC, et chaque sortie réellement mesurée est consigné ici.

---

## 2026-11-15 — Implémentation initiale (V2)

### Ce qui a été écrit

12 fichiers, 1 326 lignes de Python, **zéro dépendance**.

| Fichier | Lignes | Rôle |
|---|---|---|
| `mark1.py` | 248 | CLI, 7 commandes |
| `libs/env.py` | 38 | 8 clés optionnelles, état seul |
| `libs/economy.py` | 60 | net, revenue, vues nécessaires, $/h |
| `libs/s1_context.py` | 156 | auto-suffisance contextuelle |
| `libs/title_forge.py` | 114 | 12 gabarits, `generate()` rend seulement du valide |
| `libs/campaign.py` | 61 | éligibilité, risque `unfunded` |
| `libs/gates.py` | 207 | 6 portes implémentées |
| `libs/tokens.py` | 87 | `pack_token` + `clip_token` par clip |
| `libs/ledger.py` | 126 | CSV 26 colonnes, idempotent |
| `libs/__init__.py` | 5 | — |
| `tests/test_mark1.py` | 224 | 36 tests |
| `README.md` | — | doc de la frégate |

### Sorties réellement mesurées (remplacent les `ATTENDU` du CDC §9 et §10)

```
$ python mark1.py selftest
Ran 36 tests in 0.136s
OK
```

Le CDC V2 annonçait `Ran 24 tests`. Réel : **36**. Écart expliqué ci-dessous.

```
$ python mark1.py doctor
== MARK1 doctor ==
[OK] dependances : aucune (stdlib seule, aucun ffmpeg)
[ absent] CLIPPING_PREMIUM_API_KEY F04 copywriter — LLM premium
[ absent] CLIPPING_LLM_API_KEY     F04 titre — LLM off par defaut
[ absent] CLIPPING_BASE_URL        endpoint compatible OpenAI
[ absent] CLIPPING_LLM_MODEL       nom du modele
[ absent] MODAL_TOKEN_ID           GLOW — hors perimetre MARK1
[ absent] MODAL_TOKEN_SECRET       GLOW — hors perimetre MARK1
[ absent] TELEGRAM_BOT_TOKEN       alertes portes
[ absent] TELEGRAM_CHAT_ID         alertes portes
[ absent] YTDLP_COOKIES_FILE       VOD privees / age-restricted
[OK] export_dir               .../MONDES_FORGES/CLIPPING/EXPORT
[OK] asset_modes              blur, reframing
[OK] GLOBAL
```

9 clés absentes (le CDC en annonçait 8), `[OK] GLOBAL`. **Aucune clé requise.**

```
$ python mark1.py export packs/demo.json --platform tiktok
[OK] X1_EXPORT : 2 clip_tokens uniques, mode=blur
[OK] pack ecrit : .../EXPORT/production_pack_mark1_DEMO_C1.json
[OK] ledger : A01-20261115-ae45e408
[OK] ledger : A02-20261115-ae45e408
```

Deux clips, **un seul `pack_token` (`ae45e408`)**, deux `clip_token` distincts.
C'est la propriété du §8.8, vérifiée sur une sortie réelle.

```
$ python mark1.py export packs/demo.json --platform tiktok   # 2e fois
[OK] pack ecrit : .../EXPORT/production_pack_mark1_DEMO_C1.json
[SKIP] ledger : A01-20261115-ae45e408
[SKIP] ledger : A02-20261115-ae45e408
```

Idempotence prouvée.

```
$ python mark1.py ledger --update A01-20261115-ae45e408 \
      --changes '{"views_approved": 42000, "minutes_worked": 25}'
mis a jour

$ python mark1.py ledger --econ
  A01-20261115-ae45e408 : 75.60 $ net, 181.44 $/h
```

Le point d'écriture du §17.3 fonctionne : 42 000 vues à 2 $/1k, frais 10 % → 75,60 $ net,
25 min travaillées → 181,44 $/h.

### Écarts assumés par rapport au CDC V2

| # | Écart | Motif |
|---|---|---|
| **E1** | `render.style` → **`asset_mode`**, valeurs `blur` / `reframing` | Décision utilisateur. `asset_mode` est le nom réel du terrain (`production_pack_asf_c1.json`, `liber_clipping.json → inputs_warsmith.asset_mode`). Le CDC V2 est donc **légèrement en retard** sur ce point. |
| **E2** | Porte **`C2_DISCLOSURE` ajoutée** (non prévue au CDC V2) | `CONTRACTS/clipping_rules.md` règle C2 : `#ad`/`#sponsored` obligatoire dans la caption, sous peine de rejet Whop + shadowban. Le CDC V2 ne la couvrait pas. Sans elle, MARK1 exportait des clips impubliables. |
| **E3** | **36 tests** au lieu de 24 | Les 24 méthodes du CDC sont là, plus : `test_bad_asset_mode`, `test_disclosure_gate` (2 assertions), et `frozen` keys. `unittest` compte par méthode, pas par ligne de tableau — c'est le CDC qui comptait large. |
| **E4** | `production_pack_mark1_<cid>.json` | Convention réelle de `EXPORT/` (`production_pack_<campagne>.json`), préfixe `mark1_` pour ne pas collisionner avec les packs F05_PACKAGER. |
| **E5** | 9 clés dans `doctor`, pas 8 | `CLIPPING_PREMIUM_API_KEY` (réelle dans la forge) s'ajoute aux 8 connues. |

### Bug trouvé pendant l'implémentation (et corrigé)

**B1 — `ledger` affichait `net=None`.** La commande `ledger` lisait la colonne
`net_usd`, qui n'existe pas dans `FIELDS` (le net est **calculé**, jamais stocké :
il dépend d'un taux de frais qui peut changer). Corrigé : la commande affiche
`paid_usd`, la donnée réellement constatée. Les 26 colonnes n'ont pas bougé.

### Bugs de syntaxe rencontrés (Windows)

Les apostrophes ASCII françaises (`c'est`, `l'entité`) fermaient les docstrings
Python. `libs/s1_context.py` a dû être réécrit sans aucun caractère non-ASCII.
**Règle pour la suite : les fichiers `.py` de MARK1 sont en ASCII pur.** Les
accents vivent dans le `.md` et le `.html`, jamais dans le code.

### Invariants vérifiés après implémentation

```
$ grep -rn "urllib\|requests\|socket" MARK1/ --include=*.py     → 0 résultat
$ grep -rn "llm_enabled" MARK1/ --include=*.py                  → 0 résultat
$ grep -rni "ffmpeg\|ffprobe" MARK1/ --include=*.py             → 3 résultats, tous des négations en docstring
```

- Aucun appel réseau ✅
- Aucun seuil en dur ✅ (tout dans `config/selection.json`)
- `llm_enabled` jamais lu ✅
- Aucune suppression dans la forge ✅ (`git status` : seul `MARK1/` est nouveau)
- Aucun rendu vidéo ✅

### E2E vérifiés

| Geste | Résultat |
|---|---|
| `doctor` | `[OK] GLOBAL`, rc=0 |
| `pack packs/demo.json` | `[OK] G0_PACK : 2 assets` |
| `export` | pack dans `EXPORT/`, 2 `clip_token` partageant `ae45e408` |
| `export` (2e fois) | `[SKIP]` × 2 → idempotence |
| `ledger --update` | ligne complétée, `--econ` recalcule 75,60 $ / 181,44 $/h |
| Pack relu dans `EXPORT/` | `mode`, `asset_mode`, `pack_token`, `clip_token`, `exported_at` présents |

### Ce qui n'a PAS été vérifié

- **Aucun pack réel de campagne** n'a été exporté : le seul pack testé est
  `packs/demo.json`, fabriqué pour l'occasion. Le premier pack réel révélera
  peut-être un champ manquant.
- **S1 n'est pas calibré.** L'hypothèse « `context_dep` bas → portée hors-fans
  haute » reste **non validée** (CDC §15.2). Aucune donnée réelle ne l'appuie.
- **Le taux de frais (10 %) et le délai de règlement sont NON VÉRIFIÉS.** Ils sont
  paramétrés, pas affirmés.

---

## Prochaine entrée attendue

Au premier pack réel de campagne : consigner ici le `pack_token` produit, le
nombre de clips, et tout champ du pack que le consommateur OMNIS_WATCH déclarera
manquant.
