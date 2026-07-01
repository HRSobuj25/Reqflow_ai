@echo off
title ReqFlow AI Launcher

cd /d %~dp0

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed!
    pause
    exit
)

echo Starting ReqFlow AI...

python -m streamlit run app.py

pause