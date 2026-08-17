"""渲染课件内嵌用的"一眼看清"证据小卡（hero tile）——只放1-3行最关键的信息，
不是终端截图缩小版。完整细节版另见 render_card.py 产出的 demo-evidence 1920x1080 图。
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MENLO = "/System/Library/Fonts/Menlo.ttc"
HELVETICA = "/System/Library/Fonts/HelveticaNeue.ttc"
HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"  # CJK coverage; Helvetica/Menlo don't have it

DARK = (23, 33, 41)
GREEN = (13, 139, 118)
GREEN_BG = (14, 46, 40)
RED = (201, 75, 71)
FG = (247, 250, 248)
DIM = (154, 168, 163)


def _has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)


def _font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def _line_font(text: str, size: int, bold: bool):
    if _has_cjk(text):
        return _font(HIRAGINO, size, index=2 if bold else 0)  # W6 bold / W3 regular
    return _font(MENLO, size, index=1 if bold else 0)


def _cap_font(size=30):
    return _font(HIRAGINO, size, index=2)


# 1650x800 matches the page-35 gallery tile slot's aspect ratio (~2.06:1),
# so `fit: cover` in the deck doesn't crop the title bar or footer note.
def render_bug_tile(out_path, width=1650, height=800):
    img = Image.new("RGB", (width, height), DARK)
    d = ImageDraw.Draw(img)
    d.text((44, 30), "注入的 BUG（diff）", font=_cap_font(30), fill=(215, 243, 236))

    lines = [
        ('  if coupon == "VIP100" and customerLevel == "GOLD"', FG, False),
        ("      and amount >= GOLD_THRESHOLD:", FG, False),
        ("+     # 跳过 GOLD 判断，直接按券给 200", GREEN, True),
        ("+     discount = GOLD_DISCOUNT + VIP_DISCOUNT", GREEN, True),
    ]
    y = 118
    for text, color, bold in lines:
        font = _line_font(text, 30, bold)
        if bold:
            bbox = d.textbbox((0, 0), text, font=font)
            d.rectangle([28, y - 6, width - 28, y + (bbox[3] - bbox[1]) + 12], fill=GREEN_BG)
        d.text((44, y), text, font=font, fill=color)
        y += 56

    note_font = _font(HIRAGINO, 22, index=0)
    d.text((44, height - 54), "app/service.py — 14 行改动，其余原样保留", font=note_font, fill=DIM)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print("wrote", out_path)


def render_verdict_tile(out_path, big_text, big_color, sub_text, caption, width=1650, height=800, bg=DARK):
    img = Image.new("RGB", (width, height), bg)
    d = ImageDraw.Draw(img)
    d.text((44, 30), caption, font=_cap_font(30), fill=(215, 243, 236) if bg == DARK else (255, 255, 255))

    big_font = _font(HELVETICA, 130, index=1)
    d.text((44, 160), big_text, font=big_font, fill=big_color)

    y = 380
    for line in sub_text:
        color = RED if ("assert" in line or "failed" in line) else FG
        font = _line_font(line, 36, True)
        d.text((44, y), line, font=font, fill=color)
        y += 56

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print("wrote", out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    out = Path(args.out_dir)

    render_bug_tile(out / "tile-bug-diff.png")
    render_verdict_tile(
        out / "tile-generated-green.png",
        big_text="4 passed",
        big_color=GREEN,
        sub_text=["tests/generated/  — 全绿", "同一份 BUG 实现"],
        caption="GENERATED 套件（同一份 BUG 实现下）",
        bg=DARK,
    )
    render_verdict_tile(
        out / "tile-verified-red.png",
        big_text="1 failed",
        big_color=RED,
        sub_text=["assert 0 == 100", "3 passed · 同一份 BUG 实现"],
        caption="VERIFIED 套件（同一份 BUG 实现下）",
        bg=(43, 20, 19),
    )


if __name__ == "__main__":
    main()
