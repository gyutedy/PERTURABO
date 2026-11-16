# JOURNAL DES SIÈGES — MARK1

> Une entrée par siège réel. Écrit à la main, à partir de la trace machine
> (`EXPORT/sieges/<run>_<token>.json`) et du ledger.
>
> Ce fichier répond à une question que ni le README ni le plan ne peuvent
> poser : **est-ce que ça a déjà tourné, et qu'est-ce que ça a donné ?**

---

## Siège 1 — 2026-11-16 — VOD TWITCHCON DAY 1 (AISHAH)

### Entrée
| | |
|---|---|
| VOD | `https://www.twitch.tv/videos/2927914500` |
| Titre | TWITCHCON DAY 1 💜 \| !discord !socials |
| Durée | 2 h 56 (10 575 s) |
| Transcript | `ARCHIVUM/montage/transcripts/v2927914500_transcript.json` |
| Mode | `words` (5 313 mots, run `43872241148`) |
| Pack d'entrée | `packs/twitchcon_v2927914500.json` |
| Campagne | `2026-07-24_AISHAH_SOFEY_MULTI` |
| Plateforme | tiktok |
| Commande | `python mark1.py export packs/twitchcon_v2927914500.json --transcript ../ARCHIVUM/montage/transcripts/v2927914500_transcript.json --nb-segments 3 --platform tiktok` |

### Sortie
| | |
|---|---|
| `pack_token` | `e99bd523` |
| Pack | `EXPORT/production_pack_mark1_e99bd523.json` |
| Watermark | `EXPORT/production_pack_mark1_e99bd523.png` (47,8 Ko) |
| Portes | 11/11 `[OK]` |

```
[OK] TRANSCRIPT       : v2927914500_transcript.json -> 3 segments choisis
[OK] D0_DIRECTIVE     : 2026-07-24_AISHAH_SOFEY_MULTI | en | 0.30 $/1k | 4 plates
[OK] M0B_CYCLE        : cycle 2026-07-20 -> 2026-11-21, ouvert
[OK] M1_SELECTION     : 3 segments, langue en
[OK] M5_VOX           : 3 segments, 0 transcrits
[OK] M2_METADATA      : 3 assets valides (via ORACLE)
[OK] M2B_COMPLIANCE   : 3 assets conformes (focus declare par operator)
[OK] M3_WATERMARK     : aishahsofey_1.png (requis)
[OK] A1_ACCOUNT       : warmup 21j
[OK] A2_CAMPAIGN      : CPM 0.30 $/1k, net 0.3000
[OK] X1_EXPORT        : production_pack_mark1_e99bd523.json
```

### Les 3 clips

| ID | Bornes | Overlay | Texte source |
|---|---|---|---|
| A01 | 10328 → 10358 (172:08) | She lost 50,000 dollars | « I looks like it's like 50,000 dollars. No. Scary. There's no way. » |
| A02 | 8616,6 → 8646,6 (143:36) | She lost 86,000 seconds | « Yo, being timed out for 86,000 seconds is insane. What did I miss? » |
| A03 | 2375,8 → 2405,8 (39:35) | She paid 385 was much | « I feel like 385 was a bit much, no? […] » |

### Ce qui a été appris — et corrigé

1. **Le focus ne se mesure pas dans le texte.** `aishah`/`sofey` :
   **0 occurrence** en 2 h 53. Normal sur un POV caméra portée où elle est à
   l'écran en permanence. La règle de la campagne est visuelle
   (*« as long as she's featured in the clip »*). → **V3.6** : focus déclaratif.
2. **`M00B_SELECTOR` jetait `source_text`**, donc le `bait` mesurait sur du
   vide et échouait à 0 % sur les 3 assets. Bug silencieux. → **V3.6**.
3. **`A1_ACCOUNT` / `A2_CAMPAIGN` n'étaient jamais appelées.** → **V3.5**.
4. **`M3_WATERMARK` jugeait une opacité sans regarder un pixel.** → **V3.5**.
5. **Trois itérations d'overlay** avant que `title_forge` + `bait` +
   `s1_context` acceptent le même titre : « She just lost fifty grand »
   (bait 0 %), « Timed out for a whole day » (`unexplained_entity`),
   « She lost 86,000 seconds » (passe). Les 4 mots de contenu doivent
   exister dans le segment.

### Réserves assumées

- **Le focus est déclaré, pas prouvé** : `asserted_by: operator`,
  preuve « POV caméra portée ». MARK1 ne voit pas la vidéo.
- **« She lost » est une reformulation** : elle a été *timeout*, pas
  « perdue ». Défendable, mais ce n'est pas une citation.
- **Le cycle a expiré le lendemain** (2026-11-15). Le pack a été produit
  avec la valeur provisoire `2026-11-21`, remise à la vraie valeur
  (`2026-11-15`) ensuite. **Ce pack n'est pas rejouable tel quel** :
  `M0B_CYCLE` refuserait aujourd'hui, et c'est la porte qui fait son travail.
- **Aucune ligne de ledger n'a été écrite PAR `export`** pour ce siège :
  `cmd_export` n'appelait pas `ledger.append` à l'époque. → **V3.8**.
  Les 3 lignes existent aujourd'hui, mais rétro-remplies à la main.

### Suivi (à remplir par l'opérateur)
- [ ] `clip_url` collé dans le ledger, pour chacun des 3 clips
- [ ] `published_at`, `submitted_at`
- [ ] `views_raw` / `views_approved` / `paid_usd`

**Les 3 lignes du ledger ont été rétro-remplies à la main le 2026-11-16**
(`outcome: exported`, `notes: … (retro-rempli)`), à partir du pack lui-même :
les `clip_token`, bornes, titres et `vod_url` viennent du JSON livré, aucune
valeur n'a été inventée. Ce n'est pas ce que `export` aurait écrit (il n'y
avait pas de ledger à l'époque) ; c'est la même information posée à la main,
une seule fois, pour que le suivi des vues puisse commencer.

```
A01-20261116-e99bd523 | She lost 50,000 dollars
A02-20261116-e99bd523 | She lost 86,000 seconds
A03-20261116-e99bd523 | She paid 385 was much
```

> Prochaine fois : ces cases deviennent trois lignes écrites automatiquement
> à l'export, et la trace part dans `EXPORT/sieges/` sans intervention.
