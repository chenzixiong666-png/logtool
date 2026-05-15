import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import subprocess
import threading
import shutil

# Windows 下隐藏子进程黑色控制台窗口
_SP_FLAGS = {}
if os.name == 'nt':
    _SP_FLAGS['creationflags'] = subprocess.CREATE_NO_WINDOW


def _run_sp(*args, **kwargs):
    """subprocess.run 包装，自动隐藏控制台窗口"""
    kwargs.update(_SP_FLAGS)
    return subprocess.run(*args, **kwargs)


class LogToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("日志管理工具")
        self.root.geometry("780x550")
        self.root.resizable(False, False)
        
        # 配置文件路径（保存到桌面）
        desktop = os.path.expanduser("~/Desktop")
        self.config_file = os.path.join(desktop, "LogTool_config.json")
        self.default_save_path = os.path.join(desktop, "logs")
        self.load_config()
        
        # 脚本路径 - 处理打包后的情况
        # 运行目录优先使用 exe 所在目录，避免把保存路径误当成脚本执行目录
        self.runtime_dir = self.get_runtime_dir()
        if hasattr(sys, '_MEIPASS'):
            # 打包后的临时解压目录（兼容旧版本逻辑）
            self.workspace = sys._MEIPASS
        else:
            # 开发环境
            self.workspace = os.path.dirname(os.path.abspath(__file__))
        
        self.startlogcatd_script = os.path.join(self.runtime_dir, "startLogcatd.bat")
        self.pull_logs_script = os.path.join(self.runtime_dir, "pull_all_logs.py")
        
        # 设置样式
        self.root.configure(bg="#f0f0f0")
        style = ttk.Style()
        style.theme_use('clam')
        
        # 主框架
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="日志管理工具", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 按键区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=8)
        
        self.start_btn = ttk.Button(
            button_frame,
            text="🟢 开启日志",
            command=self.start_logging,
            width=20
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.get_btn = ttk.Button(
            button_frame,
            text="📥 近期日志",
            command=self.get_logs,
            width=18
        )
        self.get_btn.pack(side=tk.LEFT, padx=2)

        self.get_all_btn = ttk.Button(
            button_frame,
            text="🗂 全部日志",
            command=self.get_all_logs,
            width=18
        )
        self.get_all_btn.pack(side=tk.LEFT, padx=2)
        
        self.bugreport_btn = ttk.Button(
            button_frame,
            text="🐛 崩溃日志",
            command=self.collect_bugreport,
            width=18
        )
        self.bugreport_btn.pack(side=tk.LEFT, padx=2)
        
        self.perfetto_btn = ttk.Button(
            button_frame,
            text="⚡ 性能日志",
            command=self.show_perfetto_config,
            width=18
        )
        self.perfetto_btn.pack(side=tk.LEFT, padx=2)
        
        # 功能说明区域
        help_frame = ttk.LabelFrame(main_frame, text="功能说明", padding="8")
        help_frame.pack(fill=tk.X, pady=(0, 8))

        help_text = (
            "🟢 开启日志：开启设备持久化日志记录（logcatd）\n"
            "📥 近期日志：仅抓取昨天和今天更新的日志（含 ANR）\n"
            "🗂 全部日志：抓取设备上的全部日志文件（含 ANR）\n"
            "🐛 崩溃日志：执行 adb bugreport，导出系统级崩溃/异常日志压缩包\n"
            "⚡ 性能日志：录制 Perfetto 性能 trace，可配置采集时长和数据类别"
        )
        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT)
        help_label.pack(anchor="w")

        # 保存位置区域
        location_frame = ttk.LabelFrame(main_frame, text="保存位置设置", padding="8")
        location_frame.pack(fill=tk.X, pady=8)
        
        path_input_frame = ttk.Frame(location_frame)
        path_input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_input_frame, text="路径:").pack(side=tk.LEFT, padx=(0, 8))
        
        self.path_var = tk.StringVar(value=self.save_path)
        self.path_entry = ttk.Entry(path_input_frame, textvariable=self.path_var, width=45)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(
            path_input_frame,
            text="浏览",
            command=self.browse_folder,
            width=8
        )
        browse_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        save_btn = ttk.Button(
            path_input_frame,
            text="保存",
            command=self.save_settings,
            width=8
        )
        save_btn.pack(side=tk.LEFT)
        
        # 状态信息区域
        status_frame = ttk.LabelFrame(main_frame, text="执行日志", padding="8")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        
        self.status_text = tk.Text(
            status_frame, 
            height=12, 
            width=75, 
            state=tk.DISABLED, 
            font=("Courier", 8),
            bg="white",
            fg="black"
        )
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self.log_status = "已停止"
        self.update_status("【系统】工具已启动")
        self.check_scripts()
    
    def get_runtime_dir(self):
        """获取工具运行目录（优先 exe 所在目录）"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def get_bjt_now(self):
        """获取北京时间（UTC+8）"""
        return datetime.now(timezone(timedelta(hours=8)))

    def check_scripts(self):
        """检查脚本文件是否存在"""
        self.update_status("【脚本检查】")
        
        # 检查 startLogcatd.bat
        if os.path.exists(self.startlogcatd_script):
            self.update_status(f"  ✓ startLogcatd.bat: 已找到")
        else:
            # 尝试在原始工作目录找
            alt_path = os.path.join(os.path.expanduser("~/"), ".openclaw/workspace", "startLogcatd.bat")
            if os.path.exists(alt_path):
                self.startlogcatd_script = alt_path
                self.update_status(f"  ✓ startLogcatd.bat: 已找到 (alt)")
            else:
                self.update_status(f"  ⚠ startLogcatd.bat: 未找到")
                self.update_status(f"    期望位置: {self.startlogcatd_script}")
        
        # 检查 pull_all_logs.py
        if os.path.exists(self.pull_logs_script):
            self.update_status(f"  ✓ pull_all_logs.py: 已找到")
        else:
            # 尝试在原始工作目录找
            alt_path = os.path.join(os.path.expanduser("~/"), ".openclaw/workspace", "pull_all_logs.py")
            if os.path.exists(alt_path):
                self.pull_logs_script = alt_path
                self.update_status(f"  ✓ pull_all_logs.py: 已找到 (alt)")
            else:
                self.update_status(f"  ⚠ pull_all_logs.py: 未找到")
                self.update_status(f"    期望位置: {self.pull_logs_script}")
    
    def load_config(self):
        """加载保存的配置"""
        self.perfetto_config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.save_path = config.get('save_path', self.default_save_path)
                    self.perfetto_config = config.get('perfetto', {})
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.save_path = self.default_save_path
        else:
            self.save_path = self.default_save_path
    
    def save_settings(self):
        """保存设置"""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("警告", "请输入保存路径")
            return
        
        try:
            os.makedirs(path, exist_ok=True)
            config = {'save_path': path}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.save_path = path
            self.update_status(f"【设置】路径已保存: {path}")
            self.update_status(f"【设置】当前运行目录: {self.runtime_dir}")
            messagebox.showinfo("成功", f"设置已保存")
        except Exception as e:
            self.update_status(f"✗ 保存失败: {str(e)}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory(title="选择日志保存位置")
        if folder:
            self.path_var.set(folder)
    
    def start_logging(self):
        """开启日志 - 执行 startLogcatd.bat"""
        if not os.path.exists(self.startlogcatd_script):
            self.update_status("✗ startLogcatd.bat 脚本不存在")
            messagebox.showerror(
                "错误", 
                f"找不到脚本:\n{self.startlogcatd_script}\n\n" +
                "请确保与 LogTool.exe 在同一目录中有:\n" +
                "- startLogcatd.bat\n" +
                "- pull_all_logs.py"
            )
            return
        
        self.update_status("【日志开启】正在执行 startLogcatd.bat...")
        self.start_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._run_start_logging, daemon=True)
        thread.start()
    
    def _run_start_logging(self):
        """后台执行开启日志"""
        try:
            # 预检查设备
            ok, err_msg = self._check_adb_device()
            if not ok:
                self.update_status("  ✗ 设备检查失败")
                self.root.after(0, lambda: (
                    self.start_btn.config(state=tk.NORMAL),
                    messagebox.showerror("设备检查失败", err_msg)
                ))
                return
            
            result = _run_sp(
                [self.startlogcatd_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                err = (result.stdout + result.stderr).strip()
                self.update_status(f"  ✗ 开启失败 (exitcode: {result.returncode})")
                if err:
                    self.update_status(f"  {err[:200]}")
                err_detail = self._diagnose_adb_error(err)
                self.root.after(0, lambda: (
                    self.start_btn.config(state=tk.NORMAL),
                    messagebox.showerror("开启失败", err_detail)
                ))
                return
            
            self.update_status(f"✓ 日志已开启")
            self.log_status = "运行中"
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[:5]:
                    if line.strip():
                        self.update_status(f"  {line}")
            
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showinfo("成功", "日志开启命令已执行")
            ))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>30秒）")
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showerror("超时",
                    "开启日志超时（>30秒）\n\n"
                    "可能原因：\n"
                    "1. 设备响应慢\n"
                    "2. USB 连接不稳定\n"
                    "3. 设备进入休眠")
            ))
        except FileNotFoundError:
            self.update_status("✗ 找不到 adb 或脚本文件")
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showerror("执行失败",
                    "找不到执行文件\n\n"
                    "请检查：\n"
                    "1. adb 是否已安装并加入 PATH\n"
                    "2. startLogcatd.bat 是否在同一目录")
            ))
        except Exception as e:
            self.update_status(f"✗ 执行失败: {str(e)}")
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", f"执行失败: {str(e)}")
            ))
    
    def get_logs(self):
        """获取最新日志 - 执行 pull_all_logs.py"""
        if not os.path.exists(self.pull_logs_script):
            self.update_status("✗ pull_all_logs.py 脚本不存在")
            messagebox.showerror(
                "错误", 
                f"找不到脚本:\n{self.pull_logs_script}\n\n" +
                "请确保与 LogTool.exe 在同一目录中有:\n" +
                "- startLogcatd.bat\n" +
                "- pull_all_logs.py"
            )
            return
        
        self.update_status("【最新日志】正在执行 pull_all_logs.py...")
        self.get_btn.config(state=tk.DISABLED)
        self.get_all_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=lambda: self._run_get_logs(all_logs=False), daemon=True)
        thread.start()

    def _run_get_logs(self, all_logs=False):
        """后台执行获取日志"""
        try:
            # 预检查设备
            ok, err_msg = self._check_adb_device()
            if not ok:
                self.update_status("  ✗ 设备检查失败")
                self.root.after(0, lambda: (
                    self.get_btn.config(state=tk.NORMAL),
                    self.get_all_btn.config(state=tk.NORMAL),
                    messagebox.showerror("设备检查失败", err_msg)
                ))
                return
            
            # 确保保存目录存在
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path, exist_ok=True)

            if not os.path.isdir(self.save_path):
                raise FileNotFoundError(f"保存目录不可用: {self.save_path}")
            
            self.update_status(f"  保存位置: {self.save_path}")
            self.update_status(f"  运行目录: {self.runtime_dir}")
            self.update_status(f"  抓取范围: {'全部日志' if all_logs else '近期日志（昨天+今天）'}")
            
            cmd = ["python", self.pull_logs_script, self.save_path]
            if all_logs:
                cmd.append("--all")
            
            result = _run_sp(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.runtime_dir
            )
            
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and ('[OK]' in line or '[X]' in line or '==' in line or 'Pulling' in line or 'Skipping' in line):
                        self.update_status(line[:80])
            
            if result.returncode == 0:
                self.update_status(f"✓ 日志获取完成")
                self.root.after(0, lambda: messagebox.showinfo("成功", f"日志已成功获取\n位置: {self.save_path}"))
                try:
                    if os.name == 'nt':
                        os.startfile(self.save_path)
                except:
                    pass
            else:
                err = (result.stdout + result.stderr).strip()
                self.update_status(f"  ✗ 执行异常 (exitcode: {result.returncode})")
                err_detail = self._diagnose_adb_error(err)
                self.root.after(0, lambda: messagebox.showerror("获取失败", err_detail))
            
            self.root.after(0, lambda: self.get_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.get_all_btn.config(state=tk.NORMAL))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>120秒）")
            self.root.after(0, lambda: (
                self.get_btn.config(state=tk.NORMAL),
                self.get_all_btn.config(state=tk.NORMAL),
                messagebox.showerror("超时",
                    "日志获取超时（>120秒）\n\n"
                    "可能原因：\n"
                    "1. 日志文件过大，传输慢\n"
                    "2. USB 连接不稳定\n"
                    "3. 设备存储响应慢")
            ))
        except FileNotFoundError as e:
            self.update_status(f"✗ {str(e)}")
            self.root.after(0, lambda: (
                self.get_btn.config(state=tk.NORMAL),
                self.get_all_btn.config(state=tk.NORMAL),
                messagebox.showerror("执行失败",
                    f"{str(e)}\n\n"
                    "请检查：\n"
                    "1. pull_all_logs.py 是否在同一目录\n"
                    "2. python 是否已安装并加入 PATH\n"
                    "3. 保存路径是否可用")
            ))
        except Exception as e:
            self.update_status(f"✗ 执行失败: {str(e)}")
            self.root.after(0, lambda: (
                self.get_btn.config(state=tk.NORMAL),
                self.get_all_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", f"执行失败: {str(e)}")
            ))

    def get_all_logs(self):
        """获取全部日志 - 执行 pull_all_logs.py --all"""
        if not os.path.exists(self.pull_logs_script):
            self.update_status("✗ pull_all_logs.py 脚本不存在")
            messagebox.showerror(
                "错误", 
                f"找不到脚本:\n{self.pull_logs_script}\n\n" +
                "请确保与 LogTool.exe 在同一目录中有:\n" +
                "- startLogcatd.bat\n" +
                "- pull_all_logs.py"
            )
            return

        self.update_status("【全部日志】正在执行 pull_all_logs.py --all...")
        self.get_btn.config(state=tk.DISABLED)
        self.get_all_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=lambda: self._run_get_logs(all_logs=True), daemon=True)
        thread.start()
    
    def collect_bugreport(self):
        """收集系统日志 - 执行 adb bugreport"""
        save_path = self.save_path
        
        try:
            if not os.path.exists(save_path):
                os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            self.update_status(f"✗ 创建目录失败: {str(e)}")
            messagebox.showerror("错误", f"无法创建目录: {str(e)}")
            return
        
        timestamp = self.get_bjt_now().strftime("%Y-%m-%d_%H-%M-%S")
        bugreport_filename = f"bugreport_{timestamp}.zip"
        bugreport_file = os.path.join(save_path, bugreport_filename)
        
        self.update_status("【系统日志收集】正在执行 adb bugreport...")
        self.update_status(f"  文件: {bugreport_filename}")
        self.bugreport_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(
            target=self._run_bugreport, 
            args=(bugreport_file, save_path),
            daemon=True
        )
        thread.start()
    
    def _run_bugreport(self, bugreport_file, save_path):
        """后台执行 adb bugreport"""
        try:
            # 预检查设备
            ok, err_msg = self._check_adb_device()
            if not ok:
                self.update_status("  ✗ 设备检查失败")
                self.root.after(0, lambda: (
                    self.bugreport_btn.config(state=tk.NORMAL),
                    messagebox.showerror("设备检查失败", err_msg)
                ))
                return
            
            filename = os.path.basename(bugreport_file)
            
            self.update_status(f"  命令: adb bugreport {filename}")
            self.update_status(f"  位置: {save_path}")
            self.update_status(f"  正在收集，请等待 1~5 分钟...")
            
            result = _run_sp(
                ["adb", "bugreport", filename],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=save_path
            )
            
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines[:10]:
                    if line.strip():
                        self.update_status(f"  {line[:75]}")
            
            if result.returncode != 0:
                err = (result.stdout + result.stderr).strip()
                self.update_status(f"  ✗ bugreport 失败 (exitcode: {result.returncode})")
                err_detail = self._diagnose_adb_error(err)
                self.root.after(0, lambda: (
                    self.bugreport_btn.config(state=tk.NORMAL),
                    messagebox.showerror("收集失败", err_detail)
                ))
                return
            
            # 检查文件生成
            if os.path.exists(bugreport_file):
                file_size = os.path.getsize(bugreport_file)
                size_mb = file_size / (1024 * 1024)
                
                if file_size == 0:
                    self.update_status("⚠ 文件大小为 0，可能收集失败")
                    self.root.after(0, lambda: (
                        self.bugreport_btn.config(state=tk.NORMAL),
                        messagebox.showwarning("异常提示",
                            "bugreport 文件大小为 0\n\n"
                            "可能原因：\n"
                            "1. 设备存储空间不足\n"
                            "2. 权限不足（尝试 adb root）\n"
                            "3. 设备状态异常")
                    ))
                else:
                    self.update_status(f"  ✓ 文件大小: {size_mb:.2f} MB")
                    self.root.after(0, lambda: (
                        self.bugreport_btn.config(state=tk.NORMAL),
                        messagebox.showinfo("成功",
                            f"崩溃日志已收集\n文件: {filename}\n大小: {size_mb:.2f} MB")
                    ))
                    try:
                        if os.name == 'nt':
                            os.startfile(save_path)
                    except:
                        pass
            else:
                # 检查是否生成了不同名称的文件（bugreport 有时会自动命名）
                found_files = [f for f in os.listdir(save_path) if f.startswith("bugreport") and f.endswith(".zip")]
                if found_files:
                    actual = found_files[-1]
                    actual_path = os.path.join(save_path, actual)
                    size_mb = os.path.getsize(actual_path) / (1024 * 1024)
                    self.update_status(f"  ✓ 找到文件: {actual} ({size_mb:.2f} MB)")
                    self.root.after(0, lambda: (
                        self.bugreport_btn.config(state=tk.NORMAL),
                        messagebox.showinfo("成功",
                            f"崩溃日志已收集\n文件: {actual}\n大小: {size_mb:.2f} MB")
                    ))
                    try:
                        if os.name == 'nt':
                            os.startfile(save_path)
                    except:
                        pass
                else:
                    self.update_status("✗ 文件未生成")
                    self.root.after(0, lambda: (
                        self.bugreport_btn.config(state=tk.NORMAL),
                        messagebox.showerror("收集失败",
                            "未找到 bugreport 文件\n\n"
                            "可能原因：\n"
                            "1. 设备 USB 连接中断\n"
                            "2. 设备存储空间不足\n"
                            "3. 权限不足\n\n"
                            "建议：尝试 adb root 后重试")
                    ))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>300秒）")
            self.root.after(0, lambda: (
                self.bugreport_btn.config(state=tk.NORMAL),
                messagebox.showerror("超时",
                    "bugreport 收集超时（>5分钟）\n\n"
                    "可能原因：\n"
                    "1. 设备状态异常/死机\n"
                    "2. USB 连接中断\n"
                    "3. 存储空间不足导致写入卡住")
            ))
        except FileNotFoundError:
            self.update_status("✗ 找不到 adb 命令")
            self.root.after(0, lambda: (
                self.bugreport_btn.config(state=tk.NORMAL),
                messagebox.showerror("ADB 未安装",
                    "找不到 adb 命令\n\n"
                    "请确保：\n"
                    "1. 已安装 Android SDK Platform Tools\n"
                    "2. adb 已加入系统 PATH")
            ))
        except Exception as e:
            self.update_status(f"✗ 执行失败: {str(e)}")
            self.root.after(0, lambda: (
                self.bugreport_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", f"执行失败: {str(e)}")
            ))
    
    # ==================== ADB 通用检查 ====================
    
    def _check_adb_device(self):
        """检查 ADB 设备连接，返回 (ok, err_msg)"""
        try:
            result = _run_sp(
                ["adb", "devices"],
                capture_output=True, text=True, timeout=5
            )
            connected = [l for l in result.stdout.split('\n') if '\tdevice' in l]
            if not connected:
                # 进一步检查是否有未授权设备
                unauthorized = [l for l in result.stdout.split('\n') if '\tunauthorized' in l]
                if unauthorized:
                    return False, (
                        "设备未授权 ADB 调试\n\n"
                        "请在设备屏幕上确认“允许 USB 调试”弹窗\n"
                        "然后重试"
                    )
                offline = [l for l in result.stdout.split('\n') if '\toffline' in l]
                if offline:
                    return False, (
                        "设备离线\n\n"
                        "请检查：\n"
                        "1. USB 线是否插稳\n"
                        "2. 设备是否正常开机\n"
                        "3. 尝试重新插拔 USB"
                    )
                return False, (
                    "未检测到 ADB 设备\n\n"
                    "请检查：\n"
                    "1. USB 线是否连接\n"
                    "2. 设备是否开启 USB 调试\n"
                    "3. 是否已授权 ADB 调试"
                )
            return True, None
        except FileNotFoundError:
            return False, (
                "找不到 adb 命令\n\n"
                "请确保：\n"
                "1. 已安装 Android SDK Platform Tools\n"
                "2. adb 已加入系统 PATH"
            )
        except Exception as e:
            return False, f"ADB 检查失败: {str(e)}"
    
    def _diagnose_adb_error(self, err_text):
        """通用 ADB 错误诊断"""
        if not err_text:
            return "执行失败，未返回错误信息\n\n建议重新插拔 USB 后重试"
        
        err_lower = err_text.lower()
        
        if "device not found" in err_lower or "no devices" in err_lower:
            return (
                "设备未找到\n\n"
                "请检查：\n"
                "1. USB 线是否连接\n"
                "2. 设备是否开启 USB 调试\n"
                "3. 是否已授权 ADB"
            )
        elif "device offline" in err_lower:
            return (
                "设备离线\n\n"
                "解决方案：\n"
                "1. 重新插拔 USB\n"
                "2. 在设备上重新授权 ADB\n"
                "3. 执行 adb kill-server && adb start-server"
            )
        elif "permission denied" in err_lower or "not permitted" in err_lower:
            return (
                "权限不足\n\n"
                "解决方案：\n"
                "1. 执行 adb root 获取 root 权限\n"
                "2. 或执行 adb remount 重新挂载\n"
                "3. 检查设备是否已 root"
            )
        elif "read-only" in err_lower or "remount" in err_lower:
            return (
                "文件系统只读\n\n"
                "解决方案：\n"
                "1. 执行 adb root\n"
                "2. 执行 adb remount\n"
                "3. 重试操作"
            )
        elif "no space" in err_lower or "enospc" in err_lower:
            return (
                "设备/本地存储空间不足\n\n"
                "解决方案：\n"
                "1. 清理设备存储\n"
                "2. 清理本地磁盘空间\n"
                "3. 更换保存路径"
            )
        elif "unauthorized" in err_lower:
            return (
                "设备未授权\n\n"
                "请在设备屏幕上确认“允许 USB 调试”弹窗\n"
                "然后重试"
            )
        elif "connection refused" in err_lower or "cannot connect" in err_lower:
            return (
                "连接被拒绝\n\n"
                "解决方案：\n"
                "1. 重新插拔 USB\n"
                "2. adb kill-server && adb start-server\n"
                "3. 检查是否有其他程序占用 ADB"
            )
        else:
            return (
                f"执行失败\n\n"
                f"错误信息：\n{err_text[:300]}\n\n"
                f"常见排查：\n"
                f"1. 重新插拔 USB\n"
                f"2. adb kill-server && adb start-server\n"
                f"3. 确认设备状态正常"
            )
    
    # ==================== Tooltip 工具 ====================
    
    def _bind_tooltip(self, widget, text):
        """给控件绑定悬浮提示"""
        tip = None
        
        def show(event):
            nonlocal tip
            if tip:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 2
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tip, text=text, justify=tk.LEFT,
                background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                font=("Arial", 9), padx=6, pady=3
            )
            label.pack()
        
        def hide(event):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None
        
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
    
    # ==================== Perfetto 性能日志 ====================
    
    PERFETTO_CATEGORIES = [
        ("sched",         "进程调度",       "记录 CPU 上进程/线程的调度切换，分析卡顿、抢占、调度延迟"),
        ("freq",          "CPU 频率",      "记录各 CPU 核心频率变化，分析性能调节和功耗"),
        ("idle",          "CPU 空闲",      "记录 CPU 进入/退出 idle 状态，分析功耗和唤醒源"),
        ("am",            "Activity Manager", "Activity/Service/Broadcast 生命周期，分析启动慢、ANR"),
        ("wm",            "Window Manager",   "窗口创建/销毁/动画，分析界面切换和窗口异常"),
        ("gfx",           "图形渲染",       "SurfaceFlinger/HWC 合成、帧提交，分析掉帧和渲染卡顿"),
        ("view",          "View 系统",      "View 的 measure/layout/draw 流程，分析 UI 绘制性能"),
        ("binder_driver", "Binder 驱动",    "跨进程 Binder 调用，分析 IPC 耗时和阻塞"),
        ("hal",           "HAL 层",        "硬件抽象层调用，分析硬件交互耗时"),
        ("dalvik",        "Dalvik/ART",    "GC 事件、JIT 编译、类加载，分析内存和运行时性能"),
        ("camera",        "相机",          "相机 HAL/Framework 调用链，分析拍照、预览延迟"),
        ("input",         "输入事件",       "触摸/按键事件分发链路，分析输入延迟和事件丢失"),
        ("res",           "资源加载",       "资源文件读取和解析，分析启动时资源加载耗时"),
        ("memory",        "内存",          "内存分配/回收/RSS 变化，分析内存泄漏和 OOM"),
        ("power",         "电源管理",       "WakeLock/电池状态/充放电，分析续航和异常耗电"),
        ("audio",         "音频",          "AudioFlinger/AudioPolicy 调用，分析音频延迟和断流"),
        ("video",         "视频",          "MediaCodec/OMX 编解码，分析视频播放卡顿"),
        ("network",       "网络",          "网络收发包统计，分析网络延迟和流量异常"),
        ("disk",          "磁盘 I/O",      "块设备读写和 fstrace，分析 I/O 等待导致的卡顿"),
        ("webview",       "WebView",       "Chromium 内核渲染流水线，分析 H5 页面性能"),
    ]
    
    PERFETTO_DEFAULTS = {
        "sched", "freq", "idle", "am", "wm", "gfx", "view",
        "binder_driver", "hal", "dalvik", "camera", "input", "res", "memory"
    }
    
    def show_perfetto_config(self):
        """弹出 Perfetto 配置窗口"""
        win = tk.Toplevel(self.root)
        win.title("⚡ 性能日志 - Perfetto 配置")
        win.geometry("540x520")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        
        # 自定义打勾样式 - 不需要 ttk，用原生 tk.Checkbutton 就是✓
        
        main = ttk.Frame(win, padding="12")
        main.pack(fill=tk.BOTH, expand=True)
        
        # --- 采集时长 ---
        time_frame = ttk.LabelFrame(main, text="采集时长", padding="8")
        time_frame.pack(fill=tk.X, pady=(0, 8))
        
        time_inner = ttk.Frame(time_frame)
        time_inner.pack(fill=tk.X)
        
        saved_duration = self.perfetto_config.get("duration", 5)
        saved_cats = set(self.perfetto_config.get("categories", list(self.PERFETTO_DEFAULTS)))
        
        duration_var = tk.IntVar(value=saved_duration)
        ttk.Label(time_inner, text="录制时长:").pack(side=tk.LEFT)
        ttk.Spinbox(
            time_inner, from_=1, to=300, width=6,
            textvariable=duration_var
        ).pack(side=tk.LEFT, padx=6)
        ttk.Label(time_inner, text="秒  (范围 1~300)").pack(side=tk.LEFT)
        
        # --- 数据类别 ---
        cat_frame = ttk.LabelFrame(main, text="数据类别（悬停查看说明）", padding="8")
        cat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # 快捷按钮
        sel_frame = ttk.Frame(cat_frame)
        sel_frame.pack(fill=tk.X, pady=(0, 6))
        
        cat_vars = {}
        
        def select_all():
            for v in cat_vars.values():
                v.set(True)
        
        def select_none():
            for v in cat_vars.values():
                v.set(False)
        
        def select_default():
            for cat, v in cat_vars.items():
                v.set(cat in self.PERFETTO_DEFAULTS)
        
        ttk.Button(sel_frame, text="全选", command=select_all, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(sel_frame, text="清空", command=select_none, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(sel_frame, text="默认", command=select_default, width=6).pack(side=tk.LEFT, padx=2)
        
        # 勾选框网格布局
        check_frame = ttk.Frame(cat_frame)
        check_frame.pack(fill=tk.BOTH, expand=True)
        
        cols = 2
        for i, (cat, desc, detail) in enumerate(self.PERFETTO_CATEGORIES):
            var = tk.BooleanVar(value=(cat in saved_cats))
            cat_vars[cat] = var
            cb = tk.Checkbutton(
                check_frame,
                text=f"{cat} ({desc})",
                variable=var,
                anchor="w",
                font=("Arial", 9)
            )
            cb.grid(row=i // cols, column=i % cols, sticky="w", padx=6, pady=1)
            self._bind_tooltip(cb, f"【{cat}】{detail}")
        
        # --- 自定义类别 ---
        custom_frame = ttk.Frame(main)
        custom_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(custom_frame, text="自定义类别（空格分隔）:").pack(side=tk.LEFT)
        custom_var = tk.StringVar(value=self.perfetto_config.get("custom_categories", ""))
        ttk.Entry(custom_frame, textvariable=custom_var, width=40).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        
        # --- 底部按钮 ---
        def start_recording():
            duration = duration_var.get()
            if duration < 1 or duration > 300:
                messagebox.showwarning("警告", "采集时长范围: 1~300 秒", parent=win)
                return
            
            selected = [cat for cat, var in cat_vars.items() if var.get()]
            custom = custom_var.get().strip().split()
            all_cats = selected + custom
            
            if not all_cats:
                messagebox.showwarning("警告", "请至少选择一个数据类别", parent=win)
                return
            
            self.perfetto_config = {
                "duration": duration,
                "categories": selected,
                "custom_categories": custom_var.get().strip()
            }
            self._save_perfetto_config()
            win.destroy()
            self.run_perfetto(duration, all_cats)
        
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="开始录制", command=start_recording, width=10).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_frame, text="取消", command=win.destroy, width=8).pack(side=tk.RIGHT, padx=3)
    
    def _save_perfetto_config(self):
        """保存 Perfetto 配置"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['perfetto'] = self.perfetto_config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.update_status(f"  ⚠ 保存 Perfetto 配置失败: {e}")
    
    def run_perfetto(self, duration, categories):
        """执行 Perfetto 录制"""
        save_path = self.save_path
        try:
            if not os.path.exists(save_path):
                os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            self.update_status(f"✗ 创建目录失败: {str(e)}")
            messagebox.showerror("错误", f"无法创建目录: {str(e)}")
            return
        
        timestamp = self.get_bjt_now().strftime("%Y-%m-%d_%H-%M-%S")
        remote_path = "/data/misc/perfetto-traces/trace_file.perfetto-trace"
        local_file = os.path.join(save_path, f"perfetto_{timestamp}.perfetto-trace")
        
        cats_str = " ".join(categories)
        self.update_status(f"【性能日志】开始录制 {duration}s")
        self.update_status(f"  类别: {cats_str}")
        self.perfetto_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(
            target=self._run_perfetto,
            args=(duration, categories, remote_path, local_file, save_path),
            daemon=True
        )
        thread.start()
    
    def _run_perfetto(self, duration, categories, remote_path, local_file, save_path):
        """后台执行 Perfetto 录制"""
        try:
            # 预检查: 设备连接
            ok, err_msg = self._check_adb_device()
            if not ok:
                self.update_status("  ✗ 设备检查失败")
                self.root.after(0, lambda: (
                    self.perfetto_btn.config(state=tk.NORMAL),
                    messagebox.showerror("设备检查失败", err_msg)
                ))
                return
            
            # 预检查: perfetto 命令
            which_result = _run_sp(
                ["adb", "shell", "which", "perfetto"],
                capture_output=True, text=True, timeout=5
            )
            if which_result.returncode != 0 or not which_result.stdout.strip():
                self.update_status("  ✗ 设备上未找到 perfetto 命令")
                self.root.after(0, lambda: (
                    self.perfetto_btn.config(state=tk.NORMAL),
                    messagebox.showerror("Perfetto 不可用",
                        "设备上未找到 perfetto 命令\n\n"
                        "可能原因：\n"
                        "1. Android 版本太低（需要 Android 9+）\n"
                        "2. 系统裁剪了 perfetto 组件")
                ))
                return
            
            cats_str = " ".join(categories)
            cmd = f'adb shell perfetto -o {remote_path} -t {duration}s {cats_str}'
            
            self.update_status(f"  命令: {cmd}")
            self.update_status(f"  录制中... 请等待 {duration} 秒")
            
            timeout = duration + 30
            result = _run_sp(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                err = (result.stdout + result.stderr).strip()
                err_msg = self._diagnose_perfetto_error(err)
                self.update_status(f"  ✗ Perfetto 录制失败: {err}")
                self.root.after(0, lambda: (
                    self.perfetto_btn.config(state=tk.NORMAL),
                    messagebox.showerror("录制失败", err_msg)
                ))
                return
            
            self.update_status("  ✓ 录制完成，正在拉取文件...")
            
            pull_result = _run_sp(
                ["adb", "pull", remote_path, local_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if pull_result.returncode == 0 and os.path.exists(local_file):
                file_size = os.path.getsize(local_file)
                size_mb = file_size / (1024 * 1024)
                filename = os.path.basename(local_file)
                
                if file_size == 0:
                    self.update_status("  ⚠ 文件大小为 0，可能录制未实际采集到数据")
                    self.root.after(0, lambda: messagebox.showwarning(
                        "异常提示",
                        "Perfetto 文件大小为 0 字节\n\n"
                        "可能原因：\n"
                        "1. 所选数据类别在设备上不可用\n"
                        "2. traced 服务未运行\n"
                        "3. 磁盘空间不足"
                    ))
                elif size_mb < 0.001:
                    self.update_status(f"  ⚠ 文件异常小 ({file_size} bytes)")
                    self.root.after(0, lambda: messagebox.showwarning(
                        "异常提示",
                        f"Perfetto 文件异常小（{file_size} bytes）\n\n"
                        "建议：\n"
                        "1. 增加采集时长\n"
                        "2. 检查所选类别是否被设备支持"
                    ))
                else:
                    self.update_status(f"  ✓ 文件: {filename} ({size_mb:.2f} MB)")
                    self.root.after(0, lambda: messagebox.showinfo(
                        "成功",
                        f"性能日志录制完成\n文件: {filename}\n大小: {size_mb:.2f} MB\n\n"
                        f"可用 https://ui.perfetto.dev 打开分析"
                    ))
                
                try:
                    if os.name == 'nt':
                        os.startfile(save_path)
                except:
                    pass
            else:
                err = pull_result.stderr.strip()
                self.update_status(f"  ✗ Pull 失败: {err}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Pull 失败",
                    f"无法从设备拉取 trace 文件\n\n"
                    f"可能原因：\n"
                    f"1. 设备存储空间不足\n"
                    f"2. 权限不足（尝试 adb root）\n"
                    f"3. USB 连接中断\n\n"
                    f"错误: {err}"
                ))
            
            # 清理设备上的 trace
            _run_sp(
                ["adb", "shell", "rm", "-f", remote_path],
                capture_output=True, timeout=10
            )
            
            self.root.after(0, lambda: self.perfetto_btn.config(state=tk.NORMAL))
            
        except subprocess.TimeoutExpired:
            self.update_status(f"✗ 执行超时（>{duration + 30}秒）")
            self.root.after(0, lambda: (
                self.perfetto_btn.config(state=tk.NORMAL),
                messagebox.showerror("超时",
                    f"Perfetto 录制超时（预计 {duration}s，实际超过 {duration + 30}s）\n\n"
                    "可能原因：\n"
                    "1. 设备 USB 连接中断\n"
                    "2. 设备进入休眠\n"
                    "3. perfetto 进程被杀死")
            ))
        except FileNotFoundError:
            self.update_status("✗ 找不到 adb 命令")
            self.root.after(0, lambda: (
                self.perfetto_btn.config(state=tk.NORMAL),
                messagebox.showerror("ADB 未安装",
                    "找不到 adb 命令\n\n"
                    "请确保：\n"
                    "1. 已安装 Android SDK Platform Tools\n"
                    "2. adb 已加入系统 PATH")
            ))
        except Exception as e:
            self.update_status(f"✗ 执行失败: {str(e)}")
            self.root.after(0, lambda: (
                self.perfetto_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", f"执行失败: {str(e)}")
            ))
    
    def _diagnose_perfetto_error(self, err_text):
        """根据错误信息给出具体诊断"""
        err_lower = err_text.lower()
        
        if "permission denied" in err_lower:
            return (
                "Perfetto 权限不足\n\n"
                "解决方案：\n"
                "1. 先执行 adb root\n"
                "2. 或使用 adb shell perfetto --background\n"
                "3. 检查 SELinux 策略"
            )
        elif "no space" in err_lower or "enospc" in err_lower:
            return (
                "设备存储空间不足\n\n"
                "解决方案：\n"
                "1. 清理设备存储\n"
                "2. 缩短采集时长\n"
                "3. 减少采集类别"
            )
        elif "traced" in err_lower and ("not running" in err_lower or "connect" in err_lower):
            return (
                "Perfetto traced 服务未运行\n\n"
                "解决方案：\n"
                "1. 执行: adb shell setprop persist.traced.enable 1\n"
                "2. 重启设备\n"
                "3. 检查: adb shell getprop init.svc.traced"
            )
        elif "invalid" in err_lower and "category" in err_lower:
            return (
                "无效的数据类别\n\n"
                "某些所选类别在当前设备不可用\n\n"
                "建议：\n"
                "1. 去掉不支持的类别重试\n"
                "2. 执行 adb shell perfetto --query 查看可用类别"
            )
        elif "device offline" in err_lower or "device not found" in err_lower:
            return (
                "设备断开连接\n\n"
                "录制过程中设备断开了\n\n"
                "请检查：\n"
                "1. USB 线是否松动\n"
                "2. 设备是否重启\n"
                "3. ADB 授权是否过期"
            )
        else:
            return (
                f"Perfetto 录制失败\n\n"
                f"错误信息：\n{err_text[:200]}\n\n"
                f"常见排查：\n"
                f"1. 设备是否 Android 9+\n"
                f"2. 尝试 adb root 后重试\n"
                f"3. 检查 adb shell perfetto --help"
            )
    
    # ==================== 通用 ====================
    
    def update_status(self, message):
        """更新状态信息"""
        try:
            self.status_text.config(state=tk.NORMAL)
            self.status_text.insert(tk.END, f"{message}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"更新状态失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LogToolApp(root)
    root.mainloop()
