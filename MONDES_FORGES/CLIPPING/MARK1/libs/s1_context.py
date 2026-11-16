"""libs/s1_context.py -- S1, auto-suffisance contextuelle.

LE PROBLEME QU IL RESOUT
    Le titre reellement produit par la forge etait
    "Cucumber Key? The Shocking Truth Behind It". Un spectateur froid ne sait pas
    ce qu est "Cucumber Key". Le titre n est pas mauvais : il est inintelligible
    sans le contexte du fan.

CE QU IL MESURE
    `context_dependency` : la part du titre qui n a de sens que si l on connait
    deja le sujet. Une entite est "expliquee" si elle est apparue plus haut dans
    le titre avec une apposition, si elle est le sujet declare, ou si c est un
    terme universel.

CE QU IL NE FAIT PAS
    Aucune API, aucun modele, aucune heuristique magique. Un lexique de mots
    universels, une detection d apposition, et une liste de termes internes
    declares. C est grossier et c est assume : l hypothese S1 est NON VALIDEE
    (voir le CDC section 15.2), elle est mesuree, pas supposee.

HYPOTHESE CENTRALE (non validee) : context_dep bas -> portee hors-fans haute.
"""

from __future__ import annotations

import json
import os
import re

_LANG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang")
_CACHE = {}

# Repli francais : si aucune langue n'est chargee, on garde le comportement V2.
_FR_UNIVERSAL = frozenset("""
il elle ils elles on nous vous je tu me moi toi lui leur
un une des le la les ce cet cette ces mon ma mes ton ta tes son sa ses notre nos
a ai as avons avez ont avait avaient eu etre ete suis es est sommes etes sont
fait font faisait faire dit dire va aller vient venir prend prendre mis met mettre
perdu perd gagne paye vend vendu achete donne trouve
tout tous toute toutes rien personne quelqu un quelque chose
jour jours nuit semaine semaines mois an ans annee annees heure heures minute minutes
seconde secondes fois
dollar dollars euro euros cent cents million millions milliard milliards
argent prix cher chere gratuit gratis
homme femme fille garcon gamin gamine enfant enfants
pere mere frere soeur ami amie amis famille
vie mort vivant tue
nouveau nouvelle vieux vieille jeune grand grande petit petite gros grosse
premier premiere dernier derniere meilleur pire
plus moins tres trop peu beaucoup assez encore deja jamais toujours souvent
avant apres pendant depuis jusqu sans avec pour par dans sur sous entre chez vers
et ou mais donc car ni or si comme quand parce alors puis
ne pas
stop arret arreter commence commencer change changer
vrai faux vraiment
reve cauchemar
seul seule ensemble
monde terre pays ville maison voiture telephone ordinateur travail ecole
""".split())

_CAP_SEQ = re.compile(r'\b[A-Z][\w-]*(?:\s+[A-Z][\w-]*)*')
_WORD = re.compile(r"[A-Za-zÀ-ſ]+")


def load_lang(lang):
    """Charge (et met en cache) le lexique d'une langue. Repli FR sinon."""
    code = (lang or "fr").lower()
    if code in _CACHE:
        return _CACHE[code]
    path = os.path.join(_LANG_DIR, "%s.json" % code)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        spec = {
            "universal": frozenset(w.lower() for w in data.get("universal", [])),
            "stake": tuple(data.get("stake_markers", [])),
            "articles": tuple(data.get("apposition_articles", ["le", "la", "les", "un", "une"])),
        }
    else:
        spec = {
            "universal": _FR_UNIVERSAL,
            "stake": ("perdu", "perd", "gagne", "paye", "dollars", "euro", "euros",
                      "tout", "rien", "jamais", "survecu", "bascule", "verite",
                      "mentait", "personne", "personnes", "nuit", "jour", "apres",
                      "avant", "vue", "vraiment"),
            "articles": ("le", "la", "les", "l", "un", "une", "the"),
        }
    _CACHE[code] = spec
    return spec


def _universal(token, spec):
    return token.lower().strip("-") in spec["universal"]


def _explained_by_apposition(text, entity, spec):
    """Vrai si l entite est suivie d une virgule puis d un article (apposition).

    "Sophie Rain, la creatrice la plus suivie, a tout arrete" -> expliquee.
    """
    idx = text.find(entity)
    if idx < 0:
        return False
    tail = text[idx + len(entity):]
    m = re.match(r"\s*,\s*([A-Za-zÀ-ſ]+)\s+", tail)
    if not m:
        return False
    return m.group(1).lower() in spec["articles"]


def _candidate_entities(text, spec):
    """Sequences capitalisees de 2 caracteres ou plus, hors mots universels."""
    found = []
    for m in _CAP_SEQ.finditer(text):
        seq = m.group(0).strip()
        if len(seq) < 2:
            continue
        tokens = seq.split()
        if all(_universal(t, spec) for t in tokens):
            continue
        found.append((seq, m.start()))
    return found


def analyse(text, subject="", internal_terms=(), lang=None):
    """Analyse un texte (titre ou hook) et rend un dict.

    `lang` : "en" ou "fr". Absent -> repli FR (comportement V2 inchange).
    Cles rendues : verdict, context_dependency, unexplained_entities,
                   internal_terms, reasons, word_count
    """
    spec = load_lang(lang)
    raw = (text or "").strip()
    reasons = []

    if not raw:
        return {
            "verdict": "reject",
            "context_dependency": 1.0,
            "unexplained_entities": [],
            "internal_terms": [],
            "reasons": ["empty"],
            "word_count": 0,
        }

    subject_norm = (subject or "").strip().lower()
    internals = [t.strip() for t in (internal_terms or ()) if t and t.strip()]
    words = _WORD.findall(raw)
    lowered = raw.lower()

    hit_internals = [t for t in internals if t.lower() in lowered]
    if hit_internals:
        reasons.append("internal_term")

    unexplained = []
    for seq, _pos in _candidate_entities(raw, spec):
        if subject_norm and seq.lower() in subject_norm:
            continue
        if _explained_by_apposition(raw, seq, spec):
            continue
        if seq not in unexplained:
            unexplained.append(seq)
    if unexplained:
        reasons.append("unexplained_entity")

    if words:
        unknown = sum(1 for w in words if not _universal(w, spec))
        dep = round(unknown / len(words), 4)
    else:
        dep = 0.0

    return {
        "verdict": "reject" if reasons else "ok",
        "context_dependency": dep,
        "unexplained_entities": unexplained,
        "internal_terms": hit_internals,
        "reasons": reasons,
        "word_count": len(words),
        "lang": (lang or "fr").lower(),
    }
