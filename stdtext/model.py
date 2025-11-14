# -*- coding: utf-8 -*-
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib
from pathlib import Path
import pandas as pd

class CorpusCorrector:
    def __init__(self, texts=None, vectorizer=None, nn=None):
        self.vectorizer = vectorizer
        self.nn = nn
        self.df = None
        if texts is not None:
            self.fit(texts)

    def fit(self, texts):
        self.df = pd.DataFrame({"text": texts}).drop_duplicates().reset_index(drop=True)
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), min_df=1)
        X = self.vectorizer.fit_transform(self.df["text"])
        self.nn = NearestNeighbors(n_neighbors=min(5, len(self.df)), metric="cosine").fit(X)

    def save(self, path: Path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, path / "vectorizer.pkl")
        joblib.dump(self.nn, path / "nn.pkl")
        self.df.to_csv(path / "cleaned.csv", index=False, encoding="utf-8")

    @classmethod
    def load(cls, path: Path):
        path = Path(path)
        v = joblib.load(path / "vectorizer.pkl")
        nn = joblib.load(path / "nn.pkl")
        df = pd.read_csv(path / "cleaned.csv", encoding="utf-8")
        obj = cls()
        obj.vectorizer, obj.nn, obj.df = v, nn, df
        return obj

    def query(self, text: str, top_k: int=3):
        if self.vectorizer is None or self.nn is None or self.df is None or len(self.df)==0:
            return []
        vec = self.vectorizer.transform([text])
        n = min(top_k, len(self.df))
        dists, idx = self.nn.kneighbors(vec, n_neighbors=n)
        return [self.df.iloc[i]["text"] for i in idx[0]]
