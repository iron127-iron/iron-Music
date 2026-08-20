<# 
.SYNOPSIS
    Cloudflare Tunnel 一鍵設置腳本
    執行前請確認已安裝 cloudflared 並登入
#>

param(
    [string]$Domain = "iron-music-bot.cc.cd",
    [int]$LocalPort = 1270,
    [string]$TunnelName = "iron-music-bot"
)

Write-Host "=== Cloudflare Tunnel 自動設置 ===" -ForegroundColor Cyan

# 檢查 cloudflared
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Write-Host "❌ 未安裝 cloudflared" -ForegroundColor Red
    Write-Host "下載: https://github.com/cloudflared/cloudflared/releases/latest" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ cloudflared 已安裝: $($cloudflared.Source)" -ForegroundColor Green

# 登入檢查
$credPath = "$env:USERPROFILE\.cloudflared"
$certFiles = Get-ChildItem "$credPath\*.pem" -ErrorAction SilentlyContinue
if (-not $certFiles) {
    Write-Host "🔐 需要登入 Cloudflare..." -ForegroundColor Yellow
    cloudflared tunnel login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 登入失敗" -ForegroundColor Red
        exit 1
    }
}

# 建立隧道
Write-Host "🔧 建立隧道: $TunnelName" -ForegroundColor Cyan
$tunnelOutput = cloudflared tunnel create $TunnelName 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($tunnelOutput -match "already exists") {
        Write-Host "⚠️ 隧道已存在，取得 ID..." -ForegroundColor Yellow
    } else {
        Write-Host "❌ 建立失敗: $tunnelOutput" -ForegroundColor Red
        exit 1
    }
}

# 取得隧道 ID
$tunnels = cloudflared tunnel list --output json | ConvertFrom-Json
$tunnel = $tunnels | Where-Object { $_.name -eq $TunnelName }
if (-not $tunnel) {
    Write-Host "❌ 找不到隧道" -ForegroundColor Red
    exit 1
}

$tunnelId = $tunnel.id
$credFile = "$env:USERPROFILE\.cloudflared\$tunnelId.json"
Write-Host "✅ 隧道 ID: $tunnelId" -ForegroundColor Green

# 配置 DNS
Write-Host "🌐 設定 DNS: $Domain" -ForegroundColor Cyan
cloudflared tunnel route dns $TunnelName $Domain

# 產生配置檔
$configDir = "C:\cloudflared"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
$configPath = "$configDir\config.yml"
$credPath = "$env:USERPROFILE\.cloudflared\$tunnelId.json"

$config = @"
tunnel: $tunnelId
credentials-file: $credPath

ingress:
  - hostname: $Domain
    service: http://localhost:1270
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      keepAliveTimeout: 90s
  - service: http_status:404
"@

$config | Out-File -FilePath $configPath -Encoding utf8
Write-Host "✅ 配置檔已建立: $configPath" -ForegroundColor Green

# 安裝 Windows 服務
Write-Host "🔧 安裝 Windows 服務..." -ForegroundColor Cyan
cloudflared service install --config "$configPath"

# 啟動服務
Write-Host "▶️ 啟動服務..." -ForegroundColor Cyan
net start cloudflared 2>$null
Start-Sleep 2

# 驗證
Write-Host "🔍 驗證連線..." -ForegroundColor Cyan
Start-Sleep 3
try {
    $resp = Invoke-RestMethod -Uri "https://$Domain/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "✅ 健康檢查通過: $($resp | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 健康檢查失敗，請稍等幾秒再試" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 設置完成 ===" -ForegroundColor Cyan
Write-Host "域名: https://$Domain" -ForegroundColor Green
Write-Host "Discord Redirect URI: https://$Domain/callback" -ForegroundColor Green
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "1. 更新 Discord Developer Portal Redirect URI"
Write-Host "2. 啟動 Bot: python BOT.PY"
Write-Host "3. 訪問前端: https://iron127-iron.github.io/iron-Music/"