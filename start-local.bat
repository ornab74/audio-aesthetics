@echo off
cd /d "%~dp0engine"
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python run.py
