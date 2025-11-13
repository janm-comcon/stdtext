from fastapi import FastAPI
from pydantic import BaseModel
from stdtext.normalize import simple_normalize, extract_placeholders, reinsert_placeholders
from stdtext.entity_scrubber import extract_entities, reinsert_entities
from stdtext.spell import SpellWrapper

app=FastAPI()
spell=SpellWrapper()

class RewriteIn(BaseModel): text:str
class RewriteOut(BaseModel): rewrite:str

@app.post("/rewrite",response_model=RewriteOut)
def rw(r:RewriteIn):
    n=simple_normalize(r.text)
    t1,m1=extract_placeholders(n)
    t2,m2=extract_entities(t1)
    toks=[spell.correction(x) for x in t2.split()]
    out=" ".join(toks)
    out=reinsert_entities(out,m2)
    out=reinsert_placeholders(out,m1)
    return {"rewrite":out.upper()}
