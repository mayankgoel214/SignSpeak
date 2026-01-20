@echo off
echo ============================================================
echo SignSpeak AI - Real-time Sign Language Translation
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or later from https://python.org
    pause
    exit /b 1
)

echo Starting SignSpeak AI...
echo.
echo The app will open in your browser at: http://localhost:7860
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python app.py

pause
