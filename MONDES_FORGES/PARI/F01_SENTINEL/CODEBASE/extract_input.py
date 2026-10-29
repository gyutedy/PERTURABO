"""
F01 SENTINEL — EXTRACTEUR MULTI-FORMAT
======================================
Porte d'entree unique : fichier ou texte -> texte brut.
Formats : txt, md, markdown, png, jpg, jpeg, webp, pdf, docx.

Le parseur (input_capture.py) recoit uniquement du texte.
Zero Data, Zero Calc : si l'extraction echoue, on signale, on n'invente rien.
"""

import os
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree as ET

TEXT_EXT = {".txt", ".md", ".markdown", ".csv"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
PDF_EXT = {".pdf"}
DOCX_EXT = {".docx"}


def detect_format(path):
    ext = os.path.splitext(path or "")[1].lower()
    if ext in TEXT_EXT:
        return "text"
    if ext in IMAGE_EXT:
        return "image"
    if ext in PDF_EXT:
        return "pdf"
    if ext in DOCX_EXT:
        return "docx"
    return "unknown"


def extract_from_path(path):
    """Retourne {text, format, warnings}. text peut etre vide."""
    warnings = []
    if not path or not os.path.exists(path):
        return {"text": "", "format": "missing", "warnings": [f"fichier introuvable: {path}"]}
    fmt = detect_format(path)
    if fmt == "unknown":
        try:
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
            warnings.append(f"extension inconnue ({os.path.splitext(path)[1]}) — lu comme texte")
            return {"text": txt, "format": "text", "warnings": warnings}
        except UnicodeDecodeError:
            return {"text": "", "format": "unknown",
                    "warnings": [f"format non reconnu et fichier binaire: {path}"]}
    if fmt == "text":
        with open(path, "r", encoding="utf-8") as f:
            return {"text": f.read(), "format": "text", "warnings": warnings}
    if fmt == "docx":
        text, w = extract_docx(path)
        return {"text": text, "format": "docx", "warnings": warnings + w}
    if fmt == "pdf":
        text, w = extract_pdf(path)
        return {"text": text, "format": "pdf", "warnings": warnings + w}
    if fmt == "image":
        text, w = extract_image(path)
        return {"text": text, "format": "image", "warnings": warnings + w}
    return {"text": "", "format": fmt, "warnings": ["extraction impossible"]}


def extract_docx(path):
    warnings = []
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        return "", [f"DOCX illisible: {e}"]
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml)
    lines = []
    for p in root.findall(".//w:p", ns):
        bits = [t.text or "" for t in p.findall(".//w:t", ns)]
        line = "".join(bits).strip()
        if line:
            lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        warnings.append("DOCX sans texte extractible")
    return text, warnings


def extract_pdf(path):
    warnings = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        if text.strip():
            return text, warnings
        warnings.append("pypdf n'a extrait aucun texte — fallback flux brut")
    except Exception:
        pass
    with open(path, "rb") as f:
        data = f.read()
    text = _pdf_literal_strings(data)
    if not text.strip():
        warnings.append("PDF sans texte extractible (scan image ? passe par OCR image ou colle le markdown)")
    return text, warnings


def _pdf_literal_strings(data):
    chunks = []
    for m in re.finditer(rb"\((?:\\.|[^\\)])*\)", data):
        raw = m.group()[1:-1]
        raw = (raw.replace(b"\\(", b"(").replace(b"\\)", b")")
                   .replace(b"\\n", b"\n").replace(b"\\r", b"").replace(b"\\\\", b"\\"))
        try:
            s = raw.decode("latin-1")
        except Exception:
            continue
        if s.strip() and not s.startswith("\\"):
            chunks.append(s)
    return "\n".join(chunks)


def extract_image(path):
    warnings = []
    tess = shutil.which("tesseract")
    if not tess:
        return "", ["OCR image indisponible (tesseract absent) — colle le markdown/texte ou installe tesseract-ocr"]
    try:
        r = subprocess.run(
            [tess, path, "stdout", "-l", "eng+fra", "--psm", "6"],
            capture_output=True, text=True, timeout=90,
        )
        text = (r.stdout or "").strip()
        if r.returncode != 0:
            warnings.append("tesseract a signale une erreur — texte partiel possible")
        if not text:
            warnings.append("OCR image vide — capture illisible, Zero Data, Zero Calc")
        return text, warnings
    except Exception as e:
        return "", [f"OCR image en echec: {e}"]
