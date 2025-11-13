stdtext_v2 - redesigned invoice text normalization service (prototype)

Layout:
  stdtext/                - python package with core modules
    config.yaml           - runtime configuration template
    normalize.py          - extraction & normalization helpers
    spell.py              - hunspell wrapper / fallback
    model.py              - corpus corrector (TF-IDF + KMeans + NN)
  app.py                  - FastAPI app (top-level)
  scripts/                - helper scripts to build dict, scrub, rebuild, etc.

Usage (high-level):
  1) Copy raw CSV to C:/Temp/text.csv (comma separated)
  2) python scripts/build_dict.py        -> builds C:/Temp/da_dictionary.txt
  3) python scripts/scrub_csv.py         -> builds C:/Temp/text_scrubbed.csv (placeholders kept)
  4) python scripts/spell_correct_corpus.py -> builds C:/Temp/text_corrected.csv
  5) python scripts/abbrev_builder.py    -> builds C:/Temp/abbrev_map.json
  6) python scripts/rebuild_artifacts.py -> builds ./artifacts (vectorizer, kmeans, nn)
  7) python app.py                       -> starts FastAPI (or run via uvicorn app:app)
