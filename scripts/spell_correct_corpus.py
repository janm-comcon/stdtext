# -*- coding: utf-8 -*-
"""
spell_correct_corpus.py

Spell-corrects the corpus EXCEPT:
  - abbreviations (2–3 letters + ".")
  - abbreviations in abbrev_map.json
  - placeholders like <CITY_0001>
  - COUNT placeholders <COUNT_0001>
"""

import csv
import json
from pathlib import Path

import sys
sys.path.insert(1, "../stdtext")

from stdtext.spell import SpellWrapper

SRC = Path("C:/Temp/text_scrubbed.csv")
OUT = Path("C:/Temp/text_corrected.csv")
ABBREV_MAP = Path("C:/Temp/abbrev_map.json")

# Load abbreviation whitelist
ABBREVS = set()
if ABBREV_MAP.exists():
    data = json.loads(ABBREV_MAP.read_text(encoding="utf-8"))
    ABBREVS = set(k.lower() for k in data.keys())


def is_placeholder(tok: str) -> bool:
    return tok.startswith("<") and tok.endswith(">")


def is_abbreviation(tok: str) -> bool:
    t = tok.lower()
    # whitelist abbreviation?
    if t in ABBREVS:
        return True
    # matches basic pattern: 2–3 letters + "."
    if len(t) <= 4 and t.endswith(".") and t[:-1].isalpha():
        return True
    return False


def spell_fix_line(line: str, sp: SpellWrapper) -> str:
    tokens = line.split()
    fixed = []

    for tok in tokens:
        if is_placeholder(tok):
            fixed.append(tok)
            continue
        if is_abbreviation(tok):
            fixed.append(tok)
            continue

        # safe spell correction
        fixed.append(sp.correction(tok))

    return " ".join(fixed)


def main():
    if not SRC.exists():
        print("ERROR: Source CSV not found:", SRC)
        return

    sp = SpellWrapper()

    with SRC.open("r", encoding="utf-8") as f_in, OUT.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)

        header = next(reader)
        writer.writerow(header)

        # detect text column
        text_col = max(range(len(header)), key=lambda i: len(header[i]))

        for row in reader:
            text = row[text_col]
            row[text_col] = spell_fix_line(text, sp)
            writer.writerow(row)

    print("Spell corrected corpus written to:", OUT)


if __name__ == "__main__":
    main()
