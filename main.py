# main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser
import os
import sys
import webbrowser  
import subprocess  
import threading
import configparser  # 新增：用于读写Settings.ini

# 保留原代码的外部模块导入（ustreader、ustplayer，不做任何额外修改）
import ustreader as ur
import ustplayer as up

# ---------------------- userform.py 原始内容（修改 on_play_click，增加线程安全支持） ----------------------
class UstxPlayerSettings:
    def __init__(self, root):  # 1. 去掉 play_callback 参数
        self.root = root
        self.root.title("ustPlayer - v26a31")
        self.root.geometry("800x500")
        # 2. 去掉 self.play_callback 赋值
        
        # ========== 新增：配置文件相关 ==========
        self.settings_path = "./Settings.ini"  # 配置文件路径（程序同目录）
        self.config = configparser.ConfigParser()
        # 初始化默认路径（兜底值）
        self.last_open_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.last_export_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        # =======================================

        self.OPU_site = ""
        self.default_singer = ""
        self.default_phenomizer = ""
        
        # 读取配置文件（程序启动时加载上次路径）
        self.read_settings()

        # ===================== 【变量定义】 =====================
        self.ustx_path_var = tk.StringVar()
        self.project_name_var = tk.StringVar()
        self.song_name_var = tk.StringVar()
        self.song_author_var = tk.StringVar()
        self.ust_author_var = tk.StringVar()

        # 勾选框变量
        self.show_bpm_var = tk.BooleanVar(value=True)
        self.show_play_time_var = tk.BooleanVar(value=True)
        self.show_song_name_var = tk.BooleanVar(value=True)
        self.show_song_author_var = tk.BooleanVar(value=True)
        self.show_ust_author_var = tk.BooleanVar(value=True)

        # 编码选择变量
        self.encoding_var = tk.StringVar(value="Shift-JIS")

        # 播放器样式颜色变量（默认值）
        self.bg_color_var = tk.StringVar(value="#000000")       # 背景色：黑
        self.note_color_var = tk.StringVar(value="#C3C3C3")     # 音名色：(195,195,195)
        self.lyric_color_var = tk.StringVar(value="#FFFFFF")    # 歌字色：白
        self.lyric_text_color_var = tk.StringVar(value="#FFFFFF")# 歌词色：白
        self.other_text_color_var = tk.StringVar(value="#FFFFFF")# 其他文字色：白

        # 歌词位置下拉框
        self.lyric_pos_var = tk.StringVar(value="上")

        # 显示选项（音素、midinote、波形、全屏）
        self.show_phoneme_var = tk.BooleanVar(value=False)
        self.show_midinote_var = tk.BooleanVar(value=False)
        self.show_waveform_var = tk.BooleanVar(value=False)
        self.fullscreen_var = tk.BooleanVar(value=True)

        # ===== 新增：歌词标签页变量 =====
        self.show_lyric_var = tk.BooleanVar(value=False)  # 显示歌词（默认勾选）
        self.lrc_path_var = tk.StringVar()               # 存储lrc文件路径

        # 是否显示歌词
        self.curve_show = tk.BooleanVar(value=False)

        # ===== 新增：静默/结束显示相关变量 =====
        self.silent_display_var = tk.StringVar(value="R")
        self.silent_custom_text_var = tk.StringVar(value="")
        self.end_display_var = tk.StringVar(value="END")
        self.end_custom_text_var = tk.StringVar(value="")

        # ===================== 【集中样式配置】 =====================
        self.style_config = {
            "font_family": "等线",
            "font_size": 10,
            "frame_padding": "10 10 10 10",
            "global_padx": 2,
            "global_pady": 4,
            "play_btn_pady": 10,
            "play_btn_columnspan": 2,
            "entry_width": 30,
            "label_sticky": tk.E,
            "entry_sticky": tk.W+tk.E,
            "label_style": "Custom.TLabel",
            "button_style": "Custom.TButton",
            "entry_style": "Custom.TEntry",
        }

        # ===================== 【标签页容器】 =====================
        tab_container = tk.Frame(root, bg="white")
        tab_container.pack(fill=tk.X, padx=10, pady=5)

        self.tab_btns = []
        self.tab_frames = []
        tab_names = ["基础", "文件", "播放器", "歌词", "其他"]

        for idx, name in enumerate(tab_names):
            btn = tk.Button(
                tab_container,
                text=name,
                font=(self.style_config["font_family"], self.style_config["font_size"]),
                bg="white", fg="black", relief="flat",
                padx=15, pady=5,
                command=lambda i=idx: self.switch_tab(i)
            )
            btn.grid(row=0, column=idx, padx=1)
            self.tab_btns.append(btn)

            frame = tk.Frame(root, bg="white")
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            self.tab_frames.append(frame)

        self.switch_tab(0)

        # ===================== 【样式配置】 =====================
        style = ttk.Style()
        style.configure("Custom.TButton", font=(self.style_config["font_family"], self.style_config["font_size"]))
        style.configure("Custom.TLabel", font=(self.style_config["font_family"], self.style_config["font_size"]))
        style.configure("Custom.TEntry", font=(self.style_config["font_family"], self.style_config["font_size"]))

        # 初始化标签页（新增歌词+其他标签页初始化）
        self.setup_basic_tab(self.tab_frames[0])
        self.setup_play_tab(self.tab_frames[1])
        self.setup_player_style_tab(self.tab_frames[2])
        self.setup_lyric_tab(self.tab_frames[3])
        self.setup_other_tab(self.tab_frames[4])  # 新增：其他标签页

        self.load_dropped_uplr_file()
    
    def load_dropped_uplr_file(self):
        """处理拖拽到exe上的.uplr文件，自动加载（从命令行参数获取路径）"""
        # 1. 获取命令行参数（sys.argv[0]是程序自身路径，sys.argv[1:]是传递的额外参数）
        if len(sys.argv) > 1:
            dropped_file_path = sys.argv[1].strip()
            
            # 2. 校验文件有效性：路径非空、文件存在、后缀是.uplr
            if (dropped_file_path and 
                os.path.exists(dropped_file_path) and 
                dropped_file_path.lower().endswith(".uplr")):
                
                try:
                    # 3. 自动导入该.uplr文件
                    self.import_uplr_file(dropped_file_path)
                    # 4. 可选：更新上次导入路径并写入配置（保持路径记忆一致性）
                    self.last_open_dir = os.path.dirname(dropped_file_path)
                    self.write_settings()
                    # 5. 提示用户文件已自动加载
                    messagebox.showinfo("自动加载成功", f"已成功加载拖拽的配置文件：\n{dropped_file_path}")
                except Exception as e:
                    messagebox.showerror("ERcode006", f"加载工程文件失败：\n{str(e)}")

    # ========== 新增：配置文件读写方法 ==========
    # ========== 新增：配置文件读写方法 ==========
    def read_settings(self):
        """读取Settings.ini配置文件，加载上次保存的导入/导出路径"""
        # 1. 先获取实际的桌面路径（直接用最佳实践，抛弃 %desktop%）
        default_desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        try:
            # 若配置文件存在，读取内容；不存在则不做操作（后续写入时创建）
            if os.path.exists(self.settings_path):
                self.config.read(self.settings_path, encoding="utf-8")
                
                # 检查节和键是否存在，避免KeyError
                if "PathSettings" in self.config:
                    # 2. 读取配置值，直接用桌面路径作为兜底（无需解析 %desktop%）
                    self.last_open_dir = self.config["PathSettings"].get("last_open_dir", default_desktop_path)
                    self.last_export_dir = self.config["PathSettings"].get("last_export_dir", default_desktop_path)
                    
                    # 3. 校验路径有效性：若路径不存在，使用桌面路径兜底
                    if not os.path.isdir(self.last_open_dir):
                        self.last_open_dir = default_desktop_path
                    if not os.path.isdir(self.last_export_dir):
                        self.last_export_dir = default_desktop_path
            else:
                # 配置文件不存在时，直接初始化为桌面路径
                self.last_open_dir = default_desktop_path
                self.last_export_dir = default_desktop_path
        except Exception as e:
            # 读取失败时使用桌面路径兜底，不影响程序运行
            self.last_open_dir = default_desktop_path
            self.last_export_dir = default_desktop_path
            print(f"读取配置文件失败：{e}")
        
    def write_settings(self):
        """将当前的导入/导出路径写入Settings.ini配置文件"""
        try:
            # 创建/更新配置节和键值
            if "PathSettings" not in self.config:
                self.config["PathSettings"] = {}
            self.config["PathSettings"]["last_open_dir"] = self.last_open_dir
            self.config["PathSettings"]["last_export_dir"] = self.last_export_dir
            
            # 写入配置文件（编码为utf-8，避免中文路径乱码）
            with open(self.settings_path, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"写入配置文件失败：{e}")
        # =======================================

    def outport_uplr_file(self, output_file):
        """ 导出uplr文件"""
        try:
            with open(output_file, "w", encoding="utf-8") as uplr:
                # ========== 第一模块：编码配置 ==========
                uplr.write("#Encoding\n")
                # 写入编码配置（获取 encoding_var 的值）
                uplr.write(f"encoding={self.encoding_var.get()}\n\n")
                
                # ========== 第二模块：基础设置 ==========
                uplr.write("#BasicSettings\n")
                # 基础字符串变量
                uplr.write(f"project_name={self.project_name_var.get()}\n")
                uplr.write(f"ust_path={self.ustx_path_var.get()}\n")
                uplr.write(f"song_name={self.song_name_var.get()}\n")
                uplr.write(f"song_author={self.song_author_var.get()}\n")
                uplr.write(f"ust_author={self.ust_author_var.get()}\n\n")
                
                # ========== 第三模块：显示开关设置（布尔值 1/0） ==========
                uplr.write("#DisplaySettings\n")
                # 布尔值变量（转换为 1/0，贴合你的使用习惯）
                uplr.write(f"show_bpm={1 if self.show_bpm_var.get() else 0}\n")
                uplr.write(f"show_play_time={1 if self.show_play_time_var.get() else 0}\n")
                uplr.write(f"show_song_name={1 if self.show_song_name_var.get() else 0}\n")
                uplr.write(f"show_song_author={1 if self.show_song_author_var.get() else 0}\n")
                uplr.write(f"show_ust_author={1 if self.show_ust_author_var.get() else 0}\n")
                uplr.write(f"show_phoneme={1 if self.show_phoneme_var.get() else 0}\n")
                uplr.write(f"show_midinote={1 if self.show_midinote_var.get() else 0}\n")
                uplr.write(f"show_waveform={1 if self.show_waveform_var.get() else 0}\n")
                uplr.write(f"fullscreen={1 if self.fullscreen_var.get() else 0}\n")
                uplr.write(f"show_lyric={1 if self.show_lyric_var.get() else 0}\n\n")
                
                # ========== 第四模块：颜色配置 ==========
                uplr.write("#ColorSettings\n")
                # 颜色变量
                uplr.write(f"bg_color={self.bg_color_var.get()}\n")
                uplr.write(f"note_color={self.note_color_var.get()}\n")
                uplr.write(f"lyric_color={self.lyric_color_var.get()}\n")
                uplr.write(f"lyric_text_color={self.lyric_text_color_var.get()}\n")
                uplr.write(f"other_text_color={self.other_text_color_var.get()}\n\n")
                
                # ========== 第五模块：歌词与额外配置 ==========
                uplr.write("#LyricAndExtra\n")
                uplr.write(f"lyric_pos={self.lyric_pos_var.get()}\n")
                uplr.write(f"lrc_path={self.lrc_path_var.get()}\n")
                uplr.write(f"silent_display={self.silent_display_var.get()}\n")
                uplr.write(f"silent_custom_text={self.silent_custom_text_var.get()}\n")
                uplr.write(f"end_display={self.end_display_var.get()}\n")
                uplr.write(f"end_custom_text={self.end_custom_text_var.get()}\n")
                uplr.write(f"curve_show={self.curve_show.get()}\n")
            
            # 可选：如果是 GUI 程序，弹出成功提示
            print(f"配置文件已成功导出到：{output_file}")
        
        except Exception as e:
            # 捕获异常，避免程序崩溃
            print(f"导出配置文件失败：{str(e)}")

    def import_uplr_file(self, input_file):
        """读取uplr文件的方法"""
        with open(input_file, "r", encoding="utf-8") as uplr:
            for lines in uplr:
                # 步骤1：清理行首尾的空白、换行符
                lines = lines.strip()
                
                # 步骤2：跳过空行
                if not lines:
                    continue
                
                # 步骤3：跳过开头带 # 的注释行（核心过滤逻辑）
                if lines.startswith("#"):
                    continue
                
                # 步骤4：按 = 分割，最多分割1次（避免值中包含 =）
                line = lines.split("=", 1)
                
                # 步骤5：判断分割结果是否有效（必须包含 =，即列表长度为 2）
                if len(line) != 2:
                    continue  # 跳过格式不正确的行（无 = 或分割后不完整）
                
                # 步骤6：提取键和值，再次清理空白（避免键/值前后有多余空格）
                key = line[0].strip()
                value = line[1].strip()
                if key == "project_name":
                    self.project_name_var.set(value)
                elif key == "ust_path":
                    self.ustx_path_var.set(value)
                elif key == "song_name":
                    self.song_name_var.set(value)
                elif key == "song_author":
                    self.song_author_var.set(value)
                elif key == "ust_author":
                    self.ust_author_var.set(value)
                elif key == "show_bpm":
                    self.show_bpm_var.set(value == "1")
                elif key == "show_play_time":
                    self.show_play_time_var.set(value == "1")
                elif key == "show_song_name":
                    self.show_song_name_var.set(value == "1")
                elif key == "show_song_author":
                    self.show_song_author_var.set(value == "1")
                elif key == "show_ust_author":
                    self.show_ust_author_var.set(value == "1")
                elif key == "encoding":
                    self.encoding_var.set(value)
                elif key == "bg_color":
                    self.bg_color_var.set(value)
                elif key == "note_color":
                    self.note_color_var.set(value)
                elif key == "lyric_color":
                    self.lyric_color_var.set(value)
                elif key == "lyric_text_color":
                    self.lyric_text_color_var.set(value)
                elif key == "other_text_color":
                    self.other_text_color_var.set(value)
                elif key == "lyric_pos":
                    self.lyric_pos_var.set(value)
                elif key == "show_phoneme":
                    self.show_phoneme_var.set(value == "1")
                elif key == "show_midinote":
                    self.show_midinote_var.set(value == "1")
                elif key == "show_waveform":
                    self.show_waveform_var.set(value == "1")
                elif key == "fullscreen":
                    self.fullscreen_var.set(value == "1")
                elif key == "show_lyric":
                    self.show_lyric_var.set(value == "1")
                elif key == "lrc_path":
                    self.lrc_path_var.set(value)
                elif key == "silent_display":
                    self.silent_display_var.set(value)
                elif key == "silent_custom_text":
                    self.silent_custom_text_var.set(value)
                elif key == "end_display":
                    self.end_display_var.set(value)
                elif key == "end_custom_text":
                    self.end_custom_text_var.set(value)
                elif key == "curve_show":
                    self.curve_show.set(value == "1")

    def on_export(self):
        """弹出“另存为”对话框，让用户选择导出路径和文件名"""
        output_file = filedialog.asksaveasfilename(
            title="导出你的工程文件",
            initialfile=self.project_name_var.get(),
            defaultextension=".uplr",  # 默认后缀名
            filetypes=[
                ("ustPlayer工程文件", "*.uplr"),
                ("所有文件", "*.*")
            ],
            initialdir=self.last_export_dir  # 修改：使用上次保存的导出路径
        )
        
        # 如果用户点击了“取消”，则返回空字符串，不执行导出
        if not output_file:
            return
        
        # 调用你的导出函数
        self.outport_uplr_file(output_file)
        tk.messagebox.showinfo("成功", f"工程已导出到：\n{output_file}")
        
        # ========== 新增：更新上次导出路径并写入配置 ==========
        self.last_export_dir = os.path.dirname(output_file)  # 提取文件所在目录
        self.write_settings()
    
    def on_open(self):
        """
        弹出打开文件对话框，让用户选择要读取的 .uplr 配置文件
        选择后调用读取函数处理文件
        """
        # 弹出“打开文件”对话框（修改：使用上次保存的导入路径作为初始目录）
        input_file = filedialog.askopenfilename(
            title="打开工程文件",  # 对话框窗口标题
            defaultextension=".uplr",  # 默认文件扩展名
            filetypes=[
                ("ustPlayer工程文件", "*.uplr"),  # 优先显示的文件类型（和你的配置文件格式对应）
                ("所有文件", "*.*")           # 兜底：显示所有文件
            ],
            initialdir=self.last_open_dir  # 修改：使用上次保存的导入路径
        )
        
        # 判断用户是否点击了“取消”（点击取消会返回空字符串）
        if not input_file:
            return  # 无操作，直接返回
        
        try:
            # 调用你的读取函数（import_uplr_file）处理选中的文件
            self.import_uplr_file(input_file)
            messagebox.showinfo("成功", f"已成功打开并加载工程：\n{input_file}")
            
            # ========== 新增：更新上次导入路径并写入配置 ==========
            self.last_open_dir = os.path.dirname(input_file)  # 提取文件所在目录
            self.write_settings()
        except Exception as e:
            messagebox.showerror("ERcode007", f"加载文件失败：\n{str(e)}")

    def switch_tab(self, idx):
        """为标签页创建frame栈"""
        for frame in self.tab_frames:
            frame.pack_forget()
        for btn in self.tab_btns:
            btn.config(bg="white", fg="black", relief="flat")
        self.tab_frames[idx].pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tab_btns[idx].config(bg="#4a86e8", fg="white", relief="flat")

    def setup_basic_tab(self, parent_frame):
        """基础页的初始化"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部按钮
        ttk.Button(
            frame, text="保存项目", command=self.on_export, style=cfg["button_style"]
        ).grid(row=0, column=1, padx=cfg["global_padx"], pady=cfg["global_pady"], sticky=tk.W)
        ttk.Button(
            frame, text="导入项目", command=self.on_open, style=cfg["button_style"]
        ).grid(row=0, column=0, padx=cfg["global_padx"], pady=cfg["global_pady"], sticky=tk.W)

        # 分隔线
        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 项目信息标题
        ttk.Label(
            frame, text="/ 关于项目", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 项目信息输入框
        ttk.Label(frame, text="项目名：", style=cfg["label_style"]).grid(
            row=3, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.project_name_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=3, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="曲名&曲师：", style=cfg["label_style"]).grid(
            row=4, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.song_name_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=4, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="MIDI作者：", style=cfg["label_style"]).grid(
            row=5, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.song_author_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=5, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="调音师：", style=cfg["label_style"]).grid(
            row=6, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.ust_author_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=6, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ========== 分隔线（保留原有，无修改） ==========
        ttk.Separator(frame, orient="horizontal").grid(
            row=7, column=0, columnspan=2, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ========== 显示选项（核心修复：优化列数、调整排版，解决溢出） ==========
        # 1. 基础信息标题（仍保留 columnspan=2，适配原有容器列数）
        ttk.Label(
            frame, text="/ 基础信息", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 2. 复选框布局修复：不超出 2 列，分多行排列，避免溢出
        # 第 9 行：放 2 个复选框（column=0 和 column=1，不超出容器列数）
        tk.Checkbutton(frame, text="显示BPM", variable=self.show_bpm_var,
                    font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        tk.Checkbutton(frame, text="显示播放时间", variable=self.show_play_time_var,
                    font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # 第 10 行：放 2 个复选框（把“显示曲目信息”移到这一行，column=0 和 column=1）
        tk.Checkbutton(frame, text="显示曲目信息", variable=self.show_song_name_var,
                    font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=10, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])  # 改为 column=0，不溢出
        tk.Checkbutton(frame, text="显示MIDI作者", variable=self.show_song_author_var,
                    font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=10, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # 第 11 行：放“显示调音师”（column=0，保持排版整齐）
        tk.Checkbutton(frame, text="显示调音师", variable=self.show_ust_author_var,
                    font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=11, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])  # 新增一行，避免拥挤

        # ========== Play按钮（调整 row 为 12，避免和复选框重叠） ==========
        ttk.Button(
            frame, text="播放Play", command=self.on_play_click, style=cfg["button_style"]
        ).grid(
            row=12, column=0, columnspan=cfg["play_btn_columnspan"],
            padx=cfg["global_padx"], pady=cfg["play_btn_pady"], sticky=tk.EW
        )

        frame.grid_columnconfigure(1, weight=1)

    def setup_play_tab(self, parent_frame):
        """文件标签页：导入框 + 编码选择 + 内容预览"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True)

        frame.bind("<Button-1>", self.on_play_tab_clicked)

        # ---------------------- 第一行：ust导入框 + 选择按钮 ----------------------
        ttk.Label(frame, text="ust:", style=cfg["label_style"]).grid(
            row=0, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        self.ustx_entry = ttk.Entry(
            frame, textvariable=self.ustx_path_var, width=50, style=cfg["entry_style"]
        )
        self.ustx_entry.grid(
            row=0, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Button(frame, text="选择ust文件", command=self.select_ustx_file, style=cfg["button_style"]).grid(
            row=0, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])
        
        tk.Checkbutton(frame, text="显示音高线变化", variable=self.curve_show,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=1, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        

        # ---------------------- 第二行：编码选择下拉框 ----------------------
        ttk.Label(frame, text="编码方式:", style=cfg["label_style"]).grid(
            row=2, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        self.encoding_combobox = ttk.Combobox(
            frame, textvariable=self.encoding_var,
            values=["UTF-8", "GBK", "Shift-JIS"],
            state="readonly",
            font=(cfg["font_family"], cfg["font_size"])
        )
        self.encoding_combobox.grid(
            row=2, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        # 绑定编码切换事件
        self.encoding_combobox.bind("<<ComboboxSelected>>", self.on_encoding_change)

        # ---------------------- 第三行：ust内容预览框（带滚动条） ----------------------
        ttk.Label(frame, text="编码检查 ⬇", style=cfg["label_style"]).grid(
            row=2, column=2, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 预览文本框 + 滚动条
        self.preview_text = scrolledtext.ScrolledText(
            frame,
            font=(cfg["font_family"], cfg["font_size"]),
            wrap=tk.WORD,
            bg="white",
            height=15
        )
        self.preview_text.grid(
            row=3, column=0, columnspan=3, sticky=tk.NSEW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 让预览框自适应拉伸
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(1, weight=1)
            
    def on_play_tab_clicked(self, event):
        """点击文件标签页Frame，自动触发UST预览（有有效路径时）"""
        # 1. 获取并清理 UST 路径（核心：判断路径是否有效，而非绑定阶段）
        ustx_path = self.ustx_path_var.get()
        
        # 2. 只有路径非空且文件存在，才触发预览
        if ustx_path and os.path.exists(ustx_path):
            self.preview_ust_content(ustx_path)

    def setup_player_style_tab(self, parent_frame):
        """播放器样式标签页：颜色选择 + 歌词位置 + 显示选项 + 静默/结束显示"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        ttk.Label(
            frame, text="/ 播放器样式", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 颜色选择行 ----------------------
        # 背景色
        ttk.Label(frame, text="背景色:", style=cfg["label_style"]).grid(
            row=1, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(
            frame, textvariable=self.bg_color_var, width=10, style=cfg["entry_style"]
        ).grid(
            row=1, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Button(
            frame, text="更改", command=lambda: self.choose_color(self.bg_color_var), style=cfg["button_style"]
        ).grid(row=1, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 音名色
        ttk.Label(frame, text="音名色:", style=cfg["label_style"]).grid(
            row=2, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(
            frame, textvariable=self.note_color_var, width=10, style=cfg["entry_style"]
        ).grid(
            row=2, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Button(
            frame, text="更改", command=lambda: self.choose_color(self.note_color_var), style=cfg["button_style"]
        ).grid(row=2, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 歌字色
        ttk.Label(frame, text="歌字色:", style=cfg["label_style"]).grid(
            row=3, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(
            frame, textvariable=self.lyric_color_var, width=10, style=cfg["entry_style"]
        ).grid(
            row=3, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Button(
            frame, text="更改", command=lambda: self.choose_color(self.lyric_color_var), style=cfg["button_style"]
        ).grid(row=3, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 歌词色
        ttk.Label(frame, text="歌词色:", style=cfg["label_style"]).grid(
            row=4, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(
            frame, textvariable=self.lyric_text_color_var, width=10, style=cfg["entry_style"]
        ).grid(
            row=4, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Button(
            frame, text="更改", command=lambda: self.choose_color(self.lyric_text_color_var), style=cfg["button_style"]
        ).grid(row=4, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 其他文字色
        ttk.Label(frame, text="其他文字色:", style=cfg["label_style"]).grid(
            row=5, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(
            frame, textvariable=self.other_text_color_var, width=10, style=cfg["entry_style"]
        ).grid(
            row=5, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Button(
            frame, text="更改", command=lambda: self.choose_color(self.other_text_color_var), style=cfg["button_style"]
        ).grid(row=5, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 歌词位置
        ttk.Label(frame, text="歌词位置:", style=cfg["label_style"]).grid(
            row=6, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Combobox(
            frame, textvariable=self.lyric_pos_var,
            values=["上", "下"],
            state="readonly",
            font=(cfg["font_family"], cfg["font_size"])
        ).grid(
            row=6, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=7, column=0, columnspan=3, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        """# ---------------------- 显示选项（勾选框） ----------------------
        ttk.Label(
            frame, text="- 显示选项 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=8, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 显示音素
        tk.Checkbutton(frame, text="显示音素", variable=self.show_phoneme_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        # 显示midinote
        tk.Checkbutton(frame, text="显示midinote", variable=self.show_midinote_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        # 显示波形
        tk.Checkbutton(frame, text="显示波形", variable=self.show_waveform_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=10, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        # 全屏显示
        tk.Checkbutton(frame, text="全屏显示", variable=self.fullscreen_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=10, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])"""

        """# ---------------------- 【新增】静默/结束时显示设置 ----------------------
        # 分隔线
        ttk.Separator(frame, orient="horizontal").grid(
            row=11, column=0, columnspan=3, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])"""

        # 标题
        ttk.Label(
            frame, text="/ 其他显示设置", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=12, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 1. 静默时显示（下拉框）
        ttk.Label(frame, text="静默时显示:", style=cfg["label_style"]).grid(
            row=13, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Combobox(
            frame, textvariable=self.silent_display_var,
            values=["R", "-", "自定义文字", "什么都不显示"],
            state="readonly",
            font=(cfg["font_family"], cfg["font_size"])
        ).grid(
            row=13, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        # 绑定下拉选择事件
        self.silent_display_var.trace("w", self.update_silent_custom_entry)

        # 2. 自定义静默文字（输入框，默认隐藏）
        self.silent_custom_entry = ttk.Entry(
            frame, textvariable=self.silent_custom_text_var, width=20, style=cfg["entry_style"]
        )
        # 初始隐藏
        self.silent_custom_entry.grid(
            row=13, column=2, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        self.silent_custom_entry.grid_remove()  # 隐藏

        # 3. 结束时显示（下拉框）
        ttk.Label(frame, text="结束时显示:", style=cfg["label_style"]).grid(
            row=14, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Combobox(
            frame, textvariable=self.end_display_var,
            values=["END", "-", "自定义文字", "什么都不显示"],
            state="readonly",
            font=(cfg["font_family"], cfg["font_size"])
        ).grid(
            row=14, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        # 绑定下拉选择事件
        self.end_display_var.trace("w", self.update_end_custom_entry)

        # 4. 自定义结束文字（输入框，默认隐藏）
        self.end_custom_entry = ttk.Entry(
            frame, textvariable=self.end_custom_text_var, width=20, style=cfg["entry_style"]
        )
        # 初始隐藏
        self.end_custom_entry.grid(
            row=14, column=2, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        self.end_custom_entry.grid_remove()  # 隐藏

        # 让布局自适应拉伸
        frame.grid_columnconfigure(1, weight=1)

    # ===== 歌词标签页实现 =====
    def setup_lyric_tab(self, parent_frame):
        """歌词标签页：显示歌词复选框 + lrc文件导入"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        ttk.Label(
            frame, text="/ 歌词", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 显示歌词复选框 ----------------------
        tk.Checkbutton(frame, text="展示歌词", variable=self.show_lyric_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- LRC文件导入 ----------------------
        ttk.Label(frame, text="歌词文件（.lrc）:", style=cfg["label_style"]).grid(
            row=3, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # LRC路径显示框
        ttk.Entry(
            frame, textvariable=self.lrc_path_var, width=50, style=cfg["entry_style"]
        ).grid(
            row=3, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 选择LRC文件按钮
        ttk.Button(frame, text="选择文件", command=self.select_lrc_file, style=cfg["button_style"]).grid(
            row=3, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 让布局自适应拉伸
        frame.grid_columnconfigure(1, weight=1)

    # ===== 新增：其他标签页实现 =====
    def setup_other_tab(self, parent_frame):
        """其他标签页：版权信息、文件转换、用户协议、开源许可"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        ttk.Label(
            frame, text="/ 关于软件", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 版权信息 ----------------------
        # 版权文本（蓝色下划线模拟超链接）
        copyright_label = ttk.Label(
            frame, 
            text="ustPlayer-v26a31 (c)2026 SYEternalR", 
            style=cfg["label_style"],
            foreground="#0066CC",
            cursor="hand2"  # 鼠标悬浮显示手型
        )
        copyright_label.grid(
            row=1, column=0, columnspan=3, sticky=tk.W, 
            padx=10, pady=(cfg["global_pady"]*2, cfg["global_pady"])
        )
        # 绑定点击事件
        copyright_label.bind("<Button-1>", lambda e: self.open_webpage("https://space.bilibili.com/661930756"))

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky=tk.EW, 
            padx=cfg["global_padx"], pady=cfg["global_pady"]
        )

        # ---------------------- 工具类功能 ----------------------
        ttk.Label(
            frame, text="/ 外部工具与纠错", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 文件转换按钮（跳转utaformatix.tk）
        ttk.Button(
            frame, 
            text="UtaFormatix", 
            command=lambda: self.open_webpage("https://utaformatix.tk/"),
            style=cfg["button_style"]
        ).grid(
            row=4, column=0, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        # 文件转换按钮（跳转utaformatix.tk）
        ttk.Button(
            frame, 
            text="ERcodes", 
            command=lambda: subprocess.run(['notepad.exe', "ERcode.txt"], shell=True),
            style=cfg["button_style"]
        ).grid(
            row=4, column=1, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=5, column=0, columnspan=3, sticky=tk.EW, 
            padx=cfg["global_padx"], pady=cfg["global_pady"]
        )

        # ---------------------- 协议相关 ----------------------
        ttk.Label(
            frame, text="/ 协议与许可", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 用户协议按钮
        ttk.Button(
            frame, 
            text="使用协议", 
            command=lambda: subprocess.run(['notepad.exe', "Terms.txt"], shell=True),
            style=cfg["button_style"]
        ).grid(
            row=7, column=0, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        ttk.Button(
            frame, 
            text="Github仓库", 
            command=lambda: self.open_webpage("https://github.com/SYEternalR/ustPlayer"),
            style=cfg["button_style"]
        ).grid(
            row=7, column=1, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=8, column=0, columnspan=3, sticky=tk.EW, 
            padx=cfg["global_padx"], pady=cfg["global_pady"]
        )

        tk.Label(frame, 
                 text="你知道吗：alpha版本在提交托管时曾被错误地命名为ustPlyaer。orz"
                ).grid(row=9,columnspan=3,  sticky=tk.W)

        # 让布局自适应拉伸
        frame.grid_columnconfigure(1, weight=1)

    # ===================== 【新增】静默/结束自定义输入框显示/隐藏逻辑 =====================
    def update_silent_custom_entry(self, *args):
        """根据静默时显示的选择，显示/隐藏自定义文字输入框"""
        selected = self.silent_display_var.get()
        if selected == "自定义文字":
            self.silent_custom_entry.grid()  # 显示
        else:
            self.silent_custom_entry.grid_remove()  # 隐藏

    def update_end_custom_entry(self, *args):
        """根据结束时显示的选择，显示/隐藏自定义文字输入框"""
        selected = self.end_display_var.get()
        if selected == "自定义文字":
            self.end_custom_entry.grid()  # 显示
        else:
            self.end_custom_entry.grid_remove()  # 隐藏

    # ===== 新增：网页跳转函数 =====
    def open_webpage(self, url):
        """打开指定网页"""
        try:
            webbrowser.open(url, new=2)  # new=2 表示在新标签页打开
        except Exception as e:
            messagebox.showerror("ERcode003", f"打开网页失败：{str(e)}")

    # ===== 选择LRC文件函数 =====
    def select_lrc_file(self):
        """打开文件选择框，选择.lrc歌词文件"""
        file_path = filedialog.askopenfilename(
            title="选择LRC歌词文件",
            filetypes=[("LRC歌词文件", "*.lrc"), ("所有文件", "*.*")]
        )
        if file_path:
            self.lrc_path_var.set(file_path)  # 把选中的路径赋值给变量

    # ===================== 【颜色选择】 =====================
    def choose_color(self, color_var):
        """打开取色器，选择颜色"""
        color = colorchooser.askcolor(title="选择颜色", initialcolor=color_var.get())
        if color[1]:  # 选择了颜色
            color_var.set(color[1])

    def select_ustx_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ust文件", filetypes=[("UST文件", "*.ust"), ("所有文件", "*.*")]
        )
        if file_path:
            self.ustx_path_var.set(file_path)
            # 选择后自动预览
            self.preview_ust_content(file_path)

    def preview_ust_content(self, file_path):
        """按当前编码读取ust并预览"""
        try:
            encoding = self.encoding_var.get()
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            # 清空并写入预览框
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("ERcode002", f"读取文件失败：{str(e)}")

    def on_encoding_change(self, event):
        """编码切换时刷新预览框"""
        ustx_path = self.ustx_path_var.get().strip()
        if ustx_path and os.path.exists(ustx_path):
            self.preview_ust_content(ustx_path)

    # ===== 新增：线程安全的GUI播放方法（运行在主线程） =====
    def _safe_display_play(self, ust_info):
        """
        主线程执行的GUI播放方法，避免子线程直接操作GUI
        由 after() 方法从子线程投递到主线程调用
        """
        try:
            up.display(ust_info)
        except Exception as e:
            messagebox.showerror("ERcode005", f"播放器运行失败：{str(e)}")

    def on_play_click(self):
        """Play按钮逻辑（完善参数传递，线程安全）"""
        ustx_path = self.ustx_path_var.get().strip()
        if not ustx_path or not os.path.exists(ustx_path):
            messagebox.showerror("ERcode001", "请选择有效的UST文件！")
            return

        try:
            # 1. 从UST文件提取核心信息
            encoding = self.encoding_var.get()
            core_ust_info = ur.get_ust_info(ustx_path, encoding)
            
            # 2. 补全完整的ust_info参数（所有GUI配置项）
            ust_info = {
                # 核心解析信息
                "version": core_ust_info.get("version", "未知版本"),
                "tempo": core_ust_info.get("tempo", 120.0),  # 兜底120BPM
                "tracks": core_ust_info.get("tracks", 1),
                "notes": core_ust_info.get("notes", []),
                
                # 显示配置（来自GUI勾选框）
                "show_config": {
                    "bpm": self.show_bpm_var.get(),
                    "play_time": self.show_play_time_var.get(),
                    "song_name": self.show_song_name_var.get(),
                    "song_author": self.show_song_author_var.get(),
                    "ust_author": self.show_ust_author_var.get(),
                    "lyric": self.show_lyric_var.get(),
                    "curve_show": self.curve_show.get()
                },
                
                # 项目信息（来自GUI输入框）
                "project_info": {
                    "project_name": self.project_name_var.get(),
                    "song_name": self.song_name_var.get(),
                    "song_author": self.song_author_var.get(),
                    "ust_author": self.ust_author_var.get()
                },
                
                # 编码信息
                "encoding": encoding,
                
                # 播放器样式（来自GUI配置，补全所有兜底值）
                "player_style": {
                    "bg_color": self.bg_color_var.get(),
                    "note_color": self.note_color_var.get(),
                    "lyric_color": self.lyric_color_var.get(),
                    "lyric_text_color": self.lyric_text_color_var.get(),
                    "other_text_color": self.other_text_color_var.get(),
                    "lyric_pos": self.lyric_pos_var.get(),
                    "show_phoneme": self.show_phoneme_var.get(),
                    "show_midinote": self.show_midinote_var.get(),
                    "show_waveform": self.show_waveform_var.get(),
                    "fullscreen": self.fullscreen_var.get(),
                    "lrc_path": self.lrc_path_var.get(),
                    "lrc_gray_level": 180,  # 兜底歌词灰度值，适配ustplayer.py
                    "lrc_font_scale": 0.03,  # 兜底歌词字体缩放，适配ustplayer.py
                    
                    # 静默/结束显示（处理“什么都不显示”逻辑）
                    "silent_display": self.silent_display_var.get() if self.silent_display_var.get() != "什么都不显示" else "",
                    "silent_custom_text": self.silent_custom_text_var.get(),
                    "end_display": self.end_display_var.get() if self.end_display_var.get() != "什么都不显示" else "",
                    "end_custom_text": self.end_custom_text_var.get()
                }
            }
            
            # 3. 提示用户即将播放
            messagebox.showinfo("WaitingForUser", "按下确认后将启动播放器，鼠标单击后按ESC键退出全屏")
            
            # 4. 线程安全：启动子线程，GUI操作投递到主线程
            play_ust(ust_info, self.root, self._safe_display_play)
            
        except UnicodeDecodeError:
            messagebox.showerror("ERcode004", "解析UST文件失败：使用了错误的编码，请切换编码后重试")
        except Exception as e:
            messagebox.showerror("ERcode999", f"播放准备失败：{str(e)}")

# ---------------------- main.py 原始内容（改造为线程安全版本） ----------------------
# ---------------------- 核心：播放程序（线程安全化） ----------------------
def play_ust(ust_info, root, safe_display_func):
    """main.py 中的播放核心逻辑（独立线程执行，不阻塞界面，线程安全）"""
    def play_task():
        print(ust_info)
        print("\n=== main.py 播放程序启动 ===")
        print(f"版本：{ust_info['version']}")
        print(f"速度：{ust_info['tempo']} BPM")
        print(f"音符数量：{len(ust_info['notes'])}")
        print(f"歌词列表：{[note['lyric'] for note in ust_info['notes']]}")
        
        # 线程安全：通过 root.after() 将 GUI 操作投递到主线程
        root.after(0, safe_display_func, ust_info)
    
    # 启动子线程（仅执行非GUI操作，GUI操作投递到主线程）
    play_thread = threading.Thread(target=play_task, daemon=True)
    play_thread.start()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    root = tk.Tk() 
    userform = UstxPlayerSettings(root)
    root.mainloop()

# 感谢你看到这里