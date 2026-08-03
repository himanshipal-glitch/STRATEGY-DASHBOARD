@echo off
REM Double-click this to open the Strategy Team Project Registry.
cd /d "%~dp0"
streamlit run app.py --server.port 8503
pause
