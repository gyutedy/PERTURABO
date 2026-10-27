# RESSOURCES — transcriptions YouTube « The Football Bank »

Zone d'archivage des transcriptions de la chaîne YouTube @thefootballbank2924
(longueur : 64 vidéos au 2026-10-27).Elle alimente la **doctrine** du monde PARI
(filtres, marchés, réflexes) — JAMAIS les calculs de probabilités (hérésie = biais de survie).

## Règle d'archivage (obligatoire)

Voir `ARCHIVUM/rules/freshness_sources.md`. Deux dates minimum par ressource source :

- **date de publication** de la vidéo (upload YouTube, AAAA-MM-JJ) ;
- **date de récupération** de la transcription (jour où on l'a posée ici, AAAA-MM-JJ).

Ce qui permet de croiser : vidéo de 2024 (données saison antérieure) × article 2026
→ savoir si l'info est encore **applicable**, **obsolète**, ou **à recécicher** avant
de l'utiliser dans une décision du monde.

## Structure des répertoires

```
RESSOURCES/
  catalogue_videos.csv       ← registre maître des 64 vidéos (id, titre, url, upload_date, catégorie, fichier, date_recuperation, statut, notes)
  TPL_transcription.md       ← gabarit d'un fichier de transcription brute
  TPL_fiche.md               ← gabarit d'une fiche d'analyse (dépouillement)
  ingest_transcripts.py      ← script d'ingestion automatique (voir ci-dessous)
  README_RESSOURCES.md
  <CATEGORIE>/transcripts/   ← transcriptions brutes classées (GENERAL, OVER_UNDER, BTTS, HOTPICKS, CHALLENGE, KEYS, FOOTUPDATE, LIVE, QUIZCHALLENGE, PATREON, SERIEB, OTHER)
  <CATEGORIE>/fiches/        ← fiches de dépouillement
```

## Utilisation du script (Warsmith)

Placer les transcriptions brutes venant de ton outil externe dans un dossier quelconque,
puis :

```bash
# ingérer (créé le fichier .md au bon endroit + met à jour le catalogue)
python3 ingest_transcripts.py --add <chemin_dossier_ou_fichiers> ...

# confirmer/résumer les dates de publication YouTube après coup
python3 ingest_transcripts.py --dates dates.csv      # lignes : id,date
#   ou à la main :
python3 ingest_transcripts.py --dates <id>=YYYY-MM-JJ [<id>=YYYY-MM-JJ ...]

# marquer le statut de dépouillement
python3 ingest_transcripts.py --status <id>=depouille [<id>=... ]   # brut|depouille|a_valider

# vérifier la fraîcheur : sources sans date, transcriptions vieilles, fiches sans recouplement
python3 ingest_transcripts.py --freshness [nb_jours=90]
```

## Statuts possibles (statut_transcription)

- **brut** : transcription déposée, non lue ;
- **a_valider** : testée, validée ;
- **depouille** : fiche d'analyse produite dans `<CATEGORIE>/fiches/` (référencer le fichier de la fiche dans la colonne notes du catalogue).
