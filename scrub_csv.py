# -*- coding: utf-8 -*-
"""
scrub_csv.py  –  canonical cleaner for historical invoice text (side-by-side + summary)

Reads :  C:\Temp\text.csv   (comma separated)
Writes:
  - C:\Temp\text_scrubbed.csv         (scrubbed only)
  - C:\Temp\text_scrubbed_compare.csv (original + scrubbed for QA)
"""

import re, csv
from pathlib import Path
import pandas as pd
from collections import Counter

RAW_CSV = Path(r"C:\Temp\text.csv")
SCRUBBED_CSV = Path(r"C:\Temp\text_scrubbed.csv")
COMPARE_CSV = Path(r"C:\Temp\text_scrubbed_compare.csv")

ACTION_VERBS = [
    "demontering"
    "etablering",
    "fejlfinding"
    "fejlsøgning"
    "flytning",
    "fræsning"
    "installation",
    "køb",
    "levering",
    "montering", 
    "nedtagning",
    "udskiftning",
    "ombygning",
    "opbevaring",
    "ophængning", 
    "opmærkning",
    "opsætning",
    "tilslutning",
    "trækning",
    "udkald",
    "ændring"    
]

ROOM_WORDS = {
    "køkken","bad","badeværelse","wc","toilet","stue","gang","loft","tag",
    "værksted","kontor","kælder","garage","udhus","bryggers","entre"
}
TEST_WORDS = {"afprøvet","kontrolleret","fundet","ok","i","orden","testet"}

RE_NUMERIC = re.compile(r"\b\d+[.,]?\d*(?:[xX*/-]\d+[.,]?\d*)*\b")
RE_DATE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
RE_UNIT = re.compile(r"\b(?:mm|cm|m|meter|m2|m³|amp|a|v|kw|hz|ø\d+)\b", re.IGNORECASE)
RE_STK = re.compile(r"\bstk\b", re.IGNORECASE)
RE_ADDRESS = re.compile(
    r"\b(?:vej|gade|alle|plads|road|street|boulevard|city|town|kommune|aps|a/s|aps\.|as|aps,|a/s,)\b",
    re.IGNORECASE)
RE_POSTCODE = re.compile(r"\b\d{4,5}\b")
TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå]+")
RE_PHRASE_OK = re.compile(r"\bok\b|\bi orden\b", re.IGNORECASE)

def clean_raw(s: str) -> str:
    if s is None: return ""
    s = str(s).replace("\r"," ").replace("\n"," ").replace("\\r"," ").replace("\\n"," ")
    return re.sub(r"\s+"," ", s).strip()

def remove_sensitive_parts(text: str, counts: Counter) -> str:
    """strip numbers, units, stk, dates, addresses, company names"""
    before = text
    for pat in (RE_NUMERIC, RE_DATE, RE_UNIT, RE_STK, RE_POSTCODE, RE_ADDRESS):
        if pat.search(text):
            counts[pat.pattern] += 1
        text = pat.sub(" ", text)
    if text != before:
        counts["modified"] += 1
    return re.sub(r"\s+", " ", text).strip()

def find_text_col(df: pd.DataFrame):
    best, best_len = None, 0
    for c in df.columns:
        try:
            med = df[c].astype(str).str.len().median()
            if med > best_len:
                best_len, best = med, c
        except Exception:
            continue
    return best or df.columns[-1]

def canonicalize_line(raw: str, corrector=None, counts=None) -> str:
    """return cleaned canonical uppercase line"""
    if not isinstance(raw, str) or not raw.strip():
        return ""
    text = clean_raw(raw).lower()
    text = remove_sensitive_parts(text, counts)
    if corrector is not None:
        try:
            new = corrector.correct_and_expand(text)
            if new != text:
                counts["phrase_expanded"] += 1
            text = new
        except Exception:
            pass
    toks = TOKEN_RE.findall(text)
    if not toks:
        return ""
    joined = " ".join(toks)
    action = next((a.lower() for a in ACTION_VERBS if a.lower() in joined), None)
    object_tokens, room_tokens, test_tokens = [], [], []
    seen_action = False
    act_parts = action.split() if action else []
    i = 0
    while i < len(toks):
        t = toks[i]
        if not seen_action:
            if act_parts and toks[i:i+len(act_parts)] == act_parts:
                seen_action = True
                i += len(act_parts)
                continue
        else:
            if t in ROOM_WORDS:
                room_tokens.append(t)
            elif t in TEST_WORDS:
                test_tokens.append(t)
            else:
                object_tokens.append(t)
        i += 1
    parts = []
    if action:
        seg = [action] + object_tokens
        parts.append(" ".join(seg).strip().capitalize() + ".")
    else:
        parts.append(" ".join(object_tokens).strip().capitalize() + ".")
    if room_tokens:
        parts.append(" ".join(["i"] + room_tokens) + ".")
    if test_tokens:
        parts.append(" ".join(test_tokens) + ".")
    out = " ".join(parts)
    out = re.sub(r"\s*\.\s*", ". ", out)
    out = re.sub(r"(\.\s*){2,}", ". ", out)
    return out.strip().upper()

def main():
    try:
        from invoice_styler import corpus_corrector
    except Exception:
        corpus_corrector = None

    if not RAW_CSV.exists():
        print(f"File not found: {RAW_CSV}")
        return

    df = pd.read_csv(RAW_CSV, sep=";", engine="python", encoding="utf-8", on_bad_lines="skip")
    text_col = find_text_col(df)
    print("Detected text column:", text_col)

    corrector = None
    if corpus_corrector:
        try:
            corrector = corpus_corrector(df[text_col].astype(str).tolist(), max_edit=2)
            print("History-biased corrector initialized.")
        except Exception as e:
            print("Corrector init failed:", e)

    counts = Counter()
    originals, scrubbed = [], []
    for i, txt in enumerate(df[text_col].astype(str).tolist()):
        try:
            can = canonicalize_line(txt, corrector, counts)
        except Exception as e:
            print(f"Row {i} failed: {e}")
            can = ""
        originals.append(txt)
        scrubbed.append(can)
        if can != txt:
            counts["changed"] += 1
        else:
            counts["unchanged"] += 1

    df[text_col] = scrubbed
    df.to_csv(SCRUBBED_CSV, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    comp = pd.DataFrame({"original_text": originals, "scrubbed_text": scrubbed})
    comp.to_csv(COMPARE_CSV, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    total = len(df)
    print("\nSummary:")
    print(f"  Total rows processed: {total}")
    print(f"  Lines modified:       {counts['changed']} ({counts['changed']/total*100:.1f}%)")
    print(f"  Unchanged lines:      {counts['unchanged']}")
    print(f"  Numbers removed:      {counts[RE_NUMERIC.pattern]}")
    print(f"  Dates removed:        {counts[RE_DATE.pattern]}")
    print(f"  Units removed:        {counts[RE_UNIT.pattern]}")
    print(f"  'stk' removed:        {counts[RE_STK.pattern]}")
    print(f"  Address/company refs: {counts[RE_ADDRESS.pattern]}")
    print(f"  Phrase expansions:    {counts['phrase_expanded']}")
    print("\nOutputs:")
    print(f"  {SCRUBBED_CSV}")
    print(f"  {COMPARE_CSV}")

if __name__ == "__main__":
    main()
