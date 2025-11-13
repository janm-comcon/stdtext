# entity scrubber minimal version
from pathlib import Path
import re
from collections import Counter

CITY_FILE = Path(__file__).parent / "data" / "danish_cities.txt"
CITIES = {l.strip() for l in CITY_FILE.read_text().splitlines() if l.strip()}

POST = re.compile(r"\b\d{4}\b")

def extract_entities(t):
    mapping={}
    c=Counter()
    def key(k): c[k]+=1; return f"{k}_{c[k]:04d}"
    # postcodes
    def rpl(m):
        k=key("POST"); mapping[k]=m.group(0); return f"<{k}>"
    t=POST.sub(rpl,t)
    # simple city
    out=[]
    for w in t.split():
        if w.lower() in CITIES:
            k=key("CITY"); mapping[k]=w; out.append(f"<{k}>")
        else:
            out.append(w)
    return " ".join(out), mapping

def reinsert_entities(t,m):
    for k,v in m.items(): t=t.replace(f"<{k}>",v)
    return t
