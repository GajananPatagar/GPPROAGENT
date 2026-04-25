@echo off
title GP PRO AGENT Installer
color 0B
echo.
echo  GP PRO AGENT - Auto Installer
echo  Downloading 40GB AI Brain...
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo Downloading Python...
    curl -fsSL https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe -o py.exe
    py.exe /quiet InstallAllUsers=1 PrependPath=1
    del py.exe
)
python -m pip install --upgrade pip --quiet
python installer/brain_installer.py
python main.py --mode gui
pause
