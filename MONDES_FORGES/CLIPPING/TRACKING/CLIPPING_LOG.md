# TRACKING/CLIPPING_LOG — Monde Forge CLIPPING

> *Journal général de déploiement du forge. Une entrée par jalon.*
> *Pour le détail par frégate, voir `<FREGATE>/TRACKING/<XX>_LOG.md`.*

---

## [INIT] Monde Forge CLIPPING déployé — Arborescence + docs tracking

### Contexte
Le forge CLIPPING est le 3e Monde Forge de PERTURABO, après `API/` (générique) et `YOUTUBE/` (spécialisé shorts YouTube). Il se concentre sur le **clipping Whop Content Rewards** : produire les **stratégies + textes** (pas les vidéos) consommées par OMNIS_WATCH (projet externe, branche `dev1`).

### Arborescence créée
```
MONDES_FORGES/CLIPPING/
├── README.md                  ← vue d'ensemble du forge
├── CONTRACTS/                 ← see CONTRACTS/INDEX.md
├── ARCHIVUM/                  ← 10 zones (rules, campaign, platform_gen,
│                                 market_gen, knowledge_base, copywriting,
│                                 angles, demons, channels, learnings,
│                                 ledgers, templates)
├── SHARED/                    ← IN/ + OUT/ partagés
├── F01_SCOUT/                 ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F02_TYRANT_CAMP/           ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F03_SOURCE_HUNTER/         ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F04_COPYWRITER/            ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F05_PACKAGER/              ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F06_TRACKER/               ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── TYRANT/                    ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── F00_CAPTEURS/              ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── ORCHESTRATOR/              ← CODEBASE/ + IN/ + OUT/ + TRACKING/
├── TRACKING/                  ← ce dossier
└── MANIFEST.md                ← manifeste de livraison (fichiers + statuts)
```

### Conventions alignées sur YOUTUBE/
Chaque frégate suit la structure `CODEBASE/` (code Python — pas rempli pour l'instant), `IN/` (inputs), `OUT/` (artefacts produits), `TRACKING/` (journal de déploiement). Voir `MONDES_FORGES/YOUTUBE/` pour la référence.

### Statut des composants

| Composant | Arborescence | Docs Tracking | Code Python | Notes |
|---|---|---|---|---|
| F01_SCOUT | ✅ | ✅ | ❌ | À implémenter par autre model |
| F02_TYRANT_CAMP | ✅ | ✅ | ❌ | À implémenter |
| F03_SOURCE_HUNTER | ✅ | ✅ | ❌ | À implémenter |
| F04_COPYWRITER | ✅ | ✅ | ❌ | Frégate lourde — pattern 4 phases distinct |
| F05_PACKAGER | ✅ | ✅ | ❌ | À implémenter |
| F06_TRACKER | ✅ | ✅ | ❌ | À implémenter |
| TYRANT | ✅ | ✅ | ❌ | 2 modes (réactif + prospectif) |
| F00_CAPTEURS | ✅ | ✅ | ❌ | Commandité Warsmith, pas auto |
| ORCHESTRATOR | ✅ | ✅ | ❌ | 4 Portes, pattern hybride |
| CONTRACTS | ✅ | ✅ (squelettes) | n/a | copywriting_doctrine à remplir par le Warsmith |
| ARCHIVUM (10 zones) | ✅ | ✅ (squelettes) | n/a | Contenu secret à remplir par le Warsmith |

### Prochaines étapes
1. Le Warsmith remplit `CONTRACTS/copywriting_doctrine.md` (son savoir secret — slang, subliminal, formulas)
2. Le Warsmith peuple `ARCHIVUM/copywriting/` (8 sous-dossiers) avec son musée
3. Un autre model implémente le code Python des frégates en suivant religieusement chaque `TRACKING.md`
4. Le Warsmith révoque le token GitHub exposé (cf. note sécurité)

### Note sécurité
⚠️ Un token GitHub a été partagé en clair pendant la session. **Il doit être révoqué** immédiatement après cette session — il est publiquement compromis. Ce token a été utilisé **temporairement** pour cloner/pusher le forge. Ne pas réutiliser.

---

## [DEV-ORCHESTRATOR] Nerf central implémenté — ORCHESTRATOR + IW_CUSTOS

### Contexte
Première vague de code Python du forge CLIPPING. Le nerf central est en place : le ledger (`liber_clipping.json`), le gardien (`IW_CUSTOS.py`) et l'Orchestrateur (4 Portes).

### Fichiers livrés
```
CLIPPING/
├── IW_CUSTOS.py                    ← gardien du ledger (check-out/check-in/validate/status)
├── liber_clipping.json             ← état inter-frégates (singulier, 1 siège actif max)
└── ORCHESTRATOR/CODEBASE/
    ├── orchestrator.py             ← CLI : --start-siege / --gate N / --resume / --status / --close-siege
    ├── gates.py                    ← les 4 Portes (verdict, angles, textes, packs)
    ├── requirements_orchestrator.txt
    └── libs/
        ├── ledger_manager.py       ← CRUD liber_clipping.json + délégation IW_CUSTOS
        ├── siege_initializer.py    ← validation des 4 inputs Warsmith (campaign/ singulier)
        ├── gate_validator.py       ← vérifie les artefacts attendus avant validation de porte
        └── omnis_watch_distributor.py ← génère packs_index.json + raw URLs OMNIS_WATCH
```

### Décisions d'implémentation
- `gate_validator` refuse la validation d'une porte si les artefacts attendus sont absents (hérésie « passer une porte sans validation » impossible).
- Le `--close-siege` est la seule voie de fermeture (seul le Warsmith déclare la fin).
- F04 reste autonome : l'Orchestrateur ne pilote pas le dialogue premium direct (statut F04 = done via son propre check-in).
- `gates.py` est calqué sur le pattern `YOUTUBE/ORCHESTRATOR/CODEBASE/gates.py` (réutilisation ~70%).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | 4 Portes, pattern hybride, ledger |
| IW_CUSTOS | ✅ (racine) | ✅ (v1) | Gardien liber_clipping.json |
| F01_F06 + TYRANT + F00_CAPTEURS + ANGLESMITH | ✅ | ❌ | Prochaines vagues |

### Prochaines étapes
1. Implémenter F01_SCOUT (vague 2)
2. Implémenter F02_TYRANT_CAMP + TYRANT (vague 3)
3. Implémenter ANGLESMITH + F03_SOURCE_HUNTER + F04_COPYWRITER + F05_PACKAGER + F06_TRACKER + F00_CAPTEURS
4. Premier siège réel avec les inputs du Warsmith

---

## [DEV-F01] F01_SCOUT implémentée — Reconnaissance de fer

### Contexte
Deuxième vague de code : la frégate d'acquisition est opérationnelle. Elle inventorie les assets de la campagne (strict-source, règle C1) et produit le `source_specimen.json` consommé par F02_TYRANT_CAMP (Porte 1) et F03_SOURCE_HUNTER (Porte 3).

### Fichiers livrés
```
F01_SCOUT/CODEBASE/
├── scout.py                  ← wrapper 3 phases (--prepare / --auto / --finalize)
├── requirements_c01.txt
└── libs/
    ├── recon.py              ← parse directive.md (section assets, campaign_id, types)
    ├── enrich.py             ← yt-dlp --dump-json + outlier_score (mode dry si absent)
    └── scribe.py             ← transcription (youtube-transcript-api → yt-dlp → dry)
```

### Décisions d'implémentation
- Mode `--prepare` : génère `IN/scout_prompt.json` pour l'IRON + pré-remplit le specimen.
- Mode `--auto` : analyse locale sans IRON (enrichissement + transcription optionnelle) — les assets restent strictement ceux de `directive.md`.
- Mode `--finalize` : valide cohérence (campaign_id, assets non vides, URLs valides), génère `scout_report.md`, check-in IW_CUSTOS (statut F01 = done).
- `outlier_score = view_count / baseline` calculé dans enrich (aucun chiffre inventé).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | recon/enrich/scribe + scout.py |
| F02_F06 + TYRANT + F00_CAPTEURS + ANGLESMITH | ✅ | ❌ | Vagues suivantes |

### Prochaines étapes
1. Implémenter F02_TYRANT_CAMP + TYRANT (vague 3)
2. Implémenter ANGLESMITH (vague 4)
3. Implémenter F03_F06 + F00_CAPTEURS

---

## [DEV-F02-TYRANT] F02_TYRANT_CAMP + TYRANT implémentées — Verdict & Oracle

### Contexte
Troisième vague de code : la Porte 1 est couverte côté stratégie. F02_TYRANT_CAMP (mode réactif) rend le verdict GO/NO-GO + océan bleu pour chaque campagne ; TYRANT (mode prospectif) veille les Démons du wild clipping et nourrit `ARCHIVUM/demons/`.

### Fichiers livrés
```
F02_TYRANT_CAMP/CODEBASE/
├── tyrant_camp.py                ← wrapper 3 phases (--prepare / --auto / --finalize)
├── requirements_c02.txt
└── libs/
    ├── skeleton_extractor.py     ← pré-squelette viral du clip ref (l'IRON affine)
    ├── blue_ocean_finder.py      ← océans bleus depuis ARCHIVUM/demons/ + saturation low/medium eligible
    └── fit_scorer.py             ← score fit plateforme x marche x niche (0-10, aucun chiffre invente)

TYRANT/CODEBASE/
├── tyrant.py                     ← wrapper 3 phases (--prepare / --auto / --finalize)
├── requirements_tyrant.txt       ← yt-dlp + youtube-transcript-api (Warsmith/IRON)
└── libs/
    ├── outlier_scorer.py         ← outlier_score = views / baseline, seuil > 3x par defaut
    ├── emotion_classifier.py     ← emotion dominante (drame/joie/outrage/...) depuis titre/transcript
    ├── blue_ocean_mapper.py      ← territoires adjacents 1 couche max (clamp profondeur = heresie guard)
    └── demon_archivist.py        ← ecrit ARCHIVUM/demons/<demon_id>.json
```

### Decisions d'implementation
- Heresie guard au finalize : toute profondeur d'ocean bleu != 1 est clampee (jamais 2 couches).
- Aucun Demon sans preuve quantitative : outlier_score calcule strictement (views / baseline), jamais invente.
- F02 --auto : verdict GO si assets presents dans le specimen, sinon NO-GO (strict-source).
- Les deux frégates font leur check-in IW_CUSTOS (statuts `tyrant_done` / `verdict_ready` via preconditions).
- `TYRANT/IN/tyrant_config.json` : defaults (outlier_threshold_x=3, max_blue_ocean_depth=1) generes par --prepare.

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict GO/NO-GO + ocean bleu (Porte 1) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Demon -> ARCHIVUM/demons/ |
| F03_F06 + F00_CAPTEURS + ANGLESMITH | ✅ | ❌ | Vagues suivantes |

### Prochaines etapes
1. Implementer ANGLESMITH (vague 4 — forge les N angles sur verdict.json)
2. Implementer F03_SOURCE_HUNTER + F04_COPYWRITER (vague 5)
3. Implementer F05_PACKAGER + F06_TRACKER + F00_CAPTEURS
4. Premier siege reel avec les inputs du Warsmith

---

## [DEV-ANGLESMITH] ANGLESMITH implémentée — La forge des N angles (Porte 2)

### Contexte
Quatrième vague de code. ANGLESMITH est portée par F02_TYRANT_CAMP (décision README/ORCHESTRATOR : "ANGLESMITH via F02 stratégie"). Elle forge les N angles d'attaque sur le verdict de la Porte 1 : X directs (territoire du Démon) + Y océan bleu (re-ciblage non saturé, MÊME source, 1 couche max).

### Fichiers livrés
```
F02_TYRANT_CAMP/CODEBASE/
├── anglesmith.py                  ← wrapper 3 phases (--prepare / --auto / --finalize)
│                                    (--n-angles, sortie OUT/angles.json pour F03 + F04)
└── libs/
    ├── angle_forger.py            ← combinatoire 4 axes (family/emotion/engagement/reframe_dim)
    │                                 + anti-cannibale (2 axes différenciants minimum)
    └── learnings_weight.py        ← pondération (poids nul si < 50 packs exécutés)
```

### Décisions d'implémentation
- Zones : `n_blue = min(len(blue_ocean_unlocked), n/3)` — le reste en direct. Chaque angle porte `zone`, `territory`, `blue_ocean_depth=1` (blue) et `blue_ocean_reframe_applied`.
- Anti-cannibale vérifié au forge ET re-vérifié au finalize (2 axes différenciants min, sinon flag CANNIBALE).
- Poids : `learnings.json.cumulative_packs_executed < 50` → tous les poids = 1.0 (neutre) ; éligible ensuite → poids par `angle_performance[*].weight`.
- Hérésie guard au finalize : toute profondeur != 1 est clampée.
- Check-in IW_CUSTOS `--frigate ANGLESMITH` (fleet_status → `angles_forged` quand la précondition verdict_ready est remplie).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_F06 + F00_CAPTEURS | ✅ | ❌ | Vagues suivantes |

### Prochaines étapes
1. Implémenter F03_SOURCE_HUNTER (vague 5)
2. Implémenter F04_COPYWRITER (vague 6 — frégate lourde premium)
3. Implémenter F05_PACKAGER + F06_TRACKER + F00_CAPTEURS
4. Premier siège réel avec les inputs du Warsmith

---

## [DEV-F03] F03_SOURCE_HUNTER implémentée — La Sélection de la Seam (Porte 3)

### Contexte
Cinquième vague de code. La frégate de sélection est opérationnelle : à la Porte 3, elle prend les N angles forgés par ANGLESMITH (Porte 2) et identifie pour chaque angle la meilleure vidéo longue des assets de la campagne (strict-source, règle C1) + les segments pertinents (directives pour D-F02 d'OMNIS_WATCH). Elle produit un `source_specimen_<angle_id>.json` par angle, consommé par F04_COPYWRITER et F05_PACKAGER.

### Fichiers livrés
```
F03_SOURCE_HUNTER/CODEBASE/
├── source_hunter.py                ← wrapper 3 phases (--prepare / --auto / --finalize)
├── requirements_c03.txt            ← stdlib pure (yt-dlp/transcript-api optionnels)
└── libs/
    ├── transcript_loader.py        ← charge + indexe les transcripts F01
    │                                 (ARCHIVUM/campaign/transcripts/transcript_<id>.json)
    ├── segment_matcher.py          ← score angle ↔ transcript (banques émotion/reframe),
    │                                 fenêtres contiguës clampées [min,max],
    │                                 extension au min de durée sur le transcript complet
    └── duration_guard.py           ← fourchette min/max par plateforme
                                      (profil ARCHIVUM/platform_generator/, défauts déclarés sinon)
```

### Décisions d'implémentation
- `--prepare` : génère `IN/source_hunter_prompt.json` (mission + angles + assets + fourchette plateforme + hérésies) — l'IRON affine qualitativement.
- `--auto` : analyse locale sans IRON — meilleur asset par angle (score fenêtres transcript), `blue_ocean_reframe_applied` calé sur la zone de l'angle, chaque score tracé dans la `rationale` (aucun chiffre inventé).
- `--finalize` : gardes anti-hérésie (asset hors assets F01 = HERESIE, segments hors fourchette plateforme, incohérence océan bleu) + `OUT/source_summary.md` + check-in IW_CUSTOS (F03 → `specimens_selected`).
- Les segments sont des directives, jamais des coupes (le cut reste à D-F02 d'OMNIS_WATCH).
- Choix plateforme/marché : args CLI prioritaire, sinon `liber_clipping.json → inputs_warsmith`.

### Tests effectués (environnement mock)
- 4 angles (direct + océan bleu) sur 2 assets transcriptés : matchs corrects par banque, fenêtres dans la fourchette YouTube [15,45]s, océan bleu coché.
- Garde HERESIE : asset hors assets campagne → finalize refuse.
- Garde durée : segment > max plateforme → finalize refuse.
- `--prepare` : fourchette plateforme injectée dans le prompt (tiktok = [15,30]s).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_SOURCE_HUNTER | ✅ | ✅ (v1) | Sélection asset + segments (Porte 3) |
| F04_COPYWRITER | ✅ | ❌ | Vague 6 — frégate lourde premium |
| F05_PACKAGER + F06_TRACKER + F00_CAPTEURS | ✅ | ❌ | Vague 7-8 |

### Prochaines étapes
1. Implémenter F04_COPYWRITER (vague 6 — frégate lourde premium direct, 4 phases)
2. Implémenter F05_PACKAGER (vague 7) + F06_TRACKER (vague 7) + F00_CAPTEURS (vague 8)
3. Premier siège réel avec les inputs du Warsmith

---

## [DEV-F04] F04_COPYWRITER implémentée — La Plume de la Forteresse (Porte 3)

### Contexte
Sixième vague de code. La frégate lourde de la Porte 3 est opérationnelle : elle forge le `text_payload` complet pour chaque angle (3 titres calibrés + paragraphe reframing + caption + hashtags 3 strates + on-screen text + CTA). **Singularité** : rupture du pattern 3 phases — la génération parle DIRECT au modèle premium (clé API dédiée), l'IRON ordonnance seulement.

### Fichiers livrés
```
F04_COPYWRITER/CODEBASE/
├── copywriter.py                    ← orchestrateur 4 phases + init one-time
├── requirements_c04.txt             ← stdlib pure (client urllib, aucun SDK obligatoire)
└── libs/
    ├── context_builder.py           ← Phase A — rassemble TOUT l'ARCHIVUM pertinent
    │                                  (8 sous-dossiers copywriting + rules + profiles +
    │                                  angles + demons + knowledge_base + learnings +
    │                                  doctrine + systemprompt), fichiers > 30k chars tronqués
    ├── premium_client.py            ← Phase B — client modèle premium direct
    │                                  (OpenAI-compatible via urllib, Anthropic supporté,
    │                                  clé depuis env CLIPPING_PREMIUM_API_KEY,
    │                                  config gitignored CONTRACTS/copywriter_secrets.json)
    ├── iron_ordonnancer.py          ← Phase C — prompt IRON (validation + classement)
    │                                  + mode --auto-ord local heuristique (rank titles,
    │                                  reco paragraphe, auto-fix #ad)
    ├── compliance_checker.py        ← garde-fous : FTC #ad, phrases interdites
    │                                  (abonne-toi/like et partage/swipe up…), paragraphe
    │                                  > 2 lignes, clickbait sans payoff, 3 titres/3 strates
    └── md_renderer.py               ← Phase D — .md lisible opérateur (le Warsmith
                                       lit le .md au moment de poster, pas le JSON)
```

### Décisions d'implémentation
- Pattern 4 phases : `--setup-context` (A) → `--generate` (B) → `--ordonnance` (C) → `--finalize` (D). Phase B refusée tant que `copywriter_systemprompt.md` est le placeholder (sauf `--force`).
- Init one-time : `--init-systemprompt` — le premium génère le system prompt figé depuis la doctrine + le musée copywriting (refus si déjà généré, `--force` pour refaire).
- `--generate --dry-run` : écrit `IN/premium_call_<angle>.json` (system + user prompt) sans appel réseau — inspectable avant de dépenser la clé premium.
- `--ordonnance` sans flag : prompt IRON (le Warsmith copie dans Claude sandbox) ; `--ordonnance --auto-ord` : classement local (rank = platform_fit + market_fit + bonus hook_type connu), reco paragraphe (use si ≤ 2 lignes / ≤ 220 chars), auto-fix FTC (`#ad` ajouté à la caption si absent).
- Veto paragraphe 3 niveaux : `recommendation` (F04) → `override_omniswatch` (Oracle, null) → `final_operator` (Warsmith, null) — résolution : le dernier non-null gagne.
- `--finalize` : hérésies critiques → refus (FORBIDDEN_PHRASE, FTC_AD_MISSING, PARAGRAPH_TOO_LONG) ; génère le `.md` ; check-in IW_CUSTOS F04 seulement quand TOUS les angles ont leur payload ordonnancé (fleet_status → `text_payloads_forged`).
- Clé premium : jamais dans les fichiers — `copywriter_secrets.json` (gitignored) ne référence que la var d'env `CLIPPING_PREMIUM_API_KEY` + model_id/provider/base_url.

### Tests effectués (environnement mock TEST_F04)
- 3 angles (A01/A02/A03) : phases A→B→C→D complètes, `campaign_id` propagé depuis le contexte.
- Classement titres : le titre au score le plus haut (9+8+1) passe rank 1 — vérifié sur sortie ordonnancée.
- Garde FORBIDDEN_PHRASE : caption "abonne-toi…" → finalize refusé (corrigé après normalisation des traits d'union).
- FTC auto-fix : caption sans #ad → `#ad` ajouté + hashtags.
- Serveur mock OpenAI-compatible : `--generate` réel → POST /chat/completions OK (model + system prompt + schema envoyés), sortie brute parsée et sauvegardée.
- `--init-systemprompt` sans clé → refus propre (message clair, exit 1, pas de traceback).
- Robustesse : `load_json` en utf-8-sig (BOM PowerShell Windows).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_SOURCE_HUNTER | ✅ | ✅ (v1) | Sélection asset + segments (Porte 3) |
| F04_COPYWRITER | ✅ | ✅ (v1) | text_payloads — 4 phases premium direct (Porte 3) |
| F05_PACKAGER + F06_TRACKER + F00_CAPTEURS | ✅ | ❌ | Vague 7-8 |

### Prochaines étapes
1. Le Warsmith : créer `CONTRACTS/copywriter_secrets.json` (gitignored) + `export CLIPPING_PREMIUM_API_KEY`
2. Le Warsmith : remplir la doctrine (sections I-X) + le musée `ARCHIVUM/copywriting/` → puis `python copywriter.py --init-systemprompt` (one-time)
3. Implémenter F05_PACKAGER (vague 7) + F06_TRACKER (vague 7) + F00_CAPTEURS (vague 8)
4. Premier siège réel avec les inputs du Warsmith

---

## [DEV-F05] F05_PACKAGER implémentée — Le Ferrier de la Porte 4

### Contexte
Septième vague de code. La frégate d'assemblage final est opérationnelle : elle fusionne les artefacts F01 → F04 en N `production_pack.json` conformes au schéma canonique `CONTRACTS/production_pack_schema.json` (contrat d'interface OMNIS_WATCH). Un pack = 1 vidéo pour 1 plateforme pour 1 marché. **F05 ne fait pas appel à l'IRON** — enchaînement purement déterministe de fusion de JSONs.

### Fichiers livrés
```
F05_PACKAGER/CODEBASE/
├── packager.py                      ← --assemble (N packs) + --finalize (validation + expédition)
├── requirements_c05.txt             ← stdlib pure (jsonschema optionnel)
└── libs/
    ├── schema_validator.py          ← validateur draft-07 maison, fidèle au schéma canonique
    │                                  (type/required/enum/const/min-maxItems/contains/min-max)
    └── reference_style_extractor.py ← ADN style du clip de référence (pacing, energy_level,
                                        cut_density, color_palette, text_treatment) —
                                        matière première brute, OMNIS_WATCH applique ses presets
```

### Décisions d'implémentation
- Blocs du pack : `identite`, `cibles`, `source`, `angle`, `cut_directives`, `reference_style`, `text_payload`, `compliance`, `metadata` + `submission_checklist` (7 items pending, deadline 60 min Whop).
- `hook_style_fit` dérivé des 3 hook_types classés par F04 ; `loop_tech` = open_loop si engagement cliffhanger, closed_loop sinon ; `anti_cannibal_diff.differentiated_axes` = axes qui diffèrent vs tous les autres angles (min 2).
- `blue_ocean` : les clés `blue_ocean_depth`/`territory`/`rationale` ne sont émises que si l'angle est réellement océan bleu (pas de null dans le contrat).
- `cut_directives` : fourchettes par plateforme (profil ARCHIVUM/platform_generator/, défauts déclarés sinon — aligné sur F03 duration_guard) + `forbidden` contient obligatoirement `silences > 3s` (contrainte `contains` du schéma).
- `reference_style` : ordre de résolution = `ARCHIVUM/campaign/reference_style.json` (vision IRON) → bloc `reference_style` du `reference_clip.json` → défauts honnêtes `observed: false` + prompt de vision écrit dans `IN/reference_style_prompt.json`. Le champ `observed` est un flag additionnel (additionalProperties autorisé) — la `note` du schéma est une const figée.
- Gardes hérésie : video_url hors assets F01 (règle C1) → assemble refuse ; `source_permission != campaign_provided` → finalize refuse ; text_payload sans bloc F04 requis → refuse ; pack non conforme au schéma → finalize refuse (exit 1, liste des erreurs).
- `--finalize` : `packs_index.json` (index OMNIS_WATCH) + `packager_summary.md` ("N packs prêts à expédier → OMNIS_WATCH", flag style ADN par défaut) + check-in IW_CUSTOS (F05 → `packs_assembled`).
- Robustesse Windows : lectures JSON en utf-8-sig (BOM PowerShell).

### Tests effectués (environnement mock TEST_F05)
- 3 angles (A01/A02/A03) : assemble + finalize, 3 packs validés contre le schéma canonique (0 erreur).
- Contenu pack vérifié : 10 blocs, checklist 7 items, `forbidden` contient `silences > 3s`, metadata title_pattern = titre rank 1.
- Garde HERESIE strict-source : video_url externe (hors assets F01) → assemble refuse.
- Style ADN : sans `reference_style.json` → défauts `observed: false` + prompt vision ; avec le fichier → `observed: true` (pacing/energy/cut_density/color_palette pris en compte).
- Validateur : pack avec `disclosure: #sponsored` → const violation détectée ; pack conforme → OK.
- Check-in IW_CUSTOS : F05 done (fleet_status reste pending dans le mock — préconditions non remplies, comportement attendu).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_SOURCE_HUNTER | ✅ | ✅ (v1) | Sélection asset + segments (Porte 3) |
| F04_COPYWRITER | ✅ | ✅ (v1) | text_payloads — 4 phases premium direct (Porte 3) |
| F05_PACKAGER | ✅ | ✅ (v1) | production_packs -> OMNIS_WATCH (Porte 4) |
| F06_TRACKER + F00_CAPTEURS | ✅ | ❌ | Vague 8 |

### Prochaines étapes
1. Implémenter F06_TRACKER (vague 8 — checklist + learnings) puis F00_CAPTEURS (vague 8, commandité)
2. Premier siège réel avec les inputs du Warsmith (F01 → F05 bout en bout)
3. Le Warsmith : doctrine + musée copywriting + `--init-systemprompt` F04 + vision IRON du clip de référence (`reference_style.json`)

---

## [DEV-F06] F06_TRACKER implémentée — Le Traqueur de la Forteresse (post-Porte 4)

### Contexte
Huitième vague de code. La frégate post-publication est opérationnelle : elle active la `submission_checklist` des packs F05, enregistre les saisies du Warsmith (post, soumission Whop, vues 1h/24h, payout), boucle le `learnings.json` à la fermeture de campagne et ferme le ledger via IW_CUSTOS. **F06 ne fait pas appel à l'IRON ni au premium** — pur mécanique de log + calcul.

### Fichiers livrés
```
F06_TRACKER/CODEBASE/
├── tracker.py                       ← CLI : --post / --submit / --views / --payout / --close-campaign
├── requirements_c06.txt             ← stdlib pure
└── libs/
    ├── readings_validator.py        ← cohérence saisies Warsmith (monotonie vues, doublons,
    │                                  négatifs refusés)
    ├── learnings_aggregator.py      ← agrégation angle_performance (clé composite 6 axes),
    │                                  weight progressif (seuil 50 packs), campaign_history préservée
    └── channel_performance_updater.py ← ARCHIVUM/channels/<slug>/performance.json (packs + totaux)
+ IW_CUSTOS.py                       ← nouveau mode --close-campaign (campaign_status closed,
                                        siege_closed_at) — seul agent autorisé à écrire liber
```

### Décisions d'implémentation
- Les axes d'angle (family/emotion/engagement/reframe_dim) sont copiés du pack F05 vers l'entrée du submission_log au `--post` — sinon l'agrégation par clé composite serait vide.
- Soumission : `submission_within_1h` = (soumis − posté) ≤ deadline du checklist (60 min par défaut) ; flag `submission_late` sinon.
- Seuils low_payout / low_views lus par regex dans `clipping_rules.md` (CONTRACTS puis ARCHIVUM/rules) — si non déclarés par le Warsmith, défaut 0 (flag inactif, pas de faux positif).
- Pondération v1 progressive : `weight = clamp(1 + 0.25 × (moy_grp/moy_glob − 1), 0.5, 2.0)` uniquement si `cumulative >= 50`, sinon 1.0 pour tous (hérésie sinon — ANGLESMITH lit ce flag).
- `--close-campaign` : agrège learnings en PRÉSERVANT l'historique (append/update, jamais d'écrasement), calcule `aggregate_cpm`, écrit `campaign_summary.md`, check-in IW_CUSTOS F06 (fleet_status → campaign_closed) puis `--mode close-campaign` (campaign_status closed dans liber).
- Validateur : refus des doublons (déjà posté, vues/payout déjà enregistrés), vues négatives, views_24h < views_1h, payout négatif.
- Perfs par compte : `ARCHIVUM/channels/<slug>/performance.json` créé à la volée (le Warsmith ajoute ses comptes au fil du temps).

### Tests effectués (environnement mock TEST_F06)
- 3 packs postés/soumis/vues/payout → close-campaign : learnings agrégés par 6 axes (3 groupes), weight neutres (< 50), campaign_history 1 entrée, aggregate_cpm calculé, submission_log closed, IW_CUSTOS campaign_status closed + F06 done.
- Validateur : views_24h < views_1h refusé ; vues/payout doublons refusés ; payout négatif refusé ; double --post refusé.
- Channel perfs : clip_main (2 packs, totaux vues/payout) et clip_alt suivis séparément.
- Boucle préservée : 2e campagne fermée → cumulative 3→4, history 1→2 entrées, groupe A03 fusionné (packs_count 1→2, moyennes recalculées).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_SOURCE_HUNTER | ✅ | ✅ (v1) | Sélection asset + segments (Porte 3) |
| F04_COPYWRITER | ✅ | ✅ (v1) | text_payloads — 4 phases premium direct (Porte 3) |
| F05_PACKAGER | ✅ | ✅ (v1) | production_packs -> OMNIS_WATCH (Porte 4) |
| F06_TRACKER | ✅ | ✅ (v1) | Checklist + vues/payout + learnings + close (post-Porte 4) |
| F00_CAPTEURS | ✅ | ❌ | Vague 9 — commandité Warsmith |

### Prochaines étapes
1. Implémenter F00_CAPTEURS (vague 9 — scrap commandité, avant Porte 1)
2. Premier siège réel : F01 → F05 bout en bout, puis F06 au fil des posts
3. Le Warsmith : déclarer les seuils low_payout/low_views dans `CONTRACTS/clipping_rules.md` (règles C), doctrine F04 + `--init-systemprompt`, vision IRON du clip de référence

---

## [DEV-F00_CAPTEURS] F00_CAPTEURS implémentée — Les Yeux du Siège (avant Porte 1)

### Contexte
Neuvième et dernière vague de code. La frégate de veille est opérationnelle : elle produit la **cartographie** de l'écosystème (Whop + sites clipping commandités + perception niche) pour que F02 rende son verdict GO/NO-GO et son océan bleu en connaissance de cause. **Strictement commandité par le Warsmith** — aucun cron, aucune boucle auto.

### Fichiers livrés
```
F00_CAPTEURS/CODEBASE/
├── capteurs.py                       ← CLI : --scan (cartographie) / --scan-demons (Démon wild)
├── requirements_capteurs.txt         ← stdlib urllib requis ; requests/bs4/playwright/selenium optionnels
└── libs/
    ├── whop_scanner.py               ← page campagne (statut, budget, CPM, guidelines, assets) + Discover
    ├── clipping_ecosystem_scanner.py ← sites commandités : titres, campagnes Whop référencées,
    │                                    payouts observés, outils AI mentionnés
    ├── campaign_context_scanner.py   ← perception campagne via sources de contexte (compétiteurs,
    │                                    angles déjà utilisés, vues)
    └── demon_scanner.py              ← Démon wild (sondes TikTok/Shorts/Reels commanditées,
                                        archivées ARCHIVUM/demons/)
```

### Décisions d'implémentation
- **Commandité strict** : aucun auto-cron ; un site non listé dans `clipping_sites_to_scrap.json` n'est JAMAIS touché ; Whop est toujours scanné (défaut système non listable).
- **Hérésie gardée** : campagne fermée (liber `campaign_status == closed`) → F00_CAPTEURS refuse tout scan (exit 1). Le siège est éteint.
- **Best-effort mécanique + IRON** : extraction stdlib (urllib), tolérance 403/404/JS → chaque échec est flaggé `requires_vision` dans la cartographie avec le site/URL concerné, pour lecture IRON par le Warsmith.
- **Perception niche honnête** : `dominant_emotion_in_niche` et angles saturés calculés sur les textes effectivement récupérés ; sinon `non_estime` + flag IRON — jamais de valeur inventée.
- **Démon wild** : le Warsmith fournit les URLs de sonde explicites par plateforme (IN/scan_list.json) ; pages JS → `js_rendered` + chasse IRON ; résultats archivés `ARCHIVUM/demons/demon_wild_scan_<id>.json`.
- **Check-in IW_CUSTOS** : fin de scan → `CAPTEURS` done, `fleet_status` → `capteurs_done` (transition déjà déclarée dans IW_CUSTOS).

### Tests effectués (environnement mock TEST_F00_CAPTEURS)
- Scan complet avec serveur HTTP factice (127.0.0.1:8898) : page campagne (statut active, budget restant $250, CPM $0.10, guidelines, 5 assets), Discover (3 campagnes listées), site clippa (payouts $0.08/$0.05, outils Claude/GPT/Playwright/Premiere extraits), site cliptic 404 → `fetch_failed` + requires_vision, source X 403 → compétiteur `inconnu` + vision.
- Perception niche : émotion `non_estime` + flag IRON (corpus factice insuffisant) — pas de faux positif.
- Scan demons : page JS → `js_rendered` + vision ; sonde sans URL → `skipped` + vision ; 1 démon observé archivé.
- Hérésie campagne fermée : liber `campaign_status=closed` → refus des deux commandes, exit 1.
- Check-in IW_CUSTOS : CAPTEURS done + `fleet_status: capteurs_done` (vérifié via --mode status).

### Statut des composants

| Composant | Docs Tracking | Code Python | Notes |
|---|---|---|---|
| ORCHESTRATOR | ✅ | ✅ (v1) | |
| F01_SCOUT | ✅ | ✅ (v1) | |
| F02_TYRANT_CAMP | ✅ | ✅ (v1) | Verdict + océan bleu (Porte 1) |
| ANGLESMITH (via F02) | ✅ (README/F02) | ✅ (v1) | N angles direct + blue ocean (Porte 2) |
| TYRANT (prospectif) | ✅ | ✅ (v1) | Veille Démon -> ARCHIVUM/demons/ |
| F03_SOURCE_HUNTER | ✅ | ✅ (v1) | Sélection asset + segments (Porte 3) |
| F04_COPYWRITER | ✅ | ✅ (v1) | text_payloads — 4 phases premium direct (Porte 3) |
| F05_PACKAGER | ✅ | ✅ (v1) | production_packs -> OMNIS_WATCH (Porte 4) |
| F06_TRACKER | ✅ | ✅ (v1) | Checklist + vues/payout + learnings + close (post-Porte 4) |
| F00_CAPTEURS | ✅ | ✅ (v1) | Cartographie écosystème — commandité Warsmith (avant Porte 1) |

### Prochaines étapes
1. Premier siège réel : F00_CAPTEURS → F01 → F05 bout en bout, puis F06 au fil des posts
2. Le Warsmith : déclarer les seuils low_payout/low_views dans `CONTRACTS/clipping_rules.md` (règles C), doctrine F04 + `--init-systemprompt`, vision IRON du clip de référence
3. Le Warsmith : peupler `IN/clipping_sites_to_scrap.json` + `IN/campaign_to_observe.json` au lancement du siège

---

## Portes — mapping des jalons futurs

| Porte | Jalon attendu | Statut |
|---|---|---|
| Avant Porte 1 | F00_CAPTEURS scrap ecosysteme + niche | Code pret (attente siege reel) |
| Porte 1 | F02_TYRANT_CAMP verdict campagne | Code pret (attente siege reel) |
| Porte 2 | ANGLESMITH N angles forges | Code pret (attente siege reel) |
| Porte 3 | F03 + F04 text_payloads prets | Code pret (attente siege reel) |
| Porte 4 | F05 production packs expedies -> OMNIS_WATCH | Code pret (attente siege reel) |
| Post-Porte 4 | F06 tracker + learnings + close | Code pret (attente siege reel) |

*Fer au-dedans, Fer au-dehors.*

## [2026-08-04T17:39:01Z] siege_init — mode=logo — siege_id=SIEGE-LOGO-20260804T173901

## [2026-08-04T17:40:24Z] campaign_closed — None — siege_closed_at: 2026-08-04T17:40:24Z

## [2026-08-04T17:41:53Z] campaign_closed — None — siege_closed_at: 2026-08-04T17:41:53Z

## [2026-08-04T17:41:53Z] siege_init — mode=logo — siege_id=SIEGE-LOGO-20260804T174153

## [2026-08-04T17:43:24Z] F01 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F01_SCOUT/OUT/source_specimen.json — md5: a3b3357e8576f6b552f7d85323f3d095 — status: done

## [2026-08-04T17:45:16Z] F02 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/campaign_verdict.json — md5: 96c2786f3ed56652e774292eac63645a — status: done

## [2026-08-04T19:39:41Z] ANGLESMITH — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: cd7706807870582eb93876be2737b285 — status: done

## [2026-08-04T19:40:37Z] ANGLESMITH — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: d4e2c2b5a7f0afd0c081632c50ce6d91 — status: done

## [2026-08-04T20:12:55Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: de104869b9e20a9e5cff14f221528ec1 — status: done

## [2026-08-04T20:12:55Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 524cb5a0564b8a52403e6bab007931a9 — status: done

## [2026-08-04T20:12:55Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 7b4f0c434cd8cf6cb040f9fac10d95c9 — status: done

## [2026-08-04T20:12:55Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 9858074d1e3d3dcf604bb5ab24b135b3 — status: done

## [2026-08-04T20:12:55Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: 3f24bcf8c219efa20f73efdba75934d0 — status: done

## [2026-08-04T20:13:04Z] F04 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: 3f24bcf8c219efa20f73efdba75934d0 — status: done

## [2026-08-04T20:14:23Z] F05 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 98d22d920ba6323ad8d5eb388c17a435 — status: done

## [2026-08-04T21:23:00Z] F05 — check-in — output: /home/daytona/codebase/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 0451f5429555c6e94e2e6a2b79e12cae — status: done

## [2026-08-10T20:50:37Z] campaign_closed — None — siege_closed_at: 2026-08-10T20:50:37Z

## [2026-08-10T21:10:42Z] F01 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F01_SCOUT/OUT/source_specimen.json — md5: 01deedc305d6b732e0d5bfa23e610e8f — status: done

## [2026-08-10T21:11:11Z] F02 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/campaign_verdict.json — md5: c50d9ffb18977cbde36cd2ba68358cda — status: done

## [2026-08-10T21:14:11Z] ANGLESMITH — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: 5f4c45a460c34cc80916b0d0db43ee2e — status: done

## [2026-08-10T21:29:06Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: 8bd44bb58d649615216419ae5bcaef36 — status: done

## [2026-08-10T21:29:07Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 79339e56db03b601d9722762ffb90d42 — status: done

## [2026-08-10T21:29:07Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 125bcf6e98b6f5ce804189e5a3ae61df — status: done

## [2026-08-10T21:29:07Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 49bec2c62ead47fb980e877327906a81 — status: done

## [2026-08-10T21:29:07Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: cb24660d5e0ccaec5c701ce12a14de43 — status: done

## [2026-08-10T21:29:38Z] F05 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 35b91cf46fee43ba5637412441426a2f — status: done

## [2026-08-10T21:38:00Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: aaee765a0a7af8c097d485bd2c4a0536 — status: done

## [2026-08-10T21:38:00Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 0b86327166df6126155defdfd92bde4f — status: done

## [2026-08-10T21:38:00Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: a8b17f509638253524a1cb1691285fdc — status: done

## [2026-08-10T21:38:00Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 9278adea2c3c7268acb9cc6c6312d77b — status: done

## [2026-08-10T21:38:00Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: 2bb4b0f8e77baf011c37d96f36d4397e — status: done

## [2026-08-10T21:38:15Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: 5b09058f813d2e2f8a626195ae2622d7 — status: done

## [2026-08-10T21:38:16Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 0b86327166df6126155defdfd92bde4f — status: done

## [2026-08-10T21:38:16Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: a8b17f509638253524a1cb1691285fdc — status: done

## [2026-08-10T21:38:16Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 9278adea2c3c7268acb9cc6c6312d77b — status: done

## [2026-08-10T21:38:16Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: ccc510f473aabdd49eafbebea570697a — status: done

## [2026-08-10T21:38:19Z] F05 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 617d34b4d3931225e280a9b46eb66068 — status: done

## [2026-08-13T23:29:22Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/subjects_proposal.md — md5: 59b7b8327c27b9ead52f8f62c15d8044 — status: done

## [2026-08-13T23:31:56Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/subjects_proposal.md — md5: 2796c049a7685f023ad45ffec702d570 — status: done

## [2026-08-14T07:00:22Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/subjects_proposal.md — md5: 1a3fb914f0b66f0ef324a36e36164e24 — status: done

## [2026-08-14T07:46:47Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/subjects_proposal.md — md5: fb35b9fd0eaf47b77943b3459eed3a5b — status: done

## [2026-08-14T07:52:21Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/subjects_proposal.md — md5: 1b5c9ffdc00885d2a06695fa63088ad3 — status: done

---

## [DELIVER-SUBJECT] Commande `--deliver-subject <index>` + livraison NBA_WESTBROOK

### Contexte
La porte `warsmith_chooses` est automatisée : le Warsmith choisit un sujet de
`EXPORT/subjects_proposal.json` (scan `F00-5581179c`, niche NBA) et la nouvelle
commande livre le sujet choisi dans `ARCHIVUM/campaign/` pour démarrer le siège.

### Fichiers livrés
```
F00_CAPTEURS/CODEBASE/capteurs.py
└── cmd_deliver_subject() + _derive_tag() + _build_article_source() +
    _build_reference_clip() + _write_directive_md() + args CLI
```

### Décisions d'implémentation
- `--deliver-subject <index>` (1-based) lit la proposition (défaut
  `EXPORT/subjects_proposal.json`), prend le sujet choisi et écrit dans
  `ARCHIVUM/campaign/` : `directive.md` (Campaign ID `NICHE_TAG` dérivé,
  parseable F01), `article_source.json`, `reference_clip.json`.
- Le clip de fond est la VRAIE URL YouTube (preuve : candidat clip du sujet),
  les vues réelles de la métrique `top_video_views` — aucun chiffre inventé.
- Ledger : `campaign_id` + `inputs_warsmith.directive_path/reference_clip_path`
  mis à jour + check-in IW_CUSTOS CAPTEURS.
- Tag dérivé du sujet (pattern nom+prénom : 'Russell Westbrook…' -> westbrook).

### Livraison réalisée (2026-08-14)
- Sujet n°1 : **Westbrook tribute backlash** (GLM 9/10, méca 76.0/100).
- Campaign ID : `NBA_WESTBROOK`.
- Fichiers écrits dans `ARCHIVUM/campaign/` (directive.md, article_source.json,
  reference_clip.json) — vérifiés parseables par F01 (3 assets extraits).

### Prochaines étapes
1. F01_SCOUT `--prepare` / `--auto` sur `ARCHIVUM/campaign/directive.md`
2. F02_TYRANT_CAMP (Porte 1) → ANGLESMITH (Porte 2) → F03/F04 (Porte 3)
3. F05_PACKAGER (Porte 4) → F06_TRACKER (post-Porte 4)

## [2026-08-14T16:14:40Z] CAPTEURS — check-in — output: /workspace/MONDES_FORGES/CLIPPING/ARCHIVUM/campaign/directive.md — md5: e91e331cc7ba96c2a2039503ae73531f — status: done

## [2026-08-14T16:21:33Z] F01 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F01_SCOUT/OUT/source_specimen.json — md5: 0740832c6e88a600406b1e0b4032224a — status: done

## [2026-08-14T16:22:07Z] F02 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/campaign_verdict.json — md5: 24d7f11d87bc45563a597e12afc72c33 — status: done

## [2026-08-14T16:22:24Z] ANGLESMITH — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: d8d00056e4e432b5df1a4bca80716be6 — status: done

## [2026-08-14T16:23:07Z] F03 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F03_SOURCE_HUNTER/OUT/source_summary.md — md5: 565c5b0548683631124273edfb19c184 — status: done

## [2026-08-14T16:25:25Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: 6e7942193a76723dad3f8bfbad78e955 — status: done

## [2026-08-14T16:25:25Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 133d73156096c595fe3572c4465095d9 — status: done

## [2026-08-14T16:25:29Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 6a40d5ba4ae7fd988b37c6b700bf5b93 — status: done

## [2026-08-14T16:25:29Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: da5a2d6af7dcdb9c1036b6d467e33d6d — status: done

## [2026-08-14T16:25:29Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: dc8e49d25c8622b5274460e1e2e46de9 — status: done

## [2026-08-14T16:26:05Z] F05 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 55281af1d20fb59aa7edfeade8fffede — status: done

## [2026-08-14T16:30:52Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: 1fc722a6406bbdb6212f2538e81180a2 — status: done

## [2026-08-14T16:31:08Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 1d45d3f7fb31046cea7cc8fec55a9065 — status: done

## [2026-08-14T16:42:52Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 689751b0449199ea39284c753533d226 — status: done

## [2026-08-14T16:43:07Z] F04 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: a607df09d7d7398bd646ae0a585efa2c — status: done

## [2026-08-14T16:43:22Z] F05 — check-in — output: /workspace/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: e1512720b9b0df3efc13d6fea7b9158b — status: done

## [2026-08-15T09:34:31Z] CAPTEURS — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/ARCHIVUM/campaign/directive.md — md5: df03e0c592d1a051a9cce2738e28e22b — status: done

## [2026-08-15T09:34:42Z] F01 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F01_SCOUT/OUT/source_specimen.json — md5: 1f223f5d1e8dcbc6a6662ce9181861f3 — status: done

## [2026-08-15T09:50:03Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: 9612be6e0df10267a8ca6094b428f669 — status: done

## [2026-08-15T09:50:03Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: a69c5e4ece76825812163dae79221c0f — status: done

## [2026-08-15T09:50:03Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 2a4e0ee1f1a44de94db963fed8fa0245 — status: done

## [2026-08-15T09:50:04Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 02d15fbb32255b891f01b57ec6821974 — status: done

## [2026-08-15T09:50:04Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: faa4e5c95531b799c4c6067a85aa75d0 — status: done

## [2026-08-15T09:50:18Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: a69c5e4ece76825812163dae79221c0f — status: done

## [2026-08-15T09:50:18Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: 2a4e0ee1f1a44de94db963fed8fa0245 — status: done

## [2026-08-15T09:50:19Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 02d15fbb32255b891f01b57ec6821974 — status: done

## [2026-08-15T09:50:19Z] F04 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: faa4e5c95531b799c4c6067a85aa75d0 — status: done

## [2026-08-15T09:50:42Z] F05 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: e388b6a9c351f013f2c536c502d865b6 — status: done

## [2026-08-15T10:12:43Z] F05 — check-in — output: /tmp/opencode/perturabo/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 0b22903292a7174cbb326e10cc6932ee — status: done

## [2026-08-15T19:51:01Z] CAPTEURS — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/meme_virality_student_debt.md — md5: e7ea4b8d5067458b6ac59ea3ebcdee24 — status: done

## [2026-08-15T20:19:35Z] ANGLESMITH — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: e28e837b1e61acc6580e85506ce4e086 — status: done

## [2026-08-15T20:28:02Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: 9c0aea5a4ef02215abd0e268b3ab7ba3 — status: done

## [2026-08-15T20:37:40Z] F05 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 2c2bc27c434e5cb2af85e1765bc74968 — status: done

## [2026-08-18T13:43:40Z] CAPTEURS — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/meme_virality_marvel_doomsday.md — md5: 96c403cdda6589857f46bdc2885aebf6 — status: done

## [2026-08-18T13:44:03Z] CAPTEURS — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/meme_virality_student_loan_forgiveness.md — md5: 41676150fa72acc8bebc1c1f2a832880 — status: done

## [2026-08-18T14:27:17Z] ANGLESMITH — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F02_TYRANT_CAMP/OUT/angles.json — md5: 18b1d7a2a82f34be2e7fbed952eed226 — status: done

## [2026-08-18T16:08:04Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A01.md — md5: e5b09d1786c2d1146d7f3b61abc7954e — status: done

## [2026-08-18T16:08:04Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A02.md — md5: cb2a7de02e420bff5d06f78e804f4704 — status: done

## [2026-08-18T16:08:05Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A03.md — md5: bec7f52daffd78e64ceab82b4c2abdfe — status: done

## [2026-08-18T16:08:05Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A04.md — md5: 86ad666aefa5034ad1d69d3fc0c4767b — status: done

## [2026-08-18T16:08:05Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A05.md — md5: d13ef2a22c16d64112d95ad7c17d6c31 — status: done

## [2026-08-18T16:08:05Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A06.md — md5: 09fda1dfbcc650092c8f99509297f90c — status: done

## [2026-08-18T16:08:05Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A07.md — md5: 5183f0c39c0326911dac175718e6d7a3 — status: done

## [2026-08-18T16:08:06Z] F04 — check-in — output: /workspace/PERTURABO/MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_A08.md — md5: 0ffef97cbd450ef6063b575536243329 — status: done

## [2026-08-21T23:46:30Z] CAPTEURS — check-in — output: /home/ubuntu/perturabo_work/MONDES_FORGES/CLIPPING/F00_CAPTEURS/OUT/meme_virality_new_york_bagel.md — md5: 85e1ef3ab4646b01e8f328d994b12b27 — status: done

## [2026-08-22T08:53:55Z] campaign_closed — None — siege_closed_at: 2026-08-22T08:53:55Z

## [2026-08-22] Siège New York Bagel — leçons MEME

- F00 Discovery a été exécuté sur le marché US 25–45, YouTube Shorts, niche meme, avec ancrages de référence Zdak et Directeur premium ; les preuves et signaux restent séparés des hypothèses.
- ANGLESMITH a produit 10 angles ; le Champion a validé le sujet, puis F04 a généré les tweets, les textes motion et les métadonnées avec la clé premium.
- Le texte motion doit être contextualisé par les personnes du tweet (`My sister and me right now:`, `My friend and me right now:`), sans marqueur `A:` / `B:`, sans formule héritée d’un ancien siège et avec contrôle anti-cannibalisation.
- F05 a assemblé un pack unique `production_pack_logo.json` avec 10 vidéos et la balise commune `M1`. F05 est déterministe et n’utilise pas la clé premium.
- La revue opérateur précède l’export : le Champion est l’unique autorité des Gates. Le pack validé a été copié dans `EXPORT/production_pack_meme_new_york_bagel.json`, puis le siège a été fermé par IW_CUSTOS afin d’isoler ses résidus.
- Les artefacts de production ont été commités et poussés dans le commit `bf78ea3`.

## [2026-08-24T09:35:33Z] F05 — check-in — output: /home/ubuntu/perturabo_work/MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/packager_summary.md — md5: 88f0278700e1c19b612ba400bc73481d — status: done


## [2026-09-09T02:06:42Z] F06 — montage VIRAL (v2) — doctrine ARCHIVUM consommée

- `director.py` réécrit : plus de défauts morts. Zooms brutaux, smash/breath/idea cut, SFX sync, anti-détection obligatoire, émotion dérivée du signal VOX.
- `pur_montage_pipeline.py` : VOX (candidats) + F04 (overlay) -> `production_pack_<angle>.json` complet, montage EMBARQUÉ dans le pack (bloc `montage_instructions`).
- Sorties dans `ARCHIVUM/montage/packs/` (git-trackées, contrairement à OUT/).
- Workflow `perturabo_montage.yml` créé.

## [2026-09-09T03:25:06Z] F06 — montage frame-près validé + EXPORT

- Calage frame-près des cuts/zooms sur les word-timestamps (commit 31a576a) ; run montage vert.
- Packs calibrés A01/A02/A03 commités dans ARCHIVUM/montage/packs/ (commit de sortie 69f3da0).
- Doublon `copywriting` corrigé dans director.py (retiré du bloc montage_instructions).
- Packs PUR corrigés copiés dans EXPORT/ pour validation Warsmith.


## [2026-09-09] v2-live — naissance de la branche du live

- Branche `v2-live` = copie exacte de main (base `8ee8c8b`) ; seule divergence : la couche live de VOX.
- Radar `chat_pulse` (IRC Twitch anonyme, baseline EMA 5 min, clip pressure, cooldown) — 100% stdlib.
- `f00b_vox_live.py` : session live -> clip Helix immediat -> scoring VOX inchange -> gate hybride -> `trail.json` meme schema VOD.
- Workflows radar (dispatch, 6h max, statut board /3 min) + Oracle (cron 5 min, issues Oracle).
- `BOARD_LIVE/index.html` + docs (`README_V2.md`, guide 18, CONTINUATION, logs).

## [2026-09-15] Doctrine gates - mise en DRAFT de la session Sophie Rain

- Rappel doctrine (Warsmith) : **gate apres CHAQUE fregate** - l'operateur valide l'output avant de declencher la suivante. Chaine corrigee : F00C -> gate -> F00D -> gate -> F04 -> gate -> F06 (instructions montage + ses 4 gates internes) -> gate -> F05 (pack final embarquant montage_instructions + etats de gates) -> gate -> EXPORT.
- Constat : la session voxc-2/3/4 (blur) a saute les gates post-F00D, post-F04 (non executee), post-F06 (non execute) et le gate pre-EXPORT.
- Action corrective : les 3 manifestes caviar blur (docs/data/caviar/ voxc2/3/4) et le pack EXPORT/production_pack_pur_voxc2_blur.json sont marques `status: DRAFT` (champ + note). Aucun produit de cette session ne sort d'EXPORT sans la chaine complete.
- voxc-3/voxc-4 restent RESERVES (ad-reads Hims / Claude / FanDuel - interdits campagne).
- Prochaine etape validee par l'operateur : F04 sur voxc-2 (cle premium fournie), puis chaine gate par gate jusqu'a EXPORT.

## [2026-09-15] Session Sophie Rain voxc-2 : chaine COMPLETE gate-par-gate → EXPORT

- Première exécution conforme de la chaîne complète : F00C GO blur (opérateur) → F00D partition caviar → F04 GO overlay (kimi-k3/NVIDIA, transcript réel voxc-2, purges contamination ARCHIVUM) → F06 GO (v3.0.0-caviar_bound, soumis à F00D : 0 cut/zoom/SFX F06, 2 panneaux blur, duck climax 28.216 s, hook hérité, caviar_binding sha256) → F05 GO (pack final embarquant montage_instructions + chain_of_custody) → **EXPORT/production_pack_pur_voxc2_blur_v2.json (VALIDATED, ALL_GATES_GO)**.
- Correctif infra : artefacts pytest purgés du ledger narrativum + caviar_index (voxc-9 /tmp).
- Prochain chantier (hors pipeline) : exécution du pack par le bras armé LACRIMAE → MP4 9:16 → QA → soumission.

## [2026-09-18] F00B : run perdu -> refonte en mode matrice

- Run sequentiel F00B sur v2873615032 (session Aishah Sofey) : transcription
  terminee puis push HEAD:main rejete -- sorties perdues. Deux pieges appris
  (push code en dur + absence d artefacts) : corriges dans le nouveau workflow.
- Refonte perturabo_transcribe_matrix.yml (3 jobs, 15 segments paralleles,
  artefacts tout du long, push sur branche du run) + scripts segment_vod.py,
  merge_transcripts.py, matrix_score.py + champ offset optionnel cote Modal.
- Chaine d analyse et schema candidats INCHANGES -- le gate F00B operateur reste
  le seul point humain. Details : F00B_VOX/TRACKING/F00B_LOG.md, guide 21.

## [2026-09-19] Mode matrice : 1re session reelle - 3 runs, 2 fixes, reussite + correctif metadonnees

- Run 1 : echec deploy (fastapi manquant dans le job prepare) - corrige.
- Run 2 : HTTP 408 (segment 12 min > plafond requete Modal) - corrige :
  pieces de 480 s (transcribe_segment.py), offset global reel ffprobe, retries.
- Run 3 : reussite - 18 171 mots (4 h couvertes), 7 773 messages chat,
  10 candidats commits (9d24511).
- Anomalie : metadonnees (duree/titre) non transmises au reassemble ->
  scoring chat biaise (10/10 chat_spike sur les 9 premieres minutes).
- Correctifs : metadonnees traversant les jobs (outputs -> merge ->
  metadata.json), garde-fous duration<=0, chat de secours reecrit dans le
  transcript. Relance pour candidats propres -> gate F00B operateur.

## [2026-09-19] Gate F00B ferme -> F00D execute -> GATE F00D

- Verdict Warsmith enregistre (5 mixed approuves, vue de gate Salle de Controle).
- F00D : 5 medias extraits (download-sections, regle d or), 5 partitions caviar
  blur emises apres 2 fixes : seuil silences 250->400 ms (Budget) + arbitrage
  composeur dans le budget (refuse_to_emit reste derniere defense). Self-test
  + 10/10 tests verts.
- Climax reels diversifies, budgets 46-55/55u, trio blur+flash+SFX respecte.
- Gate F00D soumis a l operateur (emotions des panneaux a qualifier).

## [2026-09-19] F04 execute - 5 overlays blur gate-pret

- Mode overlay_only (asset blur), campagne 2026-07-24_AISHAH_SOFEY_MULTI,
  kimi-k3/NVIDIA via CLIPPING_PREMIUM_API_KEY.
- Purge 1 : residus Sophie Rain/Marvel dans angles.json (meme_hook Doom...) ->
  5 titres contamines refuses, champs purges des contextes + heresies etendues.
- Purge 2 : 2 titres en francais -> regeneres (directive Language = English).
- Anti-cond verifie par grep transcript (boat/elephant fenetre c1, kidney/dad c4).
- Sorties : overlay_raw_asf_c*.json + overlay_payload_asf_c*.json.
- GATE F04 soumis a l operateur.

## [2026-09-20] Gate F04 ferme -> phase metadonnees executee -> gate etendu

- Verdict Warsmith enregistre : 5/5 titres overlay ACCEPTED, emotions F00D
  `intrigue` x5 propagees dans les 5 manifestes caviar.
- Phase METADONNEES F04 executee (kimi-k3, directive campagne integree :
  @hiaishahsofey + #aishahsofey, English, pas de OF) -> 5 payloads
  `metadata_payload_asf_cN.json`, garde-fous 5/5 PASS, anti-cond verifie
  sur le transcript reel (mots dans `words`, pas `segments` - piege note).
- Page gate F04 etendue (Section C metadonnees). En attente : verdict
  metadonnees de l'operateur -> F06 (montage blur).

## [2026-09-20] F06 execute (5 instructions caviar_bound) - gate F06 ouvert : fenetres F00B + overlay F04 + emotions intrigue + partitions F00D sha-liees ; fix doctrine segment.emotion ; tests 13/13 verts.

## [2026-09-21] F05 execute - 5 production packs blur assembles (custody 4 gates, integrite PASS) - gate F05 ouvert avant EXPORT.

## [2026-09-21] GATE F05 GO -> EXPORT (session AISHAH v2873615032)
- 5 production packs blur VALIDATED (ALL_GATES_GO) + packager_summary copies dans EXPORT/.
- Conformité directive verifiée a l'export : @hiaishahsofey + #aishahsofey, anglais, zero OF, longueurs OK.
- Incident Pages : build Jekyll en echec sur les nouveaux contenus -> .nojekyll (site statique pur), toutes les pages servent 200.
- Chaine F00B->F00D->F04->F06->F05->EXPORT fermee avec gate operateur a chaque frégate.

## [2026-10-16] CERVEAU PARTAGÉ — repli oracle automatique (premium → oracle → off)
- Nouveau module unique `MONDES_FORGES/CLIPPING/SHARED/brain.py` : tout appel IA du tronc CLIPPING passe par lui. `ask()` résout premium (NVIDIA NIM kimi-k3 / CLIPPING_*) → oracle (passerelle AI_GATEWAY_*) → off, avec trace des échecs.
- Frégates branchées : F00B `libs/vox_premium.py`, F00C `f00c_vox.py` (bloc brain du manifeste + `--transcript`/`--no-brain`), F04 `libs/premium_client.py` (chat premium → repli oracle).
- Motif : run 38831207071 échoué `Payment Required: Insufficient credits` — une clé premium qui tombe ne bloque plus le pipeline.
- Contrat public `CONTRACTS/premium_bus_schema.json` ; exemples de secrets mis à jour (aucune clé dans les fichiers).
- Workflows : secrets NVIDIA_NIM_* + AI_GATEWAY_* injectés (matrix F00B, analysis F00C).
- Doctrine : `GUIDE_UTILISATION/22_MODE_CERVEAU_PARTAGE.md`.
