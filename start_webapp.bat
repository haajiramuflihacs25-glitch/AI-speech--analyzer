@echo off
echo Starting AI Speech Analyzer Web Application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Create uploads directory if it doesn't exist
if not exist "uploads" mkdir uploads

REM Start the Flask application
echo.
echo Starting web server...
echo The application will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause