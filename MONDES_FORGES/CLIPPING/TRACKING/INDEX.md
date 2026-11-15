# TRACKING/INDEX.md — Cartographie des journaux du forge CLIPPING

> *Point d'entrée unique vers tous les journaux de tracking.*

---

## Journal général

| Fichier | Contenu |
|---|---|
| `CLIPPING_LOG.md` | Journal de déploiement du forge — jalons, statut, notes sécurité |

## Journaux par frégate

| Frégate | Fichier | Rôle de la frégate |
|---|---|---|
| `F01_SCOUT` | `../F01_SCOUT/CODEBASE/TRACKING.md` | Chasse les assets campagne (jamais ailleurs) |
| `F02_TYRANT_CAMP` | `../F02_TYRANT_CAMP/CODEBASE/TRACKING.md` | Verdict campagne + océan bleu |
| `F03_SOURCE_HUNTER` | `../F03_SOURCE_HUNTER/CODEBASE/TRACKING.md` | Sélectionne vidéos longues à clipper |
| `F04_COPYWRITER` | `../F04_COPYWRITER/CODEBASE/TRACKING.md` | Frégate lourde — texte viral via premium direct |
| `F05_PACKAGER` | `../F05_PACKAGER/CODEBASE/TRACKING.md` | Emballe production packs |
| `F06_TRACKER` | `../F06_TRACKER/CODEBASE/TRACKING.md` | Checklist submission active + learnings |
| `MARK1` | `../MARK1/TRACKING/MARK1_LOG.md` | Frégate autonome — journal d'implémentation et sorties mesurées |
| `MARK1` | `../MARK1/TRACKING/MARK1_V1_V2_CHANGES.md` | Écarts V1 → V2 (pack JSON, plus de MP4) |

## Composants annexes

| Composant | Fichier | Rôle |
|---|---|---|
| `TYRANT` | `../TYRANT/CODEBASE/TRACKING.md` | 2 modes (réactif + prospectif océan bleu) |
| `F00_CAPTEURS` | `../F00_CAPTEURS/CODEBASE/TRACKING.md` | Commandité Warsmith, multi-sites clipping |
| `ORCHESTRATOR` | `../ORCHESTRATOR/CODEBASE/TRACKING.md` | 4 Portes, pattern hybride, ledger IW_CUSTOS |

## Docs doctrinales (CONTRACTS/)

| Fichier | Rôle |
|---|---|
| `../CONTRACTS/copywriting_doctrine.md` | Socle doctrinal F04_COPYWRITER (10 sections — à remplir par Warsmith) |
| `../CONTRACTS/copywriter_systemprompt.md` | System prompt F04 (généré par premium à l'init, puis figé) |
| `../CONTRACTS/copywriter_secrets.example.json` | Schéma secret F04 (gitignored la version réelle) |
| `../CONTRACTS/whop_rules.md` | Mécanique Content Rewards |
| `../CONTRACTS/clipping_rules.md` | Warmup, volume, FTC, transformative |
| `../CONTRACTS/production_pack_schema.json` | Schéma JSON du production pack (contrat interface OMNIS_WATCH) |
| `../F00_IRON_SENTINEL/F00B_VOX/MODAL/DEPLOYER.md` | Guide déploiement transcription GPU Modal (F00B_VOX) |
| `../F00_IRON_SENTINEL/F00B_VOX/PLAN_REFONTE_VOX.md` | **Plan de refonte VOX** (architecture multi-capteurs, validé) |
| `../GUIDE_UTILISATION/17_PLAN_REFONTE_VOX.md` | Guide du plan de refonte VOX |
| `../pur_adapter.py` | Adaptateur PUR (VOX → source_specimen F02, skip F01) |
| `../pur_adapter_direct.py` | Adaptateur PUR direct (VOX → angles+specimen F04, skip F01/F02/F03) |
| `.github/workflows/perturabo_f04_copywriting.yml` | Workflow F04 copywriting PUR (VOX direct) |
| `.github/workflows/perturabo_f02_verdict.yml` | Workflow F02 verdict PUR (skip F01) |
| `../GUIDE_UTILISATION/15_TRANSCRIPTION_MODAL.md` | Transcription GPU Modal — principe, correctifs, rotation de compte |
| `../GUIDE_UTILISATION/16_ORCHESTRATION_GITHUB_ACTIONS.md` | Orchestration Oracle via GH Actions (rôles, flux, secrets) |

## ARCHIVUM — index des zones

| Zone | Emplacement | Voir README de la zone |
|---|---|---|
| `rules/` | `../ARCHIVUM/rules/README.md` | Règles statiques |
| `campaign/` | `../ARCHIVUM/campaign/README.md` | Campagne en cours (singulier) |
| `platform_generator/` | `../ARCHIVUM/platform_generator/README.md` | Profils plateforme |
| `market_generator/` | `../ARCHIVUM/market_generator/README.md` | Profils marché |
| `knowledge_base/` | `../ARCHIVUM/knowledge_base/README.md` | Tout sur le clipping |
| `copywriting/` | `../ARCHIVUM/copywriting/README.md` | Musée du copywriting |
| `angles/` | `../ARCHIVUM/angles/README.md` | Patterns d'angles |
| `demons/` | `../ARCHIVUM/demons/README.md` | Démon (campagne + veille) |
| `channels/` | `../ARCHIVUM/channels/README.md` | Comptes de clipping |
| `learnings/` | `../ARCHIVUM/learnings/README.md` | Boucle rétro-active |

## Manifeste

| Fichier | Contenu |
|---|---|
| `../MANIFEST.md` | Liste exhaustive des fichiers créés + leur statut (doc tracking, squelette, gitkeep, etc.) |
