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

---

## 2026-11-16 — V3.4 : MARK1 lit les 4 formats de transcription

### Ce qui a change
`libs/transcript.py` lisait un seul format. F00B_VOX livre des
transcriptions dont la structure varie selon le mode du workflow
(`segments` a la racine, `words[]` reel, `text` seul). Les 4 formats sont
desormais lus, avec conversion `words[]` -> segments : ponctuation coupee,
silence > `word_silence_sec` (0.6) coupe, groupe borne par `word_group_max`
(60 mots).

### Sorties mesurees
- `v2901790628` -> 1869 segments
- `v2873615032` -> 2372 segments
- `v2927914500` -> 1103 segments

73 tests OK.

---

## 2026-11-16 — V3.5 : les portes qui mentaient

### Le constat (aligne sur l'audit des gates)
Quatre portes decrivaient un comportement qu'elles n'avaient pas.

1. **A1_ACCOUNT et A2_CAMPAIGN** etaient ecrites, testees, et JAMAIS appelees
   par `cmd_export`. Le guide promettait qu'un compte banni ou une campagne
   non financee ne peut pas exporter : c'etait faux. Elles sont desormais
   branchees avant l'export.
2. **M3_WATERMARK** jugeait l'opacite (seuil 0.75 en dur, violation de R1)
   sans jamais regarder un pixel. MARK1 ne produit pas de video : il DECRIT
   le watermark pour OMNIS_WATCH. Ne verifie plus que : fichier present,
   non vide, chemin exploitable. Le seuil voyage dans le pack.
3. **M00E_PACKAGER** ne copiait pas le PNG dans EXPORT/. Il le copie
   desormais, et le pack porte `watermark.file` + `bundled: true`.
4. **M1_SELECTION** affichait « source_text manquant » alors qu'elle testait
   `key_fact`. Message corrige.

78 tests OK.

---

## 2026-11-16 — V3.6 : le focus passe de juge a greffier

### Le probleme (decouvert au premier siege reel)
La campagne exige « main focus or topic », mais la directive dit aussi
« as long as she's featured in the clip » : la regle est VISUELLE, pas
lexicale. Compter les occurrences du nom dans la transcription refusait la
VOD TWITCHCON DAY 1 (2 h 53, POV camera portee, zero mention du prenom)
alors que le personnage principal etait a l'ecran 100 % du temps.

MARK1 ne voit pas la video (R3). Il ne peut pas prouver qu'elle est a
l'ecran. Donc :

- `focus_declared` dans le pack d'entree : l'operateur DECLARE le focus
  (asserted_by + evidence), MARK1 le recopie dans le pack livrable.
- Repli de mesure : si rien n'est declare, compter les mentions du nom,
  comme avant.
- Refus seulement si rien n'est declare ET zero mention.
- Bug annexe : `M00B_SELECTOR` jetait `source_text`, ce qui vidait la mesure
  du bait (0 % sur tous les assets) sans le signaler. Corrige.

84 tests OK. Premier siege reel : pack `e99bd523` (3 clips, focus declare,
PNG a cote du JSON).

---

## 2026-11-16 — V3.7 : watermark PNG ou JPEG

### Le probleme
Le watermark fourni par la campagne est un JPEG 960x200 (logos + nom),
pas un PNG. Trois couches ne connaissaient que `.png` :

- `vexillum.find_png` ne listait que les `.png` : le JPEG etait INVISIBLE,
  et M3 refusait d'exporter en disant « PNG absent » alors qu'il etait la.
- `packager` forcait l'extension `.png` a la copie : un JPEG livre devenait
  un fichier mal nomme dans EXPORT/.
- `watermark_rules.json` interdisait le jpg.

### Ce qui a change
- `find_png` -> `find_watermark`, accepte `.png` / `.jpeg` / `.jpg`.
  Priorite : slug exact du createur tous formats confondus, puis `_1`,
  puis `slug*` ; a egalite de nom, le PNG (fond transparent) gagne.
- `packager` conserve l'extension d'origine, expose `bundled_ext`.
- MARK1 ne convertit rien : le fichier voyage tel quel, OMNIS_WATCH decide
  de la composition.

90 tests OK.

---

## 2026-11-16 — V3.8 : une identite, une trace, un ledger qui vit

### Le probleme 1 : deux calculs de pack_token
`packager._pack_token` hashait 4 champs par asset, `libs.tokens.pack_token`
hashait le pack entier. Sur le pack e99bd523 ils rendaient deux valeurs
differentes. Un appel a `clip_tokens(pack)` fabriquait des identites qui ne
correspondaient a aucun clip livre : l'appariement clip_token <-> lien
publie aurait casse en silence.

**Corrige** : `libs/tokens.py` est la source de verite unique. Le token
hash les 4 champs de contenu (`id`, `overlay_title`, `metadata_title`,
`caption`). Le watermark, le compte, les plateformes, la declaration de
focus et les dates n'entrent PAS dans le token : changer d'opacite n'est
pas changer de clip.`exported_at` remonte au niveau du pack (et reste par
asset, X1_EXPORT le verifie par asset).

### Le probleme 2 : le ledger n'etait jamais alimente
`libs/ledger.py` existait, etait teste, et `cmd_export` ne l'appelait
jamais. Le siege du 16/11 n'a laisse aucune ligne. `cmd_export` ecrit
desormais une ligne par clip (cle `clip_token`), et le ledger vit dans
`EXPORT/` (pas `OUT/`, gitignore par convention).

### Le probleme 3 : pas de trace de siege
`libs/siege_log.py` : un fichier par run (`EXPORT/sieges/<run>_<token>.json`),
jamais reecrit, avec chaque porte, son verdict, sa duree, et le commit du
code. Pas un journal global : deux runs (local + Actions) ecrivent des
fichiers differents, donc pas de conflit git.

### Cycle de vie d'un clip
1. export -> ligne dans ledger.csv (clip_url vide)
2. publication -> `ledger --update <clip_token> --changes '{"clip_url": ...}'`
3. suivi -> views_raw / views_approved / paid_usd sur le meme clip_token
4. `ledger --econ` -> $ net et $/h

Valide en local sur le pack twitchcon (cycle ouvert temporairement puis
restaure a 2026-11-15) : 3 lignes ecrites, rerun = 0 nouveau (idempotent),
`--update` remplit le lien et les vues. 102 tests OK.
