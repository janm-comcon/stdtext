# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pathlib import Path
import os
import yaml
from typing import List, Dict, Any

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper
from stdtext.count_utils import extract_counts_structured, format_count_phrase

from stdtext.rules.patterns import apply_rewrite_patterns
from stdtext.rules.actions import apply_action_rules

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

CONFIG_PATH = Path(__file__).parent / "stdtext" / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

app = FastAPI(title="StdText Rule-Based + OpenAI Rewrite Service")

spell = SpellWrapper()

global corrector

class RewriteIn(BaseModel):
    text: str = Field(..., description="Raw invoice line")
    use_openai: bool = Field(False, description="Force OpenAI even if disabled in config")


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


def rule_based_rewrite(text: str, stages: Dict[str, Any]) -> str:
    """Pure rule-based pipeline, no OpenAI."""

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
    text = payload.text

    stages = {}

    # 1) normalize
    norm = simple_normalize(text)
    stages["normalized"] = norm

    # 2a) action expansion
    expanded = apply_action_rules(norm)
    stages["action_expanded"] = expanded

    # 2) abbreviations
    t1, map_abbr = extract_placeholders(expanded)
    stages["abbr_placeholders"] = t1
    stages["abbr_map"] = map_abbr

    # 3) entities
    t2, map_ent = extract_entities(t1)
    stages["entities_placeholders"] = t2
    stages["entities_map"] = map_ent

    # 4) spell-correct
    raw_tokens = t2.split()
    corrected_tokens = []
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

    # 8) uppercase final
    if CFG.get("output", {}).get("uppercase", True):
        out = out.upper()
    stages["final_rule_based"] = out
    stages["reinsert"] = out

    return stages


@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):

    text = payload.text or ""

    # 1) normalize
    norm = simple_normalize(text)

    # 2a) action expansion
    expanded = apply_action_rules(norm)

    # 2) abbreviations
    t1, map_abbr = extract_placeholders(expanded)

    # 3) entities
    t2, map_ent = extract_entities(t1)

    # 4) spell-correct
    raw_tokens = t2.split()
    corrected_tokens = []
    for tok in raw_tokens:
        if tok.startswith("<") and tok.endswith(">"):
            corrected_tokens.append(tok)
        else:
            corrected_tokens.append(spell.correction(tok))

    # 5) COUNT extraction
    count_tokens, count_mapping = extract_counts_structured(corrected_tokens)

    text_with_counts = " ".join(count_tokens)

    # 6) rule-based patterns (ACTION AF OBJECT [LOCATION])
    rule_text = apply_rewrite_patterns(count_tokens)

    # 7) reinsertion: entities -> abbreviations -> COUNT
    out = reinsert_entities(rule_text, map_ent)
    out = reinsert_placeholders(out, map_abbr)

    for key, info in count_mapping.items():
        phrase = format_count_phrase(info)
        out = out.replace(f"<{key}>", phrase)

    # 8) uppercase final
    if CFG.get("output", {}).get("uppercase", True):
        out = out.upper()

    return out


def openai_enhance(text_in: str, draft: str, stages: Dict[str, Any]) -> str:
    """Optionally call OpenAI to polish the rule-based rewrite."""
    if not CFG.get("openai", {}).get("enabled", False):
        return draft
    if OpenAI is None:
        return draft

    api_key =  CFG.get("openai", {}).get("api_key")
    if not api_key:
        return draft

    client = OpenAI(api_key=api_key)

    model = CFG["openai"].get("model", "gpt-5.1-chat-latest")
    reasoning_effort = CFG["openai"].get("reasoning_effort", "none")

    prompt = (
        "Du er en dansk tekst-normaliseringsassistent for fakturalinjer.\n"
        "Du får en original tekst og et udkast fra en regelbaseret motor.\n"
        "Din opgave er KUN at lave små justeringer for at gøre teksten mere naturlig,\n"
        "men du må ikke ændre betydning, antal, datoer eller stednavne.\n"
        "Returnér KUN én linje i HELT UPPERCASE, uden forklaring.\n\n"
        f"ORIGINAL: {text_in}\n"
        f"UDKAST: {draft}\n"
        "SVAR:"
    )

    try:
        # Use Responses API if available, else chat completions
        if hasattr(client, "responses"):
            resp = client.responses.create(
                model=model,
                # reasoning={"effort": reasoning_effort},
                input=prompt,
            )
            out_text = ""
            for item in resp.output:
                if hasattr(item, "content"):
                    for c in item.content:
                        if hasattr(c, "text"):
                            out_text += c.text
        else:
            chat = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            out_text = chat.choices[0].message.content

        out_text = (out_text or "").strip()
        stages["openai_output"] = out_text
        if out_text:
            return out_text
    except Exception as e:
        stages["openai_error"] = str(e)

    return draft


@app.get("/health")
def health():
    return {
        "status": "ok",
        "openai_enabled": CFG.get("openai", {}).get("enabled", False),
    }


@app.post("/check_spelling", response_model=SpellOut)
def check_spelling(payload: SpellIn):
    text = payload.text or ""
    norm = simple_normalize(text)
    tokens = norm.split()
    corrected = []
    suggestions = {}
    for tok in tokens:
        corr = spell.correction(tok)
        corrected.append(corr)
        s = spell.suggestions(tok)
        if s:
            suggestions[tok] = s[:5]
    return {
        "original": text,
        "corrected": " ".join(corrected),
        "suggestions": suggestions,
    }


@app.post("/rewrite", response_model=RewriteOut)
def rewrite(payload: RewriteIn):
    stages: Dict[str, Any] = {}
    rule = rule_based_rewrite(payload.text, stages)
    use_openai = payload.use_openai or CFG.get("openai", {}).get("enabled", False)
    if use_openai:
        final = openai_enhance(payload.text, rule, stages)
    else:
        final = rule
    stages["final"] = final
    return {"rewrite": final, "stages": stages}


@app.post("/debug_rewrite", response_model=RewriteOut)
def debug_rewrite(payload: DebugIn):
    stages: Dict[str, Any] = {}
    rule = rule_based_rewrite(payload.text, stages)
    # Do NOT call OpenAI in debug by default
    stages["final"] = rule
    return {"rewrite": rule, "stages": stages}
