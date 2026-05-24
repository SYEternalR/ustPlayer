# ust_types.py —— ustreader、main、player 共用的 TypedDict 类型定义
from typing import TypedDict, Required


class StyleConfig(TypedDict):
    """GUI 样式配置字典。"""
    font_family: Required[str]
    font_size: Required[int]
    frame_padding: Required[str]
    global_padx: Required[int]
    global_pady: Required[int]
    play_btn_pady: Required[int]
    play_btn_columnspan: Required[int]
    entry_width: Required[int]
    label_sticky: Required[str]
    entry_sticky: Required[str]
    label_style: Required[str]
    button_style: Required[str]
    entry_style: Required[str]


class NoteInfo(TypedDict):
    """单个音符（从 UST 文件中解析）。"""
    index: Required[str]
    length: Required[int]
    lyric: Required[str]
    note_num: Required[int]
    pitch_bend: Required[list[int]]


class CoreUstInfo(TypedDict):
    """ustreader.get_ust_info 的返回值。"""
    version: Required[str]
    tempo: Required[float]
    tracks: Required[int]
    notes: Required[list[NoteInfo]]


class ShowConfig(TypedDict):
    """显示开关标志。"""
    bpm: Required[bool]
    play_time: Required[bool]
    song_name: Required[bool]
    song_author: Required[bool]
    ust_author: Required[bool]
    lyric: Required[bool]
    curve_show: Required[bool]


class ProjectInfo(TypedDict):
    """项目元数据。"""
    project_name: Required[str]
    song_name: Required[str]
    song_author: Required[str]
    ust_author: Required[str]


class PlayerStyle(TypedDict, total=False):
    """播放器样式设置。部分键可能缺失。"""
    bg_color: str
    note_color: str
    lyric_color: str
    lyric_text_color: str
    other_text_color: str
    lyric_pos: str
    show_phoneme: bool
    show_midinote: bool
    show_waveform: bool
    fullscreen: bool
    lrc_path: str
    lrc_gray_level: int
    lrc_font_scale: float
    silent_display: str
    silent_custom_text: str
    end_display: str
    end_custom_text: str
    pitch_placeholder: str
    pitch_custom_text: str


class UstInfo(TypedDict):
    """传递给播放器的完整信息字典。"""
    version: Required[str]
    tempo: Required[float]
    tracks: Required[int]
    notes: Required[list[NoteInfo]]
    show_config: Required[ShowConfig]
    project_info: Required[ProjectInfo]
    encoding: Required[str]
    player_style: Required[PlayerStyle]
