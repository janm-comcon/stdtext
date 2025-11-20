# -*- coding: utf-8 -*-
"""
ENTITY SCRUBBER v5
------------------

Features:
    - URL entity      <URL_xxxx>
    - EMAIL entity    <EMAIL_xxxx>
    - PHONE entity    <PHONE_xxxx>
    - DATE entity     <DATE_xxxx>
    - COUNT entities  <COUNT_xxxx>  (2 lamper, 3 stk. lamper, 2 stk.)
    - CITY based on gazetteer
    - STREETNAME detection via suffix
    - COMPANY detection via suffix (A/S, ApS, etc.)
    - PERSON detection in context ("hos", "ved", "til", "for", "i", "på")
    - Spell-check–aware filtering (ignore entities that are valid Danish words)
    - Safe reinsertion of entities at the end of pipeline

This file is designed to be used in BOTH:
    - input rewrite pipeline
    - scrub_csv.py (via EMAIL_RE, PHONE_RE)
"""

import re
from pathlib import Path
from typing import Dict, Tuple
from collections import Counter

from stdtext.spell import SpellWrapper

# ----------------------------------------------------------------------
# Spell wrapper (used to check if a token is a known word)
# ----------------------------------------------------------------------
_spell = SpellWrapper()

def is_known_word(token: str) -> bool:
    """
    Check whether a token is known to the spell checker.
    SpellWrapper.correction(token) returns the closest correct word.
    If that is equal to the token itself, it's considered known.
    """
    if not token:
        return True
    corr = _spell.correction(token)
    return corr.lower() == token.lower()


# ----------------------------------------------------------------------
# Gazetteer: Danish cities (loaded once)
# ----------------------------------------------------------------------
CITY_GAZETTEER_PATH = Path(__file__).parent / "data" / "danish_cities.txt"
_city_set = set()
if CITY_GAZETTEER_PATH.exists():
    with CITY_GAZETTEER_PATH.open("r", encoding="utf-8") as fh:
        _city_set = {ln.strip().lower() for ln in fh if ln.strip()}

# ----------------------------------------------------------------------
# REGEX PATTERNS (absolute entities first)
# ----------------------------------------------------------------------

# URL detection (UPPERCASE/lowercase safe)
URL_RE = re.compile(
    r"\b((?:https?://|www\.)[A-Za-z0-9._%:/?#=&+-]+)",
    flags=re.IGNORECASE
)

# Email
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Phone number (Danish formats)
PHONE_RE = re.compile(
    r"(?:\+45\s?)?\b(?:\d{2}[\s.-]?){3}\d{2}\b"
)

# DATE: dd.mm.yyyy or dd-mm-yyyy (year 2–4 digits)
DATE_RE = re.compile(
    r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b"
)

# COUNT patterns
COUNT_SIMPLE = re.compile(
    r"\b(\d+)\s+([A-Za-zÆØÅæøå]+)\b"
)

COUNT_STK = re.compile(
    r"\b(\d+)\s+stk\.?\s*([A-Za-zÆØÅæøå]+)?\b"
)


# ----------------------------------------------------------------------
# Dictionaries for street, company, room words, person context
# ----------------------------------------------------------------------
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


# ======================================================================
# ENTITY EXTRACTION
# ======================================================================
def extract_entities(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract entities, replacing them with <TYPE_xxxx> placeholders.
    Returns:
        cleaned_text, mapping
    """
    mapping: Dict[str, str] = {}
    counters = Counter()

    def newkey(kind: str) -> str:
        counters[kind] += 1
        return f"{kind}_{counters[kind]:04d}"

    # ============================================================
    # 1) URL
    # ============================================================
    def rpl_url(m):
        k = newkey("URL")
        mapping[k] = m.group(1)
        return f"<{k}>"

    text = URL_RE.sub(rpl_url, text)

    # ============================================================
    # 2) EMAIL
    # ============================================================
    def rpl_email(m):
        k = newkey("EMAIL")
        mapping[k] = m.group(0)
        return f"<{k}>"

    text = EMAIL_RE.sub(rpl_email, text)

    # ============================================================
    # 3) PHONE
    # ============================================================
    def rpl_phone(m):
        k = newkey("PHONE")
        mapping[k] = m.group(0)
        return f"<{k}>"

    text = PHONE_RE.sub(rpl_phone, text)

    # ============================================================
    # 4) DATE
    # ============================================================
    def rpl_date(m):
        k = newkey("DATE")
        mapping[k] = m.group(0)
        return f"<{k}>"

    text = DATE_RE.sub(rpl_date, text)

    # ============================================================
    # 5) COUNT entities ("2 lamper", "3 stk lamper", "2 stk.")
    # ============================================================
    def rpl_count_stk(m):
        num = m.group(1)
        word = m.group(2)
        if word and is_known_word(word.lower()):
            k = newkey("COUNT")
            mapping[k] = f"{num} stk. {word}"
            return f"<{k}>"
        if word is None:
            k = newkey("COUNT")
            mapping[k] = f"{num} stk."
            return f"<{k}>"
        return m.group(0)

    def rpl_count_simple(m):
        num = m.group(1)
        word = m.group(2)
        if is_known_word(word.lower()):
            k = newkey("COUNT")
            mapping[k] = f"{num} {word}"
            return f"<{k}>"
        return m.group(0)

    text = COUNT_STK.sub(rpl_count_stk, text)
    text = COUNT_SIMPLE.sub(rpl_count_simple, text)

    # ============================================================
    # 6) Token-based entity detection
    # ============================================================
    tokens = text.split()
    out = []
    i = 0
    L = len(tokens)

    while i < L:
        w = tokens[i]
        wl = w.lower()

        if wl.startswith("<") and wl.endswith(">"):
            out.append(w)
            i += 1
            continue

        if is_known_word(wl):
            out.append(w)
            i += 1
            continue

        if wl in ROOM_WORDS:
            out.append(w)
            i += 1
            continue

        if wl in _city_set:
            k = newkey("CITY"); mapping[k] = w; out.append(f"<{k}>"); i += 1; continue

        # Street detection
        if any(wl.endswith(suf) for suf in STREET_SUFFIXES):
            k = newkey("STREETNAME")
            mapping[k] = w
            out.append(f"<{k}>")
            i += 1
            continue

        # Company detection
        if any(wl.endswith(suf) for suf in COMPANY_SUFFIXES):
            k = newkey("COMP")
            mapping[k] = w
            out.append(f"<{k}>")
            i += 1
            continue

        # Person detection in context ("hos", "ved", etc.)
        if i > 0 and tokens[i - 1].lower() in PREP_CONTEXT:
            ent = [w]
            j = i + 1

            # collect up to 3 unknown words
            while j < L and len(ent) < 3:
                t = tokens[j]
                tl = t.lower()

                if is_known_word(tl):
                    break
                if any(ch.isdigit() for ch in t):
                    break
                if tl in PREP_CONTEXT or tl in ROOM_WORDS:
                    break

                ent.append(t)
                j += 1

            k = newkey("PERS")
            mapping[k] = " ".join(ent)
            out.append(f"<{k}>")
            i = j
            continue

        out.append(w)
        i += 1

    return " ".join(out), mapping


# ======================================================================
# ENTITY REINSERTION
# ======================================================================
def reinsert_entities(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for k, v in mapping.items():
        out = out.replace(f"<{k}>", v)
    return out
