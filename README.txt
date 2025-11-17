stdtext_v2 - redesigned invoice text normalization service (prototype)

Layout:
  stdtext/
    app.py
    build.cmd
    requirements.txt
    artifacts/          ← empty (to be built from scratch)
    scripts/
      build_dict.py
      scrub_csv.py
      abbrev_builder.py
      spell_correct_corpus.py
      rebuild_artifacts.py
    stdtext/
      data/
        danish_cities.txt
      __init__.py
      config.yaml
      normalize.py
      entity_scrubber.py
      count_utils.py
      spell.py
      spell_msword.py
      model.py

Usage (high-level):

1) py scripts\build_dict.py           -> C:/Temp/da_dictionary.txt
2) py scripts\scrub_csv.py            -> C:/Temp/text_scrubbed.csv
3) py scripts\abbrev_builder.py       -> C:/Temp/abbrev_map.json
4) py scripts\spell_correct_corpus.py -> C:/Temp/text_corrected.csv
5) py scripts\rebuild_artifacts.py    -> tdtext/artifacts/ with vectorizer.pkl, nn.pkl, cleaned.csv
5) py app.py                          -> starts FastAPI (or run via uvicorn app:app)
