# -*- coding: utf-8 -*-
from pathlib import Path
import logging

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
    def __init__(self, da_dictionary_path: str=None):
        self.msword = None
        self.sp = None

        if MSWORD_AVAILABLE:
            try:
                self.msword = MSWordSpellChecker()
                logging.info("Using Microsoft Word spell checker.")
            except Exception:
                self.msword = None

        if self.msword is None and PYSPELL_AVAILABLE:
            try:
                self.sp = SpellChecker(language=None)
                if da_dictionary_path and Path(da_dictionary_path).exists():
                    self.sp.word_frequency.load_text_file(da_dictionary_path)
                logging.info("Using PySpellChecker fallback.")
            except Exception:
                self.sp = None

        if self.msword is None and self.sp is None:
            logging.warning("No spellchecker available.")

    def correction(self, token: str) -> str:
        if not token:
            return token
        if self.msword:
            return self.msword.correction(token)
        if self.sp:
            try:
                return self.sp.correction(token) or token
            except Exception:
                return token
        return token

    def suggestions(self, token: str):
        if not token:
            return []
        if self.msword:
            return self.msword.suggestions(token)
        if self.sp:
            try:
                return list(self.sp.candidates(token))[:10]
            except Exception:
                return []
        return []
