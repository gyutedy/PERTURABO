"""
CONNECTEUR football-data.org (clé FOOTBALL_DATA_ORG_KEY, plan gratuit) — calendrier
====================================================================================
https://api.football-data.org/v4 — 12 compétitions, 10 calls/min, €0.
Donne les fixtures (paires + horaires + goal events si dispo / plan).

Usage (via capteurs.py):
  python capteurs.py fixtures-list --source football-data-org --competition PL \\
         --date-from 2026-10-24 --date-to 2026-10-27

Codes compétition : PL, PD (La Liga), SA, BL1, FL1.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.football-data.org/v4"
_WORLD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


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


def _key():
    key = os.environ.get("FOOTBALL_DATA_ORG_KEY")
    if not key:
        raise SystemExit("[FOOTBALL-DATA.ORG] Clé absente — ajoute FOOTBALL_DATA_ORG_KEY "
                         "(Settings → Keys, puis GitHub Secrets). Plan gratuit : 12 compétitions.")
    return key


def _key_or_none():
    return os.environ.get("FOOTBALL_DATA_ORG_KEY") or None


def _get(path, timeout=8):
    key = _key_or_none()
    if not key:
        return None
    url = f"{BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"X-Auth-Token": key, "User-Agent": "PERTURABO-PARI/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            left = r.headers.get("X-Requests-Available-Minute")
            reset = r.headers.get("X-RequestCounter-Reset")
            if left is not None:
                print(f"[FOOTBALL-DATA.ORG] quota minute restant={left} reset={reset}s")
            return json.loads(r.read().decode())
    except Exception:
        return None


def _norm(name):
    return "".join(c for c in (name or "").lower() if c.isalnum())


COMP_BY_CODE = {"E0": "PL", "SP1": "PD", "I1": "SA", "D1": "BL1", "F1": "FL1", "N1": "DED"}


def rest_days_and_h2h(dom, ext, date, competition=None, timeout=8):
    """Jours de repos (dernier match FINISHED) + H2H par NOM. Clé absente = None."""
    if not _key_or_none() or not date:
        return None
    day = str(date)[:10]
    try:
        d0 = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    from datetime import timedelta
    start = (d0 - timedelta(days=21)).strftime("%Y-%m-%d")
    end = (d0 - timedelta(days=1)).strftime("%Y-%m-%d")
    q = f"/matches?dateFrom={start}&dateTo={end}"
    if competition:
        q += f"&competitions={competition}"
    data = _get(q, timeout=timeout)
    if not data:
        return None
    nd, ne = _norm(dom), _norm(ext)
    last_d = last_e = None
    h2h = {"played": 0, "dom_wins": 0, "draws": 0, "ext_wins": 0,
           "source": "football-data.org", "matches": []}
    for m in data.get("matches") or []:
        ht_name = (m.get("homeTeam") or {}).get("name") or ""
        at_name = (m.get("awayTeam") or {}).get("name") or ""
        ht = _norm(ht_name)
        at = _norm(at_name)
        utc = (m.get("utcDate") or "")[:10]
        if not utc:
            continue
        if ht == nd or at == nd:
            if last_d is None or utc > last_d:
                last_d = utc
        if ht == ne or at == ne:
            if last_e is None or utc > last_e:
                last_e = utc
        pair = {ht, at} == {nd, ne} and nd and ne
        if pair and (m.get("status") or "") in ("FINISHED", "AWARDED"):
            sc = (m.get("score") or {}).get("fullTime") or {}
            ht_sc = (m.get("score") or {}).get("halfTime") or {}
            hg, ag = sc.get("home"), sc.get("away")
            if hg is None or ag is None:
                continue
            h2h["played"] += 1
            if hg == ag:
                h2h["draws"] += 1
            elif (hg > ag and ht == nd) or (ag > hg and at == nd):
                h2h["dom_wins"] += 1
            else:
                h2h["ext_wins"] += 1
            hh, ha = ht_sc.get("home"), ht_sc.get("away")
            h2h["matches"].append({
                "date": utc,
                "home": ht_name,
                "away": at_name,
                "ft": f"{int(hg)}-{int(ag)}",
                "ht": f"{int(hh)}-{int(ha)}" if hh is not None and ha is not None else None,
            })

    def _rest(last):
        if not last:
            return None
        try:
            return max(0, (d0 - datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days)
        except ValueError:
            return None

    return {
        "rest_days": {"dom": _rest(last_d), "ext": _rest(last_e), "source": "football-data.org"},
        "h2h": h2h if h2h["played"] else None,
    }


def fixtures(date_from: str, date_to: str, competition: str = "PL", timeout: int = 60) -> dict:
    url = f"{BASE}/matches?dateFrom={date_from}&dateTo={date_to}&competitions={competition}"
    req = urllib.request.Request(
        url,
        headers={"X-Auth-Token": _key(), "User-Agent": "PERTURABO-PARI/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    out = []
    for m in data.get("matches", []) or []:
        out.append({
            "id": f"FDO{m.get('id')}",
            "dom": (m.get("homeTeam") or {}).get("name"),
            "ext": (m.get("awayTeam") or {}).get("name"),
            "date": m.get("utcDate"),
            "ligue": (m.get("competition") or {}).get("name"),
            "round": (m.get("matchday") and f"J{m['matchday']}") or (m.get("stage") or ""),
        })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "football-data.org",
        "competition": competition,
        "date_from": date_from,
        "date_to": date_to,
        "fixtures": out,
    }
