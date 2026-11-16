#!/usr/bin/env python3
"""mark1.py -- point d entree unique de MARK1. 7 commandes.

MARK1 ne produit JAMAIS de video. Il produit un pack JSON livrable dans EXPORT/
que le consommateur externe (OMNIS_WATCH) transforme en clip.

Aucune dependance, aucun appel reseau, aucun ffmpeg.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from libs import env, gates, transcript                                        # noqa: E402
# Sous-fregates V3. Chacune a son CODEBASE ; import par chemin explicite.
for _sub in ("M00A_DIRECTIVA", "M00B_SELECTOR", "M00C_METADATA",
             "M00D_VEXILLUM", "M00E_PACKAGER", "M00F_VOX"):
    _p = str(ROOT / _sub / "CODEBASE")
    if _p not in sys.path:
        sys.path.insert(0, _p)
import directiva        # noqa: E402
import selector         # noqa: E402
import metaforge        # noqa: E402
import overlay          # noqa: E402
import vexillum         # noqa: E402
import packager         # noqa: E402
import vox              # noqa: E402
from libs.campaign import evaluate                                 # noqa: E402
from libs.economy import views_needed, revenue, usd_per_hour        # noqa: E402
from libs.ledger import append, read, update, now_iso              # noqa: E402
from libs import siege_log                                        # noqa: E402
from libs.s1_context import analyse                                # noqa: E402
from libs.title_forge import generate as gen_titles                # noqa: E402
from libs.tokens import pack_token, clip_tokens                    # noqa: E402


def _cfg():
    return json.loads((ROOT / "config" / "selection.json").read_text(encoding="utf-8"))


def _code_version():
    """Le commit court du code qui tourne, ou None hors repo git.

    Sans ca, une trace de siege dit ce qui s est passe sans dire avec quelle
    version. Six mois plus tard on ne peut pas rejouer le siege.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=5)
        sha = (out.stdout or "").strip()
        return sha or None
    except (OSError, subprocess.SubprocessError):
        return None


def _fail(run, cfg, code, msg, extra=None):
    """Note le refus dans la trace, l ecrit, et rend le code de sortie 2.

    Centralise pour qu AUCUN chemin de refus n oublie sa trace. Un siege qui
    echoue sans laisser de trace est un siege qu on ne peut pas diagnostiquer.
    """
    print("[FAIL] %s : %s" % (code, msg))
    if extra:
        print(extra)
    siege_log.close(run, "refused", "%s: %s" % (code, msg))
    try:
        p = siege_log.save(run, cfg, str(ROOT))
        print("     trace=%s" % Path(p).name)
    except OSError as e:                                    # pragma: no cover
        print("     (trace non ecrite : %s)" % e)
    return 2


def _asset_mode(pack):
    """Lit asset_mode sous ses trois formes possibles, rend la valeur."""
    r = pack.get("asset_mode") or pack.get("render")
    if isinstance(r, dict):
        return r.get("style") or r.get("mode")
    return r


def cmd_doctor(_a):
    cfg = _cfg()
    print("== MARK1 doctor ==")
    print("[OK] dependances : aucune (stdlib seule, aucun ffmpeg)")
    for name, state, usage in env.doctor():
        print("[%7s] %-24s %s" % (state, name, usage))

    exp = (ROOT / cfg["export_dir"]).resolve()
    print("[%s] %-24s %s" % ("OK" if exp.parent.is_dir() else "FAIL", "export_dir", exp))

    modes = cfg.get("allowed_asset_modes", [])
    print("[%s] %-24s %s" % ("OK" if modes and set(modes) <= {"blur", "reframing"}
                             else "FAIL", "asset_modes", ", ".join(modes)))
    print("[OK] GLOBAL")
    return 0


def cmd_pack(a):
    cfg = _cfg()
    pack = json.loads(Path(a.pack).read_text(encoding="utf-8"))
    ok, code, msg = gates.g0_pack(pack, cfg)
    print("[%s] %s : %s" % ("OK" if ok else "FAIL", code, msg))
    return 0 if ok else 2


def cmd_title(a):
    cfg = _cfg()
    text = a.text or ""
    s1 = analyse(text, subject=a.subject or "",
                 internal_terms=a.internal.split(",") if a.internal else ())
    print("S1 dep=%.4f verdict=%s entites=%s internes=%s"
          % (s1["context_dependency"], s1["verdict"],
             s1["unexplained_entities"], s1["internal_terms"]))
    cands = gen_titles({"text": text, "subject": a.subject or "",
                        "number": a.number or "", "unit": a.unit or "une nuit"}, cfg)
    if not cands:
        print("  aucun gabarit valide -- ecris le titre a la main")
    for c in cands:
        print("  %s [%s] %s" % (c["template_id"], c["stake"], c["text"]))
    return 0


def cmd_campaign(a):
    cfg = _cfg()
    c = json.loads(Path(a.campaign).read_text(encoding="utf-8"))
    v = evaluate(c, cfg, a.platform)
    print(json.dumps(v, indent=2, ensure_ascii=False))
    if a.target:
        n = views_needed(float(a.target), float(c.get("rate_usd_per_1k") or 0),
                         float(cfg.get("platform_fee_pct", 0.10)),
                         float(cfg.get("default_approval_rate", 1.0)))
        print("vues brutes necessaires pour %.0f $ nets : %d" % (float(a.target), n))
    return 0


def cmd_export(a):
    """V3.8 : enchaine les portes, ecrit le pack, la trace et le ledger.

    Ne produit JAMAIS de video. Le pack est le seul livrable.
    En mode ORACLE sans reponse, sort avec le code 3 (etat waiting_oracle).

    TROIS ECRITURES, TROIS ROLES
        1. EXPORT/production_pack_mark1_<token>.json  -> le livrable
        2. EXPORT/sieges/<run>_<token>.json           -> le parcours (immuable)
        3. EXPORT/ledger.csv                          -> une ligne par clip,
           cle = clip_token. C'est dans la ligne qu'on colle `clip_url` quand
           la video est publiee, puis `views_approved` et `paid_usd`.
    """
    cfg = _cfg()
    pack_in = json.loads(Path(a.pack).read_text(encoding="utf-8"))
    run = siege_log.new_run(Path(a.pack).name, a.platform)
    run["code_version"] = _code_version()

    def note(code, ok, msg):
        siege_log.gate(run, code, ok, msg)

    # --- Mode transcript : MARK1 choisit les segments lui-meme ---
    # Si --transcript est fourni (ou si le pack pointe un transcript ARCHIVUM),
    # MARK1 lit les segments horodates produits par F00B_VOX et propose des
    # fenetres. Il ne telecharge rien, il n'appelle aucune fregate.
    tpath = a.transcript
    if not tpath and isinstance(pack_in.get("source"), dict):
        tpath = pack_in["source"].get("transcript_path")
    if not tpath and isinstance(pack_in.get("source"), dict):
        tpath = transcript.find_transcript(cfg, str(ROOT), pack_in["source"].get("vod_url") or "")
    if tpath and not pack_in.get("assets"):
        try:
            doc = transcript.load(tpath)
        except FileNotFoundError as e:
            return _fail(run, cfg, "M1_SELECTION", str(e),
                         "       lance d'abord le workflow perturabo_transcribe sur ce VOD.")
        windows = transcript.candidate_windows(doc, cfg, limit=a.nb_segments)
        if not windows:
            return _fail(run, cfg, "M1_SELECTION",
                         "aucune fenetre exploitable dans %s" % Path(tpath).name)
        pack_in["assets"] = [
            {"id": "A%02d" % (i + 1), "start_sec": w["start_sec"], "end_sec": w["end_sec"],
             "source_text": w["source_text"]}
            for i, w in enumerate(windows)
        ]
        pack_in.setdefault("source", {})
        pack_in["source"]["transcript_path"] = tpath
        note("TRANSCRIPT", True, "%s -> %d segments choisis"
             % (Path(tpath).name, len(pack_in["assets"])))
        print("[OK] TRANSCRIPT : %s -> %d segments choisis"
              % (Path(tpath).name, len(pack_in["assets"])))

    ok, code, msg = gates.g0_pack(pack_in, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)

    # --- M0 : directive (obligatoire, lue depuis ARCHIVUM) ---
    try:
        directive = directiva.run(cfg, str(ROOT))
    except FileNotFoundError as e:
        return _fail(run, cfg, "D0_DIRECTIVE", str(e))
    ok, code, msg = gates.d0_directive(directive, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    print("[OK] D0_DIRECTIVE : %s" % msg)

    # --- M0b : cycle encore ouvert ? ---
    ok, code, msg = gates.m0b_cycle(directive, cfg)
    if not ok:
        return _fail(run, cfg, code, msg,
                     "       (la campagne a peut-etre change de cycle : relis l'annonce)")
    note(code, True, msg)
    print("[OK] M0B_CYCLE : %s" % msg)

    # --- M1 : selection ---
    segments = selector.select(pack_in, directive, cfg, str(ROOT))
    ok, code, msg = gates.m1_selection(segments, directive, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    print("[OK] M1_SELECTION : %s" % msg)

    # --- M5 : transcription (avant M2, le pack porte la transcription) ---
    vox_results = [vox.transcribe_segment(s_, cfg, str(ROOT)) for s_ in pack_in.get("assets") or []]
    ok, code, msg = gates.m5_vox(vox_results, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    print("[OK] M5_VOX : %s" % msg)
    for r in vox_results:
        if r.get("transcript"):
            for s_ in segments:
                if s_["id"] == r["asset_id"]:
                    s_["transcript"] = r["transcript"]

    # --- M2 : overlay (EXC-1) + metadonnees mecaniques ---
    platform = a.platform or (directive.get("platforms") or ["tiktok"])[0]
    run["platform"] = platform
    pt_probe = "%s" % (pack_in.get("pack_token") or "probe")
    try:
        chosen, overlay_mode, rounds, errs = overlay.resolve(
            segments, directive, cfg, str(ROOT), pt_probe)
    except overlay.WaitingOracle as e:
        print("[WAIT] waiting_oracle : %s" % e.pending_path)
        print("       reponds dans ORACLE/answers.json puis relance la commande.")
        note("M2_METADATA", False, "waiting_oracle : %s" % Path(e.pending_path).name)
        siege_log.close(run, "waiting_oracle",
                        "waiting_oracle: %s" % Path(e.pending_path).name)
        siege_log.save(run, cfg, str(ROOT))
        return 3

    built = []
    for seg in segments:
        s_ = dict(seg)
        s_["overlay_title"] = chosen.get(seg["id"]) or ""
        built.append(metaforge.build(s_, directive, cfg, platform))

    ok, code, msg = gates.m2_metadata(built, cfg, had_oracle=(overlay_mode == "oracle"))
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, "%s (overlay=%s, %d round(s))" % (msg, overlay_mode, rounds))
    print("[OK] M2_METADATA : %s (overlay=%s, %d round(s))" % (msg, overlay_mode, rounds))

    # --- M2b : vocabulaire, focus, bait, negative PR ---
    # V3.6 : le focus n'est pas mesurable par MARK1 (la regle de la campagne
    # est visuelle : "as long as she's featured in the clip"). L'operateur
    # peut le DECLARER dans le pack (`focus_declared`), et la declaration est
    # recopiee dans le pack livrable pour etre assumee en aval.
    focus_declared = pack_in.get("focus_declared") or (pack_in.get("source") or {}).get("focus_declared")
    for b in built:
        b["subject"] = directive.get("creator_name") or ""
        b["source_text"] = b.get("source_text") or b.get("transcript") or ""
        if focus_declared:
            b["focus_declared"] = focus_declared
    ok, code, msg = gates.m2b_compliance(built, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    if focus_declared:
        detail = "%s (focus declare par %s)" % (
            msg, (focus_declared.get("asserted_by")
                  if isinstance(focus_declared, dict) else "operator"))
    else:
        detail = "%s (focus mesure dans le texte)" % msg
    note(code, True, detail)
    print("[OK] M2B_COMPLIANCE : %s" % detail)

    # --- M3 : watermark ---
    wm = vexillum.build(cfg, str(ROOT), directive, platform)
    ok, code, msg = gates.m3_watermark(wm, directive, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    run["watermark"] = {"file": wm.get("file"), "format": wm.get("format"),
                        "required": wm.get("required"), "opacity": wm.get("opacity")}
    print("[OK] M3_WATERMARK : %s" % msg)

    # --- A1 / A2 : le compte et la campagne autorisent-ils ce siege ? ---
    # Ces deux portes existaient, etaient testees, et n'etaient JAMAIS appelees
    # par export : un compte banni ou une campagne non financee pouvait
    # exporter. Le guide les annoncait pourtant comme actives.
    ok, code, msg = gates.a1_account(pack_in.get("account") or {}, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    print("[OK] A1_ACCOUNT : %s" % msg)

    verdict = evaluate(pack_in.get("campaign") or {}, cfg, platform)
    ok, code, msg = gates.a2_campaign(verdict)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)
    print("[OK] A2_CAMPAIGN : %s" % msg)

    # --- M4 : packager ---
    asset_mode = pack_in.get("asset_mode") or cfg.get("default_asset_mode", "blur")
    if asset_mode not in (cfg.get("allowed_asset_modes") or ["blur", "reframing"]):
        return _fail(run, cfg, "G0_PACK", "asset_mode %r non autorise" % asset_mode)
    out = packager.build(built, directive, wm, cfg, {
        "mode": pack_in.get("mode", "mark1"),
        "overlay_mode": overlay_mode,
        "asset_mode": asset_mode,
        "subject": pack_in.get("subject"),
        "account": pack_in.get("account") or {},
        "focus_declared": focus_declared,
    })

    ok, code, msg = gates.x1_export(out, cfg)
    if not ok:
        return _fail(run, cfg, code, msg)
    note(code, True, msg)

    path = packager.write(out, cfg, str(ROOT))
    print("[OK] X1_EXPORT : %s" % Path(path).name)
    print("     pack_token=%s  clips=%d  overlay=%s" % (
        out["pack_token"], len(out["assets"]), overlay_mode))

    # --- Le ledger : une ligne par clip, cle = clip_token ---
    # C'est la table qui survit au siege. Elle porte `clip_url`, que
    # l'operateur colle quand la video est publiee, puis `views_approved` et
    # `paid_usd`. Sans cette ecriture, le ledger restait vide et le seul
    # journal des gains etait un fichier inexistant.
    ledger_path = a.ledger or str(ROOT / cfg.get("ledger_path", "../EXPORT/ledger.csv"))
    written = 0
    cpm = float(((directive.get("payouts") or {}).get(platform) or {}).get("usd_per_1k") or 0)
    for asset in out["assets"]:
        row = {
            "clip_token": asset.get("clip_token"),
            "pack_token": out.get("pack_token"),
            "clip_id": asset.get("id"),
            "date": (out.get("exported_at") or "")[:10],
            "exported_at": out.get("exported_at"),
            "vod_url": (pack_in.get("source") or {}).get("vod_url") or pack_in.get("vod_url"),
            "start_sec": asset.get("start_sec"),
            "end_sec": asset.get("end_sec"),
            "asset_mode": out.get("asset_mode"),
            "title": asset.get("overlay_title"),
            "campaign_id": out.get("source", {}).get("campaign_id"),
            "cpm_usd": round(cpm, 4),
            "platform": platform,
            "outcome": "exported",
            "notes": "pack=%s" % Path(path).name,
        }
        if append(ledger_path, row):
            written += 1
        run["assets"].append({
            "id": asset.get("id"),
            "clip_token": asset.get("clip_token"),
            "start_sec": asset.get("start_sec"),
            "end_sec": asset.get("end_sec"),
            "overlay_title": asset.get("overlay_title"),
        })

    print("     ledger=%s  (%d nouveau(x), %d deja present(s))"
          % (Path(ledger_path).name, written, len(out["assets"]) - written))

    # --- La trace : le parcours du siege, ecrit une seule fois ---
    run["pack_token"] = out.get("pack_token")
    run["pack_path"] = str(Path(path).name)
    siege_log.close(run, "exported")
    try:
        tp = siege_log.save(run, cfg, str(ROOT))
        print("     trace=%s" % Path(tp).name)
    except OSError as e:                                    # pragma: no cover
        print("     (trace non ecrite : %s)" % e)
    return 0


def cmd_ledger(a):
    cfg = _cfg()
    # Le ledger vit a cote du pack (EXPORT/), pas dans OUT/ : OUT/ est
    # gitignore par convention, et un journal de gains que git jette ne
    # compte pas les gains.
    ledger_path = a.ledger or str(ROOT / cfg.get("ledger_path", "../EXPORT/ledger.csv"))
    if a.add:
        row = json.loads(Path(a.add).read_text(encoding="utf-8"))
        print("ecrit" if append(ledger_path, row) else "refuse ou deja present")
        return 0
    if a.update:
        changes = json.loads(a.changes) if a.changes else {}
        print("mis a jour" if update(ledger_path, a.update, **changes) else "clip_token absent")
        return 0

    rows = read(ledger_path)
    print("%d lignes  (%s)" % (len(rows), Path(ledger_path).name))
    for r in rows[-10:]:
        print("  %s | %s | url=%s | views=%s | payout=%s"
              % (r.get("clip_token"), r.get("title"),
                 (r.get("clip_url") or "-")[:40],
                 r.get("views_approved") or "-", r.get("paid_usd") or "-"))
    if a.econ:
        fee = float(cfg.get("platform_fee_pct", 0.10))
        for r in rows:
            try:
                v = int(r.get("views_approved") or 0)
                cpm = float(r.get("cpm_usd") or 0)
                m = float(r.get("minutes_worked") or 0)
            except ValueError:
                continue
            print("  %s : %.2f $ net, %.2f $/h"
                  % (r.get("clip_token"), revenue(v, cpm, fee), usd_per_hour(v, cpm, m, fee)))
    return 0


def cmd_selftest(_a):
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=str(ROOT)).returncode


def main():
    p = argparse.ArgumentParser(prog="mark1")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor").set_defaults(f=cmd_doctor)

    q = sub.add_parser("pack")
    q.add_argument("pack")
    q.set_defaults(f=cmd_pack)

    q = sub.add_parser("title")
    q.add_argument("text")
    q.add_argument("--subject", default="")
    q.add_argument("--number", default="")
    q.add_argument("--unit", default="une nuit")
    q.add_argument("--internal", default="")
    q.set_defaults(f=cmd_title)

    q = sub.add_parser("campaign")
    q.add_argument("campaign")
    q.add_argument("--platform", default="tiktok")
    q.add_argument("--target", default=None)
    q.set_defaults(f=cmd_campaign)

    q = sub.add_parser("export")
    q.add_argument("pack")
    q.add_argument("--platform", default="tiktok")
    q.add_argument("--transcript", default=None,
                   help="transcription F00B_VOX (ARCHIVUM/montage/transcripts/). "
                        "Si fournie, MARK1 choisit les segments au lieu de lire le pack.")
    q.add_argument("--nb-segments", type=int, default=3,
                   help="nombre de segments a produire depuis le transcript")
    q.add_argument("--ledger", default=None,
                   help="chemin du ledger CSV (defaut : EXPORT/ledger.csv, a cote du pack)")
    q.set_defaults(f=cmd_export)

    q = sub.add_parser("ledger")
    q.add_argument("--ledger", default=None,
                   help="chemin du ledger CSV (defaut : EXPORT/ledger.csv)")
    q.add_argument("--add", default=None)
    q.add_argument("--update", default=None)
    q.add_argument("--changes", default=None)
    q.add_argument("--econ", action="store_true")
    q.set_defaults(f=cmd_ledger)

    sub.add_parser("selftest").set_defaults(f=cmd_selftest)

    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
