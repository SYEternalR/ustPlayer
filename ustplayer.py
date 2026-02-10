import tkinter as tk
import time
import re
from datetime import timedelta

class NoteLyricDisplay:
    def __init__(self, root, ust_info):
        self.root = root
        self.root.title("ustPlayerform")

        self.fullscreen = ust_info["player_style"].get("fullscreen", True)
        if self.fullscreen:
            self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)

        self.bg_color = self.validate_hex_color(ust_info["player_style"].get("bg_color", "#000000"))
        self.root.config(bg=self.bg_color)

        self.canvas = tk.Canvas(root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.root.bind("<Escape>", self.close)

        self.notes = ust_info.get("notes", [])
        self.tempo = ust_info.get("tempo", 120)
        self.last_valid_lyric = ""

        self.start_real_time = time.time()
        self.play_timer_id = None
        self.tick_per_second = (self.tempo * 480) / 60
        self.total_tick = sum(max(n.get("length", 480), 1) for n in self.notes)

        self.curve_show = ust_info["show_config"].get("curve_show", False)

        self.show_lyric = ust_info["show_config"].get("lyric", True)
        self.lrc_path = ust_info["player_style"].get("lrc_path", "")
        self.lrc_lines = []
        self.current_lrc_idx = -1
        self.lyric_pos = ust_info["player_style"].get("lyric_pos", "上")
        self.lrc_font_scale = 0.03

        if self.show_lyric and self.lrc_path:
            self.parse_lrc_file()

        self.note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        try:
            self.w = self.root.winfo_screenwidth() or 1920
            self.h = self.root.winfo_screenheight() or 1080
        except:
            self.w = 1920
            self.h = 1080

        self.note_font_size = max(int(self.h * 2/3 * 0.4), 50)
        self.lyric_font_size = max(int(self.h * self.lrc_font_scale), 10)
        self.ust_lyric_font_size = max(int(self.h * 2/3 * 0.2), 80)
        self.note_font = ("等线", self.note_font_size, "bold")
        self.lyric_font = ("等线", self.lyric_font_size, "normal")
        self.ust_lyric_font = ("等线", self.ust_lyric_font_size, "bold")

        self.small_font = ("等线", 14)
        self.small_font_color = self.validate_hex_color(ust_info["player_style"].get("other_text_color", "#FFFFFF"))

        self.copyright_font = ("等线", 12)
        self.copyright_alpha = 100
        self.note_alpha = 225

        self.ust_lyric_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("lyric_color", "#FFFFFF")))
        self.note_color = self.hex_to_rgb(self.validate_hex_color(ust_info["player_style"].get("note_color", "#C3C3C3")))

        self.show_bpm = ust_info["show_config"].get("bpm", True)
        self.show_play_time = ust_info["show_config"].get("play_time", True)
        self.show_song_name = ust_info["show_config"].get("song_name", True)
        self.show_song_author = ust_info["show_config"].get("song_author", True)
        self.show_ust_author = ust_info["show_config"].get("ust_author", True)

        self.project_info = ust_info.get("project_info", {})
        self.song_name = self.project_info.get("song_name", "")
        self.song_author = self.project_info.get("song_author", "")
        self.ust_author = self.project_info.get("ust_author", "")

        self.silent_display = ust_info["player_style"].get("silent_display", "R")
        self.silent_custom_text = ust_info["player_style"].get("silent_custom_text", "")
        self.end_display = ust_info["player_style"].get("end_display", "END")
        self.end_custom_text = ust_info["player_style"].get("end_custom_text", "")

        # ===================== 音高占位符 =====================
        self.pitch_placeholder = ust_info["player_style"].get("pitch_placeholder", "无")
        self.pitch_custom_text = ust_info["player_style"].get("pitch_custom_text", "")

        self.note_line_offset = self.note_font_size // 4
        self.note_line_width = 5
        self.length_to_pixel = 1

        self.note_tick_ranges = self._calc_note_tick_ranges()
        self.start_main_timer()

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
                    ms = int(frag[2])
                    if len(frag[2]) == 2:
                        ms *= 10
                    ts = minutes * 60 + seconds + ms / 1000
                    txt = frag[3].strip()
                    if txt:
                        self.lrc_lines.append([ts, txt])
                except:
                    continue
            self.lrc_lines.sort(key=lambda x: x[0])
        except:
            self.lrc_lines = []

    def _calc_note_tick_ranges(self):
        note_ranges = []
        current_tick = 0
        for note in self.notes:
            length = max(note.get("length", 480), 1)
            note_ranges.append([current_tick, current_tick + length, note])
            current_tick += length
        return note_ranges

    def start_main_timer(self):
        def update():
            try:
                now = time.time()
                elapsed = now - self.start_real_time
                current_tick = elapsed * self.tick_per_second

                if current_tick >= self.total_tick:
                    self.update_full_display(self.get_end_text(), "", {})
                    if self.play_timer_id:
                        self.root.after_cancel(self.play_timer_id)
                    self.root.after(1000, self.root.destroy)
                    return

                current_note = None
                for s, e, n in self.note_tick_ranges:
                    if s <= current_tick < e:
                        current_note = n
                        break

                if current_note:
                    self._draw_current_note(current_note)
                self._update_dynamic_info(elapsed)
            except Exception:
                pass
            self.play_timer_id = self.root.after(5, update)
        update()

    def _draw_current_note(self, current_note):
        raw_lyric = current_note.get("lyric", "")
        raw_note_num = current_note.get("note_num", 0)

        if raw_lyric == "R":
            ust_lyric = self.get_silent_text()
            note_name = ""
        elif raw_lyric == "-":
            ust_lyric = self.last_valid_lyric if self.last_valid_lyric else self.get_silent_text()
            note_name = self.get_pitch_placeholder_text(raw_note_num)
        else:
            ust_lyric = raw_lyric
            self.last_valid_lyric = ust_lyric
            note_name = self.get_pitch_placeholder_text(raw_note_num)

        self.update_full_display(ust_lyric, note_name, current_note)

    # ===================== 核心：音名占位符（已修复自定义） =====================
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
                    return f"{note}{suffix}{num}" if suffix else f"{note}{num}"

            # 其他格式原样返回
            return ori

        except:
            pass
        return self.midi_to_note_name(raw_note_num)
    
    def _update_dynamic_info(self, elapsed):
        self.update_lrc_index(elapsed)
        self.update_dynamic_elements(elapsed)

    def update_lrc_index(self, elapsed):
        if not self.lrc_lines:
            return
        new_idx = -1
        for i, (ts, _) in enumerate(self.lrc_lines):
            if ts <= elapsed:
                new_idx = i
            else:
                break
        self.current_lrc_idx = new_idx

    def get_current_lyric(self):
        if 0 <= self.current_lrc_idx < len(self.lrc_lines):
            return self.lrc_lines[self.current_lrc_idx][1]
        return ""

    def get_transparent_color(self, r, g, b, alpha):
        try:
            a = max(0, min(255, alpha))
            return f"#{int(r*a/255):02x}{int(g*a/255):02x}{int(b*a/255):02x}"
        except:
            return "#FFFFFF"

    def format_play_time(self, sec):
        try:
            ms = int((sec - int(sec)) * 100)
            m = int(sec) // 60
            s = int(sec) % 60
            return f"{m:02d}:{s:02d}:{ms:02d}"
        except:
            return "00:00:00"

    def update_dynamic_elements(self, elapsed):
        try:
            self.canvas.delete("dynamic")
            if self.show_play_time:
                self.canvas.create_text(20, self.h-20, text=self.format_play_time(elapsed),
                    fill=self.small_font_color, font=self.small_font, anchor=tk.SW, tag="dynamic")

            if self.show_lyric and self.lrc_lines:
                lyr = self.get_current_lyric()
                if lyr:
                    cx = self.w//2
                    cy = self.h*0.3 if self.lyric_pos == "上" else self.h*0.7
                    self.canvas.create_text(cx, cy, text=lyr,
                        fill=self.small_font_color,  # 已同步：其他文字颜色
                        font=self.lyric_font, width=self.w-200,
                        anchor=tk.CENTER, justify=tk.CENTER, tag="dynamic")
        except:
            pass

    def update_full_display(self, ust_lyric, note_name, current_note):
        try:
            self.canvas.delete("all")
            cx, cy = self.w//2, self.h//2

            if note_name:
                self.canvas.create_text(cx, cy, text=note_name,
                    fill=self.get_transparent_color(*self.note_color, self.note_alpha),
                    font=self.note_font)

            if self.curve_show:
                pb = current_note.get("pitch_bend", [])
                ln = current_note.get("length", 0)
                if pb and len(pb) >= 2 and ln > 0:
                    w = int(ln * self.length_to_pixel)
                    x0 = cx - w//2
                    x1 = cx + w//2
                    pts = []
                    cnt = len(pb)
                    for i in range(cnt):
                        x = x0 + (i/(cnt-1))*w if cnt>1 else x0
                        yoff = (pb[i]/100)*(self.h*0.09)
                        y = cy - yoff
                        y = max(50, min(self.h-50, y))
                        pts.append((x, y))
                    self.canvas.create_line(*sum(pts, ()), fill=self.small_font_color,
                        width=self.note_line_width, smooth=True)

            if ust_lyric:
                self.canvas.create_text(cx, cy, text=ust_lyric,
                    fill=f"#{self.ust_lyric_color[0]:02x}{self.ust_lyric_color[1]:02x}{self.ust_lyric_color[2]:02x}",
                    font=self.ust_lyric_font)

            yoff = 20
            if self.show_song_name and self.song_name:
                self.canvas.create_text(20, yoff, text=self.song_name, fill=self.small_font_color, font=("等线", 14, "bold"), anchor=tk.NW)
                yoff += 27
            if self.show_song_author and self.song_author:
                self.canvas.create_text(20, yoff, text=self.song_author, fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
                yoff += 25
            if self.show_ust_author and self.ust_author:
                self.canvas.create_text(20, yoff, text=self.ust_author, fill=self.small_font_color, font=self.small_font, anchor=tk.NW)
                yoff += 25
            if self.show_bpm:
                self.canvas.create_text(self.w-20, 20, text=f"BPM={self.tempo}", fill=self.small_font_color, font=self.small_font, anchor=tk.NE)

            self.canvas.create_text(self.w//2, self.h-20,
                text="ustPlayer-v26b10 © 2026 SYEternalR",
                fill=self.get_transparent_color(195,195,195,self.copyright_alpha),
                font=self.copyright_font)
        except:
            pass

    def get_silent_text(self):
        try:
            if self.silent_display == "R":
                return "R"
            elif self.silent_display == "-":
                return "-"
            elif self.silent_display == "自定义文字":
                return self.silent_custom_text.strip()
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
                return self.end_custom_text.strip()
        except:
            pass
        return ""

    def midi_to_note_name(self, midi_num):
        try:
            m = int(midi_num)
            octave = (m // 12) - 1
            return f"{self.note_names[m % 12]}{octave}"
        except:
            return str(midi_num)

    def close(self, event=None):
        try:
            if self.play_timer_id:
                self.root.after_cancel(self.play_timer_id)
            self.root.destroy()
        except:
            self.root.quit()

def display(ust_info):
    try:
        root = tk.Tk()
        app = NoteLyricDisplay(root, ust_info)
        root.mainloop()
    except Exception as e:
        print(f"启动失败: {e}")