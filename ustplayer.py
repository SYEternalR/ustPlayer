# ustplayer.py
import tkinter as tk
import time
import re
from datetime import timedelta
import keyboard
from time import sleep

class NoteLyricDisplay:
    def __init__(self, root, ust_info):
        self.record = ust_info["show_config"].get("record", True) #录屏参数

        if self.record == True:
            keyboard.press_and_release('F2')
        
        self.root = root
        self.root.title("ustPlayerform")

        # 基础配置
        self.fullscreen = ust_info["player_style"].get("fullscreen", True)
        if self.fullscreen:
            self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)

        # 背景色（合法性校验）
        self.bg_color = self.validate_hex_color(ust_info["player_style"].get("bg_color", "#000000"))
        self.root.config(bg=self.bg_color)

        # 画布配置
        self.canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 仅ESC退出
        self.root.bind("<Escape>", self.close)

        # 核心数据
        self.notes = ust_info.get("notes", [])
        self.tempo = ust_info.get("tempo", 120)
        self.last_valid_lyric = ""
        
        # ========== 核心重构：基于绝对时间的播放基准，无累计误差 ==========
        self.start_real_time = time.time()  # 播放启动绝对时间，永久不变
        self.play_timer_id = None
        # UST时间轴核心参数
        self.tick_per_second = (self.tempo * 480) / 60  # 每秒tick数，固定值
        self.total_tick = sum(max(n.get("length", 480), 1) for n in self.notes)  # 总tick数

        # 是否显示音高线变化
        self.curve_show = ust_info["show_config"].get("curve_show", False)
        
        # LRC配置
        self.show_lyric = ust_info["show_config"].get("lyric", True)
        self.lrc_path = ust_info["player_style"].get("lrc_path", "")
        self.lrc_lines = []
        self.current_lrc_idx = -1
        self.lyric_pos = ust_info["player_style"].get("lyric_pos", "上")
        self.lrc_gray_level = 180
        self.lrc_font_scale = 0.03

        # 解析LRC
        if self.show_lyric and self.lrc_path:
            self.parse_lrc_file()

        # MIDI转音名
        self.note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # 屏幕尺寸
        try:
            self.w = self.root.winfo_screenwidth() or 1920
            self.h = self.root.winfo_screenheight() or 1080
        except:
            self.w = 1920
            self.h = 1080

        # 字体配置
        self.note_font_size = max(int(self.h * 2/3 * 0.4), 50)
        self.lyric_font_size = max(int(self.h * self.lrc_font_scale), 10)
        self.ust_lyric_font_size = max(int(self.h * 2/3 * 0.2), 80)
        self.note_font = ("等线", self.note_font_size, "bold")
        self.lyric_font = ("等线", self.lyric_font_size, "normal")
        self.ust_lyric_font = ("等线", self.ust_lyric_font_size, "bold")
        
        # 小字体配置
        self.small_font = ("等线", 14)
        self.small_font_color = self.validate_hex_color(ust_info["player_style"].get("other_text_color", "#FFFFFF"))

        # 版权配置
        self.copyright_font = ("等线", 12)
        self.copyright_alpha = 100

        # 音名透明度
        self.note_alpha = 225

        # 颜色配置
        self.ust_lyric_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("lyric_color", "#FFFFFF")))
        self.note_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("note_color", "#C3C3C3")))
        # ===== 修正：歌词颜色使用其他文字颜色 =====
        self.lrc_text_color = self.hex_to_rgb(self.small_font_color)  # 替换为其他文字颜色

        # 显示配置
        self.show_bpm = ust_info["show_config"].get("bpm", True)
        self.show_play_time = ust_info["show_config"].get("play_time", True)
        self.show_song_name = ust_info["show_config"].get("song_name", True)
        self.show_song_author = ust_info["show_config"].get("song_author", True)
        self.show_ust_author = ust_info["show_config"].get("ust_author", True)

        # 项目信息
        self.project_info = ust_info.get("project_info", {})
        self.song_name = self.project_info.get("song_name", "")
        self.song_author = self.project_info.get("song_author", "")
        self.ust_author = self.project_info.get("ust_author", "")

        # 静默/结束显示
        self.silent_display = ust_info["player_style"].get("silent_display", "R")
        self.silent_custom_text = ust_info["player_style"].get("silent_custom_text", "")
        self.end_display = ust_info["player_style"].get("end_display", "END")
        self.end_custom_text = ust_info["player_style"].get("end_custom_text", "")

        # ===== 新增：音高见占位符配置 =====
        self.pitch_placeholder = ust_info["player_style"].get("pitch_placeholder", "无")
        self.pitch_custom_text = ust_info["player_style"].get("pitch_custom_text", "")

        # 音高线配置
        self.note_line_offset = self.note_font_size // 4
        self.note_line_width = 5
        self.length_to_pixel = 1

        # 预计算每个音符的累计tick区间，用于快速匹配
        self.note_tick_ranges = self._calc_note_tick_ranges()
        # 启动主计时器：5ms高精度，直接计算当前音符位置
        self.start_main_timer()

    # ========== 工具方法 ==========
    def validate_hex_color(self, hex_color):
        pattern = r'^#([0-9A-Fa-f]{6})$'
        if re.match(pattern, str(hex_color)):
            return hex_color.strip()
        return "#FFFFFF"

    def hex_to_rgb(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (255, 255, 255)

    def parse_lrc_file(self):
        try:
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'shift-jis']
            content = ""
            for enc in encodings:
                try:
                    with open(self.lrc_path, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except:
                    continue
            if not content:
                return

            lrc_fragment_pattern = r'\[(\d{1,2}):(\d{1,2})\.(\d{2,3})\]([^\[]*)'
            fragments = re.findall(lrc_fragment_pattern, content)

            for frag in fragments:
                try:
                    minutes = int(frag[0])
                    seconds = int(frag[1])
                    milliseconds = int(frag[2])
                    if len(frag[2]) == 2:
                        milliseconds *= 10
                    timestamp_sec = minutes * 60 + seconds + milliseconds / 1000
                    lyric_frag = frag[3].strip()
                    if lyric_frag:
                        self.lrc_lines.append([timestamp_sec, lyric_frag])
                except:
                    continue

            self.lrc_lines.sort(key=lambda x: x[0])
        except:
            self.lrc_lines = []

    # ========== 核心预计算：每个音符的累计tick区间 ==========
    def _calc_note_tick_ranges(self):
        """预计算每个音符的[起始tick, 结束tick]，避免实时遍历，提升效率"""
        note_ranges = []
        current_tick = 0
        for note in self.notes:
            length = max(note.get("length", 480), 1)
            note_ranges.append([current_tick, current_tick + length, note])
            current_tick += length
        return note_ranges

    # ========== 主计时器：直接计算当前应播放的音符 ==========
    def start_main_timer(self):
        def update():
            try:
                # 1. 计算当前真实播放的累计tick（无任何累计误差）
                current_real_time = time.time()
                play_elapsed = current_real_time - self.start_real_time
                current_total_tick = play_elapsed * self.tick_per_second

                # 2. 播放完成判断
                def close_window_and_press_f2(self):
                    # 检查是否需要录制（self.record为True时按F2）
                    if self.record == True:
                        keyboard.press_and_release('F2')
                    # 关闭主窗口
                    sleep(0.5)
                    self.root.destroy()

                if current_total_tick >= self.total_tick:
                    self.update_full_display(self.get_end_text(), "", {})
                    if self.play_timer_id:
                        self.root.after_cancel(self.play_timer_id)
                    self.root.after(500, lambda: close_window_and_press_f2(self))
                    return
                

                # 3. 快速匹配当前应播放的音符（基于预计算的tick区间）
                current_note = None
                for tick_start, tick_end, note in self.note_tick_ranges:
                    if tick_start <= current_total_tick < tick_end:
                        current_note = note
                        break

                # 4. 绘制当前音符/LRC/动态信息
                if current_note:
                    self._draw_current_note(current_note)
                self._update_dynamic_info(play_elapsed)

            except Exception as e:
                pass
            # 5ms高精度轮询，兼顾精度和性能
            self.play_timer_id = self.root.after(5, update)
        # 立即启动，无延迟
        update()

    # ========== 绘制当前音符 ==========
    def _draw_current_note(self, current_note):
        raw_lyric = current_note.get("lyric", "")
        raw_note_num = current_note.get("note_num", 0)

        if raw_lyric == "R":
            ust_lyric = self.get_silent_text()
            note_name = ""
        elif raw_lyric == "-":
            ust_lyric = self.last_valid_lyric if self.last_valid_lyric else self.get_silent_text()
            # ===== 适配：使用音高占位符处理音名 =====
            note_name = self.get_pitch_placeholder_text(raw_note_num)
        else:
            ust_lyric = raw_lyric
            self.last_valid_lyric = ust_lyric
            # ===== 适配：使用音高占位符处理音名 =====
            note_name = self.get_pitch_placeholder_text(raw_note_num)

        self.update_full_display(ust_lyric, note_name, current_note)

    # ===== 修正：音高占位符文本生成逻辑 =====
    def get_pitch_placeholder_text(self, raw_note_num):
        try:
            ori = self.midi_to_note_name(raw_note_num)

            # 匹配：C4、D5 这类不带#的
            pure = re.fullmatch(r'^([A-G])(\d+)$', ori)
            # 匹配：C#4、D#5 带#的
            sharp = re.fullmatch(r'^([A-G]#)(\d+)$', ori)

            if sharp:
                # 带#一律原样返回：C#4 → C#4
                return ori

            if pure:
                note = pure.group(1)   # C
                num = pure.group(2)    # 4

                if self.pitch_placeholder == "无":
                    return f"{note}{num}"

                elif self.pitch_placeholder == "-":
                    return f"{note}-{num}"

                elif self.pitch_placeholder == "自定义文字":
                    # C4 → C(自定义)4
                    suffix = self.pitch_custom_text.strip()
                    return f"{note}({suffix}){num}" if suffix else f"{note}{num}"

            # 其他格式原样返回
            return ori

        except:
            pass
        return self.midi_to_note_name(raw_note_num)

    # ========== 更新动态信息（播放时间/LRC） ==========
    def _update_dynamic_info(self, play_elapsed):
        # 更新LRC歌词
        self.update_lrc_index(play_elapsed)
        # 绘制动态元素（播放时间/LRC）
        self.update_dynamic_elements(play_elapsed)

    def update_lrc_index(self, play_elapsed):
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
        except:
            self.current_lrc_idx = -1

    def get_current_lyric(self):
        try:
            if 0 <= self.current_lrc_idx < len(self.lrc_lines):
                return self.lrc_lines[self.current_lrc_idx][1]
        except:
            pass
        return ""

    # ========== 显示更新 ==========
    def get_transparent_color(self, r, g, b, alpha):
        try:
            alpha = max(0, min(255, alpha))
            return f"#{int(r*alpha/255):02x}{int(g*alpha/255):02x}{int(b*alpha/255):02x}"
        except:
            return "#FFFFFF"

    def format_play_time(self, seconds):
        try:
            ms = int((seconds - int(seconds)) * 100)
            td = timedelta(seconds=int(seconds))
            return f"{td.seconds//60:02d}:{td.seconds%60:02d}:{ms:02d}"
        except:
            return "00:00:00"

    def update_dynamic_elements(self, play_elapsed):
        try:
            self.canvas.delete("dynamic")
            # 播放时间
            if self.show_play_time:
                self.canvas.create_text(
                    20, self.h-20, text=self.format_play_time(play_elapsed),
                    fill=self.small_font_color, font=self.small_font, anchor=tk.SW, tag="dynamic"
                )
            # LRC歌词
            if self.show_lyric and self.lrc_lines:
                current_lyric = self.get_current_lyric()
                if current_lyric:
                    cx = self.w // 2
                    cy = self.h * 0.3 if self.lyric_pos == "上" else self.h * 0.7
                    try:
                        # ===== 修正：歌词颜色直接使用其他文字颜色的十六进制值 =====
                        self.canvas.create_text(
                            cx, cy, text=current_lyric,
                            fill=self.small_font_color,  # 直接使用其他文字颜色
                            font=self.lyric_font,
                            width=self.w - 200,
                            anchor=tk.CENTER,
                            justify=tk.CENTER,
                            tag="dynamic"
                        )
                    except:
                        pass
        except:
            pass

    def update_full_display(self, ust_lyric, note_name, current_note):
        try:
            self.canvas.delete("all")
            cx, cy = self.w//2, self.h//2

            # 音名/音高占位符
            if note_name:
                self.canvas.create_text(
                    cx, cy, text=note_name,
                    fill=self.get_transparent_color(*self.note_color, self.note_alpha),
                    font=self.note_font
                )

            # 音高线
            if self.curve_show:
                pb_data = current_note.get("pitch_bend", [])
                note_length = current_note.get("length", 0)
                if pb_data and len(pb_data) >= 2 and note_length > 0:
                    curve_total_width = int(note_length * self.length_to_pixel)
                    start_x = cx - (curve_total_width // 2)
                    end_x = cx + (curve_total_width // 2)
                    base_y = cy
                    points = []
                    pb_count = len(pb_data)
                    for i in range(pb_count):
                        x = start_x + (i / (pb_count - 1)) * curve_total_width
                        y_offset = (pb_data[i] / 100) * (self.h * 0.09)
                        y = base_y - y_offset
                        safe_top = 100
                        safe_bottom = self.h - 100
                        if safe_top <= y <= safe_bottom:
                            final_y = y
                        elif y < safe_top:
                            exceed_value = safe_top - y
                            scale = max(0.3, 1 - (exceed_value / self.h * 2))
                            final_y = safe_top - (exceed_value * scale)
                        else:
                            exceed_value = y - safe_bottom
                            scale = max(0.3, 1 - (exceed_value / self.h * 2))
                            final_y = safe_bottom + (exceed_value * scale)
                        final_y = max(50, min(final_y, self.h - 50))
                        points.append((x, final_y))
                    self.canvas.create_line(
                        *sum(points, ()),
                        fill=self.small_font_color,
                        width=self.note_line_width,
                        smooth=True
                    )

            # 歌字
            if ust_lyric:
                self.canvas.create_text(
                    cx, cy, text=ust_lyric,
                    fill=f"#{self.ust_lyric_color[0]:02x}{self.ust_lyric_color[1]:02x}{self.ust_lyric_color[2]:02x}",
                    font=self.ust_lyric_font
                )

            # 静态信息（曲名/作者/BPM/版权）
            y_offset = 20
            if self.show_song_name and self.song_name:
                self.canvas.create_text(20, y_offset, text=self.song_name,fill=self.small_font_color, font=("等线", 14, "bold"), anchor=tk.NW)
                y_offset += 27
            if self.show_song_author and self.song_author:
                self.canvas.create_text(20, y_offset, text=self.song_author,fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
                y_offset += 25
            if self.show_ust_author and self.ust_author:
                self.canvas.create_text(20, y_offset, text=self.ust_author,fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
            if self.show_bpm:
                self.canvas.create_text(self.w-20, 20, text=f"BPM={self.tempo}",fill=self.small_font_color, font=self.small_font, anchor=tk.NE)
            self.canvas.create_text(self.w//2, self.h-20,
                text="ustPlayer-v26b10 © 2026 SYEternalR",
                fill=self.get_transparent_color(195,195,195,self.copyright_alpha),
                font=self.copyright_font)
        except:
            pass

    # ========== 静默/结束文本 ==========
    def get_silent_text(self):
        try:
            if self.silent_display == "R":
                return "R"
            elif self.silent_display == "-":
                return "-"
            elif self.silent_display == "自定义文字":
                return self.silent_custom_text
        except:
            pass
        return ""

    def get_end_text(self):
        try:
            if self.end_display == "END":
                return "END"
            elif self.end_display == "-":
                return "-"
            elif self.end_display == "自定义文字":
                return self.end_custom_text
        except:
            pass
        return ""

    # ========== MIDI转音名 ==========
    def midi_to_note_name(self, midi_num):
        try:
            midi_num = int(midi_num)
            octave = (midi_num // 12) - 1
            return f"{self.note_names[midi_num%12]}{octave}"
        except:
            return str(midi_num)

    # ========== ESC关闭 ==========
    def close(self, event=None):
        try:
            if self.play_timer_id:
                self.root.after_cancel(self.play_timer_id)
            self.root.destroy()
            if self.record == True :
                keyboard.press_and_release('F2')
        except:
            self.root.quit()
            self.root.destroy()
            if self.record == True :
                keyboard.press_and_release('F2')


# 对外接口
def display(ust_info):
    try:
        root = tk.Tk()
        app = NoteLyricDisplay(root, ust_info)
        root.mainloop()
    except Exception as e:
        print(f"程序启动失败：{e}")