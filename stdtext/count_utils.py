# -*- coding: utf-8 -*-
"""
COUNT extraction and reformatting utilities.

Converts patterns like:
    "lampe 2 stk"
into placeholders:
    <COUNT_0001>
and stores structured data:
    {"noun": "lampe", "qty": 2, "unit": "stk"}

Later reinsertion produces normalized invoice style:
    "2 stk. lamper"
"""

import re

COUNT_UNITS = {
    "stk", "stk.", "st", "st.",
    "pcs", "x", "à",
    "enheder", "antal",
    "kg", "m", "meter", "cm"
}


def extract_counts_structured(tokens):
    """
    Given spell-corrected token list, detect COUNT patterns:
        noun qty unit
    and replace them with <COUNT_xxxx> placeholders.

    Returns:
        new_tokens: list[str]
        mapping: dict { COUNT_xxxx: {"noun":..., "qty":..., "unit":...} }
    """
    new_tokens = []
    mapping = {}
    c = 0
    i = 0
    n = len(tokens)

    while i < n:
        # Pattern: WORD NUMBER UNIT
        if (
            i + 2 < n
            and not tokens[i].startswith("<")             # don't start inside placeholder
            and tokens[i+1].isdigit()                    # numeric quantity
            and tokens[i+2].lower().rstrip(".") in COUNT_UNITS
        ):
            noun = tokens[i]
            qty = int(tokens[i+1])
            unit_raw = tokens[i+2]
            unit = unit_raw.lower().rstrip(".")

            c += 1
            key = f"COUNT_{c:04d}"

            mapping[key] = {
                "noun": noun,
                "qty": qty,
                "unit": unit,
            }

            new_tokens.append(f"<{key}>")
            i += 3
            continue

        # Default: no COUNT match
        new_tokens.append(tokens[i])
        i += 1

    return new_tokens, mapping


def pluralize_da(noun: str, qty: int) -> str:
    """
    Very simple Danish pluralization heuristic.
    Enough for invoice-like nouns:
        lampe -> lamper
        sikring -> sikringer
    """
    if qty == 1:
        return noun

    # Already looks plural?
    if noun.endswith(("er", "e", "s", "r")):
        return noun

    # Default rule: add "er"
    return noun + "er"


def format_count_phrase(info: dict) -> str:
    """
    Generate canonical invoice phrase:
        qty unit. plural_noun
    Example:
        {noun: "lampe", qty: 2, unit: "stk"} -> "2 stk. lamper"
    """
    noun = info["noun"]
    qty = info["qty"]
    unit = info["unit"]

    if unit in {"stk", "st"}:
        unit_out = unit + "."
    else:
        unit_out = unit

    noun_pl = pluralize_da(noun, qty)

    return f"{qty} {unit_out} {noun_pl}"
