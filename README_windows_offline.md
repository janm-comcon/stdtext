# Offline install (Windows)

1) On an ONLINE PC:
   - Open cmd/PowerShell in this folder.
   - Run: `.\scripts\download_wheels.bat`  (creates .\wheels\)

2) Copy the whole `stdtext_service` folder (including `wheels`) to the OFFLINE workstation.

3) On the OFFLINE workstation:
   - Ensure Python 3.11 x64 is installed and on PATH.
   - Run: `.\scriptsuild_offline.bat`
   - Then: `.\scriptsun.bat`

Endpoints:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/representatives
- POST http://127.0.0.1:8000/rewrite  with JSON: { "text": "...", "top_k": 3 }
- Docs: http://127.0.0.1:8000/docs
