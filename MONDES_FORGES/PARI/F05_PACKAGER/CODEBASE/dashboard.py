"""
F05 PACKAGER — Dashboard HTML (charte Iron Warriors 🟡⚫🔵)
============================================================
Génère SHARED/OUT/dashboard.html : statique, Chart.js CDN, responsive
(tel/PC), Mode Discret (police réduite + libellés neutres sauvegardés).

Onglets : RADAR · PACK · LEDGER · DOCTRINE
Usage:
  python dashboard.py --radar F00_RADAR/OUT/radar.json \
                      --pack F05_PACKAGER/OUT/pari_pack.json \
                      --tickets ../../ARCHIVUM/learnings/tickets.json \
                      --calibration ../../ARCHIVUM/learnings/calibration.json
"""

import json
import argparse
import os
from datetime import datetime, timezone

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIÈGE ANTIQUE</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root{
  --fond:#14161b; --panneau:#1d2026; --fer:#8a9099; --acier:#3a3f46;
  --bleu:#24507e; --bleu-clair:#3f7ac2; --or:#d4a017; --or-clair:#f5c400;
  --rouge:#c0392b; --vert:#2e8b57; --txt:#e8e6e3;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fond);color:var(--txt);
  font-family:'Roboto Condensed',system-ui,sans-serif;font-size:16px}
body.discret{font-size:12px}
header{padding:14px 18px;background:linear-gradient(180deg,#1d2026,#14161b);
  border-bottom:3px solid var(--bleu);position:relative}
header::after{content:"";position:absolute;inset:0 auto 0 0;width:100%;height:6px;
  bottom:-9px;background:repeating-linear-gradient(45deg,var(--or-clair) 0 10px,#111 10px 20px)}
h1{font-family:'Saira Stencil One',Impact,sans-serif;color:var(--or);
  letter-spacing:3px;margin:0;font-size:1.9rem;text-transform:uppercase}
h1 .camo{position:relative}
.tabs{display:flex;gap:4px;flex-wrap:wrap;padding:10px 14px}
.tabs button{flex:0 0 auto;background:var(--panneau);border:1px solid var(--acier);
  color:var(--fer);padding:8px 18px;cursor:pointer;font-weight:600;letter-spacing:1px}
.tabs button.on{color:var(--or-clair);border-color:var(--or);background:#20242b}
main{padding:14px 18px;max-width:1200px;margin:0 auto}
.panneau{background:var(--panneau);border:1px solid var(--acier);padding:14px;margin-bottom:16px;
  border-radius:4px}
.kpis{display:flex;gap:10px;flex-wrap:wrap}
.kpi{flex:1;min-width:130px;background:#23272e;border-left:4px solid var(--bleu);padding:10px}
.kpi b{color:var(--or-clair);font-size:1.3rem;display:block}
table{width:100%;border-collapse:collapse;font-size:.92em}
th{color:var(--or);text-align:left;border-bottom:2px solid var(--acier);padding:6px 8px}
td{padding:5px 8px;border-bottom:1px solid #2a2e35}
tr:hover td{background:#232830}
.badge{padding:1px 8px;border-radius:3px;font-weight:700}
.b-go{background:#123a24;color:#8f7;color:#7fd08f}
.b-thin{background:#3a3412;color:#e4c549}
.b-nogay{background:#3a1712;color:#e07a6a}
canvas{max-width:100%}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-left:auto}
.controls button{background:var(--panneau);border:1px solid var(--or);color:var(--or-clair);
  padding:6px 12px;cursor:pointer}
footer{color:var(--fer);font-size:.8em;padding:16px;text-align:center}
.note{color:var(--fer);font-size:.85em}
@media(max-width:700px){h1{font-size:1.2rem} .kpi{min-width:42%} table{font-size:.8em}}
</style>
</head>
<body>
<header>
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">      <h1><span id="titreChef" class="camo">🛡️ SIÈGE ANTIQUE — DIRECTION DES OPÉRATIONS</span></h1>
    <div class="controls">
      <button id="btnDiscret" onclick="toggleDiscret()">MODE DISCRET 🔕</button>
    </div>
  </div>
</header>
<div class="tabs">
  <button data-tab="radar" class="on" onclick="showTab('radar',this)">📡 RADAR</button>
  <button data-tab="pack" onclick="showTab('pack',this)">🏆 PARI PACK</button>
  <button data-tab="ledger" onclick="showTab('ledger',this)">📊 LEDGER</button>
  <button data-tab="doctrine" onclick="showTab('doctrine',this)">📜 DOCTRINE</button>
</div>
<main>
  <section id="tab-radar">
    <div class="panneau kpis" id="radarKpis"></div>
    <div class="panneau" id="rgSpanChart" style="max-width:920px"><canvas id="chRadar"></canvas></div>
    <div class="panneau"><h3 class="camo">🛡️ Classement de la ligue (Top N)</h3><div id="radarTable"></div></div>
  </section>
  <section id="tab-pack" hidden>
    <div class="panneau kpis" id="packKpis"></div>
    <div class="panneau"><div id="packTable"></div><div id="packCombines"></div>
      <p class="note" id="packDisclaimer"></p></div>
  </section>
  <section id="tab-ledger" hidden>
    <div class="panneau"><h3>📈 Bankroll</h3><canvas id="chBankroll" style="max-width:820px"></canvas></div>
    <div class="panneau"><h3>🎯 Calibration (proba prédite vs réalisation)</h3><canvas id="chCalib" style="max-width:820px"></canvas></div>
    <div class="panneau"><div id="ticketsTable"></div></div>
  </section>
  <section id="tab-doctrine" hidden>
    <div class="panneau">
      <h3>Les 3 couleurs du verdict</h3>
      <ul>
        <li><span class="badge b-go">VALUE</span> EV ≥ seuil → mise ¼ Kelly plafonnée.</li>
        <li><span class="badge b-thin">THIN</span> EV positive mais sous le seuil → possibilité de mise réduite ou SKIP.</li>
        <li><span class="badge b-nogay">NO BET</span> proba correcte mais cote vidée → interdiction formelle.</li>
      </ul>
      <h3>Les non-négociables</h3>
      <ul>
        <li>1u = 1% de bankroll ; mise max 5% (3% exotique) ; combinés : toutes jambes +EV, ¼ Kelly, max 1u, max 3 jambes.</li>
        <li>Loterie (10+ jambes) : budget séparé ≤ 2% de bankroll.</li>
        <li>Zero Data Zero Calc : donnée manquante déclarée, jamais estimée en silence.</li>
        <li>Le ledger prend TOUS les tickets (gagnants ET perdants) — biais de survie = hérésie.</li>
      </ul>
      <h3>Démarcation</h3>
      <p>L'opérateur humain place les paris. Le monde ne passe jamais d'ordre automatique.</p>
    </div>
  </section>
</main>
<footer>PERTURABO — Monde Forge PARI · Fer au-dedans, Fer au-dehors · <span id="genDate"></span></footer>

<script>
const DATA = __DATA__;
const fmtPct = x => (x==null? '—' : (100*x).toFixed(1)+'%');
const evBadge = ev => ev>=0.03? '<span class="badge b-go">VALUE</span>' : ev>0? '<span class="badge b-thin">THIN</span>' : '<span class="badge b-nogay">NO BET</span>';
document.getElementById('genDate').textContent = DATA.generated_at || '';

function showTab(name, btn){
  ['radar','pack','ledger','doctrine'].forEach(t=>document.getElementById('tab-'+t).hidden = t!==name);
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on', b===btn));
}
function kpi(v,l){return `<div class="kpi"><b>${v}</b>${l}</div>`}

/* RADAR */
const radar = DATA.radar||{};
const ar = radar.analyses||[];
if(ar.length){
  const top = radar.top_ids||[];
  document.getElementById('radarKpis').innerHTML =
    kpi(ar.length,'Matchs scannés')+kpi(top.length,'TOP')+kpi(fmtPct(ar.reduce((s,a)=>s+(a.probas["o2.5"]||0),0)/ar.length),'P(O2.5) moyen');
  const names=ar.slice(0,20).map(a=>a.id+' · '+a.match.split(' vs ')[0]);
  const c=document.getElementById('chRadar').getContext('2d');
  new Chart(c,{type:'bar',data:{labels:names,datasets:[
    {label:'P(O2.5)',data:ar.slice(0,20).map(a=>a.probas["o2.5"]*100),backgroundColor:'#24507e'},
    {label:'P(MT2>)',data:ar.slice(0,20).map(a=>a.probas.mt2_plus*100),backgroundColor:'#d4a017'}]},
    options:{responsive:true,plugins:{legend:{labels:{color:'#e8e6e3'}}},scales:{x:{ticks:{color:'#8a9099'},maxRotation:60},y:{ticks:{color:'#e8e6e3',callback:v=>v+'%'}}}}});
  document.getElementById('radarTable').innerHTML =
    '<table><tr><th>Rang</th><th>Match</th><th>λ</th><th>P(O2.5)</th><th>P(MT2>)</th><th>Score</th></tr>'+
    ar.map((a,i)=>{const lam=a.lambdas.dom_total+a.lambdas.ext_total;
      return `<tr><td>${i<top.length?'🔥':'  '}${i+1}</td><td>${a.match}</td><td>${lam.toFixed(2)}</td><td>${fmtPct(a.probas["o2.5"])}</td><td>${fmtPct(a.probas.mt2_plus)}</td><td>${a.radar_score}</td></tr>`;}).join('')+'</table>';
}
/* PACK */
const pack = DATA.pack||{};
if(pack.top_picks){
  document.getElementById('packKpis').innerHTML =
    kpi(pack.metriques.mise_totale_units+'u','Mise totale')+kpi(fmtPct(pack.metriques.ev_moyenne_pct),'EV moyenne')+kpi(pack.metriques.nb_no_bet,'NO BET');
  document.getElementById('packTable').innerHTML =
    '<table><tr><th>#</th><th>Match</th><th>Sélection</th><th>Cote</th><th>EV</th><th>Mise</th></tr>'+
    pack.top_picks.map(x=>`<tr><td>${x.rang}</td><td>${x.match}</td><td>${x.selection_label}</td><td>${x.cote}</td><td>${fmtPct(x.ev)} ${evBadge(x.ev)}</td><td>${x.mise_units}u</td></tr>`).join('')+'</table>';
  document.getElementById('packCombines').innerHTML =
    (pack.combines||[]).map(c=>`<p>🧩 Combiné ${c.jambes.length} jambes — cote <b>${c.cote_totale}</b> — EV <b>${fmtPct(c.ev_combine)}</b> — mise ${c.mise_units}u</p>`).join('')
    + (pack.no_bet||[]).map(x=>`<p class="note">⛔ NO BET · ${x.match} — ${x.raison}</p>`).join('');
  document.getElementById('packDisclaimer').textContent = pack.disclaimer||'';
}
/* LEDGER */
const tickets=(DATA.tickets&&DATA.tickets.tickets)||[];
if(tickets.length){
  let cum=0; const labels=[],vals=[];
  tickets.forEach(t=>{cum+=t.pnl_units||0;labels.push(t.id);vals.push(+cum.toFixed(2))});
  new Chart(document.getElementById('chBankroll'),{type:'line',data:{labels:labels,
    datasets:[{label:'PnL cumulé (unités)',data:vals,borderColor:'#d4a017',backgroundColor:'rgba(212,160,23,.15)',fill:true}]},
    options:{plugins:{legend:{labels:{color:'#e8e6e3'}}},scales:{x:{ticks:{color:'#8a9099'}},y:{ticks:{color:'#e8e6e3'}}}}});
  document.getElementById('ticketsTable').innerHTML =
    '<h3>🎫 Tickets (TOUS — gagnants et perdants)</h3><table><tr><th>ID</th><th>Date</th><th>Jambes</th><th>Cote</th><th>Mise</th><th>Résultat</th><th>PnL</th></tr>'+
    tickets.map(t=>`<tr><td>${t.id}</td><td>${t.date||'—'}</td><td>${t.nb_jambes||'—'}</td><td>${t.cote_totale||'—'}</td><td>${t.mise_units||'—'}u</td><td class="${t.resultat==='gagné'?'b-go':'b-nogay'}">${t.resultat||'—'}</td><td>${t.pnl_units!=null?'+':''}${t.pnl_units!=null?t.pnl_units:'—'}</td></tr>`).join('')+'</table>';
}
/* CALIBRATION */
const recs=(DATA.calib&&DATA.calib.records)||[];
if(recs.length){
  const byBucket={};
  recs.forEach(r=>{const b=Math.floor(r.p*10)/10; (byBucket[b]=byBucket[b]||{p:0,n:0,ok:0,r:0});
    byBucket[b].p+=r.p; byBucket[b].n++; if(r.gagne) byBucket[b].ok++;});
  const pts=Object.entries(byBucket).map(([b,v])=>({x:v.p/v.n*100,y:v.ok/v.n*100,r:v.n}));
  new Chart(document.getElementById('chCalib'),{type:'scatter',data:{datasets:[{data:pts,pointBackgroundColor:'#3f7ac2',pointRadius:ctx=>2+ctx.raw.r}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`prédit ${c.raw.x.toFixed(0)}% → réalisé ${c.raw.y.toFixed(0)}% (n=${c.raw.r})`}}},
    scales:{x:{title:{display:true,text:'Proba prédite %'},min:0,max:100,ticks:{color:'#8a9099'}},y:{title:{display:true,text:'Réalisation %'},min:0,max:100,ticks:{color:'#e8e6e3'}}},
    plugins2:null}});
  const diag={type:'line',data:{datasets:[{data:[{x:0,y:0},{x:100,y:100}],borderColor:'#3a3f46',pointRadius:0}]}};
  console.log('calibration', pts.length,'points');
}
/* MODE DISCRET */
function toggleDiscret(){
  document.body.classList.toggle('discret');
  const on = document.body.classList.contains('discret');
  const t = document.getElementById('titreChef');
  if (t) t.textContent = on ? '📄 ANALYSE DE MATCHS · DOSSIER INTERNE' : '🛡️ SIÈGE ANTIQUE — DIRECTION DES OPÉRATIONS';
  try{localStorage.setItem('pari_discret', on? '1':'')}catch(e){}
  const b=document.getElementById('btnDiscret'); if(b) b.textContent = on? 'MODE DISCRET ✅' : 'MODE DISCRET 🔕';
}
try{ if(localStorage.getItem('pari_discret')) document.body.classList.add('discret'); }catch(e){}
(function initDiscret(){
  const on = document.body.classList.contains('discret');
  const t = document.getElementById('titreChef');
  if (t && on) t.textContent = '📄 ANALYSE DE MATCHS · DOSSIER INTERNE';
  const b=document.getElementById('btnDiscret'); if(b) b.textContent = on? 'MODE DISCRET ✅' : 'MODE DISCRET 🔕';
})
</script>
</body>
</html>
"""


def collect_inputs(args):
    d = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    def load(path):
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    d["radar"] = load(args.radar)
    d["pack"] = load(args.pack)
    d["tickets"] = load(args.tickets)
    d["calib"] = load(args.calibration)
    return d


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Dashboard PARI — charte Iron Warriors")
    parser.add_argument("--radar", default=os.path.join(here, "..", "..", "F00_RADAR", "OUT", "radar.json"))
    parser.add_argument("--pack", default=os.path.join(here, "..", "OUT", "pari_pack.json"))
    parser.add_argument("--tickets", default=os.path.join(here, "..", "..", "ARCHIVUM", "learnings", "tickets.json"))
    parser.add_argument("--calibration", default=os.path.join(here, "..", "..", "ARCHIVUM", "learnings", "calibration.json"))
    parser.add_argument("--output", default=os.path.join(here, "..", "..", "SHARED", "OUT", "dashboard.html"))
    args = parser.parse_args()

    data = collect_inputs(args)
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(args.output) / 1024
    print(f"[PACKAGER] 🖥️ Dashboard généré: {args.output} ({size:.0f} Ko)")
    print("[PACKAGER]   - charte: fond acier #14161b, bleu Perturabo #24507e, or #d4a017, hazard stripes")
    print("[PACKAGER]   - mode discret: bouton 🔕 (police réduite + titres camouflés, sauvegardé)")


if __name__ == "__main__":
    main()
