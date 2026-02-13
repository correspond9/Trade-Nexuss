@echo off
setlocal
echo ========================================================
echo   Running Backend in SIMULATED PRODUCTION MODE
echo ========================================================

:: 1. Force Production Environment
set ENVIRONMENT=production

:: 2. Unset any "offline" or "disable" flags that might be in your system vars
set DISABLE_DHAN_WS=
set BACKEND_OFFLINE=
set DISABLE_MARKET_STREAMS=

:: 3. Optional: Unset V1 compat disable if you want V1 routes
set DISABLE_V1_COMPAT=

echo [INFO] ENVIRONMENT=%ENVIRONMENT%
echo [INFO] Offline flags cleared.
echo.
echo [INFO] Starting Uvicorn...
echo.

set PYTHONPATH=%CD%\fastapi_backend
cd fastapi_backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
