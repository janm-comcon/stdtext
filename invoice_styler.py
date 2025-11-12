# -*- coding: utf-8 -*-
import re
import pandas as pd
from spell import spell_fix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

from corpus_corrector import CorpusCorrector

def _clean_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.upper()
    s = s.replace(",", ".")
    s = re.sub(r"\s*\.+\s*", ". ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\.\s*){2,}", ". ", s)
    return s

class InvoiceStyler:
    def __init__(self, df, vectorizer, kmeans, nn, corrector=None):
        self.df = df
        self.vectorizer = vectorizer
        self.kmeans = kmeans
        self.nn = nn
        self.corrector = corrector

    @classmethod
    def from_csv(cls, path, sep=";", text_col=None):
        df = pd.read_csv(path, sep=sep, engine="python", header=0, encoding="utf-8", on_bad_lines="skip")
        if text_col is None:
            text_col = df.columns[-1]
            for c in df.columns[::-1]:
                try:
                    if df[c].astype(str).str.len().median() > 15:
                        text_col = c
                        break
                except Exception:
                    continue
        df['text'] = df[text_col].astype(str).map(_clean_text)
        df = df[df['text'].str.strip().ne('')].drop_duplicates(subset=['text']).reset_index(drop=True)


        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=2)
        X = vectorizer.fit_transform(df['text'])

        best_model = KMeans(n_clusters=min(8, max(2, X.shape[0]//10)), random_state=42, n_init=10).fit(X)
        nn = NearestNeighbors(n_neighbors=min(5, X.shape[0]), metric='cosine').fit(X)

        corrector = CorpusCorrector(df['text'].astype(str).tolist(), max_edit=2)
        return cls(df=df, vectorizer=vectorizer, kmeans=best_model, nn=nn, corrector=corrector)

    def representatives(self):
        import numpy as np
        from sklearn.metrics import pairwise_distances
        X = self.vectorizer.transform(self.df['text'])
        labels = self.kmeans.predict(X)
        self.df = self.df.assign(cluster=labels)
        centroids = self.kmeans.cluster_centers_
        dist = pairwise_distances(X, centroids, metric='cosine')
        self.df['dist_to_centroid'] = [dist[i, lbl] for i, lbl in enumerate(labels)]
        reps = (self.df.loc[self.df.groupby('cluster')['dist_to_centroid'].idxmin(), ['cluster','text']]
                     .sort_values('cluster').reset_index(drop=True))
        return reps

    def rewrite(self, new_text: str, top_k: int = 3):
        # --- NEW: general spell-checker (before history-biased correction)
        new_text = spell_fix(self.corrector, new_text)

        # --- NEW: history-biased correction + phrase expansion (internal lowercase)
        if self.corrector is not None:
            pre = self.corrector.correct_and_expand(new_text)
        else:
            pre = new_text
        cleaned = _clean_text(pre)
        vec = self.vectorizer.transform([cleaned])
        dists, idxs = self.nn.kneighbors(vec, n_neighbors=min(top_k, len(self.df)))
        idxs = idxs[0].tolist()
        matches = self.df.iloc[idxs]['text'].tolist()
        s = cleaned
        s = re.sub(r"\b OG \b", " SAMT ", s)
        s = re.sub(r"\b SAMT OG \b", " SAMT ", s)
        if not s.endswith('.'):
            s = s + '.'
        s = re.sub(r"\s*[,;]\s*", ". ", s)
        s = re.sub(r"\s*\.+\s*", ". ", s).strip()
        s = re.sub(r"(\.\s*){2,}", ". ", s)
        return s, matches
