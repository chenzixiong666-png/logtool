#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pull logs organized by timestamp
Auto-compress logs after pulling
Uses explicit output directory passed by LogTool
Only pulls files updated yesterday or today (Beijing Time)
"""

import os
import sys
import re
import subprocess
import shutil
from datetime import datetime, timezone, timedelta

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        print(f"Error: {e}")
        return "", 1

def get_bjt_now():
    """获取北京时间（UTC+8）"""
    return datetime.now(timezone(timedelta(hours=8)))

def is_recent_bjt_date(date_str):
    """按北京时间判断文件更新时间是否为今天或昨天"""
    try:
        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False

    today = get_bjt_now().date()
    yesterday = today - timedelta(days=1)
    return file_date in {today, yesterday}

def parse_ls_line(line):
    """解析 adb shell ls -l 输出，提取日期和文件名"""
    line = line.strip()
    if not line or line.startswith("total "):
        return None, None

    match = re.match(r"^\S+\s+\d+\s+\S+\s+\S+\s+\d+\s+(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+(.+)$", line)
    if not match:
        return None, None

    return match.group(1), match.group(2).strip()

def main():
    # 参数：python pull_all_logs.py <save_root> [--all]
    all_logs = '--all' in sys.argv[1:]
    path_args = [arg for arg in sys.argv[1:] if arg != '--all']

    # 保存根目录优先使用参数，未传入时退回当前工作目录
    save_root = path_args[0] if path_args else os.getcwd()
    save_root = os.path.abspath(save_root)
    os.makedirs(save_root, exist_ok=True)

    # 使用北京时间生成时间戳
    timestamp = get_bjt_now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # 在指定保存目录下创建时间戳目录
    base_dir = os.path.join(save_root, f"logs_{timestamp}")
    
    print("=" * 50)
    print("Pull Logs - Timestamp-based with Compression")
    print(f"Timestamp (BJT): {timestamp}")
    print(f"Save location: {save_root}")
    print("=" * 50)
    print()
    
    # Create directories
    os.makedirs(base_dir, exist_ok=True)
    system_logd_dir = os.path.join(base_dir, "system_logd")
    switchbot_dir = os.path.join(base_dir, "switchbot_log")
    os.makedirs(system_logd_dir, exist_ok=True)
    os.makedirs(switchbot_dir, exist_ok=True)
    
    print(f"[OK] Created: {base_dir}")
    print()
    
    # 1. Pull Android system logs
    print("=" * 50)
    print("1. Pulling Android System Logs (/data/misc/logd/)")
    print("=" * 50)
    
    cmd = 'adb shell "ls -l /data/misc/logd/"'
    files, _ = run_cmd(cmd)
    if files:
        for line in files.split('\n'):
            file_date, file = parse_ls_line(line)
            if not file:
                continue
            if not all_logs and not is_recent_bjt_date(file_date):
                print(f"Skipping old file: {file} ({file_date})")
                continue
            if file == 'event-log-tags' or file == 'logcat.id':
                print(f"Skipping metadata file: {file}")
                continue

            print(f"Pulling: /data/misc/logd/{file} ({file_date})")
            cmd = f'adb pull "/data/misc/logd/{file}" "{system_logd_dir}\\{file}"'
            _, code = run_cmd(cmd)
            if code == 0:
                print(f"  [OK] Success: {file}")
            else:
                print(f"  [X] Failed: {file}")
    
    print()
    
    # 2. Pull SwitchBot logs
    print("=" * 50)
    print("2. Pulling SwitchBot App Logs (/data/local/switchbot/log/)")
    print("=" * 50)
    
    cmd = 'adb shell "ls -l /data/local/switchbot/log/"'
    files, _ = run_cmd(cmd)
    if files:
        for line in files.split('\n'):
            file_date, file = parse_ls_line(line)
            if not file:
                continue
            if not all_logs and not is_recent_bjt_date(file_date):
                print(f"Skipping old file: {file} ({file_date})")
                continue

            print(f"Pulling: /data/local/switchbot/log/{file} ({file_date})")
            cmd = f'adb pull "/data/local/switchbot/log/{file}" "{switchbot_dir}\\{file}"'
            _, code = run_cmd(cmd)
            if code == 0:
                print(f"  [OK] Success: {file}")
            else:
                print(f"  [X] Failed: {file}")
    
    print()
    
    # 3. Create compressed version
    print("=" * 50)
    print("3. Creating Compressed Archive")
    print("=" * 50)
    
    zip_name = f"logs_{timestamp}"
    zip_path = os.path.join(save_root, zip_name)
    
    try:
        print(f"Compressing to: {zip_name}.zip")
        shutil.make_archive(zip_path, 'zip', base_dir, '.')
        print(f"  [OK] Compressed successfully: {zip_name}.zip")
    except Exception as e:
        print(f"  [X] Compression failed: {e}")
    
    print()
    print("=" * 50)
    print("Done!")
    print("=" * 50)
    print()
    
    print(f"Uncompressed logs: {base_dir}")
    print(f"Compressed archive: {zip_path}.zip")
    print()

if __name__ == "__main__":
    main()
