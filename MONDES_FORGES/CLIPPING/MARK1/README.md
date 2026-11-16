# MARK1 — ensemble autonome de sélection et de livraison de clips

> *Le moteur décide, l'opérateur valide, le ledger juge.*

MARK1 vit **à côté** de la forge, dans `MONDES_FORGES/CLIPPING/MARK1/`. Ce
n'est **pas une frégate** : c'est un ensemble autonome qui contient ses propres
**sous-frégates**, chacune nommée en latin et dotée de sa porte.

## Les 6 sous-frégates (V3)

| Sous-frégate | Rôle | Porte |
|---|---|---|
| `M00A_DIRECTIVA` | lit la directive de campagne dans ARCHIVUM | **M0** |
| `M00B_SELECTOR` | sélectionne les segments, pose le cadre du titre | **M1** |
| `M00C_METADATA` | overlay_title (EXC-1) + les 4 champs mécaniques | **M2** |
| `M00D_VEXILLUM` | associe le PNG watermark et ses paramètres | **M3** |
| `M00F_VOX` | transcrit le segment (EXC-2) | **M5** |
| `M00E_PACKAGER` | assemble le pack V3 pour OMNIS_WATCH | **M4** |

**Ordre d'exécution : M0 → M0b → M1 → M5 → M2 → M2b → M3 → A1 → A2 → M4.**
La transcription passe avant les métadonnées parce que le bait se mesure sur
elle. `M0b` (cycle de campagne) coupe avant tout travail si le pack est périmé.
`A1`/`A2` (compte et campagne) coupent juste avant l'export — c'est ce qui
empêche de livrer un pack pour un compte banni sur une campagne non financée.

**Le pack embarque son watermark.** `M00E_PACKAGER` copie le PNG à côté du JSON
dans `EXPORT/` (`production_pack_mark1_<token>.png`) et réécrit
`watermark.file` + `bundled: true`. OMNIS_WATCH n'a plus à deviner où est le
PNG, et rien ne peut être publié avec le mauvais fichier.

> **Deux exceptions bornées.** MARK1 ne fait de réseau qu'en deux endroits
> nommés (`overlay.py`, `vox.py`) et ne lit `llm_enabled` qu'à un seul endroit.
> Tout est écrit dans [`TRACKING/LES_EXCEPTIONS.md`](TRACKING/LES_EXCEPTIONS.md),
> avec les trois `grep` qui le vérifient. Si le code déroge ailleurs, le code
> est en faute.

---

## Ce que MARK1 fait — et ce qu'il ne fait JAMAIS

MARK1 **décide** quels segments valent un clip, **forge** le titre, **vérifie**
que la campagne paie, **emballe** le pack et **écrit** le ledger.

MARK1 **ne produit jamais de vidéo.** Ni MP4, ni ffmpeg, ni `.ass`. C'est la
doctrine du monde-forge CLIPPING :

> « Le forge CLIPPING ne touche **jamais** une vidéo. Il décide **quoi** clipper,
> sous **quel** angle, avec **quel** texte — et livre à OMNIS_WATCH un
> `production_pack.json` prêt à consommer. »

MARK1 produit un **pack JSON** déposé dans `EXPORT/`. Le consommateur
(OMNIS_WATCH) le récupère et produit le clip.

```
MARK1                    │   OMNIS_WATCH            │   Opérateur
─────────────────────────┼──────────────────────────┼──────────────────────
décide, titre, vérifie   │   coupe, reframe, rend   │   publie, soumet <1h
écrit le pack + ledger   │   applique asset_mode     │   colle le lien
                         │                          │   remplit les vues
```

---

## Démarrage en 4 commandes

```bash
cd MONDES_FORGES/CLIPPING/MARK1

python mark1.py doctor                      # prouve qu'aucune clé n'est requise
python mark1.py pack packs/demo.json        # valide le pack d'entrée
python mark1.py export packs/demo.json      # écrit le pack livrable + le ledger
python mark1.py selftest                    # 36 tests, 0 dépendance
```

---

## Les 7 commandes

| Commande | Ce qu'elle fait |
|---|---|
| `doctor` | Liste l'état des clés, vérifie `export_dir` et les `asset_mode`. Sort `0`. |
| `pack <pack.json>` | Applique `G0_PACK` seul. |
| `title "<texte>" [--number --subject --internal]` | Analyse S1 puis propose les titres **déjà valides**. |
| `campaign <camp.json> --platform tiktok [--target 500]` | Éligibilité + $ net/1k + vues nécessaires. |
| `export <pack.json> [--platform tiktok] [--ledger <path>]` | **La commande centrale.** Enchaîne `G0_PACK → D0_DIRECTIVE → M0B_CYCLE → M1_SELECTION → M5_VOX → M2_METADATA → M2B_COMPLIANCE → M3_WATERMARK → A1_ACCOUNT → A2_CAMPAIGN → X1_EXPORT`, écrit le pack dans `EXPORT/`, une ligne de ledger par clip, et une trace de siège. **Aucun MP4.** |
| `ledger [--add | --update <clip_token> --changes '{…}'] [--econ] [--ledger <path>]` | Liste, ajoute, complète, recalcule. `--update` sert à coller le `clip_url` quand la vidéo est publiée. |
| `selftest` | Lance la suite de tests. |

---

## Ce que `export` écrit — trois fichiers, trois rôles

| Fichier | Rôle | Réécrit ? |
|---|---|---|
| `EXPORT/production_pack_mark1_<token>.json` | **Le livrable.** OMNIS_WATCH le consomme. | oui, si le contenu change |
| `EXPORT/production_pack_mark1_<token>.png/.jpeg` | Le watermark, à côté du pack, extension d'origine conservée. | oui |
| `EXPORT/ledger.csv` | **Une ligne par clip**, clé `clip_token`. C'est là qu'on colle `clip_url`, `published_at`, puis `views_approved` et `paid_usd`. | non (append only) |
| `EXPORT/sieges/<run>_<token>.json` | **Le parcours du run** : chaque porte, son verdict, sa durée, le commit du code. | **jamais** — un fichier par run |

**Pourquoi un fichier de trace par run et pas un journal global.** Un journal
modifié à chaque run est le pire cas pour git : deux runs (local + Actions)
écrivent la même ligne, le push est rejeté, et le travail disparaît — c'est
exactement le bug corrigé par `e62386a` sur les transcripts. Ici chaque run
écrit un fichier dont le nom contient déjà son identité, donc deux runs ne
peuvent pas se disputer un fichier qui n'existe pas encore.

**Pourquoi le ledger est dans `EXPORT/` et pas dans `OUT/`.** `OUT/` est
gitignoré par convention (`**/OUT/*.json`) : un journal de gains que git jette
ne compte pas les gains.

**Ce qu'une trace ne dit pas.** Elle dit *qu'une* porte a refusé, jamais
*pourquoi la règle était mal posée*. Ce « pourquoi » appartient à
`TRACKING/MARK1_LOG.md`, écrit à la main. Mélanger les deux noie la décision
de conception dans les `[OK]`.

---

## Les deux tokens

| Token | Formule | Rôle |
|---|---|---|
| `pack_token` | SHA-256 tronqué à 8 car., **des 4 champs de contenu par asset** (`id`, `overlay_title`, `metadata_title`, `caption`) | Identité du **contenu** du pack. Stable, insensible à l'ordre des clés. |
| `clip_token` | `<asset_id>-<AAAAMMJJ>-<pack_token>` | Identité d'**un clip**. Contient le `pack_token`. Ex. `A01-20261116-e99bd523`. |

Un pack sert N clips → **N `clip_token` pour 1 `pack_token`**. Le ledger est
apparié **par `clip_token`**, jamais par titre, date ou ordre de publication.

**Une seule source de vérité : `libs/tokens.py`.** Avant la V3.8 il existait
deux calculs — `packager._pack_token` (4 champs) et `libs.tokens.pack_token`
(pack entier) — qui rendaient deux tokens différents sur le même pack. Un
appel à `clip_tokens(pack)` fabriquait alors des identités qui ne
correspondaient à aucun clip livré, et l'appariement `clip_token` ↔ lien
publié cassait en silence. `packager` délègue désormais à `libs.tokens`.

**Ce qui n'entre PAS dans le `pack_token`** : la date, l'heure, `exported_at`,
le watermark (opacité, position, taille), le compte, les plateformes, la
déclaration de focus. Changer l'opacité d'un watermark ne crée pas un nouveau
clip : c'est le même contenu, donc le même token, donc la même ligne de ledger.

---

## Le cycle de vie d'un clip

```
1. export   → clip_token + pack_token dans ledger.csv (clip_url vide)
2. tu postes la vidéo
3. ledger --update <clip_token> --changes '{"clip_url":"https://…","published_at":"…"}'
4. plus tard : views_raw / views_approved / paid_usd sur le même clip_token
5. ledger --econ → $ net et $/h par clip
```

Un `clip_token` est **immuable** : il identifie le clip pour toute sa vie.
C'est la seule clé qui relie la décision (le pack) au résultat (les vues).

---

## `asset_mode` — les deux valeurs admises

MARK1 ne transmet que **`blur`** et **`reframing`** (validés à l'usage sur la
forge). Le vocabulaire complet de la forge (`split`, `reframing`, `ranking`,
`blur`, cf. `F00D_NARRATIVUM/CODEBASE/caviar_director.py:34`) est plus large :
MARK1 n'accepte que les deux qui sont éprouvés.

MARK1 **transmet** `asset_mode`. Il ne l'exécute jamais.

---

## Les invariants — jamais violés, quel que soit le motif

1. **Aucun appel réseau.** `grep -rn "urllib\|requests\|socket" MARK1/ --include=*.py` → rien.
2. **Aucun seuil en dur.** Tout dans `config/selection.json`.
3. **`llm_enabled` reste `false` et rien ne le lit.**
4. **Aucune suppression dans `MONDES_FORGES/CLIPPING`.**
5. **Aucun ffmpeg, ffprobe, `.ass`, MP4.** MARK1 ne rend pas de vidéo.

---

## Arborescence

```
MARK1/
├── mark1.py                  CLI, 7 commandes (248 l.)
├── config/selection.json     source unique des seuils
├── libs/
│   ├── env.py                les 8 clés optionnelles (38 l.)
│   ├── economy.py            net, revenue, vues nécessaires, $/h (60 l.)
│   ├── s1_context.py         auto-suffisance contextuelle (156 l.)
│   ├── title_forge.py        12 gabarits, 0 LLM (114 l.)
│   ├── campaign.py           éligibilité + revenu attendu (61 l.)
│   ├── gates.py              portes (V3.8)
│   ├── tokens.py             source de verite unique des tokens
│   ├── siege_log.py          trace de siege, 1 fichier par run
│   └── ledger.py             CSV, 26 colonnes, idempotent
├── tests/test_mark1.py       102 tests
├── packs/demo.json           pack d'exemple
├── OUT/                      sorties runtime (gitignoré)
├── ../EXPORT/                pack + watermark + ledger.csv + sieges/
└── TRACKING/                 journal, plan, journal des sieges
```

**~3 540 lignes de Python (hors tests), 0 dépendance.**

---

## Documentation

- `TRACKING/MARK1_LOG.md` — journal d'implémentation, décisions, écarts
- `TRACKING/MARK1_V1_V2_CHANGES.md` — ce que la V2 change par rapport à la V1
- `MARK1_CDC_V2_CLIPPING.html` — cahier des charges complet (dans `GUIde_UTILISATION/24_MODE_MARK1.md` côté forge)
- `GUIDE_UTILISATION/24_MODE_MARK1.md` — guide opérateur dans la forge
