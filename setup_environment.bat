@echo off
REM KYNORA Backend - Automated Setup Script for Windows
REM This script automates the initial setup process

echo ============================================================
echo   KYNORA E-Commerce Backend - Automated Setup
echo ============================================================
echo.

REM Check Python installation
echo [1/8] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ERROR: Python is not installed or not in PATH
    echo    Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo    OK - Python is installed
echo.

REM Check if virtual environment exists
echo [2/8] Setting up virtual environment...
if exist venv\ (
    echo    Virtual environment already exists
) else (
    echo    Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo    ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo    OK - Virtual environment created
)
echo.

REM Activate virtual environment
echo [3/8] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo    ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo    OK - Virtual environment activated
echo.

REM Upgrade pip
echo [4/8] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo    OK - pip upgraded
echo.

REM Install dependencies
echo [5/8] Installing dependencies from requirements.txt...
echo    This may take a few minutes...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo    ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo    OK - Dependencies installed
echo.

REM Check for .env file
echo [6/8] Checking environment configuration...
if exist .env (
    echo    OK - .env file exists
) else (
    if exist .env.example (
        echo    Creating .env from .env.example...
        copy .env.example .env >nul
        echo    OK - .env file created
        echo    WARNING: Please edit .env file with your credentials!
    ) else (
        echo    ERROR: .env.example not found
    )
)
echo.

REM Check for service account key
echo [7/8] Checking Firebase configuration...
if exist serviceAccountKey.json (
    echo    OK - Firebase service account key found
) else (
    echo    WARNING: serviceAccountKey.json not found
    echo    Please download from Firebase Console and place in project root
)
echo.

REM Run verification script
echo [8/8] Running setup verification...
python verify_setup.py
echo.

echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Edit .env file with your Firebase and Cloudinary credentials
echo   2. Place serviceAccountKey.json in project root (if not done)
echo   3. Run: python scripts/setup_firestore.py --seed=true
echo   4. Run: python scripts/deploy_indexes.py
echo   5. Start server: uvicorn main:app --reload
echo.
echo Useful commands:
echo   - Check database: python check_database.py
echo   - Verify setup: python verify_setup.py
echo   - Start server: start.bat or uvicorn main:app --reload
echo   - API docs: http://localhost:8000/docs
echo.
echo ============================================================
pause
