# -*- coding: utf-8 -*-
"""
scrub_csv.py
------------
Prepares raw invoice CSV for ML training:

    - removes URLs (uppercase/lowercase)
    - removes emails
    - removes phone numbers
    - removes dates (dd.mm.yyyy, dd-mm-yyyy)
    - normalizes whitespace
    - preserves abbreviations
    - strips sensitive numbers except placeholders

Dates and URLs are VALID in invoice rewrites but excluded from ML.
"""

import csv
import re
from pathlib import Path

import sys
sys.path.insert(1, '../stdtext')

from stdtext.normalize import simple_normalize, remove_sensitive
from stdtext.entity_scrubber import EMAIL_RE, PHONE_RE

RAW = Path("C:/Temp/text.csv")
OUT = Path("C:/Temp/text_scrubbed.csv")

# ======================================================================
# UPPERCASE-SAFE URL REGEX
# ======================================================================
URL_RE = re.compile(
    r"\b((?:https?://|www\.)[A-Za-z0-9._%:/?#=&+-]+)",
    flags=re.IGNORECASE,
)

def remove_urls(text: str) -> str:
    return URL_RE.sub(" ", text)


# ======================================================================
# DATE REGEX (dd.mm.yyyy or dd-mm-yyyy, with 2–4 digit years)
# ======================================================================
DATE_RE = re.compile(
    r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b"
)

def remove_dates(text: str) -> str:
    return DATE_RE.sub(" ", text)


# ======================================================================
# EMAIL + PHONE REMOVAL
# ======================================================================
def remove_emails(text: str) -> str:
    return EMAIL_RE.sub(" ", text)

def remove_phones(text: str) -> str:
    return PHONE_RE.sub(" ", text)


# ======================================================================
# MAIN CLEANING FUNCTION
# ======================================================================
def scrub_text(text: str) -> str:
    if not text:
        return ""

    # 1) Normalize (preserves abbreviations)
    t = simple_normalize(text)

    # 2) Remove URLs
    t = remove_urls(t)

    # 3) Remove emails and phones
    t = remove_emails(t)
    t = remove_phones(t)

    # 4) Remove dates (training corpus should not contain dates)
    t = remove_dates(t)

    # 5) Remove standalone numbers (except placeholders)
    t = remove_sensitive(t, keep_room_words=True)

    # 6) Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()

    return t


# ======================================================================
# CSV PROCESSOR
# ======================================================================
def main():
    if not RAW.exists():
        print(f"ERROR: Raw CSV not found: {RAW}")
        return

    with RAW.open("r", encoding="utf-8") as f_in, OUT.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:

        reader = csv.reader(f_in)
        writer = csv.writer(f_out)

        header = next(reader)
        writer.writerow(header)

        text_col = max(range(len(header)), key=lambda i: len(header[i]))

        for row in reader:
            txt = row[text_col]
            row[text_col] = scrub_text(txt)
            writer.writerow(row)

    print(f"Scrubbed corpus written to: {OUT}")


if __name__ == "__main__":
    main()
