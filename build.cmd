@echo off
echo ==========================================
echo   Setting up stdtext clean env
echo ==========================================

echo Creating virtual environment...
py -3.11 -m venv .venv

call .venv\Scripts\activate

echo Upgrading pip...
py -m pip install --upgrade pip

echo Installing requirements...
py -m pip install -r requirements.txt

echo Done.
pause
