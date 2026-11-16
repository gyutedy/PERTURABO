# LES EXCEPTIONS — MARK1 V3

> **Ce document existe pour être lu par quelqu'un qui n'a pas confiance.**
> MARK1 a trois règles absolues. Deux fois, une exception a été ouverte, et
> chaque fois dans **un seul module nommé**. Si le code déroge ailleurs, le
> code est en faute, pas le document.

---

## Les trois règles absolues

| Règle | Sens |
|---|---|
| **R1** | Aucun seuil en dur. Tout nombre qui décide vit dans `config/selection.json`. |
| **R2** | Aucune suppression. MARK1 ajoute, ne retire jamais. |
| **R3** | Aucune vidéo. Jamais de MP4, jamais de ffmpeg sur du contenu, jamais de `.ass`. |

**Conservées intégralement.** Deux autres énoncés ont été abrogés, et
l'abrogation est bornée : voir « Les trois invariants abrogés ».

---

## EXC-1 — `overlay_title` par un LLM contraint

### Le besoin
Un titre d'overlay doit dire l'enjeu en 4 mots. Aucune règle mécanique ne le
produit correctement : c'est un acte de formulation, pas de calcul.

### Le bornage
| Interdit | Où c'est appliqué |
|---|---|
| Le LLM décide des règles | `overlay.constraints()` — les règles viennent de `config/selection.json` |
| Le LLM valide son propre texte | `overlay.accept()` appelle `title_forge.validate()` **et** `s1_context.analyse()` |
| Le LLM boucle indéfiniment | `llm.max_rounds = 3`, codé en config, épuisé dans `overlay.resolve()` |
| Le LLM est obligatoire | Mode ORACLE (aucune clé, aucun réseau) disponible à parité |
| Le LLM invente des faits | Contrainte déclarée + vérification S1 |
| **Une vidéo est produite** | Rien, nulle part : EXC-1 ne produit que du texte |

### Le rayon exact
| | |
|---|---|
| **Autorisé dans** | `M00C_METADATA/CODEBASE/overlay.py` **uniquement** |
| **Fonction d'appel réseau** | `_direct_candidates()` — une seule fonction |
| **Défaut en config** | `llm.enabled: false` → mode ORACLE, zéro réseau |
| **Comment vérifier** | `grep -rn "urllib\|requests\|http" M00C_METADATA/CODEBASE/overlay.py` → 1 résultat attendu (`_direct_candidates`) |

---

## EXC-2 — `M00F_VOX` transcrit un segment

### Le besoin
Le pack doit porter la transcription pour que l'overlay soit ancré sur le
contenu réel, pas sur un titre fourni en amont.

### Le bornage
| Interdit | Où c'est appliqué |
|---|---|
| Le service découpe la vidéo | `vox.py` n'appelle **jamais** ffmpeg ; `ffprobe` lit une durée, c'est tout |
| Un segment trop long part au service | `probe_duration()` + refus explicite au-delà de `vox.piece_sec` |
| Un service absent bloque le siège | `transcribe()` rend `("", raison)` — jamais d'exception |
| Une boucle de retry infinie | 3 essais, backoff `2**attempt`, puis raison explicite |
| **Le service est obligatoire** | Le pack peut porter `source_text` : M5 tolère alors une transcription vide |

### Le rayon exact
| | |
|---|---|
| **Autorisé dans** | `M00F_VOX/CODEBASE/vox.py` **uniquement** |
| **Fonctions externes** | `probe_duration()` (ffprobe) et `transcribe()` (HTTP) |
| **Comment vérifier** | `grep -rn "ffprobe\|ffmpeg" M00F_VOX/CODEBASE/vox.py` → `ffprobe` seulement, **zéro `ffmpeg`** dans tout MARK1 |

---

## Les trois invariants abrogés

Chacun passe d'absolu à **borné à un module nommé**.

| Invariant d'origine | Statut | Bornage |
|---|---|---|
| « Aucun appel réseau » | **abrogé** | Quatre fonctions au total : `overlay._direct_candidates`, `vox.probe_duration`, `vox.transcribe`, et les retries internes. Ailleurs : zéro. |
| « `llm_enabled: false` jamais lu » | **abrogé** | Lu par `overlay.pick_mode()` seul. `false` par défaut, ce qui force le mode ORACLE. |
| « ffprobe interdit » | **abrogé** | Autorisé dans `M00F_VOX/vox.py` pour lire une durée. Aucun autre module. |

---

## Les contrôles

À lancer avant tout siège. Un seul résultat inattendu = STOP.

```bash
# 1. Aucune vidéo n'est produite
#    (attention : ne PAS chercher ".ass" nu, cela matche assert() des tests.
#    On cherche les extensions entre guillemets et les binaires.)
grep -rnE 'ffmpeg|ffplay|\.mp4|\.mov|\.mkv|\.ass"' MONDES_FORGES/CLIPPING/MARK1 --include="*.py" \
  | grep -v "jamais\|interdit\|aucun\|pas de\|ne touche" || echo "  AUCUN (OK)"

# 2. Réseau : seulement EXC-1 et EXC-2
grep -rn "urllib\|requests\|urlopen\|socket" MONDES_FORGES/CLIPPING/MARK1 --include="*.py"

# 3. MARK1 ne parle jamais à F00
grep -rni "F00\|F01\|F02\|F03\|F04\|F05\|F06\|IRON_SENTINEL\|VOX\|COPYWRITER" \
  MONDES_FORGES/CLIPPING/MARK1 --include="*.py"
```

Résultat attendu du contrôle **3** : aucune référence à une frégate F0x en
import ou en appel. Le nom `M00F_VOX` est une sous-frégate de MARK1, pas
`F00B_VOX` — la logique est **copiée**, jamais appelée.

---

## Ce qui n'est pas une exception

| Tentation | Pourquoi c'est refusé |
|---|---|
| « Juste un petit ffmpeg pour normaliser l'audio » | R3. Le découpage est le travail de quelqu'un d'autre. |
| « Le LLM sait mieux que la règle, laissons-le juger » | EXC-1. Le moteur impose, le LLM remplit. |
| « Appeler F00B_VOX, c'est plus propre que copier » | MARK1 ne parle qu'à ARCHIVUM. Un appel à une frégate le ferme. |
| « Le seuil de 4 mots, on peut l'écrire dans le code » | R1. S'il n'est pas dans `config/`, il ne peut pas être audité. |

---

*Document vivant. Toute nouvelle exception doit apparaître ici avec son
rayon exact et sa commande de contrôle, ou elle n'existe pas.*

---

## Ce que MARK1 ne verifie PAS (et ne pretend pas verifier)

Depuis la directive du cycle 2026-07-24, quatre regles existent qui sont
**hors du perimetre de MARK1**, parce qu'il ne produit pas la video :

| Regle de la campagne | Qui la gere |
|---|---|
| Aucun autre logo visible | OMNIS_WATCH (montage) |
| Caption non editee sur IG Reels | l'operateur (saisie plateforme) |
| Post public, commentaires ouverts | l'operateur |
| Engagement organique normal | la plateforme / le ledger |

**Les mettre dans MARK1 serait du theatre.** Une porte qui pretend verifier
ce qu'elle ne peut pas voir est pire qu'une porte absente : elle donne une
fausse assurance.

En revanche, ces regles SONT verifiees par MARK1 parce qu'il produit le texte :
- **main focus** -> presence du sujet dans la transcription (`compliance.focus_report`)
- **pas de bait** -> overlay soutenu par le texte source (`compliance.bait_report`)
- **pas de negative PR** -> marqueurs d'attaque (`compliance.negative_pr_report`)
- **vocabulaire interdit** -> nettoyage + refus sur overlay (`compliance.scrub`, `check_asset`)
