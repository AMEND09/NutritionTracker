@echo off
echo Building Nutrient Tracker for Windows...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if build.py exists
if not exist "build.py" (
    echo Error: build.py not found in current directory
    pause
    exit /b 1
)

REM Run the build script
python build.py

echo.
echo Build complete! Check the dist folder for your executable.
pause