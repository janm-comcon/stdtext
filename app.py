# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders, remove_sensitive
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper
from stdtext.count_utils import extract_counts_structured, format_count_phrase
from stdtext.model import CorpusCorrector

CONFIG_PATH = Path(__file__).parent / "stdtext" / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

ART = Path(CFG["paths"]["artifacts"])
ART.mkdir(exist_ok=True, parents=True)

spell = SpellWrapper(da_dictionary_path=CFG["paths"]["da_dictionary"],
                     abbrev_map_path=CFG["paths"]["abbrev_map"])

corrector = None
if (ART / "vectorizer.pkl").exists():
    try:
        corrector = CorpusCorrector.load(ART)
    except Exception:
        corrector = None

app = FastAPI(title="StdText Production v4")

class RewriteIn(BaseModel):
    text: str = Field(..., description="Raw invoice text")
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

    tokens = []
    suggestions = {}

    for tok in t2.split():
        if tok.startswith("<") and tok.endswith(">"):
            tokens.append(tok)
            continue
        corr = spell.correction(tok)
        tokens.append(corr)
        s = spell.suggestions(tok)
        if s:
            suggestions[tok] = s[:5]

    corrected = " ".join(tokens)
    return {
        "original": t,
        "corrected": corrected,
        "suggestions": suggestions
    }

@app.post("/debug_rewrite")
def debug_rewrite(payload: RewriteIn):
    from stdtext.count_utils import extract_counts_structured, format_count_phrase

    text_in = payload.text

    stages = {}

    # 1 Normalize
    norm = simple_normalize(text_in)
    stages["normalize"] = norm

    # 2 Abbreviations
    t1, map_abbr = extract_placeholders(norm)
    stages["placeholders"] = t1
    stages["placeholder_map"] = map_abbr

    # 3 Entities
    t2, map_ent = extract_entities(t1)
    stages["entities"] = t2
    stages["entity_map"] = map_ent

    # 4 Remove numbers
    t3 = remove_sensitive(t2, keep_room_words=True)
    stages["remove_numbers"] = t3

    # 5 Spell correction
    raw_tokens = t3.split()
    corr = []
    for tok in raw_tokens:
        if tok.startswith("<") and tok.endswith(">"):
            corr.append(tok)
        else:
            corr.append(spell.correction(tok))
    corrected = " ".join(corr)
    stages["spell_correct"] = corrected

    # 6 COUNT extraction
    count_tokens, count_info = extract_counts_structured(corr)
    t4 = " ".join(count_tokens)
    stages["count_extract"] = t4
    stages["count_info"] = count_info

    # 7 Corpus correction
    if corrector:
        examples = corrector.query(t4, 3)
        stages["corpus_examples"] = examples
        final = examples[0] if examples else t4
    else:
        stages["corpus_examples"] = []
        final = t4
    stages["corpus_corrected"] = final

    # 8 Reinsertion
    out = reinsert_entities(final, map_ent)
    out = reinsert_placeholders(out, map_abbr)
    for key, info in count_info.items():
        phrase = format_count_phrase(info)
        out = out.replace(f"<{key}>", phrase)
    stages["reinsert"] = out

    return stages


@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):
    global corrector

    text_in = payload.text or ""

    # 1) normalize
    norm = simple_normalize(text_in)

    # 2) abbreviations
    t1, map_abbr = extract_placeholders(norm)

    # 3) entities
    t2, map_ent = extract_entities(t1)

    # 4) remove sensitive numbers
    cleaned = remove_sensitive(t2, keep_room_words=True)

    # 5) spell-correct
    raw_tokens = cleaned.split()
    corrected_tokens = []
    for tok in raw_tokens:
        if tok.startswith("<") and tok.endswith(">"):
            corrected_tokens.append(tok)
        else:
            corrected_tokens.append(spell.correction(tok))

    # 6) COUNT extraction
    count_tokens, count_mapping = extract_counts_structured(corrected_tokens)
    corrected_text = " ".join(count_tokens)

    # 7) corpus corrector
    final = corrected_text
    examples = []
    if corrector is not None:
        examples = corrector.query(corrected_text, top_k=payload.top_k)
        if examples:
            final = examples[0]

    # 8) reinsertion: entities -> abbreviations -> COUNT
    out = reinsert_entities(final, map_ent)
    out = reinsert_placeholders(out, map_abbr)
    for key, info in count_mapping.items():
        phrase = format_count_phrase(info)
        out = out.replace(f"<{key}>", phrase)

    # 9) UPPERCASE
    if CFG["output"].get("uppercase", True):
        out = out.upper()

    return {"rewrite": out, "nearest_examples": examples}


@app.post("/reload_artifacts")
def reload_artifacts():
    """Reload or create artifacts from scratch using corrected CSV."""
    global corrector
    import pandas as pd

    src = Path(CFG["paths"]["corrected_csv"])
    if not src.exists():
        src = Path(CFG["paths"]["scrubbed_csv"])
    if not src.exists():
        return {"status": "error", "detail": f"Source CSV not found: {src}"}

    df = pd.read_csv(src, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    texts = df[text_col].astype(str).tolist()
    if CFG["model"].get("lowercase_training", True):
        texts = [t.lower() for t in texts]

    corrector = CorpusCorrector(texts=texts)
    corrector.save(ART)
    return {"status": "reloaded", "records": len(texts)}
