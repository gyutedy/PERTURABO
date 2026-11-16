# AUDIT — constats croisés MARK1 ↔ LACRIMAE

> **Copie a la racine de PERTURABO.** La version qui fait foi vit a la racine
de LACRIMAE (gyutedy/LACRIMAE-FULL, branche sanguinala-v1).
> Problemes MARK1 (M1-M4) : a traiter ici. Problemes LACRIMAE (L1-L6) : a
traiter dans LACRIMAE-FULL.



 — constats croisés MARK1 ↔ LACRIMAE

> Document racine. Chaque problème est daté et décrit avec sa cause et sa
> conséquence. Aucun correctif n'est appliqué ici : ce document EST la liste
> de travail. VOD de référence du cycle : `https://twitch.tv/videos/2927914500`.

---

## Partie 1 — Problèmes constatés sur MARK1 (le bras qui produit le pack)

Tous constatés en date du 2026-11-16 sur le pack
`production_pack_mark1_e99bd523.json`.

### M1. Titres d'overlay hachés / grammaticalement cassés

| Asset | bornes | overlay_title produit | texte source réel |
|---|---|---|---|
| A01 | 10328 → 10358 | She lost 50,000 dollars | « I looks like it's like 50,000 dollars » |
| A02 | 8616 → 8646 | **She lost 86,000 seconds** | « Yo, being timed out for 86,000 seconds is » |
| A03 | 2375 → 2405 | **She paid 385 was much** | « I feel like 385 was a bit much, » |

**Cause** : en mode ORACLE (mode 2, sans clé LLM), le titre vient d'une
réponse humaine collée dans `ORACLE/answers.json`. La porte `accept()` vérifie :
`title_forge.validate()` (mots max, CTA, ponctuation) et `s1_context.analyse()`
(entités inexpliquées). **Aucune de ces deux règles ne vérifie que le titre est
une phrase grammaticalement correcte.**

**Conséquence** : les titres hachés passent toutes les portes. A02 déforme le
sens (86 000 s = 24 h de timeout Twitch, pas une « perte »). A03 n'est pas de
l'anglais. En production, ces titres partent à l'écran sur TikTok.

**Piste** : ajouter un contrôle de grammaticalité (détection de fragments :
titre commençant par un verbe conjugué haché, absence de sujet, fragments
prépositionnels orphelins), ou contraindre davantage le prompt ORACLE avec le
texte source complet au lieu d'un fragment.

### M2. `source.directive_path` = chemin local Windows

```json
"source": {
  "directive_path": "D:\\mes couilles\\_perturabo_tmp\\MONDES_FORGES\\CLIPPING\\ARCHIVUM\\..."
}
```

**Cause** : `directiva.run()` écrit le chemin absolu de la machine qui a lancé
le siège.

**Conséquence** : inutile et hostile. Ne veut rien dire pour GitHub Actions,
ni pour le consommateur du pack. Les références doivent être `campaign_id`
+ `source_file` relatifs au repo.

### M3. Le pack MARK1 ne porte pas de `vod_url`

Le pack MARK1 a `source.campaign_id` mais **aucune `vod_url`**. Or LACRIMAE et
`F00_SOURCE` ne peuvent rien télécharger sans elle.

**Cause** : le siège MARK1 travaille sur une transcription F00B_VOX déjà
produite ; la VOD n'est pas une entrée de MARK1.

**Conséquence** : le pack seul est inutilisable pour un rendu. L'adaptateur
(`lac_adapter_mark1`) doit injecter la `vod_url` — actuellement fournie à la
main : `https://twitch.tv/videos/2927914500`.

### M4. Contrat de format absent : `mode: mark1` ≠ `mode: pur`

| | MARK1 produit | LACRIMAE attend |
|---|---|---|
| `mode` | `mark1` | `pur` |
| bornes | `assets[].start_sec` | `source.start_sec` / `montage_instructions` |
| granularité | 1 pack = N assets | 1 pack = 1 clip |

**Cause** : MARK1 a été conçu autonome, sans connaître le contrat PUR.

**Conséquence** : le bridge actuel (`BRIDGE/CODEBASE/lac_bridge_forge.py`)
refuse le pack à `G0 : mode != pur`. L'adaptateur est indispensable, il n'y a
pas de chemin direct.

---

## Partie 2 — Problèmes constatés sur LACRIMAE (le bras qui rend le MP4)

Tous constatés en date du 2026-11-16, branch `sanguinala-v1`.

### L1. Crash Windows sur le caractère « → » (U+2192)

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
  File "run_all.py", line 381, in main  →  print(msg) → cp1252
```

**Cause** : `log()` fait `print(msg)` sans forcer l'UTF-8. La console Windows
est en cp1252, qui ne connaît pas `→`.

**Conséquence** : le crash survient **après** les portes G0/G0-S pourtant
vertes — le pack est accepté puis le script meurt. Trompeur : on croit que le
problème est le pack, alors que c'est l'encodage.

**Contournement existant** : `export PYTHONIOENCODING=utf-8`.
**Correction attendue** : `sys.stdout.reconfigure(encoding="utf-8")` en tête
de `run_all.py`, ou `hide` des caractères non-ASCII des logs.

### L2. `node_modules` absent dans F01_LOOK

`F01_LOOK/CODEBASE/package.json` déclare Remotion 4 + React 18, mais
`node_modules/` n'existe pas. **Prérequis** : `npm install` dans
`F01_LOOK/CODEBASE` avant tout rendu (`render_pictor.mjs`).

### L3. `REVIEW/sanguinala_review.json` absent

`REVIEW/` ne contient que `README.md` + `.gitkeep`. Le code **tolère**
l'absence (`W1 REVIEW: JSON absent — titres/watermark pack bruts`), donc le
run continue — mais la validation opérateur est contournée silencieusement.
Avec `--require-previews`, la porte `W1` passe en FAIL. **Décider** : est-ce
qu'un siège doit exiger le review ?

### L4. Workflow `dev10_pur_render.yml` pointe vers un repo inexistant

```yaml
perturabo_repo:   "jfbjfojfonf/PERTURABO"
perturabo_branch: "v2-live-vox-c"
```

Le pack réel est sur **`gyutedy/PERTURABO`**, branche
**`pari-forge-perturabo-xs4c`**. Tel quel, le workflow cherche le pack au
mauvais endroit et échouerait (fetch 404).

### L5. Fixture `twitch.tv/videos/0` court-circuite yt-dlp

`is_fixture_vod()` détecte un VOD terminant par `/videos/0` et saute le
téléchargement **sans** créer les MP4 sources. La chaîne F01→F06 ne peut donc
pas être validée avec la fixture seule : il faut un vrai VOD ou fournir
`--look-dir` avec des MP4 pré-rendus.

### L6. `python3` absent sous Windows

Le README dit `python3 run_all.py` ; Windows ne connaît que `python`. Sans
conséquence fonctionnelle, mais cohérence du guide à prévoir.

---

## Section 3 — Chaîne cible (ce que le document prépare)

```
production_pack_mark1_*.json   (MARK1, mode: mark1, N assets)
        │
        ▼
lac_adapter_mark1.py           (BRIDGE — éclate N → N packs PUR, injecte
        │                       vod_url + montage_instructions minimum)
        ▼
dev10_pur_render.yml           (corrigé : gyutedy/PERTURABO,
        │                       pari-forge-perturabo-xs4c)
        ▼
F00_SOURCE yt-dlp → F01_LOOK Remotion 9:16 → F02 → F03 → F05 → F06
        ▼
OUT/*.mp4
```

## État de chaque constat

| # | Constat | Sévérité | Corrigé ? |
|---|---|---|---|
| M1 | titres hachés | haute | non |
| M2 | directive_path local | moyenne | non |
| M3 | vod_url absente | haute | **RESOLU** par l adaptateur (--vod-url) |
| M4 | format mark1 vs pur | haute | **CORRIGE** (BRIDGE/lac_adapter_mark1.py) |
| L1 | crash « → » cp1252 | haute | **CORRIGE** (run_all.py reconfigure UTF-8) |
| L2 | node_modules absent | blocante | non |
| L3 | review absent | moyenne | toléré |
| L4 | workflow mauvais repo | blocante | **CORRIGE** (gyutedy/PERTURABO, pari-forge) |
| L5 | fixture sans MP4 | moyenne | non |
| L6 | python3 vs python | basse | non |

---

## Section 4 — Correctifs appliques le 2026-11-16

### L1 — CORRIGE
`run_all.py` reconfigure `sys.stdout` et `sys.stderr` en UTF-8 avec
`errors="replace"` a l'import. Plus besoin de `PYTHONIOENCODING`.
Verifie : le dry-run affiche la fleche dans les logs sans variable
d'environnement.

### L4 — CORRIGE
`.github/workflows/dev10_pur_render.yml` pointe desormais
`gyutedy/PERTURABO` + `pari-forge-perturabo-xs4c` (defaut ET repli dans le
script inline).

### M4 / M3 — CORRIGE
Nouveau `BRIDGE/CODEBASE/lac_adapter_mark1.py` : lit un pack MARK1, injecte
`--vod-url`, eclate chaque asset en un pack PUR autonome.

Verifie de bout en bout :

    python BRIDGE/CODEBASE/lac_adapter_mark1.py         --pack ../pack_e99.json         --vod-url https://twitch.tv/videos/2927914500 --out /tmp/pur_test

    -> 3 packs PUR (A01, A02, A03), style blur

    python BRIDGE/CODEBASE/lac_bridge_forge.py --pur         --pack /tmp/pur_test/production_pack_pur_e99bd523_A01.json --dry-run

    -> [ok] Pack PUR valide : e99bd523-A01 | segment 10328.0s -> 10358.0s

La chaine MARK1 -> PUR -> bridge est bouclee.

### Restent ouverts
| # | Constat | Note |
|---|---|---|
| M1 | titres haches | non corrige : MARK1 ne mesure pas la grammaticalite |
| M2 | directive_path local | non corrige : chemins absolus dans le pack |
| L2 | node_modules absent | prerequis : `npm install` dans F01_LOOK/CODEBASE |
| L3 | review absent | decision a prendre : exiger le review ? |
| L5 | fixture sans MP4 | utiliser un vrai VOD ou `--look-dir` |
| L6 | python3 vs python | coherence du README |
