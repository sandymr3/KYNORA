@echo off
REM Firebase Token Generator - Batch Script
REM Usage: get_token.bat [admin|user|custom] [options]

echo.
echo ==========================================
echo    Firebase Authentication Token Generator
echo ==========================================
echo.

if "%1"=="" (
    echo Generating admin token...
    python utils\get_token.py --type admin
) else if "%1"=="admin" (
    echo Generating admin token...
    python utils\get_token.py --type admin %2 %3 %4 %5
) else if "%1"=="user" (
    echo Generating user token...
    python utils\get_token.py --type user %2 %3 %4 %5 %6 %7
) else if "%1"=="custom" (
    echo Generating custom token...
    python utils\get_token.py --type custom %2 %3 %4 %5 %6 %7
) else if "%1"=="verify" (
    echo Verifying token...
    python utils\get_token.py --verify %2
) else if "%1"=="help" (
    echo.
    echo Usage Examples:
    echo   get_token.bat                           - Generate admin token
    echo   get_token.bat admin                     - Generate admin token
    echo   get_token.bat user --uid user123        - Generate user token
    echo   get_token.bat custom --uid custom123    - Generate custom token
    echo   get_token.bat verify "your-token-here"  - Verify a token
    echo.
    echo Options:
    echo   --uid USER_ID       - Specify user ID
    echo   --email EMAIL       - Specify email
    echo   --role ROLE         - Specify role (default: user)
    echo   --output FILE       - Save token to file
    echo   --claims JSON       - Additional claims as JSON
    echo.
) else (
    echo Unknown command: %1
    echo Use "get_token.bat help" for usage information
)

echo.
pause
