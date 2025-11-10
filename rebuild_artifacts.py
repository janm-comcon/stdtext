# -*- coding: utf-8 -*-
"""
rebuild_artifacts.py
run locally to rebuild artifacts after text.csv changes.

usage:
    python rebuild_artifacts.py --csv "C:\\path\\to\\text.csv"
"""

import argparse, json, re, joblib
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors

def clean_text(s: str) -> str:
    if not isinstance(s, str): s = str(s)
    s = s.replace('\r\n',' ').replace('\n',' ').replace('\r',' ')
    s = re.sub(r'\s+',' ', s).strip()
    s = s.upper().replace(',', '.')
    s = re.sub(r'\s*[\.\u2026]+\s*', '. ', s)
    s = re.sub(r'\s+',' ', s).strip()
    s = re.sub(r'(\.\s*){2,}', '. ', s)
    return s

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="path to new text.csv")
    args = ap.parse_args()

    root = Path(__file__).parent
    art  = root / "artifacts"
    art.mkdir(exist_ok=True)

    df_raw = pd.read_csv(args.csv, sep=';', engine='python', header=0, encoding='utf-8', on_bad_lines='skip')

    # text column guess (same heuristic as service)
    text_col = None
    for c in df_raw.columns[::-1]:
        try:
            if df_raw[c].astype(str).str.len().median() > 15:
                text_col = c
                break
        except Exception:
            pass
    if text_col is None:
        text_col = df_raw.columns[-1]

    df = df_raw.copy()
    df['text'] = df[text_col].astype(str).map(clean_text)
    df = df[df['text'].str.strip().ne('')].drop_duplicates(subset=['text']).reset_index(drop=True)

    # vectorize + cluster
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=2)
    X = vectorizer.fit_transform(df['text'])

    k = min(8, max(2, X.shape[0]//10)) or 4
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    nn = NearestNeighbors(n_neighbors=min(5, X.shape[0]), metric='cosine').fit(X)

    # write artifacts
    df[['text']].to_csv(art/"cleaned.csv", index=False, encoding='utf-8')
    joblib.dump(vectorizer, art/"vectorizer.pkl")
    joblib.dump(kmeans,   art/"kmeans.pkl")
    joblib.dump(nn,       art/"nn.pkl")

    meta = {"built_at":"local run", "records":int(df.shape[0]), "model_version":"v1"}
    (art/"model_meta.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')

    print("OK: artifacts rebuilt in", art)
