@echo off
setlocal
py -v3.11 -m venv .venv
call .venv\Scripts\activate
py -m pip install --no-index --find-links=.\wheels -r requirements.txt
echo Install complete.
endlocal
