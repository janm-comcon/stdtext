# -*- coding: utf-8 -*-
import json
from pathlib import Path
import logging

# Optional spell backends
try:
    from stdtext.spell_msword import MSWordSpellChecker
    MSWORD_AVAILABLE = True
except Exception:
    MSWORD_AVAILABLE = False

try:
    from spellchecker import SpellChecker
    PYSPELL_AVAILABLE = True
except Exception:
    PYSPELL_AVAILABLE = False


class SpellWrapper:
    """
    Unified spell correction:
    - MS Word (preferred)
    - PySpellChecker fallback
    - Abbreviations skipped entirely
    - Placeholders untouched
    """

    def __init__(self, da_dictionary_path=None, abbrev_map_path="C:/Temp/abbrev_map.json"):

        # ----------------------------------------------------------------------
        # Load abbreviation whitelist
        # ----------------------------------------------------------------------
        self.abbrevs = set()
        try:
            p = Path(abbrev_map_path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                self.abbrevs = set(k.lower() for k in data.keys())
        except Exception:
            self.abbrevs = set()

        # ----------------------------------------------------------------------
        # MS Word spell checker
        # ----------------------------------------------------------------------
        self.msword = None
        if MSWORD_AVAILABLE:
            try:
                import win32com.client
                self.msword = win32com.client.Dispatch("Word.Application")
            except Exception:
                self.msword = None

        # ----------------------------------------------------------------------
        # PySpellChecker fallback
        # ----------------------------------------------------------------------
        self.sp = None
        if PYSPELL_AVAILABLE:
            try:
                self.sp = SpellChecker(language=None)
                if da_dictionary_path and Path(da_dictionary_path).exists():
                    self.sp.word_frequency.load_text_file(da_dictionary_path)
            except Exception:
                self.sp = None

    # ==========================================================================
    # MAIN SPELL CORRECTION
    # ==========================================================================
    def correction(self, token: str) -> str:
        if not token:
            return token

        tok_low = token.lower()

        # --- Skip abbreviations entirely -------------------------------------
        if tok_low in self.abbrevs:
            return token

        # --- Skip generic abbreviation shapes (2–3 letters + '.') -------------
        if len(tok_low) <= 4 and tok_low.endswith(".") and tok_low[:-1].isalpha():
            return token

        # --- Skip placeholders -------------------------------------------------
        if tok_low.startswith("<") and tok_low.endswith(">"):
            return token

        # --- Try MS Word spell checker ----------------------------------------
        if self.msword:
            try:
                result = self.msword.CheckSpelling(token)
                if result is False:
                    suggestions = self.msword.GetSpellingSuggestions(token)
                    if suggestions:
                        return suggestions[0].Name
                return token
            except Exception:
                pass

        # --- Fallback: PySpellChecker -----------------------------------------
        if self.sp:
            try:
                if token in self.sp:     # already correct
                    return token
                return self.sp.correction(token)
            except Exception:
                return token

        # --- Fallback: do nothing ---------------------------------------------
        return token

    # ==========================================================================
    # GET SUGGESTIONS
    # ==========================================================================
    def suggestions(self, token: str):
        if not token:
            return []
        if self.msword:
            try:
                return [s.Name for s in self.msword.GetSpellingSuggestions(token)]
            except Exception:
                pass
        if self.sp:
            try:
                return list(self.sp.candidates(token))[:10]
            except Exception:
                return []
        return []
