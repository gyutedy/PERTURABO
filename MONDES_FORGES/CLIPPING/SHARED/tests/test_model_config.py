#!/usr/bin/env python3
"""Garde-fou : le modèle premium par défaut doit rester aligné partout."""

import re
import sys
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent
REPO = SHARED.parents[2]
sys.path.insert(0, str(SHARED))

import brain  # noqa: E402

OLD_MODEL = "moonshotai/kimi-k3"
DEFAULT_MODEL = "openai/gpt-oss-20b"


class ModelConfigTest(unittest.TestCase):
    def test_brain_default(self):
        self.assertEqual(brain.DEFAULT_PREMIUM_MODEL, DEFAULT_MODEL)

    def test_workflows_use_default(self):
        workflows = sorted((REPO / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(workflows, "aucun workflow trouvé")
        seen = []
        for path in workflows:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(OLD_MODEL, text, f"ancien modèle dans {path.name}")
            seen += re.findall(r"NVIDIA_NIM_MODEL:\s*(\S+)", text)
            seen += re.findall(r'"model_id":\s*"([^"]+)"', text)
        self.assertTrue(seen, "aucun modèle premium déclaré en CI")
        for model in seen:
            self.assertEqual(model, DEFAULT_MODEL)

    def test_operational_files_have_no_old_model(self):
        targets = [SHARED / "brain.py"]
        targets += sorted((REPO / "MONDES_FORGES" / "CLIPPING" / "CONTRACTS").glob("*.json"))
        for path in targets:
            self.assertNotIn(
                OLD_MODEL, path.read_text(encoding="utf-8"),
                f"ancien modèle dans {path.relative_to(REPO)}",
            )


if __name__ == "__main__":
    unittest.main()
