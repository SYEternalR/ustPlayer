# player.py  ——  PySide6 全屏 UST 播放器
import time
import re
from datetime import timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QPen,
    QShowEvent, QResizeEvent, QPaintEvent, QKeyEvent,
)
from PySide6.QtWidgets import QApplication, QWidget

from ust_types import NoteInfo, UstInfo
from typing import cast


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ===================== 工具函数 =====================
def _validate_hex_color(hex_color: str) -> str:
    if re.match(r'^#([0-9A-Fa-f]{6})$', str(hex_color)):
        return hex_color.strip()
    return "#FFFFFF"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    try:
        h = hex_color.lstrip('#')
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (255, 255, 255)


def _transparent_color(r: int, g: int, b: int, alpha: int) -> QColor:
    a = max(0, min(255, alpha))
    return QColor(
        int(r * a / 255),
        int(g * a / 255),
        int(b * a / 255),
    )


def _format_play_time(seconds: float) -> str:
    try:
        ms = int((seconds - int(seconds)) * 100)
        td = timedelta(seconds=int(seconds))
        return f"{td.seconds // 60:02d}:{td.seconds % 60:02d}:{ms:02d}"
    except Exception:
        return "00:00:00"


# ===================== 播放器窗口 =====================
class NoteLyricDisplay(QWidget):
    def __init__(self, ust_info: UstInfo) -> None:
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("ustPlayerform")

        ps = ust_info["player_style"]
        self.do_fullscreen: bool = ps.get("fullscreen", True)

        # ---- 背景色 ----
        self.bg_color = QColor(_validate_hex_color(ps.get("bg_color", "#000000")))

        # ---- 核心数据 ----
        self.notes: list[NoteInfo] = ust_info.get("notes", [])
        self.tempo: float = ust_info.get("tempo", 120.0)
        self.last_valid_lyric: str = ""

        # ---- 计时相关 ----
        self.start_real_time = time.time()
        self.tick_per_second: float = (self.tempo * 480) / 60.0
        self.total_tick: int = sum(max(n.get("length", 480), 1) for n in self.notes)

        # ---- 显示开关 ----
        sc = ust_info["show_config"]
        self.curve_show: bool = sc.get("curve_show", False)
        self.show_lyric: bool = sc.get("lyric", True)
        self.show_bpm: bool = sc.get("bpm", True)
        self.show_play_time: bool = sc.get("play_time", True)
        self.show_song_name: bool = sc.get("song_name", True)
        self.show_song_author: bool = sc.get("song_author", True)
        self.show_ust_author: bool = sc.get("ust_author", True)

        # ---- LRC ----
        self.lrc_path: str = ps.get("lrc_path", "")
        self.lrc_lines: list[tuple[float, str]] = []
        self.current_lrc_idx: int = -1
        self.lyric_pos: str = ps.get("lyric_pos", "上")

        # ---- 项目信息 ----
        pi = ust_info.get("project_info", {})
        self.song_name: str = pi.get("song_name", "")
        self.song_author: str = pi.get("song_author", "")
        self.ust_author: str = pi.get("ust_author", "")

        # ---- 静默 / 结束显示 ----
        self.silent_display: str = ps.get("silent_display", "R")
        self.silent_custom_text: str = ps.get("silent_custom_text", "")
        self.end_display: str = ps.get("end_display", "END")
        self.end_custom_text: str = ps.get("end_custom_text", "")

        # ---- 音高见占位符 ----
        self.pitch_placeholder: str = ps.get("pitch_placeholder", "无")
        self.pitch_custom_text: str = ps.get("pitch_custom_text", "")

        # ---- 预计算音符 tick 区间 ----
        self.note_tick_ranges: list[tuple[int, int, NoteInfo]] = self._calc_note_tick_ranges()

        # ---- 解析 LRC ----
        if self.show_lyric and self.lrc_path:
            self._parse_lrc_file()

        # ---- 显示颜色 ----
        self.ust_lyric_color = QColor(*_hex_to_rgb(
            _validate_hex_color(ps.get("lyric_color", "#FFFFFF"))
        ))
        self.note_color = QColor(*_hex_to_rgb(
            _validate_hex_color(ps.get("note_color", "#C3C3C3"))
        ))
        self.note_alpha: int = 225
        self.small_font_color = QColor(*_hex_to_rgb(
            _validate_hex_color(ps.get("other_text_color", "#FFFFFF"))
        ))
        self.lrc_text_color = QColor(self.small_font_color)

        # ---- 字体（具体大小在 resizeEvent 中调整）----
        self.note_font = QFont("Microsoft YaHei", 100, QFont.Weight.Bold)
        self.lyric_font = QFont("Microsoft YaHei", 30, QFont.Weight.Normal)
        self.ust_lyric_font = QFont("Microsoft YaHei", 140, QFont.Weight.Bold)
        self.small_font = QFont("Microsoft YaHei", 14)
        self.copyright_font = QFont("Microsoft YaHei", 12)

        # ---- 音高线配置 ----
        self.note_line_width: int = 5
        self.length_to_pixel: float = 1.0

        # ---- 当前显示状态 ----
        self.ust_lyric: str = ""
        self.note_name: str = ""
        self.current_note: dict[str, object] = {}
        self.play_elapsed: float = 0.0

        # ---- 计时器 ----
        self._timer = QTimer(self)
        self._timer.setInterval(5)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start()

    # ===================== 字体大小（窗口几何确定后调用）=====================
    def _setup_fonts(self, w: int, h: int) -> None:
        self.note_font_size = max(int(h * 2 / 3 * 0.4), 50)
        self.lyric_font_size = max(int(h * 0.03), 10)
        self.ust_lyric_font_size = max(int(h * 2 / 3 * 0.2), 80)
        self.note_font = QFont("Microsoft YaHei", self.note_font_size, QFont.Weight.Bold)
        self.lyric_font = QFont("Microsoft YaHei", self.lyric_font_size, QFont.Weight.Normal)
        self.ust_lyric_font = QFont("Microsoft YaHei", self.ust_lyric_font_size, QFont.Weight.Bold)
        self.note_line_offset = self.note_font_size // 4

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        w = self.width()
        h = self.height()
        if w > 0 and h > 0:
            self._setup_fonts(w, h)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        if w > 0 and h > 0:
            self._setup_fonts(w, h)

    # ===================== LRC 解析器 =====================
    def _parse_lrc_file(self) -> None:
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312", "shift-jis"]
        content = ""
        try:
            for enc in encodings:
                try:
                    with open(self.lrc_path, "r", encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, OSError):
                    continue
            if not content:
                return
            fragments = re.findall(r'\[(\d{1,2}):(\d{1,2})\.(\d{2,3})\]([^\[]*)', content)
            for frag in fragments:
                try:
                    minutes = int(frag[0])
                    seconds = int(frag[1])
                    milliseconds = int(frag[2])
                    if len(frag[2]) == 2:
                        milliseconds *= 10
                    ts = minutes * 60 + seconds + milliseconds / 1000.0
                    lyric = frag[3].strip()
                    if lyric:
                        self.lrc_lines.append((ts, lyric))
                except (ValueError, IndexError):
                    continue
            self.lrc_lines.sort(key=lambda x: x[0])
        except Exception:
            self.lrc_lines = []

    # ===================== Tick 区间预计算 =====================
    def _calc_note_tick_ranges(self) -> list[tuple[int, int, NoteInfo]]:
        result: list[tuple[int, int, NoteInfo]] = []
        current_tick = 0
        for note in self.notes:
            length = max(note.get("length", 480), 1)
            result.append((current_tick, current_tick + length, note))
            current_tick += length
        return result

    # ===================== 计时器回调 =====================
    def _on_timer(self) -> None:
        try:
            play_elapsed = time.time() - self.start_real_time
            current_total_tick = play_elapsed * self.tick_per_second

            if current_total_tick >= self.total_tick:
                self.ust_lyric = self._get_end_text()
                self.note_name = ""
                self.current_note = {}
                self.play_elapsed = play_elapsed
                self._update_lrc_index(play_elapsed)
                self.update()
                QTimer.singleShot(1000, self._close)
                return

            found: NoteInfo | None = None
            for tick_start, tick_end, note in self.note_tick_ranges:
                if tick_start <= current_total_tick < tick_end:
                    found = note
                    break

            self.play_elapsed = play_elapsed
            self._update_lrc_index(play_elapsed)

            if found is not None:
                self.current_note = found  # type: ignore[assignment]
                raw_lyric: str = found.get("lyric", "")
                raw_note_num: int = found.get("note_num", 0)

                if raw_lyric == "R":
                    self.ust_lyric = self._get_silent_text()
                    self.note_name = ""
                elif raw_lyric == "-":
                    self.ust_lyric = self.last_valid_lyric if self.last_valid_lyric else self._get_silent_text()
                    self.note_name = self._get_pitch_placeholder_text(raw_note_num)
                else:
                    self.ust_lyric = raw_lyric
                    self.last_valid_lyric = raw_lyric
                    self.note_name = self._get_pitch_placeholder_text(raw_note_num)
            else:
                self.ust_lyric = ""
                self.note_name = ""

            self.update()
        except Exception:
            pass

    # ===================== LRC 索引 =====================
    def _update_lrc_index(self, play_elapsed: float) -> None:
        if not self.lrc_lines:
            return
        try:
            new_idx = -1
            for i in range(len(self.lrc_lines)):
                if self.lrc_lines[i][0] <= play_elapsed:
                    new_idx = i
                else:
                    break
            if new_idx != self.current_lrc_idx:
                self.current_lrc_idx = new_idx
        except Exception:
            self.current_lrc_idx = -1

    def _get_current_lyric(self) -> str:
        try:
            if 0 <= self.current_lrc_idx < len(self.lrc_lines):
                return self.lrc_lines[self.current_lrc_idx][1]
        except Exception:
            pass
        return ""

    # ===================== 文本辅助 =====================
    def _get_silent_text(self) -> str:
        try:
            if self.silent_display == "R":
                return "R"
            if self.silent_display == "-":
                return "-"
            if self.silent_display == "自定义文字":
                return self.silent_custom_text
        except Exception:
            pass
        return ""

    def _get_end_text(self) -> str:
        try:
            if self.end_display == "END":
                return "END"
            if self.end_display == "-":
                return "-"
            if self.end_display == "自定义文字":
                return self.end_custom_text
        except Exception:
            pass
        return ""

    def _get_pitch_placeholder_text(self, raw_note_num: int) -> str:
        try:
            ori = self._midi_to_note_name(raw_note_num)
            pure = re.fullmatch(r'^([A-G])(\d+)$', ori)
            sharp = re.fullmatch(r'^([A-G]#)(\d+)$', ori)
            if sharp:
                return ori
            if pure:
                note = pure.group(1)
                num = pure.group(2)
                if self.pitch_placeholder == "无":
                    return f"{note}{num}"
                if self.pitch_placeholder == "-":
                    return f"{note}-{num}"
                if self.pitch_placeholder == "自定义文字":
                    suffix = self.pitch_custom_text.strip()
                    return f"{note}({suffix}){num}" if suffix else f"{note}{num}"
            return ori
        except Exception:
            return self._midi_to_note_name(raw_note_num)

    def _midi_to_note_name(self, midi_num: int) -> str:
        try:
            octave = (midi_num // 12) - 1
            return f"{_NOTE_NAMES[midi_num % 12]}{octave}"
        except Exception:
            return str(midi_num)

    # ===================== 绘制 =====================
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        # 背景
        painter.fillRect(self.rect(), self.bg_color)

        # ---- 音名 ----
        if self.note_name:
            nc = QColor(
                int(self.note_color.red() * self.note_alpha / 255),
                int(self.note_color.green() * self.note_alpha / 255),
                int(self.note_color.blue() * self.note_alpha / 255),
            )
            painter.setPen(nc)
            painter.setFont(self.note_font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.note_name)

        # ---- 音高线 ----
        if self.curve_show and self.current_note:
            pb_data_raw = cast(list[int], self.current_note.get("pitch_bend"))
            note_length_raw = self.current_note.get("length", 0)
            if len(pb_data_raw) >= 2 and isinstance(note_length_raw, int) and note_length_raw > 0:
                note_length: int = note_length_raw
                curve_total_width = int(note_length * self.length_to_pixel)
                start_x = cx - curve_total_width // 2
                base_y = cy
                points: list[tuple[float, float]] = []
                pb_count = len(pb_data_raw)
                for i in range(pb_count):
                    xx = start_x + (i / (pb_count - 1)) * curve_total_width
                    yy_offset = (pb_data_raw[i] / 100.0) * (h * 0.09)
                    yy = base_y - yy_offset
                    safe_top = 100.0
                    safe_bottom = float(h - 100)
                    if safe_top <= yy <= safe_bottom:
                        final_y = yy
                    elif yy < safe_top:
                        exceed = safe_top - yy
                        scale = max(0.3, 1.0 - (exceed / h * 2))
                        final_y = safe_top - (exceed * scale)
                    else:
                        exceed = yy - safe_bottom
                        scale = max(0.3, 1.0 - (exceed / h * 2))
                        final_y = safe_bottom + (exceed * scale)
                    final_y = max(50.0, min(final_y, h - 50.0))
                    points.append((xx, final_y))

                path = QPainterPath()
                path.moveTo(points[0][0], points[0][1])
                for pt in points[1:]:
                    path.lineTo(pt[0], pt[1])
                pen = QPen(self.small_font_color, self.note_line_width)
                painter.setPen(pen)
                painter.drawPath(path)

        # ---- 歌字 ----
        if self.ust_lyric:
            painter.setPen(self.ust_lyric_color)
            painter.setFont(self.ust_lyric_font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.ust_lyric)

        # ---- 播放时间 ----
        if self.show_play_time:
            painter.setPen(self.small_font_color)
            painter.setFont(self.small_font)
            painter.drawText(20, h - 20, _format_play_time(self.play_elapsed))

        # ---- LRC 歌词 ----
        if self.show_lyric and self.lrc_lines:
            current_lyric = self._get_current_lyric()
            if current_lyric:
                painter.setPen(self.lrc_text_color)
                painter.setFont(self.lyric_font)
                ly = int(h * 0.3) if self.lyric_pos == "上" else int(h * 0.7)
                text_rect = self.rect()
                text_rect.setY(ly - 40)
                text_rect.setHeight(80)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, current_lyric)

        # ---- 静态信息（左上角）----
        y_offset = 20
        painter.setPen(self.small_font_color)
        if self.show_song_name and self.song_name:
            font_b = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
            painter.setFont(font_b)
            painter.drawText(20, y_offset, self.song_name)
            y_offset += 27
        if self.show_song_author and self.song_author:
            painter.setFont(self.small_font)
            painter.drawText(20, y_offset, self.song_author)
            y_offset += 25
        if self.show_ust_author and self.ust_author:
            painter.setFont(self.small_font)
            painter.drawText(20, y_offset, self.ust_author)

        # ---- BPM（右上角）----
        if self.show_bpm:
            painter.setPen(self.small_font_color)
            painter.setFont(self.small_font)
            fm = painter.fontMetrics()
            text = f"BPM={self.tempo}"
            tw = fm.horizontalAdvance(text)
            painter.drawText(w - 20 - tw, 20, text)

        # ---- 版权信息（底部居中）----
        copyright_color = _transparent_color(195, 195, 195, 100)
        painter.setPen(copyright_color)
        painter.setFont(self.copyright_font)
        painter.drawText(self.rect().adjusted(0, 0, 0, -20), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                         "ustPlayer-v26b11 © 2026 SYEternalR")

        painter.end()

    # ===================== 关闭 =====================
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        super().keyPressEvent(event)

    def _close(self) -> None:
        self._timer.stop()
        self.close()


# ===================== 外部入口 =====================
def display(ust_info: UstInfo) -> NoteLyricDisplay:
    """由 main_window 调用，将播放器作为新的顶层窗口显示。
    main_window 的 QApplication 事件循环会同时管理两个窗口。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
    w = NoteLyricDisplay(ust_info)
    w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    if w.do_fullscreen:
        w.show()
        w.showFullScreen()
    else:
        w.show()
    return w
