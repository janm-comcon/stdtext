# -*- coding: utf-8 -*-
import uvicorn
import json, joblib, pandas as pd, re, threading
from fastapi import FastAPI, HTTPException, Body
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from invoice_styler import InvoiceStyler
from corpus_corrector import CorpusCorrector
from spell import spell, get_spell_dictionary_size


HERE = Path(__file__).parent
ART = HERE / "artifacts"

# === CONFIG: RAW MASTER CSV PATH (Windows absolute path) ===
RAW_MASTER_CSV = r"C:\Temp\text_scrubbed.csv"

class RewriteIn(BaseModel):
    text: str = Field(...)
    top_k: int = Field(3, ge=1, le=10)

class RewriteOut(BaseModel):
    rewrite: str
    nearest_examples: list[str]

app = FastAPI(title="Invoice Style Service", version="1.1.0")

# Concurrency guard for reload
_reload_lock = threading.Lock()

def _clean_text(s: str) -> str:
    if not isinstance(s, str): s = str(s)
    s = s.replace('\r\n',' ').replace('\n',' ').replace('\r',' ')
    s = re.sub(r'\s+',' ', s).strip()
    s = s.upper().replace(',', '.')
    s = re.sub(r'\s*[\.\u2026]+\s*', '. ', s)
    s = re.sub(r'\s+',' ', s).strip()
    s = re.sub(r'(\.\s*){2,}', '. ', s)
    return s

# Load cached artifacts once at startup
_vectorizer = joblib.load(ART / "vectorizer.pkl")
_kmeans    = joblib.load(ART / "kmeans.pkl")
_nn        = joblib.load(ART / "nn.pkl")
_cleaned   = pd.read_csv(ART / "cleaned.csv")

# Build corrector from cleaned corpus
_corrector = CorpusCorrector(_cleaned['text'].astype(str).tolist(), max_edit=2)

class CachedStyler(InvoiceStyler):
    @classmethod
    def from_artifacts(cls, cleaned_df, vectorizer, kmeans, nn, corrector=None):
        obj = object.__new__(cls)
        obj.df = cleaned_df.copy()
        obj.vectorizer = vectorizer
        obj.kmeans = kmeans
        obj.nn = nn
        obj.corrector = corrector
        return obj

styler = CachedStyler.from_artifacts(_cleaned, _vectorizer, _kmeans, _nn, _corrector)

class SpellCheckIn(BaseModel):
    text: str = Field(..., example="monterig af lamppu i køken ok")

class SpellCheckOut(BaseModel):
    original: str
    corrected: str
    suggestions: Dict[str, List[str]]
    dictionary_size: Optional[int] = None

@app.post("/check_spelling", response_model=SpellCheckOut, summary="Spell-check input text")
def check_spelling(payload: SpellCheckIn):
    """
    Runs the general spell-checker on the provided text and returns
    corrected output + alternative suggestions for each token.
    """
    text = payload.text.strip()
    if not text:
        return SpellCheckOut(original="", corrected="", suggestions={}, dictionary_size=None)

    toks = text.split()
    suggestions = {}
    corrected_tokens = []

    for t in toks:
        corr = spell.correction(t) or t
        corrected_tokens.append(corr)
        # collect suggestions (candidates) if available
        try:
            cand = spell.candidates(t)
            if len(cand) > 1 or corr != t:
                suggestions[t] = list(cand)[:5]
        except Exception:
            pass

    corrected = " ".join(corrected_tokens)
    dictionary_size = get_spell_dictionary_size(spell)

    return SpellCheckOut(
        original=text,
        corrected=corrected,
        suggestions=suggestions,
        dictionary_size=dictionary_size
    )

@app.get("/health")
def health():
    meta_path = ART / "model_meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {}
    return {
        "status": "ok",
        "model": meta,
        "records": int(styler.df.shape[0]),
        "python": __import__("sys").version,
        "sklearn": __import__("sklearn").__version__,
        "source_raw_csv": RAW_MASTER_CSV,
        "correction": {"enabled": True, "max_edit": 2}
    }

@app.get("/representatives")
def representatives():
    reps = styler.representatives()
    return {"count": int(reps.shape[0]), "representatives": [{"cluster": int(r.cluster), "text": r.text} for _, r in reps.iterrows()]}

@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):
    # let the styler handle correction internally; nothing else to do
    styled, matches = styler.rewrite(payload.text, top_k=payload.top_k)
    return {"rewrite": styled, "nearest_examples": matches[:payload.top_k]}

@app.post("/reload_artifacts")
def reload_artifacts():
    """
    OPEN endpoint: rebuild artifacts from RAW_MASTER_CSV and hot-swap models.
    """
    with _reload_lock:
        raw_path = Path(RAW_MASTER_CSV)
        if not raw_path.exists():
            raise HTTPException(status_code=404, detail=f"RAW_MASTER_CSV not found: {RAW_MASTER_CSV}")
        # Read raw CSV (semicolon separated)
        df_raw = pd.read_csv(raw_path, sep=';', engine='python', header=0, encoding='utf-8', on_bad_lines='skip')
        # Heuristic: choose text column
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
        df['text'] = df[text_col].astype(str).map(_clean_text)
        df = df[df['text'].str.strip().ne('')].drop_duplicates(subset=['text']).reset_index(drop=True)
        # Refit models
        vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=2)
        X = vectorizer.fit_transform(df['text'])
        k = min(8, max(2, X.shape[0]//10)) or 4
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        nn = NearestNeighbors(n_neighbors=min(5, X.shape[0]), metric='cosine').fit(X)
        # Persist artifacts
        df[['text']].to_csv(ART / "cleaned.csv", index=False, encoding='utf-8')
        joblib.dump(vectorizer, ART / "vectorizer.pkl")
        joblib.dump(kmeans,   ART / "kmeans.pkl")
        joblib.dump(nn,       ART / "nn.pkl")
        (ART / "model_meta.json").write_text(json.dumps({
            "built_at": "hot reload",
            "source_raw": RAW_MASTER_CSV,
            "records": int(df.shape[0]),
            "model_version": "v1"
        }, indent=2), encoding="utf-8")
        # Hot-swap in-memory
        global styler, _vectorizer, _kmeans, _nn, _cleaned, _corrector
        _vectorizer, _kmeans, _nn = vectorizer, kmeans, nn
        _cleaned = df[['text']].copy()
        _corrector = CorpusCorrector(_cleaned['text'].astype(str).tolist(), max_edit=2)
        styler = CachedStyler.from_artifacts(_cleaned, _vectorizer, _kmeans, _nn, _corrector)
        return {"status": "reloaded", "records": int(df.shape[0]), "k": int(k)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)