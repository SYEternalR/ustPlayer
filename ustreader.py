def get_ust_info(ust_folder):
    # ===== 1. 初始化要提取的信息（本地化变量）=====
    ust_version = ""          # 存储UST版本
    ust_tempo = 0.0           # 存储速度
    ust_tracks = 0            # 存储轨道数
    note_list = []            # 存储所有音符信息（列表里放字典）
    current_note = {}         # 临时存储当前解析的音符
    
    # ===== 2. 打开文件并读取内容（保留你的原始写法，优化了文件关闭）=====
    input_file = open(f"{ust_folder}", "r", encoding="Shift-JIS")
    try:
        # 按行读取（避免一次性读入后再遍历字符）
        ust_lines = input_file.readlines()
        
        # 状态标记：当前是否在[#SETTING]分段内、是否在音符分段内
        in_setting = False
        in_note = False
        
        # ===== 3. 逐行解析（嵌入式识别分段 + 提取信息）=====
        for line in ust_lines:
            line = line.strip()  # 去掉每行首尾的空格/换行符
            if not line:  # 跳过空行
                continue
            
            # ---- 识别分段标记 ----
            # 1. 识别版本分段
            if line == "[#VERSION]":
                in_setting = False
                in_note = False
                # 下一行就是版本信息，需要单独处理
                continue
            # 2. 识别设置分段
            elif line == "[#SETTING]":
                in_setting = True
                in_note = False
                continue
            # 3. 识别音符分段（[#0000]/[#0001]这类）
            elif line.startswith("[#") and line.endswith("]") and line[3:-1].isdigit():
                # 如果上一个音符没保存，先保存
                if current_note:
                    note_list.append(current_note)
                # 初始化新音符
                current_note = {
                    "index": line[3:-1],  # 音符序号（0000/0001）
                    "length": 0,
                    "lyric": "",
                    "note_num": 0,
                    "pitch_bend": ""
                }
                in_setting = False
                in_note = True
                continue
            
            # ---- 提取分段内的具体信息 ----
            # 1. 提取版本信息（[#VERSION]的下一行）
            if ust_version == "" and line.startswith("UST Version"):
                ust_version = line
            # 2. 提取[#SETTING]内的信息（速度/轨道数）
            elif in_setting and "=" in line:
                key, value = line.split("=", 1)  # 按第一个=分割，避免值里有=
                key = key.strip()
                value = value.strip()
                if key == "Tempo":
                    ust_tempo = float(value)  # 转成浮点数
                elif key == "Tracks":
                    ust_tracks = int(value)   # 转成整数
            # 3. 提取音符分段内的信息
            elif in_note and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "Length":
                    current_note["length"] = int(value)
                elif key == "Lyric":
                    current_note["lyric"] = value
                elif key == "NoteNum":
                    current_note["note_num"] = int(value)
                elif key == "PitchBend":
                    current_note["pitch_bend"] = value
        
        # 最后一个音符加入列表
        if current_note:
            note_list.append(current_note)
    
    finally:
        input_file.close()  # 确保文件一定关闭

    # ===== 4. 返回提取的所有信息（本地化整合结果）=====
    return {
        "version": ust_version,
        "tempo": ust_tempo,
        "tracks": ust_tracks,
        "notes": note_list
    }

# ---------------------- 测试调用（本地化使用示例）----------------------
if __name__ == "__main__":
    # 替换成你的UST文件路径
    ust_path = "sample.ust"
    
    # 调用函数提取信息
    ust_info = get_ust_info(ust_path)
    
    # 本地化打印提取结果
    print("=== UST 提取结果 ===")
    print(f"版本：{ust_info['version']}")
    print(f"速度：{ust_info['tempo']} BPM")
    print(f"轨道数：{ust_info['tracks']}")
    print("\n音符列表：")
    for idx, note in enumerate(ust_info['notes']):
        print(f"  音符{idx+1}：歌词={note['lyric']}，音高={note['note_num']}，时长={note['length']}")