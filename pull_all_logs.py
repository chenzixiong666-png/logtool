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

def pull_private_dir(pkg, remote_dir, dest_dir):
    """拉取 app 私有目录下的所有文件（/data/user/0/<pkg>/files/mmkv 等）。
    返回成功拉取的文件数。依次尝试 root 直拉 / run-as / su 。
    """
    # 先列出目录下的文件名（优先 root ls，其次 run-as ls）
    names = []
    out, code = run_cmd(f'adb shell "ls -1 {remote_dir} 2>/dev/null"')
    if code == 0 and out:
        names = [l.strip() for l in out.split("\n") if l.strip()]
    if not names:
        rel = remote_dir.split(f"/{pkg}/", 1)[-1]  # files/mmkv
        out, code = run_cmd(f'adb shell "run-as {pkg} ls -1 {rel} 2>/dev/null"')
        if code == 0 and out:
            names = [l.strip() for l in out.split("\n") if l.strip()]
    if not names:
        return 0

    count = 0
    for name in names:
        remote = f"{remote_dir}/{name}"
        dest = os.path.join(dest_dir, name)
        if pull_private_file(pkg, remote, dest):
            count += 1
            print(f"    [OK] {name}")
        else:
            print(f"    [X]  {name}")
    return count


def pull_private_file(pkg, remote, dest):
    """拉取 app 私有目录文件（/data/user/0/<pkg>/...）。
    普通 adb pull 无权限，依次尝试：
      1) root 直拉（adb root 后 adb pull）
      2) run-as <pkg> + cat 重定向到 /sdcard 再 pull（debuggable 包可用）
      3) su -c cat 重定向（已 root 但未 adb root）
    成功返回 True。
    """
    # 方式1：root 直拉
    _, code = run_cmd(f'adb pull "{remote}" "{dest}"')
    if code == 0 and os.path.exists(dest):
        return True

    tmp_remote = f"/sdcard/_mmkv_pull_tmp"

    # 方式2：run-as（仅 debuggable 包，工作目录为 app 私有根）
    rel = remote.split(f"/{pkg}/", 1)[-1]  # files/mmkv/mmkv.default
    _, c1 = run_cmd(f'adb shell "run-as {pkg} cat {rel} > {tmp_remote}"')
    if c1 == 0:
        _, c2 = run_cmd(f'adb pull "{tmp_remote}" "{dest}"')
        run_cmd(f'adb shell "rm -f {tmp_remote}"')
        if c2 == 0 and os.path.exists(dest):
            return True

    # 方式3：su -c cat
    _, c3 = run_cmd(f'adb shell "su -c \'cat {remote}\' > {tmp_remote}"')
    if c3 == 0:
        _, c4 = run_cmd(f'adb pull "{tmp_remote}" "{dest}"')
        run_cmd(f'adb shell "rm -f {tmp_remote}"')
        if c4 == 0 and os.path.exists(dest):
            return True

    return False


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
    mmkv_dir = os.path.join(base_dir, "mmkv")
    anr_dir = os.path.join(base_dir, "anr")
    os.makedirs(system_logd_dir, exist_ok=True)
    os.makedirs(switchbot_dir, exist_ok=True)
    os.makedirs(mmkv_dir, exist_ok=True)
    os.makedirs(anr_dir, exist_ok=True)
    
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

    # 3. Pull MMKV config files (app private dirs, whole mmkv/ folder)
    print("=" * 50)
    print("3. Pulling MMKV Config Files (app private data)")
    print("=" * 50)

    mmkv_pkgs = ["com.theswitchbot.aihub", "com.theswitchbot.central"]
    for pkg in mmkv_pkgs:
        remote_dir = f"/data/user/0/{pkg}/files/mmkv"
        dest_dir = os.path.join(mmkv_dir, pkg)
        os.makedirs(dest_dir, exist_ok=True)
        print(f"Pulling: {remote_dir}/")
        n = pull_private_dir(pkg, remote_dir, dest_dir)
        if n > 0:
            print(f"  [OK] Success: {pkg} ({n} files)")
        else:
            print(f"  [X] Failed: {pkg} (no root / run-as not permitted? or empty dir)")
            # 未拉到数据时写提示文件
            readme = os.path.join(dest_dir, "_NO_MMKV_FOUND.txt")
            with open(readme, 'w', encoding='utf-8') as f:
                f.write(f"检查时间: {get_bjt_now().strftime('%Y-%m-%d %H:%M:%S')} (BJT)\n")
                f.write(f"未能拉取 {remote_dir} （设备未 root / 该目录不存在 / 包未安装）\n")
            print(f"  [INFO] created _NO_MMKV_FOUND.txt placeholder for {pkg}")
    print()

    # 4. Pull ANR traces (/data/anr/)
    print("=" * 50)
    print("4. Pulling ANR Traces (/data/anr/)")
    print("=" * 50)

    # ANR 目录需要 root 权限
    root_out, root_code = run_cmd('adb root')
    if root_code == 0:
        print(f"  adb root: {root_out}")
        if "already running as root" not in root_out:
            # adb root 会重启 adbd，等待设备重连
            print("  Waiting for device reconnect...")
            run_cmd('adb wait-for-device')

        cmd = 'adb shell "ls -la /data/anr/"'
        anr_files, anr_code = run_cmd(cmd)

        if anr_code != 0 or not anr_files or "No such file" in anr_files:
            print("  [INFO] /data/anr/ does not exist or is empty - no ANR traces")
        else:
            pulled = 0
            for line in anr_files.split('\n'):
                line = line.strip()
                if not line or line.startswith('total'):
                    continue
                parts = line.split()
                if len(parts) < 7:
                    continue
                fname = parts[-1]
                if fname in ('.', '..'):
                    continue

                remote = f"/data/anr/{fname}"
                local = os.path.join(anr_dir, fname)
                print(f"Pulling: {remote}")
                _, code = run_cmd(f'adb pull "{remote}" "{local}"')
                if code == 0:
                    print(f"  [OK] Success: {fname}")
                    pulled += 1
                else:
                    print(f"  [X] Failed: {fname}")

            if pulled == 0:
                print("  [INFO] No ANR files pulled")
            else:
                print(f"  [OK] Pulled {pulled} ANR file(s)")
    else:
        print(f"  [WARN] adb root failed ({root_out}) - skipping ANR collection")

    # 保留 anr 目录，即使为空也给用户提示
    if not os.listdir(anr_dir):
        readme = os.path.join(anr_dir, "_NO_ANR_FOUND.txt")
        with open(readme, 'w', encoding='utf-8') as f:
            f.write(f"检查时间: {get_bjt_now().strftime('%Y-%m-%d %H:%M:%S')} (BJT)\n")
            f.write("设备 /data/anr/ 目录为空，当前没有 ANR 记录\n")
        print("  [INFO] No ANR files found, created _NO_ANR_FOUND.txt as placeholder")
    print()

    # 5. Create compressed version
    print("=" * 50)
    print("5. Creating Compressed Archive")
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
