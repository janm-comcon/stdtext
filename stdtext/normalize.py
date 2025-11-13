import re
from stdtext.entity_scrubber import extract_entities, reinsert_entities

def simple_normalize(t):
    return re.sub(r"\s+"," ",t.lower()).strip()

def extract_placeholders(t):
    return t, {}

def reinsert_placeholders(t,m):
    return t

def remove_sensitive(t, keep_room_words=True):
    return t
