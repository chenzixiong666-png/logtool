@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 拉取 /data/misc/logd/ 下 shell 用户可读的文件
REM 自动创建带时间戳的输出目录
REM 适用于 Windows + 非 root ADB 环境
REM ============================================================

REM === 获取当前时间，格式化为 2025-10-20_15-42-07 ===
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

set REMOTE_DIR=/data/misc/logd
set LOCAL_DIR=logd_copy_!TIMESTAMP!

echo ================================================
echo  创建本地目录: !LOCAL_DIR!
echo ================================================
if not exist "!LOCAL_DIR!" mkdir "!LOCAL_DIR!"

echo.
echo 扫描设备上可读的文件...
echo -----------------------------------------------

for /f "usebackq delims=" %%F in (`adb shell "for f in %REMOTE_DIR%/*; do [ -r \"$f\" ] && echo $f; done"`) do (
    set FILE=%%F
    for %%A in (!FILE!) do set NAME=%%~nxA
    echo 拉取: !FILE!
    adb pull "!FILE!" "!LOCAL_DIR!\!NAME!" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo    ✅ 成功: !NAME!
    ) else (
        echo    ⚠️ 跳过(权限拒绝或其他错误): !NAME!
    )
)

echo.
echo ================================================
echo  完成。文件已保存到 !LOCAL_DIR!
echo ================================================
pause
