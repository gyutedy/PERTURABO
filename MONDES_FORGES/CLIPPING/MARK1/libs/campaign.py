"""libs/campaign.py -- eligibilite d une campagne et revenu attendu.

C est ici que vit la seule vraie question : est-ce que cette campagne paie ?
Le risque reel n est pas le CPM, c est `funded`.
"""

from __future__ import annotations

from . import economy


def evaluate(campaign, cfg, platform="tiktok"):
    """Rend un dict d eligibilite.

    Cles : eligible, reasons, rate_usd_per_1k, net_per_1k_usd,
           budget_remaining_usd, cap_usd_per_clip_usd, notes
    """
    c = campaign or {}
    reasons = []
    notes = []

    rate = float(c.get("rate_usd_per_1k") or 0.0)
    min_rate = float(cfg.get("min_cpm_usd_per_1k", 1.5))
    fee = float(cfg.get("platform_fee_pct", 0.10))

    if rate <= 0:
        reasons.append("no_rate")
    elif rate < min_rate:
        reasons.append("rate_below_min")

    if not c.get("funded", False):
        reasons.append("unfunded")
        notes.append("campagne non financee : elle ne paie jamais, quel que soit le CPM")

    budget = float(c.get("budget_remaining_usd") or 0.0)
    if budget <= 0:
        reasons.append("budget_exhausted")

    allowed = c.get("platforms") or []
    if allowed and platform not in allowed:
        reasons.append("platform_not_allowed")

    cap = c.get("cap_usd_per_clip")
    if cap is None:
        cap = cfg.get("default_cap_usd_per_clip", 200)
        notes.append("cap_usd_per_clip absent de la campagne : valeur par defaut appliquee")

    if cap is not None and float(cap) <= 0:
        reasons.append("cap_invalid")

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "rate_usd_per_1k": rate,
        "net_per_1k_usd": economy.net_per_1k(rate, fee),
        "budget_remaining_usd": budget,
        "cap_usd_per_clip_usd": float(cap) if cap is not None else None,
        "platform": platform,
        "notes": notes,
        "capacity": "capacite inconnue -- a mesurer par tes propres soumissions",
    }
