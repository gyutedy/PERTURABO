# GUIDE_UTILISATION — PERTURABO CLIPPING

> Le mode d'emploi du forge CLIPPING pour les **futurs champions (opérateurs)** et les **oracles**.
> Tout ce qu'il faut savoir pour lancer un siège **sans connaître l'historique du développement**. Le Champion reste l’unique autorité de validation.

---

## 📚 Ce dossier

Ici, **un guide par mode**. Chaque guide explique, étape par étape et avec les **commandes exactes**, comment mener un siège de A à Z : ce que tu fournis, ce que les frégates produisent, ce que tu valides à chaque gate, et ce qui part chez **LACRIMAE**.

## 🗂️ Les guides

| Fichier | Mode | Statut |
|---|---|---|
| `00_COMMENCER_ICI.md` | Tous | ✅ Le strict minimum pour lancer un siège |
| `01_MODE_LOGO_INFORMATIF.md` | **logo / informatif** | ✅ **Complet** (testé en production, siège TS01_SANDOVAL) |
| `02_MODE_LOGO_HUMOUR.md` | logo / humour | ⏳ À compléter (même squelette) |
| `03_MODE_WHOP.md` | whop (clip canon) | ⏳ À compléter (même squelette) |
| `04_MODE_MEME.md` | logo / meme | ✅ **Opérationnel** (10 angles, tweet/motion contextualisés, LACRIMAE) |
| `06_RECHERCHE_SUJETS_US_YOUTUBE_MEME.md` | Recherche | ✅ Profil US / YouTube Shorts / niche meme |
| `07_HORIZONS_RECHERCHE.md` | Recherche | ✅ Fenêtres 2h / 6h / 12h / 24h / 3d / 7d / 30d |
| `08_DISCOVERY_MARKET_DEMONS_RED_BLUE.md` | Discovery | ✅ Marché, Démons, océans rouge/bleu et validation |
| `09_DIRECTEUR_PROSPECTION_PREMIUM.md` | Discovery | ✅ Questions premium, collecte Oracle et anti-invention |
| `11_MODE_PUR.md` | PUR long-form | ✅ 4 gates, `pur.py`, F05 — **distinct du PUR direct** |
| `13_MODE_PUR_VOX_ET_CAMPAGNES.md` | PUR direct | ✅ 2 entrées F00B / F00C → un tronc |
| `14_GUIDE_OPERATEUR_PUR.md` | PUR opérateur | ✅ Parcours des 2 entrées + schéma canonique |
| `18_MODE_LIVE_V2.md` | **live (branche `v2-live`)** | ✅ radar chat temps réel, gate hybride, board téléphone |
| `19_MODE_VOX_C_YOUTUBE.md` | **VOX-C (F00C)** | ✅ YouTube/Twitch/local + pont PUR `--to-candidats` |
| `20_NOTE_TECHNIQUE_PUR_BRIDGE_F00C.md` | Note technique | ✅ Unité du schéma `candidates` |
| `22_MODE_CERVEAU_PARTAGE.md` | **Cerveau partagé** | ✅ premium → oracle (relais) → off (F00B/F00C/F04) |
| `23_MODE_ORACLE_RELAY.md` | **Oracle relay** | ✅ raisonner sans clé (questions → réponses, `ORACLE/`) |
| `_PIEGES_APPRIS.md` | Tous | ✅ Les leçons du siège test — **à lire avant chaque siège** |
| `_PIEGES_APPRIS_PUR.md` | PUR | ✅ Pièges PUR + pont F00C |

## 🧭 Comment naviguer

1. **Premier lancement** → lis `00_COMMENCER_ICI.md`
2. **Avant chaque siège** → relis `_PIEGES_APPRIS.md` (5 minutes, ça évite les erreurs déjà payées)
3. **Recherche de sujet** → lis `06_RECHERCHE_SUJETS_US_YOUTUBE_MEME.md`, `07_HORIZONS_RECHERCHE.md`, `08_DISCOVERY_MARKET_DEMONS_RED_BLUE.md` et `09_DIRECTEUR_PROSPECTION_PREMIUM.md`
4. **Mode utilisé** → ouvre le guide du mode (ex : `01_MODE_LOGO_INFORMATIF.md`)
5. **Doute en cours de siège** → reviens sur la section concernée du guide

## ➕ Comment ajouter un guide (nouveau mode)

Chaque guide suit le **même squelette** — duplique un guide existant et remplis. En mode meme, les champs réels (`tweet.text`, `text_emotion`, métadonnées) priment sur l’ancien schéma généraliste :

1. **Le but en 3 lignes** (ce que fait le mode)
2. **Les inputs** (ce que le champion doit fournir, format, exemple)
3. **Le chemin complet** — les 4 gates avec les commandes EXACTES
4. **La clé premium** (avec clé / backup `--oracle`)
5. **Les règles verrouillées** (garde-fous)
6. **Le livrable final** (pack + EXPORT + liens GitHub)
7. **Checklist rapide avant chaque gate**

Règle de nommage : `NN_MODE_<PROFIL>_<SOUS_MODE>.md` (NN = ordre, 2 chiffres).

## 🏗️ Rappel de l'architecture (en bref)

```
F00_CAPTEURS     → en pause en MEME V2 ; actif seulement pour les anciens scans
F01 SCOUT        → archive et contrôle la source sociale fournie (Gate 1)
F02 TYRANT CAMP  → analyse source/marché et verdict
ANGLESMITH (F02) → forge les angles de réaction (Gate 2)
F03 SOURCE HUNTER→ ignorée en mode MEME V2
F04 COPYWRITER   → forge reaction_tweet + text_emotion + métadonnées (Gate 3)
F05 PACKAGER     → assemble source + transformation (Gate 4)
F06 TRACKER      → suit les posts après publication
ORCHESTRATOR     → le nerf central : gates + ledger + expédition
```

**Mode MEME V2** : le Champion fournit un **tweet ou post Reddit réel**, sa copie textuelle, sa capture, son URL, son auteur, sa date et ses métriques disponibles → F01 archive et contrôle la source → F02/ANGLESMITH analyse et forge jusqu’à 10 réactions distinctes → F04 produit un `reaction_tweet` puissant, un `text_emotion` contextualisé et les métadonnées → l’opérateur valide → F05 assemble source + transformation avec la balise choisie, par exemple `M1` → l’opérateur valide puis copie dans `EXPORT` → **LACRIMAE** monte via `04_MODE_MEME.md`. **F00 est en pause et F03 est ignorée en MEME V2.**

**Vocabulaire** : on dit **gate** (ou porte) — `gate 1` à `gate 4`. Le champion **valide ou rejette** chaque gate. Rien ne passe sans ta signature.


## Addendum MEME V2 — sourcing manuel et réaction originale

Le mode MEME V2 ne démarre plus par un mot-clé inventé par le forge. Le Champion fournit un tweet ou post Reddit réel, sa copie textuelle, une capture, son URL, son auteur, sa date et les métriques disponibles. F01 archive et contrôle cette source ; F00 reste en pause dans ce mode.

La source (`source_post`) est distincte de la transformation PERTURABO (`reaction_tweet`). ANGLESMITH forge des lectures réellement différentes, F04 produit une réaction puissante ciblée sur le marché, puis un `text_emotion` simple et contextualisé, et F05 assemble le tout pour LACRIMAE. Le Champion reste l’unique autorité des Gates.

Référence détaillée : `04_MODE_MEME.md` et `05_NOTE_PERTURABO_PACK_MEME.md`.

En V2, la copie textuelle du post reste un input interne F01. La capture PNG contenant le tweet et son image est obligatoire dans le pack final et s’affiche au-dessus du clip mème de la release LACRIMAE. Le pack contient aussi `reaction_tweet`, `text_emotion`, les métadonnées, `clip_id`, `meme_tag` et `channel_id`. L’Opérateur fournit le tag et la chaîne ; F05 assemble ; LACRIMAE produit la vidéo finale.
