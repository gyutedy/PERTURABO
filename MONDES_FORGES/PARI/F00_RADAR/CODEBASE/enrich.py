"""
F00 ENRICH — gâchette /capture : binaire + notes 3 voix.
Trou visible. Matching par nom. Jamais dans Poisson.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
CONNECTORS = os.path.join(WORLD, "F01_SENTINEL", "CODEBASE", "connectors")
sys.path.insert(0, HERE)
sys.path.insert(0, CONNECTORS)

import cache
import capteurs
import vote

NOTES_3_VOIX = {"E0", "SP1", "I1", "D1", "F1", "N1"}
NOTES_PATH = os.path.join(WORLD, "ARCHIVUM", "fixtures", "notes_qualitatives.json")
ELO_PATH = os.path.join(WORLD, "ARCHIVUM", "teams", "elo.json")


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _dump(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)


def _match_date(m, carte):
    return (m.get("date") or carte.get("date") or "")[:10]


def _code(m, carte):
    return capteurs.ligue_code(m.get("ligue") or carte.get("ligue") or "")


def _elo_blob(date):
    payload, _ = cache.get_or_fetch("clubelo", date or "today", lambda: _fetch_elo(date))
    return payload


def _fetch_elo(date):
    import clubelo
    try:
        data = clubelo.elo_map(date or None)
    except Exception:
        return None
    if data:
        _dump(ELO_PATH, data)
    return data


def _xg_blob(code, date):
    if not code:
        return None
    payload, _ = cache.get_or_fetch("understat", f"{code}-{date or 'na'}", lambda: _fetch_xg(code, date))
    return payload


def _fetch_xg(code, date):
    import understat
    return understat.fetch_league(code, date)


def _fd_blob(dom, ext, date, code):
    if not date:
        return None
    import football_data_org as fdo
    comp = fdo.COMP_BY_CODE.get(code or "")
    key = f"{capteurs.team_key(dom)}_{capteurs.team_key(ext)}_{date}_{comp or ''}"
    payload, _ = cache.get_or_fetch("fdorg", key, lambda: fdo.rest_days_and_h2h(dom, ext, date, competition=comp))
    return payload


def _uk_rows(code):
    if not code:
        return []
    import football_data_uk as uk
    return uk.rows_from_cache(code, "2627", extra_seasons=["2526"])


def _attach_form_h2h(m, holes, code, key_fn=None):
    """Forme 10 + H2H scores depuis le CSV deja telecharge (zero reseau)."""
    import football_data_uk as uk
    rows = _uk_rows(code)
    dom, ext = m.get("dom") or "", m.get("ext") or ""
    form_d = uk.last_matches(rows, dom, n=10, key_fn=key_fn) if rows else []
    form_e = uk.last_matches(rows, ext, n=10, key_fn=key_fn) if rows else []
    if form_d or form_e:
        m["form"] = {"dom": form_d, "ext": form_e}
    if not form_d or not form_e:
        if "form" not in holes:
            holes.append("form")
    csv_h2h = uk.h2h_matches(rows, dom, ext, key_fn=key_fn) if rows else []
    h2h = dict(m.get("h2h") or {})
    if csv_h2h:
        h2h["matches"] = csv_h2h
        agg = uk.h2h_aggregate(csv_h2h, dom, key_fn=key_fn)
        if agg.get("played"):
            h2h["played"] = agg["played"]
            h2h["dom_wins"] = agg["dom_wins"]
            h2h["draws"] = agg["draws"]
            h2h["ext_wins"] = agg["ext_wins"]
            h2h["source"] = h2h.get("source") or "football-data.co.uk"
        m["h2h"] = h2h
        if "h2h" in holes:
            holes.remove("h2h")
        if "h2h_scores" in holes:
            holes.remove("h2h_scores")
    else:
        if not h2h.get("matches") and "h2h_scores" not in holes:
            holes.append("h2h_scores")
        if not h2h.get("played") and "h2h" not in holes:
            holes.append("h2h")


def _voice(mod_name, team, code=None):
    """code n'est utilise que par sportradar (index par competition)."""
    try:
        mod = __import__(mod_name)
        if mod_name == "sportradar" and code:
            return list(mod.missing_players(team, code) or [])
        return list(mod.missing_players(team) or [])
    except Exception:
        return []


def _notes_wanted():
    if os.environ.get("PARI_F00_NOTES") == "0":
        return False
    if os.environ.get("PARI_F00_NOTES") == "1":
        return True
    return bool(os.environ.get("SPORTRADAR_API_KEY") or os.environ.get("WHOSCORED_KEY")
                or os.environ.get("RAPIDAPI_WHOSCORED_KEY"))


def _collect_hits(team, code=None):
    if not _notes_wanted():
        return []
    hits = []
    hits.extend(_voice("sofascore", team))
    hits.extend(_voice("sportradar", team, code))
    hits.extend(_voice("whoscored", team))
    return hits


def _env_skip(*keys):
    return any(os.environ.get(k) == "1" for k in keys)


def enrich_carte(carte, skip_notes=None, skip_binary=None):
    """Enrichit matchs in-place. Retourne (carte, notes_blob)."""
    skip_all = _env_skip("PARI_SKIP_F00", "PARI_SKIP_INJECT")
    skip_notes = skip_notes if skip_notes is not None else (skip_all or _env_skip("PARI_SKIP_NOTES"))
    skip_binary = skip_binary if skip_binary is not None else (skip_all or _env_skip("PARI_SKIP_BINARY"))
    matchs = carte.get("matchs") or []
    notes_out = []
    n_out = 0
    date0 = None
    for m in matchs:
        d = _match_date(m, carte)
        if d:
            date0 = d
            break

    elo_data = None if skip_binary else _elo_blob(date0)
    elos = (elo_data or {}).get("elos") or {}
    xg_by_code = {}

    for m in matchs:
        holes = list(m.get("holes") or [])
        code = _code(m, carte)
        day = _match_date(m, carte)
        dom, ext = m.get("dom") or "", m.get("ext") or ""

        if not skip_binary:
            if elos:
                import clubelo as _cl
                el = dict(m.get("elo") or {})
                for side, team in (("dom", dom), ("ext", ext)):
                    if el.get(side) is not None:
                        continue
                    hit = _cl.best_match(team, elos)
                    if hit:
                        el[side] = hit[1]
                if el:
                    m["elo"] = el
                if el.get("dom") is None or el.get("ext") is None:
                    if "elo" not in holes:
                        holes.append("elo")
            else:
                if "elo" not in holes:
                    holes.append("elo")

            if code and code not in xg_by_code:
                xg_by_code[code] = _xg_blob(code, day)
            xg_blob = xg_by_code.get(code)
            if xg_blob:
                import understat
                xd = understat.lookup(xg_blob, dom)
                xe = understat.lookup(xg_blob, ext)
                m["xg"] = {
                    "dom": (xd or {}).get("xg"),
                    "ext": (xe or {}).get("xg"),
                    "source": "understat",
                }
                if m["xg"]["dom"] is None or m["xg"]["ext"] is None:
                    if "xg" not in holes:
                        holes.append("xg")
            else:
                if "xg" not in holes:
                    holes.append("xg")

            fd = _fd_blob(dom, ext, day, code)
            if fd:
                rd = fd.get("rest_days")
                if rd:
                    m["rest_days"] = rd
                    if rd.get("dom") is None or rd.get("ext") is None:
                        if "rest_days" not in holes:
                            holes.append("rest_days")
                else:
                    if "rest_days" not in holes:
                        holes.append("rest_days")
                if fd.get("h2h"):
                    m["h2h"] = fd["h2h"]
                else:
                    if "h2h" not in holes:
                        holes.append("h2h")
            else:
                for k in ("rest_days", "h2h"):
                    if k not in holes:
                        holes.append(k)

            _attach_form_h2h(m, holes, code, key_fn=capteurs.team_key)
            if "timing" not in holes:
                holes.append("timing")

        m["holes"] = holes

        items = []
        themes = {}
        if not skip_notes and code in NOTES_3_VOIX:
            by_theme = {}
            for team in (dom, ext):
                for h in _collect_hits(team, code):
                    th = h.get("theme") or "blessures"
                    by_theme.setdefault(th, []).append(h)
            for th, hits in by_theme.items():
                v = vote.vote_theme(hits)
                imp = vote.impact_for(th, v["verdict"])
                items.append({
                    "theme": th,
                    "verdict": v["verdict"],
                    "detail": v["detail"],
                    "sources": v["sources"],
                    "window_h": v["window_h"],
                    "impact": imp,
                })
                if v["verdict"] == "OUT":
                    n_out += 1
                    if imp:
                        themes[th] = {"impact": imp, "detail": v["detail"]}

        rest = (m.get("rest_days") or {})
        rd_min = None
        vals = [rest.get("dom"), rest.get("ext")]
        nums = [x for x in vals if isinstance(x, int)]
        if nums:
            rd_min = min(nums)
        if rd_min is not None and rd_min <= 3:
            imp = vote.impact_for("fatigue", "OUT", rest_days=rd_min)
            fat = {
                "theme": "fatigue",
                "verdict": "OUT",
                "detail": f"repos min {rd_min}j (calendrier football-data.org)",
                "sources": ["football-data.org"],
                "window_h": 48,
                "impact": imp,
            }
            items.append(fat)
            n_out += 1
            if imp:
                themes["fatigue"] = {"impact": imp, "detail": fat["detail"]}

        digest = []
        for it in items:
            if it["verdict"] == "OUT":
                digest.append(f"{it['theme']}: {it['detail']}")
        if digest:
            m["notes"] = " ; ".join(digest)[:400]

        rec = {"match_id": m.get("id"), "dom": dom, "ext": ext, "items": items}
        if themes:
            rec["themes"] = themes
        notes_out.append(rec)

    notes_blob = {
        "generated_at": now_str(),
        "source": "f00_vote",
        "notes_count": n_out,
        "window_h": 48,
        "notes": notes_out,
    }
    carte["notes_count"] = n_out
    return carte, notes_blob


def enrich_paths(carte_path, notes_path=None):
    carte = _load(carte_path)
    if not carte:
        return None, None
    carte, notes = enrich_carte(carte)
    _dump(carte_path, carte)
    _dump(notes_path or NOTES_PATH, notes)
    return carte, notes


def enrich_from_capture(parsed, notes_path=None):
    """Construit une carte minimale depuis capture_parsed.json et enrichit."""
    matchs = []
    for bloc in (parsed or {}).get("captures") or []:
        for m in bloc.get("matchs") or []:
            matchs.append({
                "id": m.get("id"),
                "dom": m.get("dom"),
                "ext": m.get("ext"),
                "date": bloc.get("date"),
                "ligue": bloc.get("competition"),
                "cotes": m.get("cotes"),
                "stats": m.get("stats") or {},
            })
    carte = {
        "generated_at": now_str(),
        "source": "f00_enrich",
        "ligue": ((parsed.get("captures") or [{}])[0].get("competition") if parsed else None),
        "matchs": matchs,
    }
    carte, notes = enrich_carte(carte)
    _dump(notes_path or NOTES_PATH, notes)
    return carte, notes
