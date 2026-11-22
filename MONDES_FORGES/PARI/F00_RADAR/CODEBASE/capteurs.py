"""
F00 CAPTEURS — Le Fer qui Veille : orchestrateur des connecteurs (monde PARI)
=============================================================================
Bras opératoire des sources whitelist :
  - build-stats       : football-data.co.uk (SANS CLÉ) → stats Dom/Ext + split MT
  - build-elo         : ClubElo (SANS CLE) → carte Elo du jour (timeout = trou)
  - backtest-shares   : parts MT1 + pente Elo depuis CSV cache (offline)
  - fit-league        : rho / bonus domicile / part_mt1 → league_params.json (offline)
  - walk-forward      : Brier/RPS/ECE cut-off explicite → backtest_report.json (offline)
  - fixtures-list     : calendrier live (API-Football ou football-data.org, CLE)
  - inject            : peuple une carte de matchs (stats + Elo) depuis la bibliothèque
  - telegram-test     : vérifie le bot (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)

Usage:
  python capteurs.py build-stats --league E0 --season 2627 --last 12 \
      --out ../../ARCHIVUM/teams/E0_2627.json
  python capteurs.py inject --stats ../../ARCHIVUM/teams/E0_2627.json \
      --carte ../../ARCHIVUM/fixtures/matches.json [--elo ../../ARCHIVUM/teams/elo.json]
  python capteurs.py fixtures-list --source api-football --league-id 39 --date 2026-10-25
  python capteurs.py walk-forward --cutoff 2026-01-01 --csv-dir ../../ARCHIVUM/cache/f00
  python capteurs.py fit-league --csv-dir ../../ARCHIVUM/cache/f00
  python capteurs.py odds-watch [--force] [--notify] [--close]
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CONNECTORS = os.path.join(HERE, "..", "..", "F01_SENTINEL", "CODEBASE", "connectors")
sys.path.insert(0, CONNECTORS)

LIGUE_CODE = {
    "premier league": "E0",
    "epl": "E0",
    "la liga": "SP1",
    "laliga": "SP1",
    "liga santander": "SP1",
    "liga bbva": "SP1",
    "serie a": "I1",
    "seria a": "I1",
    "championship": "E1",
    "efl championship": "E1",
    "bundesliga 2": "D2",
    "2. bundesliga": "D2",
    "2 bundesliga": "D2",
    "zweite bundesliga": "D2",
    "bundesliga": "D1",
    "ligue 1": "F1",
    "ligue1": "F1",
    "eredivisie": "N1",
    "pays bas": "N1",
    "netherlands": "N1",
    "super lig": "T1",
    "superlig": "T1",
    "turquie": "T1",
    "turkey": "T1",
    "turkiye": "T1",
    "j1 league": "J1",
    "jleague": "J1",
    "japon": "J1",
    "japan": "J1",
}

LIGUE_REJECT = (
    "laliga 2", "la liga 2", "segunda",
    "serie b", "ligue 2", "ligue2", "premier league 2",
)

TEAM_ALIASES = {
    "athmadrid": "atleticomadrid",
    "atleticomadrid": "atleticomadrid",
    "atlmadrid": "atleticomadrid",
    "atleticomadridcf": "atleticomadrid",
    "mgladbach": "monchengladbach",
    "borussiamonchengladbach": "monchengladbach",
    "monchengladbach": "monchengladbach",
    "gladbach": "monchengladbach",
    "nottmforest": "nottinghamforest",
    "nottinghamforest": "nottinghamforest",
    "nottsforest": "nottinghamforest",
    "leverkusen": "bayerleverkusen",
    "bayerleverkusen": "bayerleverkusen",
    "bayer04leverkusen": "bayerleverkusen",
    "afcbournemouth": "bournemouth",
    "bournemouth": "bournemouth",
    "leedsunited": "leeds",
    "leeds": "leeds",
    "brentfordfc": "brentford",
    "brentford": "brentford",
    "sunderlandafc": "sunderland",
    "sunderland": "sunderland",
    "acmonza": "monza",
    "monza": "monza",
    "bolognafc": "bologna",
    "bolognasc": "bologna",
    "bologna": "bologna",
    "levanteud": "levante",
    "levante": "levante",
    "vfbstuttgart": "stuttgart",
    "stuttgart": "stuttgart",
    "tsghoffenheim": "hoffenheim",
    "hoffenheim": "hoffenheim",
    "fcaugsburg": "augsburg",
    "augsburg": "augsburg",
    "scfreiburg": "freiburg",
    "freiburg": "freiburg",
    "werderbremen": "werderbremen",
    "svwerderbremen": "werderbremen",
    "rbleipzig": "leipzig",
    "leipzig": "leipzig",
    "schalke04": "schalke",
    "fcschalke04": "schalke",
    "schalke": "schalke",
    "scpaderborn07": "paderborn",
    "paderborn07": "paderborn",
    "paderborn": "paderborn",
    "coventrycity": "coventry",
    "coventry": "coventry",
    "manunited": "manunited",
    "manchesterunited": "manunited",
    "mancity": "mancity",
    "manchestercity": "mancity",
    "spurs": "tottenham",
    "tottenham": "tottenham",
    "tottenhamhotspur": "tottenham",
    "wolves": "wolves",
    "wolverhampton": "wolves",
    "wolverhamptonwanderers": "wolves",
    "einfrankfurt": "eintrachtfrankfurt",
    "eintrachtfrankfurt": "eintrachtfrankfurt",
    "frankfurt": "eintrachtfrankfurt",
    "athbilbao": "athleticbilbao",
    "athleticbilbao": "athleticbilbao",
    "athleticclub": "athleticbilbao",
    "realbetis": "betis",
    "betis": "betis",
    "realsociedad": "sociedad",
    "sociedad": "sociedad",
    "espanyol": "espanol",
    "espanol": "espanol",
}

_STRIP_PREFIX = ("borussia", "bayer", "tsg", "vfb", "svw", "afc", "acf", "asroma", "rcd", "ud", "ac", "as", "sc", "fc", "cf", "rb")
_STRIP_SUFFIX = ("hotspur", "wanderers", "united", "city", "afc", "cfc", "ud", "fc", "cf", "ac", "sc", "04", "07")


def _alnum(name: str) -> str:
    raw = unicodedata.normalize("NFKD", name or "")
    raw = raw.encode("ascii", "ignore").decode("ascii")
    return "".join(c for c in raw.lower() if c.isalnum())


def ligue_code(name: str):
    lg = re.sub(r"\s+", " ", (name or "").lower().replace("-", " ").strip())
    compact = lg.replace(" ", "")
    for bad in LIGUE_REJECT:
        if bad.replace(" ", "") in compact or bad in lg:
            return None
    if "laliga" in compact:
        return "SP1"
    for key, code in sorted(LIGUE_CODE.items(), key=lambda kv: -len(kv[0])):
        if key in lg or key.replace(" ", "") in compact:
            return code
    return None


def team_key(name: str) -> str:
    n = _alnum(name)
    if not n:
        return ""
    if n in TEAM_ALIASES:
        return TEAM_ALIASES[n]
    changed = True
    while changed and len(n) >= 6:
        changed = False
        for p in _STRIP_PREFIX:
            if n.startswith(p) and len(n) - len(p) >= 4:
                n = n[len(p):]
                changed = True
                break
        if changed:
            continue
        for s in _STRIP_SUFFIX:
            if n.endswith(s) and len(n) - len(s) >= 4:
                n = n[:-len(s)]
                changed = True
                break
    return TEAM_ALIASES.get(n, n)


def _fuzzy_stats_lookup(stats: dict, name: str):
    n = team_key(name)
    if not n:
        return None, None
    best = None
    for key, val in stats.items():
        k = team_key(key)
        if not k:
            continue
        if k == n:
            return key, val
        if len(k) >= 5 and len(n) >= 5 and (n in k or k in n):
            diff = abs(len(k) - len(n))
            if best is None or diff < best[0]:
                best = (diff, key, val)
    return (best[1], best[2]) if best else (None, None)


def fuzzy_stats_lookup(stats: dict, name: str):
    return _fuzzy_stats_lookup(stats, name)


def cmd_build_stats(args):
    import football_data_uk
    extras = [s.strip() for s in (args.include_seasons or "").split(",") if s.strip()]
    data = football_data_uk.build_team_stats(args.league.upper(), args.season, last_n=args.last,
                                             extra_seasons=extras or None)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] ⚙️ {len(data['teams'])} équipes (tier: {data['tier']}, "
          f"{data['last_n_considered']} derniers matchs) → {args.out}")
    for name, t in list(data["teams"].items())[:5]:
        d = t.get("dom") or t.get("ext") or {}
        print(f"   {name:<22} mj {d.get('mj', 0)} marq {d.get('marques', 0):.0f} enc {d.get('encaisses', 0):.0f}")


def cmd_build_elo(args):
    import clubelo
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        data = clubelo.elo_map(date)
    except Exception as e:
        print(f"[CAPTEURS] ClubElo injoignable ({e}). Trou declare, pas de pente inventee.")
        data = None
    if not data or not (data.get("elos") or {}):
        data = clubelo._hole(date) if hasattr(clubelo, "_hole") else {
            "meta": {"generated_at": now_str(), "source": "api.clubelo.com",
                     "date": date, "nb_clubs": 0, "holes": ["elo"]},
            "elos": {},
            "holes": ["elo"],
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[CAPTEURS] ClubElo trou → {args.out}")
        return False
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] {data['meta']['nb_clubs']} clubs Elo du {data['meta']['date']} → {args.out}")
    return True


def cmd_walk_forward(args):
    import walkforward
    if args.csv:
        rec = walkforward.run_file(args.csv, args.cutoff, out=args.out)
        print(f"[CAPTEURS] walk-forward n_train={rec.get('n_train')} n_test={rec.get('n_test')} "
              f"holes={rec.get('holes')} → {args.out}")
    else:
        blob = walkforward.run_dir(args.csv_dir, args.cutoff, out=args.out)
        print(f"[CAPTEURS] walk-forward {len(blob.get('leagues') or {})} ligue(s) → {args.out}")
    return True


def cmd_fit_league(args):
    f02 = os.path.normpath(os.path.join(HERE, "..", "..", "F02_BREACHER", "CODEBASE"))
    if f02 not in sys.path:
        sys.path.insert(0, f02)
    import league_fit
    if args.csv:
        rec = league_fit.fit_file(args.csv)
        leagues = {}
        if rec and rec.get("league_code"):
            leagues[rec["league_code"]] = rec
        blob = league_fit.wrap_blob(leagues)
    else:
        blob = league_fit.fit_dir(args.csv_dir)
    league_fit.save_params(blob, args.out)
    print(f"[CAPTEURS] fit-league {len(blob.get('leagues') or {})} ligue(s) → {args.out}")
    return True


def cmd_backtest_shares(args):
    import backtest
    elo_map = backtest.load_elo(args.elo)
    shares = backtest.scan_dir(args.csv_dir, elo_map=elo_map)
    blob = {
        "generated_at": now_str(),
        "offline": True,
        "leagues": shares,
        "holes": backtest.holes_for(shares, elo_map),
    }
    for code, rec in shares.items():
        blob[code] = rec
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] backtest-shares {len(shares)} ligue(s) holes={blob['holes']} → {args.out}")
    return True


def cmd_fixtures_list(args):
    if args.source == "api-football":
        import api_football
        data = api_football.fixtures(args.date, args.league_id)
    else:
        import football_data_org
        data = football_data_org.fixtures(args.date_from or args.date, args.date_to or args.date,
                                          competition=args.competition)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] 🗓️ {len(data['fixtures'])} fixtures ({data['source']}) → {args.out}")
    for fx in data["fixtures"][:10]:
        print(f"   {fx['id']:<12} {fx['dom']} vs {fx['ext']}  [{fx.get('date')}]")


def cmd_inject(args):
    with open(args.carte, "r", encoding="utf-8") as f:
        carte = json.load(f)
    with open(args.stats, "r", encoding="utf-8") as f:
        blob = json.load(f)
    stats = blob.get("teams", {})
    stats_code = (blob.get("league_code") or "").upper()

    elos = {}
    if args.elo and os.path.exists(args.elo):
        with open(args.elo, "r", encoding="utf-8") as f:
            elos = json.load(f).get("elos", {})

    filled, manquants = 0, []
    for m in carte.get("matchs", []):
        lg = m.get("ligue") or carte.get("ligue") or ""
        code = ligue_code(lg)
        if stats_code and code and code != stats_code:
            continue
        if stats_code and not code:
            continue
        k_d, s_d = _fuzzy_stats_lookup(stats, m.get("dom", ""))
        k_e, s_e = _fuzzy_stats_lookup(stats, m.get("ext", ""))
        if m.get("stats") is None:
            m["stats"] = {}
        s_d_venue = (s_d or {}).get("dom")
        if s_d_venue and not m["stats"].get("dom"):
            m["stats"]["dom"] = {k: s_d_venue.get(k) for k in ("mj", "marques", "encaisses",
                                 "marques_mt1", "encaisses_mt1", "marques_mt2", "encaisses_mt2")}
            m["stats"]["dom"] = {k: v for k, v in m["stats"]["dom"].items() if v is not None}
            filled += 1
        elif not s_d_venue and not m["stats"].get("dom"):
            manquants.append(f"stats dom: {m.get('dom')}")
        s_e_venue = (s_e or {}).get("ext")
        if s_e_venue and not m["stats"].get("ext"):
            m["stats"]["ext"] = {k: s_e_venue.get(k) for k in ("mj", "marques", "encaisses",
                                 "marques_mt1", "encaisses_mt1", "marques_mt2", "encaisses_mt2")}
            m["stats"]["ext"] = {k: v for k, v in m["stats"]["ext"].items() if v is not None}
            filled += 1
        elif not s_e_venue and not m["stats"].get("ext"):
            manquants.append(f"stats ext: {m.get('ext')}")
        el = {}
        if elos:
            import clubelo as _cl
            for side, team in (("dom", m.get("dom")), ("ext", m.get("ext"))):
                hit = _cl.best_match(team, elos)
                if hit:
                    el[side] = hit[1]
        if el:
            m["elo"] = {**(m.get("elo") or {}), **el}

    carte.setdefault("warnings", []).append(
        f"inject CAPTEURS {now_str()} [{stats_code or '?'}]: {filled} auto / {len(manquants)} manquants")
    with open(args.carte, "w", encoding="utf-8") as f:
        json.dump(carte, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] inject: {filled} stats remplies, {len(elos)} clubs Elo dispo → {args.carte}")
    for miss in manquants:
        print(f"   SKIP {miss} — hors CSV ligue ou alias manquant (Zero Data, Zero Calc sur CE match)")


def cmd_enrich(args):
    """Gâchette /capture : Elo + xG + repos/H2H + vote notes 3 voix. Trou = 0."""
    import enrich
    if args.capture_parsed:
        parsed = json.load(open(args.capture_parsed, encoding="utf-8"))
        carte, notes = enrich.enrich_from_capture(parsed, notes_path=args.notes)
        if args.carte:
            enrich._dump(args.carte, carte)
    elif args.carte:
        carte, notes = enrich.enrich_paths(args.carte, notes_path=args.notes)
    else:
        print("[CAPTEURS] enrich: --carte ou --capture-parsed requis")
        return False
    n = (notes or {}).get("notes_count", 0)
    print(f"[CAPTEURS] enrich notes: {n} OUT — {(args.notes or enrich.NOTES_PATH)}")
    return True


def cmd_odds_watch(args):
    """Rescan T-2h / T-0 The Odds API. Cle absente = skip. Jamais dans Poisson."""
    import odds_watch
    force = bool(args.force) or os.environ.get("PARI_ODDS_FORCE") == "1"
    close = bool(getattr(args, "close", False))
    odds_watch.run(carte_path=args.carte, pred_path=args.predictions,
                   force=force, notify=args.notify, close=close)
    return True


def cmd_telegram_test(args):
    sys.path.insert(0, os.path.join(HERE, "..", "..", "ORCHESTRATOR", "CODEBASE"))
    import notifier
    ok = notifier.send("PING du monde PARI 🛡️ — les capteurs et le canal sont opérationnels.")
    sys.exit(0 if ok else 1)


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser(description="F00 CAPTEURS — connecteurs PARI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-stats")
    b.add_argument("--league", required=True, help="code football-data (E0, SP1, I1, D1, F1…)")
    b.add_argument("--season", required=True, help="2627 pour 2026-27")
    b.add_argument("--last", type=int, default=12)
    b.add_argument("--include-seasons", default=None,
                   help="saisons antérieures à fusionner, ex: 2526 (indispensable en début de saison)")
    b.add_argument("--out", required=True)

    e = sub.add_parser("build-elo")
    e.add_argument("--date", default=None, help="AAAA-MM-JJ (défaut: aujourd'hui)")
    e.add_argument("--out", required=True)

    fl = sub.add_parser("fixtures-list")
    fl.add_argument("--source", choices=["api-football", "football-data-org"], required=True)
    fl.add_argument("--league-id", type=int, default=None)
    fl.add_argument("--competition", default="PL")
    fl.add_argument("--date", default=None)
    fl.add_argument("--date-from", default=None)
    fl.add_argument("--date-to", default=None)
    fl.add_argument("--out", required=True)

    i = sub.add_parser("inject")
    i.add_argument("--stats", required=True)
    i.add_argument("--carte", required=True)
    i.add_argument("--elo", default=None)

    sub.add_parser("telegram-test")

    en = sub.add_parser("enrich")
    en.add_argument("--carte", default=None)
    en.add_argument("--capture-parsed", default=None)
    en.add_argument("--notes", default=None)

    ow = sub.add_parser("odds-watch")
    ow.add_argument("--carte", default=None)
    ow.add_argument("--predictions", default=None)
    ow.add_argument("--force", action="store_true")
    ow.add_argument("--notify", action="store_true")
    ow.add_argument("--close", action="store_true", help="snapshot T-0 kickoff")

    bs = sub.add_parser("backtest-shares")
    bs.add_argument("--csv-dir", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "cache", "f00"))
    bs.add_argument("--elo", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "teams", "elo.json"))
    bs.add_argument("--out", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "learnings", "shares.json"))

    flg = sub.add_parser("fit-league")
    flg.add_argument("--csv", default=None)
    flg.add_argument("--csv-dir", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "cache", "f00"))
    flg.add_argument("--out", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "learnings", "league_params.json"))

    wf = sub.add_parser("walk-forward")
    wf.add_argument("--csv", default=None)
    wf.add_argument("--csv-dir", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "cache", "f00"))
    wf.add_argument("--cutoff", required=True)
    wf.add_argument("--out", default=os.path.join(HERE, "..", "..", "ARCHIVUM", "learnings", "backtest_report.json"))

    args = parser.parse_args()
    {"build-stats": cmd_build_stats, "build-elo": cmd_build_elo,
     "fixtures-list": cmd_fixtures_list, "inject": cmd_inject,
     "enrich": cmd_enrich, "odds-watch": cmd_odds_watch,
      "telegram-test": cmd_telegram_test,
      "backtest-shares": cmd_backtest_shares,
      "fit-league": cmd_fit_league,
      "walk-forward": cmd_walk_forward}[args.cmd](args)


if __name__ == "__main__":
    main()
