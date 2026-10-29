"""
F05 PACKAGER — PREVIEW 1 : DONNÉES BRUTES (v2, Phase 3)
=======================================================
Première preview de la campagne (charte PERTURABO / Iron Warriors).
Contenu : TOUTES les données brutes, math binaire ET info non binaire :
  - cotes reconstituées + marchés disponibles
  - probas froides du modèle (1X2, O/U, mi-temps, BTTS)
  - EV / seuil / verdict par marché
  - Top 3 marchés + score commun 01-10 + bucket
  - notes qualitatives (blessures, fatigue, enjeux…) et leurs effets BORNÉS
  - qualité data (haute/moyenne/basse) → verdict d'âge de la donnée
Menu déroulant par match (mobile-friendly, économe en espace).

Entrées : top3.json, predictions(.json|_filtered), analysis.json, carte fixtures,
          qualitative_verdict.json (optionnel)
Sortie  : SHARED/OUT/preview1.html
"""

import json
import argparse
import os
from datetime import datetime, timezone

STEEL = "#14161b"
BLUE = "#24507e"
GOLD = "#d4a017"


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bucket_badge(bucket):
    color = {"HAUTE": "#2e7d32", "MOYENNE": GOLD, "FAIBLE": "#b06000"}.get(bucket, "#888")
    return f'<span class="badge" style="background:{color}">{esc(bucket)}</span>'


def build_match_row(r_, match_info, pred, qualv):
    """Un bloc <details> par match : tout le brut, déroulant pour l'économie d'écran."""
    mid, match = r_["id"], r_["match"]
    date = (match_info or {}).get("date") or "—"
    heure = (match_info or {}).get("heure") or "—"
    ligue = (match_info or {}).get("ligue") or "—"
    marched = sorted((match_info or {}).get("marches_disponibles") or [])
    norb = (qualv or {}).get("verdicts", [])
    vq = next((v for v in norb if v.get("match_id") == mid), None)

    # ---- cotes et marchés --------------------------------------------------
    cotes_rows = []
    for k, v in sorted(((match_info or {}).get("cotes") or {}).items(), key=lambda x: x[0]):
        cotes_rows.append(f"<tr><td class='mk'>{esc(k)}</td><td class='odds'>{v}</td></tr>")

    # ---- probas froides du modèle -----------------------------------------
    proba = PROBAS_BY_ID.get(mid)
    if proba:
        keys_order = ["1", "X", "2", "o2.5", "u2.5", "btts", "mt1_plus", "mte", "mt2_plus"]
        proba_rows = []
        for k in keys_order:
            if k in proba:
                label = {"1": "1", "X": "Nul", "2": "2", "o2.5": "Over 2.5", "u2.5": "Under 2.5",
                         "btts": "BTTS", "mt1_plus": "MT1 > MT2", "mte": "MT Égalité",
                         "mt2_plus": "MT2 > MT1"}.get(k, k)
                proba_rows.append("<tr><td class='mk'>%s</td><td class='num'>%.1f%%</td></tr>"
                                  % (esc(label), 100 * proba[k]))

    # ---- EV / verdict par marché -------------------------------------------
    sel = pred.get("selections") if pred else []
    ev_rows = []
    for s in sel:
        verdict = s.get("verdict") or "?"
        cls = "v_value" if verdict == "VALUE" else "v_nobet"
        mise = s.get("mise_units")
        sq = (s.get("notes_qualitatives") or {})
        raisons = sq.get("raisons") or []
        raison = " · ".join(esc(r_) for r_ in raisons)
        ev_rows.append(
            f"<tr><td>{esc(s.get('selection_label') or s.get('selection'))}</td>"
            f"<td class='num'>{s.get('cote')}</td>"
            f"<td class='num'>{(s.get('p_modele') or 0)*100:.1f}%</td>"
            f"<td class='num'>{(s.get('ev') or 0)*100:+.1f}%</td>"
            f"<td><span class='{cls}'>{verdict}</span></td>"
            f"<td class='num'>{mise if mise is not None else '—'}</td>"
            f"<td class='raison'>{raison}</td></tr>")

    # ---- notes qualitatives -------------------------------------------------
    nq = vq or {}
    themes = nq.get("themes") or {}
    theme_html = "<p class='gone'>— aucune note qualitatif pour ce match —</p>"
    if themes:
        rows = "".join(
            f"<span class='theme'><b>{esc(t)}</b> — impact {esc(i.get('impact'))}"
            + (f" · {esc(i.get('detail'))}" if i.get("detail") else "")
            + "</span> " for t, i in sorted(themes.items()))
        theme_html = f"<p>{rows}</p>"
        if nq.get("marches_exclus"):
            theme_html += "<p>Marchés exclus : <b>" + esc(", ".join(nq["marches_exclus"])) + "</b></p>"
        if nq.get("bonus_seuil_ev"):
            theme_html += f"<p>Seuil EV exigé : <b>+{100*nq['bonus_seuil_ev']:.0f} pts</b></p>"
        if nq.get("no_bet_recommande"):
            theme_html += "<p class='danger'>🔴 NO BET RECOMMANDÉ (impact non-binaire)</p>"

    top3_html = ""
    for s in r_.get("top3", []):
        top3_html += (f"<div class='top3-item'><b>{s['rang']}.</b> {esc(s.get('selection_label'))} "
                      f"<span class='cote'>cote {s.get('cote')}</span> "
                      f"<span class='ev'>EV {(s.get('ev') or 0)*100:+.1f}%</span>"
                      + (f" <span class='pp'>proba {s.get('p_modele')*100:.0f}%</span>" if s.get("p_modele") else "")
                      + "</div>")
    if not top3_html:
        top3_html = "<p class='gone'>— aucun marché éligible —</p>"

    score = r_.get("score_commun")
    dq = r_.get("quality_data", "basse")
    dq_badge = {"haute": "#2e7d32", "moyenne": GOLD, "basse": "#b06000"}.get(dq, "#888")

    return f"""
<details class="match" {"open" if (r_.get("bucket") == "HAUTE") else ""}>
  <summary>
    <span class="m-id">{esc(mid)}</span>
    <span class="m-name">{esc(match)}</span>
    <span class="m-time">{esc(date)} · {esc(heure)}</span>
    {bucket_badge(r_.get("bucket", "FAIBLE"))}
    <span class="score">score <b>{score}/10</b></span>
    {"<span class='badge moteur'>NO BET</span>" if r_.get("no_bet_recommande") else ""}
  </summary>
  <div class="body">
    <div class="cols">
      <div class="col">
        <h4>Cotes reconstituées</h4>
        <p class="sub">ligue : {esc(ligue)} · marchés affichés : {esc(", ".join(marched)) or "—"}</p>
        <table>{''.join(cotes_rows) or "<tr><td>—</td></tr>"}</table>
        <h4>Probas du modèle (froides)</h4>
        <table>{''.join(proba_rows) if proba else "<tr><td>Zero Data, Zero Calc</td></tr>"}</table>
      </div>
      <div class="col">
        <h4>🏆 Top 3 marchés</h4>
        {top3_html}
        <h4>Qualité data</h4>
        <p><span class="badge" style="background:{dq_badge}">{esc(dq.upper())}</span>
           <span class="sub">→ verdict d'âge : {esc({'haute':'utilisable','moyenne':'flag estimate','basse':'verdict TYRANT exigé'}.get(dq, dq))}</span></p>
        <h4>± Infos non binaires (blessures, fatigue, enjeux…)</h4>
        {theme_html}
      </div>
    </div>
    <h4>EV par marché (post filtre qualitatif)</h4>
    <table class="ev-table">
      <tr><th>Marché</th><th>Cote</th><th>P(modelle)</th><th>EV</th><th>Verdict</th><th>Mise (u)</th><th>Raisons</th></tr>
      {''.join(ev_rows) or "<tr><td colspan='7'>—</td></tr>"}
    </table>
  </div>
</details>"""


CSS = f"""
:root {{ --steel:{STEEL}; --blue:{BLUE}; --gold:{GOLD}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--steel); color:#d7dae0;
        font-family:'Segoe UI',Roboto,system-ui,sans-serif; font-size:clamp(14px,2.5vw,16px); }}
header {{ padding:18px 20px 10px; border-bottom:3px solid var(--gold);
          background:repeating-linear-gradient(45deg, #171a20 0 12px, #13161c 12px 24px); }}
h1 {{ margin:0 0 4px; color:var(--blue); font-family:'Saira Stencil One',Impact,sans-serif;
      letter-spacing:2px; font-size:clamp(22px,5vw,34px); }}
h1 em {{ color:var(--gold); font-style:normal; }}
.sub {{ color:#8b93a5; font-size:0.85em; margin:2px 0; }}
main {{ padding:14px 16px 40px; max-width:980px; margin:0 auto; }}
details.match {{ border:1px solid #262c38; border-radius:10px; margin:10px 0; background:#181c24; overflow:hidden; }}
details.match summary {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px;
        padding:12px 14px; cursor:pointer; background:#1c2130; font-size:1.02em; }}
details.match[open] summary {{ border-bottom:1px solid #262c38; }}
.m-id {{ color:#8b93a5; font-size:0.85em; }}
.m-name {{ flex:1 1 200px; font-weight:600; color:#e8eaf0; }}
.m-time {{ color:#8b93a5; font-size:0.85em; }}
.score b {{ color:var(--gold); }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:12px; color:#fff; font-size:0.8em; font-weight:700; }}
.moteur {{ background:#b71c1c; }}
.body {{ padding:12px 14px; }}
.cols {{ display:flex; gap:16px; flex-wrap:wrap; }}
.col {{ flex:1 1 300px; min-width:260px; }}
h4 {{ color:var(--gold); border-bottom:1px solid #262c38; padding-bottom:4px; margin:14px 0 6px;
      font-size:0.95em; letter-spacing:1px; }}
table {{ width:100%; border-collapse:collapse; font-size:0.92em; }}
td, th {{ padding:4px 8px; border-bottom:1px solid #232833; text-align:left; }}
th {{ color:#8b93a5; font-weight:600; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.mk {{ color:var(--gold); font-weight:600; }}
.odds {{ text-align:right; font-variant-numeric:tabular-nums; color:#e8eaf0; }}
.v_value {{ color:#4caf50; font-weight:700; }}
.v_nobet {{ color:#9aa1b2; }}
.top3-item {{ padding:4px 0; border-bottom:1px dashed #262c38; }}
.cote {{ color:#e8eaf0; }} .ev {{ color:#4caf50; }} .pp {{ color:#8b93a5; font-size:0.85em; }}
.theme {{ display:inline-block; margin:2px 6px 2px 0; padding:2px 8px; background:#232833;
          border-radius:8px; font-size:0.88em; }}
.danger {{ color:#ef5350; font-weight:700; }}
.gone {{ color:#6a7284; font-style:italic; }}
.raison {{ color:#b06000; font-size:0.85em; }}
footer {{ color:#6a7284; text-align:center; padding:20px 12px; font-size:0.85em; }}
@media (max-width:640px) {{ .cols {{ flex-direction:column; }} }}
"""

HEAD = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PERTURABO · PARI — Preview 1 · Données brutes</title>
<link href="https://fonts.googleapis.com/css2?family=Saira+Stencil+One&display=swap" rel="stylesheet">
<style>"""


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    arg = argparse.ArgumentParser(description="F05 — Preview 1 données brutes")
    arg.add_argument("--top3", default=os.path.join(here, "..", "..", "F03_FORGEWARD", "OUT", "top3.json"))
    arg.add_argument("--predictions", default=os.path.join(here, "..", "..", "F03_FORGEWARD", "OUT", "predictions_filtered.json"))
    arg.add_argument("--analysis", default=os.path.join(here, "..", "..", "F02_BREACHER", "OUT", "analysis.json"))
    arg.add_argument("--carte", default=os.path.join(here, "..", "..", "ARCHIVUM", "fixtures", "matches.json"))
    arg.add_argument("--qualitative", default=os.path.join(here, "..", "..", "TYRANT", "OUT", "qualitative_verdict.json"))
    arg.add_argument("--output", default=os.path.join(here, "..", "..", "SHARED", "OUT", "preview1.html"))
    args = arg.parse_args()

    def load(p):
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    top3 = load(args.top3) or {"matchs": []}
    predict = load(args.predictions) or load(args.predictions.replace("_filtered.json", ".json")) or {"predictions": []}
    qualitative = load(args.qualitative)
    carte = load(args.carte) or {}

    global PROBAS_BY_ID
    ProbasBy = {}
    analysis = load(args.analysis) or {"analyses": []}
    for a in analysis.get("analyses", []):
        ProbasBy[a["id"]] = a.get("probas")
    PROBAS_BY_ID = ProbasBy

    matches_info = {m["id"]: m for m in carte.get("matchs", [])}
    preds_by_id = {p["id"]: p for p in predict.get("predictions", [])}

    rows = []
    for r_ in top3["matchs"]:
        rows.append(build_match_row(r_, matches_info.get(r_["id"], {}), preds_by_id.get(r_["id"]), qualitative))

    nb_haute = sum(1 for r_ in top3["matchs"] if r_.get("bucket") == "HAUTE")
    nb_norb = sum(1 for r_ in top3["matchs"] if r_.get("no_bet_recommande"))
    g_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ligue = esc(carte.get("ligue") or "—")
    horizon = esc(carte.get("horizon") or "—")

    html = (HEAD + CSS + "</style></head><body>"
            "<header><h1>PERTURABO <em>· PARI</em></h1>"
            f"<div class='sub'>PREVIEW 1 — DONNÉES BRUTES · {ligue} · {horizon}</div>"
            f"<div class='sub'>generé {g_at} · {len(rows)} matchs · bockets HAUTE: {nb_haute} · "
            f"NO BET qualitatif: {nb_norb}</div></header><main>"
            + "".join(rows)
            + "<footer>🪙 Jeu responsable : le pari est un divertissement à maîtriser. "
              "Ces probabilités ne sont pas des certitudes — EV positive = verdict long terme."
              "<br>« Fer au-dedans, Fer au-dehors. »</footer></main></body></html>")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[PREVIEW1] {len(rows)} matchs — sorties : {args.output}")


if __name__ == "__main__":
    main()
