import tkinter as tk
import time
import re
import codecs
from datetime import timedelta

class NoteLyricDisplay:
    def __init__(self, root, ust_info):
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

        # 全屏Canvas
        self.canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ESC关闭
        self.root.bind("<Escape>", self.close)

        # 核心数据（强制默认值，杜绝空值）
        self.notes = ust_info.get("notes", [])
        self.tempo = ust_info.get("tempo", 120)
        self.current = 0
        self.last_valid_lyric = ""
        
        # 播放时间
        self.start_real_time = time.time()
        self.play_elapsed_time = 0
        self.play_timer_id = None

        # 是否显示音高线变化
        self.curve_show = ust_info["show_config"].get("curve_show", False)
        
        # ========== 你的LRC自定义配置（完全保留） ==========
        self.show_lyric = ust_info["show_config"].get("lyric", True)
        self.lrc_path = ust_info["player_style"].get("lrc_path", "")
        self.lrc_lines = []
        self.current_lrc_idx = -1
        self.lyric_pos = ust_info["player_style"].get("lyric_pos", "上")
        self.lrc_gray_level = 180
        self.lrc_font_scale = 0.03  # 你的小字体配置
        
        # 解析LRC文件
        if self.show_lyric and self.lrc_path:
            self.parse_lrc_file()

        # MIDI转音名
        self.note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # 屏幕尺寸（强制兜底值，杜绝异常）
        try:
            self.w = self.root.winfo_screenwidth() or 1920
            self.h = self.root.winfo_screenheight() or 1080
        except:
            self.w = 1920
            self.h = 1080

        # 字体配置（强制最小值，杜绝负数）
        self.note_font_size = max(int(self.h * 2/3 * 0.4), 50)  # 强制最小50px
        self.lyric_font_size = max(int(self.h * self.lrc_font_scale), 10)  # 强制最小10px
        self.ust_lyric_font_size = max(int(self.h * 2/3 * 0.2), 80)  # 强制最小80px
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
        self.note_alpha = 90

        # 颜色配置
        self.ust_lyric_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("lyric_color", "#FFFFFF")))
        self.note_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("note_color", "#C3C3C3")))
        self.lrc_text_color = (self.lrc_gray_level, self.lrc_gray_level, self.lrc_gray_level)

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

        # ===== 音高线配置（修改：长度随length变化，固定粗细）=====
        self.note_line_offset = self.note_font_size // 4  # 音高名下方偏移
        self.note_line_width = 5  # 固定粗细（解决不一致）
        self.length_to_pixel = 1  # 缩放系数：length=480 → 240像素（可自定义调整）

        # 启动计时器
        self.start_play_timer()
        self.play_next()

    # ========== 工具方法（完全保留） ==========
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

    # ========== 播放计时（完全保留） ==========
    def start_play_timer(self):
        def update():
            try:
                self.play_elapsed_time = time.time() - self.start_real_time
                self.update_lrc_index()
                self.update_dynamic_elements()
            except:
                pass
            self.play_timer_id = self.root.after(10, update)
        self.play_timer_id = self.root.after(10, update)

    def update_lrc_index(self):
        if not self.lrc_lines:
            return
        
        try:
            current_time = self.play_elapsed_time
            new_idx = -1
            
            for i in range(len(self.lrc_lines)):
                if self.lrc_lines[i][0] <= current_time:
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

    # ========== 显示更新（核心修改：音高线绘制 + 图层顺序） ==========
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

    def update_dynamic_elements(self):
        """彻底修复：歌词位置计算，无论上/下都不会崩溃"""
        try:
            self.canvas.delete("dynamic")

            # 1. 播放时间
            if self.show_play_time:
                self.canvas.create_text(
                    20, self.h-20, text=self.format_play_time(self.play_elapsed_time),
                    fill=self.small_font_color, font=self.small_font, anchor=tk.SW, tag="dynamic"
                )

            # 2. LRC歌词（核心修复：硬兜底坐标）
            if self.show_lyric and self.lrc_lines:
                current_lyric = self.get_current_lyric()
                if current_lyric:
                    cx = self.w // 2  # 水平居中固定
                    # 彻底修复：无论上/下，都用绝对安全的坐标
                    if self.lyric_pos == "上":
                        cy = self.h * 0.3  # 上位置固定在屏幕30%处
                    else:
                        cy = self.h * 0.7  # 下位置固定在屏幕70%处（核心：不再依赖note_font_size）
                    
                    # 绘制歌词（包裹try，杜绝绘制崩溃）
                    try:
                        self.canvas.create_text(
                            cx, cy, text=current_lyric,
                            fill=f"#{self.lrc_text_color[0]:02x}{self.lrc_text_color[1]:02x}{self.lrc_text_color[2]:02x}",
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

    def update_full_display(self, ust_lyric, note_name, current_note):  # 带current_note参数，解决错位
        try:
            self.canvas.delete("all")
            cx, cy = self.w//2, self.h//2  # 屏幕整体中点（横纵基准）

            # ========== 第一步：最先绘制音高名（最下层，底层） ==========
            if note_name:
                self.canvas.create_text(
                    cx, cy, text=note_name,
                    fill=self.get_transparent_color(*self.note_color, self.note_alpha),
                    font=self.note_font
                )

            # ========== 第二步：再绘制音高线（中间层，在音高名上方、歌字下方） ==========
            if self.curve_show:
                pb_data = current_note.get("pitch_bend", [])
                note_length = current_note.get("length", 0)
                
                # 仅当有有效PitchBend数据且length>0时绘制
                if pb_data and len(pb_data) >= 2 and note_length > 0:
                    # 1. 计算音高线总长度（随note_length变化，可通过length_to_pixel调整）
                    curve_total_width = int(note_length * self.length_to_pixel)
                    
                    # 2. 横向居中：以屏幕水平中点为中心，左右对称延伸
                    start_x = cx - (curve_total_width // 2)
                    end_x = cx + (curve_total_width // 2)
                    
                    # 3. 纵向居中：以屏幕垂直中点为基准，围绕中点上下波动（无额外偏移，纯居中）
                    base_y = cy  # 垂直中点，如需微调可改为 cy ± 数值（如cy + 30）
                    
                    # 4. 生成曲线坐标点（横纵均贴合屏幕中点）
                    points = []
                    pb_count = len(pb_data)
                    for i in range(pb_count):
                        # 横向：从左到右均匀分布，保持水平居中
                        x = start_x + (i / (pb_count - 1)) * curve_total_width
                        # 纵向：围绕垂直中点波动，控制波动范围（屏幕9%，避免过大）
                        y_offset = (pb_data[i] / 100) * (self.h * 0.09)
                        y = base_y - y_offset
                        
                        # ========== 核心修改：超出安全边界后平滑削减跨度 ==========
                        # 1. 定义安全边界（上下各留100像素，可自定义）
                        safe_top = 100
                        safe_bottom = self.h - 100  # 直接使用实例的屏幕高度self.h，无需重新获取
                        
                        # 2. 分段判断并处理超出边界的情况
                        if safe_top <= y <= safe_bottom:
                            # 正常范围：保持原y坐标
                            final_y = y
                        elif y < safe_top:
                            # 超出上边界：计算超出差值，按比例削减跨度（梯度缩放）
                            exceed_value = safe_top - y  # 超出上边界的差值（正数）
                            # 缩放系数：超出越多，缩放越强（0.3~1.0之间，可调整），避免完全归零
                            scale = max(0.3, 1 - (exceed_value / self.h * 2))  # 2是调节系数，可自定义
                            final_y = safe_top - (exceed_value * scale)  # 削减超出部分的跨度
                        else:  # y > safe_bottom
                            # 超出下边界：同理，梯度缩放
                            exceed_value = y - safe_bottom  # 超出下边界的差值（正数）
                            scale = max(0.3, 1 - (exceed_value / self.h * 2))
                            final_y = safe_bottom + (exceed_value * scale)
                        
                        # 3. 确保最终坐标不会极端超出（兜底保护，可选）
                        final_y = max(50, min(final_y, self.h - 50))
                        
                        # 4. 添加处理后的最终坐标到列表
                        points.append((x, final_y))
                    
                    # 5. 绘制音高线（5像素粗、平滑曲线、横纵居中、中间图层）
                    self.canvas.create_line(
                        *sum(points, ()),
                        fill=self.small_font_color,
                        width=self.note_line_width,  # 已配置为5像素
                        smooth=True
                    )

            # ========== 第三步：最后绘制歌字(UST歌词)（最上层，顶层） ==========
            if ust_lyric:
                self.canvas.create_text(
                    cx, cy, text=ust_lyric,
                    fill=f"#{self.ust_lyric_color[0]:02x}{self.ust_lyric_color[1]:02x}{self.ust_lyric_color[2]:02x}",
                    font=self.ust_lyric_font
                )

            # ========== 后续其他信息绘制（保留原有所有功能，无修改） ==========
            # 4. 左上角信息（曲名、作者等）
            y_offset = 20
            if self.show_song_name and self.song_name:
                self.canvas.create_text(20, y_offset, text=self.song_name,
                    fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
                y_offset += 25
            if self.show_song_author and self.song_author:
                self.canvas.create_text(20, y_offset, text=self.song_author,
                    fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
                y_offset += 25
            if self.show_ust_author and self.ust_author:
                self.canvas.create_text(20, y_offset, text=self.ust_author,
                    fill=self.small_font_color, font=self.small_font, anchor=tk.NW)

            # 5. 右上角BPM
            if self.show_bpm:
                self.canvas.create_text(self.w-20, 20, text=f"BPM={self.tempo}",
                    fill=self.small_font_color, font=self.small_font, anchor=tk.NE)

            # 6. 底部版权信息
            self.canvas.create_text(self.w//2, self.h-20,
                text="ustPlayer-v26a31 © 2026 SYEternalR",
                fill=self.get_transparent_color(195,195,195,self.copyright_alpha),
                font=self.copyright_font)

            # 更新动态元素（播放时间、LRC歌词等）
            self.update_dynamic_elements()
        except:
            pass

    # ========== 播放逻辑（完全保留） ==========
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

    def play_next(self):
        try:
            if self.current >= len(self.notes):
                self.update_full_display(self.get_end_text(), "", {})  # 第三个参数传空字典
                if self.play_timer_id:
                    self.root.after_cancel(self.play_timer_id)
                self.root.after(1000, self.root.destroy)
                return

            # 取出当前音符（这是关键：直接获取当前self.current对应的音符，不偏移）
            current_note = self.notes[self.current] if self.current < len(self.notes) else {}
            raw_lyric = current_note.get("lyric", "")
            raw_note_num = current_note.get("note_num", 0)

            if raw_lyric == "R":
                ust_lyric = self.get_silent_text()
                note_name = ""
            elif raw_lyric == "-":
                ust_lyric = self.last_valid_lyric if self.last_valid_lyric else self.get_silent_text()
                note_name = self.midi_to_note_name(raw_note_num)
            else:
                ust_lyric = raw_lyric
                self.last_valid_lyric = ust_lyric
                note_name = self.midi_to_note_name(raw_note_num)

            length = current_note.get("length", 480)
            beat = 60 / max(self.tempo, 1)
            dur = max(length * beat / 480, 0.1)

            # 修改：传递当前音符current_note给update_full_display
            self.update_full_display(ust_lyric, note_name, current_note)

            self.current += 1
            self.root.after(int(dur * 1000), self.play_next)
        except:
            self.current += 1
            self.root.after(100, self.play_next)

    def midi_to_note_name(self, midi_num):
        try:
            midi_num = int(midi_num)
            octave = (midi_num // 12) - 1
            return f"{self.note_names[midi_num%12]}{octave}"
        except:
            return str(midi_num)

    # ========== 关闭（完全保留） ==========
    def close(self, event=None):
        try:
            if self.play_timer_id:
                self.root.after_cancel(self.play_timer_id)
            self.root.destroy()
        except:
            pass

# 对外接口（完全保留）
def display(ust_info):
    try:
        root = tk.Tk()
        NoteLyricDisplay(root, ust_info)
        root.mainloop()
    except Exception as e:
        print(f"程序启动失败：{e}")
