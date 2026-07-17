@echo off
call .venv\Scripts\activate.bat
python start.py %*
.\ngrok.exe http 8000