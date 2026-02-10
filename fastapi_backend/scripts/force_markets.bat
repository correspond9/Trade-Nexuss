@echo off
echo Forcing NSE open...
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"NSE\",\"state\":\"open\"}"
echo.
echo Forcing BSE open...
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"BSE\",\"state\":\"open\"}"
echo.
echo Forcing MCX open...
curl -s -X POST "http://127.0.0.1:8000/api/v2/admin/market/force" -H "Content-Type: application/json" -d "{\"exchange\":\"MCX\",\"state\":\"open\"}"
echo.
pause
