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

## V3 — 2026-11-16 (phases 0-6 implémentées)

- 6 sous-frégates latines + 6 portes (M0..M5), ordre M0→M1→M5→M2→M3→M4.
- Pipeline complète E2E vérifiée sur la vraie directive AISHAH :
  D0 (0.30 $/1k) → M1 → M5 → WAIT oracle (code 3) → réponse → M2 → M3
  → pack `production_pack_mark1_dcc4d94b.json`.
- Le trou V2 « Abonne toi vite » est fermé : le CTA est rejeté par la boucle
  de réparation, le bon titre est retenu.
- 46 tests OK (36 V2 + 10 V3).
- Deux corrections de doctrine : G0_PACK n'exige plus de titre à l'entrée
  (le moteur produit) ; vox ne ment plus sur la source du texte.
- `TRACKING/LES_EXCEPTIONS.md` : EXC-1 (overlay LLM contraint), EXC-2 (VOX),
  3 invariants abrogés bornés, 3 grep de contrôle documentés et vérifiés.
- Budget : 14 462/15 000 crédits consommés, 36 tests verts, 4 poussées GitHub.

## V3.1 — 2026-11-16 (conformite reelle de campagne)

Directive source du cycle utilisee : `ARCHIVUM/campaign/directive_aishah_2026-07-24.txt`
(archivee, 3744 octets). Confrontation texte <-> base : 4 ecarts trouves.

1. **Payouts faux sur 2 plateformes.** La base disait 15$ pour les quatre ;
   la directive dit 10$ pour X et IG Reels. Corrige (0.200 $/1k au lieu de
   0.300). Le ledger surevaluait de 50% la moitie des plateformes.
2. **Porte M0B_CYCLE.** La directive impose "Always follow the announcement
   for the current cycle". Rien ne verifiait `cycle.end`. **Le cycle AISHAH
   est expire depuis le 2026-11-15** : un siege aujourd'hui est refuse en
   rouge. C'est le premier blocage reel de la porte, et il est legitime.
3. **Porte M2B_COMPLIANCE** : vocabulaire interdit (refus sur overlay,
   nettoyage ailleurs), main focus (mesure sur la transcription),
   bait (overlay non soutenu par le texte), negative PR (marqueurs).
4. **Vocabulaire interdit mixte** : `metaforge` nettoie tags/description/
   caption/metadata_title ; `check_asset` refuse si un terme interdit
   subsiste dans overlay_title.

Ce qui n'est PAS traite, et ne doit pas l'etre : logos visibles, caption
editee sur IG, post prive, engagement organique. MARK1 ne produit pas la
video -- ces regles appartiennent a OMNIS_WATCH et a l'operateur.

56 tests OK (36 V2 + 10 V3 + 10 V3.1).

### A FAIRE avant le premier siege reel
- [ ] La campagne doit avoir un cycle ouvert (M0B le dit, en rouge)
- [ ] `MODAL_URL` / `MODAL_TOKEN_ID` pour la transcription (EXC-2)
- [ ] Fournir une transcription horodatee OU un audio par segment (option B)

## V3.2 — 2026-11-16 (vox aligne sur la convention de la forge)

**Le probleme** : mon `vox.py` cherchait `MODAL_URL` dans l'environnement.
La forge, elle, range l'URL dans `CONTRACTS/f00b_secrets.json` (champ
`base_url`), fichier genere par `.github/workflows/perturabo_transcribe.yml`
qui l'extrait du log de deploiement :

    URL=$(grep -oE 'https://[a-zA-Z0-9.-]+\.modal\.run' /tmp/modal_deploy.log)

Le fichier n'est JAMAIS commite (seul `f00b_secrets.example.json` l'est).
Resultat : deux conventions pour la meme chose, et le local ne voyait rien.

**Corrige** : `vox.py` lit `CONTRACTS/f00b_secrets.json` comme F00B, avec
repli sur les variables d'environnement. Le service est un endpoint
**OpenAI-compatible** `/audio/transcriptions` en multipart/form-data
(`file`, `language`, `offset`), pas le JSON base64 que j'avais suppose.
Multipart construit sans dependance externe. Taille bornee par `max_audio_mb`
du fichier de secrets.

Priorite de transcription : transcript fourni (option B) > source_text >
audio_path. Message honnete quand la base_url manque.

60 tests OK (36 V2 + 10 V3 + 10 V3.1 + 4 V3.2).

### Pour faire tourner un siege en local
1. Deployer le service : workflow `perturabo_transcribe` (Actions > Run)
2. Recuperer `base_url` dans les logs (`Deployed at: https://...`)
3. Ecrire `CONTRACTS/f00b_secrets.json` avec ce `base_url`
4. Exporter `MODAL_TOKEN_ID` dans le shell
5. Fournir un pack avec `source_text` ou `transcript` par segment

## V3.3 — 2026-11-16 (MARK1 lit les transcriptions de F00B_VOX)

**Decision d'architecture** : MARK1 ne parle JAMAIS a F00B_VOX, il lit
ARCHIVUM. Le declenchement reste a l'operateur (workflow
`perturabo_transcribe`), parce que MARK1 ne doit pas avoir d'effet de bord
distant.

Pourquoi ARCHIVUM et pas un appel direct :
  - la transcription est payee UNE fois et relue autant de fois qu'on veut
    (un appel direct la rejouerait a chaque siege, a chaque round ORACLE)
  - chaque transcript est un commit date : tracable, rejouable
  - si Modal tombe, MARK1 continue sur l'existant
  - appeler une fregate = heresie dans la doctrine

**`libs/transcript.py`** :
  - `vod_id(url)` : extrait l'id Twitch (`/videos/1234`) ou YouTube (`v=...`)
  - `find_transcript(cfg, root, url)` : cherche dans
    `ARCHIVUM/montage/transcripts/v<ID>_transcript.json`
  - `segments(doc)` / `window_text(doc, a, b)` : lit les segments horodates
  - `candidate_windows(doc, cfg, limit)` : propose des fenetres autour des
    marqueurs d'enjeu et des chiffres, bornees par min/max_segment_sec

**`mark1.py export --transcript <path> --nb-segments N`** : si fourni (ou si
le pack pointe `source.transcript_path` / `source.vod_url`), MARK1 choisit
les segments lui-meme au lieu de lire `assets[]`.

Format lu (celui de la forge) :
    {"transcript": {"text": ..., "segments": [{"start","text","duration"}]}}

Teste de bout en bout sur une fixture reelle (120 segments) :
TRANSCRIPT -> 2 segments choisis -> D0 -> M0B -> M1 -> M5 -> WAIT oracle.

67 tests OK (36 V2 + 10 V3 + 10 V3.1 + 4 V3.2 + 7 V3.3).
