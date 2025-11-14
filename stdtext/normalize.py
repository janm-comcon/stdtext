# -*- coding: utf-8 -*-
import re
from typing import Tuple, Dict
from stdtext.entity_scrubber import extract_entities, reinsert_entities

ABBR_RE = re.compile(r'\b([A-Za-zÆØÅæøå]{2,3})\.', flags=re.IGNORECASE)
NUM_RE = re.compile(r'\b\d+[.,]?\d*(?:[xX*/-]\d+[.,]?\d*)*\b')

def simple_normalize(text: str) -> str:
    if text is None:
        return ""
    t = str(text)
    t = t.replace("\r"," ").replace("\n"," ").replace("\\r"," ").replace("\\n"," ")
    t = re.sub(r"[;:]+", ".", t)
    t = re.sub(r"\s+", " ", t)
    return t.lower().strip()

def extract_placeholders(text: str) -> Tuple[str, Dict[str,str]]:
    mapping: Dict[str,str] = {}
    i = 0
    def repl(m):
        nonlocal i
        i += 1
        key = f"ABBR_{i:04d}"
        mapping[key] = m.group(0)
        return f"<{key}>"
    new_text = ABBR_RE.sub(repl, text)
    return new_text, mapping

def reinsert_placeholders(text: str, mapping: Dict[str,str]) -> str:
    out = text
    for k,v in mapping.items():
        out = out.replace(f"<{k}>", v)
    return out

def remove_sensitive(text: str, keep_room_words: bool=True) -> str:
    t = NUM_RE.sub(" ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t
