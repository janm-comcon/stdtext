@echo off
setlocal
call .venv\Scripts\activate
py -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
endlocal
