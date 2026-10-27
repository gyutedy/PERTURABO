#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "MONDES_FORGES/PARI/ARCHIVUM/knowledge_base/RESSOURCES")
from ingest_transcripts import cmd_add
files = [
    "tmp_tv/transcripts_input/video1.txt",
    "tmp_tv/transcripts_input/video2.txt",
    "tmp_tv/transcripts_input/video3.txt",
    "tmp_tv/transcripts_input/video4.txt",
]
# on lance --add sur chaque fichier séparément pour que le script puisse extraire l'ID
for f in files:
    if os.path.isfile(f):
        print(f"\n--- Traitement de : {f} ---")
        ret = cmd_add([f])
        sys.exit(ret)
print("\nTerminé.")