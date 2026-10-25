"""
F00 CAPTEURS — Le Fer qui Veille : orchestrateur des connecteurs (monde PARI)
=============================================================================
Bras opératoire des sources whitelist :
  - build-stats       : football-data.co.uk (SANS CLÉ) → stats Dom/Ext + split MT
  - build-elo         : ClubElo (SANS CLÉ) → carte Elo du jour
  - fixtures-list     : calendrier live (API-Football ou football-data.org, CLÉ)
  - inject            : peuple une carte de matchs (stats + Elo) depuis la bibliothèque
  - telegram-test     : vérifie le bot (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)

Usage:
  python capteurs.py build-stats --league E0 --season 2627 --last 12 \
      --out ../../ARCHIVUM/teams/E0_2627.json
  python capteurs.py inject --stats ../../ARCHIVUM/teams/E0_2627.json \
      --carte ../../ARCHIVUM/fixtures/matches.json [--elo ../../ARCHIVUM/teams/elo.json]
  python capteurs.py fixtures-list --source api-football --league-id 39 --date 2026-10-25
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CONNECTORS = os.path.join(HERE, "..", "..", "F01_SENTINEL", "CODEBASE", "connectors")
sys.path.insert(0, CONNECTORS)

def _fuzzy_stats_lookup(stats: dict, name: str):
    n = "".join(c for c in name.lower() if c.isalnum())
    best = None
    for key, val in stats.items():
        k = "".join(c for c in key.lower() if c.isalnum())
        if k == n:
            return key, val
        if len(k) >= 4 and (n in k or k in n):
            diff = abs(len(k) - len(n))
            if best is None or diff < best[0]:
                best = (diff, key, val)
    return (best[1], best[2]) if best else (None, None)


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
    try:
        data = clubelo.elo_map(args.date)
    except Exception as e:
        print(f"[CAPTEURS] ⚠️ ClubElo injoignable depuis cet environnement ({e}).")
        print("   → le connecteur tournera depuis GitHub Actions (réseau ouvert) ;")
        print("   → en attendant, le monde tourne sans Elo (data_quality 'moyenne').")
        return False
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] 📐 {data['meta']['nb_clubs']} clubs Elo du {data['meta']['date']} → {args.out}")
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
        stats = json.load(f).get("teams", {})

    elos = {}
    if args.elo and os.path.exists(args.elo):
        with open(args.elo, "r", encoding="utf-8") as f:
            elos = json.load(f).get("elos", {})

    filled, manquants = 0, []
    for m in carte.get("matchs", []):
        k_d, s_d = _fuzzy_stats_lookup(stats, m.get("dom", ""))
        k_e, s_e = _fuzzy_stats_lookup(stats, m.get("ext", ""))
        if m.get("stats") is None:
            m["stats"] = {}
        s_d_venue = (s_d or {}).get("dom")
        if s_d_venue:
            m["stats"]["dom"] = {k: s_d_venue.get(k) for k in ("mj", "marques", "encaisses",
                                 "marques_mt1", "encaisses_mt1", "marques_mt2", "encaisses_mt2")}
            m["stats"]["dom"] = {k: v for k, v in m["stats"]["dom"].items() if v is not None}
            filled += 1
        else:
            manquants.append(f"stats dom: {m.get('dom')}")
        s_e_venue = (s_e or {}).get("ext")
        if s_e_venue:
            m["stats"]["ext"] = {k: s_e_venue.get(k) for k in ("mj", "marques", "encaisses",
                                 "marques_mt1", "encaisses_mt1", "marques_mt2", "encaisses_mt2")}
            m["stats"]["ext"] = {k: v for k, v in m["stats"]["ext"].items() if v is not None}
            filled += 1
        else:
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
        f"inject CAPTEURS {now_str()}: {filled} auto / {len(manquants)} manquants")
    with open(args.carte, "w", encoding="utf-8") as f:
        json.dump(carte, f, indent=2, ensure_ascii=False)
    print(f"[CAPTEURS] 💉 inject: {filled} stats remplies, {len(elos)} clubs Elo dispo → {args.carte}")
    for miss in manquants:
        print(f"   ⚠️ {miss} — corrigé à la main ou renomme l'équipe (Zero Data, Zero Calc)")


def cmd_telegram_test(args):
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

    args = parser.parse_args()
    {"build-stats": cmd_build_stats, "build-elo": cmd_build_elo,
     "fixtures-list": cmd_fixtures_list, "inject": cmd_inject,
     "telegram-test": cmd_telegram_test}[args.cmd](args)


if __name__ == "__main__":
    main()
