@echo off
chcp 65001 >nul
title Iron Music Bot - Complete Startup

echo =========================================
echo  Iron Music Bot - Complete Startup
echo =========================================
echo.

REM Check if cloudflared is installed
where cloudflared >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] cloudflared not installed
    echo Download: https://github.com/cloudflared/cloudflared/releases/latest
    pause
    exit /b 1
)

echo [OK] cloudflared found

REM Check if config exists
if not exist "C:\cloudflared\config.yml" (
    echo [ERROR] Config not found. Run setup_cloudflare.ps1 first
    pause
    exit /b 1
)

echo [OK] Config found

REM Start cloudflared tunnel
echo Starting Cloudflare Tunnel...
start /B cloudflared tunnel --config C:\cloudflared\config.yml run

REM Wait for tunnel to start
echo Waiting for tunnel to start...
timeout /t 5 /nobreak >nul

REM Check if tunnel is running
curl -s https://iron-music-bot.cc.cd/health >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Tunnel is running
) else (
    echo [WARN] Tunnel may not be ready yet
)

REM Start the bot
echo.
echo Starting Discord Bot...
cd /d "D:\windows\desk\mcsmanager\daemon\data\InstanceData\cfca132964454635b9ad6d970bc015b8"
python BOT.PY

pause