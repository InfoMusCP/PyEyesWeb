@echo off
setlocal ENABLEDELAYEDEXPANSION

:: -------------------------------
:: CONFIGURATION
:: -------------------------------
set "TARGET_DIR=.\demos\Lib"
set "PIP_ARGS=--upgrade --target %TARGET_DIR%"
set "LIB_SOURCE=."
:: -------------------------------

:: -------------------------------
:: ANSI COLOR CODES (PowerShell + cmd.exe)
:: -------------------------------
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RESET=[0m"

:: -------------------------------
:: CHECK PYTHON
:: -------------------------------
echo %YELLOW%[INFO] Checking Python installation...%RESET%
where.exe python >nul 2>nul
if errorlevel 1 (
    echo %RED%[ERROR] Python not found. Please install Python 3.11.%RESET%
    goto :end_script
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo %YELLOW%[INFO] Python version detected: %PY_VER%%RESET%

echo %PY_VER% | findstr /R "^3\.11\." >nul
if errorlevel 1 (
   echo %RED%[ERROR] Python 3.11.x is required. Found %PY_VER%%RESET%
   goto :end_script
)
echo %GREEN%[OK] Python 3.11.x found.%RESET%

:: -------------------------------
:: MOVE UP ONE DIRECTORY
:: -------------------------------
echo %YELLOW%[INFO] Moving up one directory...%RESET%
cd ..
echo %GREEN%[OK] Now in %cd%%RESET%

:: -------------------------------
:: INSTALL LIBRARY
:: -------------------------------
echo %YELLOW%[INFO] Updating pip%RESET%
python -m pip install --upgrade pip setuptools wheel
echo %YELLOW%[INFO] Installing library into %TARGET_DIR%...%RESET%
python -m pip install %PIP_ARGS% "%LIB_SOURCE%"
if errorlevel 1 (
    echo %RED%[ERROR] Library installation failed.%RESET%
    goto :end_script
)
echo %GREEN%[OK] Library installed successfully into %TARGET_DIR%.%RESET%

:end_script
echo.
echo %YELLOW%[INFO] Script finished. Press any key to exit...%RESET%
pause >nul

endlocal
exit /b 0
