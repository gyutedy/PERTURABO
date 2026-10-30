#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Groupe A — entree multi-format (txt / md / pdf / docx)
==========================================================
Verifie que txt, markdown Winner Bet, PDF et DOCX aboutissent
au meme JSON reconstitute (equipes, cotes, marches) avant tout calcul.
L'image PNG sans tesseract doit sortir Zero Data, Zero Calc (pas de crash).
"""

import io
import os
import struct
import subprocess
import sys
import zipfile
import json

WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = sys.executable
ENV = {**os.environ, "PARI_AUTO_GATES": "1", "PYTHONIOENCODING": "utf-8"}
CHECKS = []
OUT = os.path.join(WORLD, "F01_SENTINEL", "OUT")


def check(name, ok, note=""):
    CHECKS.append((name, bool(ok), note))
    print(f"[E2E] {'PASS' if ok else 'FAIL'} — {name}" + (f" — {note}" if note else ""))


def run_capture(path, out_json):
    r = subprocess.run(
        [PY, "F01_SENTINEL/CODEBASE/input_capture.py", "--capture", path, "--out-json", out_json],
        capture_output=True, text=True, cwd=WORLD, env=ENV, timeout=60,
    )
    out = (r.stdout or "") + (r.stderr or "")
    parsed = {}
    if os.path.exists(out_json):
        with open(out_json, encoding="utf-8") as f:
            parsed = json.load(f)
    return r.returncode, out, parsed


def write_pdf(path, text_lines):
    content = "BT /F1 12 Tf 50 750 Td\n"
    for i, line in enumerate(text_lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i:
            content += "0 -16 Td\n"
        content += f"({safe}) Tj\n"
    content += "ET\n"
    stream = content.encode("latin-1", "replace")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n")
    objs.append(b"4 0 obj<< /Length %d >>stream\n" % len(stream) + stream + b"\nendstream\nendobj\n")
    objs.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    header = b"%PDF-1.4\n"
    body = b"".join(objs)
    xref_pos = len(header) + len(body)
    offsets = [0]
    pos = len(header)
    for o in objs:
        offsets.append(pos)
        pos += len(o)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += ("%010d 00000 n \n" % off).encode()
    trailer = b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref_pos
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + body + xref + trailer)


def write_docx(path, lines):
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paras = []
    for line in lines:
        paras.append(
            f'<w:p xmlns:w="{ns}"><w:r><w:t xml:space="preserve">{line}</w:t></w:r></w:p>'
        )
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{ns}"><w:body>{"".join(paras)}</w:body></w:document>'
    )
    types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)


def write_png_stub(path):
    def chunk(tag, data):
        crc = 0xFFFFFFFF
        body = tag + data
        for b in body:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
        crc ^= 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    import zlib
    idat = zlib.compress(raw)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


PLAIN = """Premier League - England  2026-10-29  18:00
Arsenal - Chelsea  1.85 3.60 4.20  O2.5 1.70 U2.5 2.05  MT1 2.10 MT2 2.20
Liverpool - Everton  1X2 1.55/4.10/6.00  BTTS 1.95 BTTS NON 1.85
"""


def main():
    print("=" * 70)
    print("E2E MULTIFORMAT — txt / md / pdf / docx / image")
    print("=" * 70)
    os.makedirs(OUT, exist_ok=True)

    md = os.path.join(OUT, "capture_winnerbet.md")
    r, out, parsed = run_capture(md, os.path.join(OUT, "e2e_md.json"))
    n = parsed.get("n_matchs", 0)
    matches = []
    for b in parsed.get("captures", []):
        matches.extend(b.get("matchs", []))
    kitchee = next((m for m in matches if "Kitchee" in m.get("ext", "")), {})
    cotes_k = kitchee.get("cotes", {})
    ok = r == 0 and n == 11 and parsed.get("statut") == "A_VALIDER"
    check("A.md_count", ok, f"n_matchs={n} statut={parsed.get('statut')}")
    ok = cotes_k.get("1") == 1.79 and cotes_k.get("mt2") == 2.10 and cotes_k.get("o1.5") == 2.10
    check("A.md_cotes_kitchee", ok, f"cotes={cotes_k}")
    shoulla = next((m for m in matches if "Shoulla" in m.get("dom", "")), {})
    ok = shoulla.get("cotes", {}).get("1") == 2.02 and "mt1" not in shoulla.get("cotes", {})
    check("A.md_verrouille_ignore", ok, f"cotes={shoulla.get('cotes')}")
    comps = {b.get("competition") for b in parsed.get("captures", [])}
    ok = any(c and "AFC" in c for c in comps) and any(c and "Copa del Rey" in c for c in comps)
    check("A.md_competitions", ok, f"{len(comps)} blocs")

    sys.path.insert(0, os.path.join(WORLD, "F01_SENTINEL", "CODEBASE"))
    from input_capture import parse_capture  # noqa: E402

    live_table = (
        "| Compétition & Match | Horaire | 1 | X | 2 | Ligne (Total) | Moins | Plus | 1st | Égal | 2nd |\n"
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        "| **Inde - IFL**<br>Real Kashmir vs Nagaland United SC | Aujourd'hui 14:00 | 1.41 | 4.60 | 5.50 | 2.5 | 2.37 | 1.50 | 3.10 | 3.00 | **2.10** |\n"
        "| **Iran - Pro League**<br>Nassaji Mazandaran FC vs Persepolis FC | Aujourd'hui 14:00 | 8.00 | 3.70 | 1.41 | 2.5 | 1.45 | 2.50 | 3.10 | 3.00 | **2.10** |\n"
        "| **Israël - National League**<br>Hapoel Acre FC vs Hapoel Rishon Lezion FC | Aujourd'hui 14:00 | 6.00 | 4.40 | 1.40 | 2.5 | 2.22 | 1.56 | 3.10 | 3.00 | **2.10** |\n"
        "| **Israël - National League**<br>Hapoel Afula FC vs Maccabi Ironi Kiryat Gat | Aujourd'hui 14:00 | 1.98 | 3.45 | 3.20 | 2.5 | 1.93 | 1.75 | 3.10 | 3.00 | **2.10** |\n"
        "| **Israël - National League**<br>Maccabi Achi Nazareth ... vs FC Kafr Qasim | Aujourd'hui 14:00 | 2.72 | 3.30 | 2.27 | 2.5 | 1.94 | 1.74 | 3.10 | 3.00 | **2.10** |\n"
    )
    p_br = parse_capture(live_table)
    m1 = (p_br.get("captures") or [{}])[0].get("matchs") or [{}]
    m1 = m1[0] if m1 else {}
    ok = p_br.get("n_matchs") == 5 and m1.get("dom") == "Real Kashmir" and m1.get("cotes", {}).get("mt2") == 2.10
    check("A.md_live_br", ok, f"n={p_br.get('n_matchs')} dom={m1.get('dom')} cotes={m1.get('cotes')}")

    p_nl = parse_capture(live_table.replace("<br>", "\n"))
    teams_nl = []
    for b in p_nl.get("captures") or []:
        for m in b.get("matchs") or []:
            teams_nl.append((m.get("dom"), m.get("ext"), b.get("competition")))
    ok = p_nl.get("n_matchs") == 5 and teams_nl[0][0] == "Real Kashmir" and "Inde" in (teams_nl[0][2] or "")
    check("A.md_telegram_newline", ok, f"n={p_nl.get('n_matchs')} teams={teams_nl[:2]}")

    p_sp = parse_capture(live_table.replace("<br>", " "))
    m_sp = []
    for b in p_sp.get("captures") or []:
        m_sp.extend(b.get("matchs") or [])
    ok = p_sp.get("n_matchs") == 5 and m_sp[0].get("dom") == "Real Kashmir" and "IFL" in (p_sp["captures"][0].get("competition") or "")
    check("A.md_br_as_space", ok, f"n={p_sp.get('n_matchs')} dom={m_sp[0].get('dom') if m_sp else None}")

    junk = ". " + live_table.lstrip()
    p_junk = parse_capture(junk)
    check("A.md_junk_prefix", p_junk.get("n_matchs") == 5, f"n={p_junk.get('n_matchs')}")

    cap_txt = os.path.join(OUT, "e2e_plain.txt")
    with open(cap_txt, "w", encoding="utf-8") as f:
        f.write(PLAIN)
    r, out, parsed = run_capture(cap_txt, os.path.join(OUT, "e2e_txt.json"))
    ok = r == 0 and parsed.get("n_matchs") == 2 and parsed.get("statut") == "A_VALIDER"
    check("A.txt_plain", ok, f"n={parsed.get('n_matchs')}")

    pdf_path = os.path.join(OUT, "e2e_plain.pdf")
    write_pdf(pdf_path, [ln for ln in PLAIN.splitlines() if ln.strip()])
    r, out, parsed = run_capture(pdf_path, os.path.join(OUT, "e2e_pdf.json"))
    ok = r == 0 and parsed.get("n_matchs") >= 1
    check("A.pdf_plain", ok, f"n={parsed.get('n_matchs')} warn={parsed.get('warnings', [])[:1]}")

    docx_path = os.path.join(OUT, "e2e_plain.docx")
    write_docx(docx_path, [ln for ln in PLAIN.splitlines() if ln.strip()])
    r, out, parsed = run_capture(docx_path, os.path.join(OUT, "e2e_docx.json"))
    ok = r == 0 and parsed.get("n_matchs") == 2
    check("A.docx_plain", ok, f"n={parsed.get('n_matchs')} fmt={parsed.get('source_format')}")

    png_path = os.path.join(OUT, "e2e_stub.png")
    write_png_stub(png_path)
    r, out, parsed = run_capture(png_path, os.path.join(OUT, "e2e_png.json"))
    ok = r == 0 and parsed.get("n_matchs", 0) == 0 and parsed.get("statut") == "A_VALIDER"
    warn = " ".join(parsed.get("warnings") or []).lower()
    ok = ok and ("ocr" in warn or "tesseract" in warn or "texte extractible" in warn)
    check("A.png_zerodata", ok, f"n={parsed.get('n_matchs')} warn={parsed.get('warnings', [])[:1]}")

    carte = os.path.join(WORLD, "ARCHIVUM", "fixtures", "e2e_md_carte.json")
    r = subprocess.run(
        [PY, "F01_SENTINEL/CODEBASE/input_capture.py",
         "--capture", md, "--valider", "--out-carte", carte,
         "--out-json", os.path.join(OUT, "e2e_md.json")],
        capture_output=True, text=True, cwd=WORLD, env=ENV, timeout=60,
    )
    ok = r.returncode == 0 and os.path.exists(carte)
    if ok:
        with open(carte, encoding="utf-8") as f:
            c = json.load(f)
        ok = len(c.get("matchs", [])) == 11
    check("A.md_valide_carte", ok, carte)

    n_fail = sum(1 for _, ok_, _ in CHECKS if not ok_)
    print("=" * 70)
    print(f"E2E MULTIFORMAT : {len(CHECKS) - n_fail}/{len(CHECKS)} PASS" +
          ("" if n_fail == 0 else f" — {n_fail} ECHEC(S)"))
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
