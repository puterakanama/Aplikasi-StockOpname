@echo off
title SFP ^& Cisco Network Stock Opname Tracker
color 0a
echo ===================================================================
echo   MENJALANKAN APLIKASI STOCK OPNAME ^& CISCO TRACKER
echo ===================================================================
echo.

set PY_CMD=none

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :CHECK_MODULES
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto :CHECK_MODULES
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python3
    goto :CHECK_MODULES
)

color 0c
echo [ERROR] Python belum terinstall atau belum masuk PATH di laptop ini!
echo.
echo Silakan install Python 3.12 atau 3.13 dari: https://www.python.org/downloads/
echo (Pastikan centang "Add python.exe to PATH" saat install)
echo.
pause
exit /b

:CHECK_MODULES
rem Periksa apakah library utama (uvicorn, fastapi, pandas) sudah terinstall
%PY_CMD% -c "import uvicorn, fastapi, pandas, openpyxl" >nul 2>&1
if %errorlevel% equ 0 (
    goto :RUN
)

color 0e
echo [INFO] Library pendukung (uvicorn, fastapi, dll) belum terinstall.
echo       Sedang menginstall otomatis via pip, mohon tunggu sebentar...
echo.
%PY_CMD% -m pip install -r requirements.txt --prefer-binary
if %errorlevel% neq 0 (
    color 0c
    echo.
    echo ===================================================================
    echo [ERROR] Gagal menginstall library otomatis!
    echo.
    echo Kemungkinan penyebab:
    echo 1. Laptop belum terhubung ke internet saat instalasi.
    echo 2. Terinstall Python versi Alpha/Dev (seperti Python 3.15).
    echo.
    echo Solusi Cepat:
    echo - Gunakan Python resmi STABLE (Python 3.12 atau Python 3.13)
    echo   Download di: https://www.python.org/downloads/ (tombol kuning)
    echo - Jalankan file "1_SETUP_PERTAMA_KALI.bat" untuk melihat detailnya.
    echo ===================================================================
    echo.
    pause
    exit /b
)
echo [OK] Seluruh library berhasil diinstall!
echo.

:RUN
color 0a
%PY_CMD% run.py
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Server dihentikan.
    pause
)
