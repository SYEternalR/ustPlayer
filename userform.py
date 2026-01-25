# userform.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, colorchooser
import os
import webbrowser  # 新增：用于打开网页
import subprocess  # 补充：修复其他标签页的subprocess导入
import ustreader as ur

class UstxPlayerSettings:
    def __init__(self, root, play_callback=None):
        self.root = root
        self.root.title("ustPlayer - v26a24")
        self.root.geometry("800x500")
        self.play_callback = play_callback

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
        self.encoding_var = tk.StringVar(value="UTF-8")

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
        self.show_lyric_var = tk.BooleanVar(value=True)  # 显示歌词（默认勾选）
        self.lrc_path_var = tk.StringVar()               # 存储lrc文件路径

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
        tab_names = ["基础", "ust", "播放器样式", "歌词", "其他"]

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

    def switch_tab(self, idx):
        for frame in self.tab_frames:
            frame.pack_forget()
        for btn in self.tab_btns:
            btn.config(bg="white", fg="black", relief="flat")
        self.tab_frames[idx].pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tab_btns[idx].config(bg="#4a86e8", fg="white", relief="flat")

    def setup_basic_tab(self, parent_frame):
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        """# 顶部按钮
        ttk.Button(
            frame, text="保存项目", command=self.save_project, style=cfg["button_style"]
        ).grid(row=0, column=0, padx=cfg["global_padx"], pady=cfg["global_pady"], sticky=tk.W)
        ttk.Button(
            frame, text="导入项目", command=self.load_project, style=cfg["button_style"]
        ).grid(row=0, column=1, padx=cfg["global_padx"], pady=cfg["global_pady"], sticky=tk.W)
"""
        # 项目信息标题
        ttk.Label(
            frame, text="- 关于项目 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 项目信息输入框
        ttk.Label(frame, text="项目名：", style=cfg["label_style"]).grid(
            row=2, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.project_name_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=2, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="曲名：", style=cfg["label_style"]).grid(
            row=3, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.song_name_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=3, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="曲作者：", style=cfg["label_style"]).grid(
            row=4, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.song_author_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=4, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Label(frame, text="ust作者：", style=cfg["label_style"]).grid(
            row=5, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        ttk.Entry(frame, textvariable=self.ust_author_var, width=cfg["entry_width"], style=cfg["entry_style"]).grid(
            row=5, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 分隔线
        ttk.Separator(frame, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 显示选项
        ttk.Label(
            frame, text="- 显示选项 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        tk.Checkbutton(frame, text="显示BPM", variable=self.show_bpm_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=8, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        tk.Checkbutton(frame, text="显示播放时间", variable=self.show_play_time_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=8, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        tk.Checkbutton(frame, text="显示曲名", variable=self.show_song_name_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])
        tk.Checkbutton(frame, text="显示曲作者", variable=self.show_song_author_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=9, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        tk.Checkbutton(frame, text="显示ust作者", variable=self.show_ust_author_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=10, column=0, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # Play按钮
        ttk.Button(
            frame, text="Play", command=self.on_play_click, style=cfg["button_style"]
        ).grid(
            row=12, column=0, columnspan=cfg["play_btn_columnspan"],
            padx=cfg["global_padx"], pady=cfg["play_btn_pady"], sticky=tk.EW
        )

        frame.grid_columnconfigure(1, weight=1)

    def setup_play_tab(self, parent_frame):
        """ust标签页：导入框 + 编码选择 + 内容预览"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True)

        # ---------------------- 第一行：ust导入框 + 选择按钮 ----------------------
        ttk.Label(frame, text="ust:", style=cfg["label_style"]).grid(
            row=0, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        self.ustx_entry = ttk.Entry(
            frame, textvariable=self.ustx_path_var, width=50, style=cfg["entry_style"]
        )
        self.ustx_entry.grid(
            row=0, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        ttk.Button(frame, text="选择", command=self.select_ustx_file, style=cfg["button_style"]).grid(
            row=0, column=2, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 第二行：编码选择下拉框 ----------------------
        ttk.Label(frame, text="编码:", style=cfg["label_style"]).grid(
            row=1, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        self.encoding_combobox = ttk.Combobox(
            frame, textvariable=self.encoding_var,
            values=["UTF-8", "GBK", "Shift-JIS"],
            state="readonly",
            font=(cfg["font_family"], cfg["font_size"])
        )
        self.encoding_combobox.grid(
            row=1, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])
        # 绑定编码切换事件
        self.encoding_combobox.bind("<<ComboboxSelected>>", self.on_encoding_change)

        # ---------------------- 第三行：ust内容预览框（带滚动条） ----------------------
        ttk.Label(frame, text="ust内容预览", style=cfg["label_style"]).grid(
            row=2, column=0, columnspan=3, sticky=tk.E, padx=cfg["global_padx"], pady=cfg["global_pady"])

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

    def setup_player_style_tab(self, parent_frame):
        """播放器样式标签页：颜色选择 + 歌词位置 + 显示选项 + 静默/结束显示"""
        cfg = self.style_config
        frame = ttk.Frame(parent_frame, padding=cfg["frame_padding"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        ttk.Label(
            frame, text="- 播放器样式设置 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
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

        # ---------------------- 显示选项（勾选框） ----------------------
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
            row=10, column=1, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # ---------------------- 【新增】静默/结束时显示设置 ----------------------
        # 分隔线
        ttk.Separator(frame, orient="horizontal").grid(
            row=11, column=0, columnspan=3, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 标题
        ttk.Label(
            frame, text="- 静默/结束显示 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
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
            frame, text="- 歌词设置 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 显示歌词复选框 ----------------------
        tk.Checkbutton(frame, text="显示歌词", variable=self.show_lyric_var,
                      font=(cfg["font_family"], cfg["font_size"]), bg="white").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=10, pady=cfg["global_pady"])

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky=tk.EW, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- LRC文件导入 ----------------------
        ttk.Label(frame, text="歌词文件:", style=cfg["label_style"]).grid(
            row=3, column=0, sticky=cfg["label_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # LRC路径显示框
        ttk.Entry(
            frame, textvariable=self.lrc_path_var, width=50, style=cfg["entry_style"]
        ).grid(
            row=3, column=1, sticky=cfg["entry_sticky"], padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 选择LRC文件按钮
        ttk.Button(frame, text="选择", command=self.select_lrc_file, style=cfg["button_style"]).grid(
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
            frame, text="- 关于软件 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # ---------------------- 版权信息 ----------------------
        # 版权文本（蓝色下划线模拟超链接）
        copyright_label = ttk.Label(
            frame, 
            text="ustPlayer-v26a24 © 2026 SYEternalR", 
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
            frame, text="- 工具功能 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 文件转换按钮（跳转utaformatix.tk）
        ttk.Button(
            frame, 
            text="UtaFormatix", 
            command=lambda: self.open_webpage("https://utaformatix.tk/"),
            style=cfg["button_style"]
        ).grid(
            row=4, column=0, columnspan=3, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        # 文件转换按钮（跳转utaformatix.tk）
        ttk.Button(
            frame, 
            text="DEBUG - ERcodes", 
            command=lambda: subprocess.run(['notepad.exe', "ERcode.txt"], shell=True),
            style=cfg["button_style"]
        ).grid(
            row=4, column=1, columnspan=3, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        # ---------------------- 分隔线 ----------------------
        ttk.Separator(frame, orient="horizontal").grid(
            row=5, column=0, columnspan=3, sticky=tk.EW, 
            padx=cfg["global_padx"], pady=cfg["global_pady"]
        )

        # ---------------------- 协议相关 ----------------------
        ttk.Label(
            frame, text="- 协议与许可 -", style=cfg["label_style"], font=(cfg["font_family"], 11, "bold")
        ).grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=cfg["global_padx"], pady=cfg["global_pady"])

        # 用户协议按钮
        ttk.Button(
            frame, 
            text="用户协议", 
            command=lambda: subprocess.run(['notepad.exe', "Terms.txt"], shell=True),
            style=cfg["button_style"]
        ).grid(
            row=7, column=0, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

        ttk.Button(
            frame, 
            text="Github", 
            command=lambda: self.open_webpage("https://github.com/SYEternalR/ustPlaryer"),
            style=cfg["button_style"]
        ).grid(
            row=7, column=1, sticky=tk.W, 
            padx=10, pady=cfg["global_pady"]
        )

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

    # ===================== 【功能函数】 =====================
    def save_project(self):
        messagebox.showinfo("提示", "保存项目功能待实现")

    def load_project(self):
        messagebox.showinfo("提示", "导入项目功能待实现")

    def select_ustx_file(self):
        file_path = filedialog.askopenfilename(
            title="选择ustx文件", filetypes=[("UST文件", "*.ust"), ("所有文件", "*.*")]
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

    def on_play_click(self):
        """Play按钮逻辑（新增歌词配置传递）"""
        ustx_path = self.ustx_path_var.get().strip()
        if not ustx_path or not os.path.exists(ustx_path):
            messagebox.showerror("ERcode001", "请选择有效的UST文件！")
            return

        try:
            ust_info = ur.get_ust_info(ustx_path)
            # 传递配置状态
            ust_info["show_config"] = {
                "bpm": self.show_bpm_var.get(),
                "play_time": self.show_play_time_var.get(),
                "song_name": self.show_song_name_var.get(),
                "song_author": self.show_song_author_var.get(),
                "ust_author": self.show_ust_author_var.get(),
                "lyric": self.show_lyric_var.get()  # 新增：传递显示歌词的状态
            }
            # 传递项目信息
            ust_info["project_info"] = {
                "project_name": self.project_name_var.get(),
                "song_name": self.song_name_var.get(),
                "song_author": self.song_author_var.get(),
                "ust_author": self.ust_author_var.get()
            }
            # 传递编码
            ust_info["encoding"] = self.encoding_var.get()
            # 传递播放器样式
            ust_info["player_style"] = {
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
                "lrc_path": self.lrc_path_var.get(),  # 新增：传递LRC文件路径
                # 新增：静默/结束显示配置
                "silent_display": self.silent_display_var.get(),
                "silent_custom_text": self.silent_custom_text_var.get(),
                "end_display": self.end_display_var.get(),
                "end_custom_text": self.end_custom_text_var.get(),
            }

            messagebox.showinfo("Waiting for user", "按下确认后即开始播放")
            if self.play_callback:
                self.play_callback(ust_info)
        except Exception as e:
            messagebox.showerror("ERcode999", f"解析失败：{str(e)}")

# 启动函数
def callout():
    root = tk.Tk()
    userform = UstxPlayerSettings(root)
    root.mainloop()
    return userform

if __name__ == "__main__":
    callout()