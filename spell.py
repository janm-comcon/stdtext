import json
from pathlib import Path
from spellchecker import SpellChecker
from pathlib import Path
from corpus_corrector import CorpusCorrector

# Load Danish wordlist (built from your corpus)
DICT_PATH = Path(r"C:\Temp\da_dictionary.txt")

# Load Danish abbreviation wordlist (built from your corpus)
ABBREV_FILE = Path(r"C:\Temp\abbrev_map.json")

if ABBREV_FILE.exists():
    ABBREV_MAP = json.loads(ABBREV_FILE.read_text(encoding="utf-8"))
    print(f"[abbrev] Loaded {len(ABBREV_MAP)} abbreviations")
else:
    ABBREV_MAP = {}

def expand_abbreviations(token: str, vocab: set[str]) -> str:
    """Expand known abbreviations or fuzzy prefixes using vocab."""
    t = token.lower()
    # direct map
    if t in ABBREV_MAP:
        return ABBREV_MAP[t]
    # prefix match in vocab
    for v in vocab:
        if v.startswith(t) and len(v) - len(t) <= 4:
            return v
    # fuzzy match using simple Levenshtein
    import difflib
    candidates = difflib.get_close_matches(t, vocab, n=1, cutoff=0.7)
    if candidates:
        return candidates[0]
    return token

def get_spell_dictionary_size(spell):
    """
    Return approximate dictionary size for a pyspellchecker SpellChecker instance.
    This is robust across pyspellchecker versions where WordFrequency may not implement len().
    Returns an int or None if unavailable.
    """
    try:
        wf = getattr(spell, "word_frequency", None)
        if wf is None:
            return None
        # best: try len() first (works on some versions)
        try:
            return len(wf)
        except TypeError:
            # fallback: iterate (WordFrequency is iterable)
            try:
                return sum(1 for _ in wf)
            except Exception:
                # last resort: try to access internal dicts (private API may vary)
                for attr in ("_frequency", "_word_frequency", "frequency"):
                    if hasattr(wf, attr):
                        maybe = getattr(wf, attr)
                        try:
                            return len(maybe)
                        except Exception:
                            continue
                return None
    except Exception:
        return None

if DICT_PATH.exists():
    spell = SpellChecker(language=None)
    spell.word_frequency.load_text_file(DICT_PATH)
    size = get_spell_dictionary_size(spell)
    if size is None:
        print("[spellchecker] Loaded Danish wordlist (size unknown)")
    else:
        print(f"[spellchecker] Loaded {size} Danish words")
else:
    spell = SpellChecker(language="en")
    print("[spellchecker] Using fallback English dictionary")

def spell_fix(corrector: CorpusCorrector, text: str) -> str:
    """Fix common typos using general dictionary before historic correction."""
    toks = text.split()
    out = []
    for t in toks:
        base = spell.correction(t) or t
        expanded = expand_abbreviations(base, getattr(corrector, "vocab", set()))
        out.append(expanded)
    return " ".join(out)

