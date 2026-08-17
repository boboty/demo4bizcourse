"""从真实命令输出渲染可读的"终端卡片"图片（PNG），供课件与备份页使用。

不是截图——是把已经跑出来的真实文本，用固定规则渲染成图，保证：
1) 断言内容本体可见（不是一片绿的空终端）；2) 1920x1080 下投影可读（大字号）；
3) 可重跑：同样的输入文本 + 同一条命令 = 同样的图。

行级着色规则（纯文本前缀匹配，不依赖 ANSI 转义）：
  '+'   开头 -> 绿色（diff 新增 / pass）
  '-'   开头 -> 红色（diff 删除）
  'E ' / 'FAILED' / 'assert' 出现 -> 品红/红色高亮该行
  'PASS' / 'passed' 出现 -> 绿色高亮该行
  其余 -> 默认前景色
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MENLO = "/System/Library/Fonts/Menlo.ttc"
HELVETICA = "/System/Library/Fonts/HelveticaNeue.ttc"
HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"  # CJK coverage; Helvetica/Menlo don't have it


def _has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)

BG = (13, 17, 23)
FG = (201, 209, 217)
DIM = (110, 122, 133)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)
CYAN = (121, 192, 255)
TITLEBAR = (22, 27, 34)
ACCENT = (13, 139, 118)


def _font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def line_color(line: str):
    stripped = line.strip()
    if stripped.startswith("+++") or stripped.startswith("---"):
        return DIM
    if stripped.startswith("+"):
        return GREEN
    if stripped.startswith("-"):
        return RED
    if stripped.startswith("@@"):
        return CYAN
    if stripped.startswith("#"):
        return DIM
    if stripped.startswith("$"):
        return YELLOW
    if "assert" in line and ("==" in line or "AssertionError" in line):
        return RED
    if "FAILED" in line or "REJECTED" in line or "Missing" in line:
        return RED
    if "PASS" in line or "passed" in line or "ALL TESTS PASSED" in line:
        return GREEN
    if stripped.startswith(">"):
        return RED
    if stripped.startswith("E "):
        return RED
    return FG


def _body_font_for(text, size, bold):
    if _has_cjk(text):
        return _font(HIRAGINO, size, index=2 if bold else 0)
    return _font(MENLO, size, index=1 if bold else 0)


def _wrap_line(draw, text, font, max_width):
    """Character-wrap (safe for mixed CJK/ASCII) so no line runs off the right edge."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width or not text:
        return [text]
    out, cur = [], ""
    for ch in text:
        trial = cur + ch
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] > max_width and cur:
            out.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def render(
    body_text: str,
    out_path: str,
    title: str,
    subtitle: str = "",
    width: int = 1920,
    height: int = 1080,
    font_size: int | None = None,
    line_height_mult: float = 1.5,
    pad_x: int = 64,
    pad_top: int = 140,
    highlight_lines: list | None = None,
    min_font_size: int = 18,
    max_font_size: int = 34,
) -> None:
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    max_text_width = width - pad_x - 40
    raw_lines = body_text.split("\n")
    highlight_lines = set(highlight_lines or [])

    def wrap_all(size):
        wrapped = []  # list of (text, color, is_hl)
        for idx, raw_line in enumerate(raw_lines):
            color = line_color(raw_line)
            is_hl = idx in highlight_lines
            font = _body_font_for(raw_line, size, is_hl or color in (RED, GREEN))
            for sub in _wrap_line(draw, raw_line, font, max_text_width):
                wrapped.append((sub, color, is_hl))
        return wrapped

    if font_size is None:
        # auto-fit: every line must be visible, never silently truncated with "..."
        available_h = height - pad_top - 20
        guess = max(min_font_size, min(max_font_size, int(available_h / max(len(raw_lines), 1) / line_height_mult)))
        wrapped = wrap_all(guess)
        fitted = int(available_h / max(len(wrapped), 1) / line_height_mult)
        font_size = max(min_font_size, min(max_font_size, fitted))
        wrapped = wrap_all(font_size)  # re-wrap: font size may have changed
        if fitted < min_font_size:
            print(
                f"WARNING: {len(wrapped)} wrapped lines don't fit at min_font_size={min_font_size} "
                f"within {height}px height — text will still render, but may overflow. "
                f"Consider trimming body_text.",
                file=sys.stderr,
            )
    else:
        wrapped = wrap_all(font_size)

    draw.rectangle([0, 0, width, 96], fill=TITLEBAR)
    for i, c in enumerate((RED, YELLOW, GREEN)):
        draw.ellipse([48 + i * 34, 36, 48 + i * 34 + 22, 58], fill=c)
    title_x = 48 + 3 * 34 + 24  # clear the traffic-light dots
    title_font = _font(HIRAGINO, 30, index=2) if _has_cjk(title) else _font(HELVETICA, 30, index=1)
    draw.text((title_x, 28), title, font=title_font, fill=(230, 233, 236))
    if subtitle:
        sub_font = _font(HIRAGINO, 20, index=0) if _has_cjk(subtitle) else _font(HELVETICA, 20, index=0)
        draw.text((title_x, 64), subtitle, font=sub_font, fill=DIM)

    line_h = int(font_size * line_height_mult)
    y = pad_top

    for text, color, is_hl in wrapped:
        if y > height - line_h:
            draw.text((pad_x, y), "…", font=_body_font_for("…", font_size, False), fill=DIM)
            break
        font = _body_font_for(text, font_size, is_hl or color in (RED, GREEN))
        if is_hl:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            draw.rectangle(
                [pad_x - 12, y - 4, pad_x + tw + 12, y + line_h - 6],
                fill=(color[0] // 5, color[1] // 5, color[2] // 5),
            )
        draw.text((pad_x, y), text, font=font, fill=color)
        y += line_h

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"wrote {out_path} ({width}x{height})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text-file", required=True, help="body text source file")
    p.add_argument("--out", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--font-size", type=int, default=None, help="omit for auto-fit (recommended)")
    p.add_argument("--highlight-lines", default="", help="comma-separated 0-based line indices to highlight")
    args = p.parse_args()

    body = Path(args.text_file).read_text(encoding="utf-8")
    hl = [int(x) for x in args.highlight_lines.split(",") if x.strip()]
    render(
        body,
        args.out,
        args.title,
        subtitle=args.subtitle,
        width=args.width,
        height=args.height,
        font_size=args.font_size,
        highlight_lines=hl,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
