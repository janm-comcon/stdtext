
# -*- coding: utf-8 -*-
import pandas as pd, re, json
from pathlib import Path
from collections import Counter
TOKEN_RE = re.compile(r"[A-Za-zÆØÅæøå]+")
SRC = Path("C:/Temp/text_scrubbed.csv")
OUT = Path("C:/Temp/abbrev_map.json")
if not SRC.exists():
    print("Missing:", SRC)
else:
    df = pd.read_csv(SRC, encoding="utf-8")
    text_col = max(df.columns, key=lambda c: df[c].astype(str).str.len().median())
    cnt = Counter()
    for line in df[text_col].astype(str):
        for w in TOKEN_RE.findall(line):
            cnt[w.lower()]+=1
    vocab = set(cnt.keys())
    amap = {}
    for short in [w for w in vocab if 2<=len(w)<=4]:
        candidates = [v for v in vocab if v.startswith(short) and len(v)-len(short)<=6 and cnt[v]>=cnt[short]]
        if candidates:
            amap[short]=sorted(candidates, key=lambda v:(-cnt[v], -len(v)))[0]
    OUT.write_text(json.dumps(amap, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote", len(amap), "abbrev mappings to", OUT)
