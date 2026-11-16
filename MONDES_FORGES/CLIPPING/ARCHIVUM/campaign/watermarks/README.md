# Watermarks — Règles de Gestion

## Stockage
Les fichiers watermark sont stockés dans :
```
ARCHIVUM/campaign/watermarks/
├── [creator_name]_watermark.png     (ou .jpeg / .jpg)
├── [creator_name]_watermark_preview.png
└── README.md
```

Nommage réel attendu par `M00D_VEXILLUM` : le **slug** du `creator_name`
sans accent ni espace (`Aishah Sofey` → `aishahsofey`). La résolution essaie
`<slug>`, puis `<slug>_1`, puis tout `<slug>*`.

## Formats acceptés (V3.7)

| Format | Quand | Comportement |
|---|---|---|
| `.png` | fourni transparent | préféré si les deux existent (fond alpha) |
| `.jpeg` / `.jpg` | fourni déjà aplati avec son fond | accepté tel quel, **jamais converti** |
| `.webp` | — | non supporté |

MARK1 ne convertit rien : le fichier voyage tel quel dans le pack, et
`packager` **conserve l'extension d'origine** dans `EXPORT/`. C'est
OMNIS_WATCH qui décide comment le compositer.

## Règles techniques

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| Format | PNG (transparency) ou JPEG | PNG préféré ; JPEG accepté même avec fond opaque |
| Opacité | ≥ 75% | Jamais en dessous |
| Position | Centré | Horizontalement + verticalement |
| Taille | Lisible sur mobile | Minimum 15% de la largeur vidéo |
| Fond | Transparent | Pas de fond blanc/colore |
| Résolution | ≥ 300px de large | Pour qualité 1080p |

## Usage par plateforme

| Plateforme | Watermark obligatoire ? | Notes |
|------------|------------------------|-------|
| TikTok | ✅ OUI | Centré, opacity ≥75% |
| IG Reels | ✅ OUI | Centré, opacity ≥75% |
| YouTube Shorts | ✅ OUI | Centré, opacity ≥75% |
| X (Twitter) | ⚠️ Optionnel | Si fourni, même specs |

## Intégration dans le pack

Le watermark est inclus dans le `production_pack.json` par F05_PACKAGER :

```json
{
  "watermark": {
    "file": "watermark.png",
    "opacity": 0.80,
    "position": "center",
    "size_pct": 15,
    "platforms_obliged": ["tiktok", "instagram_reels", "youtube_shorts"],
    "platforms_optional": ["twitter_x"]
  }
}
```

## Checklist avant soumission
- [ ] Watermark visible sur toute la durée du clip
- [ ] Opacité ≥ 75% (vérifier sur fond sombre ET clair)
- [ ] Lisible sur écran mobile (test 360p)
- [ ] Aucun autre logo/promotion visible
- [ ] Position centrée (pas décalé vers un coin)
