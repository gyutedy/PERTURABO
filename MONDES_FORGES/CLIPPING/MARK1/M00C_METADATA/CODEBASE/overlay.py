"""M00C_METADATA / overlay -- overlay_title sous contrainte (EXC-1).

POURQUOI UNE EXCEPTION ICI
    Le titre d'overlay demande une formulation qu'aucune regle mecanique ne
    produit correctement : il faut dire l'enjeu en 4 mots. C'est le SEUL
    endroit ou MARK1 touche un LLM. Le bornage est strict :
      - le moteur impose les regles (validate + S1), jamais le LLM ;
      - 4 mots max, 2 lignes, 60 car./ligne, pas de CTA ;
      - boucle de reparation limitee a max_rounds ;
      - sans cle -> relais ORACLE, aucun appel reseau.

TROIS MODES, decides au demarrage :
    llm_enabled=true  + cle       -> MODE 1 : appel direct
    llm_enabled=true  + sans cle  -> MODE 2 : relais ORACLE
    llm_enabled=false             -> MODE 2 : relais ORACLE
"""

from __future__ import annotations

import json
import os

_ORACLE_STATUS = {"waiting_oracle": "waiting_oracle"}


class WaitingOracle(Exception):
    """Levee quand un pending ORACLE est ecrit et qu'aucune reponse n'existe.

    mark1.py attrape cette exception, ecrit l'etat et sort avec le code 3.
    """

    def __init__(self, pending_path):
        super().__init__("en attente de reponse ORACLE : %s" % pending_path)
        self.pending_path = pending_path


def pick_mode(cfg):
    """Rend 'direct' ou 'oracle' selon llm.enabled et la presence de la cle."""
    llm = cfg.get("llm") or {}
    enabled = bool(llm.get("enabled", False))
    key_env = llm.get("key_env", "CLIPPING_LLM_API_KEY")
    has_key = bool(os.environ.get(key_env))
    if enabled and has_key:
        return "direct"
    return "oracle"


def constraints(cfg):
    """Les contraintes dures, en clair, reutilisables par les deux modes."""
    return {
        "max_words": int(cfg.get("overlay_max_words", 4)),
        "max_chars_per_line": int(cfg.get("overlay_max_chars_per_line", 60)),
        "max_lines": 2,
        "no_cta": True,
        "no_question_mark": not bool(cfg.get("allowed_question_mark", False)),
        "no_invented_facts": True,
    }


def accept(text, cfg, lang, subject, internal_terms):
    """Un candidat est accepte si validate() ET S1 sont muets."""
    from libs import title_forge, s1_context
    viol = title_forge.validate(text, cfg, lang)
    if viol:
        return False, viol
    rep = s1_context.analyse(text, subject=subject,
                             internal_terms=internal_terms, lang=lang)
    if rep["verdict"] != "ok":
        return False, rep["reasons"]
    return True, []


def oracle_pending_path(cfg, root, pack_token):
    rel = cfg.get("oracle_pending_dir", "../ORACLE/pending")
    base = os.path.normpath(os.path.join(root, rel))
    return os.path.join(base, "overlay_%s.json" % pack_token)


def oracle_answers_path(cfg, root):
    rel = cfg.get("oracle_answers", "../ORACLE/answers.json")
    return os.path.normpath(os.path.join(root, rel))


def write_oracle_pending(cfg, root, pack_token, segments, directive, round_no, errors):
    """Ecrit UN SEUL pending pour tous les segments, avec mode d'emploi clair."""
    path = oracle_pending_path(cfg, root, pack_token)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    cons = constraints(cfg)
    asks = []
    for seg in segments:
        asks.append({
            "asset_id": seg.get("id"),
            "language": seg.get("language"),
            "source_text": (seg.get("source_text") or seg.get("key_fact") or "")[:600],
            "subject": directive.get("creator_name") or "",
            "previous_errors": (errors or {}).get(seg.get("id"), []),
        })

    doc = {
        "task": "overlay_title",
        "pack_token": pack_token,
        "round": round_no,
        "constraints": cons,
        "instructions": (
            "Pour chaque asset_id, propose TROIS titres d'overlay en 2 lignes. "
            "Respecte constraints. Reponds en JSON strict : "
            '{"answers": [{"asset_id": "A01", "candidates": ["t1","t2","t3"]}]}'
        ),
        "asks": asks,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    return path


def read_oracle_answers(cfg, root, pack_token):
    """Rend {asset_id: [candidats]} depuis answers.json, ou {} si pas de reponse."""
    path = oracle_answers_path(cfg, root)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except ValueError:
            return {}
    entries = data.get("answers") or data.get("overlay") or []
    out = {}
    if isinstance(entries, dict):
        for k, v in entries.items():
            out[k] = list(v)
    else:
        for e in entries:
            if e.get("pack_token") not in (None, pack_token):
                continue
            aid = e.get("asset_id")
            cands = e.get("candidates") or ([e["title"]] if e.get("title") else [])
            if aid and cands:
                out[aid] = list(cands)
    return out


def _direct_candidates(cfg, segment, directive, errors):
    """MODE 1 : appel direct au LLM. Best-effort, jamais bloquant pour les tests.

    Aucun SDK impose : on parle HTTP a une endpoint compatible chat. Si l'appel
    echoue, on rend [] et la boucle passe au round suivant.
    """
    import urllib.request

    llm = cfg.get("llm") or {}
    base = os.environ.get(llm.get("base_url_env", "CLIPPING_BASE_URL"), "")
    key = os.environ.get(llm.get("key_env", "CLIPPING_LLM_API_KEY"), "")
    model = os.environ.get(llm.get("model_env", "CLIPPING_LLM_MODEL"), "")
    if not base or not key or not model:
        return []

    cons = constraints(cfg)
    prompt = (
        "Propose %d overlay titles for a short clip. Constraints: max %d words, "
        "max %d lines, max %d chars/line, no call-to-action, no question mark, "
        "no invented facts. Previous errors to fix: %s. "
        'Reply JSON only: {"candidates": ["...", "...", "..."]}. '
        "Source: %s"
    ) % (int(llm.get("candidates_per_round", 3)), cons["max_words"], cons["max_lines"],
         cons["max_chars_per_line"], errors or "none",
         (segment.get("source_text") or segment.get("key_fact") or "")[:600])

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=llm.get("timeout_sec", 120)) as resp:
            data = json.load(resp)
        text = data["choices"][0]["message"]["content"]
        text = text[text.find("{"):text.rfind("}") + 1]
        return list(json.loads(text).get("candidates", []))
    except Exception:
        return []


def resolve(segments, directive, cfg, root, pack_token):
    """Boucle de reparation commune aux deux modes.

    Rend (chosen{asset_id: titre}, mode, rounds_used, errors).
    Leve WaitingOracle en mode 2 si aucune reponse n'existe.
    """
    mode = pick_mode(cfg)
    lang = directive.get("language") or cfg.get("default_language", "en")
    subject = directive.get("creator_name") or ""
    internals = directive.get("internal_terms") or ()
    max_rounds = int((cfg.get("llm") or {}).get("max_rounds", 3))
    per_round = int((cfg.get("llm") or {}).get("candidates_per_round", 3))

    chosen, errors = {}, {}
    rounds = 0

    answers = {}
    if mode == "oracle":
        answers = read_oracle_answers(cfg, root, pack_token)

    for round_no in range(1, max_rounds + 1):
        rounds = round_no
        missing = []
        for seg in segments:
            aid = seg.get("id")
            if aid in chosen:
                continue

            if mode == "direct":
                cands = _direct_candidates(cfg, seg, directive, errors.get(aid))
                if not cands:
                    cands = [seg.get("title") or "", seg.get("key_fact") or ""]
            else:
                cands = answers.get(aid) or []
                if not cands:
                    missing.append(aid)
                    continue

            for cand in cands[:max(per_round, 1)]:
                ok, why = accept(cand, cfg, lang, subject, internals)
                if ok:
                    chosen[aid] = cand
                    break
                errors.setdefault(aid, []).extend(why)

        if len(chosen) == len(segments):
            return chosen, mode, rounds, errors

        if mode == "oracle" and missing:
            # pas de reponse pour certains segments : ecrire le pending et sortir
            path = write_oracle_pending(cfg, root, pack_token,
                                        [s for s in segments if s.get("id") not in chosen],
                                        directive, round_no, errors)
            raise WaitingOracle(path)

    return chosen, mode, rounds, errors
