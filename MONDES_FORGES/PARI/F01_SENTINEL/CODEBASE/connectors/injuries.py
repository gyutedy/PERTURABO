"""
S15 — API-Football injuries = flags TYRANT.
Jamais un P. Jamais un 2e facteur lambda (severite = table A S13).
Cle existante API_FOOTBALL_KEY. Holes si KO. Cache 1 hit / ligue / jour.
"""

import difflib
import os
import sys
import unicodedata

_THIS = os.path.dirname(os.path.abspath(__file__))
_WORLD = os.path.normpath(os.path.join(_THIS, "..", "..", ".."))
CAP = os.path.normpath(os.path.join(_WORLD, "F00_RADAR", "CODEBASE"))
if CAP not in sys.path:
    sys.path.insert(0, CAP)
import cache
import http_util

BASE = "https://v3.football.api-sports.io"

LEAGUES = {
    "E0": 39, "SP1": 140, "I1": 135, "D1": 78, "F1": 61,
    "N1": 88, "T1": 203, "J1": 98, "E1": 40, "D2": 79,
}

S15_FLAGS = (
    "double_motivation",
    "satisfait_nul",
    "buteur_manquant",
    "defenseur_manquant",
)

_STRIP = {
    "fc", "cf", "sc", "ac", "afc", "as", "ss", "ssc", "us", "ud", "sd", "cd",
    "ca", "rc", "rcd", "club", "de", "del", "la", "le", "the", "futbol",
    "football", "calcio", "ii", "sv", "vfl", "vfb", "tsg", "fsv", "spvgg",
}

_ATT_TOKENS = {
    "f", "fw", "att", "attacker", "forward", "striker", "w", "wing", "winger",
    "cf", "st", "lw", "rw", "lf", "rf", "ss",
}
_DEF_TOKENS = {
    "d", "df", "def", "defender", "cb", "lb", "rb", "lwb", "rwb", "wb",
    "centreback", "fullback", "wingback",
}


def _load_env_pari():
    for name in (".env", "env_pari"):
        path = os.path.join(_WORLD, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key, val = k.strip(), v.strip()
                    if key and val and not os.environ.get(key):
                        os.environ[key] = val
        except OSError:
            pass


_load_env_pari()


def _key_or_none():
    return os.environ.get("API_FOOTBALL_KEY") or None


def _season_for(date):
    if not date or len(date) < 7:
        return None
    try:
        y = int(date[:4])
        return y if int(date[5:7]) >= 7 else y - 1
    except ValueError:
        return None


def _norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    tokens = []
    for raw in s.split():
        tok = "".join(c for c in raw if c.isalnum())
        if not tok or tok.isdigit() or tok in _STRIP:
            continue
        tokens.append(tok)
    return "".join(tokens)


def _match_name(name, idx):
    n = _norm(name)
    if not n or not idx:
        return None
    if n in idx:
        return idx[n]
    close = difflib.get_close_matches(n, list(idx), n=1, cutoff=0.9)
    if close:
        return idx[close[0]]
    return None


def _empty(reason, extra_holes=None):
    holes = ["injuries"]
    for h in extra_holes or []:
        if h not in holes:
            holes.append(h)
    return {
        "flags": [],
        "holes": holes,
        "detail": {"reason": reason},
        "source": "api-football",
    }


def _response(data):
    if not isinstance(data, dict):
        return None
    err = data.get("errors")
    if isinstance(err, dict) and err:
        return None
    if isinstance(err, list) and err:
        return None
    resp = data.get("response")
    if resp is None:
        return None
    return resp


def _af_get(path, key):
    url = f"{BASE}{path}"
    return http_util.get_json(url, headers={"x-apisports-key": key})


def _fetch_injuries(league_id, day, key):
    data = _af_get(f"/injuries?league={league_id}&date={day}", key)
    resp = _response(data)
    if resp is None:
        return None
    out = []
    for row in resp:
        if not isinstance(row, dict):
            continue
        player = row.get("player") or {}
        team = row.get("team") or {}
        out.append({
            "player": player.get("name") or "",
            "position": player.get("position") or player.get("pos") or "",
            "type": player.get("type") or "",
            "reason": player.get("reason") or "",
            "team": team.get("name") or "",
        })
    return out


def _fetch_standings(league_id, season, key):
    data = _af_get(f"/standings?league={league_id}&season={season}", key)
    resp = _response(data)
    if resp is None:
        return None
    rows = []
    for block in resp:
        if not isinstance(block, dict):
            continue
        league = block.get("league") or {}
        tables = league.get("standings") or []
        if tables and isinstance(tables[0], list):
            tables = tables[0]
        for rec in tables or []:
            if not isinstance(rec, dict):
                continue
            team = (rec.get("team") or {}).get("name") or ""
            played = ((rec.get("all") or {}).get("played"))
            rows.append({
                "rank": rec.get("rank"),
                "team": team,
                "played": played,
            })
    return rows


def _bucket(position):
    if not position:
        return None
    s = str(position).strip().lower().replace("-", " ").replace("_", " ")
    if not s:
        return None
    if any(k in s for k in ("wing back", "wingback", "full back", "fullback",
                             "centre back", "center back", "centreback")):
        return "def"
    if "back" in s and "wing" not in s:
        return "def"
    tokens = set(s.split())
    tokens.add(s.split()[0])
    if tokens & _DEF_TOKENS or any(t in _DEF_TOKENS for t in tokens):
        return "def"
    if tokens & _ATT_TOKENS or any(t in _ATT_TOKENS for t in tokens):
        return "att"
    if any(k in s for k in ("forward", "striker", "attacker", "winger")):
        return "att"
    if any(k in s for k in ("defender", "centreback", "fullback")):
        return "def"
    return None


def _classify_injuries(match, rows):
    flags = []
    detail = {"att": [], "def": []}
    idx = {}
    for row in rows or []:
        k = _norm(row.get("team"))
        if k:
            idx.setdefault(k, []).append(row)
    for side in ("dom", "ext"):
        team = (match or {}).get(side) or ""
        hits = _match_name(team, idx)
        if hits is None:
            continue
        for row in hits:
            bucket = _bucket(row.get("position"))
            label = row.get("player") or "?"
            if bucket == "att":
                detail["att"].append(label)
            elif bucket == "def":
                detail["def"].append(label)
    if detail["att"]:
        flags.append("buteur_manquant")
    if detail["def"]:
        flags.append("defenseur_manquant")
    return flags, detail


def _classify_motivation(match, rows):
    flags = []
    n = len(rows or [])
    if n < 8:
        return flags, {"reason": "standings_courtes"}
    idx = {}
    for rec in rows:
        k = _norm(rec.get("team"))
        if k:
            idx[k] = rec
    found = []
    for side in ("dom", "ext"):
        rec = _match_name((match or {}).get(side) or "", idx)
        if rec is None:
            return flags, {"reason": "equipe_absente_standings"}
        found.append(rec)
    ranks = []
    played = []
    for rec in found:
        try:
            ranks.append(int(rec.get("rank")))
        except (TypeError, ValueError):
            return flags, {"reason": "rank_trou"}
        try:
            played.append(int(rec.get("played") or 0))
        except (TypeError, ValueError):
            played.append(0)
    top = 6
    bottom = max(n - 2, top + 1)
    mid_lo, mid_hi = 8, max(n - 4, 9)
    both_top = all(r <= top for r in ranks)
    both_bottom = all(r >= bottom for r in ranks)
    if both_top or both_bottom:
        flags.append("double_motivation")
        return flags, {"ranks": ranks, "n": n}
    mid = all(mid_lo <= r <= mid_hi for r in ranks)
    late = all(p >= 30 for p in played)
    if mid and late:
        flags.append("satisfait_nul")
    return flags, {"ranks": ranks, "played": played, "n": n}


def flags_for(match, code=None):
    """Retourne {flags, holes, detail, source}. Jamais un P. Jamais un lambda."""
    if os.environ.get("PARI_SKIP_INJURIES") == "1":
        return _empty("PARI_SKIP_INJURIES")
    key = _key_or_none()
    if not key:
        return _empty("no_key")
    code = (code or (match or {}).get("league_code") or "").strip().upper()
    league_id = LEAGUES.get(code)
    if not league_id:
        return _empty("ligue_inconnue")
    day = ((match or {}).get("date") or "")[:10]
    if len(day) < 10:
        return _empty("date_absente")
    season = _season_for(day)
    if season is None:
        return _empty("saison_trou")

    holes = []
    flags = []
    detail = {}

    inj_rows, _ = cache.get_or_fetch(
        "api_football_injuries", f"{code}:{day}",
        lambda: _fetch_injuries(league_id, day, key))
    if inj_rows is None:
        holes.append("injuries")
        detail["injuries"] = {"reason": "fetch_ko"}
    else:
        inj_flags, inj_detail = _classify_injuries(match, inj_rows)
        flags.extend(inj_flags)
        detail["injuries"] = inj_detail

    stand_rows, _ = cache.get_or_fetch(
        "api_football_standings", f"{code}:{season}",
        lambda: _fetch_standings(league_id, season, key))
    if stand_rows is None:
        holes.append("standings")
        detail["standings"] = {"reason": "fetch_ko"}
    else:
        mot_flags, mot_detail = _classify_motivation(match, stand_rows)
        flags.extend(mot_flags)
        detail["standings"] = mot_detail

    seen = []
    for f in flags:
        if f in S15_FLAGS and f not in seen:
            seen.append(f)
    return {
        "flags": seen,
        "holes": holes,
        "detail": detail,
        "source": "api-football",
    }


def stamp_state(sf, s15):
    """Append flags/holes. NEVER touch lambdas or factors."""
    if not isinstance(sf, dict):
        return sf
    blob = s15 if isinstance(s15, dict) else {}
    flags = list(sf.get("flags") or [])
    holes = list(sf.get("holes") or [])
    for f in blob.get("flags") or []:
        if f in S15_FLAGS and f not in flags:
            flags.append(f)
    for h in blob.get("holes") or []:
        if h not in holes:
            holes.append(h)
    out = dict(sf)
    out["flags"] = flags
    out["holes"] = holes
    return out
