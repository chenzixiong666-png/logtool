@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 拉取多个日志目录
REM 1. /data/misc/logd/ - Android 系统日志
REM 2. /data/local/switchbot/log - SwitchBot 应用日志
REM 自动创建带时间戳的输出目录
REM 适用于 Windows + ADB 环境
REM ============================================================

REM === 获取当前时间，格式化为 2026-04-10_17-58-00 ===
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set YYYY=%%d
    set MM=%%b
    set DD=%%c
)
for /f "tokens=1-3 delims=: " %%a in ('time /t') do (
    set HH=%%a
    set MN=%%b
)
REM 处理 12 小时制 AM/PM 的情况
set HH=!HH: =0!
set HH=!HH:AM=!
set HH=!HH:PM=!
set TIMESTAMP=!YYYY!-!MM!-!DD!_!HH!-!MN!-00

set LOCAL_DIR=logs_!TIMESTAMP!

echo ================================================
echo  日志拉取工具 - 双日志版本
echo  时间戳: !TIMESTAMP!
echo ================================================
echo.

REM === 创建本地目录 ===
if not exist "!LOCAL_DIR!" mkdir "!LOCAL_DIR!"
echo [✓] 创建本地目录: !LOCAL_DIR!

REM === 拉取 /data/misc/logd/ ===
echo.
echo ================================================
echo  1. 拉取 Android 系统日志 (/data/misc/logd/)
echo ================================================

set LOGD_DIR=!LOCAL_DIR!\system_logd
if not exist "!LOGD_DIR!" mkdir "!LOGD_DIR!"

for /f "usebackq delims=" %%F in (`adb shell "ls -1 /data/misc/logd/ 2^>^&1"`) do (
    set FILE=%%F
    if not "!FILE!"=="" (
        echo 拉取: /data/misc/logd/!FILE!
        adb pull "/data/misc/logd/!FILE!" "!LOGD_DIR!\!FILE!" >nul 2>&1
        if !errorlevel! EQU 0 (
            echo    [✓] 成功: !FILE!
        ) else (
            echo    [✗] 失败: !FILE!
        )
    )
)

REM === 拉取 /data/local/switchbot/log/ ===
echo.
echo ================================================
echo  2. 拉取 SwitchBot 应用日志 (/data/local/switchbot/log/)
echo ================================================

set SWITCHBOT_DIR=!LOCAL_DIR!\switchbot_log
if not exist "!SWITCHBOT_DIR!" mkdir "!SWITCHBOT_DIR!"

for /f "usebackq delims=" %%F in (`adb shell "ls -1 /data/local/switchbot/log/ 2^>^&1"`) do (
    set FILE=%%F
    if not "!FILE!"=="" (
        echo 拉取: /data/local/switchbot/log/!FILE!
        adb pull "/data/local/switchbot/log/!FILE!" "!SWITCHBOT_DIR!\!FILE!" >nul 2>&1
        if !errorlevel! EQU 0 (
            echo    [✓] 成功: !FILE!
        ) else (
            echo    [✗] 失败: !FILE!
        )
    )
)

REM === 完成 ===
echo.
echo ================================================
echo  完成！
echo  日志已保存到: !LOCAL_DIR!
echo ================================================
echo.
echo 目录结构:
echo  !LOCAL_DIR!\
echo    ├── system_logd\       (Android 系统日志)
echo    └── switchbot_log\     (SwitchBot 应用日志)
echo.
pause
