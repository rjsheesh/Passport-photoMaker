@echo off
title Smart Passport Photo Studio - Auto Setup
color 0A

echo ===================================================
echo       Smart Passport Photo Studio Setup
echo               Developed by fabiTECH
echo ===================================================
echo.


python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not installed on this system.
    echo [*] Downloading Python 3.11... Please wait.
    curl -o python_installer.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    
    echo [*] Installing Python... This may take a few minutes.

    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    echo [*] Cleaning up installer...
    del python_installer.exe
    
    echo.
    echo [SUCCESS] Python has been installed successfully! 
    echo [!] ACTION REQUIRED: Since Python was just installed, Windows needs to refresh.
    echo Please CLOSE this black window and double-click this .bat file AGAIN.
    pause
    exit
) ELSE (
    echo [OK] Python is already installed!
)

echo.
echo [*] Checking and updating PIP...
python -m pip install --upgrade pip >nul 2>&1

echo [*] Installing required libraries (PySide6, Pillow, rembg)...

pip install PySide6 Pillow rembg

echo.
echo [OK] Setup Complete! Starting the application...
echo ===================================================


python passport_maker_v3.3.py

pause
