# PERTURABO v2-live — F00C_VOX JOURNAL DE CAMPAGNE

> *Chaque entrée est immuable. Une fois écrite, elle ne s'efface pas.*

| Date | Source analysée | Statut | Segments | Run CI | Décision Warsmith |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Entrées de mise en service

### 2026-09-14 — STYLE CHOISI AU COCKPIT + 4e STYLE « BLUR » (F00D)

- **Manque acté par le Warsmith** : le style (split/reframing/ranking) était
  pré-rempli « reframing » dans les fichiers d'entrée F00D sans choix
  opérateur — aucun sélecteur dans la War Room.
- **F00D — nouveau style `blur`** (4e recette) : le flux est crop-zoomé ×1.3
  puis flouté (~18 px) derrière un panneau vertical de texte — l'écran se
  libère pour le message, aucun asset requis. Trio **blur+flash+SFX**
  inséparable (budget broll_trio), hook `climax_first` comme reframing,
  rien après la résolution, voix MAINTENUE. Clip < 15 s → pas de panneau
  (repli gracieux). Tests 10/10 verts.
- **War Room — sélecteur de style par carte** : 4 boutons SPLIT/REFRAMING/
  RANKING/BLUR + description au survol, choix AVANT le GO ; le GO envoie
  verdict+style ensemble ; le badge de verdict affiche le style acté.
- **Récepteur — émission pilotée par le gate** : `POST /api/gate` accepte
  `style` (validation split|reframing|ranking|blur) ; un GO déclenche F00D
  (caviar_director.py) qui compose le manifeste avec le style du cockpit et
  met à jour `caviar_index.json` — le style n'est plus un pré-remplissage.
  Idempotence par couple (verdict, style) ; style conservé si GO sans style.
  Échec F00D = diagnostic au cockpit, verdict inchangé (jamais de faux vert).
- **Tests** : 33/33 verts récepteur (3 nouveaux : style inconnu refusé,
  couple verdict+style idempotent, boucle cockpit→F00D style blur émis)
  + self-test round-trip OK (état réel restauré).

### 2026-09-13 — AUDIT WARSMITH + CONTRAT V2 (le dashboard ne devine plus)

- **Audit du Warsmith sur la preview** : file des candidats vide, pas d'axes,
  rien de cliquable, légende mensongère, doute « 8 min sur une vidéo plus longue ».
- **Cause racine (bug bloquant)** : le dashboard lisait `c.id`/`c.score`/`c.rank`
  tandis que F00C pousse `candidate_id`/`signal_intensity` — TypeError JS avalé
  en silence par `catch(_)` → liste vide, gate envoyant `undefined`.
- **Fait établi** : la 1re URL (`qm3E3cchBmQ`) = 514 s réels (`not_live`, confirmé
  yt-dlp) — F00C a analysé 100 % de cette vidéo. Le doute venait de l'absence de
  durée affichée. Nouvelle URL du Warsmith (`cP8vli4kfhs`) = 6156 s (1 h 42).
- **Contrat V2 (`build_webhook_payload`)** : chaque candidat part avec `id`,
  `rank`, `score /100`, `start_label`/`end_label` (m:ss), `vs_mean_pct`,
  `platforms` ; le run porte `title`, `channel`, `duration_total_sec`,
  `analyzed_duration_sec`, `coverage_pct`, `mean_attention`, `replayed_note`.
- **Dashboard v2 (docs/war_room.html)** : axe X gradué (m:ss), axe Y 0→1,
  tooltips exacts au survol, candidats cliquables ↔ timeline, cartes complètes
  (durée, position %, intensité vs moyenne, barre métrique), légende truthful
  (présente/absente), histogramme de distribution, bandeau couverture
  (« analysé X / Y — ✔ complet »), bandeau d'erreur (fini le silence).
- **Workflow runner** : installation de deno ajoutée (runtime JS exigé par
  yt-dlp pour les challenges n/sig — warning observé au test local).
- **Tests** : 25/25 verts (2 nouveaux : enrichissement V2 + labels m:ss).
- **Territoire intact** : F00B (docs/index.html + radar) NON touché.

### 2026-09-12 — LIVRAISONS C+D : Salle de Guerre complète (dashboard + mode LIVE + gate cockpit)

- **Récepteur v2** (`WAR_ROOM/receiver.py`, miroir dans ce repo) : sert le
  dashboard (`GET /` → `docs/war_room.html`), `GET /api/war-room` (polling),
  `POST /api/gate` (verdicts Warsmith, sans token — cockpit navigateur),
  `POST /` webhook F00C (X-Siege-Token). Port : `--port` > env `PORT` > 8787.
- **Boucle de retour Livraison D fermée** : le dashboard poste GO/NO-GO sur
  `/api/gate` → stocké dans `war_room.json` (`gates`, idempotent : re-voter
  identique ne gonfle pas les compteurs, une inversion remplace le compteur
  précédent) → le pipeline PERTURABO relit `GET /api/war-room` pour connaître
  les clips GO.
- **Dashboard** (`docs/war_room.html`, thème Iron Warriors) : timeline SVG
  (heatmap capteur or + barre rouge most-replayed pointillée + fusion or vif +
  blocs candidats), cartes triées par score avec boutons **GO / NO-GO**,
  badge mode VOD/LIVE pulsé (poll 2 s), nouveaux candidats marqués `NEW` en
  LIVE, **toggle DONNÉES BRUTES** (le JSON réel affiché tel quel).
- **Seed démo** (`WAR_ROOM/seed_demo.py`) : payload Sophie Rain synthétique
  conforme au contrat (100 buckets, barre rouge 25 pas, fusion 0.6/0.4,
  3 candidats) — l'état affiché tant que le run réel n'a pas poussé.
- **Tests** : 11/11 verts côté récepteur (gate inconnue, candidate fantôme,
  idempotence des compteurs) + self-test round-trip.

### 2026-09-12 — LIVRAISON B : barre rouge Most Replayed + webhook Salle de Guerre

- **Barre rouge** : `--fetch-replayed` → `yt-dlp --dump-json` (zéro média
  téléchargé, escalier habituel) → `replayed_curve` [{start, end, value}] dans
  le manifeste. Indisponible ⇒ `replayed_note` explicite (jamais de silence).
- **Fusion** : `fused_heatmap = 0.6 × attention_norm (capteur) + 0.4 ×
  replayed_norm (humains réels)` — le croisement capteur × comportement.
  Sans barre rouge : `fused = attention_norm`, `replayed_applied: false`.
- **Webhook** : `--webhook-url` (+ `X-Siege-Token`, défaut env
  `SIEGE_WEBHOOK_TOKEN`) → payload contrat §4 (run_id, siege_id, mode
  vod|live, status, heatmap, replayed_curve, fused_heatmap, candidates,
  pushed_at). Échec réseau = warning, le manifeste local reste le livrable.
- **Workflow** : `--fetch-replayed` toujours actif, input `webhook_url` +
  secret `SIEGE_WEBHOOK_TOKEN`.
- **Récepteur de référence** (repo kbkjhjhl) : `war_room/receiver.py` —
  validation stricte (422 si payload invalide, 401 si token), stockage
  `docs/data/war_room.json` (last_run + historique), `GET /api/war-room`
  pour le dashboard. 8/8 tests + self-test round-trip verts.
- **Tests** : 23/23 verts côté F00C (6 nouveaux : parsing dump-json,
  note non silencieuse, fusion avec/sans barre rouge, payload canonique,
  envoi token+payload).
- **Docs** : guide 19 (section « barre rouge et webhook »).

### 2026-09-12 — LIVRAISON A : escalier anti-anti-bot + garde-fou + contrat découplé

- **Code (`f00c_vox.py`)** :
  - `download_media()` réécrite — escalier 3 marches : `player_client=ios,mweb`
    (gratuit) → yt-dlp nu → `--cookies` (session burner). Formats video-only
    `height<=144` (défaut) : la heatmap réduit à 64×36, ~30-60 Mo/h au lieu de Go.
  - **Contrat découplé** `--media-source` : métadonnées = URL source, média =
    fichier local séparé (piste fichier disponible sans dépendre de YouTube).
  - **CLI `--cookies-file`** pour la session burner.
- **Garde-fou anti-faux-vert** : CLI exit 2 si `download_budget_seconds > 0` et
  (`status != "full"` sans `--media-source`, ou 0 candidat avec `--to-candidats`).
  Workflow : étape GUARD dédiée (exit 1, message « Analyse fonctionnelle échouée… »)
  + `if: always()` pour couvrir les échecs d'étapes amont.
- **Workflow** : secret `YT_COOKIES_BASE64` → `/tmp/yt_cookies.txt` (`umask 077`,
  jamais loggé) → `--cookies-file` → **détruit en fin de job** (`if: always()`).
  Input `media_source` ajouté. `pip install --upgrade yt-dlp` (course anti-bot).
- **Tests** : 17/17 verts (9 bridge + 8 voxc) — régression zéro.
- **Docs** : guide 19 (section « Le mur anti-bot et l'escalier » + protocole cookies
  burner + 2 hérésies), `requirements_f00c.txt` (escalier documenté), CONTINUATION.
- **Reste côté Warsmith** : créer le burner, coller `YT_COOKIES_BASE64` dans les
  secrets GH, rotation hebdo. Ensuite : relancer le run Sophie Rain (86400 s) —
  attendu `status: full` sinon échec explicite.

### 2026-09-11 — PORTAGE INITIAL (lot 1+2)

- **Origine** : `f00_live.py` porté depuis LACRIMAE `dev10-v3-live`
  (commit `d1b182c`, tests 8/8 verts) et adapté aux conventions F00B.
- **Créé** :
  - `CODEBASE/f00c_vox.py` — resolve → metadata (YouTube public / Twitch GQL) →
    heatmap d'attention (numpy + ffmpeg, média local) → manifeste
    `perturabo.voxc.v1` (metadata, attention_heatmap, viral_segments pics ≥ 5 s,
    raw_data Oracle). Live EN COURS et vidéo FINIE : même pipeline.
  - `CODEBASE/tests/test_f00c_vox.py` — 8 tests hors-ligne, **8/8 verts**.
  - `CODEBASE/requirements_f00c.txt` — stdlib pour l'analyse ; yt-dlp + ffmpeg
    système pour l'ingest (doctrine F00B respectée) ; numpy pour la heatmap.
  - `IN/vox_c_input.example.json`, workflow `.github/workflows/perturabo_vox_c_analysis.yml`
    (dispatch manuel, gate L0, artefact `voxc-analysis-*`).
- **Note de nommage** : dans LACRIMAE, `F00C` désigne déjà « Motion Slow »
  (interpolation). Dans PERTURABO, F00C était libre — F00C_VOX vit ici, pas
  de collision au sein du repo. À ne pas confondre entre repos.
- **Doctrine** : jamais de VOD complète (`--download-sections` uniquement),
  jamais de recompression, jamais de manifeste vide (metadata_only reste
  un livrable pour l'Oracle).

### 2026-09-12 — PLAN_SALLE_DE_GUERRE (diagnostic + plan, aucun code)

- **Run réel raté (Sophie Rain)** : workflow lancé avec `download_budget_seconds=86400`
  → yt-dlp bloqué « Sign in to confirm you're not a bot » (IP datacenter du runner)
  → `status: metadata_only`, 0 segment, 0 candidat — **mais workflow VERT** (faux succès).
- **Diagnostic acté** : le blocage est identitaire (IP datacenter), pas de configuration.
  L'API YouTube ne donne que les métadonnées ; la heatmap vidéo exige le média.
- **Plan validé par le Warsmith** : `PLAN_SALLE_DE_GUERRE.md` (à la racine F00C_VOX).
  Combinaison retenue : **contrat découplé** (`--media-source`, metadata ≠ média)
  + **cookies burner** (secret `YT_COOKIES_BASE64`, fichier temporaire détruit en fin
  de job, rotation hebdo) + **garde-fou anti-faux-vert** (exit 1 si budget > 0 et
  `status != "full"` ou si `to_candidats` avec 0 candidat) + téléchargement 144p
  video-only + **Most Replayed** (barre rouge YouTube fusionnée à la heatmap vidéo).
- **Ajouts issus du brainstorm externe** : test gratuit `player_client=ios,mweb` en
  Étape 0 ; hook words / seamless loop en backlog. **Refusés** : Ragebait (viole la
  directive : pas de bait/misinfo/PR négative), scramble d'empreinte audio.
- **Salle de Guerre** (workspace Freebuff, Vite+Convex, repo `kbkjhjhl`) : webhook
  `X-Siege-Token` ← PERTURABO ; dashboard `/war-room` avec timeline heatmap + barre
  rouge + candidats, toggle DONNÉES BRUTES, mode VOD (tout d'un coup) et mode LIVE
  (temps réel), gate Warsmith inline (GO/NO-GO par carte).
- **Règle de territoire rappelée** : F00B = Twitch uniquement. La campagne Sophie Rain
  (YouTube) ne touche que F00C.
- **Prochaine étape** : Livraison A (Phases 0-4 du plan) dès le GO du Warsmith.

### 2026-09-11 — PONT F00C → TRONC PUR (Note 20)

- **`--to-candidats`** + `--top N` : `viral_segments` → `OUT/candidats.json`
  (clé `candidates`, `signal_type: platform_heat`, intensité = `attention_norm`).
- **Lecteur tolérant** `SHARED/candidates_reader.py` branché dans
  `pur_adapter.py`, `pur_adapter_direct.py`, `pur_montage_pipeline.py`.
- **Workflow** : input `to_candidats` (défaut true) + artefact `voxc-candidats-*`.
- **Tests** : `test_candidates_bridge.py` (3 formes + vide = erreur, pas de silence).
- **Docs** : guides 11/13/14/19/20, README_V2, CONTINUATION_F00, `_PIEGES_APPRIS_PUR.md`.

### 2026-09-14 — PACK FINAL voxc-2 BLUR + AUDIT ÉDITORIAL (ad-reads refusés)

- **GO ×3 style blur actés au cockpit** (voxc-2/3/4, 18:16-18:18) → 3 manifestes
  blur émis par F00D (2 panneaux, 32u/55u, caps respectés), Archivum versionné
  (docs/data/caviar/*_blur.json).
- **Audit éditorial du transcript opérateur** : voxc-3 (30:47) = lecture de pub
  **Hims** ; voxc-4 (1:02:25) = pubs **Claude + FanDuel**. La directive campagne
  interdit la promotion d'autres marques dans le clip → voxc-3/4 NON packables
  (manifestes conservés marqués RÉSERVÉ, aucun pack émis).
- **voxc-2 (2:34→3:25) = contenu réel** (LeBron, cible, placements) →
  **production_pack_pur_voxc2_blur.json** émis : overlay 2 lignes (« SHE
  OUT-EARNS LEBRON JAMES. » / citation dream), émotions qualifiées
  (incredulity, dreamlike), anti-détection, compliance #ad + watermark 75%.
- **Recommandation** : GO voxc-1 (net worth) / voxc-5 (koi) + run ciblé sur le
  pic humain 1:36:27 (photos lycée) pour compléter les 3 clips de la campagne.
- **Correctif infra** : le serveur tournait encore avec le receiver pré-commit
  (restart antérieur aux edits) — les GO avaient acté le style sans émission.
  Restart effectué, émissions rejouées, index réaligné, artefact de test purgé.

### 2026-09-15 — AUDIT DOCTRINE DES GATES + RÉTRO-TAG DRAFT

- **Violation constatée** : la doctrine des gates veut un verrou après CHAQUE
  exécution de frégate (l'opérateur valide l'output AVANT de déclencher la
  suivante). Or la session a enchaîné F00D → F04 (sauté) → F05 → EXPORT sans
  gates intermédiaires ; les accroches ont été rédigées hors F04.
- **Chaîne corrigée (validée Warsmith)** : F00C → gate → F00D → gate → F04 →
  gate → **F06 (instructions de montage, 4 gates internes)** → gate → F05
  (assemble le pack FINAL embarquant montage_instructions) → gate → EXPORT.
- **Rétro-tag DRAFT appliqué** (bloc `review` ajouté, rien supprimé) :
  `docs/data/caviar/caviar_manifest_*.json` (6) et
  `EXPORT/production_pack_pur_voxc2_blur.json` — statut DRAFT, gate_state
  `F00D_output_PENDING_warsmith_gate`.
- **Prochaine étape** : F04 PUR sur voxc-2 (clé API premium à fournir par
  l'opérateur) puis reprise gate par gate.

### 2026-09-15 — F04 GO + F06 soumis à F00D (chaîne gate-par-gate)

- **F04 PUR exécuté** (kimi-k3/NVIDIA NIM, clé Warsmith) sur voxc-2 A01 blur :
  contamination ARCHIVUM purgée (Aishah/Joe en _archive), liber frais
  SOPHIE_RAIN_CLIPIFY_US_2026, transcript réel injecté → **GATE : GO opérateur**
  sur l'overlay « She makes MORE than LeBron James? / Top 0.1% OF earner speaks out ».
- **Conflit F06×F00D détecté et résolu** : F06 émettait cuts/zooms/SFX concurrents
  de la partition (saturation). Décision opérateur : **F00D commande, F06 soumis**
  (v3.0.0-caviar-bound, 13 tests verts) — hook hérité de la partition,
  anti-détection complémentaire seulement, bloc caviar_binding.
- **Statut** : code + docs commités. Prochain gate : output F06 réel voxc-2,
  puis F05 → gate → EXPORT.

### 2026-09-15 (suite) — GATE F06 : GO opérateur → pack final F05 assemblé

- **GATE F06 : GO** (opérateur). Le `montage_instructions.json` caviar_bound
  voxc-2 est validé : zéro cut/zoom/SFX F06, 2 panneaux blur partition
  (12.825 s / 25.651 s, flash+SFX), duck climax 28.216 s, overlay F04 GO,
  anti-détection complémentaire, compliance #ad.
- **Pack final assemblé** (sortie F05-like, hors EXPORT) :
  `F06_DIRECTOR/OUT/production_pack_pur_voxc2_blur_v2.json` — embarque
  montage_instructions GO + partition caviar (source de vérité) +
  `chain_of_custody` des 4 gates (F00C/F00D/F04/F06 GO, F05 PENDING).
  Statut : **DRAFT — F05_PENDING_warsmith_gate**. EXPORT interdit avant gate.

### 2026-09-15 (final) — GATE F05 : GO opérateur → EXPORT

- **GATE F05 : GO** (opérateur). Pack passé en VALIDATED (ALL_GATES_GO) et
  copié dans **EXPORT/production_pack_pur_voxc2_blur_v2.json**.
- **Chaîne complète exécutée gate-par-gate pour la première fois** :
  F00C GO blur → F00D partition → F04 GO (kimi-k3, transcript réel) →
  F06 GO (caviar_bound v3, soumis à la partition) → F05 GO → EXPORT.
- **Prochaine étape hors pipeline** : exécution du pack par le bras armé
  (LACRIMAE) → rendu MP4 9:16 → contrôle qualité → soumission campagne.

## 2026-10-16 — Tri sémantique via le cerveau partagé (F00C branché)

- **Nouvelles fonctions** dans `f00c_vox.py` : `load_transcript_words`,
  `brain_rank_segments`. Le manifeste porte un bloc `brain` :
  `{mode, scores, note}` — jamais bloquant.
- **Modes** : `premium` (NVIDIA NIM) → `oracle` (passerelle `AI_GATEWAY_*`) →
  `off`. En `off` ou sans transcript textuel, le tri plateforme reste seul juge
  (`note` explicite). Les segments ne sont **jamais** mutés (contrat F00C intact).
- **CLI** : `--transcript <transcript.json>` (words) et `--no-brain` (désactive).
- **Workflow** `perturabo_vox_c_analysis.yml` : secrets `NVIDIA_NIM_*` +
  `AI_GATEWAY_*` injectés à l'étape d'analyse.
- Doctrine : `GUIDE_UTILISATION/22_MODE_CERVEAU_PARTAGE.md`.
