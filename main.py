# main.py — PySide6 版主窗口
from __future__ import annotations
import os
import sys
from types import MethodType
import webbrowser
import subprocess
import threading # pyright: ignore[reportUnusedImport]
import configparser
import hashlib
import urllib.request

from PySide6.QtCore import Qt, QTimer # pyright: ignore[reportUnusedImport]
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QComboBox,
    QTextEdit, QFrame, QFileDialog, QMessageBox, QColorDialog,
)

import ust_reader as ur
from ust_types import StyleConfig, UstInfo, CoreUstInfo, PlayerStyle, ShowConfig, ProjectInfo
from get_setting import Setting, get_setting


# ===================== 默认样式配置（带类型）=====================
STYLE_CFG: StyleConfig = {
    "font_family": "Microsoft YaHei",
    "font_size": 10,
    "frame_padding": "10 10 10 10",
    "global_padx": 2,
    "global_pady": 4,
    "play_btn_pady": 10,
    "play_btn_columnspan": 2,
    "entry_width": 30,
    "label_sticky": "E",
    "entry_sticky": "WE",
    "label_style": "Custom.TLabel",
    "button_style": "Custom.TButton",
    "entry_style": "Custom.TEntry",
}
SETTING: Setting = get_setting()

# ---------------------------------------------------------------------------
# ---------------------- 播放线程辅助函数 ----------------------
def play_ust(ust_info: UstInfo, main_win: UstPlayerMain, safe_display_func: MethodType) -> None: # pyright: ignore[reportGeneralTypeIssues, reportPrivateUsage]
    """在后台线程中启动播放，GUI 操作通过 QTimer 投递到主线程。"""
    def play_task() -> None:
        print(ust_info)
        print("\n=== ustPlayer play thread ===")
        print(f"version = {ust_info['version']}")
        print(f"tempo   = {ust_info['tempo']} BPM")
        print(f"notes   = {len(ust_info['notes'])}")
        safe_display_func(ust_info)
        # QTimer.singleShot(0, lambda: safe_display_func(ust_info))

    # t = threading.Thread(target=play_task, daemon=True)
    # t.start()

    play_task()  # 目前先直接在主线程执行，后续如果播放逻辑复杂了再切回后台线程


# ---------------------------------------------------------------------------
# ---------------------- 主窗口 ----------------------
class UstPlayerMain(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"{SETTING['Name']} – v{SETTING['Version']}")
        self.resize(820, 540)

        # ---- 文件系统路径 ----
        self.program_root = os.path.dirname(os.path.abspath(__file__))
        self.settings_path = os.path.join(self.program_root, "Settings.ini")
        self.terms_file_path = os.path.join(self.program_root, "Terms.txt")
        self.ercode_file_path = os.path.join(self.program_root, "ERcode.txt")

        # ---- 配置 ----
        self.config = configparser.ConfigParser()
        self.last_open_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.last_export_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.read_settings()

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 后初始化 ----
        self.switch_tab(0)
        self.setup_stylesheet()
        self.load_dropped_uplr_file()

    # ===================== 配置文件读写 =====================
    def read_settings(self) -> None:
        default_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            if os.path.exists(self.settings_path):
                self.config.read(self.settings_path, encoding="utf-8")
                if "PathSettings" in self.config:
                    self.last_open_dir = self.config["PathSettings"].get("last_open_dir", default_desktop)
                    self.last_export_dir = self.config["PathSettings"].get("last_export_dir", default_desktop)
                    if not os.path.isdir(self.last_open_dir):
                        self.last_open_dir = default_desktop
                    if not os.path.isdir(self.last_export_dir):
                        self.last_export_dir = default_desktop
            else:
                self.last_open_dir = default_desktop
                self.last_export_dir = default_desktop
        except Exception:
            self.last_open_dir = default_desktop
            self.last_export_dir = default_desktop

    def write_settings(self) -> None:
        try:
            if "PathSettings" not in self.config:
                self.config["PathSettings"] = {}
            self.config["PathSettings"]["last_open_dir"] = self.last_open_dir
            self.config["PathSettings"]["last_export_dir"] = self.last_export_dir
            with open(self.settings_path, "w", encoding="utf-8") as f:
                self.config.write(f)
        except Exception:
            pass

    # ===================== 样式表 =====================
    def setup_stylesheet(self) -> None:
        self.setStyleSheet("""
            QWidget { background-color: #ffffff; color: #333333; }
            QMainWindow { background-color: #ffffff; }
            QTabWidget::pane { border: 1px solid #cccccc; }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333333;
                padding: 6px 16px;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background-color: #ffffff; }
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px 20px;
                font-size: 10pt;
            }
            QPushButton:hover { background-color: #e8f0fe; }
            QPushButton:pressed { background-color: #4a86e8; color: white; }
            QLineEdit {
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;
            }
            QComboBox {
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;
            }
            QCheckBox { color: #333333; spacing: 6px; }
            QTextEdit { color: #333333; }
            QFrame[frameShape="4"] { color: #cccccc; }
        """)

    # ===================== 构建完整界面 =====================
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(4)

        self.tabs = QTabWidget(self)
        self.tabs.setFont(QFont(STYLE_CFG["font_family"], STYLE_CFG["font_size"]))
        main_layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_basic_tab(), "基础")
        self.tabs.addTab(self._build_play_tab(), "文件")
        self.tabs.addTab(self._build_player_style_tab(), "播放器")
        self.tabs.addTab(self._build_lyric_tab(), "歌词")
        self.tabs.addTab(self._build_other_tab(), "其他")

    def _make_contributor_card(self, name: str, desc: str, url: str, avatar_url: str) -> QFrame:
        """构建 VitePress 风格的贡献者卡片"""
        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #4a86e8;
                background-color: #eef2ff;
            }
        """)
        card.setMinimumWidth(260)
        card.setMaximumWidth(380)

        card_inner = QHBoxLayout(card)
        card_inner.setContentsMargins(14, 12, 14, 12)
        card_inner.setSpacing(12)

        # 头像 —— 下载远程图片，失败则显示首字
        avatar = QLabel("", card)
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        local_path = self._download_avatar(avatar_url)
        if local_path:
            pixmap = QPixmap(local_path)
            avatar.setPixmap(pixmap.scaled(
                44, 44,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            ))
            avatar.setScaledContents(True)
            avatar.setStyleSheet("border-radius: 22px;")
        else:
            avatar.setText(name[0])
            avatar.setStyleSheet(
                "background-color: #4a86e8; color: white; "
                "border-radius: 22px; "
                "font-size: 18px; font-weight: bold;"
            )

        # 名字 + 描述
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        name_label = QLabel(name, card)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333333;")
        desc_label = QLabel(desc, card)
        desc_label.setStyleSheet("font-size: 11px; color: #888888;")
        desc_label.setWordWrap(True)
        text_col.addWidget(name_label)
        text_col.addWidget(desc_label)

        card_inner.addWidget(avatar)
        card_inner.addLayout(text_col, 1)
        card_inner.addStretch()

        # 点击跳转
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda _e: self.open_webpage(url)  # type: ignore[assignment]

        return card

    def _download_avatar(self, url: str) -> str | None:
        """下载头像到本地缓存，返回路径；失败返回 None"""
        cache_dir = os.path.join(os.path.expanduser("~"), ".ustplayer_avatars")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(
            cache_dir, hashlib.md5(url.encode()).hexdigest() + ".jpg"
        )
        if os.path.exists(cache_path):
            return cache_path
        try:
            urllib.request.urlretrieve(url, cache_path)
            return cache_path
        except Exception:
            return None

    def switch_tab(self, idx: int) -> None:
        """程序化切换当前标签页"""
        self.tabs.setCurrentIndex(idx)

    # ---------------------- 共享辅助函数 ----------------------
    @staticmethod
    def _h_sep(parent: QWidget) -> QFrame:
        f = QFrame(parent)
        f.setFrameShape(QFrame.Shape.HLine)
        f.setFrameShadow(QFrame.Shadow.Sunken)
        return f

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setFont(QFont(STYLE_CFG["font_family"], 11, QFont.Weight.Bold))
        return label

    # ===================== 标签页 0 —— 基础 =====================
    def _build_basic_tab(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 顶部按钮行
        btn_row = QHBoxLayout()
        self.btn_import_project = QPushButton("导入项目", self)
        self.btn_import_project.clicked.connect(self.on_open)
        self.btn_export_project = QPushButton("保存项目", self)
        self.btn_export_project.clicked.connect(self.on_export)
        btn_row.addWidget(self.btn_import_project)
        btn_row.addWidget(self.btn_export_project)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(self._h_sep(page))

        # 项目信息区域
        layout.addWidget(self._section_label("/ 关于项目"))

        grid = QGridLayout()
        grid.setSpacing(6)

        self.project_name_edit = QLineEdit(self)
        self.song_name_edit = QLineEdit(self)
        self.song_author_edit = QLineEdit(self)
        self.ust_author_edit = QLineEdit(self)

        grid.addWidget(QLabel("项目名：", self), 0, 0)
        grid.addWidget(self.project_name_edit, 0, 1)
        grid.addWidget(QLabel("曲名&曲师：", self), 1, 0)
        grid.addWidget(self.song_name_edit, 1, 1)
        grid.addWidget(QLabel("MIDI作者：", self), 2, 0)
        grid.addWidget(self.song_author_edit, 2, 1)
        grid.addWidget(QLabel("调音师：", self), 3, 0)
        grid.addWidget(self.ust_author_edit, 3, 1)

        layout.addLayout(grid)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(self._section_label("/ 基础信息"))

        # 复选框
        self.cb_show_bpm = QCheckBox("显示BPM", self)
        self.cb_show_bpm.setChecked(True)
        self.cb_show_play_time = QCheckBox("显示播放时间", self)
        self.cb_show_play_time.setChecked(True)
        self.cb_show_song_name = QCheckBox("显示曲目信息", self)
        self.cb_show_song_name.setChecked(True)
        self.cb_show_song_author = QCheckBox("显示MIDI作者", self)
        self.cb_show_song_author.setChecked(True)
        self.cb_show_ust_author = QCheckBox("显示调音师", self)
        self.cb_show_ust_author.setChecked(True)

        cb_grid = QGridLayout()
        cb_grid.addWidget(self.cb_show_bpm, 0, 0)
        cb_grid.addWidget(self.cb_show_play_time, 0, 1)
        cb_grid.addWidget(self.cb_show_song_name, 1, 0)
        cb_grid.addWidget(self.cb_show_song_author, 1, 1)
        cb_grid.addWidget(self.cb_show_ust_author, 2, 0)
        layout.addLayout(cb_grid)

        layout.addSpacing(8)

        # Play 按钮
        self.btn_play = QPushButton("播放 Play", self)
        self.btn_play.setStyleSheet("QPushButton { font-weight: bold; }")
        self.btn_play.clicked.connect(self.on_play_click)
        layout.addWidget(self.btn_play)

        layout.addStretch()
        return page

    # ===================== 标签页 1 —— 文件 =====================
    def _build_play_tab(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 第 0 行：ust 路径
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("ust:", self))
        self.ustx_path_edit = QLineEdit(self)
        row0.addWidget(self.ustx_path_edit)
        self.btn_select_ust = QPushButton("选择ust文件", self)
        self.btn_select_ust.clicked.connect(self.select_ustx_file)
        row0.addWidget(self.btn_select_ust)
        layout.addLayout(row0)

        # 音高线复选框
        self.cb_curve_show = QCheckBox("显示音高线变化", self)
        self.cb_curve_show.setChecked(False)
        layout.addWidget(self.cb_curve_show)

        # 第 1 行：编码选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("编码方式:", self))
        self.combo_encoding = QComboBox(self)
        self.combo_encoding.addItems(["UTF-8", "GBK", "Shift-JIS"])
        self.combo_encoding.setCurrentText("Shift-JIS")
        self.combo_encoding.currentTextChanged.connect(self.on_encoding_change)
        row1.addWidget(self.combo_encoding)
        row1.addStretch()
        layout.addLayout(row1)

        # 预览提示文本
        layout.addWidget(QLabel("编码检查 ⬇", self))

        # 预览文本框
        self.preview_text = QTextEdit(self)
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.preview_text)

        return page

    # ===================== 标签页 2 —— 播放器样式 =====================
    def _build_player_style_tab(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(self._section_label("/ 播放器样式"))

        # 颜色选择行
        self.bg_color_edit = QLineEdit("#000000", self)
        self.bg_color_edit.setMaximumWidth(100)
        self.note_color_edit = QLineEdit("#6c6c6c", self)
        self.note_color_edit.setMaximumWidth(100)
        self.lyric_color_edit = QLineEdit("#FFFFFF", self)
        self.lyric_color_edit.setMaximumWidth(100)
        self.lyric_text_color_edit = QLineEdit("#FFFFFF", self)
        self.lyric_text_color_edit.setMaximumWidth(100)
        self.other_text_color_edit = QLineEdit("#FFFFFF", self)
        self.other_text_color_edit.setMaximumWidth(100)

        color_entries = [
            ("背景色:", self.bg_color_edit),
            ("音名色:", self.note_color_edit),
            ("歌字色:", self.lyric_color_edit),
            ("歌词色:", self.lyric_text_color_edit),
            ("其他文字色:", self.other_text_color_edit),
        ]

        for label_text, edit in color_entries:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text, self))
            row.addWidget(edit)
            btn = QPushButton("更改", self)
            btn.clicked.connect(lambda _checked: self.choose_color(edit))  # type: ignore[arg-type]
            row.addWidget(btn)
            row.addStretch()
            layout.addLayout(row)

        # 歌词位置
        row_lp = QHBoxLayout()
        row_lp.addWidget(QLabel("歌词位置:", self))
        self.combo_lyric_pos = QComboBox(self)
        self.combo_lyric_pos.addItems(["上", "下"])
        self.combo_lyric_pos.setCurrentText("上")
        row_lp.addWidget(self.combo_lyric_pos)
        row_lp.addStretch()
        layout.addLayout(row_lp)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(self._section_label("/ 其他显示设置"))

        # 音高见占位符
        row_pp = QHBoxLayout()
        row_pp.addWidget(QLabel("音高见占位符:", self))
        self.combo_pitch_placeholder = QComboBox(self)
        self.combo_pitch_placeholder.addItems(["无", "-", "自定义文字"])
        self.combo_pitch_placeholder.setCurrentText("无")
        self.combo_pitch_placeholder.currentTextChanged.connect(self._on_pitch_placeholder_changed)
        row_pp.addWidget(self.combo_pitch_placeholder)
        self.pitch_custom_edit = QLineEdit(self)
        self.pitch_custom_edit.setMaximumWidth(160)
        self.pitch_custom_edit.hide()
        row_pp.addWidget(self.pitch_custom_edit)
        row_pp.addStretch()
        layout.addLayout(row_pp)

        # 静默时显示
        row_sd = QHBoxLayout()
        row_sd.addWidget(QLabel("静默时显示:", self))
        self.combo_silent_display = QComboBox(self)
        self.combo_silent_display.addItems(["R", "-", "自定义文字", "什么都不显示"])
        self.combo_silent_display.setCurrentText("R")
        self.combo_silent_display.currentTextChanged.connect(self._on_silent_display_changed)
        row_sd.addWidget(self.combo_silent_display)
        self.silent_custom_edit = QLineEdit(self)
        self.silent_custom_edit.setMaximumWidth(160)
        self.silent_custom_edit.hide()
        row_sd.addWidget(self.silent_custom_edit)
        row_sd.addStretch()
        layout.addLayout(row_sd)

        # 结束时显示
        row_ed = QHBoxLayout()
        row_ed.addWidget(QLabel("结束时显示:", self))
        self.combo_end_display = QComboBox(self)
        self.combo_end_display.addItems(["END", "-", "自定义文字", "什么都不显示"])
        self.combo_end_display.setCurrentText("END")
        self.combo_end_display.currentTextChanged.connect(self._on_end_display_changed)
        row_ed.addWidget(self.combo_end_display)
        self.end_custom_edit = QLineEdit(self)
        self.end_custom_edit.setMaximumWidth(160)
        self.end_custom_edit.hide()
        row_ed.addWidget(self.end_custom_edit)
        row_ed.addStretch()
        layout.addLayout(row_ed)

        layout.addStretch()
        return page

    # ===================== 标签页 3 —— 歌词 =====================
    def _build_lyric_tab(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(self._section_label("/ 歌词"))

        self.cb_show_lyric = QCheckBox("展示歌词", self)
        self.cb_show_lyric.setChecked(False)
        layout.addWidget(self.cb_show_lyric)

        layout.addWidget(self._h_sep(page))

        row = QHBoxLayout()
        row.addWidget(QLabel("歌词文件(.lrc):", self))
        self.lrc_path_edit = QLineEdit(self)
        row.addWidget(self.lrc_path_edit)
        btn_sel_lrc = QPushButton("选择文件", self)
        btn_sel_lrc.clicked.connect(self.select_lrc_file)
        row.addWidget(btn_sel_lrc)
        layout.addLayout(row)

        layout.addStretch()
        return page

    # ===================== 标签页 4 —— 其他 =====================
    def _build_other_tab(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(self._section_label("/ 关于软件"))

        copyright_label = QLabel(f"{SETTING['Name']}-v{SETTING['Version']} (c) 2026 SYEternalR", self)
        copyright_label.setStyleSheet("color: #0066CC; text-decoration: underline;")
        copyright_label.setCursor(Qt.CursorShape.PointingHandCursor)
        copyright_label.mousePressEvent = lambda _e: self.open_webpage("https://space.bilibili.com/661930756")  # type: ignore[assignment]
        layout.addWidget(copyright_label)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(self._section_label("/ 外部工具与纠错"))

        tool_row = QHBoxLayout()
        btn_uta = QPushButton("UtaFormatix", self)
        btn_uta.clicked.connect(lambda: self.open_webpage("https://utaformatix.tk/"))
        btn_ercode = QPushButton("ERcodes纠错", self)
        btn_ercode.clicked.connect(self.open_ercode_file)
        tool_row.addWidget(btn_uta)
        tool_row.addWidget(btn_ercode)
        tool_row.addStretch()
        layout.addLayout(tool_row)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(self._section_label("/ 协议与许可"))

        lic_row = QHBoxLayout()
        btn_terms = QPushButton("使用协议", self)
        btn_terms.clicked.connect(self.open_terms_file)
        btn_github = QPushButton("Github仓库", self)
        btn_github.clicked.connect(lambda: self.open_webpage("https://github.com/SYEternalR/ustPlayer"))
        lic_row.addWidget(btn_terms)
        lic_row.addWidget(btn_github)
        lic_row.addStretch()
        layout.addLayout(lic_row)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(self._section_label("/ 贡献者"))

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.addWidget(self._make_contributor_card(
            "SYEternalR",
            "ustPlayer 原作者",
            "https://space.bilibili.com/661930756",
            "https://i1.hdslb.com/bfs/face/7a9efa6db864a6aa522f42cca69c68ec679cdc50.jpg@128w_128h_1c_1s.webp",
        ))
        cards_row.addWidget(self._make_contributor_card(
            "星燃_X-starRelight",
            "贡献者 | GitHub",
            "https://github.com/X-starRelight",
            "https://avatars.githubusercontent.com/u/161218739?v=4",
        ))
        cards_row.addStretch()
        layout.addLayout(cards_row)

        layout.addWidget(self._h_sep(page))
        layout.addWidget(QLabel("你知道吗：alpha版本在提交至托管时曾被错误地命名为ustPlyaer。orz", self))

        layout.addStretch()
        return page

    # ===================== 拖拽 .uplr 文件自动加载 =====================
    def load_dropped_uplr_file(self) -> None:
        if len(sys.argv) > 1:
            path = sys.argv[1].strip()
            if path and os.path.exists(path) and path.lower().endswith(".uplr"):
                try:
                    self.import_uplr_file(path)
                    self.last_open_dir = os.path.dirname(path)
                    self.write_settings()
                    QMessageBox.information(self, "成功", f"已成功打开并加载工程：\n{path}")  # type: ignore[call-arg]
                except Exception as exc:
                    QMessageBox.critical(self, "ERcode006", f"加载工程文件失败：\n{exc}")

    # ===================== UPLR 导入/导出 =====================
    def outport_uplr_file(self, output_file: str) -> None:
        try:
            with open(output_file, "w", encoding="utf-8") as uplr:
                uplr.write("#Encoding\n")
                uplr.write(f"encoding={self.combo_encoding.currentText()}\n\n")

                uplr.write("#BasicSettings\n")
                uplr.write(f"project_name={self.project_name_edit.text()}\n")
                uplr.write(f"ust_path={self.ustx_path_edit.text()}\n")
                uplr.write(f"song_name={self.song_name_edit.text()}\n")
                uplr.write(f"song_author={self.song_author_edit.text()}\n")
                uplr.write(f"ust_author={self.ust_author_edit.text()}\n\n")

                uplr.write("#DisplaySettings\n")
                uplr.write(f"show_bpm={1 if self.cb_show_bpm.isChecked() else 0}\n")
                uplr.write(f"show_play_time={1 if self.cb_show_play_time.isChecked() else 0}\n")
                uplr.write(f"show_song_name={1 if self.cb_show_song_name.isChecked() else 0}\n")
                uplr.write(f"show_song_author={1 if self.cb_show_song_author.isChecked() else 0}\n")
                uplr.write(f"show_ust_author={1 if self.cb_show_ust_author.isChecked() else 0}\n")
                uplr.write(f"show_lyric={1 if self.cb_show_lyric.isChecked() else 0}\n\n")

                uplr.write("#ColorSettings\n")
                uplr.write(f"bg_color={self.bg_color_edit.text()}\n")
                uplr.write(f"note_color={self.note_color_edit.text()}\n")
                uplr.write(f"lyric_color={self.lyric_color_edit.text()}\n")
                uplr.write(f"lyric_text_color={self.lyric_text_color_edit.text()}\n")
                uplr.write(f"other_text_color={self.other_text_color_edit.text()}\n\n")

                uplr.write("#LyricAndExtra\n")
                uplr.write(f"lyric_pos={self.combo_lyric_pos.currentText()}\n")
                uplr.write(f"lrc_path={self.lrc_path_edit.text()}\n")
                uplr.write(f"silent_display={self.combo_silent_display.currentText()}\n")
                uplr.write(f"silent_custom_text={self.silent_custom_edit.text()}\n")
                uplr.write(f"end_display={self.combo_end_display.currentText()}\n")
                uplr.write(f"end_custom_text={self.end_custom_edit.text()}\n")
                uplr.write(f"curve_show={1 if self.cb_curve_show.isChecked() else 0}\n")
                uplr.write(f"pitch_placeholder={self.combo_pitch_placeholder.currentText()}\n")
                uplr.write(f"pitch_custom_text={self.pitch_custom_edit.text()}\n")
            print(f"配置文件已成功导出到：{output_file}")
        except Exception as exc:
            print(f"导出配置文件失败：{exc}")

    def import_uplr_file(self, input_file: str) -> None:
        with open(input_file, "r", encoding="utf-8") as uplr:
            for line in uplr:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) != 2:
                    continue
                key, value = parts[0].strip(), parts[1].strip()
                if key == "project_name":
                    self.project_name_edit.setText(value)
                elif key == "ust_path":
                    self.ustx_path_edit.setText(value)
                elif key == "song_name":
                    self.song_name_edit.setText(value)
                elif key == "song_author":
                    self.song_author_edit.setText(value)
                elif key == "ust_author":
                    self.ust_author_edit.setText(value)
                elif key == "show_bpm":
                    self.cb_show_bpm.setChecked(value == "1")
                elif key == "show_play_time":
                    self.cb_show_play_time.setChecked(value == "1")
                elif key == "show_song_name":
                    self.cb_show_song_name.setChecked(value == "1")
                elif key == "show_song_author":
                    self.cb_show_song_author.setChecked(value == "1")
                elif key == "show_ust_author":
                    self.cb_show_ust_author.setChecked(value == "1")
                elif key == "encoding":
                    self.combo_encoding.setCurrentText(value)
                elif key == "bg_color":
                    self.bg_color_edit.setText(value)
                elif key == "note_color":
                    self.note_color_edit.setText(value)
                elif key == "lyric_color":
                    self.lyric_color_edit.setText(value)
                elif key == "lyric_text_color":
                    self.lyric_text_color_edit.setText(value)
                elif key == "other_text_color":
                    self.other_text_color_edit.setText(value)
                elif key == "lyric_pos":
                    self.combo_lyric_pos.setCurrentText(value)
                elif key == "show_lyric":
                    self.cb_show_lyric.setChecked(value == "1")
                elif key == "lrc_path":
                    self.lrc_path_edit.setText(value)
                elif key == "silent_display":
                    self.combo_silent_display.setCurrentText(value)
                elif key == "silent_custom_text":
                    self.silent_custom_edit.setText(value)
                elif key == "end_display":
                    self.combo_end_display.setCurrentText(value)
                elif key == "end_custom_text":
                    self.end_custom_edit.setText(value)
                elif key == "curve_show":
                    self.cb_curve_show.setChecked(value == "1")
                elif key == "pitch_placeholder":
                    self.combo_pitch_placeholder.setCurrentText(value)
                elif key == "pitch_custom_text":
                    self.pitch_custom_edit.setText(value)

    # ===================== 文件对话框 =====================
    def on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开工程文件", self.last_open_dir,
            "ustPlayer工程文件 (*.uplr);;所有文件 (*)"
        )
        if not path:
            return
        try:
            self.import_uplr_file(path)
            QMessageBox.information(self, "成功", f"已成功打开并加载工程：\n{path}")  # type: ignore[call-arg]
            self.last_open_dir = os.path.dirname(path)
            self.write_settings()
        except Exception as exc:
            QMessageBox.critical(self, "ERcode007", f"加载文件失败：\n{exc}")

    def on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "导出你的工程文件",
            os.path.join(self.last_export_dir, self.project_name_edit.text()),
            "ustPlayer工程文件 (*.uplr);;所有文件 (*)"
        )
        if not path:
            return
        self.outport_uplr_file(path)
        QMessageBox.information(self, "成功", f"工程已导出到：\n{path}")  # type: ignore[call-arg]
        self.last_export_dir = os.path.dirname(path)
        self.write_settings()

    def select_ustx_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择ust文件", "",
            "UST文件 (*.ust);;所有文件 (*)"
        )
        if path:
            self.ustx_path_edit.setText(path)
            self.preview_ust_content(path)

    def select_lrc_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择LRC歌词文件", "",
            "LRC歌词文件 (*.lrc);;所有文件 (*)"
        )
        if path:
            self.lrc_path_edit.setText(path)

    # ===================== 颜色选择器 =====================
    def choose_color(self, color_edit: QLineEdit) -> None:
        current = QColor(color_edit.text())
        color = QColorDialog.getColor(current, self, "选择颜色")
        if color.isValid():
            color_edit.setText(color.name().upper())

    # ===================== UST 文件预览 =====================
    def preview_ust_content(self, file_path: str) -> None:
        try:
            encoding = self.combo_encoding.currentText()
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            self.preview_text.setPlainText(content)
        except Exception as exc:
            QMessageBox.critical(self, "ERcode002", f"读取文件失败：{exc}")

    def on_encoding_change(self, _text: str) -> None:
        path = self.ustx_path_edit.text().strip()
        if path and os.path.exists(path):
            self.preview_ust_content(path)

    # ===================== 下拉框 → 自定义输入框显示/隐藏 =====================
    def _on_pitch_placeholder_changed(self, text: str) -> None:
        self.pitch_custom_edit.setVisible(text == "自定义文字")

    def _on_silent_display_changed(self, text: str) -> None:
        self.silent_custom_edit.setVisible(text == "自定义文字")

    def _on_end_display_changed(self, text: str) -> None:
        self.end_custom_edit.setVisible(text == "自定义文字")

    # ===================== 网页/文件跳转 =====================
    def open_webpage(self, url: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:
            QMessageBox.critical(self, "ERcode003", f"打开网页失败：{exc}")

    def open_ercode_file(self) -> None:
        try:
            if not os.path.exists(self.ercode_file_path):
                return
            subprocess.Popen(
                ["notepad.exe", self.ercode_file_path],
                shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
            )
        except Exception as exc:
            QMessageBox.critical(self, "ERcode008", f"打开ERcode.txt失败：{exc}")

    def open_terms_file(self) -> None:
        try:
            if not os.path.exists(self.terms_file_path):
                return
            subprocess.Popen(
                ["notepad.exe", self.terms_file_path],
                shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
            )
        except Exception as exc:
            QMessageBox.critical(self, "ERcode009", f"打开Terms.txt失败：{exc}")

    # ===================== 播放 =====================
    def _safe_display_play(self, ust_info: UstInfo) -> None:
        try:
            import player
            self._player_window = player.display(ust_info)
        except Exception as exc:
            QMessageBox.critical(self, "ERcode005", f"播放器运行失败：{exc}")

    def on_play_click(self) -> None:
        path = self.ustx_path_edit.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.critical(self, "ERcode001", "请选择有效的UST文件！")
            return

        try:
            encoding = self.combo_encoding.currentText()
            core_ust_info: CoreUstInfo = ur.get_ust_info(path, encoding)

            ust_info: UstInfo = UstInfo(
                version=core_ust_info.get("version", "未知版本"),
                tempo=core_ust_info.get("tempo", 120.0),
                tracks=core_ust_info.get("tracks", 1),
                notes=core_ust_info.get("notes", []),
                show_config=ShowConfig(
                    bpm=self.cb_show_bpm.isChecked(),
                    play_time=self.cb_show_play_time.isChecked(),
                    song_name=self.cb_show_song_name.isChecked(),
                    song_author=self.cb_show_song_author.isChecked(),
                    ust_author=self.cb_show_ust_author.isChecked(),
                    lyric=self.cb_show_lyric.isChecked(),
                    curve_show=self.cb_curve_show.isChecked(),
                ),
                project_info=ProjectInfo(
                    project_name=self.project_name_edit.text(),
                    song_name=self.song_name_edit.text(),
                    song_author=self.song_author_edit.text(),
                    ust_author=self.ust_author_edit.text(),
                ),
                encoding=encoding,
                player_style=PlayerStyle(
                    bg_color=self.bg_color_edit.text(),
                    note_color=self.note_color_edit.text(),
                    lyric_color=self.lyric_color_edit.text(),
                    lyric_text_color=self.lyric_text_color_edit.text(),
                    other_text_color=self.other_text_color_edit.text(),
                    lyric_pos=self.combo_lyric_pos.currentText(),
                    fullscreen=True,
                    lrc_path=self.lrc_path_edit.text(),
                    lrc_gray_level=180,
                    lrc_font_scale=0.03,
                    silent_display=self.combo_silent_display.currentText() if self.combo_silent_display.currentText() != "什么都不显示" else "",
                    silent_custom_text=self.silent_custom_edit.text(),
                    end_display=self.combo_end_display.currentText() if self.combo_end_display.currentText() != "什么都不显示" else "",
                    end_custom_text=self.end_custom_edit.text(),
                    pitch_placeholder=self.combo_pitch_placeholder.currentText(),
                    pitch_custom_text=self.pitch_custom_edit.text(),
                ),
            )

            QMessageBox.information(self, "WaitingForUser", "按下确认后将启动播放器，鼠标单击后按ESC键退出全屏")  # type: ignore[call-arg]

            # self._safe_display_play(ust_info)
            play_ust(ust_info, self, self._safe_display_play)

        except UnicodeDecodeError:
            QMessageBox.critical(self, "ERcode004", "解析UST文件失败：使用了错误的编码，请切换编码后重试")
        except Exception as exc:
            QMessageBox.critical(self, "ERcode999", f"播放准备失败：{exc}")


    # ===================== 程序入口 =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = UstPlayerMain()
    window.show()
    sys.exit(app.exec())
