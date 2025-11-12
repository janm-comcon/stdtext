# -*- coding: utf-8 -*-
"""
abbrev_builder.py
Scans cleaned invoice corpus (text_scrubbed.csv) to detect likely abbreviations.
Produces abbrev_map.json for integration with expand_abbreviations().

Usage:
    python C:\Temp\abbrev_builder.py
"""

import pandas as pd
import re, json
from pathlib import Path
from collections import Counter

CLEANED = Path(r"C:\Temp\text_scrubbed.csv")
OUTPUT  = Path(r"C:\Temp\abbrev_map.json")

TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå]+")

# configurable thresholds
MIN_SHORT_LEN = 3       # consider tokens this length or longer as possible abbrev
MAX_LONG_LEN = 15       # ignore extremely long tokens
MIN_FREQ = 2            # token must appear at least twice
PREFIX_DIFF_MAX = 4     # difference allowed between short and long form

def main():
    if not CLEANED.exists():
        print(f"ERROR: file not found: {CLEANED}")
        return

    df = pd.read_csv(CLEANED, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    counter = Counter()
    for line in df[text_col].astype(str):
        for tok in TOKEN_RE.findall(line):
            t = tok.lower()
            if len(t) >= MIN_SHORT_LEN and len(t) <= MAX_LONG_LEN:
                counter[t] += 1

    vocab = set(counter.keys())
    abbrev_map = {}

    # find potential abbreviations by prefix relation
    for short in vocab:
        if len(short) < 4:
            continue
        # skip if already full word (appears often)
        if counter[short] > 20:
            continue
        matches = [v for v in vocab
                   if v.startswith(short)
                   and len(v) - len(short) <= PREFIX_DIFF_MAX
                   and counter[v] >= counter[short]]
        if matches:
            # pick the longest/frequent as canonical
            long_form = sorted(matches, key=lambda w: (len(w), counter[w]), reverse=True)[0]
            # sanity: avoid mapping identical word
            if long_form != short:
                abbrev_map[short] = long_form

    # pretty sort
    abbrev_map = dict(sorted(abbrev_map.items()))

    OUTPUT.write_text(json.dumps(abbrev_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Detected {len(abbrev_map)} likely abbreviations.")
    print(f"Wrote {OUTPUT}")

    # preview a few
    for k in list(abbrev_map)[:15]:
        print(f"  {k:15s} → {abbrev_map[k]}")

if __name__ == "__main__":
    main()
