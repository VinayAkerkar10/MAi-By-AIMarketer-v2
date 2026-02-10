@echo off
title MAi UI Web Server
color 0A
echo.
echo ========================================
echo   MAi UI - Web Server Launcher
echo ========================================
echo.
echo Starting web server on port 8080...
echo.

cd /d "%~dp0frontend"

if not exist "standalone.html" (
    echo ERROR: standalone.html not found!
    echo Make sure you're running this from the project root.
    pause
    exit /b 1
)

echo Starting Python HTTP server...
echo.
echo Once you see "Serving HTTP on 0.0.0.0 port 8080"
echo Open your browser and go to:
echo.
echo   http://localhost:8080/standalone.html
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

python -m http.server 8080

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start server!
    echo Make sure Python is installed and in your PATH.
    echo.
    pause
)
