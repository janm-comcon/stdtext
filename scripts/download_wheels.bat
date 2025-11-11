@echo off
setlocal
IF NOT EXIST wheels mkdir wheels
py -3.11 -m pip download -r requirements.txt -d wheels
echo Wheels downloaded to .\wheels
endlocal
