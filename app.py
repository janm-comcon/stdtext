# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pathlib import Path
import yaml
from typing import List, Dict, Any, Optional

from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper
from stdtext.count_utils import extract_counts_structured, format_count_phrase

from stdtext.rules.patterns import apply_rewrite_patterns
from stdtext.rules.actions import apply_action_rules

try:
    from openai import OpenAI
except ImportError:  # OpenAI is optional
    OpenAI = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "stdtext" / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

app = FastAPI(title="StdText Rule-Based + OpenAI Rewrite Service")

# Spell checker initialized once
spell = SpellWrapper()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RewriteIn(BaseModel):
    text: str = Field(..., description="Raw invoice line")
    use_openai: bool = Field(
        False, description="Force OpenAI even if disabled in config"
    )


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
    text: str, stages: Optional[Dict[str, Any]] = None
) -> str:
    """
    Pure rule-based pipeline, no OpenAI.

    If a `stages` dict is provided, it will be populated with intermediate
    results for debugging purposes.
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

    # 8) uppercase final
    if CFG.get("output", {}).get("uppercase", True):
        out = out.upper()

    stages["final_rule_based"] = out
    return out


# ---------------------------------------------------------------------------
# OpenAI helper
# ---------------------------------------------------------------------------

def openai_enhance(text_in: str, draft: str, stages: Dict[str, Any]) -> str:
    """
    Optionally call OpenAI to polish the rule-based rewrite.
    Safe to call even when OpenAI is not configured.
    """
    if not CFG.get("openai", {}).get("enabled", False):
        return draft
    if OpenAI is None:
        return draft

    api_key = CFG.get("openai", {}).get("api_key")
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

    # Fallback to the rule-based draft on any error
    return draft


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "openai_enabled": CFG.get("openai", {}).get("enabled", False),
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

    Runs the rule-based pipeline, and optionally lets OpenAI polish the result
    if enabled in the config or explicitly requested.
    """
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
    """
    Debug endpoint: always returns the pure rule-based pipeline output
    plus all intermediate stages. Never calls OpenAI.
    """
    stages: Dict[str, Any] = {}
    final = rule_based_rewrite(payload.text, stages)
    stages["final"] = final
    return {"rewrite": final, "stages": stages}
