
# -*- coding: utf-8 -*-
from stdtext.model import CorpusCorrector
from pathlib import Path
import pandas as pd
SRC = Path("C:/Temp/text_corrected.csv")
ART = Path("./artifacts")
if not SRC.exists():
    print("Missing source corrected csv:", SRC)
else:
    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    texts = df[text_col].astype(str).tolist()
    # lowercase training
    texts = [t.lower() for t in texts]
    corr = CorpusCorrector(texts=texts)
    corr.save(ART)
    print("Rebuilt artifacts in", ART)
