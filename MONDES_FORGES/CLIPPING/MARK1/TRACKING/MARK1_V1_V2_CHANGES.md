# MARK1 — écarts V1 → V2

Ce fichier existe parce que des agents de codage ont lu le **V1** de ce cahier des charges
(`MARK1_CDC_V1_CLIPPING.html`) et en ont peut-être tiré des plans. Le V1 n'est **pas** faux sur
l'analyse : il est faux sur la **nature de la sortie**. Tout ce qui suit sont les écarts
qu'un agent doit connaître **avant** d'écrire la première ligne.

Référence de vérité : `MARK1_CDC_V2_CLIPPING.html`. En cas de désaccord entre ce fichier et le V2,
**le V2 gagne**, et ce fichier doit être corrigé.

---

## 0. Le changement en une phrase

> **MARK1 V1 produisait un MP4 1080×1920. MARK1 V2 produit un pack JSON livrable dans `EXPORT/`.**

Le rendu vidéo appartient au **consommateur externe** (générique, non nommé). Ce n'est pas un
report (§13) : c'est un **retrait définitif**, pour une raison de doctrine, pas de calendrier.

**Doctrine citée, README de `MONDES_FORGES/CLIPPING` :**
> « Le forge CLIPPING ne touche **jamais** une vidéo. Il décide **quoi** clipper, sous **quel** angle,
> avec **quel** texte — et livre à OMNIS_WATCH un `production_pack.json` prêt à consommer. »

Un moteur qui encode dans la forge crée une exception — et c'est toujours la frégate la plus récente
qui l'invoque en premier. MARK1 était cette exception. V2 la referme.

---

## 1. Ce qui disparaît — à ne pas recréer

| Fichier / élément V1 | V2 | Motif |
|---|---|---|
| `libs/render.py` (66 l.) | **supprimé** | Encodait le MP4 via ffmpeg. Doctrine. |
| `libs/ass_builder.py` (52 l.) | **supprimé** | Construisait le fichier `.ass` pour le rendu. Doctrine. |
| Porte `R1_RENDER` | **remplacée par `X1_EXPORT`** | Vérifiait un MP4 (taille, dimensions, codec). Vérifie désormais le pack. |
| Commande `mark1.py render` | **remplacée par `mark1.py export`** | Même raison. |
| Champ d'entrée `canvas` | **retiré du pack** | Son seul lecteur était `render.py`. Le format d'écran est une propriété du consommateur. |
| Clés de config `blur_sigma`, `video_w`, `video_h`, `caption_max_words_per_line`, `filters` | **retirées** | Toutes n'avaient de lecteur que dans `render.py`. `filters` était déjà mort en V1. |
| Test E2E « MP4 1080×1920 re-mesuré par ffprobe » | **supprimé** | Il n'y a plus de MP4 à mesurer (§10.2 du V2). |
| Dépendance `ffmpeg` + `libass` | **retirée** | MARK1 V2 est **stdlib seule**. |

**Ne pas** réintroduire ffmpeg « juste pour un preview ». Le V2 dit explicitement pourquoi (§13) :
*le preview, c'est le pack — et si vous voulez voir une vidéo, c'est le consommateur qui la rend.*

---

## 2. Ce qui apparaît — à créer

| Élément V2 | Détail |
|---|---|
| `libs/tokens.py` (46 l.) | `pack_token(pack)` → 8 car. hex, stable, insensible à l'ordre des clés. `clip_token(asset_id, date, pack_token)` → `A01-20261115-3f9a1c07`. `clip_tokens(pack)` → un token **par clip**. |
| Porte `X1_EXPORT` | Vérifie : pack écrit, JSON relisible, `mode == "mark1"`, `render.style ∈ allowed_render_styles`, **un `clip_token` unique par asset**, aucune clé morte. |
| Commande `mark1.py export` | Enchaîne `G0_PACK → A1_ACCOUNT → A2_CAMPAIGN → S2_DURATION → X1_EXPORT`, écrit le pack dans `EXPORT/`, écrit **une ligne de ledger par clip**. |
| Champ **`asset_mode`** ∈ {`blur`, `reframing`} | **Input transmis**, jamais exécuté. Nom réel du terrain (`production_pack_asf_c1.json`, `liber_clipping.json`). Le vocabulaire complet de la forge est `split\|reframing\|ranking\|blur` (`caviar_director.py:34`) : MARK1 n'admet que les **deux éprouvés**. |
| Porte **`C2_DISCLOSURE`** (NOUVEAU) | Règle C2 de `CONTRACTS/clipping_rules.md` : `#ad`/`#sponsored` obligatoire dans la caption. **Absente du CDC V1 et V2**, ajoutée à l'implémentation. |
| Colonnes ledger `pack_token`, `clip_token`, `render_style`, `clip_url`, `exported_at` | Le ledger est apparié **par `clip_token`**, jamais par titre/date/ordre. |
| §17 du V2 | Contrat d'interface du futur outil de statistiques : 2 entrées, 1 point d'écriture, 5 interdits. |

---

## 3. Ce qui change de valeur — chiffres à ne pas recopier du V1

| Grandeur | V1 | V2 | Pourquoi |
|---|---|---|---|
| Nombre de fichiers | 14 | **12** | −`render.py`, −`ass_builder.py`, +`tokens.py` |
| Nombre de lignes de code | 922 | **1 326** | mesuré par `wc -l` (`DÉDUIT` du CDC : ~820 — sous-estimé) |
| Nombre de tests | 28 | **36** | Tests de rendu retirés ; tests de tokens, `X1_EXPORT` et `C2_DISCLOSURE` ajoutés. Le CDC annonçait 24 : c'est le nombre réel mesuré qui fait foi (`Ran 36 tests ... OK`). |
| Nombre de portes | 11 | **11** | `R1_RENDER` → `X1_EXPORT`, pas d'ajout |
| Portes **implémentées** | 8 | **6** (+ `C2_DISCLOSURE` nouvelle) | `R1_RENDER` retirée, `X1_EXPORT` ajoutée, `C2_DISCLOSURE` ajoutée |
| Commandes CLI | 7 | **7** | `render` → `export` |
| Colonnes ledger | 25 | **26** | +`clip_url` (appariement), `clip_id`→`clip_token` |
| Fonctions du moteur | 5 | **3** | Filtrer, Titrer, Exporter+mesurer |
| Sortie | MP4 1080×1920 | **pack JSON dans `EXPORT/`** | doctrine |
| Dépendances | Python + ffmpeg + libass | **Python seul** | — |
| Compute par clip | ~6 s CPU | **~0 s** (chez le consommateur) | — |
| Budget J2 | 5 h | **4 h** (13 h au total) | plus de rendu à vérifier à l'œil |

---

## 4. Ce qui NE change pas — le socle est intact

Ces points sont identiques en V1 et V2. Un agent qui a lu le V1 sur ces points a eu raison.

- **Zéro suppression dans `MONDES_FORGES/CLIPPING`.** MARK1 vit à côté, dans `CLIPPING/MARK1/`.
- **Zéro appel réseau** dans `MARK1/` (invariant §16.3 n°1).
- **Zéro seuil en dur** : tout dans `config/selection.json` (invariant §16.3 n°2).
- **`llm_enabled` reste `false` et rien ne le lit** (invariant §16.3 n°3).
- **LLM hors du verdict de sélection** (décision D2).
- **S1 — auto-suffisance contextuelle** : même 5 tests, même hypothèse **non validée**, même
  condition de renversement (§13).
- **12 gabarits de titres, `generate()` ne rend que des titres valides** (bug D7).
- **Économie** : `net_per_1k`, `views_needed`, `approval_rate`, `cap_usd_per_clip`, `usd_per_hour`.
- **Éligibilité des campagnes** : planchers, `funded`, `platforms`.
- **Ledger idempotent**, `append` refuse une ligne sans `clip_token`.
- **Les 4 coquilles de transcription du V1** (§8) sont corrigées dans le code V2 et documentées
  dans `MARK1_LOG.md`, conformément à la décision B.

---

## 5. La règle pour un agent qui reprend ce dossier

1. **Lire le V2, pas le V1.** Le V1 est conservé en archive, avec un bandeau, uniquement pour
   l'analyse du §1 (diagnostic du code existant) qui reste valable et non refaite.
2. **Si vous avez un plan basé sur `render.py`, `ass_builder.py`, `R1_RENDER` ou `canvas` :
   jetez-le.** Il décrit un moteur qui n'existe plus.
3. **Le critère de réussite n'est plus un MP4 vérifié par `ffprobe`.** Il est : *un pack dans
   `EXPORT/` et une ligne de ledger par clip* (§12.1 du V2).
4. **Les sorties des §9 et §10 du V2 sont marquées `ATTENDU`.** Elles n'ont jamais été exécutées.
   Dès la première exécution, **remplacez-les par la sortie réelle** et consignez l'écart dans
   `MARK1_LOG.md` (§16.2, étape 6).
5. **En cas de doute sur une valeur numérique du V2 marquée `DÉDUIT`** : elle est estimée, pas
   mesurée. Mesurez, puis corrigez le V2. Ne traitez jamais une valeur `DÉDUIT` comme une preuve.
