from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
REMOTION_PUBLIC = ROOT / "remotion" / "public"
JOB_PATH = REMOTION_PUBLIC / "shorts-job.json"
OUT_DIR = ROOT / "data_shorts" / "renders"
TMP_DIR = OUT_DIR / "reference_layout_parts"
W, H, FPS = 720, 1280, 30
YELLOW = (255, 212, 59)
TITLE_YELLOW = (255, 205, 0)
TITLE_RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


HEADLINES = {
    "hook": ["월 100만원 배당?", "JEPI·JEPQ 전에", "이것부터 보세요"],
    "mechanism": ["월분배 ETF", "돈 나오는 구조는", "커버드콜"],
    "comparison": ["SCHD는", "월급보다", "배당의 질"],
    "tradeoff": ["이름보다", "목적이 먼저", "현금흐름 vs 성장"],
    "risk": ["높은 분배금", "공짜가 아닙니다", "원금도 흔들림"],
    "close": ["ETF 선택", "수익률보다", "내 목표부터"],
}

HIGHLIGHTS = [
    "TOP3",
    "TOP5",
    "TOP10",
    "TOP",
    "3",
    "5",
    "1위",
    "2위",
    "3위",
    "4위",
    "5위",
    "KODEX",
    "TIGER",
    "S&P500",
    "나스닥100",
    "반도체",
    "국장",
    "ETF",
    "JEPI",
    "JEPQ",
    "SCHD",
    "100만원",
    "월",
    "배당",
    "커버드콜",
    "목적",
    "현금흐름",
    "성장과",
    "성장",
    "공짜",
    "원금",
    "목표",
    "비중",
    "인기",
    "시장",
]


def font(size: int, index: int = 6) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", size=size, index=index)


TITLE_FONT = font(68)
TITLE_FONT_SMALL = font(60)
SUB_FONT = font(42, index=16)
TITLE_SCALE = 3
TITLE_STROKE = 1
TITLE_LINE_STEP = 88
SUBTITLE_SCALE = 3
SUBTITLE_STROKE = 1
TITLE_BOX_FONT_SIZES = (50, 46, 42, 38, 34)
FAUX_BOLD_OFFSETS = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
)


def cover_image(path: Path, size: tuple[int, int], zoom: float) -> Image.Image:
    src = Image.open(path).convert("RGB")
    target_w, target_h = size
    scale = max(target_w / src.width, target_h / src.height) * zoom
    resized = src.resize((math.ceil(src.width * scale), math.ceil(src.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def prepare_smooth_background(path: Path, size: tuple[int, int], zoom: float) -> Image.Image:
    src = Image.open(path).convert("RGB")
    target_w, target_h = size
    scale = max(target_w / src.width, target_h / src.height) * zoom
    resized = src.resize((math.ceil(src.width * scale), math.ceil(src.height * scale)), Image.Resampling.LANCZOS)
    if resized.width < target_w or resized.height < target_h:
        return cover_image(path, size, zoom)
    return resized


def crop_smooth_background(prepared: Image.Image, size: tuple[int, int], progress: float) -> Image.Image:
    target_w, target_h = size
    max_left = max(0, prepared.width - target_w)
    max_top = max(0, prepared.height - target_h)
    ease = 0.5 - 0.5 * math.cos(math.pi * progress)
    left = round(max_left * 0.5 + (ease - 0.5) * min(18, max_left))
    top = round(max_top * 0.5 + (ease - 0.5) * min(14, max_top))
    left = min(max(0, left), max_left)
    top = min(max(0, top), max_top)
    return prepared.crop((left, top, left + target_w, top + target_h))


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, stroke_width: int = 0) -> int:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)
    return box[2] - box[0]


def draw_heavy_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    stroke_width: int = 0,
    stroke_fill=None,
    faux_radius: int = 1,
) -> None:
    x, y = xy
    if stroke_width:
        draw.text((x, y), text, font=fnt, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill or fill)
    for ox, oy in FAUX_BOLD_OFFSETS:
        if abs(ox) <= faux_radius and abs(oy) <= faux_radius:
            draw.text((x + ox, y + oy), text, font=fnt, fill=fill)
    draw.text((x, y), text, font=fnt, fill=fill)


def highlight_parts(line: str) -> list[tuple[str, tuple[int, int, int]]]:
    parts: list[tuple[str, tuple[int, int, int]]] = []
    i = 0
    highlights = sorted(HIGHLIGHTS, key=len, reverse=True)
    while i < len(line):
        match = next((word for word in highlights if line.startswith(word, i)), None)
        if match:
            parts.append((match, YELLOW))
            i += len(match)
        else:
            next_match_at = min(
                (pos for word in highlights if (pos := line.find(word, i + 1)) != -1),
                default=len(line),
            )
            parts.append((line[i:next_match_at], WHITE))
            i = next_match_at
    return parts


def draw_centered_highlight(draw: ImageDraw.ImageDraw, y: int, line: str, fnt: ImageFont.FreeTypeFont) -> None:
    parts = highlight_parts(line)
    total = sum(text_width(draw, text, fnt) for text, _ in parts)
    x = max(24, (W - total) // 2)
    for text, color in parts:
        draw_heavy_text(draw, (x, y), text, fnt, color, stroke_width=TITLE_STROKE, stroke_fill=BLACK, faux_radius=1)
        x += text_width(draw, text, fnt)


def title_font_for_line(line: str) -> ImageFont.FreeTypeFont:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in (74, 68, 62, 56, 50):
        fnt = font(size)
        width = text_width(draw, line, fnt, TITLE_STROKE)
        if width <= W - 80:
            return fnt
    return font(46)


def title_line_parts(line: str, line_no: int, line_count: int) -> list[tuple[str, tuple[int, int, int]]]:
    if line_count == 2 and line_no == 1:
        return [(line, TITLE_YELLOW)]
    if line_count >= 3 and line_no >= 1:
        return [(line, TITLE_YELLOW)]

    parts: list[tuple[str, tuple[int, int, int]]] = []
    i = 0
    while i < len(line):
        if line.startswith("TOP", i):
            j = i + 3
            while j < len(line) and (line[j].isdigit() or line[j].isspace()):
                j += 1
            parts.append((line[i:j], TITLE_RED))
            i = j
            continue
        parts.append((line[i], WHITE))
        i += 1
    return parts


def make_title_layer(line: str, line_no: int, line_count: int, fnt: ImageFont.FreeTypeFont) -> Image.Image:
    # Render title text at higher resolution, then downsample for clean Korean glyph edges.
    scale = TITLE_SCALE
    layer = Image.new("RGBA", (W * scale, 150 * scale), (0, 0, 0, 0))
    hi_draw = ImageDraw.Draw(layer)
    hi_font = font(fnt.size * scale)
    stroke = TITLE_STROKE * scale
    parts = title_line_parts(line, line_no, line_count)
    boxes = [hi_draw.textbbox((0, 0), text, font=hi_font, stroke_width=stroke) for text, _ in parts]
    total = sum(box[2] - box[0] for box in boxes)
    x = max(28 * scale, (W * scale - total) // 2)
    min_top = min((box[1] for box in boxes), default=0)
    y_hi = 18 * scale - min_top
    cur_x = x
    for (text, color), box in zip(parts, boxes):
        part_x = cur_x - box[0]
        hi_draw.text(
            (part_x, y_hi),
            text,
            font=hi_font,
            fill=color + (255,),
            stroke_width=stroke,
            stroke_fill=BLACK + (255,),
        )
        for ox, oy in FAUX_BOLD_OFFSETS:
            hi_draw.text(
                (part_x + ox * scale, y_hi + oy * scale),
                text,
                font=hi_font,
                fill=color + (255,),
            )
        cur_x += box[2] - box[0]
    return layer.resize((W, 150), Image.Resampling.LANCZOS)


def draw_centered_highlight_smooth(base: Image.Image, y: int, layer: Image.Image) -> None:
    base.paste(layer, (0, y - 18), layer)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    tokens = text.split(" ")
    if len(tokens) == 1:
        chars = list(text)
        lines: list[str] = []
        cur = ""
        for ch in chars:
            if cur and text_width(draw, cur + ch, fnt) > max_w:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
        return lines[:2]

    lines = []
    cur = ""
    for token in tokens:
        nxt = token if not cur else f"{cur} {token}"
        if cur and text_width(draw, nxt, fnt) > max_w:
            lines.append(cur)
            cur = token
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines[:2]


def rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], radius: int, fill, outline, width: int) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_reference_title_box(draw: ImageDraw.ImageDraw, headline: list[str]) -> None:
    title = " ".join(headline[:2]).strip() or (headline[0] if headline else "")
    box_x, box_y, box_w = 52, 64, 616
    pad_l, pad_r, pad_y = 48, 28, 22
    bar_x, bar_w = box_x + 16, 8
    max_text_w = box_w - pad_l - pad_r

    title_font = font(46)
    lines = [title]
    for size in TITLE_BOX_FONT_SIZES:
        candidate_font = font(size)
        candidate_lines = wrap_text(draw, title, candidate_font, max_text_w)
        if len(candidate_lines) <= 2 and all(text_width(draw, line, candidate_font) <= max_text_w for line in candidate_lines):
            title_font = candidate_font
            lines = candidate_lines
            break

    line_h = title_font.size + 12
    box_h = pad_y * 2 + line_h * len(lines)
    draw.rounded_rectangle(
        (box_x, box_y, box_x + box_w, box_y + box_h),
        radius=10,
        fill=(5, 5, 5),
        outline=(18, 18, 18),
        width=2,
    )
    draw.rounded_rectangle((bar_x, box_y + 18, bar_x + bar_w, box_y + box_h - 18), radius=6, fill=TITLE_YELLOW)

    text_y = box_y + pad_y - 4
    for line in lines:
        draw_heavy_text(
            draw,
            (box_x + pad_l, text_y),
            line,
            title_font,
            TITLE_YELLOW,
            stroke_width=1,
            stroke_fill=(18, 18, 18),
            faux_radius=1,
        )
        text_y += line_h


def draw_reference_subtitle_box(draw: ImageDraw.ImageDraw, text: str) -> None:
    band_top, band_bottom = 904, 1168
    band_h = band_bottom - band_top
    draw.rectangle((0, band_top, W, band_bottom), fill=BLACK)
    draw.rectangle((0, band_top, W, band_top + 2), fill=(18, 18, 18))
    draw.rectangle((0, band_bottom - 2, W, band_bottom), fill=(18, 18, 18))

    max_w = W - 96
    # Keep subtitles readable on phones. Heavy Korean fonts plus thick strokes
    # close up glyph counters and turn the line into a white block.
    subtitle_font = font(38, index=6)
    stroke_width = 1
    lines = wrap_text(draw, text, subtitle_font, max_w)
    for size in (38, 36, 34, 32, 30):
        candidate = font(size, index=6)
        candidate_lines = wrap_text(draw, text, candidate, max_w)
        if (
            len(candidate_lines) <= 2
            and all(text_width(draw, line, candidate, stroke_width) <= max_w for line in candidate_lines)
        ):
            subtitle_font = candidate
            lines = candidate_lines
            break

    scale = SUBTITLE_SCALE
    layer = Image.new("RGBA", (W * scale, band_h * scale), (0, 0, 0, 0))
    hi_draw = ImageDraw.Draw(layer)
    hi_font = font(subtitle_font.size * scale, index=6)
    stroke = stroke_width * scale
    line_step = int(subtitle_font.size * 1.42 * scale)
    boxes = [hi_draw.textbbox((0, 0), line, font=hi_font, stroke_width=stroke) for line in lines]
    text_h = line_step * (len(lines) - 1) + max((box[3] - box[1] for box in boxes), default=0)
    y = 32 * scale

    for line, box in zip(lines, boxes):
        tw = box[2] - box[0]
        x = (W * scale - tw) // 2 - box[0]
        baseline_y = y - box[1]
        # Soft shadow preserves contrast without swallowing the Korean shapes.
        for dx, dy in ((0, 3), (3, 3)):
            hi_draw.text(
                (x + dx * scale, baseline_y + dy * scale),
                line,
                font=hi_font,
                fill=(0, 0, 0, 180),
            )
        hi_draw.text(
            (x, baseline_y),
            line,
            font=hi_font,
            fill=WHITE + (255,),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 255),
        )
        hi_draw.text((x, baseline_y), line, font=hi_font, fill=WHITE + (255,))
        y += line_step

    subtitle = layer.resize((W, band_h), Image.Resampling.LANCZOS)
    draw._image.paste(subtitle, (0, band_top), subtitle)


def active_subtitle(scene: dict, frame: int) -> str:
    for subtitle in scene["subtitles"]:
        start = int(subtitle["startFrame"])
        end = start + int(subtitle["durationFrames"])
        if start <= frame < end:
            return subtitle["text"]
    return scene["subtitles"][-1]["text"] if scene["subtitles"] else ""


def render_scene(scene: dict, idx: int) -> Path:
    frames = int(scene["durationFrames"])
    bg_rel = scene.get("backgroundImage") or scene.get("card")
    bg_path = REMOTION_PUBLIC / bg_rel
    audio_path = REMOTION_PUBLIC / scene["audio"]
    scene_out = TMP_DIR / f"scene_{idx:03d}.mp4"
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        f"{frames / FPS:.3f}",
        str(scene_out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    image_y, image_h = 360, 535
    prepared_bg = prepare_smooth_background(bg_path, (W, image_h), 1.04)
    headline = HEADLINES.get(scene["objective"]) or (scene.get("visualPrompt", {}).get("on_screen_emphasis") or [])[:3]
    if not headline:
        headline = [scene["subtitles"][0]["text"] if scene["subtitles"] else ""]
    for frame_idx in range(frames):
        progress = frame_idx / max(1, frames - 1)
        canvas = Image.new("RGB", (W, H), BLACK)
        draw = ImageDraw.Draw(canvas)

        img = crop_smooth_background(prepared_bg, (W, image_h), 0.5)
        canvas.paste(img, (0, image_y))
        draw.rectangle((0, image_y, W, image_y + 4), fill=(18, 18, 18))
        draw.rectangle((0, image_y + image_h - 4, W, image_y + image_h), fill=(18, 18, 18))

        draw_reference_title_box(draw, headline)

        sub = active_subtitle(scene, frame_idx)
        draw_reference_subtitle_box(draw, sub)

        bar_w = int((W - 96) * max(0.04, progress))
        draw.rounded_rectangle((48, H - 34, W - 48, H - 28), radius=99, fill=(48, 48, 48))
        draw.rounded_rectangle((48, H - 34, 48 + bar_w, H - 28), radius=99, fill=YELLOW)

        proc.stdin.write(canvas.tobytes())

    proc.stdin.close()
    code = proc.wait()
    if code:
        raise RuntimeError(f"ffmpeg scene render failed: {scene_out}")
    return scene_out


def main() -> None:
    job = json.loads(JOB_PATH.read_text(encoding="utf-8"))
    parts = [render_scene(scene, idx) for idx, scene in enumerate(job["scenes"], start=1)]
    concat_file = TMP_DIR / "concat.txt"
    concat_file.write_text("".join(f"file '{part.resolve()}'\n" for part in parts), encoding="utf-8")
    out = OUT_DIR / f"{job['scriptId']}_black_band_subtitle_css_720p.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )
    print(out)


if __name__ == "__main__":
    main()
