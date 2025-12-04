# StdText Rewrite Service

StdText is a FastAPI service that rewrites short invoice line texts using a rule-driven pipeline with optional OpenAI post-processing. It normalizes abbreviations, preserves named entities, corrects spelling, formats counts, and can call an OpenAI model to polish the final uppercase output.

## Requirements

- Python 3.11 (use a Python 3.11 virtual environment to match the supported runtime)
- pip

## Installation

1. Create and activate a Python 3.11 virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   If you want DaCy-backed refinement, make sure pip can reach the Hugging Face
   wheel for the Danish transformer model. The dependency entry in
   `requirements.txt` already points at the versioned wheel URL (for example,
   `da_dacy_small_trf-0.2.0-py3-none-any.whl`). Using the versioned filename
   avoids the `Invalid wheel filename (invalid version)` error that appears when
   the wheel is downloaded without its version segment.

## Configuration

Service behavior is configured in `stdtext/config.yaml`. You can enable optional OpenAI polishing, choose the model, and control whether responses are uppercased. The rule configuration also contains fuzzy action definitions used by the pipeline.

## Running the API

Start the FastAPI application with Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

Windows users can use `run.cmd` after activating the virtual environment.

## API Overview

- `GET /health` — Basic health probe that reports whether OpenAI support is enabled and verifies spell-check initialization.
- `POST /rewrite` — Runs the rule-based pipeline and, if configured or requested, sends the draft through OpenAI for light polishing.
- `POST /debug_rewrite` — Executes only the rule-based pipeline and returns all intermediate stages for debugging.
- `POST /check_spelling` — Performs normalization-aware spell checking while preserving placeholders for abbreviations and entities.

## Pipeline Features

1. Text normalization and domain-specific action expansion.
2. Abbreviation and entity placeholder extraction to protect key tokens.
3. Spell correction for non-placeholder tokens.
4. Structured count extraction and formatting.
5. Rewrite pattern application to produce canonical action phrases.
6. Reinsertion of entities, abbreviations, and formatted counts.
7. Optional OpenAI refinement before returning the final uppercase result.

## Development Tips

- Keep `stdtext/config.yaml` API keys out of version control.
- Use the `/debug_rewrite` endpoint when adjusting rules to see every intermediate stage.
- The service is designed to run without OpenAI access; OpenAI calls are skipped unless explicitly enabled.
