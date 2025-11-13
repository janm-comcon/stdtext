@echo off
echo ==========================================
echo   Setting up stdtext_v2 Python environment
echo ==========================================

REM Choose Python (edit if your python.exe path is different)
set PYTHON=python

echo Creating virtual environment...
py -3.11 -m venv .venv

if not exist .venv (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Upgrading pip...
py -m pip install --upgrade pip

echo Installing requirements...
py -m pip install -r requirements.txt

echo Checking Hunspell support...
py - << EOF
try:
    import hunspell
    print("Hunspell installed OK.")
except Exception:
    print("Hunspell not available – fallback to PySpellChecker will be used.")
EOF

echo ------------------------------------------
echo Environment setup complete.
echo To start the API, run:
echo     call .venv\Scripts\activate
echo     uvicorn app:app --reload
echo ------------------------------------------

pause
