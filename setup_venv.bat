@echo off
REM DShield MCP - UV Environment Setup Script for Windows
REM This script sets up the project using UV package manager

echo === DShield MCP UV Environment Setup ===
echo.

REM Check if UV is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: UV package manager is not installed
    echo Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo   # or via pip: pip install uv
    exit /b 1
)

echo ✅ UV package manager found
uv --version

REM Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: Python 3.10 or higher is required but not found
    echo Please install Python 3.10+ or let UV install it automatically
    exit /b 1
)

echo ✅ Python found
python --version

REM Install project dependencies using UV
echo 📦 Installing project dependencies with UV...
uv sync

REM Install development dependencies
echo 📥 Installing development dependencies...
uv sync --group dev

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.example .env
    echo ⚠️  Please edit .env file with your configuration
) else (
    echo ✅ .env file already exists
)

echo.
echo === Setup Complete! ===
echo.
echo To activate the UV environment:
echo   .venv\Scripts\activate.bat
echo   # or use: uv run ^<command^>
echo.
echo To deactivate the virtual environment:
echo   deactivate
echo.
echo To run the MCP server:
echo   uv run python mcp_server.py
echo   # or: .venv\Scripts\activate.bat ^&^& python mcp_server.py
echo.
echo To run the example:
echo   uv run python examples\basic_usage.py
echo.
echo To run tests:
echo   uv run pytest
echo.
echo To run the TUI interface:
echo   uv run python -m src.tui_launcher
echo.
echo To run the TCP server:
echo   uv run python -m src.server_launcher --transport tcp