@echo off
echo ========================================
echo      Starting ScholarBot...
echo ========================================

echo.
echo Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama server not responding
    echo Please start Ollama first: ollama serve
    echo.
    echo Starting Ollama automatically...
    start "Ollama" cmd /k "ollama serve"
    echo Waiting for Ollama to start...
    timeout /t 5 >nul
)

echo.
echo Activating Python environment...
if not exist "scholarbot_env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

call scholarbot_env\Scripts\activate.bat

echo.
echo Launching ScholarBot...
echo Access at: http://localhost:8501
echo Press Ctrl+C to stop
echo.

streamlit run app.py

pause