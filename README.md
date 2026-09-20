# 文章转小红书 · Article to Xiaohongshu

把文章变成 **带头像、昵称、日期的分页文字卡片**。默认 3:4 竖版，米白底、宋体正文，按实际字体宽度自动换行和分页。

这是一个可安装的 Agent Skill，也可以独立作为 Python 命令行工具使用。**无需 API Key，本地运行，输入不会上传。**

![示例卡片](examples/preview.png)

[查看整组示例](examples/contact-sheet.jpg)

## 快速开始

需要 Python 3.10+ 和覆盖文章文字的中文字体。

```bash
git clone https://github.com/Fangx-AI/article-to-xiaohongshu.git
cd article-to-xiaohongshu
python -m pip install -r skills/article-to-xiaohongshu/requirements.txt
python skills/article-to-xiaohongshu/scripts/render.py --article examples/article.md --name "纸上散步" --date "09/20" --output demo-output
```

添加自己的头像：

```bash
python skills/article-to-xiaohongshu/scripts/render.py --article your-article.md --name "你的昵称" --avatar your-avatar.jpg --date "09/20" --output your-output
```

未传头像时生成昵称首字占位头像。日期省略则不显示。文章中可使用空行分段及 `#`、`##`、`###` 标题；其他 Markdown 标记按字面显示。默认不删减或改写文章。

输出包括：

- `01.png`、`02.png`…：统一尺寸的正文卡片。
- `contact-sheet.jpg`：整组缩略预览。
- `cards.zip`：仅包含正文图片的压缩包。
- `manifest.json`：输入哈希、分页文字、行框与样式，方便核查。

输出目录必须为空或不存在。重新排版时指定新的目录，避免混入旧图片。

## 安装为 Skill

将仓库里的 `skills/article-to-xiaohongshu` 整个目录复制到你的 Agent 的技能目录。例如 Codex：`~/.codex/skills/article-to-xiaohongshu`；Claude Code：`~/.claude/skills/article-to-xiaohongshu`。其他支持 `SKILL.md` 的工具按各自技能目录安装。

依赖仍需在该 Agent 使用的 Python 环境安装。示例请求：

> 使用 article-to-xiaohongshu，把这篇文章做成 3:4 的小红书图文。头像用 avatar.jpg，昵称“纸上散步”，保留原文，日期不显示。

## 字体

脚本尝试发现 Windows 宋体、macOS 宋体及 Linux Noto CJK。也可以显式指定字体与字体集索引：

```bash
python skills/article-to-xiaohongshu/scripts/render.py --article examples/article.md --name "作者" --font /path/to/font.ttc --font-index 0 --output custom-output
```

Ubuntu / Debian 可安装中文字体：

```bash
sudo apt-get install fonts-noto-cjk
```

仓库不捆绑系统字体。使用和再分发字体时遵循其许可证。字体缺字会明确报错；当前不支持多字体回退及彩色 emoji。

## 自定义样式

```bash
python skills/article-to-xiaohongshu/scripts/render.py --article examples/article.md --name "作者" --config examples/style.json --output styled-output
```

配置参数见 [配置说明](skills/article-to-xiaohongshu/references/config.md)。默认按段落分页，长段落跨页连续排版；不会通过强制缩小字体把文章挤进固定页数。没有绑定平台上传数量限制，请按发布时的实际限制处理长文章。

## 开发与验证

```bash
python -m unittest discover -s tests -v
```

测试覆盖内容完整性、行框边界、超长英文、中文标点、空文章、缺字、错误配置和旧输出保护。GitHub Actions 在 Linux、Windows、macOS 上运行测试。

模板是一种文章阅读卡片，不包含小红书 UI，也与小红书官方无关联。示例文章为本项目原创，示例头像为文字占位；请使用自己有权使用的文章和头像。

## License

MIT，见 [LICENSE](LICENSE)。欢迎通过 Issue 描述问题、附上脱敏后的最小复现文章，或提交 Pull Request。
