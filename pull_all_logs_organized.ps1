# Pull all logs with timestamp-based folder organization
# 一键拉取所有日志，自动按时间戳分类

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$baseDir = "logs_$timestamp"

# Create base directory
New-Item -ItemType Directory -Path $baseDir -Force | Out-Null
Write-Host "================================" -ForegroundColor Cyan
Write-Host "日志拉取工具 - 时间戳版本" -ForegroundColor Cyan
Write-Host "时间戳: $timestamp" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Pull Android system logs (/data/misc/logd/)
$logdDir = "$baseDir\system_logd_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
New-Item -ItemType Directory -Path $logdDir -Force | Out-Null

Write-Host "================================" -ForegroundColor Yellow
Write-Host "1. 拉取 Android 系统日志 (/data/misc/logd/)" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

$files = adb shell "ls -1 /data/misc/logd/ 2>&1" | Where-Object {$_ -and $_ -notmatch "^total"}
foreach ($file in $files) {
    $file = $file.Trim()
    if ($file) {
        Write-Host "拉取: /data/misc/logd/$file"
        adb pull "/data/misc/logd/$file" "$logdDir\$file" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [✓] 成功: $file" -ForegroundColor Green
        } else {
            Write-Host "  [✗] 失败: $file" -ForegroundColor Red
        }
    }
}

Write-Host ""

# 2. Pull SwitchBot logs (/data/local/switchbot/log/)
$switchbotDir = "$baseDir\switchbot_log_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
New-Item -ItemType Directory -Path $switchbotDir -Force | Out-Null

Write-Host "================================" -ForegroundColor Yellow
Write-Host "2. 拉取 SwitchBot 应用日志 (/data/local/switchbot/log/)" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

$files = adb shell "ls -1 /data/local/switchbot/log/ 2>&1" | Where-Object {$_ -and $_ -notmatch "^total"}
foreach ($file in $files) {
    $file = $file.Trim()
    if ($file) {
        Write-Host "拉取: /data/local/switchbot/log/$file"
        adb pull "/data/local/switchbot/log/$file" "$switchbotDir\$file" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [✓] 成功: $file" -ForegroundColor Green
        } else {
            Write-Host "  [✗] 失败: $file" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "完成！" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "日志已保存到: $baseDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "目录结构:" -ForegroundColor Cyan
Write-Host " $baseDir\" -ForegroundColor Cyan
Write-Host "  ├── system_logd_$timestamp\"
Write-Host "  │   ├── logcat"
Write-Host "  │   ├── logcat.001"
Write-Host "  │   └── logcat.002"
Write-Host "  └── switchbot_log_$timestamp\"
Write-Host "      ├── 2026-04-10.log"
Write-Host "      ├── central-2026-04-10.log"
Write-Host "      └── dockerd.log"
Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
