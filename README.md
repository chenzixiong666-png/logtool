# LogTool - AI Hub Show 日志采集工具

一键从 ADB 设备拉取日志并打包的工具集。

## 文件说明

| 文件 | 用途 |
|------|------|
| `log-tool.py` | 主程序，支持近期日志/全量日志/logcat 实时抓取 |
| `pull_all_logs.py` | 批量拉取设备上所有日志文件 |
| `startLogcatd.bat` | 启动设备端 logcatd 服务 |
| `build_exe.py` | PyInstaller 打包为 .exe |
| `LogTool.spec` | PyInstaller 构建配置 |

## 使用方法

### 直接运行（需要 Python 3.x + ADB）
```bash
python log-tool.py
```

### 打包为 EXE
```bash
python build_exe.py
```

## 依赖

- Python 3.x
- ADB (Android Debug Bridge)
- PyInstaller（打包时需要）

## 版本

当前版本：1.0.0
