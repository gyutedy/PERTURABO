# RÈGLE — Fraîcheur des sources (toute la zone knowledge_base)

> Défaut de conformité = la donnée devient **NON UTILISABLE** pour une décision.
> Obligation de cibler le re-dépassement de l'applicable si RATIO.

## Art. 1 — Deux dates minimum, aucune exception

Toute source d'information (transcription vidéo, article, capture, statistique
d'une tierce source) porte :

1. **date de publication de la source** (AAAA-MM-JJ) — la date sur YouTube.
2. **date de récupération / archivage** (AAAA-MM-JJ) — jour de la pose dans le monde.

Pas de date = fichier accepté mais marqué `TO_CONFIRM` : examinable, **jamais**
citée dans un siège, un verdict TYRANT ou un pari_pack sans confirmation.

## Art. 2 — Règle d'interaction (règle d'obsolescence)

Avant toute utilisation d'un fait sortant d'une source :
- si la source parle de **saison en cours** (saison 26/27 par ex.) → utilisable ;
- si la source date d'**≥ 1 saison** → le fait doit être **recroisé** avec une
  source récente avant usage (stats, calendrier, effectifs, cotes) ;
- si seule (sans source récente) → mention « OBSOLÈTE SI » sur la fiche.

La fiche (`TPL_fiche.md`, § verdict sur l'âge des infos) décide de l'application :
Oui / Non / À recroiser + justification + source de recoupement.

## Art. 3 — Vérification permanente

`python3 ingest_transcripts.py --freshness [jours]` à tout moment (en Action
quotidienne en option), signaler :
- sources **sans date de publication** ;
- transcriptions de **> N jours** à recroiser avant usage.

## Art. 4 — Place du roulage à la source (qui décide)

- Les fiches d'analyse (dépouillement) portent un **verdict d'âge** obligatoire.
- TYRANT **n'écoute pas** un fait sans verdict d'âge.
- Le moteur de probabilités (BREACHER/FORGEWARD) **n'utilise jamais** le contenu
  des transcriptions ( doctrines / hérésiyes interdites) ni des fiches —
  stats froides uniquement.
