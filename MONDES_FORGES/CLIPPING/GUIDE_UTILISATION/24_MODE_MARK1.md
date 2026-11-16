# 24_MODE_MARK1 — Le mode MARK1 (sélection et livraison de clips)

> ⏱️ Lecture : 6 minutes. MARK1 est une **frégate autonome** : elle vit à côté de
> la forge, ne remplace rien, et ne demande aucune clé.

---

## 1. Ce que MARK1 est — en une phrase

MARK1 **décide** quels segments valent un clip, **forge** le titre, **vérifie** que la
campagne paie, **emballe le pack** et **écrit le ledger**. Il **ne produit jamais de vidéo.**

C'est la doctrine CLIPPING appliquée pour de vrai :

> « Le forge CLIPPING ne touche **jamais** une vidéo. Il décide **quoi** clipper, sous
> **quel** angle, avec **quel** texte — et livre à OMNIS_WATCH un `production_pack.json`
> prêt à consommer. » (`README.md`)

```
MARK1                     │  OMNIS_WATCH          │  Opérateur (toi)
──────────────────────────┼───────────────────────┼────────────────────────
décide / titre / vérifie  │  coupe, reframe, rend │  publie, soumet <1h
écrit pack + ledger       │  applique asset_mode  │  colle le lien, remplit les vues
```

---

## 2. Démarrage — 4 commandes

```bash
cd MONDES_FORGES/CLIPPING/MARK1

python mark1.py doctor                    # prouve qu'aucune clé n'est requise
python mark1.py pack packs/demo.json      # valide le pack d'entrée
python mark1.py export packs/demo.json    # écrit le pack livrable + le ledger
python mark1.py selftest                  # 36 tests, 0 dépendance
```

Sortie réelle de `doctor` (9 clés absentes, `[OK] GLOBAL`) :

```
== MARK1 doctor ==
[OK] dependances : aucune (stdlib seule, aucun ffmpeg)
[ absent] CLIPPING_PREMIUM_API_KEY F04 copywriter — LLM premium
...
[OK] export_dir               MONDES_FORGES/CLIPPING/EXPORT
[OK] asset_modes              blur, reframing
[OK] GLOBAL
```

---

## 3. Les 7 commandes

| Commande | Ce qu'elle fait |
|---|---|
| `doctor` | État des clés, `export_dir`, `asset_mode`. Sort `0`. |
| `pack <pack.json>` | Applique `G0_PACK` seul. |
| `title "<texte>" [--number N] [--subject S] [--internal a,b]` | Analyse S1, puis propose les titres **déjà valides**. Si aucun ne sort : tu l'écris à la main. |
| `campaign <camp.json> --platform tiktok [--target 500]` | Éligibilité + `$` net/1k + vues nécessaires pour la cible. |
| `export <pack.json> [--platform tiktok]` | **La commande centrale.** Enchaîne les portes, écrit le pack dans `EXPORT/`, une ligne de ledger par clip. |
| `export <pack> --transcript <path> --nb-segments N` | **Mode transcription.** MARK1 lit un transcript produit par `perturabo_transcribe` dans `ARCHIVUM/montage/transcripts/`, choisit les segments autour des marqueurs d'enjeu, et produit le pack. Ne télécharge rien, n'appelle aucune frégate. |
| `ledger [--add r.json \| --update <clip_token> --changes '{…}'] [--econ]` | Liste / ajoute / complète / recalcule. |
| `selftest` | Lance la suite. |

---

## 4. Le pack d'entrée

```json
{
  "mode": "mark1",
  "source": { "vod_url": "https://www.twitch.tv/videos/...", "duration_total_sec": 3600 },
  "asset_mode": "blur",
  "subject": "Sophie Rain",
  "internal_terms": ["duel"],
  "campaign": {
    "campaign_id": "DEMO_C1",
    "rate_usd_per_1k": 2.0,
    "funded": true,
    "budget_remaining_usd": 500,
    "platforms": ["tiktok", "youtube_shorts"],
    "cap_usd_per_clip": 200
  },
  "account": { "handle": "@mark1_demo", "warmup_days": 21, "banned": false },
  "assets": [
    {
      "id": "A01",
      "start_sec": 897,
      "end_sec": 927,
      "title": "Il a tout perdu en une nuit",
      "caption": "Il a tout perdu en une nuit #ad"
    }
  ]
}
```

**`asset_mode`** : `blur` ou `reframing`, **et rien d'autre**. Le vocabulaire complet de
la forge est `split|reframing|ranking|blur` (`caviar_director.py:34`) ; MARK1 n'admet que
les deux éprouvés, parce qu'il ne doit pas transmettre au consommateur un style qu'il n'a
jamais validé.

**`caption`** doit contenir `#ad` ou `#sponsored` (règle C2). Sans ça, `export` refuse.

---

## 5. Les deux tokens

| Token | Forme | Rôle |
|---|---|---|
| `pack_token` | `ae45e408` (8 hex) | Identité du **contenu** du pack. Stable, insensible à l'ordre des clés. |
| `clip_token` | `A01-20261115-ae45e408` | Identité d'**un clip**. Contient le `pack_token`. |

**Un pack = N clips = N `clip_token`, un seul `pack_token`.** Sortie réelle :

```
[OK] X1_EXPORT : 2 clip_tokens uniques, mode=blur
[OK] ledger : A01-20261115-ae45e408
[OK] ledger : A02-20261115-ae45e408
```

Le ledger est apparié **par `clip_token`**. Jamais par titre, jamais par date, jamais par
ordre de publication — un titre peut changer après publication, deux clips peuvent
partager un titre.

---

## 6. La journée type d'un siège MARK1

| Jour | Geste | Critère de fin |
|---|---|---|
| **J1** | Créer le pack, `doctor`, `pack`. | `[OK] GLOBAL`, `[OK] G0_PACK`. |
| **J2** | Choisir les bornes, `title`, `export`. Relire le pack dans `EXPORT/`. | Pack écrit, `clip_token` distincts, lignes de ledger. |
| **J3** | Publier, soumettre **< 1h**, `ledger --update <clip_token> --changes '{"clip_url": "..."}'`. | 3 lignes de ledger avec `clip_url`. |

---

## 7. Les 5 invariants de MARK1

1. **Aucun appel réseau.** MARK1 ne lit aucune statistique : l'outil de statistiques
   remplira le ledger plus tard, via `ledger --update`.
2. **Aucun seuil en dur.** Tout dans `MARK1/config/selection.json`.
3. **`llm_enabled` reste `false` et rien ne le lit.** Aucun LLM dans le chemin critique.
4. **Aucune suppression dans la forge.** MARK1 vit à côté.
5. **Aucun ffmpeg, ffprobe, `.ass`, MP4.** MARK1 ne rend pas de vidéo — c'est OMNIS_WATCH.

---

## 7 bis. Le flux réel d'un siège (V3.3)

MARK1 **ne déclenche rien**. La transcription est produite par un workflow
GitHub que **l'opérateur** lance, puis MARK1 la lit.

```
1. OPERATEUR  Actions > perturabo_transcribe > Run workflow
              (vod_url = https://twitch.tv/videos/...)
                    |
2. GITHUB     apt install ffmpeg + yt-dlp
              modal deploy transcribe.py   -> recupere l'URL
              f00b_vox.py auto_detect      -> telecharge, decoupe, transcrit
              commit ARCHIVUM/montage/transcripts/v<ID>_transcript.json
                    |
3. MARK1      python mark1.py export pack.json                   --transcript ARCHIVUM/montage/transcripts/v<ID>_transcript.json                   --nb-segments 3
              -> choisit les fenetres, D0 -> M0B -> M1 -> M5 -> M2 -> M2b -> M3
              -> pack dans EXPORT/, ou code 3 (waiting_oracle)
```

**Pourquoi MARK1 ne déclenche pas la transcription :** une transcription est
payée une fois et relue autant de fois qu'on veut. Un appel direct à F00B
la rejouerait à chaque siège, à chaque round ORACLE. Et appeler une frégate
est une hérésie : MARK1 ne parle qu'à ARCHIVUM.

---

## 8. Les portes implémentées (V3.6)

| Porte | Quand | Critère | Si échec |
|---|---|---|---|
| `G0_PACK` | avant tout | `mode=mark1`, `vod_url`, `asset_mode` ∈ {blur, reframing}, assets non vides, bornes dans `[min,max]_segment_sec` | arrêt |
| **`D0_DIRECTIVE`** | M0 | directive lue depuis ARCHIVUM, `campaign_id`, langue connue, payout ≥ plancher, caption_rules | arrêt |
| **`M0B_CYCLE`** | M0b | `cycle.end` ≥ aujourd'hui (règle « follow the announcement for the current cycle ») | **refus : pack périmé** |
| **`M1_SELECTION`** | M1 | segments valides, langue == directive, durée bornée, texte présent | arrêt |
| **`M5_VOX`** | M5 | transcription disponible ou `source_text` fourni | arrêt |
| **`M2_METADATA`** | M2 | overlay valide, titres/descriptions sous les limites, tags, hashtags, `#ad` | arrêt |
| **`M2B_COMPLIANCE`** | M2b | vocabulaire interdit, **focus (déclaratif, V3.6)**, bait, negative PR | arrêt |
| **`M3_WATERMARK`** | M3 | PNG présent pour chaque plateforme obligée, non vide, chemin exploitable. **Ne juge plus l'opacité** (V3.5) : celle-ci est une consigne pour OMNIS_WATCH, elle voyage dans le pack | arrêt |
| `A1_ACCOUNT` | avant export (V3.5) | `warmup_days ≥ 7` (règle C5), `banned == false` | **refus d'exporter** |
| `A2_CAMPAIGN` | avant export (V3.5) | CPM ≥ 0,15 $/1k, `funded == true`, budget > 0, plateforme autorisée | **refus d'exporter** |
| `X1_EXPORT` | finale | `pack_token` présent, `asset_mode` valide, un `clip_token` unique par asset, `exported_at` présent, PNG copié dans `EXPORT/` | rien dans `EXPORT/` |

> **Ordre : M0 → M0b → M1 → M5 → M2 → M2b → M3 → A1 → A2 → M4.**
>
> **Le focus est déclaratif depuis V3.6.** La campagne exige « main focus or
> topic » mais la règle est visuelle (*"as long as she's featured in the
> clip"*) : sur un POV caméra portée, le personnage principal n'est jamais
> nommé. MARK1 ne voit pas la vidéo, donc il **enregistre la déclaration de
> l'opérateur** (`focus_declared` dans le pack d'entrée), la recopie dans le
> pack livrable, et ne refuse que si rien n'est déclaré **et** que le nom
> n'apparaît pas dans le texte (repli de mesure). Sans la déclaration, une
> VOD POV comme TWITCHCON DAY 1 (2 h 53, zéro mention du prénom) était
> refusée à tort. Le `bait`, lui, reste vérifié mécaniquement (recouvrement
> des mots de contenu overlay ↔ texte).

---

## 9. Les 4 pièges

1. **`OUT/` est gitignoré** (`**/OUT/*.json` dans `.gitignore`). Le ledger local ne part
   pas sur GitHub. Seul le **pack dans `EXPORT/`** est récupérable par OMNIS_WATCH — et
   `EXPORT/` **n'est pas** ignoré.
2. **`funded: false` est le vrai risque.** Une campagne non financée ne paie jamais, quel
   que soit son CPM affiché. `A2_CAMPAIGN` la refuse — c'est volontaire.
3. **Oublier `#ad`.** `C2_DISCLOSURE` bloque l'export. Ce n'est pas une précaution : c'est
   une condition de paiement et une protection contre le shadowban.
4. **Croire qu'un titre forge par gabarit est bon.** `generate()` garantit qu'un titre est
   *valide* (longueur, pas de CTA, pas de « ? », un enjeu). Il ne garantit pas qu'il est
   *bon*. La différence est humaine.

---

## 10. Où lire la suite

- `MARK1/README.md` — doc technique de la frégate
- `MARK1/TRACKING/MARK1_LOG.md` — journal d'implémentation + sorties mesurées
- `MARK1/TRACKING/MARK1_V1_V2_CHANGES.md` — écarts V1 → V2
- CDC complet : `MARK1_CDC_V2_CLIPPING.html` (archive V1 : `MARK1_CDC_V1_CLIPPING.html`,
  déprécié)
