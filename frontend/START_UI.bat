@echo off
echo ========================================
echo   MAi UI - Starting Web Server
echo ========================================
echo.
echo Starting server on http://localhost:8080
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

cd /d %~dp0
python -m http.server 8080

pause
