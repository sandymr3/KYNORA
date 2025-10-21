@echo off
REM KYNORA Backend Setup Script for Windows

echo ========================================
echo KYNORA Backend Setup
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/5] Installing dependencies...
pip install -r requirements.txt

echo.
echo [3/5] Setting up environment...
if not exist .env (
    copy .env.example .env
    echo Created .env file from template
    echo Please edit .env with your Firebase and Cloudinary credentials
) else (
    echo .env file already exists
)

echo.
echo [4/5] Checking for Firebase credentials...
if not exist serviceAccountKey.json (
    echo WARNING: serviceAccountKey.json not found!
    echo Please download from Firebase Console and place in this directory
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next Steps:
echo 1. Edit .env with your Firebase and Cloudinary credentials
echo 2. Place serviceAccountKey.json in this directory
echo 3. Run: python scripts\setup_firestore.py --seed=true
echo 4. Run: python main.py
echo.
echo To test the API:
echo   python test_api.py
echo.
pause
