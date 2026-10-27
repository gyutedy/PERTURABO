# Template — Capture / OCR (input cotes)

> À remplir quand une capture screenshot est utilisée comme source de cotes.
> Ce template n'est **pas une transcription de vidéo**, c'est un fiche métier de capture/OCR.

## Métadonnées de la capture

- **Date de la capture** : AAAA-MM-JJ
- **Heure de la capture** : HH:MM (dans la timezone du bookmaker affiché)
- **Source / bookmaker** : nom du bookmaker ou page vue
- **Ligue affichée par le bookmaker** : code ou nom (ex : `E0`, `La Liga`, `Ligue 1`)
- **Compétition affichée** : championnat / coupe / autre
- **Type de capture** : ton bookmaker / web externe / autre
- **Statut de la ligue** : connue (affichée) / flou (à confirmer) / aucune (à demander)

## Matchs visibles dans la capture

| Équipe domicile | Équipe extérieur | Marché | Cote lue | Cote corrigée après validation | Heure match (affichée) | Notes |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Cotes attendues / marchés

- 1X2 (win / draw / lose)
- Over/Under 2.5 (si disponible)
- Mi-temps (MT1 / égalité / MT2) si disponible

## Résultat OCR reconstitué (avant validation)

> À remplir depuis le texte OCR produit, avant validation humaine.

```json
[
  {
    "match": "teamA vs teamB",
    "ligue": "E0",
    "cotes": {
      "1X2_win": null,
      "1X2_draw": null,
      "1X2_lose": null,
      "ou25": null,
      "mt1": null,
      "mt2": null
    }
  }
]
```

## Validation humaine (obligatoire avant calcul)

- [ ] Le JSON reconstitué a été affiché à l'utilisateur
- [ ] Les cotes ont été vérifiées champ par champ
- [ ] La ligue est confirmée (pas devinée sauf si affichée clairement)
- [ ] Aucun marché inventé n'a été conservé
- [ ] L'heure de la capture est notée
- [ ] La source est notée dans le ticket / ledger

## Notes de contexte (non-binaire)

> Blessures, fatigue, enjeu, contexte — uniquement en note de porte, jamais dans le calcul.

- Contexte saisi : 
- Source de l'info : 
- Date de l'info : 
- Fraîcheur : OK / À vérifier / OBSOLÈTE SI

## Destination

- Si validation OK → injection dans carte en tant qu'input cotes
- Si validation NOK → correction + revalidation, pas de calcul\n