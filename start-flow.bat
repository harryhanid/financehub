@echo off
title FLOW Production Server (Watchdog)
cd /d "%~dp0app"

:: Hapus sinyal stop lama jika ada
if exist ".stop_server" del /f /q ".stop_server"

echo =======================================================
echo   FLOW - Production Server Watchdog (Komputer Tetap)
echo =======================================================
echo.

:: Pastikan drive Y:\ sudah terhubung (tunggu maksimal 15 detik saat baru boot)
if not exist "Y:\Seagate\Flow" (
    echo [INFO] Menunggu network drive Y:\ terhubung...
    timeout /t 10 /nobreak >nul
)

if exist "Y:\Seagate\Flow" (
    echo [OK] Drive Y:\Seagate\Flow terdeteksi.
) else (
    echo [WARN] Drive Y:\Seagate\Flow belum terdeteksi! Pastikan network drive Y: terhubung.
)

set FH_ENV=production

:loop
if exist ".stop_server" (
    del /f /q ".stop_server"
    echo [STOP] Server dihentikan secara normal melalui stop-flow.bat.
    exit /b 0
)

echo.
echo [%date% %time%] Menjalankan FLOW Production Server...
python run_production.py

if exist ".stop_server" (
    del /f /q ".stop_server"
    echo [STOP] Server dihentikan secara normal.
    exit /b 0
)

echo.
echo [%date% %time%] Server berhenti atau sedang di-restart. Menyalakan ulang dalam 3 detik...
echo (Tekan Ctrl+C atau jalankan stop-flow.bat untuk mematikan permanen)
timeout /t 3
goto loop
