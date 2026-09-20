import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render", ROOT / "skills/article-to-xiaohongshu/scripts/render.py")
render = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = render
SPEC.loader.exec_module(render)


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_path = render.find_font(os.environ.get("ARTICLE_CARDS_FONT"))
        cls.font = ImageFont.truetype(str(cls.font_path), 38)

    def test_wrap_preserves_text_and_width(self):
        for text in ["你好，世界。这是一段（带括号）的中文！" * 20,
                     "Open Source makes a difference. " * 30,
                     "A" * 180, "中英 mixed paragraph，继续阅读。" * 20]:
            with self.subTest(text=text[:20]):
                lines = render.wrap_text(text, self.font, 400)
                self.assertEqual("".join(lines), text)
                self.assertTrue(all(self.font.getlength(line) <= 400 for line in lines))

    def test_closing_punctuation(self):
        lines = render.wrap_text("甲乙丙丁，戊己庚辛。", self.font, self.font.getlength("甲乙丙丁"))
        self.assertFalse(any(line[0] in render.CLOSING for line in lines[1:]))

    def test_full_generation_preserves_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            article = tmp / "article.md"
            article.write_text("# 排版测试\n\n" + "这是一段非常长的文章，应该跨页连续显示。" * 150 +
                               "\n\n## 下一节\n\nEnglish words stay readable. " * 3, encoding="utf-8")
            avatar = tmp / "avatar.png"
            Image.new("RGBA", (240, 160), (60, 150, 100, 180)).save(avatar)
            result = render.generate(article, "测试作者", tmp / "out", avatar=avatar, date="09/20", font=self.font_path)
            self.assertGreater(len(result["pages"]), 2)
            rebuilt = ["" for _ in result["blocks"]]
            for page in result["pages"]:
                with Image.open(tmp / "out" / page["file"]) as image:
                    self.assertEqual(image.size, (1080, 1440))
                self.assertTrue(page["lines"])
                for line in page["lines"]:
                    rebuilt[line["block"]] += line["text"]
                    self.assertGreaterEqual(line["y"], 250)
                    self.assertLessEqual(line["y"] + line["height"], 1350)
            self.assertEqual(rebuilt, [b["text"] for b in result["blocks"]])
            with zipfile.ZipFile(tmp / "out/cards.zip") as archive:
                self.assertEqual(archive.namelist(), [p["file"] for p in result["pages"]])
            self.assertTrue((tmp / "out/contact-sheet.jpg").is_file())
            with self.assertRaisesRegex(ValueError, "empty or new"):
                render.generate(article, "作者", tmp / "out")

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            render.parse_article(" \n\n")
        with self.assertRaisesRegex(ValueError, "line_height"):
            render.Style(line_height=12).validate()
        with self.assertRaisesRegex(ValueError, "overlaps"):
            render.Style(body_top=100).validate()
        with self.assertRaisesRegex(ValueError, "missing characters"):
            render.verify_glyphs(self.font_path, 0, "\U0010FFFF")
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "style.json"
            config.write_text(json.dumps({"font_sze": 38}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unknown style fields"):
                render.Style.from_file(config)

    def test_square_cards_with_placeholder_and_no_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            article = tmp / "article.txt"
            article.write_text("方形卡片也应保留完整文字。" * 50, encoding="utf-8")
            config = tmp / "style.json"
            config.write_text(json.dumps({"width": 1080, "height": 1080}), encoding="utf-8")
            result = render.generate(article, "作者", tmp / "out", font=self.font_path, config=config)
            self.assertEqual(result["avatar"], "initial-placeholder")
            self.assertEqual(result["date"], "")
            for page in result["pages"]:
                with Image.open(tmp / "out" / page["file"]) as image:
                    self.assertEqual(image.size, (1080, 1080))
                self.assertTrue(all(line["y"] + line["height"] <= 990 for line in page["lines"]))

    def test_heading_stays_with_following_lines(self):
        style = render.Style()
        heading_font = ImageFont.truetype(str(self.font_path), 48)
        blocks = [{"kind": "body", "text": "内容" * 110},
                  {"kind": "heading", "text": "下一节"},
                  {"kind": "body", "text": "新的内容" * 65}]
        pages = render.layout(blocks, style, self.font, heading_font)
        for page in pages:
            for index, line in enumerate(page):
                if line["kind"] == "heading":
                    self.assertGreaterEqual(len(page) - index - 1, 2)


if __name__ == "__main__":
    unittest.main()
