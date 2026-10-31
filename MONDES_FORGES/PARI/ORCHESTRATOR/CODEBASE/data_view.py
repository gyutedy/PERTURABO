"""
ORCHESTRATOR — vues /data (compact + fiche). Affichage seul, jamais Poisson.
"""

from __future__ import annotations

import re

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


def render_compact(top3, md, carte, notes):
    rows = ranked_rows(top3, md)
    if not rows:
        return "Aucun match classe."
    header = "#  MATCH            Q   SC  ELO   xG      REPOS  H2H    TROU      OUT TOP"
    haute = []
    all_lines = []
    for i, row in enumerate(rows, 1):
        intel = _match_carte(row, carte or {})
        note = _notes_for(row, intel, notes or {})
        dom = intel.get("dom") or row.get("dom") or _split_vs(row.get("match"))[0]
        ext = intel.get("ext") or row.get("ext") or _split_vs(row.get("match"))[1]
        q = _q(row.get("bucket"))
        sc = row.get("score_commun")
        sc_s = f"{sc:.1f}" if isinstance(sc, (int, float)) else "—"
        elo = _elo_cell(intel.get("elo"))
        xg = intel.get("xg") or {}
        xg_s = _fmt_pair(xg.get("dom"), xg.get("ext"), nd=1)
        rd = intel.get("rest_days") or {}
        repos = _fmt_pair(rd.get("dom"), rd.get("ext"))
        h2h = _h2h_cell(intel.get("h2h"))
        trou = _trou_cell(intel.get("holes"))
        out_n = _out_n(note)
        top = _top_cell(row)
        match_s = _pair(dom, ext)[:16]
        line = (
            f"{i:<2} {match_s:<16} {q} {sc_s:>4}  {elo:>4}  {xg_s:<7}  "
            f"{repos:<5}  {h2h:<6}  {trou:<8}  {out_n}   {top}"
        )
        all_lines.append(line)
        if q == "H":
            haute.append(line)
    body = "\n".join([header] + all_lines)
    extra = "\n— = trou. /data N = fiche."
    if len(body) + len(extra) > COMPACT_MAX and haute:
        body = "\n".join([header] + haute) + "\n... /data N"
        extra = ""
    return body + extra


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


def render_fiche(n, top3, md, carte, notes, n_notes=0):
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
    lines = [
        f"#{n}  {dom} vs {ext}",
        f"Q {q}  score {sc_s}  TOP {top}",
        f"Elo {_dash(elo.get('dom'))}/{_dash(elo.get('ext'))}  "
        f"delta {_elo_cell(elo)}",
        f"xG {_fmt_pair(xg.get('dom'), xg.get('ext'), nd=1)}",
        f"Repos {_fmt_pair(rd.get('dom'), rd.get('ext'))}",
        _h2h_block(intel.get("h2h")),
        _form_block("FORME D 10", form.get("dom") or []),
        _form_block("FORME E 10", form.get("ext") or []),
    ]
    if "timing" in holes or not intel.get("goal_minutes"):
        lines.append("TROU timing")
    lines.append(_notes_block(note))
    show = [h for h in holes if h != "timing"]
    if show:
        lines.append("TROU " + ",".join(show))
    return "\n".join(lines)
