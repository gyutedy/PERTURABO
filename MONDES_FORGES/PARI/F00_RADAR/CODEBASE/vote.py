"""
F00 — vote OUT | DOUTE | IGNORE (infos non binaires).
3 sources indépendantes dans 48h → OUT. DOUTE ne touche pas λ.
3 wrappers RapidAPI du même upstream = 1 source.
"""

from datetime import datetime, timezone, timedelta

WINDOW_H = 48

UPSTREAM = {
    "sofascore": "sofascore",
    "sofa": "sofascore",
    "sportradar": "sportradar",
    "sr": "sportradar",
    "statshub": "sportradar",
    "whoscored": "opta",
    "opta": "opta",
    "who": "opta",
}

INDEPENDENT = ("sofascore", "sportradar", "opta")


def _up(name):
    n = (name or "").strip().lower()
    return UPSTREAM.get(n, n)


def _parse_ts(raw):
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def vote_theme(hits, now=None, window_h=WINDOW_H):
    """hits: [{source, ts, fact}]. Retourne {verdict, sources, detail, window_h}."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_h)
    seen = {}
    facts = []
    for h in hits or []:
        up = _up(h.get("source"))
        if up not in INDEPENDENT:
            continue
        ts = _parse_ts(h.get("ts")) or now
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue
        fact = (h.get("fact") or h.get("detail") or "").strip()
        if not fact:
            continue
        if up not in seen:
            seen[up] = fact
            facts.append(fact)
    n = len(seen)
    sources = sorted(seen.keys())
    detail = " | ".join(facts)
    if n >= 3:
        return {"verdict": "OUT", "sources": sources, "detail": detail, "window_h": window_h}
    if n >= 1:
        return {"verdict": "DOUTE", "sources": sources, "detail": detail, "window_h": window_h}
    return {"verdict": "IGNORE", "sources": [], "detail": "", "window_h": window_h}


def impact_for(theme, verdict, rest_days=None):
    """Projection TYRANT. IGNORE/DOUTE → None (pas de themes)."""
    if verdict != "OUT":
        return None
    if theme == "fatigue":
        if rest_days is None:
            return "eleve"
        if rest_days <= 2:
            return "eleve"
        if rest_days == 3:
            return "moyen"
        return None
    if theme in ("blessures", "suspensions", "enjeux"):
        return "eleve"
    if theme in ("meteo", "motivation"):
        return "moyen"
    return "eleve"


def notes_count(notes_blob):
    n = 0
    for note in (notes_blob or {}).get("notes") or []:
        for item in note.get("items") or []:
            if item.get("verdict") == "OUT":
                n += 1
        if not note.get("items"):
            n += len(note.get("themes") or {})
    return n
