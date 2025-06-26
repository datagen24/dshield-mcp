@echo off
REM DShield MCP - Virtual Environment Setup Script for Windows
REM This script creates a virtual environment and installs all dependencies

echo === DShield MCP Virtual Environment Setup ===
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✅ Python is available

REM Check if virtualenv is available
python -m venv --help >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: python -m venv is not available
    echo Please ensure Python 3.8+ is installed with venv support
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your configuration
) else (
    echo ✅ .env file already exists
)

echo.
echo === Setup Complete! ===
echo.
echo To activate the virtual environment:
echo   venv\Scripts\activate.bat
echo.
echo To deactivate the virtual environment:
echo   deactivate
echo.
echo To run the MCP server:
echo   venv\Scripts\activate.bat
echo   python mcp_server.py
echo.
echo To run the example:
echo   venv\Scripts\activate.bat
echo   python examples\basic_usage.py
echo.
echo To test the installation:
echo   venv\Scripts\activate.bat
echo   python test_installation.py
echo.
pause 