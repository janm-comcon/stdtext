# -*- coding: utf-8 -*-
"""
da_dictionary_builder.py
Builds a Danish spell-check wordlist from your cleaned invoice corpus.
"""

import pandas as pd
import re
from pathlib import Path
from collections import Counter

CLEANED = Path(r"C:\Temp\text_scrubbed.csv")
OUTPUT  = Path(r"C:\Temp\da_dictionary.txt")

TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå]+")

def main():
    if not CLEANED.exists():
        print(f"File not found: {CLEANED}")
        return

    df = pd.read_csv(CLEANED, encoding="utf-8")
    # pick longest text-like column
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    words = Counter()
    for line in df[text_col].astype(str):
        for tok in TOKEN_RE.findall(line):
            words[tok.lower()] += 1

    # keep frequent words only (≥ 2 occurrences)
    vocab = [w for w, f in words.most_common() if f >= 2]
    OUTPUT.write_text("\n".join(vocab), encoding="utf-8")
    print(f"Wrote {len(vocab):,} words to {OUTPUT}")

if __name__ == "__main__":
    main()
