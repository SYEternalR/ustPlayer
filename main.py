# main.py
import userform as uf
import ustplayer as up
import tkinter as tk
import threading

# ---------------------- 核心：播放程序 ----------------------
def play_ust(ust_info):
    """main.py 中的播放核心逻辑（独立线程执行，不阻塞界面）"""
    def play_task():
        print("\n=== main.py 播放程序启动 ===")
        print(f"版本：{ust_info['version']}")
        print(f"速度：{ust_info['tempo']} BPM")
        print(f"音符数量：{len(ust_info['notes'])}")
        print(f"歌词列表：{[note['lyric'] for note in ust_info['notes']]}")
        # 调用全屏显示
        up.display(ust_info)
        print("播放完成！")
    
    # 启动播放线程
    play_thread = threading.Thread(target=play_task, daemon=True)
    play_thread.start()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("ustx player")  
    userform = uf.UstxPlayerSettings(root, play_callback=play_ust)
    root.mainloop()