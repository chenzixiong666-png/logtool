# LogTool - AI Hub Show 日志采集工具

一键从 ADB 设备拉取日志、收集崩溃报告、录制性能数据并打包的工具集。

## 功能概览

| 功能 | 说明 |
|------|------|
| 📝 开启日志 | 启动设备端 logcatd 服务 |
| 📂 近期日志 | 拉取昨天+今天的日志文件，含 ANR |
| 📂 全部日志 | 拉取设备上所有日志文件，含 ANR |
| 🐛 崩溃日志 | 执行 adb bugreport 收集系统全量信息 |
| ⚡ 性能日志 | Perfetto 录制（可配置时长、数据类别） |

## 文件说明

| 文件 | 用途 |
|------|------|
| `log-tool.py` | 主程序 GUI（Tkinter） |
| `pull_all_logs.py` | 批量拉取设备日志 + ANR 收集 |
| `startLogcatd.bat` | 启动设备端 logcatd 服务 |
| `build_exe.py` | PyInstaller 打包为 .exe |

## 使用方法

### 方式一：直接运行（需要 Python 3.x + ADB）
```bash
python log-tool.py
```

### 方式二：使用打包好的 EXE
将以下三个文件放在同一目录：
- `LogTool.exe`
- `pull_all_logs.py`
- `startLogcatd.bat`

双击 `LogTool.exe` 即可。

### 自己打包
```bash
python build_exe.py
```

## 特性

- ✅ 无黑色控制台弹窗（CREATE_NO_WINDOW）
- ✅ ADB 设备连接预检查（未连接/未授权/离线诊断）
- ✅ 7 种常见 ADB 错误智能诊断
- ✅ Perfetto 配置持久化（时长、类别、自定义类别）
- ✅ ANR 无文件时留占位文件而非静默删除
- ✅ 日志打包为 zip

## 依赖

- Python 3.x
- ADB (Android Debug Bridge)
- PyInstaller（打包时需要）

## 版本

当前版本：v1.1.0 (2026-05-15)

### 更新日志

**v1.1.0** (2026-05-15)
- 按钮重命名：“崩溃日志” + “性能日志”
- Perfetto 配置页简化为网格布局 + ✓ 打勾
- 所有按钮加入 ADB 设备预检查
- 7 种 ADB 错误智能诊断（未连接/未授权/离线/权限不足/空间不足/只读/连接拒绝）
- 隐藏子进程黑色窗口
- 超时提示增加详细原因和建议

**v1.0.0** (2026-04-28)
- 初始版本：日志开启 + 拉取 + bugreport + Perfetto
