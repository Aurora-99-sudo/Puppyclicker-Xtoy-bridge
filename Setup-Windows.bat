@echo off

setlocal

echo ========================================
echo  PuppyClicker - XToys Setup
echo ========================================
echo.

cd /d "%~dp0"

REM ------------------------------------------------------------
REM Check Python
REM ------------------------------------------------------------

where python >nul 2>&1

if errorlevel 1 (
    echo ERROR: Python was not found.
    echo.
    echo Install Python 3 and try again.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM ------------------------------------------------------------
REM Create virtual environment
REM ------------------------------------------------------------

if exist "clicker-bridge\Scripts\python.exe" (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv clicker-bridge

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo.

REM ------------------------------------------------------------
REM Upgrade pip
REM ------------------------------------------------------------

echo Updating pip...

clicker-bridge\Scripts\python.exe -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo ERROR: Failed to update pip.
    pause
    exit /b 1
)

echo.

REM ------------------------------------------------------------
REM Install requirements
REM ------------------------------------------------------------

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found.
    pause
    exit /b 1
)

echo Installing requirements...

clicker-bridge\Scripts\python.exe -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)

echo.

echo ========================================
echo  Setup complete
echo ========================================
echo.
echo Virtual environment:
echo %CD%\clicker-bridge
echo.
echo You can now run the application.
echo.
pause

endlocal
