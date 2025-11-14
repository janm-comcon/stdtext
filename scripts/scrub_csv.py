# -*- coding: utf-8 -*-
import sys
sys.path.insert(1, "../stdtext")

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders, remove_sensitive
from stdtext.entity_scrubber import extract_entities
from pathlib import Path
import pandas as pd, csv

SRC = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/text_scrubbed.csv")

if not SRC.exists():
    print("Missing source:", SRC)
else:
    df = pd.read_csv(SRC, sep=",", engine="python", encoding="utf-8", on_bad_lines="skip")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    scrubbed = []
    for line in df[text_col].astype(str):
        norm = simple_normalize(line)
        t1, map_abbr = extract_placeholders(norm)
        t2, map_ent = extract_entities(t1)
        # Remove sensitive data but keep placeholders
        cleaned = remove_sensitive(t2, keep_room_words=True)
        # For training corpus we keep entity placeholders removed (we do NOT reinsert entities)
        # but we keep abbreviations so cluster sees structure words.
        cleaned_final = reinsert_placeholders(cleaned, map_abbr)
        scrubbed.append(cleaned_final)
    df[text_col] = scrubbed
    df.to_csv(OUT, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    print("Wrote scrubbed CSV:", OUT)
