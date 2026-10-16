"""
vox_premium.py — P5 : arbitrage par le CERVEAU PARTAGÉ (double mode).
====================================================================

N'analyse QUE les finalistes (les survivants des étages 0-2). Deux rôles :
  1. Score sémantique "potentiel de reframing" (hooks_pur.json) 0..10.
  2. Verdict final : relit chaque top_words + intensité → ok / weak / skip.

Depuis la refonte « cerveau partagé », ce module ne parle plus directement à
un provider : il passe par ``SHARED/brain.py``, qui résout automatiquement le
mode  premium (clé NVIDIA/CLIPPING_*)  →  oracle (passerelle AI_GATEWAY_*)
→  off. Une clé premium absente OU refusée bascule sur l'oracle : le pipeline
n'est jamais bloqué.

Dégradation gracieuse : sans aucun cerveau disponible, renvoie un score neutre
(5.0) et ``used_premium=False`` pour ne jamais bloquer. NE lit jamais la valeur
d'une clé (elle vient de l'environnement côté serveur).
"""

import os
import sys

_LIBS_DIR = os.path.dirname(os.path.abspath(__file__))
_CODEBASE_DIR = os.path.dirname(_LIBS_DIR)
_CLIPPING_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_CODEBASE_DIR)))
_SHARED_DIR = os.path.join(_CLIPPING_ROOT, "SHARED")
for _p in (_SHARED_DIR, _LIBS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from brain import ask as _brain_ask, available_mode as _brain_mode
except Exception:  # pragma: no cover - cerveau indisponible : dégradation neutre
    _brain_ask = None

    def _brain_mode():
        return "off"


_SYSTEM = (
    "Tu es l'arbitre viral de PERTURABO (mode PUR). Pour chaque extrait de "
    "transcript de stream, juge si le moment a un POTENTIEL DE REFRAMING : "
    "peut-il être transformé en histoire virale (sérieux→drôle, drôle→épique, "
    "neutre→dramatique, neutre→inspirant, personnel→universel) ? "
    "Réponds UNIQUEMENT en JSON : {\"score\": <0..10>, \"transformation\": \"<type>\", "
    "\"reason\": \"<10 mots max>\"}"
)


def brain_mode():
    """Mode courant du cerveau partagé : premium | oracle | off."""
    return _brain_mode()


def score_reframing(top_words, intensity=0.5, timeout=25):
    """Retourne {score, transformation, reason, used_premium, brain_mode}."""
    text = (top_words or "").strip()[:1500]
    if not text or _brain_ask is None:
        return {"score": 5.0, "transformation": None,
                "reason": "no brain/no text", "used_premium": False,
                "brain_mode": "off"}
    res = _brain_ask(
        _SYSTEM,
        f"Extrait (intensité {intensity}): \"{text}\"",
        temperature=0.2, max_tokens=80, expect_json=True, timeout=timeout,
    )
    if res.get("status") != "ok":
        return {"score": 5.0, "transformation": None,
                "reason": f"brain_{res.get('mode', 'off')}: {res.get('error')}",
                "used_premium": False, "brain_mode": res.get("mode", "off")}
    obj = res.get("content") or {}
    try:
        score = float(obj.get("score", 5.0))
    except (TypeError, ValueError):
        score = 5.0
    return {
        "score": round(max(0.0, min(10.0, score)), 2),
        "transformation": obj.get("transformation"),
        "reason": str(obj.get("reason", ""))[:120],
        "used_premium": True,
        "brain_mode": res.get("mode", "off"),
    }


def arbitrate(finalists, words=None, trigger_words=None):
    """Enrichit chaque finaliste d'un verdict cerveau + un score reframing.
    Renvoie finalists triés par (reframing + intensité)."""
    out = []
    for c in finalists:
        tw = c.get("top_words") or ""
        intens = float(c.get("intensity", c.get("signal_intensity", 0.5)))
        r = score_reframing(tw, intens)
        c["premium"] = {
            "reframing_score": r["score"],
            "transformation": r["transformation"],
            "reason": r["reason"],
            "used_premium": r["used_premium"],
            "brain_mode": r["brain_mode"],
        }
        # verdict combiné : intensité réelle + reframing
        combo = 0.5 * intens * 10 + 0.5 * r["score"]
        if combo >= 6.5:
            verdict = "ok"
        elif combo >= 4.5:
            verdict = "weak"
        else:
            verdict = "skip"
        c["verdict"] = verdict
        c["verdict_score"] = round(combo, 2)
        out.append(c)
    out.sort(key=lambda x: (-x["verdict_score"], -(x.get("premium") or {}).get("reframing_score", 0)))
    return out
