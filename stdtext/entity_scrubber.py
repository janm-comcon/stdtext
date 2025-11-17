# -*- coding: utf-8 -*-
"""Simple entity scrubber for addresses, cities, phones, etc."""
import re
from pathlib import Path
from collections import Counter
from typing import Dict, Tuple

CITY_GAZETTEER_PATH = Path(__file__).parent / "data" / "danish_cities.txt"
_city_set = set()
if CITY_GAZETTEER_PATH.exists():
    with CITY_GAZETTEER_PATH.open(encoding="utf-8") as fh:
        _city_set = {ln.strip().lower() for ln in fh if ln.strip()}

POSTCODE_RE = re.compile(r"\b\d{4}\b")
PHONE_RE = re.compile(r"(?:\+45\s?)?\b(?:\d{2}[\s.-]?){3}\d{2}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

STREET_SUFFIXES = [
    "vej", "gade", "alle", "torv", "stræde", "vænget", "bakken",
    "parken", "engen", "stien", "kaj", "vænge", "plads",
]

COMPANY_SUFFIXES = ["a/s", "aps", "a.m.b.a", "p/s", "k/s", "aps."]

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

    # emails / phones / postcodes
    def rpl_email(m):
        k = newkey("EMAIL"); mapping[k] = m.group(0); return f"<{k}>"

    def rpl_phone(m):
        k = newkey("PHONE"); mapping[k] = m.group(0); return f"<{k}>"

    def rpl_post(m):
        k = newkey("POST"); mapping[k] = m.group(0); return f"<{k}>"

    text = EMAIL_RE.sub(rpl_email, text)
    text = PHONE_RE.sub(rpl_phone, text)
    text = POSTCODE_RE.sub(rpl_post, text)

    tokens = text.split()
    out = []
    i = 0
    L = len(tokens)

    while i < L:
        w = tokens[i]
        wl = w.lower()

        if wl in ROOM_WORDS:
            out.append(w)
            i += 1
            continue

        # Street name endings
        matched = False
        for suf in STREET_SUFFIXES:
            if wl.endswith(suf):
                k = newkey("STREETNAME")
                mapping[k] = w
                out.append(f"<{k}>")
                i += 1
                matched = True
                break
        if matched:
            continue

        # City via gazetteer
        if wl in _city_set:
            k = newkey("CITY")
            mapping[k] = w
            out.append(f"<{k}>")
            i += 1
            continue

        # Company suffix
        if any(suf in wl for suf in COMPANY_SUFFIXES):
            k = newkey("COMP")
            mapping[k] = w
            out.append(f"<{k}>")
            i += 1
            continue

        # Person via context (hos, ved, til, for, i, på)
        if i > 0 and tokens[i-1].lower() in PREP_CONTEXT:
            ent = [w]; j = i + 1
            while j < L and len(ent) < 3:
                t = tokens[j]; tl = t.lower()
                if any(ch.isdigit() for ch in t) or tl in PREP_CONTEXT or tl in ROOM_WORDS:
                    break
                ent.append(t); j += 1
            k = newkey("PERS")
            mapping[k] = " ".join(ent)
            out.append(f"<{k}>")
            i = j
            continue

        out.append(w)
        i += 1

    return " ".join(out), mapping


def reinsert_entities(text: str, mapping: Dict[str, str]) -> str:
    for k, v in mapping.items():
        text = text.replace(f"<{k}>", v)
    return text
