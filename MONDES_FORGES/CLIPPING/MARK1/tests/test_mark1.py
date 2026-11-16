#!/usr/bin/env python3
"""MARK1 V2 -- tests. Aucun reseau, aucun ffmpeg. Le disque : tmpdir seulement.

24 tests. Lancer : python3 mark1.py selftest
ou : python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from libs import gates                                        # noqa: E402
from libs.campaign import evaluate                             # noqa: E402
from libs.economy import views_needed, revenue, usd_per_hour   # noqa: E402
from libs.ledger import append, read, update                   # noqa: E402
from libs.s1_context import analyse                            # noqa: E402
from libs.title_forge import generate, validate                # noqa: E402
from libs.tokens import pack_token, clip_token, clip_tokens    # noqa: E402

CFG = json.loads((ROOT / "config" / "selection.json").read_text(encoding="utf-8"))


def _make_pack(**over):
    p = {
        "mode": "mark1",
        "source": {"vod_url": "https://www.twitch.tv/videos/1"},
        "asset_mode": "blur",
        "assets": [
            {"id": "A01", "start_sec": 10, "end_sec": 40,
             "title": "Il a tout perdu en une nuit",
             "caption": "Il a tout perdu en une nuit #ad"},
        ],
    }
    p.update(over)
    return p


class TestEconomy(unittest.TestCase):
    def test_net_per_1k(self):
        from libs import economy
        self.assertAlmostEqual(economy.net_per_1k(1.0875, 0.10), 0.978750, places=6)

    def test_views_needed_500_net(self):
        n = views_needed(500, 1.0875, 0.10)
        self.assertAlmostEqual(n, 510856, delta=3000)

    def test_approval_rate_inflates_views(self):
        self.assertGreater(views_needed(100, 1.0, 0.10, 0.8),
                           views_needed(100, 1.0, 0.10, 1.0))

    def test_cap_limits_revenue(self):
        self.assertLess(revenue(10_000_000, 1.0, 0.10, cap_usd_per_clip=200), 200)

    def test_usd_per_hour_zero_guard(self):
        self.assertEqual(usd_per_hour(1000, 1.0, 0.0), 0.0)


class TestS1(unittest.TestCase):
    def test_bad_title_is_rejected(self):
        r = analyse("Cucumber Key? The Shocking Truth Behind It")
        self.assertEqual(r["verdict"], "reject")
        self.assertIn("Cucumber Key", r["unexplained_entities"])

    def test_universal_sentence_passes(self):
        r = analyse("Il a perdu 5000 dollars en une nuit")
        self.assertEqual(r["verdict"], "ok")

    def test_apposition_explains_entity(self):
        r = analyse("Sophie Rain, la creatrice la plus suivie, a tout arrete")
        self.assertEqual(r["verdict"], "ok")

    def test_subject_is_whitelisted(self):
        r = analyse("Sophie a repondu", subject="Sophie Rain")
        self.assertEqual(r["verdict"], "ok")

    def test_internal_term_flagged(self):
        r = analyse("Il a perdu son duel", internal_terms=("duel",))
        self.assertEqual(r["verdict"], "reject")


class TestTitle(unittest.TestCase):
    def test_generate_returns_only_valid(self):
        cands = generate({"text": "x", "number": "5000"}, CFG)
        self.assertTrue(cands)
        self.assertTrue(all(c["ok"] for c in cands))
        self.assertFalse(any(c["violations"] for c in cands))

    def test_too_long(self):
        self.assertIn("too_many_words",
                      validate("un deux trois quatre cinq six sept huit neuf", CFG))

    def test_cta_rejected(self):
        self.assertIn("cta", validate("Abonne toi pour voir la suite", CFG))

    def test_question_mark_rejected(self):
        self.assertIn("question_mark", validate("Il a perdu combien ?", CFG))

    def test_no_stake_rejected(self):
        self.assertIn("no_stake", validate("Voici une chose", CFG))


class TestGates(unittest.TestCase):
    def test_pack_ok(self):
        self.assertTrue(gates.g0_pack(_make_pack(), CFG)[0])

    def test_wrong_mode(self):
        self.assertFalse(gates.g0_pack(_make_pack(mode="pur"), CFG)[0])

    def test_bad_asset_mode(self):
        self.assertFalse(gates.g0_pack(_make_pack(asset_mode="glow"), CFG)[0])

    def test_no_title(self):
        """V3 : le titre n'est plus exige a l'entree, MARK1 le produit.

        Doctrine "le moteur produit, l'operateur valide" : exiger un titre en
        amont la contredisait. Ce qui reste exige : id, bornes valides.
        """
        p = _make_pack()
        p["assets"][0]["title"] = ""
        self.assertTrue(gates.g0_pack(p, CFG)[0])
        p["assets"][0]["id"] = ""
        self.assertFalse(gates.g0_pack(p, CFG)[0])

    def test_segment_too_long(self):
        p = _make_pack()
        p["assets"][0]["end_sec"] = 500
        self.assertFalse(gates.g0_pack(p, CFG)[0])

    def test_warmup_gate(self):
        self.assertFalse(gates.a1_account({"warmup_days": 2}, CFG)[0])
        self.assertTrue(gates.a1_account({"warmup_days": 30}, CFG)[0])

    def test_disclosure_gate(self):
        self.assertTrue(gates.c2_disclosure(
            {"id": "A01", "caption": "Il a perdu #ad"}, CFG)[0])
        self.assertFalse(gates.c2_disclosure(
            {"id": "A01", "caption": "Il a perdu"}, CFG)[0])

    def test_duration_gate(self):
        self.assertTrue(gates.s2_duration(10, 40, CFG)[0])
        self.assertFalse(gates.s2_duration(10, 500, CFG)[0])

    def test_x1_export_refuses_bad_style(self):
        p = _make_pack(asset_mode="glow")
        for a in p["assets"]:
            a["clip_token"] = "A01-20261115-deadbeef"
            a["exported_at"] = "2026-11-15T00:00:00Z"
        self.assertFalse(gates.x1_export(p, CFG)[0])

    def test_x1_export_refuses_missing_token(self):
        self.assertFalse(gates.x1_export(_make_pack(), CFG)[0])

    def test_x1_export_ok(self):
        p = _make_pack()
        p["pack_token"] = "deadbeef"
        for a in p["assets"]:
            a["clip_token"] = "A01-20261115-deadbeef"
            a["exported_at"] = "2026-11-15T00:00:00Z"
        self.assertTrue(gates.x1_export(p, CFG)[0])


class TestCampaign(unittest.TestCase):
    BASE = {"campaign_id": "C1", "rate_usd_per_1k": 2.0, "funded": True,
            "budget_remaining_usd": 500, "platforms": ["tiktok"],
            "cap_usd_per_clip": 200}

    def test_eligible(self):
        self.assertTrue(evaluate(self.BASE, CFG, "tiktok")["eligible"])

    def test_low_rate(self):
        c = dict(self.BASE); c["rate_usd_per_1k"] = 0.05
        self.assertIn("rate_below_min", evaluate(c, CFG, "tiktok")["reasons"])

    def test_unfunded_is_the_real_risk(self):
        c = dict(self.BASE); c["funded"] = False
        self.assertIn("unfunded", evaluate(c, CFG, "tiktok")["reasons"])

    def test_wrong_platform(self):
        self.assertIn("platform_not_allowed",
                      evaluate(self.BASE, CFG, "instagram")["reasons"])


class TestTokens(unittest.TestCase):
    def test_pack_token_is_deterministic(self):
        p = {"mode": "mark1", "assets": [{"id": "A01"}]}
        self.assertEqual(pack_token(p), pack_token(dict(p)))

    def test_pack_token_ignores_key_order(self):
        a = {"mode": "mark1", "z": 1, "a": 2}
        b = {"a": 2, "mode": "mark1", "z": 1}
        self.assertEqual(pack_token(a), pack_token(b))

    def test_clip_token_contains_pack_token(self):
        tok = clip_token("A01", "20261115", "deadbeef")
        self.assertEqual(tok, "A01-20261115-deadbeef")
        self.assertIn("deadbeef", tok)

    def test_two_clips_two_tokens(self):
        p = {"mode": "mark1", "assets": [{"id": "A01"}, {"id": "A02"}]}
        toks = clip_tokens(p, datetime(2026, 11, 15, tzinfo=timezone.utc))
        self.assertEqual(len(set(toks.values())), 2)
        self.assertTrue(all("20261115" in t for t in toks.values()))


class TestLedger(unittest.TestCase):
    def test_append_idempotent_and_update(self):
        with tempfile.TemporaryDirectory() as td:
            p = str(Path(td) / "ledger.csv")
            row = {"clip_token": "A01-20261115-deadbeef", "title": "t",
                   "minutes_worked": 20}
            self.assertTrue(append(p, row))
            self.assertFalse(append(p, row))
            self.assertEqual(len(read(p)), 1)
            self.assertTrue(update(p, "A01-20261115-deadbeef", views_approved=5000))
            self.assertEqual(read(p)[0]["views_approved"], "5000")

    def test_append_without_clip_token_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = str(Path(td) / "ledger.csv")
            self.assertFalse(append(p, {"title": "sans token"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)

# ---------------------------------------------------------------------------
# Tests V3 : les sous-fregates et leurs gates.
# ---------------------------------------------------------------------------

class TestV3Gates(unittest.TestCase):
    """Chaque gate V3 doit passer sur du bon et refuser du mauvais."""

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        for sub in ("M00A_DIRECTIVA", "M00B_SELECTOR", "M00C_METADATA",
                    "M00D_VEXILLUM", "M00E_PACKAGER", "M00F_VOX"):
            p = str(root / sub / "CODEBASE")
            if p not in sys.path:
                sys.path.insert(0, p)
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def test_d0_directive_reelle(self):
        """M0 doit passer sur la vraie directive AISHAH."""
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        ok, code, msg = gates.d0_directive(d, self.cfg)
        self.assertTrue(ok, msg)
        self.assertEqual(d["language"], "en")
        self.assertAlmostEqual(list(d["payouts"].values())[0]["usd_per_1k"], 0.30, places=2)

    def test_d0_directive_refuse_incomplete(self):
        ok, code, _ = gates.d0_directive({"missing": ["payout"], "language": "en",
                                         "campaign_id": "", "platforms": []}, self.cfg)
        self.assertFalse(ok)

    def test_m1_selection_ok_et_langue(self):
        import selector
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        pack = {"assets": [{"id": "A01", "start_sec": 10, "end_sec": 30,
                            "source_text": "She lost everything overnight."}]}
        sel = selector.select(pack, d, self.cfg, str(self.root))
        self.assertTrue(gates.m1_selection(sel, d, self.cfg)[0])
        sel[0]["language"] = "fr"
        self.assertFalse(gates.m1_selection(sel, d, self.cfg)[0])

    def test_m2_metadata_refuse_cta(self):
        import metaforge
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        seg = {"id": "A01", "language": "en", "key_fact": "She lost everything overnight.",
               "overlay_title": "She lost everything overnight", "entity": ["Aishah Sofey"]}
        a = metaforge.build(seg, d, self.cfg, "tiktok")
        self.assertTrue(gates.m2_metadata([a], self.cfg)[0])
        a["overlay_title"] = "Abonne toi vite"
        self.assertFalse(gates.m2_metadata([a], self.cfg)[0])

    def test_m2_metadata_caption_sans_disclosure(self):
        import metaforge
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        seg = {"id": "A01", "language": "en", "key_fact": "She lost everything overnight.",
               "overlay_title": "She lost everything overnight", "entity": ["Aishah Sofey"]}
        a = metaforge.build(seg, d, self.cfg, "tiktok")
        a["caption"] = a["caption"].replace("#ad", "").replace("#sponsored", "")
        self.assertFalse(gates.m2_metadata([a], self.cfg)[0])

    def test_m3_watermark(self):
        import vexillum
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        w = vexillum.build(self.cfg, str(self.root), d, "tiktok")
        self.assertEqual(w["file"], "aishahsofey_1.png")
        self.assertTrue(w["exists"])
        self.assertGreaterEqual(w["opacity"], 0.75)
        self.assertTrue(gates.m3_watermark(w, d, self.cfg)[0])
        w2 = dict(w); w2["exists"] = False
        self.assertFalse(gates.m3_watermark(w2, d, self.cfg)[0])

    def test_m5_vox(self):
        import vox
        r = [vox.transcribe_segment({"id": "A01", "source_text": "x"}, self.cfg)]
        self.assertTrue(gates.m5_vox(r, self.cfg)[0])
        r2 = [vox.transcribe_segment({"id": "A02"}, self.cfg)]
        self.assertFalse(gates.m5_vox(r2, self.cfg)[0])

    def test_overlay_cta_rejete(self):
        """Le trou de la V2 : un CTA ne doit jamais devenir un overlay_title."""
        import overlay
        ok, why = overlay.accept("Abonne toi vite", self.cfg, "en", "", ())
        self.assertFalse(ok)
        ok, why = overlay.accept("She lost everything overnight", self.cfg, "en", "", ())
        self.assertTrue(ok, why)

    def test_packager_tokens(self):
        import packager
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        asset = {"id": "A01", "start_sec": 1, "end_sec": 20,
                 "overlay_title": "She lost everything overnight",
                 "metadata_title": "t", "description": "d", "tags": ["a"],
                 "hashtags": ["#a"], "caption": "c #ad"}
        pack = packager.build([asset], d, {"file": "x.png"}, self.cfg, {})
        self.assertEqual(len(pack["pack_token"]), 8)
        self.assertIn(pack["pack_token"], pack["assets"][0]["clip_token"])
        self.assertEqual(pack["language"], "en")
        self.assertEqual(pack["watermark"]["file"], "x.png")

    def test_packager_token_stable(self):
        import packager
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        asset = {"id": "A01", "start_sec": 1, "end_sec": 20,
                 "overlay_title": "She lost everything overnight",
                 "metadata_title": "t", "description": "d", "tags": ["a"],
                 "hashtags": ["#a"], "caption": "c #ad"}
        p1 = packager.build([asset], d, {"file": "x.png"}, self.cfg, {})
        p2 = packager.build([asset], d, {"file": "x.png"}, self.cfg, {})
        self.assertEqual(p1["pack_token"], p2["pack_token"])
