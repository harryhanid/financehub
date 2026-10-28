@echo off
title Stop FLOW Server
cd /d "%~dp0app"

echo =======================================================
echo   FLOW - Menghentikan Production Server
echo =======================================================
echo.

:: Buat file penanda agar loop watchdog di start-flow.bat berhenti
echo stop > ".stop_server"

powershell -NoProfile -Command ^
    "$conns = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue; " ^
    "if ($conns) { " ^
    "  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique; " ^
    "  foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Write-Host ('[OK] Proses server PID ' + $p + ' dihentikan.') } " ^
    "} else { " ^
    "  Write-Host '[INFO] Tidak ada proses server yang aktif di port 8081.' " ^
    "}"

timeout /t 3
