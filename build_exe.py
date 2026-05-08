#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包日志工具为独立 EXE（Windows）
说明：当前脚本仅用于 Windows + PyInstaller。macOS 请单独使用 py2app/Briefcase 打包 .app。
"""

import os
import shutil
import subprocess
import sys

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(workspace, "dist")
    build_dir = os.path.join(workspace, "build")
    
    print("=" * 60)
    print("Log Tool - PyInstaller Package")
    print("=" * 60)
    print()
    
    # 清理旧的构建
    print("[CLEAN] Cleaning old build files...")
    for dir_to_clean in [dist_dir, build_dir, os.path.join(workspace, "LogTool.spec")]:
        if os.path.exists(dir_to_clean):
            if os.path.isdir(dir_to_clean):
                shutil.rmtree(dir_to_clean)
                print(f"  Deleted: {dir_to_clean}")
            else:
                os.remove(dir_to_clean)
                print(f"  Deleted: {dir_to_clean}")
    
    print()
    print("[BUILD] Packaging with PyInstaller...")
    
    # 使用完整路径
    pyinstaller_exe = r"C:\Users\woan\AppData\Roaming\Python\Python314\Scripts\pyinstaller.exe"
    
    if not os.path.exists(pyinstaller_exe):
        print(f"[ERROR] PyInstaller not found at: {pyinstaller_exe}")
        sys.exit(1)
    
    pyinstaller_cmd = [
        pyinstaller_exe,
        "--onefile",
        "--windowed",
        "--name=LogTool",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "log-tool.py"
    ]
    
    try:
        result = subprocess.run(
            pyinstaller_cmd,
            cwd=workspace,
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print("\n[ERROR] Packaging failed!")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("[DONE] Packaging complete!")
    print("=" * 60)
    print()
    
    exe_path = os.path.join(dist_dir, "LogTool.exe")
    if os.path.exists(exe_path):
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"[OK] EXE file: {exe_path}")
        print(f"[OK] File size: {exe_size:.2f} MB")
        print()
        print("Run directly by double-clicking:")
        print(f"  {exe_path}")
        print()
        print("[INFO] You can also copy this to Desktop or Program Files")
    else:
        print("[ERROR] EXE file not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
