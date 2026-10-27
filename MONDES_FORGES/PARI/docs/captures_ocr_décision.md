# Décision — Flux capture screenshot → OCR → cotes (parallèle TXT/JSON)

**Décidé manuellement, hors code — documentation de contrat utilisateur.**
À consommer par le GUIDE + le contrat quant avant toute implémentation.

## 1. Ce qui est confirmé par ton bookmaker

Le bookmaker affiche nativement :
- Ligue
- Compétition (coupe / championnat)
- Cote(s)
- Date
- Heure
- Équipes

Donc : **la ligue n'est plus une question ouverte pour une capture propre de ton bookmaker**.
L'IA/OCR peut extraire ces champs, la ligue est connue par le livreur affiché, pas devinée.

## 2. Ce que le flux capture/OCR devient

Il est **autorisé comme input de cotes**, en parallèle des deux flux existants :
- TXT brut (papier ou copier-coller)
- JSON direct (colle dans la carte)
- **Capture screenshot → OCR → texte → parseur → validation → analyse**

Ce n'est **pas** une source de probabilité.
Ce n'est **pas** une source de stats.
Ce n'est **pas** du modèle.

## 3. Ce qu'on ne change pas

- Le moteur de probabilités continue de n'utiliser que les stats froides.
- Les non-binaires (blessures, fatigue, contexte) restent des notes de porte, jamais dans le calcul.
- La validation du parseur (cotes reconstituées affichées à l'utilisateur avant calcul) n'est pas supprimée, elle s'applique aussi aux OCR.
- Zero Data, Zero Calc : si la capture ne donne pas les champs minimums (équipes, ligue, cotes), on ne devine pas — on bloque en porte et on demande.

## 4. Règle de non-implication

On ne peut ni coder ni planifier l'implémentation OCR tant que :
- le contrat utilisateur (ci-dessous) n'est pas clair dans le GUIDE
- le contrat quant a bien intégré que "cotes uniquement, fraîcheur obligatoire, parseur obligatoire"
- la documentation a un template de capture/OCR pour capitaliser la donnée sans polluer le corpus

## 5. Historique (réouverture plus tard)

Ce mémo est la base de l'histoire future (logs, dashboard, résidus, rejeu).
À réouvrir uniquement après implémentation du pipeline de capture/OCR.

---

*Décision prise avant code, documentée ici, rattachée au commit de docs.*
