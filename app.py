# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

import sys
sys.path.insert(1, "./stdtext")

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders, remove_sensitive
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper
from stdtext.model import CorpusCorrector

CONFIG_PATH = Path(__file__).parent / "stdtext" / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text())

ART = Path(CFG["paths"]["artifacts"])
ART.mkdir(exist_ok=True, parents=True)

spell = SpellWrapper(da_dictionary_path=CFG["paths"]["da_dictionary"])

corrector = None
if (ART / "vectorizer.pkl").exists():
    try:
        corrector = CorpusCorrector.load(ART)
    except Exception:
        corrector = None

app = FastAPI(title="StdText Production v3")

class RewriteIn(BaseModel):
    text: str = Field(...)
    top_k: int = Field(3, ge=1, le=10)

class RewriteOut(BaseModel):
    rewrite: str
    nearest_examples: list[str]

class SpellIn(BaseModel):
    text: str

class SpellOut(BaseModel):
    original: str
    corrected: str
    suggestions: dict

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": bool(corrector is not None)
    }

@app.post("/check_spelling", response_model=SpellOut)
def check_spelling(payload: SpellIn):
    t = payload.text or ""
    norm = simple_normalize(t)
    t1, map_abbr = extract_placeholders(norm)
    t2, map_ent = extract_entities(t1)
    toks = []
    suggestions = {}
    for tok in t2.split():
        if tok.startswith("<") and tok.endswith(">"):
            toks.append(tok)
            continue
        corr = spell.correction(tok)
        toks.append(corr)
        sugg = spell.suggestions(tok)
        if sugg:
            suggestions[tok] = sugg[:5]
    corrected = " ".join(toks)
    return {
        "original": t,
        "corrected": corrected,
        "suggestions": suggestions
    }

@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):
    from stdtext.count_utils import (
        extract_counts_structured,
        format_count_phrase,
    )

    global corrector

    text = payload.text or ""

    # 1) Basic normalization
    norm = simple_normalize(text)

    # 2) Abbreviation placeholders
    t1, map_abbr = extract_placeholders(norm)

    # 3) Entity placeholders (names, addresses, companies, etc.)
    t2, map_ent = extract_entities(t1)

    # Base mapping
    base_map = {**map_abbr, **map_ent}

    # 4) Remove sensitive numbers — COUNT will be handled separately
    cleaned = remove_sensitive(t2, keep_room_words=True)

    # 5) Spell-correct (but skip placeholders)
    raw_tokens = cleaned.split()
    corrected_tokens = []
    for tok in raw_tokens:
        if tok.startswith("<") and tok.endswith(">"):
            corrected_tokens.append(tok)
        else:
            corrected_tokens.append(spell.correction(tok))

    # 6) COUNT extraction (after spell correct)
    count_tokens, count_mapping = extract_counts_structured(corrected_tokens)

    # Merge mappings
    mapping = {
        **base_map,
        **count_mapping
    }

    corrected_text = " ".join(count_tokens)

    # 7) corpus corrector
    examples = []
    final = corrected_text
    if corrector is not None:
        examples = corrector.query(corrected_text, top_k=payload.top_k)
        if examples:
            final = examples[0]

    # 8) Reinsertion order:
    #   entities → abbreviations → COUNT phrases → uppercase
    out = final

    # 1) entities
    out = reinsert_entities(out, map_ent)

    # 2) abbreviations
    out = reinsert_placeholders(out, map_abbr)

    # 3) COUNT phrases — with normalized order (2 stk. lamper)
    for key, info in count_mapping.items():
        phrase = format_count_phrase(info)
        out = out.replace(f"<{key}>", phrase)

    # 4) UPPERCASE final style if configured
    if CFG["output"].get("uppercase", True):
        out = out.upper()

    return {
        "rewrite": out,
        "nearest_examples": examples
    }

@app.post("/reload_artifacts")
def reload_artifacts():
    global corrector
    import pandas as pd
    src = Path(CFG["paths"]["corrected_csv"])
    if not src.exists():
        src = Path(CFG["paths"]["scrubbed_csv"])
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"Source CSV not found: {src}")
    df = pd.read_csv(src, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    texts = df[text_col].astype(str).tolist()
    if CFG["model"].get("lowercase_training", True):
        texts = [x.lower() for x in texts]
    corrector = CorpusCorrector(texts=texts)
    corrector.save(ART)
    return {"status": "reloaded", "records": len(texts)}
