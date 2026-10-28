@echo off
title Setup Awal Komputer Tetap - FLOW Server
cd /d "%~dp0"

echo =======================================================
echo   FLOW - Setup Awal Komputer Tetap (Tanpa Hak Admin)
echo =======================================================
echo.

:: 1. Pastikan folder storage SOP di Y:\Seagate\Flow\storage\sop tersedia
if exist "Y:\Seagate\Flow" (
    if not exist "Y:\Seagate\Flow\storage\sop" (
        mkdir "Y:\Seagate\Flow\storage\sop"
        echo [OK] Folder Y:\Seagate\Flow\storage\sop dibuat.
    )
    if exist "app\storage\sop" (
        echo [1/3] Menyalin dokumen SOP lokal ke Y:\Seagate\Flow\storage\sop ...
        xcopy "app\storage\sop\*" "Y:\Seagate\Flow\storage\sop\" /E /I /Y /D >nul
        echo [OK] Dokumen SOP tersinkronisasi ke Y:\Seagate\Flow\storage\sop.
    )
) else (
    echo [WARN] Drive Y:\Seagate\Flow tidak ditemukan! Pastikan network drive Y: sudah di-mount.
)

:: 2. Buat Shortcut di Desktop & Startup Folder
echo.
echo [2/3] Membuat shortcut di Desktop & mendaftarkan Auto-Start saat login Windows...
powershell -NoProfile -Command ^
    "$repo = (Get-Location).Path; " ^
    "$wsh = New-Object -ComObject WScript.Shell; " ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$startup = [Environment]::GetFolderPath('Startup'); " ^
    "$s1 = $wsh.CreateShortcut((Join-Path $desktop '1 - Start FLOW Server.lnk')); " ^
    "$s1.TargetPath = (Join-Path $repo 'start-flow.bat'); " ^
    "$s1.WorkingDirectory = $repo; " ^
    "$s1.Save(); " ^
    "$s2 = $wsh.CreateShortcut((Join-Path $desktop '2 - Update FLOW (Git Pull).lnk')); " ^
    "$s2.TargetPath = (Join-Path $repo 'update-flow.bat'); " ^
    "$s2.WorkingDirectory = $repo; " ^
    "$s2.Save(); " ^
    "$s3 = $wsh.CreateShortcut((Join-Path $desktop '3 - Stop FLOW Server.lnk')); " ^
    "$s3.TargetPath = (Join-Path $repo 'stop-flow.bat'); " ^
    "$s3.WorkingDirectory = $repo; " ^
    "$s3.Save(); " ^
    "$sAuto = $wsh.CreateShortcut((Join-Path $startup 'FLOW Production Server.lnk')); " ^
    "$sAuto.TargetPath = (Join-Path $repo 'start-flow.bat'); " ^
    "$sAuto.WorkingDirectory = $repo; " ^
    "$sAuto.Save(); " ^
    "Write-Host '[OK] Shortcut Desktop & Windows Startup berhasil dibuat!'"

:: 3. Pengaturan Power Sleep (Tidak butuh admin untuk user power scheme aktif)
echo.
echo [3/3] Mengatur agar PC tidak sleep saat dicolok listrik (AC Power)...
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 15
echo [OK] Standby timeout saat AC power di-set ke Never (0).

echo.
echo =======================================================
echo   Setup Komputer Tetap Selesai!
echo   Pastikan file app\.env sudah berisi konfigurasi Production.
echo =======================================================
pause
