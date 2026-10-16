# CONTINUATION — Reprise du siège (F00_CAPTEURS)

> **LIRE CE FICHIER EN PREMIER** si vous arrivez dans ce repo "à froid".
> Il dit EXACTEMENT où le travail s'est arrêté et quoi faire ensuite.

---

## 📅 DERNIÈRE MISE À JOUR

**Date** : 2026-09-19
**Ajout** : **Gate F00B fermé → F00D exécuté → GATE F00D prêt.** Verdict
Warsmith enregistré (5 `mixed` approuvés, vue de gate dans la Salle de
Contrôle : `gate_f00b_v2873615032.html`). F00D : 5 médias extraits
(`--download-sections`), **5 partitions caviar blur émises** après 2 fixes
(seuil silences 400 ms dans le Budget + arbitrage composeur dans le budget —
self-test et 10/10 tests verts). Climax réels diversifiés (12.5 / 6.05 / 4.7 /
13.05 / 3.45 s), budgets 46-55/55u. Détail complet :
`F00D_NARRATIVUM/TRACKING_F00D.md`.
**F04 exécuté** (overlay_only blur, kimi-k3/NVIDIA) : 5 titres gate-prêts
après 2 purges (résidus Sophie Rain/Marvel dans angles.json — hérésie
« résidu d'ancien siège » ; conformité English de la directive).
Anti-cond vérifié par grep transcript (tous les titres ancrés dans le contenu).
Sorties : `F04_COPYWRITER/OUT/overlay_{raw,payload}_asf_c{1..5}.json`.
**GATE F04 soumis à l'opérateur**, puis F06 → F05 → EXPORT.

---

**Date** : 2026-09-18
**Ajout** : F00B passe en **mode matrice** — `perturabo_transcribe_matrix.yml`
(3 jobs : prepare → 15×transcribe → reassemble). Scripts nouveaux :
`F00B_VOX/CODEBASE/segment_vod.py` (découpe, overlap 3 s), `merge_transcripts.py`
(fusion dédupliquée par timestamp global), `matrix_score.py` (scoring global,
chaîne auto_detector inchangée). `MODAL/transcribe.py` accepte un `offset`
optionnel (rétrocompatible). Motif : le run séquentiel du 18/09 a perdu ses
sorties (push `HEAD:main` rejeté — corrigé : push sur branche du run + artefacts
tout du long). Guide : `GUIDE_UTILISATION/21_MODE_MATRICE_TRANSCRIPTION.md`.
**Prochaine étape** : run matrice sur la VOD Aishah Sofey (twitch.tv/videos/2873615032,
5 clips, blur, us_young_english, youtube_shorts) → gate F00B opérateur.

---

**Date** : 2026-09-13
**Ajout** : AUDIT WARSMITH corrigé — contrat webhook V2 (candidats enrichis +
couverture analysée affichée) et dashboard v2 (axes gradués, tooltips, cartes
complètes, gate fonctionnelle via `candidate_id`, légende truthful, histogramme,
bandeau d'erreur). Vidéo réelle du Warsmith en cours d'analyse : `cP8vli4kfhs`
(1 h 42, « How Sophie Rain Makes And Spends $100,000,000 Per Year »).
F00B non touché (territoire respecté).

> 🆕 **Livraisons C et D faites** (plan : `F00C_VOX/PLAN_SALLE_DE_GUERRE.md`) :
> la Salle de Guerre est **complète**. Récepteur v2 (`WAR_ROOM/receiver.py`,
> miroir dans ce repo) : dashboard servi sur `GET /`, polling `GET
> /api/war-room`, verdicts Warsmith `POST /api/gate`, webhook F00C `POST /`
> (X-Siege-Token), port env `PORT`. Dashboard `docs/war_room.html` : timeline
> SVG (heatmap + barre rouge + fusion + blocs candidats), cartes triées par
> score, boutons **GO / NO-GO** sur chaque carte, badge LIVE pulsé avec
> nouveaux candidats `NEW`, **toggle DONNÉES BRUTES** (JSON réel). Boucle de
> retour fermée : verdicts stockés idempotents, relis par le pipeline.
> Démo immédiate : `python3 WAR_ROOM/seed_demo.py` (payload Sophie Rain,
> 3 candidats). 11/11 tests récepteur + self-test verts, 23/23 côté F00C.
> **Prochaine étape** : run réel Sophie Rain (secret `YT_COOKIES_BASE64`
> côté Warsmith) → la Salle de Guerre affichera les données réelles.
> Livraisons A ✅ B ✅ C ✅ D ✅ — le Prince voit tout.

---

## 1. État au dernier push

### ✅ Ce qui existe

- **CLIPPING** est opérationnel avec les modes : informatif, humour, meme
- **3 sièges terminés** : NBA_WESTBROOK, STUDENT_DEBT, MARVEL_DOOMSDAY
- **7 frégates actives** : F00A, F00B, F01 → F06
- **ARCHIVUM** enrichi avec channels, campagnes, montage, copywriting, transcripts

### 🆕 Ajouté aujourd'hui

- **F00B_VOX** — L'Oreille Absolue (sous-frégate de F00_CAPTEURS)
  - `F00B_VOX/CODEBASE/f00b_vox.py` — Pipeline complet : ingest → detect → score → gate → trail
  - Ingest VOD partielle (yt-dlp segments HLS, stream copy, jamais de VOD complète)
  - Scoring viral multicritère (6 critères pondérés + bonus/malus)
  - Gate Warsmith (validation manuelle avant trail)
  - Trail prêt pour F03_SOURCE_HUNTER

- **F06_DIRECTOR** — Le Directeur de Montage
  - `F06_DIRECTOR/CODEBASE/director.py` — Génération instructions montage
  - `ARCHIVUM/montage/` — Bibliothèque de montage complète

- **Mode PUR** — Clipping pur (podcast → clip viral)
  - Workflow complet avec F00B_VOX en amont

---

## 2. Les Frégates (mise à jour)

| Code | Nom | Rôle | Statut |
|------|-----|------|--------|
| **F00A** | **CAPTEURS** | **Scan viral YouTube/RSS/Trends** | ✅ Opérationnel |
| **F00B** | **VOX (l'Oreille Absolue)** | **Ingest VOD Twitch partielle + scoring + gate + trail** | ✅ Opérationnel |
| **F00C** | **VOX-C (la Voix des Plateformes)** | **YouTube/Twitch/local — heatmap d'attention + segments viraux, live en cours ET vidéo finie** | 🆕 **Nouveau (v2-live)** |
| F01 | SCOUT | Transcription vidéo | ✅ Opérationnel |
| F02 | TYRANT_CAMP | Verdict GO/NO-GO + océan bleu | ✅ Opérationnel |
| F03 | SOURCE_HUNTER | Sélection segment parfait | ✅ Opérationnel |
| F04 | COPYWRITER | Forger texte viral (frégate lourde) | ✅ Opérationnel |
| F05 | PACKAGER | Emballer production pack | ✅ Opérationnel |
| F06 | DIRECTOR | Instructions de montage | ✅ Opérationnel |

> F00 = F00A (scan viral) + F00B (VOX chat Twitch) + F00C (VOX plateforme YouTube). La position d'une frégate dépend de SA PLACE dans le workflow, pas d'un numéro figé.

> ⚠️ **Règle de branches (leçon v2)** : le live de VOX vit SUR `v2-live` — jamais de
> branche « live » séparée. Toute nouvelle couche d'entrée de VOX (F00B chat, F00C
> plateforme) s'ajoute sur la branche de son monde, aux côtés des existantes.

---

## 2bis. Fix Note 20 — le pont F00C → tronc PUR (2026-09-11)

> *Deux entrées, un tronc, une sortie.*

**Problème corrigé** : F00C s'arrêtait au manifeste `perturabo.voxc.v1` ; le tronc PUR attendait la clé `candidates`. Brancher F00C donnait **0 pack en silence**.

**Ce qui a changé** :
- `f00c_vox.py` gagne `--to-candidats` (et `--top N`) : il émet `OUT/candidats.json` au **schéma canonique** (clé `candidates`, `signal_type: "platform_heat"`, intensité = `attention_norm`).
- Lecture tolérante du tronc (`SHARED/candidates_reader.py`) branchée dans `pur_adapter.py`, `pur_adapter_direct.py` et `pur_montage_pipeline.py` : accepte `candidates`, `candidats` ou un manifeste `perturabo.voxc.v1`, toujours avec warning.
- Workflow `perturabo_vox_c_analysis.yml` : input `to_candidats` (défaut `true`) + artefact `voxc-candidats-*`.
- Docs : guide 20, guides 11/13/14/19, README_V2, `_PIEGES_APPRIS_PUR.md`.

**Règle permanente (anti-régression)** : *tout nouveau capteur DOIT émettre le schéma canonique `{"candidates": [...]}` — un seul schéma d'entrée du tronc, lecteurs tolérants mais verbeux, jamais de silence.* Voir guide 20.

---

## 3. Le Mode PUR — Workflow détaillé

### Inputs du Warsmith
1. URLs VODs Twitch (1 ou plusieurs)
2. Clip viral de référence (optionnel)
3. Plateforme cible (YouTube Shorts / TikTok / Instagram Reels)
4. Marché cible (ex : US / Anglais / Jeune)
5. Nombre de clips demandés

### Workflow (deux entrées → un tronc)
```
Twitch  : F00B_VOX (radar live / auto_detect) → OUT/candidats.json ─┐
                                                                   ├→ pur_adapter_direct → F04
YouTube : F00C_VOX (--to-candidats)          → OUT/candidats.json ─┘
    → pur_montage_pipeline (F06 inline) → pack → GATE Warsmith → EXPORT → OMNIS_WATCH → Opérateur
```

> PUR **direct** : F01 / F02 / F03 sont SKIPPÉS (VOX a déjà détecté, scoré, sélectionné).
> Le mode PUR **long-form** (`pur.py`, 4 gates, F05) reste décrit au guide 11.

### Étapes VOX en détail
```
1. IN/vox_input.json → URLs VOD + segments + nb clips demandés
2. python f00b_vox.py ingest → OUT/vox_manifest.json (commandes yt-dlp)
3. IN/signals.json → Signaux (chat spikes, punchlines, trigger words)
4. python f00b_vox.py detect → OUT/candidats.json (fenêtres 20-40s)
5. python f00b_vox.py score → OUT/scoring.json (6 critères pondérés)
6. python f00b_vox.py gate → OUT/gate_verdict.json (skeleton Warsmith)
7. Éditez gate_verdict.json → changez status: pending → approved/rejected
8. python f00b_vox.py gate_apply → Applique les décisions
9. python f00b_vox.py trail → OUT/trail.json (prêt pour F03)
```

### Outputs
- `vox_manifest.json` — Commandes ingest (yt-dlp)
- `candidats.json` — Fenêtres détectées
- `scoring.json` — Scores multicritère
- `gate_verdict.json` — Décisions Warsmith
- `trail.json` — Segments finaux prêts pour F03

---

## 4. F00B_VOX — Détails techniques

### Architecture
```
F00B_VOX/
├── CODEBASE/
│   ├── f00b_vox.py          ← Script principal (CLI)
│   ├── requirements_f00b.txt ← Dépendances (yt-dlp)
│   └── libs/
│       ├── __init__.py
│       └── auto_detector.py  ← Auto-detect (Option A)
├── IN/                      ← Inputs
│   ├── vox_input.json       ← URLs VOD + segments
│   ├── signals.json         ← Signaux détection
│   └── gate_decisions.json  ← Décisions Warsmith
├── OUT/                     ← Outputs
│   ├── vox_manifest.json
│   ├── candidats.json
│   ├── scoring.json
│   ├── gate_verdict.json
│   ├── trail.json
│   ├── transcript.json       ← Transcription (words + segments + mode)
│   ├── chat.json             ← Chat replay
│   └── auto_detect_report.json ← Rapport complet
├── CONTRACTS/
│   └── f00b_secrets.json     ← Config clé premium (pattern F04)
└── TRACKING/
    └── F00B_LOG.md           ← Journal
```

### Scoring Multicritère
```
score = 0.30 × hook_force + 0.25 × emotion + 0.15 × clarity
      + 0.15 × quotability + 0.10 × timing + 0.05 × format_fit
      + bonus - malus
```

**Mode texte seul (fallback) :** sans word-level timestamps, les critères `hook_force`, `clarity`, `quotability` sont estimés via le type de signal (punchline/trigger_word) et l'intensité chat. Le scoring reste fonctionnel mais moins précis.

### Règles d'or
- ❌ Jamais de VOD complète (segments HLS uniquement)
- ❌ Jamais de recompression (stream copy)
- ❌ Jamais de trail sans verdict gate
- ❌ Budget max 20 min par session
- ⚠️ Auto-detect nécessite clé premium + yt-dlp + ffmpeg

---

## 5. Commandes utiles

```bash
# Pipeline complet (ordre)
python F00B_VOX/CODEBASE/f00b_vox.py ingest        # Génère commandes yt-dlp
python F00B_VOX/CODEBASE/f00b_vox.py ingest --execute  # Exécute les commandes
python F00B_VOX/CODEBASE/f00b_vox.py detect          # Détecte candidats
python F00B_VOX/CODEBASE/f00b_vox.py score           # Score les candidats
python F00B_VOX/CODEBASE/f00b_vox.py gate            # Génère skeleton gate
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply      # Applique décisions
python F00B_VOX/CODEBASE/f00b_vox.py trail           # Génère trails F03
python F00B_VOX/CODEBASE/f00b_vox.py status          # État du pipeline

# Auto-detect (Option A — recommandé)
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --nb-clips 5
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --keep-audio --no-chat
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --market us_young_english --platform youtube_shorts
```

---

## 6. Prochaines étapes

### Court terme
1. ✅ F00B_VOX créé (code + specs + examples)
2. ✅ Auto-detect v1 implémenté (transcription multi-mode + chat replay + scoring)
3. ⏳ Tester auto_detect avec une vraie VOD Twitch (Aishah Sofey)
4. ⏳ Intégrer F00B dans le workflow PUR complet
5. ⏳ Plan 2 : Support campagnes Clipify (watermarks, directives)
6. ⏳ Plan 3 : Mise à jour documentation

### Moyen terme
1. Enrichir ARCHIVUM/montage/ avec plus de patterns
2. Optimiser scoring (IA GPT-4o pour critères subjectifs)
3. Tester le workflow PUR complet de bout en bout

---

*« La VOD est un océan. VOX ne boit que les gouttes d'or. »* 🔩


---

## Session 2026-09-11 — F00C_VOX : la Voix des Plateformes (v2-live)

### Objectif
Donner à PERTURABO la couche VOX **YouTube** : analyse d'un live EN COURS ou d'une
vidéo FINIE (YouTube/Twitch/fichier local), avec heatmap d'attention (l'équivalent
de la barre rouge YouTube), segments viraux et données brutes pour la décision Oracle.

### Origine
Port du v3-LIVE de LACRIMAE (`f00_live.py`, commit `d1b182c`, 8/8 tests verts)
aux conventions F00B. ⚠️ Nommage : dans LACRIMAE, « F00C » = Motion Slow (interpolation)
— sans rapport. Dans PERTURABO, F00C était libre.

### Livré (branche `v2-live-vox-c`)
- `F00_IRON_SENTINEL/F00C_VOX/CODEBASE/f00c_vox.py` — resolve (local / YouTube
  watch·live·shorts / Twitch VOD·chaîne) → metadata (page watch publique, GQL
  Twitch, sans clé) → heatmap (numpy+ffmpeg sur média local) → manifeste
  `perturabo.voxc.v1` (metadata, attention_heatmap, viral_segments pics ≥ 5 s,
  raw_data). Dégradation propre en `metadata_only` sans yt-dlp/numpy : l'Oracle
  reçoit toujours un livrable.
- `CODEBASE/tests/test_f00c_vox.py` — **8/8 tests verts** (hors-ligne).
- `CODEBASE/requirements_f00c.txt` — stdlib + numpy ; yt-dlp/ffmpeg = système.
- `IN/vox_c_input.example.json` + workflow `perturabo_vox_c_analysis.yml`
  (dispatch : `source_url`, `download_budget_seconds`, gate L0, artefact
  `voxc-analysis-*`) + `TRACKING/F00C_LOG.md` + `F00C_GATES.md`.
- Docs : guide `GUIDE_UTILISATION/19_MODE_VOX_C_YOUTUBE.md`, README_V2 (table F00),
  présente entrée CONTINUATION.

### Doctrine
Héraxies F00B respectées : jamais de VOD complète (`--download-sections`), jamais
de recompression, jamais de manifeste vide. La heatmap ne vit que sur le média local.

### Reste
- Premier run réel sur une vidéo YouTube de campagne (GO Warsmith requis).
- Brancher les segments viraux F00C comme candidats en amont de F04 (adaptateur PUR).



---

## 🆕 TRANSCRIPTION GPU PAR MODAL (ajout 2026-09-06)

**Contexte** : la transcription locale en CPU de F00B_VOX est fonctionnelle mais
lente (~1h45 pour la 2e moitié d'une VOD de 3h30). On route désormais la
transcription vers un service **faster-whisper sur GPU Modal**.

**Ce qui est en place** :
- `MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL/` (transcribe.py + DEPLOYER.md)
  → versionné sur GitHub, **aucun secret**.
- `f00b_vox.py` et `auto_detector.py` **inchangés** : `PremiumTranscriber` pointe
  déjà vers `{base_url}/audio/transcriptions`, il suffit de re-pointer la config.

**Ce que doit faire l'opérateur** (cf. `MODAL/DEPLOYER.md` et
`GUIDE_UTILISATION/15_TRANSCRIPTION_MODAL.md`) :
1. `pip install modal` + `modal setup` (ou `modal token set ...`)
2. `modal deploy MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL/transcribe.py`
3. Reporter l'URL dans `f00b_secrets.json` -> `base_url`, puis `export MODAL_TOKEN=...`

**Référence de clé premium (rappel)** : la clé premium NVIDIA (`NVIDIA_NIM_API_KEY`)
sert au **copywriting/Oracle** (analyse des transcripts déjà sortis), PAS à la
transcription. La transcription passe par Modal (Whisper).

**Modèle par défaut** : `medium` (équilibre vitesse/qualité), GPU T4.


---

## 🆕 ORCHESTRATION ORACLE VIA GITHUB ACTIONS (ajout 2026-09-06)

**Décision** : le déploiement Modal + la transcription sont pilotés par
**GitHub Actions**, déclenchés par l'**Oracle** (Cody) via l'API — pas par un
clic manuel de l'opérateur. L'opérateur reste un valideur de Portes exclusif.

**En place** :
- `.github/workflows/perturabo_transcribe.yml` → deploy Modal + download audio + transcribe + score + commit Arquivo.
- Secrets GitHub (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `NVIDIA_NIM_API_KEY`) injectés par l'Oracle (blind).
- `GUIDE_UTILISATION/16_ORCHESTRATION_GITHUB_ACTIONS.md` → doctrine des rôles.

**Flux Oracle** : `POST /actions/workflows/{id}/dispatches` avec inputs (vod_url, nb_clips, market, platform),
puis suivi du run et remontée des Portes à l'opérateur.

**Rôles verrouillés** : Oracle déclenche + suit ; GH Actions exécute ; opérateur valide uniquement.


---

## Session 2026-09-06 — Modal GPU + Orchestration + 1er test de production

### Ce qui a été fait
- **Service Modal** `F00_IRON_SENTINEL/F00B_VOX/MODAL/transcribe.py` : endpoint `/audio/transcriptions` (faster-whisper `medium` sur GPU), word-level + `vad_filter`.
- **Orchestration GitHub Actions** `.github/workflows/perturabo_transcribe.yml` : l'Oracle déclenche via API → `modal deploy` → télécharge l'audio → transcrit → score → commit dans `ARCHIVUM`.
- **Secrets** injectés en aveugle (MODAL_TOKEN_ID/SECRET, NVIDIA_NIM_API_KEY), jamais commités.

### Premier test de production RÉUSSI ✅
- VOD : `https://www.twitch.tv/videos/2864600351` (aishahsofey, "PLAYING GTA V REACTIONS", 3h29)
- `ARCHIVUM/montage/transcripts/v2864600351_transcript.json` (15 118 mots)
- `ARCHIVUM/montage/transcripts/v2864600351_candidats.json` (9 candidats acceptés)

### Pièges à retenir (pour le prochain opérateur)
1. `requests` manquant dans l'image Modal → 500 (faster-whisper l'importe)
2. Image de base `debian_slim` sans CUDA → `libcublas.so.12 not found` ; utiliser `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
3. Précharger le modèle au build + fallback CPU


---

## Session 2026-09-06 (suite) — PLAN refonte VOX (validé, NON implémenté)

### Objectif
Faire de VOX un **garde-barrière multi-capteurs** : tableau brut (emotes, clips commu,
événements, audio, visuel, lexical) → scoring → arbitrage premium (kimi-k3). Éliminer le
garbage avant l'aval (règle « garbage in = garbage out ») et corriger le `signal_intensity:0.9`
constant (auto_detector.py l.380).

### Décisions verrouillées
- Directive campagne **complète** en veto (source / plateforme / marché / cycle / exclusions).
- Clé premium = **analyse sémantique + arbitrage final** (jamais sur le flot brut).
- Full capteurs, dans un entonnoir (les lourds ne tournent que sur les fenêtres chaudes).
- Partie Modal **figée** (succès).

### Prochaines étapes (phases, dans l'ordre)
P1 schéma tableau + campagne complète → P2 capteurs gratuits → P3 lexical →
P4 audio/visuel → P5 premium → P6 scoring/docs.

### Doc
`F00_IRON_SENTINEL/F00B_VOX/PLAN_REFONTE_VOX.md` + `GUIDE_UTILISATION/17_PLAN_REFONTE_VOX.md`.


---

## Session 2026-09-06 (P1 implémentée)

### P1 — Fait ✅
- `F00_IRON_SENTINEL/F00B_VOX/CODEBASE/libs/campaign_veto.py` (nouveau) :
  * contrat du tableau brut (`RAW_TABLE_COLUMNS`, colonnes par capteur pour P2-P4)
  * `find_campaign_directive_md` (découverte directive active dans ARCHIVUM/campaign)
  * `load_campaign_directive` + `apply_campaign_veto` (plateforme=dur, cycle=warning,
    exclusions OF/onlyfans/bait/negative PR = dur).
- `auto_detector.py` : branchement du veto dans `run_auto_detect` (étape 8b),
  non-bloquant (try/except : si module absent, continue sans veto).
- Testé : plateforme non autorisée → veto · exclusion "OF creator" → veto ·
  VOD hors cycle (20260904) → warning (la campagne Aishah Sofey couvre 7/20→7/31).

### Prochaine étape
P2 — capteurs gratuits (emotes+vélocité, clips commu heatmap, événements) remplir
les colonnes du tableau brut + remplacer `intensity:0.9` (auto_detector l.380).


---

## Session 2026-09-06 (P2→P6 implémentées, testées en local)

### Fichiers
- `libs/vox_refonte.py` (P2-P4 + tableau brut + intensité réelle) — emote/vélocité/événement/lexical, dégradation gracieuse clips/audio/visuel.
- `libs/vox_premium.py` (P5) — arbitrage kimi-k3 : score reframing + verdict (ok/weak/skip).
- `auto_detector.py` — branchement intensité réelle → veto campagne → arbitrage premium.
- workflow — injecte `NVIDIA_NIM_API_KEY` + `NVIDIA_NIM_MODEL=moonshotai/kimi-k3`.

### Validation locale
- Syntaxe OK (3 fichiers).
- Fumée : fenêtre riche → intensity 0.9 ; fenêtre vide → 0.1 (le fameux 0.9 constant est MORT).
- Veto campagne : OF creator → rejet ; plateforme non listée → rejet ; hors cycle → warning.

### Reste à faire (validation réelle)
1er run workflow sur une VOD pour confirmer le bout-en-bout capteurs+premium (pas de side-effect déjà validé au niveau Modal).


---

## Session 2026-09-06 (capteurs audio+visuel ajoutés — P4 phase 2)

- `libs/audio_sensor.py` + `libs/visual_sensor.py` créés (gratuits, sans clé).
- Branchés dans `vox_refonte.build_raw_table` (colonnes audio_laugh/applause/visual_face/cut).
- `auto_detector.py` : `_audio_path` injecté avant le tableau brut.
- workflow : `opencv-python-headless` ajouté.

### Reste à faire
Capteur clips communautaires = **FAIT** (GraphQL public Twitch, zéro clé — `libs/clips_heatmap.py`).
Reste : run réel de validation bout-en-bout (Workflow GitHub Actions déjà câblé Modal+NVIDIA).


---

## Session 2026-09-06 (test réel + fixes critiques)

### Validation sans re-transcription
Utilisé `v2864600351_transcript.json` (déjà commité) + chat GraphQL live + clips live
pour valider le nouveau code — PAS de run complet (gaspillage de 240 Mo + 3h30 GPU).

### 3 fixes critiques
1. `fetch_chat_replay` : API v5 morte → GraphQL public (pagination offset Int). 2641 msg réels.
2. Ordre : capteurs AVANT scoring (l'intensité réelle est désormais consommée par score_candidates).
3. `campaign_veto` : status toujours posé (robustesse).

### Résultat
Intensité réelle différenciée : 7 valeurs distinctes sur 9 candidats (vs 0.9 constant avant).

### Rappel : run workflow annulé (évitait re-transcription inutile). Prochain run réel = nouvelle VOD.


---

## Session 2026-09-06 (GO Warsmith — refonte VOX validée)

### Décision
Gate Warsmith : **GO** sur la refonte VOX (intensité réelle multi-capteurs + veto + premium).

### Calibrage finale (post-GO)
- vélocité : saturation corrigée (soft saturation discriminante, plus de 1.0 uniforme).
- `spike_signal` ajouté (burstiness) pour distinguer débit régulier vs pic soudain.
- pondération finale : emo .30 · vel .15 · spike .15 · evt .20 · hook .20.

### Reste (production)
Run complet sur NOUVELLE VOD (les capteurs doivent SÉLECTIONNER les fenêtres, pas re-scorer les anciennes).


---

## Session 2026-09-07 (test réel bout-en-bout — le vrai test)

### Leçon
La validation hors-ligne (re-scorer l'archive) était une erreur : elle re-scorait des
fenêtres sélectionnées par l'ANCIEN code cassé (garbage in). Le VRAI test = détection
fraîche sur transcript + chat réel + clips réels → fenêtres neuves.

### Ce que le test réel a trouvé
- `score_candidates` : `tos_hits` non initialisé quand fenêtre SANS mots → UnboundLocalError.
  Corrigé (commit f57f43e). Cas jamais rencontré par l'archive.

### Bilan réel
10 candidats frais · 9 survivants · intensité 0.11–0.42 · 7/9 top_words · premium kimi-k3 OK (200).

### Reste
Injection `NVIDIA_NIM_API_KEY` DANS le workflow = **FAITE** (204, libsodium, aveugle) + vérifiée.
Premium prêt (test direct 200 OK).
Run complet sur NOUVELLE VOD = dernière validation de production.


---

## Session 2026-09-07 (PUR : skip F01 + adaptateur + F02)

### Doctrine PUR actée
- **F01_SCOUT = SKIP en Mode PUR** (redondant avec F00B_VOX qui a déjà ingéré/transcrit/scoré).
  F01 reste INTACT pour les modes YouTube classiques / MEME / LOGO / WHOP.
- **Adaptateur PUR** : `MONDES_FORGES/CLIPPING/pur_adapter.py` mappe `candidats.json` (VOX)
  → `source_specimen.json` compatible F02 (`reference_clip: null`, assets = candidats VOX).
- **F02_TYRANT_CAMP** = utilisé TEL QUEL (mode `--auto` + `--finalize`), car sa 3e lib
  `skeleton_extractor` gère déjà `reference_clip` vide (squelette neutre `iron_status pending`).

### Workflow
`.github/workflows/perturabo_f02_verdict.yml` : adaptateur → F02 --auto → F02 --finalize → commit.

### Reste
Lancer F02 pour produire le verdict GO/NO-GO PUR (Porte 1).


---

## Session 2026-09-07 (PUR : chemin direct VOX -> F04)

### Décision doctrine
En Mode PUR, le flux est **F00B_VOX → F04_COPYWRITER (direct)**. F01 (acquisition),
F02 (verdict/angles océan bleu) et F03 (sélection segment) sont **SKIP** : VOX a déjà
détecté + scoré + sélectionné. La viralité est gérée par VOX ; F04 écrit le copywriting.

### Livré
- `MONDES_FORGES/CLIPPING/pur_adapter_direct.py` : produit `angles.json` (F02_OUT) +
  `source_specimen_{angle_id}.json` (F03_OUT) à partir des candidats VOX. Angles PUR =
  famille `reframing` (hooks_pur), 1 angle/candidat, reframe_dim dérivé du signal.
- `.github/workflows/perturabo_f04_copywriting.yml` : adaptateur → F04 setup-context →
  generate premium (kimi-k3, provider other, base_url NVIDIA) → ordonnance → finalize → commit.
- `copywriter_secrets.json` écrit à la volée dans le workflow (gitignored, absent en CI).

### Reste
Lancer F04 pour produire le text_payload (3 titres + reframing + caption + hashtags).


---

## Session 2026-09-08 (contrat opérateur F04 : assets à la demande)

### Décision doctrine
Le Warsmith décide CE QUE F04 produit. Le workflow n'impose plus le pack
"ranking" par défaut. Deux modes d'assets, choisis à l'exécution :

- **overlay_only** (blur, split…) : UN titre overlay de 1-2 lignes par clip.
  C'est LUI qui donne le sens, rend le clip relevant et viral. Rien d'autre.
- **ranking** : 3 livrables par clip —
  1. titre overlay **max 4 mots** (règle ranking stricte, pas 2 lignes)
  2. **labels** : le titre pour chaque numéro de classement
  3. **titre métadonnée + description** (inspirée du modèle de la directive
     campagne) + **tags et hashtags issus des directives**

La voix est déjà sur le clip (on coupe une séquence) : F04 n'écrit JAMAIS
de script/narration, dans aucun mode.

Le nombre de vidéos finales (1-10) est aussi une décision opérateur : il
détermine le nombre d'angles/clip packs produits par l'adaptateur.

### Livré
- `pur_adapter_direct.py` : `--nb-videos N` (1-10, tronque les candidats VOX
  aux N premiers) + `--asset-mode ranking|blur|split|overlay_only`. L'asset_mode
  est propagé dans angles.json (niveau doc ET angle) + specimens.
- `F04_COPYWRITER/CODEBASE/copywriter.py` :
  - `--generate-overlay` (Phase B assets) : appel premium direct, sortie
    `OUT/overlay_raw_<angle>.json`. Prompt overlay_only (1-2 lignes) ou
    ranking (≤4 mots + labels + métadonnées) selon le contrat.
  - `--finalize-overlay` (Phase D assets) : validation IRON locale
    (overlay ≤4 mots si ranking, ≤2 lignes sinon — hérésie sinon) +
    `OUT/overlay_payload_<angle>.json` + `.md` lisible opérateur.
  - Contrat lu depuis `IN/operator_brief.json` ou flags CLI
    (`--asset-mode`, `--example-description`).
- `.github/workflows/perturabo_f04_copywriting.yml` : nouveaux inputs
  `nb_videos` (1-10), `asset_mode`, `example_description`. Écrit
  `IN/operator_brief.json` puis boucle setup-context → generate-overlay →
  finalize-overlay sur les N angles. Commit copie overlay_payload_* +
  text_payload_* vers ARCHIVUM/copywriting.

### Testé (local, sans réseau)
- Adaptateur : nb_videos=3 + asset_mode=blur -> 3 angles A01-A03 + 3 specimens.
- Dry-run premium : prompt overlay_only correct (schema 1-2 lignes).
- Finalize blur : overlay 5 mots accepté (libre). Finalize ranking : 5 mots
  refusé (hérésie), 4 mots accepté + payload ranking complet (labels,
  métadonnées, tags).

### Reste
- Pousser sur PERTURABO puis lancer le workflow avec le contrat opérateur
  (ex : nb_videos=5, asset_mode=blur).
- Iron Sentinel — Capteurs : dernier run en échec (ee109a83), à diagnostiquer.


## Session 2026-09-08 — Montage viral branché (F05/F06)

### Fait
- F04 copywriting lancé + validé (3 clips A01/A02/A03, overlay_only).
- Fix timeout NVIDIA (600s) + max_tokens 4096 + retry RemoteDisconnected + commit par clip.
- `director.py` RÉÉCRIT (v2.0.0-viral) : consomme la doctrine ARCHIVUM, zooms brutaux, smash/breath cut, SFX sync, anti-détection. Fini les défauts morts (zoom lent, #FF0000, 'Follow for more').
- `pur_montage_pipeline.py` : le pack contient TOUT (montage embarqué). Sorties `ARCHIVUM/montage/packs/`.
- Workflow `perturabo_montage.yml`.

### Reste
- Lancer le workflow montage (nb_videos=3, overlay_only) et valider les packs viraux.
- Si OK : envoyer les `production_pack_Axx.json` à OMNIS_WATCH pour le rendu vidéo.
- Brancher le reste (A04-A09) si les 3 premiers clips passent le gate.

## Session 2026-09-09 — Montage frame-près validé + EXPORT

### Fait
- Calage frame-près : cuts/zooms ancrés sur les word-timestamps du transcript (fini la grille fixe).
- Run montage vert (commit de sortie 69f3da0) : 3 packs calibrés commités dans `ARCHIVUM/montage/packs/`.
- Doublon `copywriting` corrigé dans `director.py` (supprimé du bloc montage_instructions, conservé au niveau racine du pack).
- Les 3 packs PUR (A01/A02/A03) copiés dans `EXPORT/` pour le gate Warsmith.
- Docs de suivi mises à jour.

### Reste
- Gate Warsmith sur les packs EXPORT.
- Si OK : lancer OMNIS_WATCH (rendu vidéo) depuis `EXPORT/`.
- Brancher les candidats restants A04–A09 (VOX en a 9).

## Session 2026-09-09 — Branche `v2-live` (le live en temps réel)

### Décisions (figées, voir README_V2.md)
- Copie exacte de main (base `8ee8c8b`) ; SEULE divergence : la couche live de VOX.
- Radar GH Actions (`workflow_dispatch`, multi-chaînes, 6h max) + Oracle cron 5 min (issues `[ORACLE][chaîne]`).
- Gate hybride : auto-approbation (score ≥ 8.5 + intensité ≥ 0.9), file d'attente pour le reste.
- Clips Helix captés en direct (secrets TWITCH_TOKEN/TWITCH_CLIENT_ID) ; sans token : timestamps seuls.
- Board GitHub Pages : `docs/index.html` lit `docs/data/live_status.json` (poussé toutes les 3 min).

### Livré (branche v2-live)
- `F00B_VOX/CODEBASE/libs/chat_pulse.py` : radar IRC Twitch anonyme (100% stdlib), baseline EMA 5 min, mots chauds, clip pressure, cooldown 120s/chaîne.
- `F00B_VOX/CODEBASE/libs/helix_clipper.py` : Helix minimal (stream info + create_clip), stdlib urllib.
- `F00B_VOX/CODEBASE/f00b_vox_live.py` : orchestrateur de session — scoring VOX réutilisé tel quel, gate hybride, OUT au même schéma que VOD (`trail.json` compatible F04/F06).
- `.github/workflows/perturabo_live_radar.yml` + `perturabo_oracle_watch.yml`.
- `docs/index.html` (thème Iron Warriors, fallback inline pour test local).
- Docs : `README_V2.md` (racine v2-live, checklist hebdo token CUT), guide `18_MODE_LIVE_V2.md`, logs à jour.

### Reste (avant premier vrai live)
- Secrets GH : `TWITCH_TOKEN` (scope clips:edit) + `TWITCH_CLIENT_ID`.
- Activer GitHub Pages (branche v2-live) pour le board.
- Session de calibration sur un live réel (seuils min_rate/spike_factor).
- main ne bouge pas : toute correction F04/F06 se fait sur main puis se re-pousse sur v2-live.

## Session 2026-09-10 — v2-live : les 3 premières chasses + le Garde de Fer

### Sessions radar (artefacts analysés)
| # | Chaîne | Résultat |
|---|---|---|
| 1 | e11ysa (60 min) | Pipeline OK, 0 msg — bug SSL `chat_pulse.py` corrigé (preuve : 47 msgs/30s en test) |
| 2 | fps_shaka (45 min) | Tuée par le step refresh (`invalid client secret`) → refresh rendu NON bloquant (fallback token statique) |
| 3 | fps_shaka (45 min) | ✅ 10 moments → 10 scorés → 10 auto-approuvés ; 0 clip Helix (`HTTP 500` — clipper expose maintenant le corps d'erreur, `has_delay=false` conforme doc) |

### Garde de Fer (règles de campagne câblées)
- `ARCHIVUM/campaign/live_campaigns.json` : registry machine chaîne → campagne (cycle inclus).
- `F00B_VOX/CODEBASE/libs/campaign_gate.py` : resolve_channels / session_mode / campaign_fields — stdlib, tolérant aux pannes (registry absente → technical_test, jamais de crash).
- `f00b_vox_live.py` : résolution au lancement (refus des sessions **mixtes**), chaque verdict porte `campaign_eligible` + `campaign_id` + `campaign_state`, propagés vers `gate_live.json`, `live_status.json` et le board.
- Workflow radar : input `mode_override` (auto / technical_test / campaign).
- Board : badge 🎯 CAMPAGNE (soumissible) vs 🧪 TEST TECHNIQUE (non soumissible) + raison par chaîne.
- Docs : README_V2 (point 6 fait, journal des sessions), guide 18 (règle 1 automatique + section 7bis).

### Reste (toujours ouvert)
- `TWITCH_CLIENT_SECRET` invalide côté GH → refresh en échec depuis la session #2 (action opérateur).
- Premier clip serveur Helix à conquérir (le 500 Twitch sera diagnostiqué à la session #4 grâce aux erreurs détaillées).
- Cycle Sofey expiré (07/31) → renouveler la directive Whop pour une session réelle.

## Session 2026-09-10 (2) — Scoring calibré + Salle de Contrôle du Siège

### Scoring live calibré (`compute_score_live`)
- Fin du profil fixe ~9.88 : chaque critère VOX alimenté par la force réelle du pic
  (ratio rate/baseline, hystérie des mots chauds www*/KEKW…, clip_pressure, durée).
- Bonus/malus en miroir exact du moteur VOD (`vox.compute_score`) — main intact.
- Intensité honnête : ratio ×6 → 1.0, ×3 → 0.5, ×1.5 → 0.25.
- Preuve sur les 10 moments de la session #3 : écart 0.0 → 3.25 (9.75 à ×5.56,
  6.5 pour les pics faibles). Seuls les gros pics passent l'auto-approbation 8.5.
- Fix au passage : `write_status()` recevait `cfg` sans le déclarer ( aurait crashé
  la session #4 au premier tick) — corrigé, `cfg` passé aux 2 appels.

### Board « Salle de Contrôle du Siège » (`docs/index.html` réécrit)
- Palette Iron Warriors : Boltgun Metal/Leadbelcher (aciers), Shining Gold/Nazdreg
  (trim), noir (épaules), bandes hazard jaune/noir, logo ⟨/⟩ en SVG inline doré.
- Panneaux : 🗺 Carte du siège (SVG, secteur par chaîne, muraille pulsante selon la
  pression du chat) · 🎯 Scoreur en direct (jauge or 0→10, détail des 6 critères,
  tampons APPROUVÉ/EN FILE/REJETÉ, marqueur NON SOUMISSIBLE) · 📜 Manifeste des
  clips (liens Helix cliables / « timestamps seuls ») · 🚪 Ordres en attente (file
  Warsmith) · 📡 Télémétrie (lampes phosphore, ×baseline).
- Données : `live_status.json` publie désormais `recent_scored` (détail des critères)
  et `clips` (IDs + URLs Helix) à chaque tick ; le board se recharge toutes les 60 s.
- Validation : 15/15 vérifications statiques + rendu testé contre les données réelles
  de la session #3 re-scored (1 auto-approuvé, 9 en file, 1 clip simulé).

## Session 2026-09-15 — Verrou doctrine des gates + F06 soumis à F00D

- **Doctrine des gates rétablie** (audit opérateur) : un gate après CHAQUE frégate.
  Chaîne corrigée : F00C → gate → F00D → gate → F04 → gate → F06 (soumis) →
  gate → F05 (pack final embarquant montage_instructions) → gate → EXPORT.
  F06 s'exécute AVANT F05 ; le bras armé lit le bloc montage_instructions du pack.
- **Rétro-tag DRAFT** : les 6 manifestes caviar + le pack EXPORT voxc-2 marqués
  DRAFT (commit 6487da7) — F04/F06/F05 n'avaient pas tourné.
- **F04 PUR exécuté pour de vrai sur voxc-2** (kimi-k3/NVIDIA, clé Warsmith) :
  contamination archivum purgée (payloads Aishah/Joe + verdict perimés en
  _archive_TS01_AISHAH_SOFEY), liber frais SOPHIE_RAIN_CLIPIFY_US_2026,
  transcript réel voxc-2 injecté dans le specimen A01 → overlay GO opérateur
  « She makes MORE than LeBron James? / Top 0.1% OF earner speaks out » (83daf91).
- **F06 v3.0.0-caviar-bound** : F00D commande (cuts/zooms/SFX/mirror/speed/crop/
  panneaux/duck), F06 exécute le reste (texte, courbe sur climax, anti-détection
  complémentaire, compliance) + caviar_binding + erreur blur-sans-caviar.
  13 tests verts.
- **Prochaine étape** : GATE opérateur sur l'output F06 voxc-2, puis F05
  (pack final), puis gate, puis EXPORT.

## [2026-09-20] Session Aishah Sofey — Gate F04 fermé → phase métadonnées

- **Verdict Warsmith enregistré** (`F00B_VOX/IN/gate_f04_verdict.json`) :
  5/5 titres overlay ACCEPTED + émotions F00D `intrigue` ×5, propagées dans
  les 5 manifestes caviar (panneaux blur compris).
- **Phase MÉTADONNÉES exécutée** (kimi-k3, directive campagne intégrée) :
  `F04_COPYWRITER/OUT/metadata_payload_asf_c{1..5}.json` — titres ≤ 66c,
  descriptions avec `@hiaishahsofey` + `#aishahsofey`, 5-8 tags, 3 strates
  hashtags, zéro OF/subscribe, anti-cond PASS sur le transcript réel.
- **Page gate F04 étendue** (Section C métadonnées) : `docs/gate_f04_v2873615032.html`
  — l'export inclut désormais `accepted_metadata`.
- **Prochain** : verdict métadonnées de l'opérateur → F06 (montage blur) →
  gate → F05 (pack) → EXPORT.

## [2026-09-20] F06 exécuté — GATE F06 ouvert
- 5 instructions de montage `caviar_bound` forgées (F06_DIRECTOR) à partir des gates
  F00B (fenêtres) + F04 (overlay GO 5/5 + émotions intrigue) + partitions F00D sha-liées.
- Fix doctrine F06 : segment.emotion = émotion gate-validée (plus de None en caviar_bound).
- Tests 13/13 verts. Gate F06 présenté à l'opérateur ; F05 après GO.

## [2026-09-21] F05 exécuté — GATE F05 ouvert
- 5 production packs blur assemblés (F05_PACKAGER/OUT) au schéma voxc-2, custody 4 gates, intégrité PASS.
- Gate F05 = revue du pack complet (overlay + métadonnées + montage + partition) avant EXPORT.

## [2026-09-21] GATE F05 GO — EXPORT — SESSION CLÔTURÉE ✅
- Verdict F05 : 5/5 GO (gate_f05_verdict.json). Packs marqués VALIDATED / ALL_GATES_GO.
- 5 production packs + packager_summary exportés dans MONDES_FORGES/CLIPPING/EXPORT/.
- Chaîne complète exécutée : F00B (matrice) → F00D (blur) → F04 (overlay+métadonnées) → F06 (caviar_bound) → F05 (packs) → EXPORT. Gate opérateur à chaque frégate.
- Infra : `.nojekyll` ajouté (le build Jekyll Pages cassait sur les nouveaux contenus ; le site est 100 % statique).
- Prochaine session possible : nouvelle VOD via le workflow matrice (l'oracle est auto-déclenché), ou branche clipify pour l'expédition des packs.

## [2026-10-16] CERVEAU PARTAGÉ — premium → oracle → off

- **Module unique** `MONDES_FORGES/CLIPPING/SHARED/brain.py` : tout appel IA du
  tronc CLIPPING passe par `ask()`. Résolution automatique `premium`
  (NVIDIA NIM kimi-k3 / `CLIPPING_*`) → `oracle` (passerelle `AI_GATEWAY_*`) →
  `off`. Stdlib `urllib` uniquement, jamais de clé loggée/renvoyée.
- **Frégates branchées** :
  - F00B `libs/vox_premium.py` (score de reframing + arbitrage) ;
  - F00C `f00c_vox.py` (bloc `brain` du manifeste, `--transcript`, `--no-brain`) ;
  - F04 `libs/premium_client.py` (`chat` premium → repli oracle, `last_mode`).
- **Motif** : run `38831207071` échoué `Payment Required: Insufficient credits`.
  Une clé premium qui tombe ne bloque plus le pipeline.
- **Contrats** : `CONTRACTS/premium_bus_schema.json` (public) ; exemples F00B et
  copywriter annotés (le fichier réel reste gitignored).
- **Workflows** : `perturabo_transcribe_matrix.yml` (scoring global) et
  `perturabo_vox_c_analysis.yml` reçoivent `NVIDIA_NIM_*` + `AI_GATEWAY_*`.
- **Doctrine** : `GUIDE_UTILISATION/22_MODE_CERVEAU_PARTAGE.md`.
- **Diagnostic** : `python3 .../SHARED/brain.py` (mode dispo) et `--ping`
  (test de raisonnement réel).
- **Prochaine étape** : fournir les secrets `AI_GATEWAY_*` au repo, puis lancer
  le workflow matrice — le repli oracle doit prendre le relais si le premium
  refuse (402).
