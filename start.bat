@echo off
echo ============================================
echo Starting KYNORA Backend with FastAPI
echo ============================================
echo.
echo Using Python 3.11 for FastAPI compatibility
echo.

py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
