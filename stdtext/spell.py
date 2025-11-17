# -*- coding: utf-8 -*-
import json
from pathlib import Path

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
    """Unified spell correction with abbreviation and placeholder handling."""

    def __init__(self, da_dictionary_path=None, abbrev_map_path="C:/Temp/abbrev_map.json"):
        # Abbreviations
        self.abbrevs = set()
        try:
            p = Path(abbrev_map_path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                self.abbrevs = set(k.lower() for k in data.keys())
        except Exception:
            self.abbrevs = set()

        # MS Word
        self.msword = None
        if MSWORD_AVAILABLE:
            try:
                self.msword = MSWordSpellChecker()
            except Exception:
                self.msword = None

        # PySpellChecker
        self.sp = None
        if PYSPELL_AVAILABLE:
            try:
                self.sp = SpellChecker(language=None)
                if da_dictionary_path and Path(da_dictionary_path).exists():
                    self.sp.word_frequency.load_text_file(da_dictionary_path)
            except Exception:
                self.sp = None

    def correction(self, token: str) -> str:
        if not token:
            return token

        tok_low = token.lower()

        # Abbreviations
        if tok_low in self.abbrevs:
            return token
        if len(tok_low) <= 4 and tok_low.endswith(".") and tok_low[:-1].isalpha():
            return token

        # Placeholders
        if tok_low.startswith("<") and tok_low.endswith(">"):
            return token

        # MS Word
        if self.msword:
            try:
                return self.msword.correction(token)
            except Exception:
                pass

        # PySpellChecker
        if self.sp:
            try:
                if token in self.sp:
                    return token
                return self.sp.correction(token)
            except Exception:
                return token

        return token

    def suggestions(self, token: str):
        if not token:
            return []
        tok_low = token.lower()
        if tok_low in self.abbrevs:
            return []
        if tok_low.startswith("<") and tok_low.endswith(">"):
            return []
        if self.msword:
            try:
                return self.msword.suggestions(token)
            except Exception:
                pass
        if self.sp:
            try:
                return list(self.sp.candidates(token))[:10]
            except Exception:
                return []
        return []
