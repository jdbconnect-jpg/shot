from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
THUMB_DIR = ROOT / "data_shorts" / "thumbnails"
W, H = 720, 1280
YELLOW = (255, 214, 34)
RED = (255, 28, 28)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def font(size: int, index: int = 6) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", size=size, index=index)


def text_box(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, stroke_width: int = 0) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)


def centered_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    stroke_width: int = 1,
    stroke_fill=BLACK,
) -> None:
    box = text_box(draw, text, fnt, stroke_width)
    x = (W - (box[2] - box[0])) // 2 - box[0]
    draw.text((x, y - box[1]), text, font=fnt, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def rounded_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], text: str, fnt: ImageFont.FreeTypeFont, fill, text_fill) -> None:
    draw.rounded_rectangle(xy, radius=13, fill=fill, outline=YELLOW, width=3)
    box = text_box(draw, text, fnt)
    x = (xy[0] + xy[2] - (box[2] - box[0])) // 2 - box[0]
    y = (xy[1] + xy[3] - (box[3] - box[1])) // 2 - box[1] - 1
    draw.text((x, y), text, font=fnt, fill=text_fill)


def rank_row(draw: ImageDraw.ImageDraw, y: int, rank: str, label: str) -> None:
    draw.rounded_rectangle((18, y, 286, y + 46), radius=8, fill=(8, 8, 8), outline=YELLOW, width=3)
    draw.ellipse((27, y + 8, 57, y + 38), fill=YELLOW)
    box = text_box(draw, rank, font(22))
    draw.text((42 - (box[2] - box[0]) // 2, y + 11), rank, font=font(22), fill=BLACK)
    draw.text((70, y + 10), label, font=font(21, 4), fill=WHITE)


def main() -> None:
    bg = Image.open(THUMB_DIR / "scr_20260517_kr_etf_top5_high_ctr_bg_720x1280.png").convert("RGBA")
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((5, 5, W - 5, H - 5), radius=10, outline=YELLOW, width=4)

    draw.rounded_rectangle((18, 22, 294, 74), radius=13, fill=YELLOW)
    draw.text((38, 34), "국장 ETF 인기순위", font=font(26), fill=BLACK)

    centered_text(draw, 112, "지금 돈 몰리는", font(56), WHITE, stroke_width=1)
    centered_text(draw, 190, "ETF TOP 3", font(72), YELLOW, stroke_width=1)
    rounded_label(draw, (396, 285, 628, 354), "1위는 의외?", font(36), RED, WHITE)

    rank_row(draw, 425, "1", "KODEX 200")
    rank_row(draw, 482, "2", "S&P 500")
    rank_row(draw, 539, "3", "반도체")

    draw.rounded_rectangle((18, 1060, W - 18, 1232), radius=14, fill=WHITE, outline=BLACK, width=3)
    centered_text(draw, 1088, "따라 사기 전에", font(48), BLACK, stroke_width=0)
    centered_text(draw, 1152, "이 순서부터 보세요", font(50), RED, stroke_width=1, stroke_fill=BLACK)

    png = THUMB_DIR / "scr_20260517_kr_etf_top5_high_ctr_thumbnail_top3_text90.png"
    jpg = THUMB_DIR / "scr_20260517_kr_etf_top5_high_ctr_thumbnail_top3_text90.jpg"
    canvas.convert("RGB").save(jpg, quality=95)
    canvas.save(png)
    print(png)
    print(jpg)


if __name__ == "__main__":
    main()
