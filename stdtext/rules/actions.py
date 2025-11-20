# -*- coding: utf-8 -*-
"""
Action phrase detection and normalization.
Replaces action verbs/roots with canonical forms like "MONTERING AF".
"""

# import re

# ACTIONS = [
#     (re.compile(r"\bins(?:t|ta|tal|tall|talla|tallat|tallati|tallatio|tallation)?\b"), "installation af"),
#     (re.compile(r"\bkon(?:t|tr|tro|trol)?\b"), "kontrol af"),
#     (re.compile(r"\blev(?:vering)?\b"), "levering af"),
#     (re.compile(r"\bmon(?:tering)?\b"), "montering af"),
#     (re.compile(r"\bnedt(?:agning)?\b"), "nedtagning af"),
#     (re.compile(r"\budsk(?:iftning)?\b"), "udskiftning af"),
#     (re.compile(r"\bops(?:ætning)?\b"), "opsætning af"),
#     (re.compile(r"\bren(?:overing)?\b"), "renovering af"),
#     (re.compile(r"\brep(?:aration)?\b"), "reparation af"),
# ]
import re
from pathlib import Path
import yaml

###############################################################
# LOAD CONFIG
###############################################################

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
CFG = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

FUZZY_RULES = CFG.get("rules", {}).get("fuzzy_actions", [])


###############################################################
# LIGHTWEIGHT LEVENSHTEIN
###############################################################

def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            insert = prev[j] + 1
            delete = curr[j - 1] + 1
            replace = prev[j - 1] + (ca != cb)
            curr.append(min(insert, delete, replace))
        prev = curr
    return prev[-1]


###############################################################
# STEM GENERATOR — AUTO CREATE DANISH STEMS
###############################################################

def generate_stems(base: str):
    """
    Generate stems and variants for a Danish action noun:
    Example: 'montering' -> ['m', 'mo', 'mon', ..., 'montering',
                             'montere', 'monteres', 'monteret']
    """
    base = base.lower()

    stems = set()

    # 1. prefix stems
    for i in range(3, len(base) + 1):
        stems.add(base[:i])  # mon, mont, monte, ...

    # 2. Danish verb forms: montere, monteres, monteret
    if base.endswith("ing"):
        verb = base[:-3] + "ere"       # montere
        stems.add(verb)
        stems.add(verb + "s")          # monteres
        stems.add(verb + "t")          # monteret

    return sorted(stems)


###############################################################
# GENERIC FUZZY EXPANDER (AUTO-STEMS)
###############################################################

def fuzzy_expand_actions(text: str) -> str:
    tokens = text.split()
    out = []

    for tok in tokens:
        clean = tok.lower().strip(".,;:-_!?")

        replaced = False

        for rule in FUZZY_RULES:
            action = rule["action"]
            base = rule["base_word"].lower()
            max_dist = rule.get("max_distance", 2)

            stems = generate_stems(base)

            # 1. Prefix-based match
            for stem in stems:
                # match token start against any reasonable Danish stem
                if clean.startswith(stem[:3]):
                    out.append(action)
                    replaced = True
                    break
            if replaced:
                break

            # 2. Fuzzy match
            for stem in stems:
                if levenshtein(clean, stem) <= max_dist:
                    out.append(action)
                    replaced = True
                    break
            if replaced:
                break

        if not replaced:
            out.append(tok)

    return " ".join(out)


###############################################################
# EXISTING ACTION RULES (unchanged)
###############################################################

ACTION_RULES = [
    # your original regex rules stay here unchanged
]


###############################################################
# MAIN APPLY ACTION RULES
###############################################################

def apply_action_rules(text: str) -> str:
    # Step 1 - fuzzy expansion from config
    text = fuzzy_expand_actions(text)

    # Step 2 - your regex-based expanders
    new_text = text
    for pattern, replacement in ACTION_RULES:
        new_text = pattern.sub(replacement, new_text)

    return new_text
