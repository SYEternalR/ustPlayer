# ustPlayer 配布文档
中文的、面向多样音声合成编辑器工程文件的可视化工具。

自 **2026.02.10** 开始，最新版本为 **ustPlayer-v26b10** 。

## 下载说明
请前往 Release 页面下载最新的.exe版本。
> 我们将不再提供 .msi 安装包，也不再打算提供 .app 格式程序。

---

## 更新内容（v26b11）

- tkinter → PySide6 全面重构，播放器改用 QPainter 渲染，性能大幅提升。
- 引入 uv 包管理，`uv sync` 一键安装依赖。
- 新增 `setting.json` 集中配置，版本号统一管理。
- 新增 `build.py` Nuitka 一键编译脚本。
- 修复文件未安全关闭、线程安全、类型缺失、编码容错等问题。
- 模块化拆分：`player.py` / `ust_reader.py` / `ust_types.py` 各司其职。
- 新增 TypedDict 全类型覆盖，Pyright 静态检查。

---

## 配布、发布视频
[【ustPlayer】UTAU可视化工具](https://www.bilibili.com/video/BV1YjcwzVEcX)

---

## 补充说明
**使用前请务必阅读并同意相关使用协议。**

本工具在开发过程中使用了 AI 工具进行辅助开发。
用户协议详情可查看：
- 程序目录下`Terms.txt`
- 或软件内入口：`其他 > 协议与许可 > 使用协议`

> ustPlayer版权由SYEternalR所有，授权给符合条件的任何用户免费使用。

感谢使用，玩得开心！
