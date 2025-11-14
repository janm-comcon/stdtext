# -*- coding: utf-8 -*-
import sys
sys.path.insert(1, "../stdtext")

from stdtext.spell import SpellWrapper
from pathlib import Path
import pandas as pd, re

SRC = Path("C:/Temp/text_scrubbed.csv")
OUT = Path("C:/Temp/text_corrected.csv")
DICT = Path("C:/Temp/da_dictionary.txt")

if not SRC.exists():
    print("Missing:", SRC)
else:
    sp = SpellWrapper(da_dictionary_path=str(DICT))
    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    def fix_line(line: str) -> str:
        tokens = re.findall(r"[A-Za-zÆØÅæøå]+|<[^>]+>", str(line))
        out = []
        for t in tokens:
            if t.startswith("<") and t.endswith(">"):
                out.append(t)
            else:
                out.append(sp.correction(t))
        return " ".join(out)

    df[text_col] = df[text_col].astype(str).map(fix_line)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print("Wrote corrected corpus to:", OUT)
