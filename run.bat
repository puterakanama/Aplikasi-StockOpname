@echo off
title SFP ^& Cisco Network Stock Opname Tracker
color 0a

set PY_CMD=none
python --version >nul 2>&1 && set PY_CMD=python
if "%PY_CMD%"=="none" py --version >nul 2>&1 && set PY_CMD=py
if "%PY_CMD%"=="none" python3 --version >nul 2>&1 && set PY_CMD=python3

if "%PY_CMD%"=="none" (
    echo [ERROR] Python tidak ditemukan! Harap jalankan 1_SETUP_PERTAMA_KALI.bat
    pause
    exit /b
)

rem Cek modul
%PY_CMD% -c "import uvicorn" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Menginstall dependencies...
    %PY_CMD% -m pip install -r requirements.txt --prefer-binary
)

%PY_CMD% run.py
pause
