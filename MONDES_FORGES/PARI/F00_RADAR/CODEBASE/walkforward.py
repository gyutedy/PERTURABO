"""
F00 WALK-FORWARD — cut-off explicite, jamais in-sample (stdlib, offline).
=========================================================================
Metrics : Brier / RPS / ECE, hit-rate EV>=3%, yield Kelly 1/4.
Odds absentes = hole, jamais 0. Sortie backtest_report.json.

Usage:
  python walkforward.py --csv tests/fixtures/uk_SP1_2526.csv --cutoff 2025-09-22
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.normpath(os.path.join(HERE, "..", ".."))
F02 = os.path.join(WORLD, "F02_BREACHER", "CODEBASE")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if F02 not in sys.path:
    sys.path.insert(0, F02)

import backtest  # noqa: E402
import empirique  # noqa: E402

ODDS_O25 = ("Avg>2.5", "B365>2.5", "BbAv>2.5", "P>2.5", "Max>2.5")
ODDS_1X2 = (
    ("AvgH", "AvgD", "AvgA"),
    ("B365H", "B365D", "B365A"),
    ("BbAvH", "BbAvD", "BbAvA"),
    ("PSH", "PSD", "PSA"),
)


def parse_cutoff(raw):
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def split_cutoff(rows, cutoff):
    cut = parse_cutoff(cutoff)
    if cut is None:
        return [], [], "cutoff_absent"
    train, test = [], []
    for r in rows:
        dt = backtest._dkey(r)
        if dt == datetime.min:
            continue
        if dt < cut:
            train.append(r)
        else:
            test.append(r)
    return train, test, None


def _odds(row, keys):
    for k in keys:
        v = backtest._num(row, k)
        if v is not None and v > 1.0:
            return v
    return None


def _odds_1x2(row):
    for trio in ODDS_1X2:
        h, d, a = _odds(row, (trio[0],)), _odds(row, (trio[1],)), _odds(row, (trio[2],))
        if h and d and a:
            return {"1": h, "X": d, "2": a}
    return None


def train_lambdas(train):
    n, sh, sa = 0, 0.0, 0.0
    for r in train:
        h, a = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if h is None or a is None:
            continue
        sh += h
        sa += a
        n += 1
    if n == 0:
        return None, None, 0
    return sh / n, sa / n, n


def _probas(lh, la, rho=-0.13):
    import breacher
    m = breacher.score_matrix(lh, la, rho=rho)
    st = breacher.matrix_stats(m)
    return {
        "o2.5": st["o2.5"],
        "1": st["1"],
        "X": st["X"],
        "2": st["2"],
    }


def brier(p, y):
    return (p - y) ** 2


def rps_1x2(p1, px, p2, outcome):
    if outcome == "H":
        o = (1.0, 1.0)
    elif outcome == "D":
        o = (0.0, 1.0)
    elif outcome == "A":
        o = (0.0, 0.0)
    else:
        return None
    f1 = p1
    f2 = p1 + px
    return 0.5 * ((f1 - o[0]) ** 2 + (f2 - o[1]) ** 2)


def ece(pairs, bins=10):
    if not pairs or bins < 1:
        return None
    buckets = [[] for _ in range(bins)]
    for p, y in pairs:
        i = min(bins - 1, max(0, int(p * bins)))
        buckets[i].append((p, y))
    n = len(pairs)
    acc = 0.0
    for b in buckets:
        if not b:
            continue
        conf = sum(p for p, _ in b) / len(b)
        hit = sum(y for _, y in b) / len(b)
        acc += abs(hit - conf) * (len(b) / n)
    return acc


def kelly_frac(p, odds, fraction=0.25):
    if odds is None or odds <= 1.0 or p is None:
        return None
    edge = p * odds - 1.0
    if edge <= 0:
        return 0.0
    f = fraction * edge / (odds - 1.0)
    if f < 0:
        return 0.0
    return min(f, 1.0)


def walk_forward(rows, cutoff, ev_min=None, kelly_q=None, ece_bins=None, rho=-0.13):
    cfg = empirique.load_config()
    ev_min = cfg["ev_min"] if ev_min is None else ev_min
    kelly_q = cfg["kelly_frac"] if kelly_q is None else kelly_q
    ece_bins = int(cfg["ece_bins"] if ece_bins is None else ece_bins)
    train, test, hole = split_cutoff(rows, cutoff)
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff": None if cutoff is None else str(cutoff)[:10],
        "n_train": len(train),
        "n_test": len(test),
        "in_sample": False,
        "holes": [],
        "metrics": {},
    }
    if hole:
        report["holes"].append(hole)
        return report
    cut = parse_cutoff(cutoff)
    report["cutoff"] = cut.strftime("%Y-%m-%d") if cut else None
    if any(backtest._dkey(r) >= cut for r in train):
        report["holes"].append("in_sample")
        return report
    lh, la, n_lam = train_lambdas(train)
    if n_lam == 0 or lh is None:
        report["holes"].append("train_vide")
        return report
    report["lambda_dom"] = round(lh, 4)
    report["lambda_ext"] = round(la, 4)
    pbrier, prps, po25 = [], [], []
    n_ev, n_ev_hit = 0, 0
    stake, pnl = 0.0, 0.0
    n_odds_o25, n_odds_1x2 = 0, 0
    for r in test:
        h, a = backtest._num(r, "FTHG"), backtest._num(r, "FTAG")
        if h is None or a is None:
            continue
        pr = _probas(lh, la, rho=rho)
        y_o = 1.0 if (h + a) >= 3 else 0.0
        pbrier.append(brier(pr["o2.5"], y_o))
        po25.append((pr["o2.5"], y_o))
        ftr = (r.get("FTR") or "").strip().upper()
        if not ftr:
            ftr = "H" if h > a else ("A" if a > h else "D")
        rp = rps_1x2(pr["1"], pr["X"], pr["2"], ftr)
        if rp is not None:
            prps.append(rp)
        cote = _odds(r, ODDS_O25)
        if cote is None:
            report.setdefault("odds_holes", 0)
            report["odds_holes"] = (report.get("odds_holes") or 0) + 1
        else:
            n_odds_o25 += 1
            ev = pr["o2.5"] * cote - 1.0
            if ev >= ev_min:
                n_ev += 1
                win = y_o == 1.0
                if win:
                    n_ev_hit += 1
                f = kelly_frac(pr["o2.5"], cote, kelly_q)
                if f and f > 0:
                    stake += f
                    pnl += f * (cote - 1.0) if win else -f
        if _odds_1x2(r):
            n_odds_1x2 += 1
    metrics = {
        "brier_o2.5": (sum(pbrier) / len(pbrier)) if pbrier else None,
        "rps_1x2": (sum(prps) / len(prps)) if prps else None,
        "ece_o2.5": ece(po25, bins=ece_bins),
        "n_brier": len(pbrier),
        "n_rps": len(prps),
        "hit_rate_ev3": (n_ev_hit / n_ev) if n_ev else None,
        "n_ev3": n_ev,
        "yield_kelly_1_4": (pnl / stake) if stake else None,
        "n_odds_o2.5": n_odds_o25,
        "n_odds_1x2": n_odds_1x2,
    }
    if n_odds_o25 == 0 and test:
        report["holes"].append("odds")
    report["metrics"] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in metrics.items()}
    report["n_eval"] = len(pbrier)
    return report


def run_file(path, cutoff, out=None):
    rows = backtest.load_csv(path)
    rec = walk_forward(rows, cutoff)
    rec["source"] = os.path.basename(path)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
    return rec


def run_dir(csv_dir, cutoff, out=None):
    reports = {}
    if csv_dir and os.path.isdir(csv_dir):
        for name in sorted(os.listdir(csv_dir)):
            if not name.lower().endswith(".csv"):
                continue
            path = os.path.join(csv_dir, name)
            rows = backtest.load_csv(path)
            if not rows:
                continue
            code = (rows[0].get("Div") or "").upper() or name
            rec = walk_forward(rows, cutoff)
            rec["source"] = name
            rec["league_code"] = code
            reports[code] = rec
    blob = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff": str(cutoff)[:10] if cutoff else None,
        "offline": True,
        "in_sample": False,
        "leagues": reports,
    }
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(blob, f, indent=2, ensure_ascii=False)
    return blob


def main():
    parser = argparse.ArgumentParser(description="F00 WALK-FORWARD cut-off explicite")
    parser.add_argument("--csv", default=None)
    parser.add_argument("--csv-dir", default=os.environ.get("PARI_UK_CACHE") or os.path.join(
        WORLD, "ARCHIVUM", "cache", "f00"))
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--out", default=os.path.join(WORLD, "ARCHIVUM", "learnings", "backtest_report.json"))
    args = parser.parse_args()
    if args.csv:
        rec = run_file(args.csv, args.cutoff, out=args.out)
        print(f"[WALKFORWARD] n_train={rec.get('n_train')} n_test={rec.get('n_test')} "
              f"holes={rec.get('holes')} → {args.out}")
    else:
        blob = run_dir(args.csv_dir, args.cutoff, out=args.out)
        print(f"[WALKFORWARD] {len(blob.get('leagues') or {})} ligue(s) → {args.out}")


if __name__ == "__main__":
    main()
