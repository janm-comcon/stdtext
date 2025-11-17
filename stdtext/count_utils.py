# -*- coding: utf-8 -*-
"""COUNT extraction and formatting utilities.

Detects patterns like "lampe 2 stk" after spell correction, converts
them to <COUNT_xxxx> placeholders, and can reformat them to
"2 stk. lamper".
"""

COUNT_UNITS = {
    "stk", "stk.", "st", "st.",
    "pcs", "x", "à",
    "enheder", "antal",
    "kg", "m", "meter", "cm",
}


def extract_counts_structured(tokens):
    """Return (new_tokens, mapping) with COUNT placeholders."""
    new_tokens = []
    mapping = {}
    c = 0
    i = 0
    n = len(tokens)

    while i < n:
        if (
            i + 2 < n
            and not tokens[i].startswith("<")
            and tokens[i+1].isdigit()
            and tokens[i+2].lower().rstrip(".") in COUNT_UNITS
        ):
            noun = tokens[i]
            qty = int(tokens[i+1])
            unit = tokens[i+2].lower().rstrip(".")
            c += 1
            key = f"COUNT_{c:04d}"
            mapping[key] = {"noun": noun, "qty": qty, "unit": unit}
            new_tokens.append(f"<{key}>")
            i += 3
            continue
        new_tokens.append(tokens[i])
        i += 1

    return new_tokens, mapping


def pluralize_da(noun: str, qty: int) -> str:
    """Very simple Danish plural heuristic."""
    if qty == 1:
        return noun
    if noun.endswith(("er", "e", "s", "r")):
        return noun
    return noun + "er"


def format_count_phrase(info: dict) -> str:
    noun = info["noun"]
    qty = info["qty"]
    unit = info["unit"]
    unit_out = unit + "." if unit in {"stk", "st"} else unit
    noun_pl = pluralize_da(noun, qty)
    return f"{qty} {unit_out} {noun_pl}"
