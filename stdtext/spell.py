from spellchecker import SpellChecker
try:
    from stdtext.spell_msword import MSWordSpellChecker
    MS=True
except:
    MS=False

class SpellWrapper:
    def __init__(self):
        self.ms = MSWordSpellChecker() if MS else None
        self.sp = SpellChecker(language=None)
    def correction(self,w):
        if self.ms:
            try: return self.ms.correction(w)
            except: pass
        return self.sp.correction(w) or w
