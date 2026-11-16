#!/usr/bin/env python3
"""MARK1 V2 -- tests. Aucun reseau, aucun ffmpeg. Le disque : tmpdir seulement.

24 tests. Lancer : python3 mark1.py selftest
ou : python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import shutil
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
        # V3.7 : priorite au nom exact du createur (slug) tous formats confondus,
        # puis au PNG plutot qu'au JPEG. Ici `aishahsofey.jpeg` (slug exact)
        # passe donc avant `aishahsofey_1.png`.
        self.assertTrue(w["file"].lower().startswith("aishahsofey"), w["file"])
        self.assertIn(w["format"], ("png", "jpeg", "jpg"), w)
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


# ---------------------------------------------------------------------------
# Tests V3.1 : cycle, compliance, payouts corriges.
# ---------------------------------------------------------------------------

class TestV31Compliance(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        for sub in ("M00A_DIRECTIVA", "M00C_METADATA"):
            p = str(root / sub / "CODEBASE")
            if p not in sys.path:
                sys.path.insert(0, p)
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def test_payouts_corriges(self):
        """X et IG paient 10$/50k = 0.200 $/1k, pas 0.300."""
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        pay = {k: v["usd_per_1k"] for k, v in d["payouts"].items()}
        self.assertAlmostEqual(pay["tiktok"], 0.300, places=3)
        self.assertAlmostEqual(pay["youtube_shorts"], 0.300, places=3)
        self.assertAlmostEqual(pay["twitter_x"], 0.200, places=3)
        self.assertAlmostEqual(pay["instagram_reels"], 0.200, places=3)

    def test_cycle_expire_refuse(self):
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        ok, code, msg = gates.m0b_cycle(d, self.cfg, "2030-01-01")
        self.assertFalse(ok)
        self.assertIn("expire", msg)

    def test_cycle_ouvert_accepte(self):
        fake = {"cycle": {"start": "2026-11-01", "end": "2027-01-31"}}
        ok, code, msg = gates.m0b_cycle(fake, self.cfg, "2026-11-16")
        self.assertTrue(ok, msg)

    def test_forbidden_scrub(self):
        from libs import compliance
        out, hits = compliance.scrub("She is an OnlyFans star", self.cfg)
        self.assertNotIn("OnlyFans", out)
        self.assertIn("onlyfans", hits)
        self.assertIn("content creator", out)
        self.assertNotIn("an content", out)

    def test_forbidden_rejette_dans_overlay(self):
        from libs import compliance
        a = {"id": "A01", "overlay_title": "OnlyFans star exposed",
             "source_text": "Aishah Sofey spoke about her channel.",
             "transcript": "Aishah Sofey spoke about her channel.",
             "subject": "Aishah Sofey", "metadata_title": "x", "description": "y"}
        ok, why = compliance.check_asset(a, self.cfg)
        self.assertFalse(ok)
        self.assertTrue(any("interdit" in w for w in why))

    def test_focus_absent_refuse(self):
        from libs import compliance
        r = compliance.focus_report("The boat was big and blue", "Aishah Sofey", "", self.cfg)
        self.assertFalse(r["ok"])

    def test_focus_present_accepte(self):
        from libs import compliance
        r = compliance.focus_report("Aishah Sofey said this boat is hers", "Aishah Sofey", "", self.cfg)
        self.assertTrue(r["ok"])

    def test_bait_refuse(self):
        from libs import compliance
        r = compliance.bait_report("You won't believe this shocking quit", "She lost her keys", self.cfg)
        self.assertFalse(r["ok"])

    def test_negative_pr_refuse(self):
        from libs import compliance
        r = compliance.negative_pr_report("she is a scam artist and a liar", self.cfg)
        self.assertFalse(r["ok"])

    def test_metaforge_neuveut_pas_onlyfans(self):
        import metaforge
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        seg = {"id": "A01", "language": "en",
               "key_fact": "She is an OnlyFans star who lost everything.",
               "overlay_title": "She lost everything overnight",
               "entity": ["Aishah Sofey"]}
        m = metaforge.build(seg, d, self.cfg, "tiktok")
        blob = " ".join([m["description"], m["caption"], " ".join(m["tags"])]).lower()
        self.assertNotIn("onlyfans", blob)


# ---------------------------------------------------------------------------
# Tests V3.2 : vox lit la convention de la forge (f00b_secrets.json).
# ---------------------------------------------------------------------------

class TestVoxSecrets(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        p = str(root / "M00F_VOX" / "CODEBASE")
        if p not in sys.path:
            sys.path.insert(0, p)
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def test_secrets_absent_donne_raison_claire(self):
        """Sans base_url, on explique ou le trouver. Pas d'exception."""
        import vox
        cfg = json.loads(json.dumps(self.cfg))
        cfg["vox"]["secrets_path"] = "../CONTRACTS/__absent__.json"
        c = vox._secrets(cfg, str(self.root))
        self.assertEqual(c["url"], "")
        text, reason = vox.transcribe("/tmp/x.m4a", cfg, str(self.root), retries=1)
        self.assertEqual(text, "")
        self.assertIn("base_url absent", reason)
        self.assertIn("perturabo_transcribe", reason)

    def test_secrets_lu_quand_present(self):
        import vox
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"base_url": "https://x--whisper.modal.run",
                       "env_var_name": "MODAL_TOKEN_ID", "language": "en",
                       "max_audio_mb": 24}, fh)
        try:
            cfg = json.loads(json.dumps(self.cfg))
            cfg["vox"]["secrets_path"] = path
            c = vox._secrets(cfg, str(self.root))
            self.assertEqual(c["url"], "https://x--whisper.modal.run")
            self.assertEqual(c["language"], "en")
            self.assertTrue(c["secrets_found"])
        finally:
            os.unlink(path)

    def test_multipart_valide(self):
        """Le corps doit porter file, language et offset."""
        import vox
        body, ctype = vox._multipart({"language": "en", "offset": "897.000"},
                                     [("file", "seg.m4a", b"FAKE")])
        self.assertTrue(ctype.startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="file"', body)
        self.assertIn(b'name="offset"', body)
        self.assertIn(b"897.000", body)
        self.assertIn(b"FAKE", body)

    def test_segment_avec_transcript_neuf_appelle_rien(self):
        """Option B : une transcription fournie en amont court-circuite le service."""
        import vox
        r = vox.transcribe_segment({"id": "A01", "transcript": "already here"}, self.cfg, str(self.root))
        self.assertEqual(r["transcript"], "already here")
        self.assertEqual(r["reason"], "")


# ---------------------------------------------------------------------------
# Tests V3.3 : lecture des transcriptions F00B_VOX depuis ARCHIVUM.
# ---------------------------------------------------------------------------

class TestTranscript(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        self.root = Path(__file__).resolve().parent.parent
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        self.cfg = json.loads((self.root / "config" / "selection.json").read_text(encoding="utf-8"))
        self.sample = self.root / "tests" / "fixtures" / "transcript_sample.json"

    def test_vod_id_twitch(self):
        from libs import transcript
        self.assertEqual(transcript.vod_id("https://twitch.tv/videos/2927914500"), "2927914500")

    def test_vod_id_youtube(self):
        from libs import transcript
        self.assertEqual(transcript.vod_id("https://www.youtube.com/watch?v=ElGoUp-0cqY"), "ElGoUp-0cqY")

    def test_load_et_segments(self):
        from libs import transcript
        doc = transcript.load(str(self.sample))
        segs = transcript.segments(doc)
        self.assertGreater(len(segs), 10)
        self.assertIn("start", segs[0])
        self.assertIn("text", segs[0])

    def test_window_text(self):
        from libs import transcript
        doc = transcript.load(str(self.sample))
        t = transcript.window_text(doc, 0, 30)
        self.assertTrue(t)
        self.assertNotIn("  ", t)

    def test_window_ne_chevauche_pas(self):
        from libs import transcript
        doc = transcript.load(str(self.sample))
        self.assertEqual(transcript.window_text(doc, 100000, 100100), "")

    def test_candidate_windows(self):
        from libs import transcript
        doc = transcript.load(str(self.sample))
        w = transcript.candidate_windows(doc, self.cfg, limit=3)
        self.assertTrue(w)
        self.assertLessEqual(len(w), 3)
        lo = self.cfg["min_segment_sec"]
        hi = self.cfg["max_segment_sec"]
        for x in w:
            d = x["end_sec"] - x["start_sec"]
            self.assertGreaterEqual(d, lo - 0.5)
            self.assertLessEqual(d, hi + 0.5)
            self.assertTrue(x["source_text"])

    def test_find_transcript_absent_donne_none(self):
        from libs import transcript
        self.assertIsNone(transcript.find_transcript(self.cfg, str(self.root), "999999999999"))


class TestTranscriptFormatReel(unittest.TestCase):
    """Le format que F00B_VOX auto_detect ecrit vraiment dans ARCHIVUM.

    V3.3 avait ete validee contre une fixture au format invente : les
    transcripts reels ont `segments: null` et des `words[]` horodates. Ces
    tests portent sur une copie fidele d'un fichier de prod.
    """

    def setUp(self):
        import sys
        from pathlib import Path
        self.root = Path(__file__).resolve().parent.parent
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        self.cfg = json.loads((self.root / "config" / "selection.json").read_text(encoding="utf-8"))
        self.words_sample = self.root / "tests" / "fixtures" / "transcript_words_sample.json"

    def test_words_produisent_des_segments(self):
        from libs import transcript
        doc = transcript.load(str(self.words_sample))
        self.assertIsNone(doc["segments"])
        segs = transcript.segments(doc, self.cfg)
        self.assertGreater(len(segs), 4)
        for s in segs:
            self.assertIn("start", s)
            self.assertIn("text", s)
            self.assertTrue(s["text"])

    def test_words_duration_parle_du_dernier_mot(self):
        from libs import transcript
        doc = transcript.load(str(self.words_sample))
        self.assertAlmostEqual(transcript.duration(doc, self.cfg), 231.1, places=1)

    def test_words_fenetre_lit_le_texte(self):
        from libs import transcript
        doc = transcript.load(str(self.words_sample))
        t = transcript.window_text(doc, 0, 20, self.cfg)
        self.assertIn("lost everything", t)

    def test_words_fenetres_proposees(self):
        from libs import transcript
        doc = transcript.load(str(self.words_sample))
        w = transcript.candidate_windows(doc, self.cfg, limit=3)
        self.assertTrue(w, "aucune fenetre sur un transcript en mode words")
        for x in w:
            self.assertTrue(x["source_text"])
            self.assertGreaterEqual(x["end_sec"] - x["start_sec"],
                                    self.cfg["min_segment_sec"] - 0.5)

    def test_segments_a_la_racine(self):
        """Mode `segments` de F00B : pas d'enveloppe `transcript`."""
        from libs import transcript
        doc = {"vod_duration": 60.0,
               "segments": [{"start": 0.0, "end": 4.0, "text": "hello there"}]}
        segs = transcript.segments(doc, self.cfg)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["text"], "hello there")

    def test_doc_vide_ne_leve_pas(self):
        from libs import transcript
        for doc in ({}, None, {"segments": None, "words": []}):
            self.assertEqual(transcript.segments(doc, self.cfg), [])
            self.assertEqual(transcript.candidate_windows(doc or {}, self.cfg), [])


# ---------------------------------------------------------------------------
# V3.5 : A1/A2 enfin branches sur export ; M3 ne juge plus l'opacite ;
# le pack embarque le PNG dans EXPORT/.
# ---------------------------------------------------------------------------

class TestV35Gates(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        for sub in ("M00A_DIRECTIVA", "M00C_METADATA", "M00D_VEXILLUM", "M00E_PACKAGER"):
            p = str(root / sub / "CODEBASE")
            if p not in sys.path:
                sys.path.insert(0, p)
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def test_m3_opacite_ne_bloque_plus(self):
        """V3.5 : MARK1 ne pose pas la video ; l'opacite est une consigne pour
        OMNIS_WATCH, plus un critere de porte. Le PNG qui EXISTE passe meme a 0."""
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        w = {"file": "aishahsofey_1.png", "path": "/tmp/aishahsofey_1.png",
             "exists": True, "required": True, "opacity": 0.0,
             "position": "center", "size_pct": 15}
        ok, code, msg = gates.m3_watermark(w, d, self.cfg)
        self.assertTrue(ok, msg)

    def test_m3_refuse_png_absent_si_requis(self):
        import directiva
        d = directiva.run(self.cfg, str(self.root))
        w = {"file": "", "exists": False, "required": True}
        ok, code, msg = gates.m3_watermark(w, d, self.cfg)
        self.assertFalse(ok)
        self.assertIn("absent", msg)

    def test_a2_refuse_campagne_non_financee(self):
        """Le risque reel du guide : funded=false ne paie jamais."""
        camp = {"campaign_id": "X", "rate_usd_per_1k": 0.3,
                "funded": False, "budget_remaining_usd": 100,
                "platforms": ["tiktok"]}
        verdict = evaluate(camp, self.cfg, "tiktok")
        ok, code, msg = gates.a2_campaign(verdict)
        self.assertFalse(ok)
        self.assertIn("unfunded", verdict["reasons"])

    def test_a1_refuse_warmup_trop_court(self):
        ok, code, msg = gates.a1_account({"warmup_days": 2, "banned": False}, self.cfg)
        self.assertFalse(ok)
        self.assertIn("warmup", msg)

    def test_export_embarque_le_png(self):
        """write() copie le PNG a cote du pack et reecrit watermark.file."""
        import packager
        tmp = tempfile.mkdtemp()
        fake = {"watermark": {"file": "", "path": None, "exists": False,
                              "required": True, "opacity": 0.8}}
        cfg = dict(self.cfg)
        cfg["export_dir"] = tmp
        p1 = os.path.join(tmp, "test.png")
        with open(p1, "wb") as fh:
            fh.write(b"\x89PNG\r\nfake")
        fake["watermark"]["path"] = p1
        fake["watermark"]["exists"] = True
        fake["pack_token"] = "abcdef01"
        fake["mode"] = "mark1"
        p = packager.write(fake, cfg, str(self.root))
        self.assertTrue(os.path.exists(p))
        with open(p, "r", encoding="utf-8") as fh:
            written = json.load(fh)
        self.assertTrue(written["watermark"]["bundled"])
        bundled = os.path.join(tmp, written["watermark"]["file"])
        self.assertTrue(os.path.exists(bundled))
        self.assertEqual(os.path.getsize(bundled), os.path.getsize(p1))


# ---------------------------------------------------------------------------
# V3.6 : le focus passe de juge a greffier.
# ---------------------------------------------------------------------------

class TestV36FocusDeclaratif(unittest.TestCase):
    """La campagne exige "main focus", mais la regle est visuelle.

    Compter le nom dans la transcription refusait la VOD TWITCHCON (POV camera
    portee, 0 mention du prenom en 2 h 53) alors que le personnage principal
    etait a l'ecran tout le temps. MARK1 ne peut pas voir : il enregistre la
    declaration de l'operateur, et refuse seulement si rien n'est declare.
    """

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def test_sans_declaration_zero_mention_refuse(self):
        from libs import compliance
        f = compliance.focus_report("", "Aishah Sofey",
                                    "we lost 12 pounds of water chip", self.cfg)
        self.assertFalse(f["ok"])
        self.assertEqual(f["source"], "measured")
        self.assertIn("aucune declaration", f["reason"])

    def test_declaration_operateur_suffit(self):
        from libs import compliance
        f = compliance.focus_report(
            "", "Aishah Sofey", "we lost 12 pounds of water chip", self.cfg,
            declared={"asserted_by": "operator", "evidence": "POV camera portee"})
        self.assertTrue(f["ok"])
        self.assertEqual(f["source"], "declared")
        self.assertEqual(f["asserted_by"], "operator")
        self.assertEqual(f["evidence"], "POV camera portee")

    def test_declaration_booleenne(self):
        from libs import compliance
        f = compliance.focus_report("", "Aishah Sofey", "x", self.cfg, declared=True)
        self.assertTrue(f["ok"])
        self.assertEqual(f["source"], "declared")

    def test_mesure_reste_un_repli_utile(self):
        """Un segment qui NOMME le sujet passe sans declaration."""
        from libs import compliance
        f = compliance.focus_report("", "Aishah Sofey",
                                    "I'm Aishah and this is my stream", self.cfg)
        self.assertTrue(f["ok"], f["reason"])
        self.assertEqual(f["source"], "measured")

    def test_check_asset_propage_la_declaration(self):
        from libs import compliance
        asset = {"id": "A01", "subject": "Aishah Sofey",
                 "source_text": "we lost 12 pounds of water chip",
                 "overlay_title": "She lost 12 pounds",
                 "focus_declared": {"asserted_by": "operator"}}
        ok, why = compliance.check_asset(asset, self.cfg)
        self.assertTrue(ok, why)
        asset2 = dict(asset)
        del asset2["focus_declared"]
        ok2, why2 = compliance.check_asset(asset2, self.cfg)
        self.assertFalse(ok2)
        self.assertTrue(any("focus" in w for w in why2))

    def test_pack_porte_focus_declared(self):
        import packager
        out = packager.build([], {"campaign_id": "X", "language": "en", "platforms": ["TikTok"]},
                             {"file": ""}, self.cfg,
                             {"focus_declared": {"asserted_by": "operator",
                                                 "evidence": "POV"}})
        self.assertEqual(out["focus_declared"]["asserted_by"], "operator")


# ---------------------------------------------------------------------------
# V3.7 : le watermark peut etre PNG ou JPEG.
# ---------------------------------------------------------------------------

class TestV37WatermarkFormats(unittest.TestCase):
    """Clipify livre tantot un PNG transparent, tantot un JPEG aplati.

    `vexillum` ne cherchait que des `.png` : un JPEG valide dans watermarks/
    etait invisible, et M3 refusait d'exporter en disant "PNG absent" alors
    qu'il etait la. Et `packager` forcait l'extension `.png` a la copie, ce
    qui produisait un JPEG mal nomme dans EXPORT/.
    """

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _wm_dir(self):
        d = os.path.join(self.tmp, "watermarks")
        os.makedirs(d, exist_ok=True)
        cfg = json.loads(json.dumps(self.cfg))
        cfg.setdefault("directiva", {})["watermark_dir"] = d
        cfg.setdefault("directiva", {})["watermark_rules"] = os.path.join(d, "rules.json")
        return d, cfg

    def test_jpeg_est_trouve(self):
        import vexillum
        d, cfg = self._wm_dir()
        open(os.path.join(d, "aishahsofey.jpeg"), "wb").write(b"\xff\xd8\xff\xe0fake")
        found, all_ = vexillum.find_watermark(
            cfg, self.tmp, "Aishah Sofey", "2026-07-24_AISHAH_SOFEY_MULTI")
        self.assertIsNotNone(found)
        self.assertTrue(found.lower().endswith(".jpeg"))

    def test_jpg_est_trouve(self):
        import vexillum
        d, cfg = self._wm_dir()
        open(os.path.join(d, "aishahsofey.jpg"), "wb").write(b"\xff\xd8\xff\xe0fake")
        found, _ = vexillum.find_watermark(cfg, self.tmp, "Aishah Sofey", "")
        self.assertIsNotNone(found)
        self.assertTrue(found.lower().endswith(".jpg"))

    def test_png_reste_prioritaire(self):
        """Si les deux existent, le PNG (fond transparent) gagne."""
        import vexillum
        d, cfg = self._wm_dir()
        open(os.path.join(d, "aishahsofey.jpeg"), "wb").write(b"\xff\xd8\xff\xe0fake")
        open(os.path.join(d, "aishahsofey.png"), "wb").write(b"\x89PNGfake")
        found, _ = vexillum.find_watermark(cfg, self.tmp, "Aishah Sofey", "")
        self.assertTrue(found.lower().endswith(".png"))

    def test_build_expose_le_format(self):
        import vexillum
        d, cfg = self._wm_dir()
        open(os.path.join(d, "aishahsofey.jpeg"), "wb").write(b"\xff\xd8\xff\xe0fake")
        wm = vexillum.build(cfg, self.tmp,
                            {"creator_name": "Aishah Sofey", "campaign_id": "X"}, "tiktok")
        self.assertEqual(wm["format"], "jpeg")
        self.assertEqual(wm["ext"], ".jpeg")
        self.assertTrue(wm["exists"])

    def test_m3_accepte_un_jpeg(self):
        from libs import gates
        wm = {"file": "aishahsofey.jpeg", "path": "/x/aishahsofey.jpeg",
              "format": "jpeg", "required": True, "exists": True}
        ok, code, msg = gates.m3_watermark(
            wm, {"platforms": ["TikTok"]}, self.cfg)
        self.assertTrue(ok, msg)
        self.assertIn("JPEG", msg)

    def test_packager_conserve_l_extension(self):
        """Un JPEG reste un .jpeg dans EXPORT/, il ne devient pas .png."""
        import packager
        d, cfg = self._wm_dir()
        cfg["export_dir"] = os.path.join(self.tmp, "EXPORT")
        src = os.path.join(d, "aishahsofey.jpeg")
        open(src, "wb").write(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
        out = packager.build(
            [], {"campaign_id": "X", "language": "en", "platforms": ["TikTok"]},
            {"file": "aishahsofey.jpeg", "path": src, "format": "jpeg"},
            cfg, {})
        path = packager.write(out, cfg, self.tmp)
        written = json.loads(open(path, encoding="utf-8").read())
        self.assertTrue(written["watermark"]["file"].endswith(".jpeg"))
        self.assertEqual(written["watermark"]["bundled_ext"], "jpeg")
        self.assertTrue(os.path.exists(
            os.path.join(cfg["export_dir"], written["watermark"]["file"])))


# ---------------------------------------------------------------------------
# V3.8 : une seule identite, une trace par run, un ledger qui se remplit.
# ---------------------------------------------------------------------------

class TestV38IdentiteUnique(unittest.TestCase):
    """`packager` et `libs.tokens` calculaient le pack_token differemment.

    Sur un vrai pack ils rendaient 275cfb51 au lieu de e99bd523. Un appel a
    `clip_tokens(pack)` fabriquait donc des tokens qui ne correspondaient a
    aucun clip livre : le ledger aurait cree des lignes orphelines et
    l'appariement clip_token <-> lien publie aurait casse en silence.
    """

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))

    def _assets(self):
        return [
            {"id": "A01", "overlay_title": "She lost 50,000 dollars",
             "metadata_title": "aishah soft", "caption": "cap one"},
            {"id": "A02", "overlay_title": "She lost 86,000 seconds",
             "metadata_title": "aishah soft", "caption": "cap two"},
        ]

    def test_packager_et_tokens_donnent_le_meme_token(self):
        import packager
        from libs import tokens
        pack = packager.build(self._assets(),
                              {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                              {"file": ""}, self.cfg, {})
        self.assertEqual(pack["pack_token"], tokens.pack_token(pack))

    def test_le_watermark_ne_change_pas_le_token(self):
        """Changer d'opacite n'est pas changer de clip."""
        import packager
        a = packager.build(self._assets(),
                           {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                           {"file": "x.png", "opacity": 0.8}, self.cfg, {})
        b = packager.build(self._assets(),
                           {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                           {"file": "x.jpeg", "opacity": 0.95}, self.cfg, {})
        self.assertEqual(a["pack_token"], b["pack_token"])

    def test_le_contenu_change_le_token(self):
        import packager
        assets = self._assets()
        a = packager.build(assets,
                           {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                           {"file": ""}, self.cfg, {})
        assets[0]["overlay_title"] = "Something else entirely"
        b = packager.build(assets,
                           {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                           {"file": ""}, self.cfg, {})
        self.assertNotEqual(a["pack_token"], b["pack_token"])

    def test_clip_tokens_du_pack_correspondent_aux_assets(self):
        import packager
        from libs import tokens
        pack = packager.build(self._assets(),
                              {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                              {"file": ""}, self.cfg, {})
        recalcules = tokens.clip_tokens(pack, when=datetime(2026, 11, 16))
        for asset in pack["assets"]:
            self.assertEqual(recalcules[asset["id"]], asset["clip_token"])

    def test_exported_at_est_au_niveau_du_pack(self):
        import packager
        pack = packager.build(self._assets(),
                              {"campaign_id": "C", "language": "en", "platforms": ["TikTok"]},
                              {"file": ""}, self.cfg, {})
        self.assertTrue(pack["exported_at"])
        # et reste sur l'asset, parce que X1_EXPORT le verifie par asset
        self.assertTrue(pack["assets"][0]["exported_at"])


class TestV38TraceDeSiege(unittest.TestCase):
    """Un run doit laisser une trace lisible. Une trace reecrite ne prouve rien."""

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self.root = root
        self.cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))
        self.tmp = tempfile.mkdtemp()
        self.cfg["siege_log_dir"] = os.path.join(self.tmp, "sieges")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_trace_ecrite_et_relue(self):
        from libs import siege_log
        run = siege_log.new_run("packs/x.json", "tiktok")
        siege_log.gate(run, "G0_PACK", True, "3 assets")
        siege_log.gate(run, "M0B_CYCLE", False, "cycle expire")
        siege_log.close(run, "refused")
        path = siege_log.save(run, self.cfg, self.tmp)

        d = json.loads(open(path, encoding="utf-8").read())
        self.assertEqual(d["status"], "refused")
        self.assertEqual(len(d["gates"]), 2)
        self.assertEqual([g["state"] for g in d["gates"]], ["OK", "FAIL"])
        self.assertIsNotNone(d["duration_sec"])

    def test_deux_runs_ne_s_ecrasent_pas(self):
        from libs import siege_log
        run = siege_log.new_run("packs/x.json", "tiktok")
        run["pack_token"] = "abc12345"
        p1 = siege_log.save(run, self.cfg, self.tmp)
        p2 = siege_log.save(run, self.cfg, self.tmp)
        self.assertNotEqual(p1, p2)
        self.assertTrue(os.path.exists(p1))
        self.assertTrue(os.path.exists(p2))

    def test_trace_ne_contient_aucun_secret(self):
        from libs import siege_log
        run = siege_log.new_run("packs/x.json", "tiktok")
        siege_log.close(run, "exported")
        path = siege_log.save(run, self.cfg, self.tmp)
        blob = open(path, encoding="utf-8").read().lower()
        for danger in ("token_id", "token_secret", "api_key", "password", "ghp_"):
            self.assertNotIn(danger, blob)


class TestV38LedgerAlimente(unittest.TestCase):
    """`libs.ledger` existait, etait teste, et n'etait JAMAIS appele par export.

    Le siege du 16/11 n'a laisse aucune ligne : le seul journal des gains
    etait un fichier inexistant.
    """

    def setUp(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_une_ligne_par_clip_avec_les_colonnes_du_suivi(self):
        from libs.ledger import append, read
        path = os.path.join(self.tmp, "ledger.csv")
        row = {
            "clip_token": "A01-20261116-abc12345",
            "pack_token": "abc12345",
            "clip_url": "",
            "views_approved": "",
            "paid_usd": "",
        }
        self.assertTrue(append(path, row))
        rows = read(path)
        self.assertEqual(len(rows), 1)
        # les colonnes qui servent au suivi existent et attendent leur valeur
        for col in ("clip_url", "published_at", "submitted_at",
                    "views_raw", "views_approved", "paid_usd"):
            self.assertIn(col, rows[0])

    def test_append_idempotent_par_clip_token(self):
        from libs.ledger import append, read
        path = os.path.join(self.tmp, "ledger.csv")
        row = {"clip_token": "A01-20261116-abc12345", "title": "un"}
        self.assertTrue(append(path, row))
        self.assertFalse(append(path, row))
        self.assertFalse(append(path, {"clip_token": row["clip_token"], "title": "deux"}))
        rows = read(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "un")

    def test_update_remplit_le_lien_publie(self):
        from libs.ledger import append, read, update
        path = os.path.join(self.tmp, "ledger.csv")
        tok = "A02-20261116-abc12345"
        append(path, {"clip_token": tok})
        ok = update(path, tok,
                    clip_url="https://tiktok.com/x",
                    published_at="2026-11-16T18:00:00Z",
                    views_approved=51200)
        self.assertTrue(ok)
        row = read(path)[0]
        self.assertEqual(row["clip_url"], "https://tiktok.com/x")
        self.assertEqual(row["views_approved"], "51200")

    def test_le_ledger_par_defaut_est_dans_export(self):
        """OUT/ est gitignore par convention : un ledger la-bas est jete."""
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        cfg = json.loads((root / "config" / "selection.json").read_text(encoding="utf-8"))
        self.assertIn("EXPORT", cfg.get("ledger_path", ""))
        self.assertNotIn("OUT/", cfg.get("ledger_path", ""))
