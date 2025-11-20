# -*- coding: utf-8 -*-
"""
Action phrase detection and normalization.
Replaces action verbs/roots with canonical forms like "MONTERING AF".
"""

import re

ACTIONS = [
    (re.compile(r"\bins(?:tallation)?\b"), "installation af"),
    (re.compile(r"\bkon(?:trol)?\b"), "kontrol af"),
    (re.compile(r"\blev(?:overing)?\b"), "levering af"),
    (re.compile(r"\bmon(?:tering)?\b"), "montering af"),
    (re.compile(r"\bnedt(?:agning)?\b"), "nedtagning af"),
    (re.compile(r"\budsk(?:iftning)?\b"), "udskiftning af"),
    (re.compile(r"\bops(?:ætning)?\b"), "opsætning af"),
    (re.compile(r"\bren(?:overing)?\b"), "renovering af"),
    (re.compile(r"\brep(?:aration)?\b"), "reparation af"),
]


def apply_action_rules(tokens):
    """
    Given a list of tokens (spell-corrected), replace the FIRST action match
    with the canonical form and remove the original token.

    Returns: (new_tokens, action_used)
    """
    out = []
    used_action = None

    for tok in tokens:
        if used_action is None:
            for regex, canon in ACTIONS:
                if regex.fullmatch(tok):
                    used_action = canon
                    out.append(canon)
                    break
            else:
                out.append(tok)
        else:
            out.append(tok)

    return out, used_action
