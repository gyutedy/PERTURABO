#!/usr/bin/env python3
"""
oracle_relay.py — Relais de raisonnement SANS clé (questions → agent → réponses).
==============================================================================

Le mode « oracle » du cerveau partagé n'appelle aucune API et ne câble aucune
clé. Il fonctionne par fichiers versionnés :

  1. Une frégate a besoin de raisonner et aucune clé premium n'est disponible.
  2. ``brain.ask()`` calcule l'empreinte de la question et cherche la réponse
     dans ``ORACLE/answers.json``.
  3. Réponse absente → la question est écrite dans ``ORACLE/pending/<id>.json``
     (status ``pending``). Le run continue en dégradé et la CI commite la question.
  4. L'opérateur transmet la question à l'agent, qui répond via ce CLI.
     La réponse est ajoutée à ``answers.json`` puis poussée.
  5. Le run suivant trouve la réponse et reprend le raisonnement réel.

Aucune dépendance pip, aucun réseau, aucune clé. Tout est auditable dans Git.

Usage opérateur :

    python3 oracle_relay.py list
    python3 oracle_relay.py show <id>
    python3 oracle_relay.py answer <id> --content-file reponse.json --model sandbox
    python3 oracle_relay.py answer <id> --content '{"score": 7}'
    python3 oracle_relay.py status

Variables :

  * ``ORACLE_RELAY_DIR``    — dossier du relais (défaut : ``<CLIPPING>/ORACLE``)
  * ``ORACLE_RELAY_ENABLED``— ``0`` désactive le relais (défaut : actif)
  * ``ORACLE_RELAY_STRICT`` — ``1`` transforme ``pending`` en ``error``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CLIPPING_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELAY_DIR = CLIPPING_ROOT / "ORACLE"
ANSWERS_FILENAME = "answers.json"
PENDING_DIRNAME = "pending"

ANSWERS_VERSION = 1


def relay_dir(path: str | os.PathLike | None = None) -> Path:
    if path is not None:
        return Path(path)
    return Path(os.environ.get("ORACLE_RELAY_DIR") or DEFAULT_RELAY_DIR)


def relay_enabled() -> bool:
    return (os.environ.get("ORACLE_RELAY_ENABLED", "1").strip().lower()
            not in {"0", "false", "no", "off"})


def relay_strict() -> bool:
    return (os.environ.get("ORACLE_RELAY_STRICT", "0").strip().lower()
            in {"1", "true", "yes", "on"})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def question_sha256(system_prompt: str, user_prompt: str,
                    expect_json: bool = True) -> str:
    canonical = json.dumps(
        {
            "system": system_prompt or "",
            "user": user_prompt or "",
            "expect_json": bool(expect_json),
        },
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def question_id(system_prompt: str, user_prompt: str,
                expect_json: bool = True) -> str:
    return question_sha256(system_prompt, user_prompt, expect_json)[:16]


def answers_path(directory: str | os.PathLike | None = None) -> Path:
    return relay_dir(directory) / ANSWERS_FILENAME


def pending_dir(directory: str | os.PathLike | None = None) -> Path:
    return relay_dir(directory) / PENDING_DIRNAME


def question_path(qid: str, directory: str | os.PathLike | None = None) -> Path:
    return pending_dir(directory) / f"{qid}.json"


def load_answers(directory: str | os.PathLike | None = None) -> dict:
    path = answers_path(directory)
    if not path.exists():
        return {"version": ANSWERS_VERSION, "answers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": ANSWERS_VERSION, "answers": {}}
    if not isinstance(data, dict):
        return {"version": ANSWERS_VERSION, "answers": {}}
    answers = data.get("answers")
    if not isinstance(answers, dict):
        answers = {}
    data["version"] = data.get("version", ANSWERS_VERSION)
    data["answers"] = answers
    return data


def get_answer(qid: str, directory: str | os.PathLike | None = None) -> dict | None:
    entry = load_answers(directory)["answers"].get(qid)
    return entry if isinstance(entry, dict) else None


def write_question(system_prompt: str, user_prompt: str, *,
                   expect_json: bool = True, source: str | None = None,
                   directory: str | os.PathLike | None = None,
                   extra: dict | None = None) -> dict:
    """Écrit (ou rafraîchit) la question et retourne son descripteur."""
    qid = question_id(system_prompt, user_prompt, expect_json)
    path = question_path(qid, directory)
    existing = None
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
    if existing and existing.get("status") == "pending":
        return {"id": qid, "path": str(path), "question": existing,
                "created": False}

    question = {
        "id": qid,
        "sha256": question_sha256(system_prompt, user_prompt, expect_json),
        "status": "pending",
        "created_at": (existing or {}).get("created_at") or _now(),
        "updated_at": _now(),
        "source": source or (existing or {}).get("source") or "unknown",
        "expect_json": bool(expect_json),
        "system": system_prompt or "",
        "user": user_prompt or "",
    }
    if extra:
        question.update(extra)
    _atomic_write(path, question)
    return {"id": qid, "path": str(path), "question": question, "created": True}


def save_answer(qid: str, content, *, expect_json: bool | None = None,
                answered_by: str = "operator", model: str | None = None,
                note: str | None = None, source: str | None = None,
                directory: str | os.PathLike | None = None) -> dict:
    """Ajoute/écrase une réponse et marque la question correspondante answered."""
    qid = str(qid).strip()
    if not qid:
        raise ValueError("id de question vide")

    if expect_json is None:
        question = read_question(qid, directory)
        expect_json = bool((question or {}).get("expect_json", False))

    if expect_json and isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"réponse attendue en JSON: {exc}") from exc

    data = load_answers(directory)
    data["answers"][qid] = {
        "content": content,
        "expect_json": bool(expect_json),
        "answered_at": _now(),
        "answered_by": answered_by or "operator",
        "model": model,
        "note": note,
        "source": source,
    }
    path = answers_path(directory)
    _atomic_write(path, data)
    mark_question_answered(qid, directory)
    return {"id": qid, "path": str(path), "answer": data["answers"][qid]}


def read_question(qid: str, directory: str | os.PathLike | None = None) -> dict | None:
    path = question_path(qid, directory)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def mark_question_answered(qid: str, directory: str | os.PathLike | None = None) -> None:
    question = read_question(qid, directory)
    if not question:
        return
    question.update({"status": "answered", "updated_at": _now()})
    _atomic_write(question_path(qid, directory), question)


def list_pending(directory: str | os.PathLike | None = None) -> list[dict]:
    root = pending_dir(directory)
    if not root.exists():
        return []
    pending = []
    for path in sorted(root.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if item.get("status") == "pending":
            pending.append(item)
    return pending


def list_answered(directory: str | os.PathLike | None = None) -> list[dict]:
    root = pending_dir(directory)
    if not root.exists():
        return []
    answered = []
    for path in sorted(root.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if item.get("status") == "answered":
            answered.append(item)
    return answered


def status(directory: str | os.PathLike | None = None) -> dict:
    data = load_answers(directory)
    return {
        "enabled": relay_enabled(),
        "strict": relay_strict(),
        "dir": str(relay_dir(directory)),
        "answers": len(data["answers"]),
        "pending": len(list_pending(directory)),
        "answered_questions": len(list_answered(directory)),
    }


def _read_content(args) -> str:
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8")
    if args.content is not None:
        return args.content
    if args.stdin:
        return sys.stdin.read()
    raise SystemExit("Fournir --content, --content-file ou --stdin.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relais oracle sans clé")
    parser.add_argument("--dir", default=None, help="dossier du relais")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="lister les questions en attente")
    sub.add_parser("status", help="état du relais")

    show = sub.add_parser("show", help="afficher une question et sa réponse")
    show.add_argument("id")

    answer = sub.add_parser("answer", help="enregistrer une réponse")
    answer.add_argument("id")
    answer.add_argument("--content")
    answer.add_argument("--content-file")
    answer.add_argument("--stdin", action="store_true")
    answer.add_argument("--text", action="store_true",
                        help="forcer une réponse texte (pas de parsing JSON)")
    answer.add_argument("--by", default="operator")
    answer.add_argument("--model", default=None)
    answer.add_argument("--note", default=None)

    args = parser.parse_args(argv)

    if args.command == "list":
        items = list_pending(args.dir)
        print(json.dumps([
            {"id": q.get("id"), "source": q.get("source"),
             "created_at": q.get("created_at"),
             "user_preview": (q.get("user") or "")[:160]}
            for q in items
        ], ensure_ascii=False, indent=2))
        return 0

    if args.command == "status":
        print(json.dumps(status(args.dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "show":
        question = read_question(args.id, args.dir)
        if not question:
            print(f"Question inconnue: {args.id}", file=sys.stderr)
            return 1
        payload = {"question": question, "answer": get_answer(args.id, args.dir)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "answer":
        question = read_question(args.id, args.dir)
        if not question:
            print(f"Question inconnue: {args.id}", file=sys.stderr)
            return 1
        expect_json = False if args.text else None
        try:
            stored = save_answer(
                args.id, _read_content(args), expect_json=expect_json,
                answered_by=args.by, model=args.model, note=args.note,
                source=question.get("source"), directory=args.dir,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(stored, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
