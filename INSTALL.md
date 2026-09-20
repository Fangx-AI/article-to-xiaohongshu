# 给 AI Agent 的安装指南

目标：将 `wenka` 安装到当前 Agent 可发现的技能目录，准备可运行的 Python 环境，并实际生成一组示例图片。用户无需手动复制命令。

本指南用于用户明确要求安装本项目的场景。根据当前工具、操作系统和已有环境选择安装方式，不假定所有聊天工具都能操作本地文件或执行命令。

## 1. 获取项目和确定安装位置

仓库：`https://github.com/Fangx-AI/wenka`

- 将仓库克隆或下载到工作目录。已有本项目时先检查状态，保留用户修改。
- 阅读 `skills/wenka/SKILL.md` 和 `requirements.txt`。
- 安装单元是完整的 `skills/wenka` 文件夹，不是整个仓库，也不只是 `SKILL.md`。
- 优先使用当前 Agent 已配置的技能目录和用户指定的位置。Codex 默认位置为 `${CODEX_HOME}/skills/wenka`（未设置时为 `~/.codex/skills/wenka`）；Claude Code 的用户级位置为 `~/.claude/skills/wenka`。其他工具使用其实际支持的目录。
- 遇到已有同名技能，先比较内容；保留本地修改，不直接覆盖。需要替换时先保存可恢复的副本。

## 2. 准备运行环境

- 检查当前环境中的 Python 3.10+。Windows 可能使用 `py -3`；不要假设 `python` 一定是可用或正确的解释器。
- 优先复用可用、合适的环境。需要新环境时，在安装后的技能目录内创建 `.venv`，用其中的 Python 安装 `requirements.txt`。不要修改系统 Python 或无关项目的依赖。
- 后续渲染也使用同一个解释器：Windows 为 `.venv/Scripts/python.exe`，macOS / Linux 为 `.venv/bin/python`。调用时使用绝对路径，无需要求用户激活环境。
- 若缺少 Python 或系统安装权限，根据当前环境和已有授权处理；无法继续时说明具体缺项，不声称已完成安装。

## 3. 检查中文字体

- 优先使用系统中已有的宋体类中文字体：Windows 宋体、macOS Songti、Linux Noto Serif CJK。
- 脚本找不到字体时，可将已有字体的绝对路径传入 `--font`。
- 若环境确实没有中文字体，可安装 Noto Serif CJK 等开放字体；优先用户目录安装，遵循字体许可证。Ubuntu / Debian 的系统包是 `fonts-noto-cjk`，系统级安装按实际权限处理。
- 不将系统字体重新打包进项目。缺字需解决，不能把方框字成品当作成功。

## 4. 使用安装后的 Skill 实际生成

使用安装后的 `scripts/render.py`、准备好的解释器及仓库中的 `examples/article.md`。保留文章旁的 `assets/` 图片目录。以昵称「方鑫三个金」、默认米白背景、未显示日期生成到新的输出目录；示例头像使用 `examples/assets/cat.png`。

命令形状如下，实际执行时展开绝对路径并按操作系统正确引用：

```text
<python> <installed-skill>/scripts/render.py --article <repo>/examples/article.md --avatar <repo>/examples/assets/cat.png --name "方鑫三个金" --output <new-output-directory>
```

检查生成结果：

- 存在编号 PNG、`contact-sheet.jpg`、`cards.zip` 和 `manifest.json`。
- 图片为 1080×1440，中文可读，正文无明显截断。
- 只有首张有头像和昵称，后续页从顶部留白处直接接正文。

查看整组预览和至少一张后续页。不能只凭文件复制成功或依赖安装成功就宣称安装完成。

## 5. 交付

向用户提供示例预览和输出位置，简要说明安装位置和可直接复制的使用提示词：

> 用 wenka 把这篇【公众号链接 或 文章内容】转成小红书卡片。

如当前 Agent 需要新会话或重新加载才能发现新增 Skill，按该工具的实际行为提示用户。无需让用户重新执行已经完成的安装命令。
