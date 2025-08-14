@echo off
echo ========================================
echo    ScholarBot Setup Script (Windows)
echo ========================================

echo.
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✅ Python found

echo.
echo [2/5] Creating virtual environment...
python -m venv scholarbot_env
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo [3/5] Activating environment and installing dependencies...
call scholarbot_env\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed

echo.
echo [4/5] Creating directory structure...
mkdir data 2>nul
mkdir vectordb 2>nul
mkdir history 2>nul
mkdir temp 2>nul
echo ✅ Directories created

echo.
echo [5/5] Checking Ollama installation...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama not found in PATH
    echo Please install Ollama from: https://ollama.com/download
    echo.
    echo After installing Ollama, run these commands:
    echo   ollama serve
    echo   ollama pull llama3.1:8b
    echo   ollama pull nomic-embed-text
) else (
    echo ✅ Ollama found
    echo.
    echo Would you like to pull the required models now? (y/n)
    set /p pull_models="Enter y to pull models: "
    if /i "%pull_models%"=="y" (
        echo Pulling models... (this may take several minutes)
        ollama pull llama3.1:8b
        ollama pull nomic-embed-text
        echo ✅ Models downloaded
    )
)

echo.
echo ========================================
echo        Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure Ollama is running: ollama serve
echo 2. Start ScholarBot: run_scholarbot.bat
echo.
echo Or manually:
echo   scholarbot_env\Scripts\activate
echo   streamlit run app.py
echo.
pause