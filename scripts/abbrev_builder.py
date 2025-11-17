# -*- coding: utf-8 -*-
"""Builds a simple whitelist of abbreviations from scrubbed corpus."""
import re
import json
from pathlib import Path
from collections import Counter
import pandas as pd

SRC = Path("C:/Temp/text_scrubbed.csv")
OUT = Path("C:/Temp/abbrev_map.json")

ABBR_RE = re.compile(r"\b([A-Za-zÆØÅæøå]{2,3}\.)\b", flags=re.UNICODE)


def main():
    if not SRC.exists():
        print("Missing source:", SRC)
        return

    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    counter = Counter()

    for line in df[text_col].astype(str):
        for m in ABBR_RE.finditer(line):
            abbr = m.group(1)
            counter[abbr] += 1

    abbrev_map = {abbr: freq for abbr, freq in counter.items() if freq >= 1}
    OUT.write_text(json.dumps(abbrev_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Found {len(abbrev_map)} abbreviations. Written to {OUT}")


if __name__ == "__main__":
    main()
