"""libs/siege_log.py -- la trace d un siege. UN FICHIER PAR RUN, jamais reecrit.

CE QUE C EST
    Le recit machine d un siege : quelles portes ont tourne, dans quel ordre,
    avec quel verdict, en combien de temps, sur quelle version du code. Le
    ledger (libs/ledger.py) dit le RESULTAT par clip ; ceci dit le PARCOURS.

POURQUOI UN FICHIER PAR RUN ET PAS UN JOURNAL GLOBAL
    Un journal global modifie a chaque run est le pire cas pour git : deux
    runs concurrents (local + GitHub Actions) ecrivent la meme ligne, le push
    est rejete, et une heure de travail disparait -- c est exactement le bug
    corrige par `e62386a` sur les transcripts. Ici chaque run ecrit un
    fichier neuf dont le nom contient deja son identite :
        sieges/2026-11-16T171829_e99bd523.json
    Deux runs ne peuvent pas se disputer un fichier qui n existe pas encore.
    Et un journal immuable est un journal qui PROUVE quelque chose : si on
    peut reecrire l entree d hier, elle ne vaut pas mieux qu un souvenir.

CE QU IL N EST PAS
    Pas un journal de developpement. « pourquoi on a change la porte M2B »
    appartient a TRACKING/MARK1_LOG.md, qui est ecrit a la main. Un journal
    automatique dit QU il y a eu un refus, jamais POURQUOI la regle etait mal
    posee. Melanger les deux noie la decision dans les [OK].

CE QU IL N ECRIT JAMAIS
    Aucun secret. Les cles d environnement ne sont pas recopiees, ni les
    chemins absolus hors du repo. Le fichier est commite : il doit etre lisible
    par n importe qui sans rien divulguer.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

SCHEMA_VERSION = "mark1-siege-1"

#: Etats possibles d une porte. Trois seulement, parce qu il n y en a que
#: trois qui veulent dire quelque chose : ca passe, ca refuse, ca attend.
OK, FAIL, WAIT = "OK", "FAIL", "WAIT"


def _now():
    return datetime.now(timezone.utc)


def new_run(pack_name, platform):
    """Ouvre une trace de siege. Le fichier n est ecrit qu a `save()`."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": _now().strftime("%Y-%m-%dT%H%M%S"),
        "started_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": None,
        "duration_sec": None,
        "status": "running",
        "pack_name": pack_name,
        "platform": platform,
        "code_version": None,
        "gates": [],
        "assets": [],
        "pack_token": None,
        "pack_path": None,
        "watermark": None,
        "errors": [],
    }


def gate(run, code, ok, message, skipped=False, duration_sec=None):
    """Note une porte franchie. Append-only, dans l ordre d execution."""
    run["gates"].append({
        "code": code,
        "state": (OK if ok else (WAIT if skipped else FAIL)),
        "message": message,
        "duration_sec": round(duration_sec, 3) if duration_sec is not None else None,
    })
    return run


def close(run, status, error=None):
    """Ferme la trace. `status` : 'exported', 'refused', 'waiting_oracle'."""
    end = _now()
    start = datetime.strptime(run["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)
    run["finished_at"] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    run["duration_sec"] = round((end - start).total_seconds(), 3)
    run["status"] = status
    if error:
        run["errors"].append(str(error))
    return run


def path_for(run, cfg, root):
    """Chemin du fichier de trace. Vit a cote du pack, dans EXPORT/sieges/.

    A cote du pack et non dans OUT/ : OUT/ est gitignore par convention
    (`**/OUT/*.json`), et une trace que git jette ne trace rien.
    """
    rel = cfg.get("siege_log_dir")
    if rel:
        base = os.path.normpath(os.path.join(root, rel))
    else:
        base = os.path.normpath(
            os.path.join(root, cfg.get("export_dir", "../EXPORT"), "sieges"))
    token = run.get("pack_token") or "nopack"
    name = "%s_%s.json" % (run["run_id"], token)
    return os.path.join(base, name)


def save(run, cfg, root):
    """Ecrit la trace une fois, et rend son chemin. Jamais de reecriture.

    Si le fichier existe deja (deux runs dans la meme seconde sur le meme
    pack -- improbable mais possible en CI), on suffixe plutot que d ecraser :
    perdre une trace est pire que d en avoir deux.
    """
    path = path_for(run, cfg, root)
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(path):
        path = "%s_%d%s" % (base, n, ext)
        n += 1

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def summary(run):
    """Une ligne lisible pour la console, sans charger le fichier."""
    counts = {}
    for g in run.get("gates") or []:
        counts[g["state"]] = counts.get(g["state"], 0) + 1
    bits = ", ".join("%s=%d" % (k, counts[k]) for k in (OK, FAIL, WAIT) if counts.get(k))
    return "%s | %s | %s | %s" % (
        run.get("status"), run.get("pack_token") or "-",
        bits or "aucune porte", "%ss" % run.get("duration_sec"))
