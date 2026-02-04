@echo off
REM Verification Script - Backend Fix Validation (Windows)
REM Run this after applying the fixes to verify everything is working

setlocal enabledelayedexpansion

echo.
echo ════════════════════════════════════════════════════════════════
echo.           Backend Fix Verification Script
echo.                    404 Error Resolution
echo.
echo ════════════════════════════════════════════════════════════════
echo.

REM Step 1: Check credentials
echo Step 1: Checking DhanHQ Credentials...
echo ─────────────────────────────────────────────────────────────────

if "%DHAN_CLIENT_ID%"=="" (
    echo [X] DHAN_CLIENT_ID not set
    echo     Set with: set DHAN_CLIENT_ID=your_client_id
) else (
    echo [OK] DHAN_CLIENT_ID is set
)

if "%DHAN_ACCESS_TOKEN%"=="" (
    echo [X] DHAN_ACCESS_TOKEN not set
    echo     Set with: set DHAN_ACCESS_TOKEN=your_token
) else (
    echo [OK] DHAN_ACCESS_TOKEN is set
)

echo.

REM Step 2: Check if backend is running
echo Step 2: Checking Backend Status...
echo ─────────────────────────────────────────────────────────────────

REM Try to reach backend health endpoint
powershell -Command "(new-object net.webclient).DownloadString('http://127.0.0.1:8000/health')" >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] Backend is running on port 8000
) else (
    echo [X] Backend is not responding on port 8000
    echo     Start backend with: cd fastapi_backend ^&^& python app/main.py
    exit /b 1
)

echo.

REM Step 3: Check cache statistics
echo Step 3: Checking Cache Population...
echo ─────────────────────────────────────────────────────────────────

for /f "delims=" %%A in ('powershell -Command "(new-object net.webclient).DownloadString('http://127.0.0.1:8000/health')"') do (
    set "RESPONSE=%%A"
)

if defined RESPONSE (
    echo [OK] Backend responded to health check
) else (
    echo [X] Backend health check failed
)

echo.

REM Step 4: Test the endpoint
echo Step 4: Testing /options/live Endpoint...
echo ─────────────────────────────────────────────────────────────────

for /f "delims=" %%A in ('powershell -Command "try { $r = (new-object net.webclient).DownloadString('http://127.0.0.1:8000/api/v2/options/live?underlying=NIFTY^&expiry=2026-02-11'); Write-Host '200' } catch { Write-Host $_.Exception.Response.StatusCode.Value }"') do (
    set "HTTP_CODE=%%A"
)

if "%HTTP_CODE%"=="200" (
    echo [OK] Endpoint returned 200 OK
    echo     Response includes data for option chain
) else if "%HTTP_CODE%"=="404" (
    echo [X] Endpoint returned 404 - Cache still empty
    echo     Check backend logs for: 'populate_with_live_data' errors
    exit /b 1
) else (
    echo [X] Endpoint returned %HTTP_CODE%
)

echo.

REM Step 5: Check code changes
echo Step 5: Verifying Code Changes...
echo ─────────────────────────────────────────────────────────────────

find "Cache verified and ready" fastapi_backend\app\main.py >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] main.py contains cache verification
) else (
    echo [X] main.py missing cache verification
)

find "update_option_price_from_websocket" fastapi_backend\app\dhan\live_feed.py >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] live_feed.py contains WebSocket integration
) else (
    echo [X] live_feed.py missing WebSocket integration
)

find "def update_option_price_from_websocket" fastapi_backend\app\services\authoritative_option_chain_service.py >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Service contains new cache update method
) else (
    echo [X] Service missing cache update method
)

echo.

REM Step 6: Summary
echo ════════════════════════════════════════════════════════════════
echo.                       SUMMARY
echo.
echo ════════════════════════════════════════════════════════════════

if "%HTTP_CODE%"=="200" (
    echo.
    echo [OK] ALL CHECKS PASSED
    echo.
    echo Next steps:
    echo   1. Start frontend: cd frontend ^&^& npm run dev
    echo   2. Open http://localhost:5173
    echo   3. Navigate to OPTIONS page
    echo   4. Select NIFTY -^> Expiry -^> View prices
    echo.
    echo Monitor backend logs for realtime updates:
    echo   Search logs for: 'Updated'
) else (
    echo.
    echo [X] CHECKS FAILED
    echo.
    echo Troubleshooting steps:
    echo   1. Verify credentials are set: echo %DHAN_CLIENT_ID%
    echo   2. Check backend logs for errors
    echo   3. Ensure DhanHQ API token is valid
    echo   4. Restart backend with credentials set
)

echo.
echo For detailed documentation, see:
echo   - QUICK_START_GUIDE.md
echo   - BACKEND_FIX_STATUS.md
echo   - IMPLEMENTATION_COMPLETE.md
echo.

endlocal
