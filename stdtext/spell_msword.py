import win32com.client, pythoncom, threading
class MSWordSpellChecker:
    _l=threading.local()
    @staticmethod
    def _w():
        if not hasattr(MSWordSpellChecker._l,"w"):
            pythoncom.CoInitialize()
            w=win32com.client.Dispatch("Word.Application"); w.Visible=False
            MSWordSpellChecker._l.w=w
        return MSWordSpellChecker._l.w
    def correction(self,w):
        try:
            app=self._w()
            s=app.GetSpellingSuggestions(w)
            return s[0].Name if s else w
        except:
            return w
