# -*- coding: utf-8 -*-
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

# --- NEW: history-biased correction + phrase expansion -----------------------
import math
import collections
import re as _re

_TOKEN_RE = _re.compile(r"[A-Za-zÆØÅæøå0-9]+")

def _lev(a: str, b: str, max_d: int = 2) -> int:
    """Levenshtein with early cutoff at max_d (small for speed)."""
    if abs(len(a) - len(b)) > max_d:
        return max_d + 1
    # ensure a is shorter
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        lo = max(1, i - max_d)
        hi = min(len(b), i + max_d)
        for j in range(1, len(b) + 1):
            if j < lo or j > hi:
                cur.append(max_d + 1)
                continue
            cost = 0 if ca == b[j - 1] else 1
            cur.append(min(
                prev[j] + 1,        # deletion
                cur[j - 1] + 1,     # insertion
                prev[j - 1] + cost  # substitution
            ))
        if min(cur) > max_d:
            return max_d + 1
        prev = cur
    return prev[-1]

class CorpusCorrector:
    """
    - token correction: prefer historic vocabulary; max edit distance = 2 (2)
    - phrase expansion: prefer frequent 2/3-grams; aggressive expansion to canonical phrases (3)
    """
    def __init__(self, texts: list[str], max_edit: int = 2,
                 min_prefix_freq: int = 3, next_token_dominance: float = 0.6):
        self.max_edit = max_edit
        self.min_prefix_freq = min_prefix_freq
        self.next_token_dominance = next_token_dominance

        toks = []
        for t in texts:
            t = t.lower()
            toks.append([m.group(0) for m in _TOKEN_RE.finditer(t)])

        # Unigram vocab + freq
        self.uni_freq = collections.Counter(w for row in toks for w in row)
        self.vocab = set(self.uni_freq.keys())

        # n-grams (2,3) + prefix→next token map
        self.bigrams = collections.Counter()
        self.trigrams = collections.Counter()
        self.next_map = collections.defaultdict(collections.Counter)  # prefix(tuple) -> Counter(next)

        for row in toks:
            for i in range(len(row) - 1):
                bg = (row[i], row[i+1])
                self.bigrams[bg] += 1
                if i + 2 <= len(row) - 1:
                    ng = (row[i], row[i+1])
                    nxt = row[i+2]
                    self.next_map[ng][nxt] += 1
            for i in range(len(row) - 2):
                tg = (row[i], row[i+1], row[i+2])
                self.trigrams[tg] += 1
                if i + 3 <= len(row) - 1:
                    ng = (row[i], row[i+1], row[i+2])
                    nxt = row[i+3]
                    self.next_map[ng][nxt] += 1

        # tiny synonyms that often appear in free text → canonical phrase tails
        # extend if you spot more in your corpus later
        self.tail_expansions = {
            "ok": ["i", "orden"],
        }

    def _best_vocab_match(self, token: str) -> str:
        """Return best historic token within edit distance; else original."""
        if token in self.vocab:
            return token
        best = (self.max_edit + 1, -1, token)  # (distance, freq, cand)
        # cheap candidate pruning: only compare to vocab words with |len diff| <= max_edit
        L = len(token)
        for v in self.vocab:
            if abs(len(v) - L) > self.max_edit:
                continue
            d = _lev(token, v, self.max_edit)
            if d <= self.max_edit:
                f = self.uni_freq[v]
                # prefer lower distance, then higher frequency
                rank = (d, -f, v)
                if rank < (best[0], best[1] * -1, best[2]):
                    best = (d, f, v)
        return best[2] if best[0] <= self.max_edit else token

    def correct_tokens(self, text: str) -> list[str]:
        toks = [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]
        return [self._best_vocab_match(t) for t in toks]

    def _dominant_next(self, prefix: tuple[str, ...]) -> str | None:
        cnt = self.next_map.get(prefix)
        if not cnt:
            return None
        total = sum(cnt.values())
        nxt, c = max(cnt.items(), key=lambda kv: kv[1])
        if c >= self.min_prefix_freq and (total == 0 or (c / total) >= self.next_token_dominance):
            return nxt
        return None

    def expand_phrases(self, tokens: list[str], max_append: int = 6) -> list[str]:
        """
        Aggressive expansion: if we see a frequent prefix (2- or 3-gram),
        keep appending the dominant next token while thresholds hold.
        Also map short tails like 'OK' -> 'I ORDEN'.
        """
        out = []
        i = 0
        n = len(tokens)
        while i < n:
            out.append(tokens[i])

            # small tail expansion first (e.g., OK -> I ORDEN)
            if tokens[i] in self.tail_expansions:
                out.pop()
                out.extend(self.tail_expansions[tokens[i]])
                i += 1
                continue

            # try expanding from 3-gram or 2-gram prefix ending at current position
            appended = 0
            while appended < max_append:
                prefix3 = tuple(out[-3:]) if len(out) >= 3 else None
                prefix2 = tuple(out[-2:]) if len(out) >= 2 else None
                nxt = None
                if prefix3:
                    nxt = self._dominant_next(prefix3)
                if nxt is None and prefix2:
                    nxt = self._dominant_next(prefix2)
                if nxt is None:
                    break
                # Avoid runaway loops: don't repeat if already the next input token matches
                out.append(nxt)
                appended += 1
            i += 1
        return out

    def correct_and_expand(self, text: str) -> str:
        toks = self.correct_tokens(text)
        toks = self.expand_phrases(toks)
        return " ".join(toks)
# --- END NEW -----------------------------------------------------------------

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
