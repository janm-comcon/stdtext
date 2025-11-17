# -*- coding: utf-8 -*-
import re
from pathlib import Path
import pandas as pd

SRC = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/da_dictionary.txt")

TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå]+")

def main():
    if not SRC.exists():
        print("Missing source:", SRC)
        return

    df = pd.read_csv(SRC, sep=",", engine="python", encoding="utf-8", on_bad_lines="skip")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    counts = {}
    for line in df[text_col].astype(str):
        for w in TOKEN_RE.findall(line):
            k = w.lower()
            counts[k] = counts.get(k, 0) + 1

    vocab = [w for w, f in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if f >= 2]
    OUT.write_text("\n".join(vocab), encoding="utf-8")
    print("Wrote", len(vocab), "words to", OUT)


if __name__ == "__main__":
    main()
