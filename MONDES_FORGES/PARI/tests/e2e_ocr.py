#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E OCR P4 — tesseract dans Actions + Zero Data hors tesseract (zero reseau).
Jamais d invention. Image sans binaire = warning, n_matchs 0.
"""

import os
import stat
import sys
import tempfile

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = os.path.normpath(os.path.join(WORLD, "..", ".."))
sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))

CHECKS = []


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def write_png_stub(path):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def main():
    print("=" * 70)
    print("E2E OCR P4 (zero reseau)")
    print("=" * 70)

    import extract_input

    listen = open(os.path.join(REPO, ".github", "workflows", "pari_listen.yml"), encoding="utf-8").read()
    daily = open(os.path.join(REPO, ".github", "workflows", "pari_daily.yml"), encoding="utf-8").read()
    check("OCR.listen_tesseract", "tesseract-ocr" in listen and "tesseract-ocr-fra" in listen)
    inbox_py = open(os.path.join(WORLD, "ORCHESTRATOR", "LISTEN", "inbox_capture.py"), encoding="utf-8").read()
    check("OCR.listen_file_id", "capture_file_id" in listen and "getFile" in inbox_py)
    check("OCR.listen_inbox_script", "ORCHESTRATOR/LISTEN/inbox_capture.py" in listen)
    check("OCR.daily_tesseract", "tesseract-ocr" in daily and "tesseract-ocr-fra" in daily)
    run_listen = listen.find("python ORCHESTRATOR/CODEBASE/workflow.py")
    apt_listen = listen.find("apt-get install -y tesseract-ocr")
    check("OCR.listen_avant_workflow", 0 <= apt_listen < run_listen, f"apt={apt_listen} run={run_listen}")
    run_daily = daily.find("capteurs.py")
    apt_daily = daily.find("apt-get install -y tesseract-ocr")
    check("OCR.daily_avant_capteurs", 0 <= apt_daily < run_daily, f"apt={apt_daily} run={run_daily}")

    src = open(os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "extract_input.py"), encoding="utf-8").read()
    check("OCR.extract_which", "shutil.which(\"tesseract\")" in src)
    check("OCR.zero_data_msg", "OCR image indisponible" in src)

    tmp = tempfile.mkdtemp(prefix="pari-ocr-")
    png = os.path.join(tmp, "stub.png")
    write_png_stub(png)

    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = tmp
    try:
        text, warn = extract_input.extract_image(png)
        blob = " ".join(warn).lower()
        check("OCR.sans_binaire_vide", text == "")
        check("OCR.sans_binaire_warn", "tesseract" in blob or "ocr" in blob, str(warn[:1]))
    finally:
        os.environ["PATH"] = old_path

    fake = os.path.join(tmp, "tesseract")
    with open(fake, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nprintf '%s\\n' 'Iron vs Lions  2.10  3.20  3.40'\n")
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
    os.environ["PATH"] = tmp + os.pathsep + old_path
    try:
        text, warn = extract_input.extract_image(png)
        check("OCR.fake_texte", "Iron vs Lions" in text, text[:80])
        check("OCR.fake_pas_crash", True)
    finally:
        os.environ["PATH"] = old_path

    fake_empty = os.path.join(tmp, "tesseract")
    with open(fake_empty, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(fake_empty, os.stat(fake_empty).st_mode | stat.S_IEXEC)
    os.environ["PATH"] = tmp + os.pathsep + old_path
    try:
        text, warn = extract_input.extract_image(png)
        blob = " ".join(warn).lower()
        check("OCR.vide_zero_data", text == "" and ("vide" in blob or "zero" in blob), str(warn[:1]))
    finally:
        os.environ["PATH"] = old_path

    print("-" * 70)
    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"OCR {len(CHECKS) - len(fails)}/{len(CHECKS)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
