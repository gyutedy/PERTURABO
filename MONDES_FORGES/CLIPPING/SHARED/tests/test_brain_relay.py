#!/usr/bin/env python3
"""Tests d'intégration brain.ask → relais oracle (sans réseau, sans clé)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED))

import brain  # noqa: E402
import oracle_relay as relay  # noqa: E402

PREMIUM_VARS = ("NVIDIA_NIM_API_KEY", "CLIPPING_F00B_API_KEY",
                "CLIPPING_PREMIUM_API_KEY")


class BrainRelayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.saved = {k: os.environ.pop(k, None) for k in PREMIUM_VARS}
        self.saved.update({
            k: os.environ.get(k) for k in
            ("ORACLE_RELAY_DIR", "ORACLE_RELAY_ENABLED", "ORACLE_RELAY_STRICT")
        })
        os.environ["ORACLE_RELAY_DIR"] = str(self.dir)
        os.environ["ORACLE_RELAY_ENABLED"] = "1"
        os.environ.pop("ORACLE_RELAY_STRICT", None)

    def tearDown(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def test_pending_then_answer(self):
        res = brain.ask("sys", "user", expect_json=True, source="F00B")
        self.assertEqual(res["status"], "pending")
        self.assertEqual(res["mode"], "oracle")
        self.assertEqual(res["provider"], brain.RELAY_PROVIDER)
        self.assertTrue(res["question_id"])
        question = json.loads(Path(res["question_path"]).read_text(encoding="utf-8"))
        self.assertEqual(question["source"], "F00B")

        relay.save_answer(res["question_id"], '{"score": 9}',
                          directory=self.dir)
        res2 = brain.ask("sys", "user", expect_json=True, source="F00B")
        self.assertEqual(res2["status"], "ok")
        self.assertEqual(res2["content"], {"score": 9})
        self.assertEqual(res2["mode"], "oracle")

    def test_strict_mode_turns_pending_into_error(self):
        os.environ["ORACLE_RELAY_STRICT"] = "1"
        res = brain.ask("sys", "strict", expect_json=False)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["mode"], "oracle")
        self.assertIn("question en attente", res["error"])

    def test_relay_disabled_without_premium_is_off(self):
        os.environ["ORACLE_RELAY_ENABLED"] = "0"
        self.assertEqual(brain.available_mode(), "off")
        res = brain.ask("sys", "off", expect_json=False)
        self.assertEqual(res["status"], "off")
        self.assertEqual(res["mode"], "off")

    def test_text_answer_roundtrip(self):
        res = brain.ask("sys", "texte", expect_json=False)
        relay.save_answer(res["question_id"], "réponse libre",
                          expect_json=False, directory=self.dir)
        res2 = brain.ask("sys", "texte", expect_json=False)
        self.assertEqual(res2["status"], "ok")
        self.assertEqual(res2["content"], "réponse libre")


if __name__ == "__main__":
    unittest.main()
