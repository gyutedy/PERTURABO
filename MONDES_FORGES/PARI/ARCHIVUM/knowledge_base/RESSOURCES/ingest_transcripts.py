#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_transcripts.py — ingestion + traçabilité des transcriptions YouTube
Le monde PARI — chaîne « The Football Bank » (@thefootballbank2924).

Place une transcription brute venant d'un outil externe :
  1. identifie la vidéo (11 caractères id YouTube) par nom de fichier ou contenu ;
  2. la classe au bon dossier <CATEGORIE>/transcripts/<slug>_<id>.md ;
  3. en-tête normalisé avec date de publication + date de récupération (règle freshness) ;
  4. met à jour catalogue_videos.csv.

Jamais auto-modifié arrière en contexte ; c'est la transposition pure.
Sub-commandes:
  --add  <fichier|dossier ...>      ingérer des transcriptions brutes (id détecté automatiquement)
  --dates <id>=YYYY-MM-JJ ...       renseigner la date de publication dans le catalogue + en-têtes
  --dates <fichier.csv>             CSV à 2 colonnes (id,upload_date)
  --status <id>=<statut> ...        brut|depouille|a_valider
  --freshness [nb_jours=90]         vérifier les données	out of date / manquantes
  --rebuild-catalogue               reconstruire la liste (tous les onboardings)
"""
import argparse, csv, os, re, sys, unicodedata
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, "catalogue_videos.csv")
CATEGORIES = ["GENERAL", "OVER_UNDER", "BTTS", "HOTPICKS", "CHALLENGE", "KEYS",
              "FOOTUPDATE", "LIVE", "QUIZCHALLENGE", "PATREON", "SERIEB", "OTHER"]
ID_RE = re.compile(r"([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
STATUTS = {"brut", "depouille", "a_valider"}


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text[:60] or "transcript"


def category_of(title):
    t = title.lower()
    if "both teams to score" in t or "btts" in t: return "BTTS"
    if "expected goals" in t or "secret to over/under" in t or "under 2.5 goals market ruined" in t:
        return "OVER_UNDER"
    if "hot picks" in t: return "HOTPICKS"
    if "football bank live stream" in t: return "LIVE"
    if "guess who" in t or "quiz" in t: return "QUIZCHALLENGE"
    if "challenge" in t or "#acca" in t or "#accumulator" in t or "50 to 500" in t: return "CHALLENGE"
    if "keys to success" in t: return "KEYS"
    if "patreon" in t: return "PATREON"
    if "league overview" in t or "serie b" in t: return "SERIEB"
    if any(k in t for k in ["tips #", "#5 in-play", "#6 avoid", "#7 avoid", "#8 research",
                            "#9 expected", "#10 expected", "#11 international",
                            "betting strategy", "football betting tips", "football update"]):
        return "GENERAL"
    return "OTHER"


def load_catalogue():
    with open(CATALOGUE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_catalogue(rows, fieldnames):
    with open(CATALOGUE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def find_video_id(filename, content):
    m = ID_RE.search(os.path.basename(filename))
    if m:
        return m.group(1)
    for pattern in (r"watch\?v=([A-Za-z0-9_-]{11})", r"^ID vidéo\s*[:=]\s*([A-Za-z0-9_-]{11})\s*$",
                    r"^Video ID\s*[:=]\s*([A-Za-z0-9_-]{11})\s*$"):
        m = re.search(pattern, content, re.M)
        if m:
            return m.group(1)
    return None


def build_header(row, slug, retrieve_date):
    return (
        f"# Transcription brute — {slug} — {row['id']}\n\n"
        f"- **ID vidéo** : {row['id']}\n"
        f"- **Chaîne** : The Football Bank (@thefootballbank2924)\n"
        f"- **URL** : {row['url']}\n"
        f"- **Date de publication (upload YouTube)** : {row['upload_date'] or 'TO_CONFIRM'}\n"
        f"- **Date de récupération de la transcription** : {retrieve_date}\n"
        f"- **Catégorie** : {row['categorie']}\n"
        f"- **Statut** : brut\n"
        f"- **Date de vérification fraicheur croisée (croisée + récent)** : (à remplir au dépouillement)\n"
        f"---\n\n"
    )


def cmd_add(paths, args):
    rows = load_catalogue()
    fieldnames = list(rows[0].keys())
    by_id = {r["id"]: r for r in rows}
    today = date.today().isoformat()
    added, skipped_id, unknown = [], [], []

    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, fnames in os.walk(p):
                files += [os.path.join(root, x) for x in sorted(fnames)
                          if x.lower().endswith((".txt", ".md", ".vtt", ".srt")) and x != ".gitkeep"]
        else:
            files.append(p)

    for path in files:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        vid = find_video_id(path, content)
        if not vid:
            unknown.append(path); continue
        row = by_id.get(vid)
        if not row:
            unknown.append(f"{path} (id « {vid} » absent du catalogue)"); continue
        if row["fichier_transcription"]:
            skipped_id.append(f"{path} -> {row['fichier_transcription']}"); continue

        slug_parts = slugify(row["titre"])
        slug = re.sub(r"^_", "", slug_parts)
        cat = row["categorie"] if row["categorie"] in CATEGORIES else "UNCLASSIFIED"
        os.makedirs(os.path.join(HERE, cat, "transcripts"), exist_ok=True)
        dest_rel = os.path.join(cat, "transcripts", f"{slug}_{vid}.md")
        dest_abs = os.path.join(HERE, dest_rel)
        body = content
        if body.startswith("# Transcription brute"):
            body = body.split("---", 1)[1].lstrip() if "---" in body[:400] else body
        with open(dest_abs, "w", encoding="utf-8") as f:
            f.write(build_header(row, slug, today))
            f.write(body.rstrip() + "\n")

        row["fichier_transcription"] = f"./{dest_rel}"
        row["date_recuperation"] = today
        row["statut_transcription"] = "brut"
        added.append(f"{path} -> {dest_rel}")

    save_catalogue(rows, fieldnames)
    print(f"INGÉRÉES  ({len(added)}) :")
    for a in added: print(f"  + {a}")
    if skipped_id:
        print(f"DÉJÀ PRÉSENTES ({len(skipped_id)}) — pas modifiées (les 14 existantes restent intactes) :")
        for s in skipped_id: print(f"  = {s}")
    if unknown:
        print(f"NON RECONNUES ({len(unknown)}) — id YouTube introuvable, à classer à la main :")
        for u in unknown: print(f"  ? {u}")
    return 0 if not unknown else 1


def cmd_dates(specs):
    rows = load_catalogue()
    fieldnames = list(rows[0].keys())
    by_id = {r["id"]: r for r in rows}
    specs = list(specs)
    if len(specs) == 1 and os.path.isfile(specs[0]):
        specs = [f"{a}={b}" for a, b in csv.reader(open(specs[0], encoding="utf-8")) if a and b]
    done = 0
    for spec in specs:
        vid, _, ds = spec.partition("=")
        vid, ds = vid.strip(), ds.strip()
        if vid not in by_id:
            print(f"  ! id inconnu : {vid}"); continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
            print(f"  ! date invalide pour {vid} : « {ds} » (format AAAA-MM-JJ)"); continue
        by_id[vid]["upload_date"] = ds
        # synchro de l'en-tête si la transcription existe déjà
        rel = by_id[vid]["fichier_transcription"]
        if rel:
            fp = os.path.join(HERE, rel)
            if os.path.isfile(fp):
                with open(fp, encoding="utf-8") as f: body = f.read()
                body = re.sub(r"(Date de publication \(upload YouTube\)\*\* : ).*[^\n]",
                              rf"\g<1>{ds}", body)
                with open(fp, "w", encoding="utf-8") as f: f.write(body)
        done += 1
    save_catalogue(rows, fieldnames)
    print(f"Dates posées : {done}/{len(specs)}")
    missing = [r["id"] for r in rows if not r["upload_date"]]
    print(f"Vidéos sans date de publication : {len(missing)}")
    if missing: print("  " + " ".join(missing))


def cmd_status(specs):
    rows = load_catalogue()
    fieldnames = list(rows[0].keys())
    by_id = {r["id"]: r for r in rows}
    for spec in specs:
        vid, _, st = spec.partition("=")
        vid, st = vid.strip(), st.strip()
        if vid not in by_id:
            print(f"  ! id inconnu : {vid}"); continue
        if st not in STATUTS:
            print(f"  ! statut invalide : {st} (choix : {' | '.join(sorted(STATUTS))})"); continue
        by_id[vid]["statut_transcription"] = st
        print(f"  = {vid} -> {st}")
    save_catalogue(rows, fieldnames)


def cmd_freshness(nb_days):
    rows = load_catalogue()
    today = datetime.strptime(date.today().isoformat(), "%Y-%m-%d")
    no_date, old, fresh = [], [], []
    for r in rows:
        if not r["fichier_transcription"]:
            continue
        if not r["upload_date"]:
            no_date.append(r)
        elif r["date_recuperation"]:
            d = (today - datetime.strptime(r["date_recuperation"], "%Y-%m-%d")).days
            (old if d > nb_days else fresh).append((r, d))
    print("=== FRAÎCHEUR RESSOURCES ===")
    print(f"Transcriptions déposées : {sum(1 for r in rows if r['fichier_transcription'])}/{len(rows)}")
    print(f"Sans date de publication (source non datée — DANGER à l'interprétation) : {len(no_date)}")
    for r in no_date: print(f"  ! {r['id']} {r['titre'][:50]}")
    print(f"Transcriptions de plus de {nb_days} jours (à recroiser avant usage) : {len(old)}")
    for r, d in old: print(f"  âge {d}j — {r['id']} {r['titre'][:50]}")
    return 1 if no_date else 0


def cmd_rebuild():
    rows = load_catalogue()
    fieldnames = list(rows[0].keys())
    for r in rows:
        if not os.path.isfile(os.path.join(HERE, r["fichier_transcription"] or "XX")):
            r["fichier_transcription"] = ""
            r["date_recuperation"] = ""
            r["statut_transcription"] = ""
    save_catalogue(rows, fieldnames)
    print("Catalogue nettoyé des entrées fantômes.")


def main():
    ap = argparse.ArgumentParser(description="Ingestion des transcriptions PARI (chaîne The Football Bank).")
    ap.add_argument("--add", nargs="+", metavar="CHEMIN")
    ap.add_argument("--dates", nargs="+", metavar="ID=AAAA-MM-JJ")
    ap.add_argument("--status", nargs="+", metavar="ID=STATUT")
    ap.add_argument("--freshness", nargs="?", const="90", metavar="NB_JOURS")
    ap.add_argument("--rebuild-catalogue", action="store_true")
    args = ap.parse_args()

    if args.add:
        sys.exit(cmd_add(args.add, args))
    elif args.dates:
        sys.exit(cmd_dates(args.dates))
    elif args.status:
        cmd_status(args.status)
    elif args.freshness:
        sys.exit(cmd_freshness(int(args.freshness)))
    elif args.rebuild_catalogue:
        cmd_rebuild()
    else:
        ap.print_help()
        print("\nRègle obligatoire : toute transcription porte une date de publication (règle freshness) — voir ARCHIVUM/rules/freshness_sources.md")


if __name__ == "__main__":
    main()
