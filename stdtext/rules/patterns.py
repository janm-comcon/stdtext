# stdtext/rules/patterns.py
# -*- coding: utf-8 -*-
"""
Rule patterns for Danish invoice lines.

Goal:
  - Put ACTION first (MONTERING, UDSKIFTNING, INSTALLATION, ...)
  - Then "af"
  - Then quantity/object (<COUNT_...> and other tokens)
  - Then location phrases ("i køkken", "i stue", "hos <PERS>" etc.)

We assume input tokens are:
  - lowercased words
  - placeholders like <COUNT_0001>, <CITY_0001>, <COMP_0001>, <PERS_0001>, <DATE_0001>, <URL_0001> etc.
"""

from typing import List

# Verbs we treat as "actions"
ACTION_VERBS = {
    "montering",
    "udskiftning",
    "installation",
    "levering",
    "opsætning",
    "nedtagning",
    "tilslutning",
    "kontrol",
    "eftersyn",
    "flytning",
}

# Prepositions that typically introduce a location phrase
PREP_LOC = {"i", "på", "hos", "ved", "til", "for"}


def apply_rewrite_patterns(tokens: List[str]) -> str:
    """
    Take a token list (after spell + COUNT extraction) and reorder it into:

        ACTION AF [COUNT/OBJECT PART] [LOCATION PART]

    If no ACTION is found, returns the original string.
    """
    if not tokens:
        return ""

    lower = [t.lower() for t in tokens]

    # 1. Find first action verb
    action_idx = None
    for i, t in enumerate(lower):
        if t in ACTION_VERBS:
            action_idx = i
            break

    if action_idx is None:
        # No recognized action verb → don't enforce any pattern
        return " ".join(tokens)

    action = tokens[action_idx]

    # All tokens except the action itself are candidates for other roles
    pre_tokens = tokens[:action_idx] + tokens[action_idx + 1 :]

    counts: List[str] = []
    locations: List[str] = []
    others: List[str] = []

    i = 0
    while i < len(pre_tokens):
        t = pre_tokens[i]
        tl = t.lower()

        # COUNT placeholders: <COUNT_0001>
        if t.startswith("<COUNT_"):
            counts.append(t)
            i += 1
            continue

        # location phrase: starts with preposition and then some words
        if tl in PREP_LOC:
            loc_tokens = [t]
            i += 1
            while i < len(pre_tokens):
                t2 = pre_tokens[i]
                tl2 = t2.lower()
                # stop if we hit another preposition or another COUNT or a DATE/URL placeholder
                if tl2 in PREP_LOC or t2.startswith("<COUNT_") or t2.startswith("<DATE_") or t2.startswith("<URL_"):
                    break
                loc_tokens.append(t2)
                i += 1
            locations.append(" ".join(loc_tokens))
            continue

        # everything else (adjectives, nouns, etc.)
        others.append(t)
        i += 1

    # Build canonical order: ACTION + "af" + counts + others + locations
    new_tokens: List[str] = [action, "af"]

    # quantities & objects
    new_tokens.extend(counts)
    new_tokens.extend(others)

    # locations at the end
    for loc in locations:
        new_tokens.append(loc)

    return " ".join(new_tokens)
