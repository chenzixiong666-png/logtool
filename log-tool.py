import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import subprocess
import threading
import shutil

class LogToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("日志管理工具")
        self.root.geometry("650x480")
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
            text="🐛 收集系统日志",
            command=self.collect_bugreport,
            width=18
        )
        self.bugreport_btn.pack(side=tk.LEFT, padx=2)
        
        # 功能说明区域
        help_frame = ttk.LabelFrame(main_frame, text="功能说明", padding="8")
        help_frame.pack(fill=tk.X, pady=(0, 8))

        help_text = (
            "🟢 开启日志：开启设备持久化日志记录（logcatd）\n"
            "📥 近期日志：仅抓取昨天和今天更新的日志\n"
            "🗂 全部日志：抓取设备上的全部日志文件\n"
            "🐛 收集系统日志：执行 adb bugreport，导出系统级压缩日志"
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
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.save_path = config.get('save_path', self.default_save_path)
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
            result = subprocess.run(
                [self.startlogcatd_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self.update_status(f"✓ 日志已开启 (exitcode: {result.returncode})")
            self.log_status = "运行中"
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[:5]:
                    if line.strip():
                        self.update_status(f"  {line}")
            
            if result.stderr:
                self.update_status(f"  [stderr] {result.stderr[:100]}")
            
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showinfo("成功", "日志开启命令已执行")
            ))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>30秒）")
            self.root.after(0, lambda: (
                self.start_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", "执行超时")
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
            
            # 使用运行目录执行脚本，保存路径作为参数传入
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.runtime_dir
            )
            
            self.update_status(f"✓ 日志获取完成 (exitcode: {result.returncode})")
            
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and ('[OK]' in line or '[X]' in line or '==' in line or 'Pulling' in line or 'Skipping' in line):
                        self.update_status(line[:80])
            
            if result.returncode == 0:
                self.root.after(0, lambda: messagebox.showinfo("成功", f"日志已成功获取\n位置: {self.save_path}"))
                try:
                    if os.name == 'nt':
                        os.startfile(self.save_path)
                except:
                    pass
            else:
                self.root.after(0, lambda: messagebox.showwarning("警告", f"执行完成但返回码: {result.returncode}"))
            
            self.root.after(0, lambda: self.get_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.get_all_btn.config(state=tk.NORMAL))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>120秒）")
            self.root.after(0, lambda: (
                self.get_btn.config(state=tk.NORMAL),
                self.get_all_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", "执行超时（>120秒）")
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
            filename = os.path.basename(bugreport_file)
            
            self.update_status(f"  命令: adb bugreport {filename}")
            self.update_status(f"  位置: {save_path}")
            
            result = subprocess.run(
                ["adb", "bugreport", filename],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=save_path
            )
            
            self.update_status(f"✓ 系统日志收集完成 (exitcode: {result.returncode})")
            
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines[:10]:
                    if line.strip():
                        self.update_status(f"  {line[:75]}")
            
            if os.path.exists(bugreport_file):
                file_size = os.path.getsize(bugreport_file)
                size_mb = file_size / (1024 * 1024)
                self.update_status(f"  ✓ 文件大小: {size_mb:.2f} MB")
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "成功", 
                    f"系统日志已收集\n文件: {filename}\n大小: {size_mb:.2f} MB"
                ))
                
                try:
                    if os.name == 'nt':
                        os.startfile(save_path)
                except:
                    pass
            else:
                self.update_status("✗ 文件未生成，请检查设备连接")
                self.root.after(0, lambda: messagebox.showwarning("警告", "文件未生成\n请检查设备连接"))
            
            self.root.after(0, lambda: self.bugreport_btn.config(state=tk.NORMAL))
            
        except subprocess.TimeoutExpired:
            self.update_status("✗ 执行超时（>300秒）")
            self.root.after(0, lambda: (
                self.bugreport_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", "执行超时（>5分钟）")
            ))
        except Exception as e:
            self.update_status(f"✗ 执行失败: {str(e)}")
            self.root.after(0, lambda: (
                self.bugreport_btn.config(state=tk.NORMAL),
                messagebox.showerror("错误", f"执行失败: {str(e)}\n检查adb是否安装")
            ))
    
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
