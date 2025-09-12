@echo off
REM DShield MCP - UV Environment Activation Script for Windows
REM This script activates the UV environment and provides helpful commands

echo === DShield MCP UV Environment ===
echo.

REM Check if UV is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ UV package manager not found!
    echo Please install UV first:
    echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo   # or via pip: pip install uv
    exit /b 1
)

REM Check if UV environment exists
if not exist .venv (
    echo ❌ UV environment not found!
    echo Please run setup_venv.bat first to create the environment.
    exit /b 1
)

REM Activate UV environment
echo 🔧 Activating UV environment...
call .venv\Scripts\activate.bat

REM Show Python version and location
echo ✅ UV environment activated!
python --version
where python

REM Show UV version
uv --version

echo.
echo 📋 Available commands:
echo   uv run python mcp_server.py                    - Run the MCP server
echo   uv run python examples\basic_usage.py          - Run the example
echo   uv run pytest                                  - Run tests
echo   uv run python -m src.tui_launcher              - Run TUI interface
echo   uv run python -m src.server_launcher --transport tcp - Run TCP server
echo   uv add ^<package^>                               - Add new dependency
echo   uv sync                                        - Sync dependencies
echo   uv run ^<command^>                               - Run any command in environment
echo   deactivate                                     - Deactivate virtual environment
echo.

REM Check if .env file exists
if not exist .env (
    echo ⚠️  Warning: .env file not found!
    echo Please copy env.example to .env and configure your settings.
)

echo 🚀 Ready to use DShield MCP with UV!
echo Type 'deactivate' to exit the virtual environment.
