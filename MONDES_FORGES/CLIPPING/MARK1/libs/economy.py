"""libs/economy.py — le prix que CLIPPING n'avait pas.

Toutes les fonctions sont pures : elles prennent des nombres, rendent des nombres.
Aucun seuil n'est ecrit ici : ils viennent de config/selection.json via l'appelant.
"""

from __future__ import annotations


def net_per_1k(cpm_usd_per_1k, platform_fee_pct):
    """Ce qu'on touche reellement pour 1000 vues, frais deduits.

    1.0875 $/1k a 10 % de frais -> 0.97875 $ net par millier de vues.
    """
    cpm = float(cpm_usd_per_1k or 0.0)
    fee = float(platform_fee_pct or 0.0)
    return round(cpm * (1.0 - fee), 6)


def revenue(views_approved, cpm_usd_per_1k, platform_fee_pct,
            cap_usd_per_clip=None):
    """Dollars nets pour N vues approuvees, plafonnes par clip si cap fourni.

    Le cap plafonne le NET, pas le brut : c'est ce que la campagne verse
    reellement a l'operateur.
    """
    views = max(0, int(views_approved or 0))
    net = views / 1000.0 * net_per_1k(cpm_usd_per_1k, platform_fee_pct)
    if cap_usd_per_clip is not None:
        cap = float(cap_usd_per_clip)
        if cap > 0:
            net = min(net, cap * (1.0 - float(platform_fee_pct or 0.0)))
    return round(net, 4)


def views_needed(target_net_usd, cpm_usd_per_1k, platform_fee_pct,
                 approval_rate=None):
    """Combien de vues BRUTES il faut pour toucher `target_net_usd` nets.

    `approval_rate` est le taux de vues validees par la campagne. A 1.0 on est
    optimiste par construction : c'est la valeur par defaut, et c'est assume.
    """
    target = float(target_net_usd or 0.0)
    rate = float(approval_rate if approval_rate is not None else 1.0)
    if rate <= 0:
        return 0
    per_view_net = net_per_1k(cpm_usd_per_1k, platform_fee_pct) / 1000.0
    if per_view_net <= 0:
        return 0
    return int(round(target / per_view_net / rate))


def usd_per_hour(views_approved, cpm_usd_per_1k, minutes_worked,
                 platform_fee_pct=0.0, cap_usd_per_clip=None):
    """La metrique de tri (decision D8). Zero minute -> 0.0, jamais d'exception."""
    minutes = float(minutes_worked or 0.0)
    if minutes <= 0:
        return 0.0
    net = revenue(views_approved, cpm_usd_per_1k, platform_fee_pct, cap_usd_per_clip)
    return round(net / (minutes / 60.0), 4)
