<# 
.SYNOPSIS
    完整啟動腳本 - 一鍵啟動所有服務
    Cloudflare Tunnel + Discord Bot + Web Panel
#>

$ErrorActionPreference = "Stop"

$Domain = "iron-music-bot.cc.cd"
$LocalPort = 1270
$TunnelName = "iron-music-bot"
$BotPath = "D:\windows\desk\mcsmanager\daemon\data\InstanceData\cfca132964454635b9ad6d970bc015b8"

Write-Host "=== Iron Music Bot 完整啟動 ===" -ForegroundColor Cyan

function Check-Process($name) {
    Get-Process -Name $name -ErrorAction SilentlyContinue
}

function Start-Cloudflared {
    Write-Host "☁️  啟動 Cloudflare Tunnel..." -ForegroundColor Cyan
    
    $process = Check-Process "cloudflared"
    if ($process) {
        Write-Host "✅ cloudflared 已在運行 (PID: $($process.Id))" -ForegroundColor Green
        return
    }
    
    # 檢查配置
    $configPath = "C:\cloudflared\config.yml"
    if (-not (Test-Path $configPath)) {
        Write-Host "❌ 找不到配置檔，請先執行 setup_cloudflare.ps1" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🚀 啟動 cloudflared..." -ForegroundColor Cyan
    $proc = Start-Process "cloudflared" -ArgumentList "tunnel --config C:\cloudflared\config.yml run" -PassThru -WindowStyle Hidden
    Start-Sleep 3
    
    $proc = Check-Process "cloudflared"
    if ($proc) {
        Write-Host "✅ cloudflared 已啟動 (PID: $($proc.Id))" -ForegroundColor Green
    } else {
        Write-Host "❌ cloudflared 啟動失敗" -ForegroundColor Red
        exit 1
    }
}

function Start-Bot {
    Write-Host "🤖 啟動 Discord Bot..." -ForegroundColor Cyan
    
    Set-Location $BotPath
    
    # 檢查本地後端
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:1270/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "✅ 本地後端已運行" -ForegroundColor Green
    } catch {
        Write-Host "❌ 本地後端未運行，請先啟動 Bot" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🚀 啟動 Discord Bot..." -ForegroundColor Cyan
    $botProc = Start-Process "python" -ArgumentList "BOT.PY" -PassThru -WorkingDirectory $BotPath
    Write-Host "✅ Bot 已啟動 (PID: $($botProc.Id))" -ForegroundColor Green
    
    return $botProc
}

function Test-Health {
    Write-Host "🔍 執行健康檢查..." -ForegroundColor Cyan
    Start-Sleep 3
    
    try {
        $resp = Invoke-RestMethod -Uri "https://iron-music-bot.cc.cd/health" -TimeoutSec 10
        Write-Host "✅ 公網健康檢查通過" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ 公網健康檢查失敗，檢查 DNS/隧道" -ForegroundColor Yellow
    }
}

# ========== 主流程 ==========
try {
    Start-Cloudflared
    Start-Bot
    Test-Health
    
    Write-Host ""
    Write-Host "=== 所有服務已啟動 ===" -ForegroundColor Green
    Write-Host "前端: https://iron127-iron.github.io/iron-Music/" -ForegroundColor Green
    Write-Host "後端 API: https://iron-music-bot.cc.cd" -ForegroundColor Green
    Write-Host "健康檢查: https://iron-music-bot.cc.cd/health" -ForegroundColor Green
    Write-Host "Discord 登入: https://iron-music-bot.cc.cd/login" -ForegroundColor Green
    Write-Host ""
    Write-Host "按 Ctrl+C 停止所有服務" -ForegroundColor Cyan
    
    # 保持運行
    while ($true) { Start-Sleep 10 }
    
} catch {
    Write-Host "❌ 錯誤: $_" -ForegroundColor Red
    exit 1
} finally {
    Write-Host "`n🛑 正在停止服務..." -ForegroundColor Yellow
    Stop-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    Write-Host "✅ 已停止" -ForegroundColor Green
}