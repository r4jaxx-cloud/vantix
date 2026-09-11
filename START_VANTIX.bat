@echo off
cd /d "%~dp0"
echo Open http://localhost:8000 in your browser.
py -3 server.py
pause
