# Invoice Text Style Normalizer

## Summary

We have built a small local service that makes new invoice descriptions automatically match the company’s historical invoice text style.

### Why this matters

- same type of work → same type of sentence
- stable vocabulary → easier accounting / auditing
- less manual writing → faster invoicing

## How it works

-it learns your historical invoice phrasing (from your past invoice text CSV)
- when a user types a new description, the service:
    1. corrects small spelling variations
    2. prefers already-used words instead of new words
    3. auto-completes partial phrases into the standard company phrasing
    4. enforces your uppercase telegraphic style

(example: “afprøvet ok” → becomes “AFPRØVET OG FUNDET I ORDEN.”)

## How it is used

- it runs locally on a Windows PC (completely offline)
- the ERP can call it through HTTP:

```bach
POST /rewrite   { "text": "<new invoice line>" }
```

and receives back a corrected standard style version + the closest historic examples.

## Maintenance

- new historic data can be added at any time (raw master CSV)
- one click reload endpoint rebuilds the style model live — no downtime

## Result

all invoice text from today forward will look like it was written by the same person who wrote the previous 5 years of invoices.

consistent
professional
auditor-friendly

and the ERP users type much less.