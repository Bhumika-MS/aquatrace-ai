@echo off
cd /d "%~dp0"
echo Checking required packages...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Check your internet connection or confirm Flask is installed.
  pause
  exit /b 1
)
echo.
echo Starting AquaTrace AI. Keep this window open while using the website.
py app.py
pause
