@echo off
cd /d "%~dp0frontend"
echo Starting REITs Frontend on http://localhost:5173
python -m http.server 5173
