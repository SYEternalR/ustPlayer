# build.py —— Nuitka 编译脚本
# 用法：python build.py            # 单文件模式（生成单个 .exe）
#      python build.py --standalone # 目录模式（生成文件夹，启动更快）
import os
import sys
import subprocess
from get_setting import Setting, get_setting


SETTING: Setting = get_setting()
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "build_output")

# 可选数据文件（放在 .exe 同目录下）
DATA_FILES = {
    os.path.join(PROJECT_ROOT, "Terms.txt"): "Terms.txt",
    os.path.join(PROJECT_ROOT, "ERcode.txt"): "ERcode.txt",
    os.path.join(PROJECT_ROOT, "README.md"): "README.md",
    os.path.join(PROJECT_ROOT, "setting.json"): "setting.json",
    os.path.join(PROJECT_ROOT, "icon.png"): "icon.png",
}

def build() -> None:
    # 用户可以通过命令行参数选择编译模式
    use_onefile = "--standalone" not in sys.argv

    cmd = [
        sys.executable, "-m", "nuitka",
        "--enable-plugin=pyside6",
        "--windows-console-mode=disable",
        f"--output-dir={OUTPUT_DIR}",
        f"--jobs={os.cpu_count() or 4}",
        "--assume-yes-for-downloads",
        # 排除 QtWebEngine（约 450 MB，本程序未使用）
        "--nofollow-import-to=PySide6.QtWebEngineWidgets",
        "--nofollow-import-to=PySide6.QtWebEngineCore",
        "--nofollow-import-to=PySide6.QtWebEngineQuick",
        "--nofollow-import-to=PySide6.QtWebChannel",
        "--noinclude-dlls=*Qt6WebEngine*",
        "--noinclude-dlls=*Qt6Pdf*",
        f"--output-filename={SETTING['Name']}.exe",
        "--windows-icon-from-ico=icon.ico" if os.path.exists(os.path.join(PROJECT_ROOT, "icon.ico")) else "",
    ]

    if use_onefile:
        cmd.append("--onefile")
        # cmd.append("--onefile-no-compression")  # 跳过 LZMA 压缩，打包更快
        print("[模式] 单文件编译 (--onefile)")
    else:
        cmd.append("--standalone")
        print("[模式] 目录编译 (--standalone)")

    # 包含数据文件
    for src, dst in DATA_FILES.items():
        if os.path.exists(src):
            cmd.append(f"--include-data-files={src}={dst}")

    # 主脚本
    cmd.append(MAIN_SCRIPT)

    print(f"\n[命令] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        if use_onefile:
            exe = os.path.join(OUTPUT_DIR, f"{SETTING['Name']}.exe")
        else:
            exe = os.path.join(OUTPUT_DIR, f"{SETTING['Name']}.dist", f"{SETTING['Name']}.exe")
        print(f"\n编译成功！输出文件：{exe}")
        # print("请将 Terms.txt / ERcode.txt / README.md / setting.json 放到 .exe 同目录下（如需要）。")
    else:
        print("\n编译失败，请查看上方错误信息。")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
