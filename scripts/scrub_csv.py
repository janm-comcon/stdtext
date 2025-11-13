# -*- coding: utf-8 -*-

import sys
sys.path.insert(1, "../stdtext")

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders, remove_sensitive
from pathlib import Path
import pandas as pd, csv
SRC = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/text_scrubbed.csv")
if not SRC.exists():
    print("Missing source:", SRC)
else:
    df = pd.read_csv(SRC, sep=",", engine="python", encoding="utf-8", on_bad_lines="skip")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    originals=[]
    scrubbed=[]
    for line in df[text_col].astype(str):
        norm = simple_normalize(line)
        txt, mapping = extract_placeholders(norm)
        cleaned = remove_sensitive(txt, keep_room_words=True)
        scrubbed_line = reinsert_placeholders(cleaned, mapping)
        originals.append(line)
        scrubbed.append(scrubbed_line)
    df[text_col]=scrubbed
    df.to_csv(OUT, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    print("Wrote scrubbed CSV:", OUT)
