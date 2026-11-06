#!/usr/bin/env python3
"""
COMPOSE — EV compose net (S5 / v3.5)
====================================
EV compose net = produit (1+edge_net) - 1, precision machine.
jambe_edge_net_negatif = info, pas rejet.
Trou edge_net = hole, jamais substitue par EV brute.
Diagnostic. Jamais un producteur de p. Pas d'arbitrage.
"""

from __future__ import annotations


def ev_compose_net(edge_nets):
    """Produit (1+edge_net) - 1. None / cast fail = hole. Negatif = flag, pas drop."""
    prod = 1.0
    flags = []
    holes = []
    used = 0
    for e in edge_nets or []:
        if e is None:
            holes.append("edge_net")
            continue
        try:
            f = float(e)
        except (TypeError, ValueError):
            holes.append("edge_net")
            continue
        if f < 0:
            flags.append("jambe_edge_net_negatif")
        prod *= (1.0 + f)
        used += 1
    if used == 0:
        return None, flags, holes + ["compose_vide"]
    return prod - 1.0, flags, holes


def stamp_jambes(sel_list):
    """Pose jambe_edge_net_negatif sur chaque jambe. Ne droppe rien."""
    for s in sel_list or []:
        e = s.get("edge_net_devig")
        if e is None:
            continue
        try:
            if float(e) < 0:
                s["jambe_edge_net_negatif"] = True
        except (TypeError, ValueError):
            pass
    return sel_list


def compose_ticket(sel_list):
    """EV compose + flags + holes pour un ticket. Precision machine, pas de round."""
    stamp_jambes(sel_list)
    edges = [s.get("edge_net_devig") for s in (sel_list or [])]
    val, flags, holes = ev_compose_net(edges)
    return {
        "ev_compose_net": val,
        "compose_flags": flags,
        "compose_holes": holes,
    }
