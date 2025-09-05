@echo off
setlocal

set "REDIS_PORT=6379"
set "DAPHNE_HOST=163.14.137.59"
set "DAPHNE_PORT=5000"
set "ASGI_MODULE=chatroom.asgi:application"

echo [INFO] Starting Redis on port %REDIS_PORT%...
start "Redis" /MIN "C:\Users\forth\scoop\apps\redis\current\redis-server.exe" --port %REDIS_PORT%
ping 127.0.0.1 -n 2 >nul

echo [INFO] Starting Daphne on %DAPHNE_HOST%:%DAPHNE_PORT% ...
daphne -b %DAPHNE_HOST% -p %DAPHNE_PORT% %ASGI_MODULE%

echo [INFO] Stopping Redis...
taskkill /IM redis-server.exe /F >nul 2>&1
taskkill /IM memurai.exe /F >nul 2>&1

pause
endlocal