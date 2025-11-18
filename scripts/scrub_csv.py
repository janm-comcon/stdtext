# -*- coding: utf-8 -*-
"""
scrub_csv.py
------------
Prepares raw invoice CSV for ML training:

    - normalizes text (lowercase, trims, preserves abbreviations)
    - removes URLs (uppercase/lowercase)
    - removes emails
    - removes phone numbers
    - removes dates (dd.mm.yyyy, dd-mm-yyyy, 2–4 digit year)
    - removes standalone numbers (via remove_sensitive)
    - preserves structure of the CSV

Dates and URLs are VALID in invoice rewrites but excluded from ML.
"""

from pathlib import Path
import re
import pandas as pd

import sys
sys.path.insert(1, '../stdtext')    

from stdtext.normalize import simple_normalize, remove_sensitive
from stdtext.entity_scrubber import EMAIL_RE, PHONE_RE

# Input / output paths
RAW = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/text_scrubbed.csv")

# ----------------------------------------------------------------------
# URL detection (case-insensitive, works with UPPERCASE text)
# ----------------------------------------------------------------------
URL_RE = re.compile(
    r"\b((?:https?://|www\.)[A-Za-z0-9._%:/?#=&+-]+)",
    flags=re.IGNORECASE,
)

def remove_urls(text: str) -> str:
    return URL_RE.sub(" ", text)


# ----------------------------------------------------------------------
# DATE detection: dd.mm.yyyy or dd-mm-yyyy (2–4 digit year)
# ----------------------------------------------------------------------
DATE_RE = re.compile(
    r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b"
)

def remove_dates(text: str) -> str:
    return DATE_RE.sub(" ", text)


# ----------------------------------------------------------------------
# EMAIL & PHONE removal (patterns imported from entity_scrubber)
# ----------------------------------------------------------------------
def remove_emails(text: str) -> str:
    return EMAIL_RE.sub(" ", text)


def remove_phones(text: str) -> str:
    return PHONE_RE.sub(" ", text)


# ----------------------------------------------------------------------
# Core scrubber for a single text cell
# ----------------------------------------------------------------------
def scrub_text(text) -> str:
    # Robust against NaN / non-strings
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1) normalize (lowercase, collapse spaces, preserve abbreviations)
    t = simple_normalize(text)

    # 2) remove URLs
    t = remove_urls(t)

    # 3) remove emails & phones
    t = remove_emails(t)
    t = remove_phones(t)

    # 4) remove dates
    t = remove_dates(t)

    # 5) remove bare numbers (keep placeholders)
    t = remove_sensitive(t, keep_room_words=True)

    # 6) collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()

    return t


# ----------------------------------------------------------------------
# Main CSV processor
# ----------------------------------------------------------------------
def main():
    if not RAW.exists():
        print(f"ERROR: Raw CSV not found: {RAW}")
        return

    # Load full CSV with pandas
    df = pd.read_csv(RAW, encoding="utf-8", on_bad_lines="skip")

    # Heuristic: assume the "main text" column is the one
    # whose values are longest on average
    text_col = max(
        df.columns,
        key=lambda c: df[c].astype(str).str.len().median()
    )

    # Apply scrubbing to that column
    df[text_col] = df[text_col].map(scrub_text)

    # Save back out
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Scrubbed corpus written to: {OUT}")


if __name__ == "__main__":
    main()
