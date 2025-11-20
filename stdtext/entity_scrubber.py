# -*- coding: utf-8 -*-
"""Spell-aware, pattern-based entity scrubber.

Extracts:
  - URL, EMAIL, PHONE, DATE
  - CITY (from gazetteer)
  - STREETNAME
  - COMPANY
  - PERSON (simple context-based)
Leaves normal Danish words untouched.
"""

import re
from pathlib import Path
from collections import Counter
from typing import Dict, Tuple

from stdtext.spell import SpellWrapper

_spell = SpellWrapper()


def is_known_word(token: str) -> bool:
    if not token:
        return True
    corr = _spell.correction(token)
    return corr.lower() == token.lower()


# Gazetteer
CITY_GAZETTEER_PATH = Path(__file__).parent / "data" / "danish_cities.txt"
_city_set = set()
if CITY_GAZETTEER_PATH.exists():
    with CITY_GAZETTEER_PATH.open(encoding="utf-8") as fh:
        _city_set = {ln.strip().lower() for ln in fh if ln.strip()}


# Patterns
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+45\s?)?\b(?:\d{2}[\s.-]?){3}\d{2}\b")
URL_RE = re.compile(r"\b((?:https?://|www\.)[A-Za-z0-9._%:/?#=&+-]+)", flags=re.IGNORECASE)
DATE_RE = re.compile(r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b")

STREET_SUFFIXES = [
    "vej", "gade", "alle", "torv", "stræde", "vænget",
    "bakken", "parken", "engen", "stien", "kaj",
    "vænge", "plads",
]

COMPANY_SUFFIXES = [
    "a/s", "aps", "a.m.b.a", "p/s", "k/s", "aps."
]

ROOM_WORDS = {
    "køkken", "bad", "badeværelse", "wc", "toilet",
    "stue", "gang", "loft", "tag", "værksted", "kontor",
    "kælder", "garage", "bryggers", "entre",
}

PREP_CONTEXT = {"hos", "ved", "til", "for", "i", "på"}


def extract_entities(text: str) -> Tuple[str, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    counters = Counter()

    def newkey(kind: str) -> str:
        counters[kind] += 1
        return f"{kind}_{counters[kind]:04d}"

    # URL
    def rpl_url(m):
        k = newkey("URL"); mapping[k] = m.group(1); return f"<{k}>"

    text = URL_RE.sub(rpl_url, text)

    # EMAIL
    def rpl_email(m):
        k = newkey("EMAIL"); mapping[k] = m.group(0); return f"<{k}>"

    text = EMAIL_RE.sub(rpl_email, text)

    # PHONE
    def rpl_phone(m):
        k = newkey("PHONE"); mapping[k] = m.group(0); return f"<{k}>"

    text = PHONE_RE.sub(rpl_phone, text)

    # DATE
    def rpl_date(m):
        k = newkey("DATE"); mapping[k] = m.group(0); return f"<{k}>"

    text = DATE_RE.sub(rpl_date, text)

    tokens = text.split()
    out = []
    i = 0
    L = len(tokens)

    while i < L:
        w = tokens[i]
        wl = w.lower()

        # Keep placeholders untouched
        if wl.startswith("<") and wl.endswith(">"):
            out.append(w)
            i += 1
            continue

        # Known Danish word => not entity
        if is_known_word(wl):
            out.append(w)
            i += 1
            continue

        # Non-entity room words
        if wl in ROOM_WORDS:
            out.append(w)
            i += 1
            continue

        # City
        if wl in _city_set:
            k = newkey("CITY"); mapping[k] = w; out.append(f"<{k}>"); i += 1; continue

        # Streetname
        if any(wl.endswith(suf) for suf in STREET_SUFFIXES):
            k = newkey("STREETNAME"); mapping[k] = w; out.append(f"<{k}>"); i += 1; continue

        # Company
        if any(wl.endswith(suf) for suf in COMPANY_SUFFIXES):
            k = newkey("COMP"); mapping[k] = w; out.append(f"<{k}>"); i += 1; continue

        # Person (context hos/ved/til/for/i/på)
        if i > 0 and tokens[i-1].lower() in PREP_CONTEXT:
            ent = [w]
            j = i + 1
            while j < L and len(ent) < 3:
                t = tokens[j]; tl = t.lower()
                if is_known_word(tl):
                    break
                if any(ch.isdigit() for ch in t):
                    break
                if tl in PREP_CONTEXT or tl in ROOM_WORDS:
                    break
                ent.append(t); j += 1
            k = newkey("PERS"); mapping[k] = " ".join(ent); out.append(f"<{k}>")
            i = j
            continue

        # Unknown but not entity pattern => keep raw
        out.append(w)
        i += 1

    return " ".join(out), mapping


def reinsert_entities(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for k, v in mapping.items():
        out = out.replace(f"<{k}>", v)
    return out
