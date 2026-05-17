from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, VideoFileClip, CompositeVideoClip, concatenate_videoclips

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

sys.path.append(str(Path(__file__).resolve().parents[1] / "tts"))
try:
    from elevenlabs_tts import synthesize as elevenlabs_synthesize
except Exception:  # pragma: no cover
    elevenlabs_synthesize = None
try:
    from gpt_sovits_tts import synthesize as gpt_sovits_synthesize
except Exception:  # pragma: no cover
    gpt_sovits_synthesize = None
try:
    from edge_tts_local import synthesize as edge_tts_local_synthesize
except Exception:  # pragma: no cover
    edge_tts_local_synthesize = None

ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
SCENES_DIR = ROOT / DATA_SUBDIR / "scenes"
ASSETS_DIR = ROOT / DATA_SUBDIR / "assets"
RENDERS_DIR = ROOT / DATA_SUBDIR / "renders"
TEMP_DIR = RENDERS_DIR / "temp"
PROVIDERS_CONFIG_PATH = ROOT / "config" / "providers.yaml"

WIDTH = int(os.getenv("MEDIA_AGENT_WIDTH", "1280"))
HEIGHT = int(os.getenv("MEDIA_AGENT_HEIGHT", "720"))
FPS = int(os.getenv("MEDIA_AGENT_FPS", "30"))
TEXT = (245, 248, 255)
ACCENT = (90, 180, 255)


def load_providers_config() -> dict:
    if yaml is None or not PROVIDERS_CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(PROVIDERS_CONFIG_PATH.read_text(encoding="utf-8")) or {}


PROVIDERS = load_providers_config()
TTS_CONFIG = PROVIDERS.get("tts", {})
TTS_LOCAL = dict(TTS_CONFIG.get("local", {}) or {})
if os.getenv("MEDIA_AGENT_TTS_RATE"):
    TTS_LOCAL["rate"] = os.getenv("MEDIA_AGENT_TTS_RATE")
if os.getenv("MEDIA_AGENT_TTS_PITCH"):
    TTS_LOCAL["pitch"] = os.getenv("MEDIA_AGENT_TTS_PITCH")
TTS_FALLBACK = TTS_CONFIG.get("fallback", {})
RENDER_CONFIG = PROVIDERS.get("render", {})
DEFAULT_MALE_VOICE_CANDIDATES = TTS_FALLBACK.get("voice_candidates") or ["Junwoo", "Jiho", "Minho", "Thomas", "Daniel"]
FINAL_FALLBACK_VOICE = TTS_FALLBACK.get("final_fallback_voice", "Yuna")
SUBTITLE_BOX_RATIO = float(RENDER_CONFIG.get("subtitle_box_ratio", 0.75))
SUBTITLE_FONT_SCALE = float(os.getenv("MEDIA_AGENT_SUBTITLE_FONT_SCALE", "1.0"))
SUBTITLE_RAISE_RATIO = float(os.getenv("MEDIA_AGENT_SUBTITLE_RAISE_RATIO", "0.0"))
SUBTITLE_MAX_LINES = int(os.getenv("MEDIA_AGENT_SUBTITLE_MAX_LINES", "1"))
TITLE_Y_RATIO = float(os.getenv("MEDIA_AGENT_TITLE_Y_RATIO", "0.18"))
SUBTITLE_CENTER_RATIO = float(os.getenv("MEDIA_AGENT_SUBTITLE_CENTER_RATIO", "0.50"))


def latest_scenes_path() -> Path:
    explicit = os.getenv("MEDIA_AGENT_SCENES_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = ROOT / explicit
        if not path.exists():
            raise FileNotFoundError(f"scenes file not found: {path}")
        return path
    files = sorted(SCENES_DIR.glob("*_scenes.json"))
    if not files:
        raise FileNotFoundError("scenes file not found")
    return files[-1]


def load_asset_plan() -> dict:
    explicit = os.getenv("MEDIA_AGENT_ASSET_PLAN_FILE", "").strip()
    path = Path(explicit) if explicit else ASSETS_DIR / "asset_plan_latest.json"
    if explicit and not path.is_absolute():
        path = ROOT / explicit
    if not path.exists():
        return {}
    items = json.loads(path.read_text())
    return {item.get("scene_id"): item for item in items}


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_scene_card(scene: dict, output_path: Path) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (13, 18, 26, 72))
    draw_bg = ImageDraw.Draw(image)
    for y in range(0, HEIGHT, 6):
        ratio = y / max(1, HEIGHT)
        shade = int(13 + ratio * 22)
        draw_bg.rectangle((0, y, WIDTH, y + 6), fill=(shade, int(18 + ratio * 26), int(26 + ratio * 34), 64))
    grid_color = (255, 255, 255, 8)
    for x in range(0, WIDTH, max(90, WIDTH // 8)):
        draw_bg.line((x, 0, x, HEIGHT), fill=grid_color, width=1)
    for y in range(0, HEIGHT, max(120, HEIGHT // 10)):
        draw_bg.line((0, y, WIDTH, y), fill=grid_color, width=1)
    chart_y = int(HEIGHT * 0.68)
    points = [
        (int(WIDTH * 0.10), chart_y + int(HEIGHT * 0.04)),
        (int(WIDTH * 0.25), chart_y + int(HEIGHT * 0.02)),
        (int(WIDTH * 0.40), chart_y + int(HEIGHT * 0.05)),
        (int(WIDTH * 0.56), chart_y - int(HEIGHT * 0.01)),
        (int(WIDTH * 0.72), chart_y - int(HEIGHT * 0.05)),
        (int(WIDTH * 0.90), chart_y - int(HEIGHT * 0.10)),
    ]
    chart_color = (98, 205, 161, 76)
    if scene.get("objective") == "risk":
        chart_color = (235, 88, 88, 82)
    draw_bg.line(points, fill=chart_color, width=max(4, WIDTH // 90), joint="curve")
    for x, y in points:
        r = max(4, WIDTH // 120)
        draw_bg.ellipse((x - r, y - r, x + r, y + r), fill=chart_color)

    if scene.get("objective") == "close":
        image = Image.new("RGBA", (WIDTH, HEIGHT), (18, 30, 43, 78))
        draw_bg = ImageDraw.Draw(image)
        for y in range(0, HEIGHT, 24):
            shade = min(70, 18 + int(y / HEIGHT * 34))
            draw_bg.rectangle((0, y, WIDTH, y + 24), fill=(shade, 42 + int(y / HEIGHT * 34), 54 + int(y / HEIGHT * 30), 70))
        grid_color = (255, 255, 255, 10)
        for x in range(90, WIDTH, 180):
            draw_bg.line((x, 0, x, HEIGHT), fill=grid_color, width=1)
        for y in range(180, HEIGHT, 180):
            draw_bg.line((0, y, WIDTH, y), fill=grid_color, width=1)
        chart = [
            (130, int(HEIGHT * 0.72)),
            (270, int(HEIGHT * 0.68)),
            (420, int(HEIGHT * 0.70)),
            (575, int(HEIGHT * 0.62)),
            (730, int(HEIGHT * 0.58)),
            (900, int(HEIGHT * 0.50)),
        ]
        draw_bg.line(chart, fill=(98, 205, 161, 92), width=10, joint="curve")
        for point in chart:
            x, y = point
            draw_bg.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(98, 205, 161, 110))

    draw = ImageDraw.Draw(image)
    badge = {
        "hook": "QUESTION",
        "background": "CONTEXT",
        "evidence": "DATA",
        "etf_link": "STRUCTURE",
        "mechanism": "STRUCTURE",
        "risk": "RISK",
        "close": "SUMMARY",
    }.get(scene.get("objective"), "BRIEF")
    badge_font = load_font(max(18, WIDTH // 34))
    badge_bbox = draw.textbbox((0, 0), badge, font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0] + 34
    badge_h = badge_bbox[3] - badge_bbox[1] + 18
    badge_x = int(WIDTH * 0.08)
    badge_y = int(HEIGHT * 0.12)
    badge_fill = (35, 82, 122, 190) if scene.get("objective") != "risk" else (120, 35, 42, 190)
    draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), radius=12, fill=badge_fill)
    draw.text((badge_x + 17, badge_y + 8), badge, font=badge_font, fill=(235, 242, 250, 255))

    title_font_size = 64 if scene.get("objective") == "hook" else 52
    title_font_size = max(34, int(title_font_size * (WIDTH / 1080)))
    title_font = load_font(title_font_size)

    title = scene.get("title_text") or scene.get("subtitle_text", "")
    max_width = WIDTH - 140
    while title_font_size > 28:
        title_lines = wrap_text(draw, title, title_font, max_width)
        if len(title_lines) <= 3:
            break
        title_font_size -= 2
        title_font = load_font(title_font_size)

    title_lines = wrap_text(draw, title, title_font, max_width)[:3]
    line_height = int(title_font_size * 1.18)
    panel_pad = max(24, WIDTH // 26)
    panel_x1 = int(WIDTH * 0.07)
    panel_x2 = int(WIDTH * 0.93)
    panel_y1 = int(HEIGHT * 0.18)
    panel_y2 = int(HEIGHT * 0.44)
    panel_fill = (7, 13, 22, 176) if scene.get("objective") != "risk" else (32, 8, 12, 182)
    panel_outline = (120, 190, 255, 80) if scene.get("objective") != "risk" else (255, 110, 110, 90)
    draw.rounded_rectangle((panel_x1, panel_y1, panel_x2, panel_y2), radius=22, fill=panel_fill, outline=panel_outline, width=2)

    y = panel_y1 + panel_pad
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font, stroke_width=4)
        line_width = bbox[2] - bbox[0]
        x = (WIDTH - line_width) // 2
        draw.text((x, y), line, font=title_font, fill=TEXT, stroke_width=4, stroke_fill=(0, 0, 0))
        y += line_height

    objective = scene.get("objective")
    if objective in {"hook", "background", "evidence", "etf_link", "risk", "close"}:
        cue_map = {
            "hook": [scene.get("subtitle_text", "")[:18] or "핵심 질문"],
            "background": ["배당의 질", "지속가능성"],
            "evidence": ["총보수 0.06%", "비용 체크"],
            "etf_link": ["재무구조", "현금흐름"],
            "risk": ["월배당 아님", "원금 변동"],
            "close": ["배당의 질", "성장", "신중한 판단"],
        }
        cue_font = load_font(max(24, int((36 if objective != "close" else 42) * (WIDTH / 1080))))
        cue_items = cue_map.get(objective, [])
        cue_y = int(HEIGHT * (0.54 if objective != "close" else 0.44))
        box_width = int(WIDTH * (0.78 if objective != "close" else 0.82))
        box_height = 92 if objective != "close" else 118
        for cue in cue_items:
            x1 = (WIDTH - box_width) // 2
            x2 = x1 + box_width
            y1 = cue_y
            y2 = cue_y + box_height
            fill = (9, 20, 30, 172) if objective != "close" else (244, 248, 255, 30)
            outline = (98, 205, 161, 200) if objective == "close" else (90, 180, 255, 185)
            draw.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=fill, outline=outline, width=3)
            bbox = draw.textbbox((0, 0), cue, font=cue_font, stroke_width=2)
            text_x = (WIDTH - (bbox[2] - bbox[0])) // 2
            text_y = y1 + ((box_height - (bbox[3] - bbox[1])) // 2) - 4
            draw.text((text_x, text_y), cue, font=cue_font, fill=TEXT, stroke_width=2, stroke_fill=(0, 0, 0))
            cue_y += box_height + 26

    image.save(output_path)


def split_subtitle_lines(text: str, max_chars: int = 40) -> list[str]:
    cleaned = " ".join(str(text).split())
    coarse = [p.strip() for p in re.split(r"(?<=[.!?])\s+|(?<=[다요죠니다])\s+|(?<=,)\s+", cleaned) if p.strip()]
    lines = []
    for part in coarse:
        if len(part) <= max_chars:
            lines.append(part)
            continue
        chunks = [c.strip() for c in re.split(r"[,·]", part) if c.strip()]
        for chunk in chunks:
            if len(chunk) <= max_chars:
                lines.append(chunk)
                continue
            words = chunk.split()
            current = ""
            for word in words:
                trial = word if not current else f"{current} {word}"
                if len(trial) <= max_chars:
                    current = trial
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
    return lines or [cleaned[:max_chars]]


def subtitle_segments(text: str, duration: float) -> list[tuple[str, float, float]]:
    lines = split_subtitle_lines(text)
    total_chars = sum(max(1, len(line.replace(" ", ""))) for line in lines)
    cursor = 0.0
    segments = []
    for line in lines:
        weight = max(1, len(line.replace(" ", ""))) / total_chars
        seg_duration = max(0.9, duration * weight)
        end = min(duration, cursor + seg_duration)
        segments.append((line, cursor, end))
        cursor = end
    if segments:
        line, start, _ = segments[-1]
        segments[-1] = (line, start, duration)
    return segments


def render_subtitle_image(text: str, output_path: Path) -> int:
    subtitle_box_width = int(WIDTH * SUBTITLE_BOX_RATIO)
    max_text_width = subtitle_box_width - 100

    font_size = max(24, int(40 * SUBTITLE_FONT_SCALE))
    font = load_font(font_size)
    probe = Image.new("RGBA", (WIDTH, 300), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)

    def wrap_pixels(raw: str, current_font) -> list[str]:
        words = str(raw).split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if probe_draw.textbbox((0, 0), trial, font=current_font)[2] <= max_text_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    lines = wrap_pixels(text, font)
    while font_size > 24 and len(lines) > SUBTITLE_MAX_LINES:
        font_size -= 2
        font = load_font(font_size)
        lines = wrap_pixels(text, font)

    if len(lines) > SUBTITLE_MAX_LINES:
        lines = lines[:SUBTITLE_MAX_LINES]
        if len(lines[-1]) > 2:
            lines[-1] = lines[-1][:-1] + "…"

    line_boxes = [probe_draw.textbbox((0, 0), line, font=font, stroke_width=4) for line in lines]
    line_heights = [(bbox[3] - bbox[1]) for bbox in line_boxes]
    content_height = sum(line_heights) + max(0, (len(lines) - 1) * 8)
    vertical_padding = max(20, int(content_height * 0.10))
    image_height = max(140, content_height + (vertical_padding * 2))

    image = Image.new("RGBA", (WIDTH, image_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    y = vertical_padding
    for line, bbox, line_height in zip(lines, line_boxes, line_heights):
        line_width = bbox[2] - bbox[0]
        x = (WIDTH - line_width) // 2
        draw.text((x, y), line, font=font, fill=TEXT, stroke_width=4, stroke_fill=(0, 0, 0))
        y += line_height + 8

    image.save(output_path)
    return image_height


def download_asset(url: str, output_path: Path) -> Path:
    if str(url).startswith("file://"):
        src = Path(str(url)[7:])
        output_path.write_bytes(src.read_bytes())
        return output_path
    import requests
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def _loop_video_to_duration(bg: VideoFileClip, duration: float):
    if bg.duration >= duration:
        return bg.subclipped(0, duration).resized((WIDTH, HEIGHT))

    loops = []
    remaining = duration
    while remaining > 0:
        part = bg.subclipped(0, min(bg.duration, remaining)).resized((WIDTH, HEIGHT))
        loops.append(part)
        remaining -= part.duration
    return concatenate_videoclips(loops, method="compose").with_duration(duration)


def prepare_photo_background(source_path: Path, output_path: Path) -> Path:
    image = Image.open(source_path).convert("RGB")
    src_w, src_h = image.size
    scale = max(WIDTH / src_w, HEIGHT / src_h)
    resized = image.resize((int(src_w * scale) + 1, int(src_h * scale) + 1), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - WIDTH) // 2)
    top = max(0, (resized.height - HEIGHT) // 2)
    cropped = resized.crop((left, top, left + WIDTH, top + HEIGHT))
    cropped.save(output_path, quality=92)
    return output_path


def build_visual_clip(scene: dict, duration: float, image_path: Path, asset_plan: dict):
    scene_assets = asset_plan.get(scene.get("scene_id"), {})
    selected_assets = scene_assets.get("selected_assets", [])
    stock_video = next((a for a in selected_assets if a.get("asset_type") == "stock_video" and a.get("url")), None)
    stock_photo = next((a for a in selected_assets if a.get("asset_type") == "stock_photo" and a.get("url")), None)

    layers = []
    if stock_video:
        local_video = TEMP_DIR / f"{scene['scene_id']}_bg.mp4"
        if not local_video.exists():
            download_asset(stock_video["url"], local_video)
        bg = VideoFileClip(str(local_video)).without_audio()
        if bg.duration < duration:
            print(f"info=looping_stock_video scene={scene.get('scene_id')} clip={bg.duration:.2f}s target={duration:.2f}s")
        layers.append(_loop_video_to_duration(bg, duration))
    elif stock_photo:
        suffix = Path(str(stock_photo.get("url", ""))).suffix
        local_photo = TEMP_DIR / f"{scene['scene_id']}_stock_photo{suffix if suffix else '.jpg'}"
        cover_photo = TEMP_DIR / f"{scene['scene_id']}_stock_photo_cover.jpg"
        if not local_photo.exists():
            download_asset(stock_photo["url"], local_photo)
        if not cover_photo.exists():
            prepare_photo_background(local_photo, cover_photo)
        layers.append(ImageClip(str(cover_photo)).with_duration(duration))
    else:
        layers.append(ImageClip(str(image_path)).with_duration(duration))

    layers.append(ImageClip(str(image_path)).with_duration(duration).with_position((0, 0)))

    for idx, (line, start, end) in enumerate(subtitle_segments(scene.get("narration", ""), duration), start=1):
        subtitle_path = TEMP_DIR / f"{scene['scene_id']}_sub_{idx:02d}.png"
        subtitle_height = render_subtitle_image(line, subtitle_path)
        subtitle_y = max(0, int((HEIGHT * SUBTITLE_CENTER_RATIO) - (subtitle_height / 2)))
        layers.append(
            ImageClip(str(subtitle_path))
            .with_start(start)
            .with_duration(max(0.1, end - start))
            .with_position((0, subtitle_y))
        )

    return CompositeVideoClip(layers, size=(WIDTH, HEIGHT)).with_duration(duration)


def _available_macos_voices() -> list[str]:
    try:
        result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    except Exception:
        return []
    voices = []
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if parts:
            voices.append(parts[0])
    return voices


def _contains_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in str(text))


def _pick_fallback_voice(text: str) -> str:
    available = set(_available_macos_voices())
    if _contains_hangul(text):
        if FINAL_FALLBACK_VOICE in available:
            return FINAL_FALLBACK_VOICE
    configured_primary = TTS_FALLBACK.get("voice_name")
    if configured_primary and configured_primary in available:
        return configured_primary
    for voice in DEFAULT_MALE_VOICE_CANDIDATES:
        if voice in available:
            return voice
    return FINAL_FALLBACK_VOICE


def normalize_tts_text(text: str) -> str:
    normalized = " ".join(str(text).split())
    replacements = {
        'ETF': '이티에프',
        'etf': '이티에프',
        'AI': '에이아이',
        'ai': '에이아이',
        'ETF로': '이티에프로',
        'ETF를': '이티에프를',
        'ETF는': '이티에프는',
        'ETF가': '이티에프가',
        'SDIV': '에스디아이브이',
        'JEPI': '제이이피아이',
        'JEPQ': '제이이피큐',
        'SCHD': '에스씨에이치디',
        'QQQ': '큐큐큐',
        'S&P': '에스 앤 피',
    }
    for src, dst in sorted(replacements.items(), key=lambda x: -len(x[0])):
        normalized = normalized.replace(src, dst)
    return normalized


def synthesize_audio(text: str, output_path: Path) -> Path:
    spoken_text = normalize_tts_text(text)
    if elevenlabs_synthesize is not None:
        try:
            target = output_path.with_suffix(".mp3")
            elevenlabs_synthesize(spoken_text, target)
            return target
        except Exception as e:
            print(f"warning=elevenlabs_failed reason={type(e).__name__}:{e}")

    if str(TTS_LOCAL.get("provider", "")).strip().lower() == "edge_tts" and edge_tts_local_synthesize is not None:
        try:
            target = output_path.with_suffix(".mp3")
            edge_tts_local_synthesize(spoken_text, target, TTS_LOCAL)
            print("info=using_edge_tts_local")
            return target
        except Exception as e:
            print(f"warning=edge_tts_failed reason={type(e).__name__}:{e}")

    if str(TTS_LOCAL.get("provider", "")).strip().lower() == "gpt_sovits" and gpt_sovits_synthesize is not None:
        try:
            target = output_path.with_suffix(".wav")
            gpt_sovits_synthesize(spoken_text, target, TTS_LOCAL)
            print("info=using_gpt_sovits")
            return target
        except Exception as e:
            print(f"warning=gpt_sovits_failed reason={type(e).__name__}:{e}")

    fallback_voice = _pick_fallback_voice(spoken_text)
    print(f"warning=using_macos_say voice={fallback_voice}")
    subprocess.run(["say", "-v", fallback_voice, "-o", str(output_path), spoken_text], check=True)
    return output_path


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return max(1.0, float(result.stdout.strip()))


def write_srt(scenes: list[dict], durations: list[float], output_path: Path) -> None:
    def fmt(seconds: float) -> str:
        ms = int((seconds % 1) * 1000)
        total = int(seconds)
        s = total % 60
        m = (total // 60) % 60
        h = total // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    current = 0.0
    counter = 1
    for scene, duration in zip(scenes, durations):
        for text, local_start, local_end in subtitle_segments(scene.get("narration", ""), duration):
            start = current + local_start
            end = current + local_end
            lines.extend([str(counter), f"{fmt(start)} --> {fmt(end)}", text, ""])
            counter += 1
        current += duration
    output_path.write_text("\n".join(lines))


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text())
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    clips = []
    durations = []
    asset_plan = load_asset_plan()
    script_id = scenes[0]["script_id"] if scenes else datetime.now().strftime("%Y%m%d_%H%M%S")

    for idx, scene in enumerate(scenes, start=1):
        image_path = TEMP_DIR / f"{script_id}_scene_{idx:03d}.png"
        audio_path = TEMP_DIR / f"{script_id}_scene_{idx:03d}.aiff"
        render_scene_card(scene, image_path)
        effective_audio_path = synthesize_audio(scene.get("narration", ""), audio_path)
        duration = audio_duration(effective_audio_path) + 0.3
        durations.append(duration)

        audio_clip = AudioFileClip(str(effective_audio_path))
        visual_clip = build_visual_clip(scene, duration, image_path, asset_plan).with_audio(audio_clip)
        clips.append(visual_clip)

    final = concatenate_videoclips(clips, method="compose")
    video_path = RENDERS_DIR / f"{script_id}.mp4"
    final.write_videofile(str(video_path), fps=FPS, codec="libx264", preset="ultrafast", audio_codec="aac", logger=None)
    final.close()
    for clip in clips:
        clip.close()

    srt_path = RENDERS_DIR / f"{script_id}.srt"
    write_srt(scenes, durations, srt_path)

    render_job = {
        "render_job_id": f"rnd_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "succeeded",
        "script_id": script_id,
        "scene_count": len(scenes),
        "output_spec": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "container": "mp4",
        },
        "artifact_urls": [str(video_path), str(srt_path)],
        "notes": "pexels background + synced single-line subtitles + tts",
    }
    output = RENDERS_DIR / f"{render_job['render_job_id']}.json"
    output.write_text(json.dumps(render_job, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    print(f"video={video_path}")
    print(f"captions={srt_path}")
    return output


if __name__ == "__main__":
    run()
