# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
from stdtext.model import CorpusCorrector

SRC = Path("C:/Temp/text_corrected.csv")
ART = Path("./artifacts")


def main():
    if not SRC.exists():
        print("Missing source:", SRC)
        return

    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())

    texts = df[text_col].astype(str).tolist()
    texts = [t.lower() for t in texts]

    corr = CorpusCorrector(texts=texts)
    corr.save(ART)
    print("Rebuilt artifacts in", ART)


if __name__ == "__main__":
    main()
