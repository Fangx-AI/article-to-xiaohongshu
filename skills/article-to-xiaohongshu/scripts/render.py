#!/usr/bin/env python3
"""Deterministic, local article-to-card renderer. Python 3.10+."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import zipfile

from fontTools.ttLib import TTFont
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps


THEMES = {
    "paper": "#F8F9F3",
    "white": "#FFFFFF",
    "cream": "#FFF2D9",
    "sage": "#EDF4E8",
    "mist": "#EAF2FA",
    "rose": "#F9EBEB",
}


@dataclass
class Style:
    width: int = 1080
    height: int = 1440
    margin: int = 76
    body_top: int = 250
    continuation_top: int = 76
    bottom: int = 90
    font_size: int = 38
    heading_size: int = 48
    line_height: int = 62
    paragraph_gap: int = 34
    avatar_size: int = 104
    header_top: int = 68
    name_size: int = 36
    date_size: int = 25
    image_max_height: int = 520
    background: str = "#F8F9F3"
    foreground: str = "#20221F"
    muted: str = "#7A7E74"
    avatar_background: str = "#DCE8DB"

    @classmethod
    def from_file(cls, path=None, theme="paper"):
        if theme not in THEMES:
            raise ValueError(f"Unknown theme: {theme}. Choose from {', '.join(THEMES)}.")
        values = json.loads(Path(path).read_text(encoding="utf-8-sig")) if path else {}
        if not isinstance(values, dict):
            raise ValueError("Style config must be a JSON object.")
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unknown style fields: {', '.join(sorted(unknown))}")
        style = cls(**{"background": THEMES[theme], **values})
        style.validate()
        return style

    def validate(self):
        for key, value in asdict(self).items():
            if key in {"background", "foreground", "muted", "avatar_background"}:
                if not isinstance(value, str):
                    raise ValueError(f"{key} must be a color string.")
                ImageColor.getrgb(value)
            elif type(value) is not int or value <= 0:
                raise ValueError(f"{key} must be a positive integer.")
        if self.width > 4096 or self.height > 4096:
            raise ValueError("Canvas dimensions must be at most 4096 px.")
        if self.line_height < self.font_size * 1.15:
            raise ValueError("line_height must be at least 1.15 times font_size.")
        if self.width - 2 * self.margin < self.heading_size * 3:
            raise ValueError("Canvas is too narrow for the configured margins and font.")
        if self.body_top < self.header_top + max(self.avatar_size, self.name_size + self.date_size + 20) + 24:
            raise ValueError("Header overlaps the body; increase body_top.")
        if self.height - self.bottom - self.body_top < self.line_height * 3:
            raise ValueError("Body must fit at least three lines.")
        if self.height - self.bottom - self.continuation_top < self.line_height * 3:
            raise ValueError("Continuation pages must fit at least three lines.")
        if self.bottom < 48:
            raise ValueError("bottom must be at least 48 px for the page number.")


def find_font(explicit=None):
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f"Font does not exist: {path}")
        return path
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/simsun.ttc",
        Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
        Path("/System/Library/Fonts/STSong.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError("No Chinese font found. Install Noto CJK or pass --font /path/font.ttf.")


def verify_glyphs(font_path, index, text):
    with TTFont(str(font_path), fontNumber=index, lazy=True) as font:
        cmap = font.getBestCmap() or {}
        missing = sorted({char for char in text if not char.isspace() and ord(char) not in cmap})
    if missing:
        shown = " ".join(f"{char} (U+{ord(char):04X})" for char in missing[:16])
        raise ValueError(f"Font is missing characters: {shown}. Choose another --font or revise the text.")


def parse_article(text):
    """Normalize blank-line paragraphs; a single newline becomes a space."""
    blocks = []
    paragraph = []

    def flush():
        if paragraph:
            blocks.append({"kind": "body", "text": " ".join(paragraph)})
            paragraph.clear()

    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip().expandtabs(4)
        heading = re.match(r"^#{1,3}\s+(.+)$", line)
        picture = re.match(r"^!\[([^\]]*)\]\((.+)\)$", line)
        if not line:
            flush()
        elif picture:
            flush()
            path = picture.group(2).strip()
            if path.startswith("<") and path.endswith(">"):
                path = path[1:-1]
            blocks.append({"kind": "image", "text": picture.group(1), "path": path})
        elif heading:
            flush()
            blocks.append({"kind": "heading", "text": heading.group(1)})
        else:
            paragraph.append(line)
    flush()
    if not blocks:
        raise ValueError("Article is empty.")
    return blocks


CLOSING = set("，。！？；：、）》】」』〉〕］｝,.!?;:%…”)﹚﹜﹞")
OPENING = set("（《【「『〈〔［｛“(﹙﹛﹝")


def wrap_text(text, font, width):
    """Preserve all characters; avoid CJK punctuation and ASCII word splits."""
    lines = []
    start = 0
    while start < len(text):
        end = start
        while end < len(text) and font.getlength(text[start:end + 1]) <= width:
            end += 1
        if end == start:
            raise ValueError("A character is wider than the text area; increase width or reduce font size.")
        if end < len(text):
            is_word = lambda c: c.isascii() and (c.isalnum() or c in "_-")
            if is_word(text[end - 1]) and is_word(text[end]):
                word_start = end - 1
                while word_start > start and is_word(text[word_start - 1]):
                    word_start -= 1
                if word_start > start:
                    end = word_start
            # Move the preceding character together with closing punctuation.
            while end > start + 1 and (text[end] in CLOSING or text[end - 1] in OPENING):
                end -= 1
        lines.append(text[start:end])
        start = end
    return lines


def load_article_images(blocks, article):
    """Load only local images contained in the article directory; never fetch URLs."""
    base = Path(article).resolve().parent
    images = {}
    for index, block in enumerate(blocks):
        if block["kind"] != "image":
            continue
        source = block["path"]
        path = Path(source)
        if path.is_absolute() or source.startswith(("/", "\\")) or ":" in source:
            raise ValueError("Article images must use relative local paths inside the article directory.")
        resolved = (base / path).resolve()
        if not resolved.is_relative_to(base):
            raise ValueError("Article image path escapes the article directory.")
        with Image.open(resolved) as image:
            images[index] = ImageOps.exif_transpose(image).convert("RGBA")
    return images


def layout(blocks, style, body_font, heading_font, images=None):
    width = style.width - 2 * style.margin
    limit = style.height - style.bottom
    prepared = []
    images = images or {}
    for block_index, block in enumerate(blocks):
        if block["kind"] == "image":
            image = images[block_index]
            max_height = min(style.image_max_height, limit - max(style.body_top, style.continuation_top))
            scale = min(width / image.width, max_height / image.height)
            image_width = max(1, min(width, round(image.width * scale)))
            image_height = max(1, min(max_height, round(image.height * scale)))
            prepared.append((block, [image_width], image_height))
            continue
        heading = block["kind"] == "heading"
        font = heading_font if heading else body_font
        line_height = max(style.line_height, math.ceil(style.heading_size * 1.4)) if heading else style.line_height
        lines = wrap_text(block["text"], font, width)
        for line in lines:
            bbox = font.getbbox(line, anchor="lt")
            if bbox[3] > line_height or bbox[2] > width:
                raise ValueError("Glyph bounds exceed the line box. Increase line_height or text width.")
        prepared.append((block, lines, line_height))
    pages = [[]]
    y = style.body_top

    def new_page():
        nonlocal y
        if pages[-1]:
            pages.append([])
        y = style.body_top if len(pages) == 1 else style.continuation_top

    capacity = limit - style.continuation_top
    for block_index, (block, lines, line_height) in enumerate(prepared):
        if block["kind"] == "image":
            if y + line_height > limit:
                new_page()
            image_width = lines[0]
            pages[-1].append({"kind": "image", "block": block_index, "text": block["text"],
                              "x": (style.width - image_width) // 2, "y": y,
                              "width": image_width, "height": line_height})
            y += line_height + style.paragraph_gap
            continue
        required = len(lines) * line_height
        if block["kind"] == "heading" and block_index + 1 < len(prepared):
            _, next_lines, next_height = prepared[block_index + 1]
            required += style.paragraph_gap + min(2, len(next_lines)) * next_height
        follows_heading = pages[-1] and pages[-1][-1]["kind"] == "heading"
        if pages[-1] and not follows_heading and required <= capacity and y + required > limit:
            new_page()
        offset = 0
        while offset < len(lines):
            available = int((limit - y) // line_height)
            if available < 1:
                new_page()
                available = int((limit - y) // line_height)
            if available < 1:
                raise ValueError("Heading or body line does not fit in the canvas.")
            take = min(available, len(lines) - offset)
            if take == 1 and len(lines) - offset > 1 and pages[-1]:
                new_page()
                continue
            if len(lines) - offset - take == 1 and take > 2:
                take -= 1
            for line in lines[offset:offset + take]:
                pages[-1].append({"text": line, "kind": block["kind"], "block": block_index,
                                  "x": style.margin, "y": y, "height": line_height})
                y += line_height
            offset += take
            if offset < len(lines):
                new_page()
        y += style.paragraph_gap
    return pages


def make_avatar(path, name, size, font, style):
    # Render the crop and circular edge at 3x resolution for smooth downsampling.
    scale = 3
    canvas = Image.new("RGB", (size * scale, size * scale), style.background)
    if path:
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            fitted = ImageOps.fit(source, canvas.size, method=Image.Resampling.LANCZOS)
            backing = Image.new("RGBA", canvas.size, style.avatar_background)
            backing.alpha_composite(fitted)
            tile = backing.convert("RGB")
    else:
        tile = Image.new("RGB", canvas.size, style.avatar_background)
        draw = ImageDraw.Draw(tile)
        draw.text((size * scale / 2, size * scale / 2), name[0], font=font,
                  fill=style.foreground, anchor="mm")
    mask = Image.new("L", canvas.size)
    ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    canvas.paste(tile, (0, 0), mask)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate(article, name, output, avatar=None, date="", font=None, font_index=0, config=None, theme="paper"):
    name = name.strip()
    if not name or "\n" in name or "\n" in date or "\r" in name or "\r" in date:
        raise ValueError("Name must be nonempty; name and date must each be a single line.")
    style = Style.from_file(config, theme)
    output = Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty or new. Choose a new --output.")
    source = Path(article).read_bytes()
    blocks = parse_article(source.decode("utf-8-sig"))
    article_images = load_article_images(blocks, article)
    font_path = find_font(font)
    verify_glyphs(font_path, font_index, "".join(b["text"] for b in blocks if b["kind"] != "image") + name + date + "0123456789/")
    fonts = {key: ImageFont.truetype(str(font_path), size, index=font_index) for key, size in {
        "body": style.font_size, "heading": style.heading_size, "name": style.name_size,
        "date": style.date_size, "avatar": style.avatar_size * 3 // 2,
    }.items()}
    header_x = style.margin + style.avatar_size + 30
    for value, selected in [(name, fonts["name"]), (date, fonts["date"])]:
        if selected.getlength(value) > style.width - style.margin - header_x:
            raise ValueError("Name or date is too wide for the header. Shorten it or adjust the style.")
    avatar_image = make_avatar(avatar, name, style.avatar_size, fonts["avatar"], style)
    pages = layout(blocks, style, fonts["body"], fonts["heading"], article_images)
    output.mkdir(parents=True, exist_ok=True)
    thumbnails = []
    page_data = []
    for index, lines in enumerate(pages, 1):
        card = Image.new("RGB", (style.width, style.height), style.background)
        draw = ImageDraw.Draw(card)
        if index == 1:
            card.paste(avatar_image, (style.margin, style.header_top))
            name_y = style.header_top + (12 if date else (style.avatar_size - style.name_size) // 2)
            draw.text((header_x, name_y), name, font=fonts["name"], fill=style.foreground, anchor="lt")
            if date:
                draw.text((header_x, style.header_top + style.name_size + 30), date,
                          font=fonts["date"], fill=style.muted, anchor="lt")
        for line in lines:
            if line["kind"] == "image":
                picture = article_images[line["block"]].resize((line["width"], line["height"]), Image.Resampling.LANCZOS)
                card.paste(picture, (line["x"], line["y"]), picture)
                continue
            selected = fonts[line["kind"]]
            draw.text((line["x"], line["y"]), line["text"], font=selected,
                      fill=style.foreground, anchor="lt")
        draw.text((style.width / 2, style.height - style.bottom / 2), f"{index} / {len(pages)}",
                  font=fonts["date"], fill=style.muted, anchor="mm")
        filename = f"{index:02d}.png"
        card.save(output / filename)
        card.thumbnail((270, 360), Image.Resampling.LANCZOS)
        thumbnails.append(card)
        page_data.append({"file": filename, "lines": lines})
    columns = min(4, len(thumbnails))
    tile_w, tile_h = thumbnails[0].size
    rows = math.ceil(len(thumbnails) / columns)
    sheet = Image.new("RGB", (columns * (tile_w + 16) + 16, rows * (tile_h + 16) + 16), "#DFE2DD")
    for index, thumb in enumerate(thumbnails):
        sheet.paste(thumb, (16 + (index % columns) * (tile_w + 16), 16 + (index // columns) * (tile_h + 16)))
    sheet.save(output / "contact-sheet.jpg", quality=90)
    manifest = {"schema_version": 2, "source_sha256": hashlib.sha256(source).hexdigest(),
                "font": font_path.name, "font_index": font_index,
                "name": name, "date": date, "avatar": "provided" if avatar else "initial-placeholder",
                "theme": theme, "style": asdict(style), "blocks": blocks, "pages": page_data}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(output / "cards.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for page in page_data:
            archive.write(output / page["file"], arcname=page["file"])
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, help="UTF-8 plain text or lightweight Markdown")
    parser.add_argument("--name", required=True, help="Author name")
    parser.add_argument("--avatar", help="Local avatar image; defaults to an initial placeholder")
    parser.add_argument("--date", default="", help="Displayed verbatim; omitted by default")
    parser.add_argument("--output", required=True, help="New or empty output directory")
    parser.add_argument("--font", help="TTF/OTF/TTC file with all required glyphs")
    parser.add_argument("--font-index", type=int, default=0, help="Face index for a font collection")
    parser.add_argument("--config", help="Optional JSON style overrides")
    parser.add_argument("--theme", choices=THEMES, default="paper", help="Background preset; config overrides the preset")
    args = parser.parse_args()
    try:
        manifest = generate(**vars(args))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps({"output": str(Path(args.output).resolve()), "pages": len(manifest["pages"]),
                      "width": manifest["style"]["width"], "height": manifest["style"]["height"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
