# PLAN_V3 — implémentation de MARK1 V3

> Plan validé par le Warsmith avant codage. Ce fichier est le contrat d'exécution :
> chaque phase a son critère de passage, et **aucune phase ne commence avant que la
> précédente soit verte**.

Branche : `pari-forge-perturabo-xs4c`
Point de départ : `3392af6` (MARK1 V2, 36 tests verts, module unique)

---

## 0. Ce qui change, en une page

La V2 était **un module unique** (`mark1.py` + 8 libs) qui écrasait tout dans une
seule commande `export`. La V3 devient **6 sous-frégates nommées à la latine**, chacune
avec son artefact et sa gate, comme `F00_IRON_SENTINEL/F00A..F00D`.

Trois exceptions sont ouvertes et **bornées à un module nommé**. Aucune ne touche
la doctrine : MARK1 ne produit toujours **aucun MP4**.

| # | Décision | Effet |
|---|---|---|
| 1 | 6 sous-frégates latines `M00A`→`M00F` | découpage + 6 gates |
| 2 | `overlay_title` par LLM **contraint** + boucle de réparation | EXC-1 |
| 3 | Sans clé → relais `ORACLE/` (mode semi-automatique) | EXC-1 bis |
| 4 | Transcription : copie totale de VOX | EXC-2 |
| 5 | Directive **toujours** lue dans `ARCHIVUM/campaign/` | conformité = paiement |
| 6 | Pack enrichi : watermark + 5 champs de métadonnées | conformité campagne |
| 7 | EN + FR pilotés par `directive.language` | marché US |
| 8 | Plancher CPM **0,15 $/1k** | décision Warsmith, pas un fait de marché |
| 9 | MARK1 n'appelle **jamais** F00 | copie de code, pas d'appel |

---

## 1. Les 6 sous-frégates et leurs gates

```
M00A_DIRECTIVA  → directive_parsed.json        → gate M0
M00B_SELECTOR   → selection.json               → gate M1
M00C_METADATA   → metadata.json (+ ORACLE)     → gate M2
M00D_VEXILLUM   → watermark.json               → gate M3
M00F_VOX        → transcript.json              → gate M5   ← s'exécute avant M4
M00E_PACKAGER   → production_pack_mark1_*.json → gate M4 (= X1_EXPORT)
```

Ordre d'exécution : `M0 → M1 → M2 → M3 → M5 → M4`.
Le numéro de `M00F_VOX` est conventionnel ; il tourne avant l'assemblage parce que
le pack porte la transcription.

---

## 2. Les 6 phases

### Phase 0 — Préparation (30 min)

**Objectif** : poser le squelette, archiver la V2, ne rien casser.

| Tâche | Détail |
|---|---|
| `git tag mark1-v2` | point de retour |
| Créer `MARK1/M00A_DIRECTIVA/` … `M00F_VOX/` | chacun avec `CODEBASE/`, `OUT/`, `.gitkeep` |
| `MARK1/TRACKING/LES_EXCEPTIONS.md` | le registre des 2 exceptions (écrit en Phase 6) |
| `config/selection.json` → `min_cpm_usd_per_1k: 0.15` | décision Warsmith |
| Ajouter `llm`, `languages`, `directiva`, `watermark` dans la config | — |

**Critère de passage** : `python mark1.py selftest` → `Ran 36 tests, OK`
(V2 intacte, rien n'est encore déplacé).

---

### Phase 1 — M00A_DIRECTIVA + gate M0 (2 h)

**Objectif** : lire la directive depuis ARCHIVUM, refuser si incomplète.

| Tâche | Détail |
|---|---|
| `M00A_DIRECTIVA/CODEBASE/directiva.py` | lit `ARCHIVUM/campaign/campaign_directive.json` |
| Champs extraits | `language`, `platforms`, `payout.per_platform`, `caption_rules[plateforme]` (handle, hashtags, format), `watermark`, `anti_spam`, `content_source`, `cycle` |
| Calcul `payout_usd_per_1k` | `payout_usd / views_per_unit * 1000` (la vraie unité de la campagne) |
| `gates.d0_directive(directive, cfg)` | refuse si `language` ∉ {English, French}, si un handle manque pour une plateforme visée, si `payout` absent |
| CLI | `python mark1.py directive` → affiche la directive parsée |

**Cas de test réels** (avec la vraie directive AISHAH) :
- `language: English` → OK
- payout `15 $ / 50 000` → `0.30 $/1k` → **≥ 0,15** → éligible
- handle tiktok `@aishah` présent, handle youtube `@hiaishahsofey` présent
- watermark `opacity_min 0.75`, `position center`

**Critère de passage** : `python mark1.py directive` lit la vraie directive et
affiche `language=English`, `payout=0.30 $/1k`, 4 plateformes avec handles.
Gate M0 rouge si on retire `language`.

---

### Phase 2 — M00B_SELECTOR + gate M1 (2 h)

**Objectif** : sélectionner les segments et poser le cadre du titre, dans la langue de la directive.

| Tâche | Détail |
|---|---|
| `M00B_SELECTOR/CODEBASE/selector.py` | prend les segments du pack d'entrée + applique `S2_DURATION` |
| Cadre du titre | extrait `entity` (sujet de la directive), `key_fact`, `numbers[]` du `source_text` |
| Lexique **EN + FR** | `libs/lang/en.json`, `libs/lang/fr.json` : mots universels + verbes d'enjeu |
| `s1_context.analyse(text, lang=...)` | paramètre de langue ajouté (rétrocompatible : `lang="fr"` par défaut) |
| `gates.m1_selection(selection, directive, cfg)` | refuse si langue ≠ directive, si un segment sort des bornes, si 0 segment |
| CLI | `python mark1.py select <pack.json>` |

**Tests** :
- `analyse("Cucumber Key? The Shocking Truth Behind It", lang="en")` → reject
- `analyse("Il a perdu 5000 dollars en une nuit", lang="fr")` → ok
- `analyse("He lost 5000 dollars overnight", lang="en")` → ok
- un pack `language: English` dont les titres sont FR → gate M1 rouge

**Critère de passage** : les 4 assertions ci-dessus vertes + `select` fonctionne
sur le pack d'exemple.

---

### Phase 3 — M00C_METADATA + gate M2 (4 h) ← la plus lourde

**Objectif** : produire les 5 champs de métadonnées + l'overlay sous contrainte.

#### 3a — Les 4 champs mécaniques (zéro LLM)

| Champ | Règle |
|---|---|
| `metadata_title` | gabarit + entité + fait, **≤ 85 car.**, capitalisation normale |
| `description` | accroche + handle de la directive + hashtags, **≤ 220 car.**, sans CTA |
| `tags[]` | fréquence dans `source_text` + entités + termes de la directive, lowercase |
| `hashtags[]` | ceux de la directive + 1–2 dérivés du sujet |
| `caption` | par plateforme : handle de `caption_rules`, hashtags, **`#ad`** |

Module : `M00C_METADATA/CODEBASE/metaforge.py`. Aucun appel réseau.

#### 3b — `overlay_title` sous contrainte (EXC-1)

Module : `M00C_METADATA/CODEBASE/overlay.py`

```
3 modes, décidés au démarrage :
  llm_enabled=true  + clé présente → MODE 1 : LLM direct
  llm_enabled=true  + clé absente  → MODE 2 : relais ORACLE
  llm_enabled=false                → MODE 2 : relais ORACLE

Boucle (commune aux 2 modes) :
  candidats = 3 propositions
  valides = [c for c in candidats if validate(c) and analyse(c).verdict == "ok"]
  si valides → on garde la première, gate M2 verte
  si aucun   → on régénère avec les ERREURS EXACTES en contexte
               max 3 rounds, puis gate M2 rouge
```

#### 3c — Le relais ORACLE (mode 2)

| Tâche | Détail |
|---|---|
| Écriture | `ORACLE/pending/overlay_<packtoken>.json` — **un seul fichier pour tous les segments** |
| Contenu | pour chaque segment : `source_text`, `language`, contraintes, les 3 erreurs du round précédent s'il y en a |
| Mode d'emploi | le fichier contient un champ `instructions` en clair : ce que l'opérateur doit copier, et le format JSON attendu |
| Lecture | `ORACLE/answers.json` via `oracle_relay` existant |
| Arrêt | si pending non répondu : MARK1 sort **code 3**, état `waiting_oracle`, relance manuelle |
| Reprise | deuxième lancement : relit `answers.json`, valide, poursuit |

**Critère de passage** :
- mode 1 (clé) : 3 candidats rendus, ≥ 1 valide, gate M2 verte
- mode 2 (sans clé) : pending écrit, MARK1 sort code 3, l'agent répond, relance → gate M2 verte
- boucle : 3 candidats tous invalides → 2e round contient les erreurs → 3e round → rouge
- **le titre `"Abonne toi vite"` est refusé** (le trou de la V2)

---

### Phase 4 — M00D_VEXILLUM + gate M3 (1 h)

**Objectif** : associer le PNG watermark et ses paramètres.

| Tâche | Détail |
|---|---|
| `M00D_VEXILLUM/CODEBASE/vexillum.py` | trouve le PNG dans `ARCHIVUM/campaign/watermarks/` |
| Résolution | `[creator]_watermark.png` ou `[creator]_1.png` ; erreur explicite si absent |
| Paramètres | `opacity` (≥ `opacity_min` de `watermark_rules.json`), `position: center`, `size_pct: 15` |
| Par plateforme | `platforms_obliged` = tiktok, instagram_reels, youtube_shorts ; `platforms_optional` = twitter_x |
| `gates.m3_watermark(wm, directive, cfg)` | rouge si un PNG obligatoire manque pour une plateforme visée |

**Critère de passage** : avec `aishahsofey_1.png` (47 Ko, vérifié présent) →
`watermark.json` avec chemin absolu, opacity 0.80, 3 plateformes obligées.
Sans PNG → gate M3 rouge avec message nommant le chemin attendu.

---

### Phase 5 — M00F_VOX + gate M5 (3 h) — EXC-2

**Objectif** : copier la sous-frégate de transcription, sans appeler F00.

| Tâche | Détail |
|---|---|
| Copier `F00B_VOX/MODAL/transcribe.py` | → `M00F_VOX/CODEBASE/modal/transcribe.py` (+ `requirements.txt`, `DEPLOYER.md`) |
| Copier `F00B_VOX/CODEBASE/transcribe_segment.py` | → `M00F_VOX/CODEBASE/transcribe_segment.py` (le client) |
| `M00F_VOX/CODEBASE/vox.py` | wrapper : prend `vod_url` + bornes, télécharge l'audio du segment, appelle le client, écrit `transcript.json` |
| Env | `MODAL_URL`, `MODAL_TOKEN_ID` (déjà en place, vérifié) |
| `gates.m5_transcript(tr, cfg)` | rouge si `MODAL_URL` absent (« service non déployé : lance `perturabo_transcribe.yml` »), si 0 mot, si langue détectée ≠ directive |
| **Aucun repli** | décision Warsmith : tout est en place, pas de bascule vers ARCHIVUM |

**Note** : `ffprobe` est utilisé **uniquement ici** (`_probe_duration`). Contrôle
`grep -rn "ffprobe" MARK1/ --include=*.py` doit ne renvoyer que ce module.

**Critère de passage** : `vox.py --check` valide la présence de `MODAL_URL` et
du PNG ; avec URL absente → message explicite et gate M5 rouge.

---

### Phase 6 — M00E_PACKAGER + gate M4 (3 h)

**Objectif** : assembler le pack V3 complet et écrire le ledger.

| Tâche | Détail |
|---|---|
| `M00E_PACKAGER/CODEBASE/packager.py` | assemble : directive + sélection + métadonnées + watermark + transcript + tokens |
| Schéma V3 | `mode`, `directive_source`, `language`, `asset_mode`, `source`, `campaign`, `account`, `watermark`, `assets[]` (avec `overlay_title`, `metadata_title`, `description`, `tags[]`, `hashtags[]`, `caption`, `transcript_excerpt`, `clip_token`, `exported_at`), `pack_token` |
| `gates.m4_pack(pack, cfg)` | = `x1_export` enrichi : watermark présent si obligatoire, 5 champs de métadonnées non vides, `#ad` dans chaque caption, `clip_token` unique |
| Ledger | 26 → **31 colonnes** (+ `language`, `overlay_title`, `metadata_title`, `hashtags`, `watermark_file`) |
| CLI | `python mark1.py siege <pack.json>` — le parcours complet M0→M4 |

**Critère de passage** : `siege packs/demo.json` va jusqu'à `[OK] M4`, pack écrit
dans `EXPORT/`, une ligne de ledger par clip, 31 colonnes.

---

## 3. Les tests

| Niveau | Cible | Contenu |
|---|---|---|
| Unitaires | **~60 tests** | économie (5), S1 EN+FR (8), titres EN+FR (8), gates M0–M4 (14), tokens (4), ledger (2), directive (6), watermark (3), métadonnées (6), overlay/boucle (4) |
| **E2E-1** | modèle 2 (sans clé) | `siege` → pending écrit → réponse injectée → relance → pack dans `EXPORT/` |
| **E2E-2** | modèle 1 (clé) | `siege` → overlay validé au 1er round |
| **E2E-3** | boucle de réparation | 3 candidats invalides → round 2 contient les erreurs → round 3 → gate M2 rouge |
| **E2E-4** | campagne réelle | directive AISHAH (0,30 $/1k) → éligible (plancher 0,15) |
| **E2E-5** | refus | sans `#ad` → M4 rouge ; sans PNG → M3 rouge ; `language` FR sur directive EN → M1 rouge |
| **E2E-6** | idempotence | `siege` deux fois → `[SKIP]` ledger |
| **E2E-7** | bornage EXC-2 | `grep ffprobe` ne trouve que `M00F_VOX` |

Les E2E sont exécutés en local **et** dans un script `tests/e2e/run_e2e.sh` versionné.

---

## 4. Documentation à mettre à jour

| Fichier | Ce qui change |
|---|---|
| `MARK1/TRACKING/LES_EXCEPTIONS.md` | **nouveau** — les 2 exceptions, ce qu'elles abrogent, les 3 `grep` de contrôle, le risque Modal |
| `MARK1/TRACKING/PLAN_V3.md` | ce fichier — tenu à jour au fil des phases |
| `MARK1/TRACKING/MARK1_LOG.md` | une entrée par phase, sorties réelles recopiées |
| `MARK1/TRACKING/MARK1_V1_V2_CHANGES.md` | renommé/complété → écarts V1→V2→V3 |
| `MARK1/README.md` | 6 sous-frégates, 6 gates, les 2 modes LLM, arborescence V3 |
| `GUIDE_UTILISATION/24_MODE_MARK1.md` | parcours opérateur **gate par gate**, le mode ORACLE expliqué pas à pas |
| `TRACKING/CLIPPING_LOG.md` | entrée V3 |
| `TRACKING/INDEX.md` | pointeurs vers les nouveaux fichiers MARK1 |
| `README.md` de la forge | MARK1 = ensemble autonome (correction : **plus** « frégate ») |
| `MARK1/CDC/MARK1_CDC_V3_CLIPPING.html` | **nouveau** CDC V3 (V2 archivé) |

---

## 5. Le commit

Un seul commit à la fin, message structuré :

```
feat(MARK1): V3 — 6 sous-fregates, 6 gates, overlay LLM contraint + ORACLE,
              transcription VOX, pack conforme campagne

Sous-fregates latines M00A_DIRECTIVA -> M00F_VOX, une gate par sous-fregate.
EXC-1 : overlay_title par LLM contraint, avec boucle de reparation et
        relais ORACLE sans cle (mode semi-automatique).
EXC-2 : transcription = copie totale de VOX, Modal + ffprobe bornes a M00F.
Pack V3 : watermark + metadata_title + description + tags + hashtags + caption.
Directive toujours lue dans ARCHIVUM. EN + FR. Plancher CPM 0.15 $/1k.
Aucun MP4. Aucune communication vers F00.
```

Puis `git push` sur `pari-forge-perturabo-xs4c`.

---

## 6. Critère de fin — où en est-on ?

Le siège réel était conditionné à **8 conditions**. État au 2026-11-16 :

| # | Condition | État | Preuve / reste à faire |
|---|---|---|---|
| 1 | `python mark1.py selftest` → tous verts | ✅ **102 tests** | `Ran 102 tests … OK` |
| 2 | `python mark1.py doctor` → `[OK] GLOBAL` | ✅ | seules les clés LLM/Modal/Telegram manquent (optionnelles) |
| 3 | Les 7 E2E verts (`tests/e2e/run_e2e.sh`) | ❌ **dossier vide** | le script n'existe pas encore |
| 4 | Un pack réel va jusqu'à `[OK] M4` dans `EXPORT/` | ✅ **pack `e99bd523`** | 11 portes `[OK]`, voir `TRACKING/JOURNAL_SIEGES.md` |
| 5 | Le pack contient watermark + 5 champs de métadonnées | ✅ | PNG copié à côté du JSON, `bundled: true` |
| 6 | `grep ffprobe` borné à `M00F_VOX` | ✅ | 2 appels, tous dans `M00F_VOX/CODEBASE/vox.py` (lecture de durée, jamais de production) |
| 7 | `grep -rni "ffmpeg\|\.ass\|\.mp4"` vide hors docstrings | ✅ | 4 occurrences, toutes des phrases de docstring (« aucun ffmpeg ») |
| 8 | Aucune suppression dans `MONDES_FORGES/CLIPPING` | ✅ | `git diff --diff-filter=D 025b08b..HEAD` vide |

**Le premier siège réel a eu lieu le 2026-11-16** (VOD `v2927914500`, pack
`e99bd523`). Seule la condition 3 reste ouverte : les E2E n'existent pas.
Le siège a prouvé le pipeline, pas la couverture E2E.

> **Note V3.8** : le ledger et la trace de siège sont désormais écrits par
> `export` (`EXPORT/ledger.csv`, `EXPORT/sieges/`). Le siège du 16/11 ne les a
> pas eus : la fonctionnalité n'existait pas encore.
