# 样式配置

UTF-8 JSON 对象；未填写字段沿用默认值。未知字段报错，避免拼写错误被忽略。

## 背景预设

用 `--theme paper|white|cream|sage|mist|rose` 选择背景，默认 `paper`。预设只改变背景颜色，不改变文字、头像、布局或分页。配置文件中的显式值优先于预设；例如指定 `--theme mist` 时，如果 JSON 仍含 `background`，将使用 JSON 的背景色。

| 预设 | 名称 | 背景色 |
| --- | --- | --- |
| paper | 米白 | #F8F9F3 |
| white | 纯白 | #FFFFFF |
| cream | 奶油 | #FFF2D9 |
| sage | 浅绿 | #EDF4E8 |
| mist | 雾蓝 | #EAF2FA |
| rose | 浅粉 | #F9EBEB |

## 自定义参数

| 字段 | 默认值 | 含义 |
| --- | --- | --- |
| width / height | 1080 / 1440 | 图片像素，支持其他竖版或方形比例 |
| margin | 76 | 左右页边距 |
| body_top | 250 | 首张正文起点 |
| continuation_top | 76 | 第二张及以后正文起点 |
| bottom | 90 | 正文底部保留空间 |
| font_size | 38 | 正文字号 |
| heading_size | 48 | 标题字号 |
| line_height | 62 | 正文行高 |
| paragraph_gap | 34 | 段落额外间距 |
| avatar_size | 104 | 头像直径 |
| header_top | 68 | 头像顶部 |
| name_size | 36 | 昵称字号 |
| date_size | 25 | 日期字号 |
| image_max_height | 520 | 正文插图最大高度，宽度不超过正文栏，保持原始比例 |
| background | #F8F9F3 | 背景颜色 |
| foreground | #20221F | 正文颜色 |
| muted | #7A7E74 | 日期、页码颜色 |
| avatar_background | #DCE8DB | 占位头像背景 |

尺寸改变后，其他数值不会自动等比缩放。例如使用 1200×1600 时，可自行同比增加页边距、字号和头像尺寸。为了维持手机阅读舒适度，优先采用默认尺寸。

布局规则：先按字体实际宽度换行，再按可用高度分页。能整段放入下一页的段落尽量不拆分；超过一页的长段落按行拆分，并尽量避免只剩一行。标题与下一段至少前两行尽量同页。仅第一张显示头像、昵称和可选日期；第二张起正文从 continuation_top 开始，页码仍在每张底部显示。

支持独占一行的本地图片 `![说明](assets/photo.png)`。路径需位于文章目录内，可用 `<assets/my photo.png>` 包住含空格的路径；不支持网络链接、绝对路径或越出文章目录。插图按原始比例居中缩放，完整放入一页，不裁切或拆分。透明图片使用当前卡片背景。manifest schema_version 2 在 pages[].lines 中新增 kind=image，含 block、x、y、width、height；文字条目保持原有结构。

不支持富文本加粗、代码块、表格或字体 fallback。发现不支持的字符时会提示更换字体或调整原文。
