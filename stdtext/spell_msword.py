# -*- coding: utf-8 -*-
import win32com.client
import pythoncom
import threading

class MSWordSpellChecker:
    _local = threading.local()

    @staticmethod
    def _get_word():
        if not hasattr(MSWordSpellChecker._local, "word"):
            pythoncom.CoInitialize()
            w = win32com.client.Dispatch("Word.Application")
            w.Visible = False
            MSWordSpellChecker._local.word = w
        return MSWordSpellChecker._local.word

    def correction(self, word: str) -> str:
        if not word:
            return word
        try:
            app = MSWordSpellChecker._get_word()
            suggestions = app.GetSpellingSuggestions(word)
            if len(suggestions) > 0:
                return suggestions[0].Name
            return word
        except Exception:
            return word

    def suggestions(self, word: str):
        if not word:
            return []
        try:
            app = MSWordSpellChecker._get_word()
            suggestions = app.GetSpellingSuggestions(word)
            return [s.Name for s in suggestions][:10]
        except Exception:
            return []
