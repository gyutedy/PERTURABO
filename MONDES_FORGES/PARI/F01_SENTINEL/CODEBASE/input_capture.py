"""
F01 SENTINEL — INPUT CAPTURE (flux capture bookmaker → OCR → JSON → carte)
==========================================================================
Le chemin officiel de la campagne :
  1. L'opérateur capture l'écran de son bookmaker (ligue/coupe, date, heure,
     matchs, marchés affichés : 1X2, O/U toutes lignes, MT1/MT2/E, BTTS).
  2. L'OCR (hors monde) sort le texte brut → ce module le parse.
  3. Le JSON reconstitué est affiché : l'opérateur VALIDE avant tout calcul.
  4. Une fois validé, la carte peut être écrite et passée au siège
     (TYRANT → F02 → F03 → ...). Zero Data, Zero Calc : un champ manquant
     est signalé, jamais deviné.

Usage:
  python input_capture.py --capture capture.txt --out-json OUT/capture_parsed.json
  python input_capture.py --capture capture.txt --out-json ... --valider \
      --out-carte ../../ARCHIVUM/fixtures/matches.json
"""

import json
import argparse
import os
import re
from datetime import datetime, timezone

from extract_input import extract_from_path

COTE_FULL_RE = re.compile(r"^\d{1,3}[.,]\d{1,2}$")

# --- Marchés reconnus (labels Winner Bet + variantes OCR) ---------------------
MARKET_ALIASES = {
    "1": ["1", "dom.", "v1", "home", "1x2 home"],
    "X": ["x", "nul", "draw", "mte"],
    "2": ["2", "ext.", "v2", "away"],
    "o1.5": ["o1.5", "over 1.5", "+1.5", "o+1.5"],
    "u1.5": ["u1.5", "under 1.5", "-1.5"],
    "o2.5": ["o2.5", "over 2.5", "+2.5", "o+2.5"],
    "u2.5": ["u2.5", "under 2.5", "-2.5"],
    "o3.5": ["o3.5", "over 3.5", "+3.5", "o+3.5"],
    "u3.5": ["u3.5", "under 3.5", "-3.5"],
    "btts": ["btts", "btts oui", "les deux marquent", "gg"],
    "btts_no": ["btts non", "ng", "les deux ne marquent pas"],
    "mt1": ["mt1", "mt1 dom", "1re mi-temps", "1er mt", "first half"],
    "mte": ["mte", "égalité mt", "egalite mt", "draw half"],
    "mt2": ["mt2", "2e mi-temps", "second half"],
    "dnb1": ["dnb 1", "dnb1", "draw no bet 1"],
    "dnb2": ["dnb 2", "dnb2", "draw no bet 2"],
}
LABEL_LOOKUP = {}
for canon, aliases in MARKET_ALIASES.items():
    for a_ in aliases:
        LABEL_LOOKUP[a_.lower()] = canon

MARGIN_HINT = " ← LIGUE/COUPE"  # rien, doc seulement

# --- Compétitions (tokens d'une LIGUE/COUPE complète) -------------------------
COMPETITION_KEYWORDS = [
    "ligue", "league", "coupe", "cup", "liga", "série", "serie", "super league",
    "championnat", "division", "bundesliga", "eredivisie", "primeira", "premier",
    "jumbotron", "CAF", "CAN", "afcon", "afa", "série", "sous-ligue", "3rd place",
    "play-off", "champions", "europa", "wafer league", "congo cup", "coup",
]

DATE_RE = re.compile(r"\b(\d{4}-\d{1,2}-\d{1,2})\b")
TIME_RE = re.compile(r"\b(\d{1,2})[:hH](\d{2})\b")
COTE_RE = re.compile(r"(\d{1,3}[.,]\d{1,2})\b")
TEAMSEP_RE = re.compile(r"\s+v[ss]+\.?\s+|\s+\bv/\.s\s+| — | – ", re.IGNORECASE)
GAME_LINE_RE = re.compile(r"^\s*([^\d\-/|:+]{2,40}?)\s*(?:—|–|-|v[vs]+\.?|vs\.?)\s*([^\d\-/|:+]{2,40})\s*([|:/+.\d a-zA-Z]*)")


def norm(txt: str) -> str:
    return " ".join((txt or "").split())


def canon_label(tok: str):
    low = tok.lower().replace("o ", "o").replace("u ", "u")
    if low in LABEL_LOOKUP:
        return LABEL_LOOKUP[low]
    for k in ("o2.5", "u2.5", "o1.5", "u1.5", "o3.5", "u3.5"):
        if low.startswith(k[:1]) and k in low:
            return k
    return None


def is_competition_line(line: str) -> bool:
    low = line.lower()
    if COTE_RE.search(line) and len(line) < 25 and not any(k in low for k in COMPETITION_KEYWORDS):
        return False
    return any(k in low for k in COMPETITION_KEYWORDS) and "vs" not in low


LOCKED_TOKENS = {"verrouille", "verrouillé", "locked", "—", "-", "–", "n/a", "na", ""}

HEADER_MAP = {
    "1": "1", "x": "X", "2": "2",
    "1st": "mt1", "1er": "mt1", "mt1": "mt1", "1re mt": "mt1",
    "egal": "mte", "égal": "mte", "egalite": "mte", "égalité": "mte", "mte": "mte",
    "2nd": "mt2", "2e": "mt2", "mt2": "mt2", "2e mt": "mt2",
    "moins": "under", "under": "under", "u": "under",
    "plus": "over", "over": "over", "o": "over",
    "1x": "1X", "x2": "X2", "12": "12",
    "btts": "btts", "gg": "btts",
}


def _md_row_start(stripped: str) -> str:
    """Retourne la ligne tableau si c'est un debut de rang, sinon ''."""
    s = (stripped or "").strip()
    if not s:
        return ""
    if s.startswith("|"):
        return s
    m = re.match(r"^[\s.\d#\-*>]+(\|.*)$", s)
    return m.group(1) if m else ""


def _looks_complete_md_row(row: str, header_pipes=None) -> bool:
    r = (row or "").strip()
    if not r.startswith("|"):
        return False
    n = r.count("|")
    if header_pipes and header_pipes >= 4:
        return n >= header_pipes - 1 and r.endswith("|")
    return n >= 4 and r.endswith("|")


def _normalize_md_table(text: str) -> str:
    """Reassemble les rangs markdown casses par Telegram (<br> → newline)."""
    out = []
    buf = ""
    header_pipes = None

    def flush():
        nonlocal buf
        if not buf:
            return
        row = buf.strip()
        if row.startswith("|") and not row.endswith("|"):
            row = row + " |"
        out.append(row)
        buf = ""

    def take_new(start):
        nonlocal buf, header_pipes
        buf = start
        if _looks_complete_md_row(buf, header_pipes) or "---" in buf or ":-" in buf:
            header_pipes = buf.count("|")
            flush()

    for ln in (text or "").splitlines():
        stripped = ln.strip()
        if not stripped:
            flush()
            out.append("")
            continue
        start = _md_row_start(stripped)
        if buf and not _looks_complete_md_row(buf, header_pipes):
            few_pipes = buf.count("|") <= 2
            if start and _looks_complete_md_row(start, header_pipes) and not few_pipes:
                flush()
                take_new(start)
            else:
                piece = start[1:].strip() if start else stripped
                buf = buf.rstrip() + "<br>" + piece
                if _looks_complete_md_row(buf, header_pipes):
                    flush()
            continue
        if start:
            flush()
            take_new(start)
            continue
        out.append(ln)
    flush()
    return "\n".join(out)


def _is_md_table(text: str) -> bool:
    text = _normalize_md_table(text)
    lines = []
    for ln in text.splitlines():
        start = _md_row_start(ln)
        if start:
            lines.append(start)
    return len(lines) >= 2 and any("---" in ln or ":-" in ln for ln in lines[:6])


def _split_md_row(line: str):
    raw = _md_row_start(line) or line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def _clean_cell(cell: str) -> str:
    cell = cell.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    cell = re.sub(r"\*\*([^*]+)\*\*", r"\1", cell)
    cell = re.sub(r"<[^>]+>", " ", cell)
    return " ".join(cell.replace("\n", " | ").split())


def _cote_or_none(cell: str):
    raw = _clean_cell(cell).strip().lower().replace(",", ".")
    if raw in LOCKED_TOKENS or "verrouill" in raw:
        return None
    m = COTE_FULL_RE.match(raw.replace(" ", ""))
    if not m:
        return None
    val = float(m.group(0).replace(",", "."))
    if 1.01 <= val <= 500:
        return val
    return None


def parse_markdown_table(capture_text: str):
    """Parse un tableau markdown Winner Bet (competition+match, horaire, 1/X/2, MT, O/U)."""
    capture_text = _normalize_md_table(capture_text)
    warnings = []
    blocs_by_comp = {}
    header = None
    bloc_idx = 0
    n = 0

    def bloc_for(comp, date, heure):
        nonlocal bloc_idx
        key = (comp or "?", date or "?", heure or "?")
        if key not in blocs_by_comp:
            bloc_idx += 1
            blocs_by_comp[key] = {
                "id": f"BLOC_{bloc_idx:03d}",
                "competition": comp,
                "date": date,
                "heure": heure,
                "matchs": [],
                "warnings": [],
            }
        return blocs_by_comp[key]

    for raw_line in capture_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = _split_md_row(line)
        if not cells:
            continue
        joined = "|".join(c.lower() for c in cells)
        if "---" in line or ":-" in line:
            continue
        if header is None and ("1" in joined and "x" in joined and "2" in joined):
            header = [_clean_cell(c).lower() for c in cells]
            continue
        if header is None:
            continue
        if len(cells) < 3:
            continue

        first = cells[0].replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        first = re.sub(r"\*\*([^*]+)\*\*", r"\1", first)
        parts = [p.strip() for p in re.split(r"\n|<br\s*/?>", first) if p.strip()]
        competition = None
        match_line = None
        if len(parts) >= 2:
            competition = re.sub(r"<[^>]+>", "", parts[0]).strip()
            match_line = re.sub(r"<[^>]+>", "", parts[-1]).strip()
        else:
            match_line = re.sub(r"<[^>]+>", "", parts[0] if parts else "").strip()
            if " - " in match_line and " vs " not in match_line.lower():
                maybe_comp, rest = match_line.split(" - ", 1)
                if any(k in maybe_comp.lower() for k in COMPETITION_KEYWORDS):
                    competition = maybe_comp.strip()
                    match_line = rest.strip()
            elif " - " in match_line:
                vs_m = re.search(r"\s+vs\.?\s+", match_line, re.IGNORECASE)
                if vs_m:
                    left = match_line[:vs_m.start()].strip()
                    dash = left.find(" - ")
                    if dash != -1:
                        tail = left[dash + 3:].strip()
                        tokens = tail.split()
                        league_n = 1
                        for i, tok in enumerate(tokens):
                            if any(k in tok.lower() for k in COMPETITION_KEYWORDS):
                                league_n = i + 1
                        if league_n < len(tokens):
                            competition = (left[:dash] + " - " + " ".join(tokens[:league_n])).strip()
                            match_line = (" ".join(tokens[league_n:]) + match_line[vs_m.start():]).strip()

        teams = TEAMSEP_RE.split(match_line, maxsplit=1)
        if len(teams) != 2:
            vs = re.split(r"\s+vs\.?\s+", match_line, maxsplit=1, flags=re.IGNORECASE)
            teams = vs if len(vs) == 2 else None
        if not teams or len(teams) != 2:
            warnings.append(f"ligne tableau ignoree (pas de vs): {match_line[:80]}")
            continue
        dom, ext = teams[0].strip(), teams[1].strip()
        if not dom or not ext:
            continue

        col = {header[i]: cells[i] if i < len(cells) else "" for i in range(len(header))}
        horaire = _clean_cell(col.get("horaire") or col.get("heure") or "")
        cur_heure = None
        t = TIME_RE.search(horaire)
        if t:
            cur_heure = f"{int(t.group(1)):02d}:{int(t.group(2)):02d}"
        cur_date = None
        d = DATE_RE.search(horaire) or DATE_RE.search(capture_text)
        if d:
            cur_date = d.group(1)
        elif re.search(r"aujourd.?hui", horaire, re.I):
            cur_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        cotes = {}
        m_warn = []
        ligne_totale = None
        for h, cell in col.items():
            hkey = h.strip().lower()
            if hkey in ("competition & match", "compétition & match", "match", "horaire", "heure",
                        "ligne (total)", "ligne", "total"):
                if hkey.startswith("ligne"):
                    raw_l = _clean_cell(cell).replace(",", ".")
                    try:
                        ligne_totale = float(raw_l)
                    except ValueError:
                        ligne_totale = None
                continue
            mapped = HEADER_MAP.get(hkey)
            if mapped in ("over", "under"):
                val = _cote_or_none(cell)
                if val is None:
                    if _clean_cell(cell).strip() and _clean_cell(cell).strip().lower() not in LOCKED_TOKENS:
                        m_warn.append(f"{hkey} illisible: {_clean_cell(cell)}")
                    continue
                if ligne_totale in (1.5, 2.5, 3.5):
                    tag = ("o" if mapped == "over" else "u") + str(ligne_totale)
                    cotes[tag] = val
                else:
                    m_warn.append(f"{mapped} sans ligne totale — cote non rattachee")
                continue
            if not mapped:
                continue
            val = _cote_or_none(cell)
            if val is None:
                continue
            cotes[mapped] = val

        n += 1
        match = {
            "id": f"M{n}",
            "dom": dom,
            "ext": ext,
            "cotes": cotes,
            "marches_disponibles": sorted(cotes.keys()),
            "warnings": m_warn,
        }
        b = bloc_for(competition, cur_date, cur_heure)
        if not b["heure"] and cur_heure:
            b["heure"] = cur_heure
        b["matchs"].append(match)

    blocs = list(blocs_by_comp.values())
    for b in blocs:
        if not b["competition"]:
            b["warnings"].append("competition/ligue absente — marque manuelle avant siege (Zero Data, Zero Calc)")
        for w in b["warnings"]:
            warnings.append(f"{b['id']}: {w}")
    if n == 0:
        warnings.append("AUCUN match reconnu dans le tableau markdown")
    return {"captures": blocs, "warnings": warnings, "statut": "A_VALIDER", "n_matchs": n,
            "source_format": "markdown_table"}


def parse_capture(capture_text: str):
    """Parse le texte OCR d'une capture de bookmaker (multi-blocs).
    Sortie : {"captures": [bloc…], "warnings": […], "statut": "A_VALIDER"}
    """
    capture_text = _normalize_md_table(capture_text or "")
    if _is_md_table(capture_text):
        return parse_markdown_table(capture_text)

    warnings = []
    blocs = []
    cur_competition = None
    cur_date = None
    cur_heure = None
    bloc_idx = 0

    def new_bloc():
        nonlocal bloc_idx
        bloc_idx += 1
        return {"id": f"BLOC_{bloc_idx:03d}", "competition": None, "date": None,
                "heure": None, "matchs": [], "warnings": []}

    bloc = next_fill = None
    has_open = False

    for raw_line in capture_text.splitlines():
        line = norm(raw_line)
        if not line:
            continue
        d = DATE_RE.search(line)
        t = TIME_RE.search(line)
        if d:
            cur_date = d.group(1)
        if t:
            hh, mm = int(t.group(1)), int(t.group(2))
            if 0 <= hh <= 23 and mm < 60:
                cur_heure = f"{hh:02d}:{mm:02d}"

        if is_competition_line(line):
            if bloc is not None and bloc["matchs"]:
                blocs.append(bloc)
                bloc = None
            cur_competition = line
            continue

        m = GAME_LINE_RE.match(line)
        if m:
            if bloc is None:
                bloc = new_bloc()
                bloc["competition"] = cur_competition
                bloc["date"] = cur_date
                bloc["heure"] = cur_heure
                has_open = True
            dom, ext, rest = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "")
            match = {"id": None, "dom": dom, "ext": ext, "cotes": {}, "marches_disponibles": [], "warnings": []}
            # Cotes étiquetées dans la même ligne ou dans les lignes suivantes
            pending = rest.strip()
            cotes, m_warn = parse_cotes_fragment(pending)
            match["cotes"].update(cotes)
            match["warnings"].extend(m_warn)
            bloc["matchs"].append(match)
            next_fill = match
            continue

        if bloc is not None and bloc["matchs"]:
            cotes, m_warn = parse_cotes_fragment(line)
            if cotes:
                next_fill["cotes"].update(cotes)
                next_fill["warnings"].extend(m_warn)
                continue
            # Fallback : suite de 3+ nombres nu(s) sur une ligne → 1X2 puis warning
            nums = COTE_RE.findall(line)
            if len(nums) >= 3 and next_fill is not None:
                vals = [float(n.replace(",", ".")) for n in nums[:3]]
                if all(1.01 <= v <= 500 for v in vals) and "1" not in next_fill["cotes"]:
                    next_fill["cotes"]["1"], next_fill["cotes"]["X"], next_fill["cotes"]["2"] = vals
                    next_fill["warnings"].append(
                        "cotes 1X2 attachées par position (3 nombres nus) — l'opérateur doit vérifier l'ordre affiché")
                    continue

    if bloc is not None and bloc["matchs"]:
        blocs.append(bloc)

    # Numérotation des matchs + marchés disponibles + propagation warnings blocs
    n = 0
    for b in blocs:
        for i, m in enumerate(b["matchs"], 1):
            n += 1
            m["id"] = m["id"] or f"M{n}"
            m["marches_disponibles"] = sorted(m["cotes"].keys())
        if not b["competition"]:
            b["warnings"].append("compétition/ligue absente — marque manuelle avant siège (Zero Data, Zero Calc)")
        for w in b["warnings"]:
            warnings.append(f"{b['id']} {matching(b, m)}: {w}" if False else f"{b['id']}: {w}")

    total_matches = sum(len(b["matchs"]) for b in blocs)
    if total_matches == 0:
        warnings.append("AUCUN match reconnu dans la capture — vérifie l'OCR ou la capture")

    return {"captures": blocs, "warnings": warnings, "statut": "A_VALIDER",
            "n_matchs": total_matches}


def matching(b, m):  # helper non utilisé (tenu pour lisibilité future)
    return ""


def parse_cotes_fragment(fragment: str):
    """Extrait des cotes étiquetées d'un fragment de texte OCR.
    Gère : étiquettes (O2.5, U2.5, MT1, BTTS…), triplet 1X2 nu par position,
    et le préfixe explicite "1X2" suivi de 3 cotes (éventuellement séparées par '/').
    Retour : (cotes dict, warnings list)"""
    cotes, warnings = {}, []
    if fragment.strip().startswith("|"):
        fragment = fragment.lstrip("|")
    tokens = [t for t in re.split(r"\s+", fragment) if t]
    # gérer les triplets collés "1.55/4.10/6.00"
    expanded = []
    for t in tokens:
        if "/" in t and all(COTE_FULL_RE.match(p.replace(" ", "")) for p in t.split("/")):
            expanded.extend(t.split("/"))
        else:
            expanded.append(t)
    tokens = expanded

    last_label = None
    x2_pending = 0          # nombre de cotes attendues après un préfixe "1X2"
    x2_keys = ["1", "X", "2"]
    unlabeled = []
    for t in tokens:
        t = t.rstrip("|:,;.")
        if not t:
            continue
        tl = t.lower()
        if COTE_FULL_RE.match(t):
            val = float(t.replace(",", "."))
            if not 1.01 <= val <= 500:
                warnings.append(f"cote ignorée hors plage: {t}")
                continue
            if x2_pending > 0:
                key = x2_keys[3 - x2_pending]
                cotes[key] = val
                x2_pending -= 1
            elif last_label:
                cotes[last_label] = val
            else:
                unlabeled.append(val)
            last_label = None
        elif tl in LABEL_LOOKUP:
            last_label = LABEL_LOOKUP[tl]
        elif tl in ("x", "nul", "draw"):
            last_label = "X"
        elif tl in ("oui", "yes"):
            last_label = "btts"
        elif tl in ("non", "no"):
            last_label = "btts_no"
        elif tl in ("1x2", "1x2:"):
            x2_pending = 3
        elif tl.startswith("o") or tl.startswith("u") or tl.startswith("mt") or tl.startswith("dnb"):
            cand = canon_label(tl)
            if cand:
                last_label = cand
    # triplet 1X2 nu : 3 nombres non étiquetés et aucune autre étiquette utilisée
    if len(unlabeled) == 3 and "1" not in cotes and x2_pending == 0:
        cotes["1"], cotes["X"], cotes["2"] = unlabeled
        warnings.append("1X2 déduit par position (3 nombres nus) — l'opérateur doit vérifier l'ordre affiché")
    elif unlabeled:
        warnings.append(f"{len(unlabeled)} cote(s) non étiquetée(s) ignorée(s) — reforme la capture ou étiquette")
    return cotes, warnings


def to_carte(parsed: dict, ligue_default="Capture — ligue à confirmer"):
    """Construit la carte fixtures à partir du JSON VALIDE. */
    Retourne la carte, plus un dict des blocs invalides.
    """
    matchs = []
    for b in parsed.get("captures", []):
        comp = b.get("competition") or ligue_default
        for m in b.get("matchs", []):
            mm = {"id": m["id"], "dom": m["dom"], "ext": m["ext"],
                  "ligue": comp, "date": b.get("date"), "heure": b.get("heure"),
                  "cotes": m.get("cotes") or None,
                  "marches_disponibles": m.get("marches_disponibles", [])}
            matchs.append(mm)
    horizon = parsed.get("captures", [{}])[0].get("date") or "capture"
    return {"source": "input_capture", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ligue": ligue_default, "horizon": f"capture {horizon}",
            "matchs": matchs}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="F01 SENTINEL — input capture multi-format")
    parser.add_argument("--capture", required=False,
                        help="fichier capture : txt, md, png/jpg, pdf, docx")
    parser.add_argument("--out-json", default=os.path.join(here, "..", "OUT", "capture_parsed.json"))
    parser.add_argument("--valider", action="store_true", help="l'opérateur a validé le JSON reconstitué")
    parser.add_argument("--out-carte", default=None, help="écrire la carte fixtures (si validé)")
    args = parser.parse_args()

    if not args.capture:
        print("[INPUT-CAPTURE] usage: --capture <txt|md|png|jpg|pdf|docx> [--valider] [--out-carte carte.json]")
        return 2
    extracted = extract_from_path(args.capture)
    extra_warn = list(extracted.get("warnings") or [])
    text = extracted.get("text") or ""
    if not text.strip():
        parsed = {"captures": [], "warnings": extra_warn + ["AUCUN texte extractible — Zero Data, Zero Calc"],
                  "statut": "A_VALIDER", "n_matchs": 0, "source_format": extracted.get("format")}
    else:
        parsed = parse_capture(text)
        parsed["warnings"] = extra_warn + list(parsed.get("warnings") or [])
        parsed["source_format"] = extracted.get("format")
        if _is_md_table(text):
            parsed["source_format"] = extracted.get("format") + "+markdown_table"
    if args.valider:
        parsed["statut"] = "VALIDE"

    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    print(f"[INPUT-CAPTURE] {parsed['n_matchs']} match(s) reconnu(s) — statut: {parsed['statut']}")
    for b in parsed["captures"]:
        comp = b.get("competition") or "❔"
        print(f"  ├ {b['id']} — {comp} — {b.get('date') or '?'} {b.get('heure') or '?'}")
        for m in b["matchs"]:
            cotes = ", ".join(f"{k}={v}" for k, v in sorted(m["cotes"].items())) or "⚠️ aucune cote"
            print(f"  │   {m['id']}: {m['dom']} - {m['ext']}  → {cotes}")
        for w in b.get("warnings", []):
            print(f"  │   ⚠️ {w}")
    for w in parsed["warnings"]:
        if not w.startswith("BLOC_"):
            print(f"  ⚠️ {w}")

    if args.valider and args.out_carte:
        carte = to_carte(parsed)
        os.makedirs(os.path.dirname(os.path.abspath(args.out_carte)), exist_ok=True)
        with open(args.out_carte, "w", encoding="utf-8") as f:
            json.dump(carte, f, indent=2, ensure_ascii=False)
        print(f"[INPUT-CAPTURE] Carte écrite: {args.out_carte} → prochain pas: "
              f"orchestrator.py --mode siege --fixtures {args.out_carte}")
    if not args.valider:
        print("[INPUT-CAPTURE] ⛔ JSON NON validé — relis-le puis rejoue avec --valider (Porte 1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
