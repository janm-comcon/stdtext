# -*- coding: utf-8 -*-
"""
abbrev_builder.py

Builds a simple whitelist of Danish-style abbreviations from the corpus.

Danish abbreviations are typically:
  - 2 or 3 letters
  - followed by a dot, e.g. "stk.", "udv.", "osv."

Output:
  C:/Temp/abbrev_map.json

Format:
  {
    "stk.": 123,
    "udv.": 45,
    "osv.": 12,
    ...
  }

No expansions are guessed, we only record which abbreviations occur
and how often, so they can be treated as valid words (and not spell-corrected).
"""

import re
import json
from pathlib import Path
from collections import Counter

SRC = Path("C:/Temp/text_scrubbed.csv")   # or text_corrected.csv if you prefer
OUT = Path("C:/Temp/abbrev_map.json")

ABBR_RE = re.compile(r"\b([A-Za-zÆØÅæøå]{2,3}\.)\b", flags=re.UNICODE)


def main():
    if not SRC.exists():
        print("Missing source CSV:", SRC)
        return

    import pandas as pd

    df = pd.read_csv(SRC, encoding="utf-8")
    # Pick the text column by longest median length heuristic
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    counter = Counter()

    for line in df[text_col].astype(str):
        # Find all abbreviations like "stk.", "udv.", "osv."
        for m in ABBR_RE.finditer(line):
            abbr = m.group(1)
            counter[abbr] += 1

    # Filter out very rare abbreviations if you want (e.g. >= 2)
    abbrev_map = {abbr: freq for abbr, freq in counter.items() if freq >= 1}

    OUT.write_text(json.dumps(abbrev_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Found {len(abbrev_map)} abbreviations. Written to {OUT}")


if __name__ == "__main__":
    main()
