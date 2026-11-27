@echo off
title Setup Aplikasi Stock Opname ^& Cisco Tracker
color 0b
echo ===================================================================
echo   SETUP DEPENDENCIES APLIKASI STOCK OPNAME ^& CISCO TRACKER
echo ===================================================================
echo.

set PY_CMD=none

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :FOUND
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto :FOUND
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python3
    goto :FOUND
)

:NOT_FOUND
color 0c
echo [ERROR] Python tidak terdeteksi di laptop ini!
echo.
echo Silakan install Python versi STABLE (disarankan Python 3.12 atau 3.13):
echo 1. Download dari website resmi: https://www.python.org/downloads/
echo 2. PENTING: Saat install, centang pilihan "Add python.exe to PATH"
echo.
pause
exit /b

:FOUND
echo [1/3] Memeriksa versi Python di laptop ini...
%PY_CMD% --version
echo.
%PY_CMD% -c "import sys; sys.exit(1 if sys.version_info >= (3, 14) else 0)"
if %errorlevel% neq 0 (
    color 0e
    echo [PERHATIAN] Anda terdeteksi menggunakan Python versi Alpha/Development.
    echo Versi development (seperti 3.14/3.15) belum memiliki pre-built wheels di internet,
    echo sehingga Windows meminta instalasi "Microsoft Visual C++ Build Tools".
    echo.
    echo SANGAT DISARANKAN menginstall versi STABLE: Python 3.12 atau Python 3.13
    echo Download: https://www.python.org/downloads/ (Klik tombol kuning besar)
    echo.
)

echo [2/3] Menginstall library yang dibutuhkan (FastAPI, Pandas, Openpyxl, dll)...
echo       Harap tunggu beberapa saat...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt --prefer-binary
if %errorlevel% neq 0 (
    color 0c
    echo.
    echo ===================================================================
    echo [KENDALA DETEKSI] Gagal menginstall library di Python versi ini.
    echo.
    echo Penyebab: Laptop menggunakan Python versi Alpha / Pre-release (misal 3.15).
    echo Solusi Cepat dan Pasti Berhasil:
    echo 1. Buka "Installed Apps" / "Control Panel" di Windows.
    echo 2. Uninstall Python versi 3.15 tersebut.
    echo 3. Buka https://www.python.org/downloads/ lalu download versi
    echo    STABLE resmi: Python 3.12 atau Python 3.13 (tombol kuning).
    echo 4. Saat install, centang "Add python.exe to PATH".
    echo 5. Jalankan kembali file "1_SETUP_PERTAMA_KALI.bat" ini.
    echo ===================================================================
    echo.
    pause
    exit /b
)
echo.
echo [3/3] Memeriksa dan memverifikasi Database lokal (stockopname.db)...
%PY_CMD% database.py
echo.
color 0a
echo ===================================================================
echo   [BERHASIL] Setup selesai! Aplikasi siap digunakan.
echo   Selanjutnya silakan double-click file "2_JALANKAN_APLIKASI.bat"
echo ===================================================================
echo.
pause
