@echo off
title Bersihkan Database - Reset Data Kosong
color 0e
echo ===================================================================
echo   PERINGATAN: KOSONGKAN SELURUH DATA PERCOBAAN (RESET KE AWAL)
echo ===================================================================
echo.
echo Tindakan ini akan menghapus 1.200+ barang uji coba, data switch,
echo dan riwayat audit sehingga aplikasi kembali bersih/kosong seperti
echo baru pertama kali dibuat.
echo.
echo CATATAN: Sistem akan otomatis membuat file BACKUP data lama Anda
echo (stockopname_backup_sebelum_reset.db) agar aman jika sewaktu-waktu
echo ingin melihat kembali data uji coba.
echo.
set /p confirm="Ketik Y lalu tekan Enter jika yakin ingin mengosongkan data (Y/N): "

if /i "%confirm%"=="Y" (
    echo.
    echo Sedang mereset database ke kondisi bersih...
    echo.
    python reset_db.py
    color 0a
    echo.
    pause
) else (
    echo.
    echo [DIBATALKAN] Database tidak diubah.
    echo.
    pause
)
