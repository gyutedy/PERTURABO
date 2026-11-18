#!/usr/bin/env python3
"""
SYSTEMES — tickets combinatoires a variance faconnee (S2, S3, S4).
==================================================================
S1 (systeme 2/3) vit dans combinator.build_system23 — reference ici.
Ces fonctions faconnent la VARIANCE, jamais la marge du book.
Aucune cote n'est estimee, aucune probabilite inventee : ValueError si absent.
Format jambe : (match_id, marche, selection, cote, p_modele).
"""
from __future__ import annotations


def _leg(leg, mid):
    if not leg or len(leg) != 5:
        raise ValueError("jambe invalide : " + str(mid))
    _, _, _, cote, p = leg
    if cote is None or float(cote) <= 1.0:
        raise ValueError("cote absente ou invalide sur " + str(mid))
    if p is None or not (0.0 < float(p) < 1.0):
        raise ValueError("p_modele absente sur " + str(mid))
    return float(cote), float(p)


def build_dutching2(jambes, mise_totale):
    """S2 — dutching egalise sur 2 matchs independants (exactement 2 jambes).
    Mises inversement proportionnelles aux cotes : retour R identique
    quelle que soit la jambe gagnante."""
    if len(jambes) != 2:
        raise ValueError("dutching 2 exige exactement 2 jambes")
    id1, id2 = jambes[0][0], jambes[1][0]
    if id1 == id2:
        raise ValueError("les 2 jambes doivent etre 2 matchs differents")
    c1, p1 = _leg(jambes[0], id1)
    c2, p2 = _leg(jambes[1], id2)
    mise = float(mise_totale)
    if mise <= 0:
        raise ValueError("mise_totale doit etre > 0")
    inv = 1.0 / c1 + 1.0 / c2
    retour = mise / inv
    s1, s2 = retour / c1, retour / c2
    p_eq = (p1 + p2) / 2.0
    ratio = retour / mise
    return {
        "type": "dutching_2",
        "mises": [round(s1, 2), round(s2, 2)],
        "mise_totale": round(mise, 2),
        "retour_si_une_gagne": round(retour, 2),
        "gain_si_une": round(retour - mise, 2),
        "gain_si_deux": round(2.0 * retour - mise, 2),
        "perte_si_aucune": round(mise, 2),
        "p_break_even_par_jambe": round(inv / 2.0, 4),
        "p_tout_perdre": round((1.0 - p1) * (1.0 - p2), 4),
        "ev_si_p_egale": round(mise * (2.0 * ratio * p_eq - 1.0), 2),
    }


def build_corridor(over_leg, under_leg, mise_par_jambe, p_corridor):
    """S3 — Over L1 + Under L2, MEME match, L1 < L2 (deux lignes : T-2h/T-0
    ou deux books). Au moins un gagnant hors push. p_corridor = P(L1 < total < L2)
    calculee par le moteur — jamais estimee ici."""
    id1, mk1, l1 = over_leg[0], over_leg[1], over_leg[2]
    id2, mk2, l2 = under_leg[0], under_leg[1], under_leg[2]
    if id1 != id2 or mk1 != "total_over" or mk2 != "total_under":
        raise ValueError("corridor : over+under du MEME match requis")
    try:
        if float(l1) >= float(l2):
            raise ValueError("corridor vide : L1 (over) doit etre < L2 (under)")
    except (TypeError, ValueError):
        raise ValueError("lignes de corridor absentes ou invalides")
    c1, _ = _leg(over_leg, id1)
    c2, _ = _leg(under_leg, id2)
    if p_corridor is None or not (0.0 < float(p_corridor) < 1.0):
        raise ValueError("p_corridor absente : le moteur doit la calculer")
    mise = float(mise_par_jambe)
    if mise <= 0:
        raise ValueError("mise_par_jambe doit etre > 0")
    gain_both = round(mise * (c1 + c2) - 2.0 * mise, 2)
    perte_one = round(mise * min(c1, c2) - 2.0 * mise, 2)
    p = float(p_corridor)
    return {
        "type": "corridor",
        "lignes": [l1, l2],
        "mises": [mise, mise],
        "gain_si_les_deux": gain_both,
        "perte_si_un_seul": perte_one,
        "p_corridor": round(p, 4),
        "ev_approx": round(p * gain_both + (1.0 - p) * perte_one, 2),
        "note": "ligne .5 = aucun push ; EV approchee depuis p_corridor",
    }


def build_tri_lettre(pivot, jambes, mise_double):
    """S4 — pivot couvert : doubles Pivot-B, Pivot-C (m) + simple Pivot (2m).
    Si le pivot passe, la perte est plafonnee au lieu de -100 %."""
    if len(jambes) != 2:
        raise ValueError("pivot couvert exige exactement 2 autres jambes")
    idA, idB, idC = pivot[0], jambes[0][0], jambes[1][0]
    if len({idA, idB, idC}) != 3:
        raise ValueError("S4 exige 3 matchs differents")
    cA, pA = _leg(pivot, idA)
    cB, pB = _leg(jambes[0], idB)
    cC, pC = _leg(jambes[1], idC)
    mise = float(mise_double)
    if mise <= 0:
        raise ValueError("mise_double doit etre > 0")
    ev_m = (2.0 * cA * pA + cA * cB * pA * pB
            + cA * cC * pA * pC + cB * cC * pB * pC - 4.0)
    return {
        "type": "pivot_couvert",
        "mises": {"double_AB": mise, "double_AC": mise, "simple_A": 2.0 * mise},
        "mise_totale": round(4.0 * mise, 2),
        "perte_si_pivot_seul": round(mise * (2.0 * cA - 4.0), 2),
        "gain_si_A_et_une": round(mise * (cA * cB + 2.0 * cA - 4.0), 2),
        "gain_si_A_B_C": round(mise * (2.0 * cA * (cB + 1.0) - 4.0), 2),
        "gain_si_BC_sans_A": round(mise * (cB * cC - 4.0), 2),
        "perte_si_rien": round(4.0 * mise, 2),
        "ev_par_mise_double": round(ev_m, 4),
    }
