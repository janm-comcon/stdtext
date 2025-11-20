# -*- coding: utf-8 -*-
"""COUNT extraction and formatting utilities.

Detects patterns like "lampe 2 stk" or "2 stk lamper" and turns
them into <COUNT_xxxx> placeholders, with structured info for later
reinsertion in canonical form: "2 stk. lamper".
"""

COUNT_UNITS = {
    "stk", "stk.", "st", "st.",
    "pcs", "x", "à",
    "enheder", "antal",
    "kg", "m", "meter", "cm",
}


def extract_counts_structured(tokens):
    """Return (new_tokens, mapping) with COUNT placeholders.

    mapping: { "COUNT_0001": {"raw": "...", "qty": int|None, "unit": str|None, "noun": str|None} }
    """
    new_tokens = []
    mapping = {}
    c = 0
    i = 0
    n = len(tokens)

    while i < n:
        t = tokens[i]
        tl = t.lower().rstrip(".")

        # Pattern A: number + unit + noun (e.g. 2 stk lamper)
        if i + 2 < n and tokens[i].isdigit():
            unit = tokens[i+1].lower().rstrip(".")
            noun = tokens[i+2]
            if unit in COUNT_UNITS:
                c += 1
                key = f"COUNT_{c:04d}"
                mapping[key] = {
                    "raw": f"{tokens[i]} {tokens[i+1]} {noun}",
                    "qty": int(tokens[i]),
                    "unit": unit,
                    "noun": noun,
                }
                new_tokens.append(f"<{key}>")
                i += 3
                continue

        # Pattern B: noun + number + unit (e.g. lampe 2 stk)
        if i + 2 < n and tokens[i+1].isdigit():
            noun = tokens[i]
            unit = tokens[i+2].lower().rstrip(".")
            if unit in COUNT_UNITS:
                c += 1
                key = f"COUNT_{c:04d}"
                mapping[key] = {
                    "raw": f"{noun} {tokens[i+1]} {tokens[i+2]}",
                    "qty": int(tokens[i+1]),
                    "unit": unit,
                    "noun": noun,
                }
                new_tokens.append(f"<{key}>")
                i += 3
                continue

        # Pattern C: number + noun (e.g. 2 lamper)
        if i + 1 < n and tokens[i].isdigit():
            noun = tokens[i+1]
            c += 1
            key = f"COUNT_{c:04d}"
            mapping[key] = {
                "raw": f"{tokens[i]} {noun}",
                "qty": int(tokens[i]),
                "unit": None,
                "noun": noun,
            }
            new_tokens.append(f"<{key}>")
            i += 2
            continue

        new_tokens.append(t)
        i += 1

    return new_tokens, mapping


def pluralize_da(noun: str, qty: int) -> str:
    """Very simple Danish plural heuristic."""
    if qty == 1 or qty is None:
        return noun
    if noun.endswith(("er", "e", "s", "r")):
        return noun
    return noun + "er"


def format_count_phrase(info: dict) -> str:
    """Render COUNT info as canonical phrase "2 stk. lamper"."""
    qty = info.get("qty")
    unit = info.get("unit")
    noun = info.get("noun") or ""

    if qty is None:
        return info.get("raw", "")

    noun_pl = pluralize_da(noun, qty)

    if unit in {"stk", "st"}:
        unit_out = unit + "."
    elif unit:
        unit_out = unit
    else:
        unit_out = ""

    if unit_out:
        return f"{qty} {unit_out} {noun_pl}".strip()
    return f"{qty} {noun_pl}".strip()
