# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, Field

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders
from stdtext.count_utils import extract_counts_structured, format_count_phrase
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper

from stdtext.rules.patterns import apply_rewrite_patterns
from stdtext.rules.actions import apply_action_rules

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "stdtext" / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

app = FastAPI(title="StdText Rule-Based Rewrite Service")

# Spell checker initialized once
spell = SpellWrapper()

# DaCy and LanguageTool are optional but preferred
try:
    import dacy

    DACY_MODEL_NAME = "da_dacy_small_trf-0.2.0"
    nlp = dacy.load(DACY_MODEL_NAME)
except Exception as exc:
    print("Failed to load DaCy model. Using placeholder-only lemmatization.")
    print("Error:", exc)  
    nlp = None

try:
    import language_tool_python

    lt_lang = CFG.get("language_tool", {}).get("language", "da-DK")
    lt = language_tool_python.LanguageTool(lt_lang)
except Exception as exc:
    print("Failed to load LanguageTool. Using placeholder-only grammar/spell checks.")
    print("Error:", exc)  
    lt = None

PLACEHOLDER_RE = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RewriteIn(BaseModel):
    text: str = Field(..., description="Raw invoice line")


class RewriteOut(BaseModel):
    rewrite: str
    stages: Dict[str, Any]


class DebugIn(BaseModel):
    text: str


class SpellIn(BaseModel):
    text: str


class SpellOut(BaseModel):
    original: str
    corrected: str
    suggestions: Dict[str, List[str]]


# ---------------------------------------------------------------------------
# Core rule-based pipeline
# ---------------------------------------------------------------------------

def rule_based_rewrite(
    text: str, stages: Optional[Dict[str, Any]] = None, uppercase: bool = True
) -> str:
    """
    Pure rule-based pipeline.

    If a `stages` dict is provided, it will be populated with intermediate
    results for debugging purposes. Uppercasing can be toggled for downstream
    refinement steps.
    """
    if stages is None:
        stages = {}

    # 1) normalize
    norm = simple_normalize(text or "")
    stages["normalized"] = norm

    # 2a) action expansion (domain-specific replacements)
    expanded = apply_action_rules(norm)
    stages["action_expanded"] = expanded

    # 2b) abbreviations -> placeholders
    t1, map_abbr = extract_placeholders(expanded)
    stages["abbr_placeholders"] = t1
    stages["abbr_map"] = map_abbr

    # 3) entities -> placeholders
    t2, map_ent = extract_entities(t1)
    stages["entities_placeholders"] = t2
    stages["entities_map"] = map_ent

    # 4) spell-correct tokens except placeholders
    raw_tokens = t2.split()
    corrected_tokens: List[str] = []
    for tok in raw_tokens:
        if tok.startswith("<") and tok.endswith(">"):
            corrected_tokens.append(tok)
        else:
            corrected_tokens.append(spell.correction(tok))

    stages["spell_corrected_tokens"] = corrected_tokens

    # 5) COUNT extraction
    count_tokens, count_mapping = extract_counts_structured(corrected_tokens)
    stages["count_tokens"] = count_tokens
    stages["count_mapping"] = count_mapping

    text_with_counts = " ".join(count_tokens)
    stages["text_with_counts"] = text_with_counts

    # 6) rule-based patterns (ACTION AF OBJECT [LOCATION])
    rule_text = apply_rewrite_patterns(count_tokens)
    stages["rule_text"] = rule_text

    # 7) reinsertion: entities -> abbreviations -> COUNT
    out = reinsert_entities(rule_text, map_ent)
    out = reinsert_placeholders(out, map_abbr)

    for key, info in count_mapping.items():
        phrase = format_count_phrase(info)
        out = out.replace(f"<{key}>", phrase)

    stages["reinserted"] = out

    # 8) uppercase final if requested
    if uppercase and CFG.get("output", {}).get("uppercase", True):
        out = out.upper()

    stages["final_rule_based"] = out
    return out


# ---------------------------------------------------------------------------
# DaCy + LanguageTool helpers
# ---------------------------------------------------------------------------

def _mask_placeholders(text: str):
    mapping: Dict[str, str] = {}

    def repl(match: re.Match[str]):
        key = f"PH_{len(mapping):04d}"
        mapping[key] = match.group(0)
        return key

    masked = PLACEHOLDER_RE.sub(repl, text)
    return masked, mapping


def _unmask_placeholders(text: str, mapping: Dict[str, str]):
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def dacy_refine(text: str, stages: Dict[str, Any]) -> str:
    """Use DaCy lemmatization to smooth wording while preserving placeholders."""
    if nlp is None:
        return text

    doc = nlp(text)
    tokens: List[str] = []
    for tok in doc:
        if PLACEHOLDER_RE.fullmatch(tok.text):
            tokens.append(tok.text)
            continue
        lemma = tok.lemma_.lower()
        if lemma == "-pron-":
            lemma = tok.text.lower()
        tokens.append(lemma)

    stages["dacy_tokens"] = tokens
    refined = " ".join(tokens)
    stages["dacy_refined"] = refined
    return refined


def language_tool_refine(text: str, stages: Dict[str, Any]) -> str:
    """Run LanguageTool corrections without disturbing placeholders."""
    if lt is None:
        return text

    masked, mapping = _mask_placeholders(text)
    try:
        matches = lt.check(masked)
        stages["language_tool_matches"] = [m.ruleId for m in matches]
        corrected = language_tool_python.utils.correct(masked, matches)
    except Exception as exc:
        stages["language_tool_error"] = str(exc)
        return text

    unmasked = _unmask_placeholders(corrected, mapping)
    stages["language_tool_refined"] = unmasked
    return unmasked


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "dacy_ready": nlp is not None,
        "language_tool_ready": lt is not None,
        "spell_ready": spell is not None,
    }


@app.post("/check_spelling", response_model=SpellOut)
def check_spelling(payload: SpellIn):
    """
    Spell-check endpoint that preserves the placeholder / entity logic.
    """
    t = payload.text or ""
    norm = simple_normalize(t)
    t1, _ = extract_placeholders(norm)
    t2, _ = extract_entities(t1)

    tokens: List[str] = []
    suggestions: Dict[str, List[str]] = {}

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
        "suggestions": suggestions,
    }


@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):
    """
    Main rewrite endpoint.

    Runs the rule-based pipeline, then refines the text using
    DaCy lemmatization and LanguageTool grammar/spell checks.
    """
    stages: Dict[str, Any] = {}
    rule = rule_based_rewrite(payload.text, stages, uppercase=False)

    refined = dacy_refine(rule, stages)
    polished = language_tool_refine(refined, stages)

    if CFG.get("output", {}).get("uppercase", True):
        polished = polished.upper()

    stages["final"] = polished
    return {"rewrite": polished, "stages": stages}


@app.post("/debug_rewrite", response_model=RewriteOut)
def debug_rewrite(payload: DebugIn):
    """
    Debug endpoint: always returns the pure rule-based pipeline output
    plus all intermediate stages. Skips DaCy/LanguageTool refinements.
    """
    stages: Dict[str, Any] = {}
    final = rule_based_rewrite(payload.text, stages)
    stages["final"] = final
    return {"rewrite": final, "stages": stages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
    )
