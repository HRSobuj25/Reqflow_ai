<<<<<<< HEAD
@echo off
title ReqFlow AI Smart Launcher

echo ==================================================
echo             ReqFlow AI Launcher
echo ==================================================

:: Go to current folder
cd /d %~dp0

echo.
echo [1/5] Checking Python installation...

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Python is not installed!
    echo Please install Python first.
    pause
    exit
)

echo Python detected successfully.
echo.

echo [2/5] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/5] Installing required packages...
python -m pip install -r requirements.txt

echo.
echo [4/5] Starting ReqFlow AI...

timeout /t 2 >nul

start http://localhost:8501

echo.
echo [5/5] Launching Streamlit Server...

python -m streamlit run app.py

=======
@echo off
title ReqFlow AI Launcher

echo ==================================================
echo             ReqFlow AI Launcher
echo ==================================================

:: Go to current folder
cd /d %~dp0

echo.
echo [1/4] Checking Python installation...

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Python is not installed!
    pause
    exit
)

echo Python detected successfully.
echo.

echo [2/4] Installing required packages...
python -m pip install -r requirements.txt

echo.
echo [3/4] Launching ReqFlow AI...

python -m streamlit run app.py

>>>>>>> 833f8ecf (New Update)
pause