"""
ORCHESTRATOR — vues /data (compact + fiche). Affichage seul, jamais Poisson.
S14 : score correspondance + 6 criteres + flags pieges (jamais un p).
"""

from __future__ import annotations

import os
import re
import sys

COMPACT_MAX = 3500
SKIP_TOKS = {
    "fc", "cf", "ud", "sc", "ac", "afc", "as", "ss", "rcd", "vfb", "tsg", "rb",
    "kks", "ce", "sv", "vfl", "vfr", "ogc", "rc", "cd", "ud", "1", "04", "07",
}


def _short_team(name):
    toks = [t for t in re.split(r"[\s.]+", name or "") if t and t.lower() not in SKIP_TOKS]
    return (toks[0] if toks else (name or "?"))[:8]


def _pair(dom, ext):
    return f"{_short_team(dom)}-{_short_team(ext)}"


def _split_vs(label):
    for sep in (" vs ", " vs. ", "–", " - "):
        if sep in (label or ""):
            a, b = (label or "").split(sep, 1)
            return a.strip(), b.strip()
    return (label or "").strip(), ""


def _dash(v):
    return "—" if v is None or v == "" else str(v)


def _fmt_pair(a, b, nd=None):
    if a is None and b is None:
        return "—/—"
    def one(x):
        if x is None:
            return "—"
        if nd is not None and isinstance(x, (int, float)):
            return f"{x:.{nd}f}"
        return str(x)
    return f"{one(a)}/{one(b)}"


def _q(bucket):
    b = (bucket or "").upper()
    if b.startswith("HAUTE"):
        return "H"
    if b.startswith("MOY"):
        return "M"
    if b.startswith("FAIBLE"):
        return "F"
    return "?"


def _match_carte(row, carte):
    mid = row.get("id")
    for m in (carte.get("matchs") or []):
        if mid and m.get("id") == mid:
            return m
    label = row.get("match") or ""
    d, e = row.get("dom"), row.get("ext")
    if not d:
        d, e = _split_vs(label)
    kd, ke = (d or "").lower(), (e or "").lower()
    for m in (carte.get("matchs") or []):
        if (m.get("dom") or "").lower() == kd and (m.get("ext") or "").lower() == ke:
            return m
        if kd and kd in (m.get("dom") or "").lower() and ke and ke in (m.get("ext") or "").lower():
            return m
    return {}


def _notes_for(row, intel, notes):
    mid = row.get("id") or intel.get("id")
    d = (intel.get("dom") or row.get("dom") or _split_vs(row.get("match"))[0] or "").lower()
    e = (intel.get("ext") or row.get("ext") or _split_vs(row.get("match"))[1] or "").lower()
    for n in (notes.get("notes") or []):
        if mid and n.get("match_id") == mid:
            return n
        if (n.get("dom") or "").lower() == d and (n.get("ext") or "").lower() == e:
            return n
    return {}


def _rows_from_top3(top3, md):
    rows = list((top3 or {}).get("matchs") or [])
    if rows:
        return rows
    out = []
    for line in (md or "").splitlines():
        m = re.search(
            r"#(\d+)\s+(.+?)\*\*.*?score\s+\*\*([0-9.]+)",
            line,
        )
        if not m:
            continue
        label = m.group(2).strip()
        dom, ext = _split_vs(label)
        bucket = "HAUTE"
        if "FAIBLE" in line.upper():
            bucket = "FAIBLE"
        elif "MOYENNE" in line.upper():
            bucket = "MOYENNE"
        out.append({
            "rang_global": int(m.group(1)),
            "match": label,
            "dom": dom,
            "ext": ext,
            "score_commun": float(m.group(3)),
            "bucket": bucket,
            "top3": [],
            "no_bet_recommande": "NO BET" in line.upper(),
        })
    return out


def _ordered(rows):
    rank = {"HAUTE": 0, "MOYENNE": 1, "FAIBLE": 2}
    return sorted(
        rows,
        key=lambda r: (
            rank.get((r.get("bucket") or "").upper().split()[0], 9),
            -(r.get("score_commun") or 0),
            r.get("rang_global") or 99,
        ),
    )


def ranked_rows(top3, md):
    return _ordered(_rows_from_top3(top3, md))


def _h2h_cell(h2h):
    if not h2h or h2h.get("played") in (None, 0):
        return "—"
    return f"{h2h.get('dom_wins', 0)}-{h2h.get('draws', 0)}-{h2h.get('ext_wins', 0)}"


def _elo_cell(elo):
    if not elo:
        return "—"
    a, b = elo.get("dom"), elo.get("ext")
    if a is None or b is None:
        return "—"
    d = int(round(a - b))
    return f"{d:+d}"


def _trou_cell(holes):
    show = [h for h in (holes or []) if h != "timing"]
    return ",".join(show) if show else "—"


def _top_cell(row):
    if row.get("no_bet_recommande") or not row.get("top3"):
        return "NO BET"
    s = row["top3"][0]
    sel = s.get("selection") or "?"
    cote = s.get("cote")
    if cote is None:
        return str(sel)
    return f"{sel} @{cote}"


def _out_n(note):
    return sum(1 for it in (note.get("items") or []) if (it.get("verdict") or "").upper() == "OUT")


def _scorer_mod():
    here = os.path.dirname(os.path.abspath(__file__))
    world = os.path.normpath(os.path.join(here, "..", ".."))
    d = os.path.join(world, "F03_FORGEWARD", "CODEBASE")
    if d not in sys.path:
        sys.path.insert(0, d)
    import market_scorer as _ms
    return _ms


def _sel_scored(sel):
    if not sel:
        return None
    return {
        "score": sel.get("scorer_score"),
        "seuil": sel.get("scorer_seuil"),
        "eligible": sel.get("scorer_eligible"),
        "contrib": sel.get("scorer_contrib") or {},
        "refuse": sel.get("scorer_refuse") or [],
        "pieges": sel.get("pieges") or [],
    }


def format_criteres(sel):
    scored = _sel_scored(sel)
    if not scored or scored.get("score") is None:
        return ""
    try:
        return _scorer_mod().format_criteres(scored)
    except Exception:
        return ""


def _pieges_cell(row):
    flags = []
    seen = set()
    for s in (row.get("top3") or []):
        for f in (s.get("pieges") or []):
            if f not in seen:
                seen.add(f)
                flags.append(f)
    if row.get("cote_plate") and "cote_plate" not in seen:
        flags.append("cote_plate")
    return ",".join(flags) if flags else "—"


LEGENDE_SCORER = (
    "SCORER : edge = écart EV / bande = cohérence de la cote / info = asymétrie "
    "d'information / data = qualité des données / marge = overround du book / "
    "confirm = double confirmation. Valeurs 0-1, seuil 0,50-0,60."
)

LEGENDE_COURTE = (
    "LEGENDE — Q : HAUTE ≥7 / MOYENNE ≥5 / FAIBLE <5 · Score : 30% qualité données "
    "+ 40% probabilité + 30% edge · TOP : meilleure cote à EV positive · "
    "TROU : donnée absente, jamais estimée · PIEGES : cote_plate / marge_anomalique "
    "/ cote_figée_sur_news / marche_vitrine · /data N = fiche détaillée."
)


def render_compact(top3, md, carte, notes):
    rows = ranked_rows(top3, md)
    if not rows:
        return "Aucun match classé."
    blocs = [f"DONNEES PARI — {len(rows)} match(s)\n"]
    for i, row in enumerate(rows, 1):
        intel = _match_carte(row, carte or {})
        note = _notes_for(row, intel, notes or {})
        dom = intel.get("dom") or row.get("dom") or _split_vs(row.get("match"))[0]
        ext = intel.get("ext") or row.get("ext") or _split_vs(row.get("match"))[1]
        q = _q(row.get("bucket"))
        sc = row.get("score_commun")
        sc_s = f"{sc:.1f}/10" if isinstance(sc, (int, float)) else "—"
        qual = {"H": "HAUTE", "M": "MOYENNE", "F": "FAIBLE"}.get(q, "?")
        top = _top_cell(row)
        pie = _pieges_cell(row)
        holes = intel.get("holes") or []
        lignes = [
            f"{i}) {dom} — {ext}",
            f"   Qualité : {qual} | Score : {sc_s}",
            f"   TOP : {top} | PIEGES : {pie} | Notes : {_out_n(note)}",
        ]
        if holes:
            lignes.append(f"   TROU : {len(holes)} donnée(s) absente(s) — détail dans /data {i}")
        blocs.append("\n".join(lignes))
    corps = "\n\n".join(blocs)
    if len(corps) + len(LEGENDE_COURTE) > COMPACT_MAX:
        corps = "\n\n".join(blocs[:3]) + "\n\n... suite dans /data N"
    return corps + "\n\n" + LEGENDE_COURTE


def _form_block(title, lines):
    if not lines:
        return f"{title}\n  TROU forme"
    out = [title]
    for L in lines:
        bits = [L.get("date") or "?", L.get("venue") or "?", L.get("opp") or "?",
                f"FT {L.get('ft') or '—'}"]
        if L.get("ht"):
            bits.append(f"HT {L['ht']}")
        extra = []
        if L.get("hs") is not None:
            extra.append(f"hs {L['hs']:.0f}")
        if L.get("hst") is not None:
            extra.append(f"hst {L['hst']:.0f}")
        if extra:
            bits.append(" ".join(extra))
        out.append("  " + "  ".join(str(b) for b in bits))
    return "\n".join(out)


def _h2h_block(h2h):
    if not h2h:
        return "H2H\n  TROU h2h"
    agg = _h2h_cell(h2h)
    lines = [f"H2H  {agg}" if agg != "—" else "H2H"]
    matches = h2h.get("matches") or []
    if not matches:
        lines.append("  TROU h2h_scores")
        return "\n".join(lines)
    for m in matches:
        ht = f"  HT {m['ht']}" if m.get("ht") else "  HT —"
        lines.append(f"  {m.get('date') or '?'}  {m.get('home')} {m.get('ft')} {m.get('away')}{ht}")
    return "\n".join(lines)


def _notes_block(note):
    items = note.get("items") or []
    if not items:
        return "NOTES\n  TROU notes"
    lines = ["NOTES"]
    for it in items:
        src = ",".join(it.get("sources") or []) or "—"
        lines.append(
            f"  {(it.get('verdict') or '?')}  {it.get('theme') or '?'}  "
            f"{it.get('detail') or ''}  [{src}]"
        )
    return "\n".join(lines)


def _motif_rejet(sel, seuil):
    """Pourquoi une cote calculee n'a pas ete retenue. Jamais un p invente."""
    ev = sel.get("ev")
    if ev is None:
        return "EV absente"
    try:
        ev = float(ev)
    except (TypeError, ValueError):
        return "EV illisible"
    if ev <= 0:
        return f"EV {ev * 100:+.1f}% <= 0"
    if seuil is not None and ev < float(seuil):
        return f"EV {ev * 100:+.1f}% < seuil {float(seuil) * 100:.0f}%"
    if sel.get("scorer_eligible") is False:
        return f"scorer {sel.get('scorer_score')} < {sel.get('scorer_seuil')}"
    if sel.get("pieges"):
        return "piege " + ",".join(sel["pieges"])
    return str(sel.get("verdict") or "non retenu")


def marches_ecartes(row, predictions=None, max_lignes=12):
    """Cotes calculees mais absentes du Top 3, avec le motif. Lecture seule."""
    preds = (predictions or {}).get("predictions") or []
    seuil = (predictions or {}).get("seuil_ev_applique")
    cible = None
    rid = row.get("id")
    label = (row.get("match") or "").lower()
    for p in preds:
        if (rid and str(p.get("id")) == str(rid)) or (label and label in (p.get("match") or "").lower()):
            cible = p
            break
    if not cible:
        return []
    retenus = {(s.get("marche"), s.get("selection")) for s in (row.get("top3") or [])}
    out = []
    for s in cible.get("selections") or []:
        key = (s.get("marche"), s.get("selection"))
        if key in retenus:
            continue
        cote = s.get("cote")
        cote_s = f"{float(cote):.2f}" if isinstance(cote, (int, float)) else "—"
        out.append(f"  {s.get('marche')} {s.get('selection')} a {cote_s} : {_motif_rejet(s, seuil)}")
        if len(out) >= max_lignes:
            out.append("  ...")
            break
    return out


def render_fiche(n, top3, md, carte, notes, n_notes=0, predictions=None):
    rows = ranked_rows(top3, md)
    if n < 1 or n > len(rows):
        return f"Rang {n} hors liste (1-{len(rows) or 0})."
    row = rows[n - 1]
    intel = _match_carte(row, carte or {})
    note = _notes_for(row, intel, notes or {})
    dom = intel.get("dom") or row.get("dom") or _split_vs(row.get("match"))[0]
    ext = intel.get("ext") or row.get("ext") or _split_vs(row.get("match"))[1]
    q = _q(row.get("bucket"))
    sc = row.get("score_commun")
    sc_s = f"{sc:.1f}/10" if isinstance(sc, (int, float)) else "—"
    top = _top_cell(row)
    elo = intel.get("elo") or {}
    xg = intel.get("xg") or {}
    rd = intel.get("rest_days") or {}
    holes = intel.get("holes") or []
    form = intel.get("form") or {}
    qual = {"H": "HAUTE", "M": "MOYENNE", "F": "FAIBLE"}.get(q, "?")
    lines = [
        f"FICHE {n} — {dom} — {ext}",
        "",
        f"Qualité : {qual} | Score : {sc_s}",
        f"Meilleur pari (TOP) : {top}",
        "",
        "DONNEES EQUIPES",
        f"  Elo domicile/extérieur : {_dash(elo.get('dom'))} / {_dash(elo.get('ext'))}"
        f" (delta {_elo_cell(elo)})",
        f"  xG domicile/extérieur : {_fmt_pair(xg.get('dom'), xg.get('ext'), nd=1)}",
        f"  Jours de repos : {_fmt_pair(rd.get('dom'), rd.get('ext'))}",
        "",
        _h2h_block(intel.get("h2h")),
        "",
        _form_block("FORME DOMICILE (10)", form.get("dom") or []),
        "",
        _form_block("FORME EXTERIEUR (10)", form.get("ext") or []),
        "",
    ]
    tm = intel.get("goal_minutes") or {}
    if tm.get("goals"):
        g8 = tm["goals"][:8]
        buts = " ".join(f"{g.get('minute')}'{(g.get('side') or '?')[0]}" for g in g8)
        cards = " ".join(f"{c.get('minute')}'" for c in (tm.get("cards") or [])[:4])
        lines.append(f"TIMING {tm.get('home','?')} {tm.get('away','?')} ({tm.get('status','?')})")
        lines.append(f"BUTS {buts}")
        if cards:
            lines.append(f"CARTONS {cards}")
    elif "timing" in holes or not tm.get("event_id"):
        lines.append("TROU timing")
    lines.append(_notes_block(note))
    top_sel = (row.get("top3") or [{}])[0] if row.get("top3") else {}
    crit = format_criteres(top_sel)
    if crit:
        lines.append(crit)
    lect = (top_sel or {}).get("lecture_cotes") or {}
    if lect.get("capture") is not None:
        lignes_cotes = [
            "COTES ET CLV",
            f"  Cote prise à la capture : {lect.get('capture')}",
            f"  T-2h (2h avant coup d'envoi) : "
            f"{lect.get('t2h') if lect.get('t2h') is not None else '— (trou)'}",
            f"  T-0 (clôture au coup d'envoi) : "
            f"{lect.get('t0') if lect.get('t0') is not None else '— (trou)'}",
            "  CLV = cote prise / cote de clôture − 1. Non mesuré si T-0 absent.",
        ]
        lines.extend(lignes_cotes)
    pie = _pieges_cell(row)
    if pie != "—":
        lines.append("PIEGES " + pie)
    show = [h for h in holes if h != "timing"]
    if show:
        lines.append("TROU " + ",".join(show))
    ecartes = marches_ecartes(row, predictions)
    if ecartes:
        lines.append("")
        lines.append("MARCHES CALCULES MAIS NON RETENUS :")
        lines.extend(ecartes)
    lines.append("")
    lines.append(LEGENDE_COURTE)
    lines.append(LEGENDE_SCORER)
    return "\n".join(lines)
