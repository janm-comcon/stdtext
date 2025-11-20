# -*- coding: utf-8 -*-
import json
import re
from typing import Tuple, Dict
from pathlib import Path

# Abbreviation pattern: 2-3 letters + dot (e.g. stk., osv., udv.)
ABBR_EXTRACT_RE = re.compile(r"\b([A-Za-zÆØÅæøå]{2,3})\.", flags=re.IGNORECASE)

# Optional abbreviation whitelist
ABBREV_LIST = set()
try:
    p = Path("C:/Temp/abbrev_map.json")
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        ABBREV_LIST = set(k.lower() for k in data.keys())
except Exception:
    ABBREV_LIST = set()

# Number pattern used for scrubber (not for runtime rewrite)
NUM_RE = re.compile(r"\b\d+[.,]?\d*(?:[xX*/-]\d+[.,]?\d*)*\b")


def simple_normalize(text: str) -> str:
    """Lowercase and collapse whitespace, but keep abbreviations intact."""
    if not text:
        return ""

    text = str(text)
    text = text.strip()
    text = text.replace("\t", " ")
    text = " ".join(text.split())

    raw_tokens = text.split()
    out_tokens = []

    for tok in raw_tokens:
        tok_low = tok.lower()

        # Known abbreviation
        if tok_low in ABBREV_LIST:
            out_tokens.append(tok_low)
            continue

        # 2–3 letters + dot -> abbreviation
        if len(tok_low) <= 4 and tok_low.endswith(".") and tok_low[:-1].isalpha():
            out_tokens.append(tok_low)
            continue

        cleaned = tok_low.strip(",;:!?()[]{}")
        if cleaned:
            out_tokens.append(cleaned)

    return " ".join(out_tokens)


def extract_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace abbreviations with <ABBR_xxxx> placeholders."""
    mapping: Dict[str, str] = {}
    i = 0

    def repl(m):
        nonlocal i
        i += 1
        key = f"ABBR_{i:04d}"
        mapping[key] = m.group(1) + "."
        return f"<{key}>"

    new_text = ABBR_EXTRACT_RE.sub(repl, text)
    return new_text, mapping


def reinsert_placeholders(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for k, v in mapping.items():
        out = out.replace(f"<{k}>", v)
    return out


def remove_sensitive(text: str, keep_room_words: bool = True) -> str:
    """Remove bare numbers (used in training scrubber, not rewrite)."""
    t = NUM_RE.sub(" ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t
