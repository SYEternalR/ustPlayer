import json
import os
from typing import TypedDict


class Setting(TypedDict):
    """从 setting.json 读取的设置结构。"""
    Name: str
    Version: str

def get_setting() -> Setting:
    """从 setting.json 读取设置。"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    setting_path = os.path.join(base_dir, "setting.json")
    try:
        with open(setting_path, "r", encoding="utf-8") as f:
            setting = json.load(f)
            return setting
    except FileNotFoundError:
        print("未找到 setting.json，返回空设置。")
        return {
            "Name": "",
            "Version": "",
        }
    except json.JSONDecodeError as e:
        print(f"解析 setting.json 时发生错误：{e}")
        return {
            "Name": "",
            "Version": "",
        }
