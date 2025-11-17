# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import csv

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders, remove_sensitive
from stdtext.entity_scrubber import extract_entities

SRC = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/text_scrubbed.csv")


def main():
    if not SRC.exists():
        print("Missing source:", SRC)
        return

    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    scrubbed = []
    for line in df[text_col].astype(str):
        norm = simple_normalize(line)
        t1, map_abbr = extract_placeholders(norm)
        t2, map_ent = extract_entities(t1)
        cleaned = remove_sensitive(t2, keep_room_words=True)
        # training: do not reinsert entities, but keep abbreviations
        cleaned_final = reinsert_placeholders(cleaned, map_abbr)
        scrubbed.append(cleaned_final)

    df[text_col] = scrubbed
    df.to_csv(OUT, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    print("Wrote scrubbed CSV:", OUT)


if __name__ == "__main__":
    main()
