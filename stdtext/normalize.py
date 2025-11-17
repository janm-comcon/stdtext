# -*- coding: utf-8 -*-
import json
import re
from typing import Tuple, Dict
from pathlib import Path

# --- Abbreviation handling -----------------------------------------------------

# Match abbreviations like: 2–3 letters + dot
ABBR_EXTRACT_RE = re.compile(r'\b([A-Za-zÆØÅæøå]{2,3})\.', flags=re.IGNORECASE)

# General abbreviation whitelist (from abbrev_builder.py)
ABBREV_LIST = set()
try:
    p = Path("C:/Temp/abbrev_map.json")
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        ABBREV_LIST = set(k.lower() for k in data.keys())
except Exception:
    ABBREV_LIST = set()

# --- Number removal used for scrubber -----------------------------------------
NUM_RE = re.compile(r'\b\d+[.,]?\d*(?:[xX*/-]\d+[.,]?\d*)*\b')


# ==============================================================================
# SIMPLE NORMALIZE: preserve abbreviations
# ==============================================================================
def simple_normalize(text: str) -> str:
    """
    Lowercase and collapse whitespace, but KEEP abbreviations:
    - 'stk.', 'udv.', 'osv.', 'vvs.' etc.
    - Any token in ABBREV_LIST
    - Any 2–3 letter abbreviation ending with '.'
    """
    if not text:
        return ""

    # Basic cleanup
    text = text.strip()
    text = text.replace("\t", " ")
    text = " ".join(text.split())

    raw_tokens = text.split()
    out_tokens = []

    for tok in raw_tokens:
        tok_low = tok.lower()

        # 1. Whitelist abbreviation?
        if tok_low in ABBREV_LIST:
            out_tokens.append(tok_low)
            continue

        # 2. Matches generic abbreviation pattern?
        if len(tok_low) <= 4 and tok_low.endswith(".") and tok_low[:-1].isalpha():
            out_tokens.append(tok_low)
            continue

        # 3. Normal token cleaning for everything else
        cleaned = tok_low.strip(",;:!?()[]{}")
        if cleaned:
            out_tokens.append(cleaned)

    return " ".join(out_tokens)


# ==============================================================================
# ABBREVIATION PLACEHOLDER EXTRACTION
# (used BEFORE spell correction)
# ==============================================================================
def extract_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace abbreviations with placeholders like <ABBR_0001>
    """
    mapping: Dict[str, str] = {}
    i = 0

    def repl(m):
        nonlocal i
        i += 1
        key = f"ABBR_{i:04d}"
        mapping[key] = m.group(1) + "."   # preserve dot
        return f"<{key}>"

    new_text = ABBR_EXTRACT_RE.sub(repl, text)
    return new_text, mapping


def reinsert_placeholders(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for k, v in mapping.items():
        out = out.replace(f"<{k}>", v)
    return out


# ==============================================================================
# REMOVE SENSITIVE NUMBERS (for scrubber)
# ==============================================================================
def remove_sensitive(text: str, keep_room_words: bool = True) -> str:
    """
    Remove explicit numbers unless part of known placeholders.
    Used in training scrubbing, not rewrite.
    """
    t = NUM_RE.sub(" ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t
