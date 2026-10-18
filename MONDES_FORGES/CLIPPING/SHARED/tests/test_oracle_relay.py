#!/usr/bin/env python3
"""Tests stdlib du relais oracle (aucun réseau, aucune clé)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED))

import oracle_relay as relay  # noqa: E402


class RelayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_question_id_deterministic(self):
        a = relay.question_id("sys", "user", True)
        b = relay.question_id("sys", "user", True)
        c = relay.question_id("sys", "user", False)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 16)

    def test_missing_answer_writes_pending_question(self):
        info = relay.write_question("Tu es un arbitre", "Extrait A",
                                    expect_json=True, source="F00B",
                                    directory=self.dir)
        self.assertTrue(info["created"])
        path = Path(info["path"])
        self.assertTrue(path.exists())
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(stored["source"], "F00B")
        self.assertEqual(stored["sha256"], relay.question_sha256(
            "Tu es un arbitre", "Extrait A", True))
        self.assertEqual(len(relay.list_pending(self.dir)), 1)
        self.assertIsNone(relay.get_answer(info["id"], self.dir))

    def test_rewrite_pending_keeps_created_at(self):
        first = relay.write_question("s", "u", directory=self.dir)
        created = first["question"]["created_at"]
        second = relay.write_question("s", "u", directory=self.dir)
        self.assertFalse(second["created"])
        self.assertEqual(second["question"]["created_at"], created)

    def test_save_answer_marks_question_answered(self):
        info = relay.write_question("s", "u", expect_json=True,
                                    source="F00C", directory=self.dir)
        relay.save_answer(info["id"], '{"score": 7.5}', model="sandbox",
                          directory=self.dir)
        self.assertEqual(relay.get_answer(info["id"], self.dir)["content"],
                         {"score": 7.5})
        self.assertEqual(relay.list_pending(self.dir), [])
        self.assertEqual(relay.read_question(info["id"], self.dir)["status"],
                         "answered")
        self.assertEqual(relay.status(self.dir)["answers"], 1)

    def test_save_text_answer(self):
        info = relay.write_question("s", "u", expect_json=False,
                                    directory=self.dir)
        relay.save_answer(info["id"], "réponse libre", expect_json=False,
                          directory=self.dir)
        entry = relay.get_answer(info["id"], self.dir)
        self.assertEqual(entry["content"], "réponse libre")
        self.assertFalse(entry["expect_json"])

    def test_invalid_json_rejected_when_expected(self):
        info = relay.write_question("s", "u", expect_json=True,
                                    directory=self.dir)
        with self.assertRaises(ValueError):
            relay.save_answer(info["id"], "pas du json", directory=self.dir)
        self.assertIsNone(relay.get_answer(info["id"], self.dir))

    def test_corrupted_answers_file_tolerated(self):
        relay.answers_path(self.dir).parent.mkdir(parents=True, exist_ok=True)
        relay.answers_path(self.dir).write_text("{oops", encoding="utf-8")
        self.assertEqual(relay.load_answers(self.dir)["answers"], {})
        info = relay.write_question("s", "u", directory=self.dir)
        relay.save_answer(info["id"], "ok", expect_json=False,
                          directory=self.dir)
        self.assertEqual(relay.get_answer(info["id"], self.dir)["content"], "ok")

    def test_flags(self):
        os.environ.pop("ORACLE_RELAY_ENABLED", None)
        os.environ.pop("ORACLE_RELAY_STRICT", None)
        self.assertTrue(relay.relay_enabled())
        self.assertFalse(relay.relay_strict())
        os.environ["ORACLE_RELAY_ENABLED"] = "0"
        os.environ["ORACLE_RELAY_STRICT"] = "1"
        try:
            self.assertFalse(relay.relay_enabled())
            self.assertTrue(relay.relay_strict())
        finally:
            os.environ.pop("ORACLE_RELAY_ENABLED", None)
            os.environ.pop("ORACLE_RELAY_STRICT", None)


if __name__ == "__main__":
    unittest.main()
