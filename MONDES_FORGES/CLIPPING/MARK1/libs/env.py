"""libs/env.py — les 8 cles optionnelles, et leur etat.

MARK1 ne requiert AUCUNE cle. Ce module existe pour que `doctor` puisse le prouver :
il liste les cles connues de la forge et affiche leur etat, sans jamais lever d'erreur.

Invariant : aucun appel reseau ici. On lit os.environ, rien d'autre.
"""

from __future__ import annotations

import os

# (nom, usage, requise_par_mark1)
_KNOWN = (
    ("CLIPPING_PREMIUM_API_KEY", "F04 copywriter — LLM premium", False),
    ("CLIPPING_LLM_API_KEY", "F04 titre — LLM off par defaut", False),
    ("CLIPPING_BASE_URL", "endpoint compatible OpenAI", False),
    ("CLIPPING_LLM_MODEL", "nom du modele", False),
    ("MODAL_TOKEN_ID", "GLOW — hors perimetre MARK1", False),
    ("MODAL_TOKEN_SECRET", "GLOW — hors perimetre MARK1", False),
    ("TELEGRAM_BOT_TOKEN", "alertes portes", False),
    ("TELEGRAM_CHAT_ID", "alertes portes", False),
    ("YTDLP_COOKIES_FILE", "VOD privees / age-restricted", False),
)


def doctor():
    """Rend [(nom, etat, usage)]. etat ∈ {"OK", "absent"}."""
    out = []
    for name, usage, _required in _KNOWN:
        state = "OK" if os.environ.get(name) else "absent"
        out.append((name, state, usage))
    return out


def missing_required():
    """Aucune cle n'est requise par MARK1. Toujours []."""
    return [n for n, _u, req in _KNOWN if req and not os.environ.get(n)]
