"""
F05 PACKAGER — PREVIEW 2 : LE TICKET FINAL (v2, Phase 5)
=========================================================
Rendu graphique du ticket final, hommage à PERTURABO (et, pour l'expérience,
à l'expérience LACRIMAE/F03_PREVIEW de l'opérateur). Chaque ticket = une carte ;
le sur-ticket (matchs au score le plus haut) est mis en avant ; le backroll
(budget alloué / reste) est affiché en tête. Responsive PC/téléphone.

Entrée : F05_PACKAGER/OUT/tickets.json (+ top3.json)
Sortie : SHARED/OUT/preview2.html
"""

import json
import argparse
import os
from datetime import datetime, timezone


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
:root{--steel:#14161b;--blue:#24507e;--gold:#d4a017;}
*{box-sizing:border-box;}
body{margin:0;background:var(--steel);color:#d7dae0;
     font-family:'Segoe UI',Roboto,system-ui,sans-serif;font-size:clamp(14px,2.6vw,16px);}
header{padding:20px 20px 12px;border-bottom:3px solid var(--gold);
       background:repeating-linear-gradient(45deg,#171a20 0 12px,#13161c 12px 24px);}
h1{margin:0 0 4px;color:var(--blue);font-family:'Saira Stencil One',Impact,sans-serif;
   letter-spacing:2px;font-size:clamp(24px,5.5vw,36px);}
h1 em{color:var(--gold);font-style:normal;}
.sub{color:#8b93a5;font-size:0.85em;margin:2px 0;}
main{padding:16px;max-width:820px;margin:0 auto;}
.budget{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0 22px;}
.budget .cell{flex:1 1 140px;background:#1a1f2b;border:1px solid #262c38;border-radius:12px;
              padding:12px 14px;text-align:center;}
.budget .big{color:var(--gold);font-weight:800;font-size:1.25em;}
.ticket{background:#181c24;border:1px solid #262c38;border-radius:14px;margin:16px 0;
        overflow:hidden;}
.ticket.sur{border-color:var(--gold);}
.ticket .head{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#1c2130;
              border-bottom:2px solid var(--gold);}
.ticket .rang{background:var(--blue);color:#fff;border-radius:10px;padding:2px 12px;
              font-weight:800;}
.ticket .cls{color:#8b93a5;font-size:0.85em;}
.ticket .mise{margin-left:auto;color:var(--gold);font-weight:800;}
.jambes{padding:10px 16px;}
.jambe{display:flex;align-items:center;gap:10px;padding:7px 0;
       border-bottom:1px dashed #232833;}
.jambe:last-child{border-bottom:0;}
.jambe .m{flex:1 1 180px;color:#e8eaf0;font-weight:600;}
.jambe .sel{color:#b9c1d2;}
.jambe .cote{color:var(--gold);font-weight:700;}
.sum{display:flex;gap:14px;flex-wrap:wrap;padding:10px 16px;background:#161a22;
     font-size:0.9em;color:#9aa1b2;}
.sum b{color:var(--gold);}
.warn{margin:14px 0;padding:10px 14px;background:#231a12;border-left:3px solid #b06000;
      color:#d8b98a;font-size:0.9em;border-radius:8px;}
footer{color:#6a7284;text-align:center;padding:24px 12px;font-size:0.85em;}
@media (max-width:640px){.jambe .sel{font-size:0.82em;}}
"""

HEAD = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PERTURABO · PARI — Preview 2 · Ticket final</title>
<link href="https://fonts.googleapis.com/css2?family=Saira+Stencil+One&display=swap" rel="stylesheet">
<style>"""


def build():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="F05 — Preview 2 ticket final")
    ap.add_argument("--tickets", default=os.path.join(here, "..", "OUT", "tickets.json"))
    ap.add_argument("--top3", default=os.path.join(here, "..", "..", "F03_FORGEWARD", "OUT", "top3.json"))
    ap.add_argument("--output", default=os.path.join(here, "..", "..", "SHARED", "OUT", "preview2.html"))
    args = ap.parse_args()

    def load(p):
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    tdata = load(args.tickets) or {"tickets": [], "budget": {}, "warnings": []}
    top3 = load(args.top3) or {"matchs": []}

    cards = []
    for t in tdata.get("tickets", []):
        jambes = []
        for j in t.get("jambes", []):
            jambes.append(
                f"<div class='jambe'><span class='m'>{esc(j['match'])}</span>"
                f"<span class='sel'>{esc(j.get('selection_label') or j.get('selection'))}"
                + (f" · p {j.get('p_modele')*100:.0f}%" if j.get("p_modele") else "")
                + f"</span><span class='cote'>@ {j.get('cote')}</span></div>")
        sur = t.get("classe") == "SUR_TICKET"
        units = f" ({t['mise_units']}u)" if t.get("mise_units") is not None else ""
        cards.append(
            f"<div class='ticket{' sur' if sur else ''}><div class='head'>"
            f"<span class='rang'>T{t['rang_ticket']}</span>"
            f"<span class='cls'>{esc(t.get('classe',''))}</span>"
            f"<span class='mise'>{t['mise_fc']:.0f} FC{units}</span></div>"
            f"<div class='jambes'>{''.join(jambes)}</div>"
            f"<div class='sum'><span>cote <b>{t['cote_totale']}</b></span>"
            f"<span>proba <b>{t['p_aggregee']*100:.0f}%</b></span>"
            f"<span>retour si gagné <b>{t['retour_si_gagne_fc']:.0f} FC</b></span></div></div>")

    if not cards:
        cards.append("<div class='warn'>Aucun ticket — aucun match éligible (buckets FAIBLE / NO BET) "
                     "ou budget non engagé.</div>")
    warns = "".join(f"<div class='warn'>⚠️ {esc(w)}</div>" for w in tdata.get("warnings", []))

    b = tdata.get("budget", {}) or {}
    t3m = top3.get("matchs", [])
    haute = sum(1 for r_ in t3m if r_.get("bucket") == "HAUTE")
    g_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = (HEAD + CSS + "</style></head><body>"
            "<header><h1>PERTURABO <em>· PARI</em></h1>"
            "<div class='sub'>PREVIEW 2 — TICKET FINAL (hommage à PERTURABO)</div>"
            f"<div class='sub'>généré {g_at} · {len(tdata.get('tickets', []))} tickets · "
            f"buckets HAUTE: {haute}</div></header>"
            "<main>"
            "<div class='budget'>"
            f"<div class='cell'><div class='sub'>Budget du jour</div><div class='big'>{b.get('budget_fc', 0):.0f} FC</div></div>"
            f"<div class='cell'><div class='sub'>Alloué aux tickets</div><div class='big'>{b.get('alloue_fc', 0):.0f} FC</div></div>"
            f"<div class='cell'><div class='sub'>Reste</div><div class='big'>{b.get('reste_fc', 0):.0f} FC</div></div>"
            "</div>"
            + "".join(cards) + warns
            + "<footer>🪙 Mise max 3% bankroll · pas de martingale · le ledger F06 prend TOUS les tickets "
              "(gagnants ET perdants).<br>« Fer au-dedans, Fer au-dehors. »</footer></main></body></html>")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[PREVIEW2] {len(tdata.get('tickets', []))} tickets — sortie : {args.output}")


if __name__ == "__main__":
    build()
