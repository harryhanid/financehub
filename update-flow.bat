@echo off
title Update FLOW Server (Git Pull & Restart)
cd /d "%~dp0"

echo =======================================================
echo   FLOW - Update Server dari GitHub (master)
echo =======================================================
echo.

echo [1/3] Menarik kode terbaru dari GitHub (git pull origin master)...
git pull origin master
if errorlevel 1 (
    echo.
    echo [ERROR] git pull gagal! Periksa koneksi internet atau konflik file lokal.
    pause
    exit /b 1
)

echo.
echo [2/3] Memastikan dependency Python terbaru terpasang...
python -m pip install --user -r app\requirements.txt --quiet

echo.
echo [3/3] Me-restart proses FLOW Server di port 8081...
powershell -NoProfile -Command ^
    "$conns = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue; " ^
    "if ($conns) { " ^
    "  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique; " ^
    "  foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Write-Host ('  -> Proses PID ' + $p + ' dihentikan (Watchdog akan menyalakan ulang otomatis).') } " ^
    "} else { " ^
    "  Write-Host '  -> Server belum berjalan. Menyalakan start-flow.bat...'; " ^
    "  Start-Process cmd.exe -ArgumentList '/c \"' + (Join-Path (Get-Location) 'start-flow.bat') + '\"' " ^
    "}"

echo.
echo =======================================================
echo   Update selesai! Server siap dengan kode terbaru.
echo =======================================================
timeout /t 4
