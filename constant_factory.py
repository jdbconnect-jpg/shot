import asyncio
import json
import logging
import os
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from random import choice, sample
from pathlib import Path
from typing import List, Optional

import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter
import PIL.ImageFont
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

warnings.filterwarnings("ignore")
logging.getLogger("google.genai").setLevel(logging.ERROR)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

load_dotenv()


@dataclass
class AppConfig:
    gemini_api_key: str
    workspace: Path = Path(__file__).resolve().parent
    rss_url: str = "https://news.google.com/rss/search?q=국내+증시+경제+전망+ETF&hl=ko&gl=KR&ceid=KR:ko"
    min_duration_sec: int = 30
    max_duration_sec: int = 60
    scene_count: int = 5
    voice: str = "ko-KR-SunHiNeural"
    width: int = 720
    height: int = 1280
    privacy_status: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")

    @property
    def temp_dir(self) -> Path:
        return self.workspace / "temp_assets"

    @property
    def output_dir(self) -> Path:
        return self.workspace / "final_shorts"

    @property
    def assets_dir(self) -> Path:
        return self.workspace / "assets"

    @property
    def analytics_dir(self) -> Path:
        return self.workspace / "analytics"

    @classmethod
    def from_env(cls) -> "AppConfig":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY가 필요합니다. .env를 채워주세요.")
        return cls(gemini_api_key=api_key)


class FactoryReport:
    def __init__(self):
        self.logs = []

    def add(self, step, status, detail):
        self.logs.append({"step": step, "status": status, "detail": detail})

    def print_summary(self):
        print("\n" + "=" * 60)
        print("📊 고양이 공장 가동 상세 리포트")
        print("-" * 60)
        for log in self.logs:
            mark = "✅" if log["status"] == "SUCCESS" else "🚨" if log["status"] == "WARNING" else "❌"
            print(f"{mark} [{log['step']}] {log['detail']}")
        print("=" * 60 + "\n")


REPORT = FactoryReport()


class EconomyAnalyst:
    def __init__(self, client: genai.Client, config: AppConfig):
        self.client = client
        self.config = config
        self.models = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite-preview",
        ]
        self.format_profiles = {
            "market": {
                "label": "오늘의 ETF 브리핑",
                "angle": "오늘 시장에서 특정 ETF가 왜 언급되는지 뉴스와 섹터 흐름 중심으로 설명",
                "cta": "이 흐름 계속 볼 거면 팔로우하고, 다음 브리핑에서 다른 섹터도 같이 보세요.",
            },
            "issue": {
                "label": "이슈로 보는 ETF",
                "angle": "하나의 핵심 이슈가 어떤 ETF로 연결되는지 설명",
                "cta": "이 이슈가 이어지는지 다음 브리핑에서 다시 체크해볼게요.",
            },
            "beginner": {
                "label": "초보자용 ETF 한 줄 정리",
                "angle": "초보자도 이해할 수 있게 ETF 성격과 보는 포인트를 쉽게 설명",
                "cta": "ETF 기본 개념은 롱폼에서 더 자세히 다루니 같이 이어서 보세요.",
            },
        }

    def execute(self):
        print("🌐 [Analyst] 실시간 경제 뉴스 분석 중...")
        headlines = self._fetch_news()
        if not headlines:
            return None
        format_key, format_profile = self._pick_format_profile()
        data = self._create_script(headlines, format_key, format_profile)
        if isinstance(data, dict):
            data["content_format"] = format_key
            data["format_label"] = format_profile["label"]
        return data

    def _fetch_news(self) -> Optional[List[str]]:
        try:
            res = requests.get(self.config.rss_url, timeout=15)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            headlines = [
                item.find("title").text.strip()
                for item in root.findall(".//item")[:12]
                if item.find("title") is not None and item.find("title").text
            ]
            REPORT.add("News", "SUCCESS", f"{len(headlines)}개 수집 완료")
            return headlines
        except Exception as e:
            REPORT.add("News", "ERROR", f"수집 실패: {e}")
            return None

    def _create_script(self, headlines: List[str], format_key: str, format_profile: dict):
        prompt = f"""
당신은 '뉴스로 읽는 ETF 30초 브리핑' 채널의 작가입니다.
역할은 투자 추천인이 아니라, 한국 경제/증시 뉴스를 바탕으로 특정 ETF가 왜 언급되는지 짧고 신뢰감 있게 설명하는 브리퍼입니다.
캐릭터 톤은 '귀엽지만 냉정한 고양이 ETF 브리퍼'이며, 말투는 짧고 단정해야 합니다.

이번 영상 포맷:
- format_key: {format_key}
- format_label: {format_profile['label']}
- format_angle: {format_profile['angle']}
- ending_cta: {format_profile['cta']}

뉴스 리스트:
{json.dumps(headlines, ensure_ascii=False)}

출력 규칙:
- JSON 객체 하나만 출력
- scenes: 길이 {self.config.scene_count}인 리스트
- 각 scene 항목은 {{"text": "..."}} 형태
- 각 scene 문장은 1~2문장, 초보자도 이해할 수 있게 쉽게 작성
- 전체 나레이션 분량은 30~45초 중심으로 간결하게 작성
- target_etf: 오늘 뉴스 흐름상 '주목할 ETF' 1개
- title: 자극적 추천형 제목 말고, 뉴스/이유/섹터 중심의 제목 1개
- description: 업로드용 설명 한 단락
- tags: 문자열 리스트 5~8개
- chalk_summary: 칠판에 크게 쓸 핵심 요약 {self.config.scene_count}개 리스트
- viewer_hook: 시청자 시선을 끄는 짧은 한 줄
- market_reason: 왜 오늘 이 ETF가 언급되는지 한 줄 설명
- cta: 마지막에 넣을 짧은 문장 하나
- brand_opening: 아래 3개 중 하나의 톤을 반영한 짧은 시작 문장
  1) 오늘 뉴스에서 ETF 포인트만 빠르게 볼게요.
  2) 오늘 시장에서 자금이 어디 붙는지 같이 볼게요.
  3) 오를 이유보다, 왜 언급되는지부터 짚어볼게요.
- viewer_hook는 18자 내외로 아주 짧고 강하게 작성할 것
- chalk_summary[0]은 첫 프레임용으로 2줄 이내, 각 줄 10자 안쪽으로 압축할 것
- 첫 scene은 훅이 아니라 '오늘 왜 이 ETF가 언급되는지'를 바로 설명
- 마지막 scene은 format_angle과 ending_cta에 맞춰 마무리
- 절대 수익 보장, 폭등 확신, 매수 유도, 과장된 표현 사용 금지
- 'ETF추천', '무조건', '지금 사야', '폭등', '터진다' 같은 표현은 피할 것
- tags에는 한국 투자자 검색 키워드를 반영하되, 브리핑/시장/섹터 성격을 우선할 것
- description에는 '본 영상은 투자 권유가 아닌 뉴스 기반 브리핑'이라는 취지를 자연스럽게 포함할 것
- title은 숫자/비교/이유 중 하나가 드러나게 더 구체적으로 작성할 것
- title 길이는 32자 안쪽 중심, 군더더기 수식어를 줄일 것
- cta는 아래 셋 중 하나 성격으로 작성할 것: 팔로우 유도 / 롱폼 유도 / 다음 브리핑 예고
- description 마지막에는 롱폼 또는 뉴스레터 중 하나로만 연결되게 자연스럽게 마무리할 것
- tags는 8개 안쪽 핵심 키워드 위주로 작성할 것
"""
        response_config = types.GenerateContentConfig(response_mime_type="application/json")

        for model in self.models:
            try:
                print(f"🔄 [Analyst] {model} 시도 중...")
                res = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=response_config,
                )
                data = json.loads(res.text)
                if self._validate_script(data):
                    REPORT.add("Analyst", "SUCCESS", f"대본 생성 완료 ({model})")
                    return data
            except Exception as e:
                REPORT.add("Analyst", "WARNING", f"{model} 실패: {str(e)[:80]}")
        REPORT.add("Analyst", "ERROR", "모든 지정 모델 응답 실패")
        return None

    def _validate_script(self, data: dict) -> bool:
        return (
            isinstance(data, dict)
            and isinstance(data.get("scenes"), list)
            and len(data["scenes"]) == self.config.scene_count
            and isinstance(data.get("target_etf"), str)
            and isinstance(data.get("title"), str)
        )

    def _pick_format_profile(self):
        key = choice(list(self.format_profiles.keys()))
        return key, self.format_profiles[key]


class AudioProducer:
    def __init__(self, config: AppConfig):
        self.voice = config.voice
        self.config = config

    def execute(self, scenes):
        print("🎙️ [Audio] 나레이션 합성 중...")
        cleaned_scenes = [self._scene_text(scene) for scene in scenes]
        path = self.config.temp_dir / "voice.mp3"
        try:
            asyncio.run(self._synth(cleaned_scenes, path))
            REPORT.add("Audio", "SUCCESS", "음성 합성 완료")
            return AudioFileClip(str(path))
        except Exception as e:
            REPORT.add("Audio", "ERROR", f"음성 합성 실패: {e}")
            return None

    async def _synth(self, scenes, path: Path):
        import edge_tts

        await edge_tts.Communicate(" ".join(scenes), self.voice).save(str(path))

    @staticmethod
    def _scene_text(scene) -> str:
        if isinstance(scene, dict):
            return str(scene.get("text", "")).strip()
        return str(scene).strip()


class TemplateArtist:
    def __init__(self, config: AppConfig):
        self.config = config
        self.bg_color = (18, 34, 54)
        self.board_color = (160, 177, 196, 120)
        self.board_frame = (220, 230, 244, 160)
        self.accent = (255, 213, 107)
        self.accent_soft = (222, 236, 255)
        self.text_dark = (24, 28, 36)
        self.white = (255, 255, 255)
        self.shadow = (0, 0, 0, 92)
        self.font = self._resolve_font_path(bold=False)
        self.bold_font = self._resolve_font_path(bold=True)
        self.template_scene_order = list(range(10))
        self.template_grid_path = self._resolve_template_grid_path()
        self._template_panels_cache = None
        self.current_scene_order: List[int] = []

    def execute(self, script_data: dict) -> List[str]:
        self._refresh_scene_order()
        if self.template_grid_path:
            print(f"🎨 [Artist] 첨부 템플릿 이미지 기반 5컷 장면 생성 중... ({self.template_grid_path.name} / order={self.current_scene_order})")
        else:
            print("🎨 [Artist] 템플릿형 고양이 칠판 장면 생성 중...")
        scene_paths = []
        chalk_summaries = script_data.get("chalk_summary") or [""] * self.config.scene_count

        viewer_hook = self._compress_hook(script_data.get("viewer_hook") or script_data.get("brand_opening") or "오늘 뉴스에서 ETF 포인트만 빠르게 볼게요.")
        market_reason = script_data.get("market_reason", "오늘 시장에서 언급된 이유를 빠르게 정리합니다.")

        for idx in range(self.config.scene_count):
            scene_text = AudioProducer._scene_text(script_data["scenes"][idx])
            chalk_text = chalk_summaries[idx] if idx < len(chalk_summaries) else ""
            out = self.config.temp_dir / f"template_scene_{idx}.png"
            summarized_scene = self._summarize_scene_caption(scene_text)
            self._render_scene(
                out,
                idx,
                summarized_scene,
                chalk_text,
                script_data.get("target_etf", "ETF"),
                viewer_hook,
                market_reason,
            )
            scene_paths.append(str(out))
            REPORT.add(f"Image-{idx + 1}", "SUCCESS", "템플릿 장면 생성 완료")

        if scene_paths:
            self._create_scene_preview(scene_paths)

        return scene_paths

    def _render_scene(self, out: Path, idx: int, script_text: str, chalk_text: str, target_etf: str, viewer_hook: str, market_reason: str):
        if self.template_grid_path:
            self._render_scene_from_template_grid(out, idx, script_text, chalk_text, target_etf, viewer_hook, market_reason)
            return

        canvas = PIL.Image.new("RGBA", (self.config.width, self.config.height), self.bg_color)
        is_final_scene = idx == self.config.scene_count - 1
        is_opening_scene = idx == 0
        scene_theme = self._scene_theme(idx, script_text, is_final_scene=is_final_scene, is_opening_scene=is_opening_scene)
        self._draw_background(canvas)
        self._draw_board(canvas, idx, chalk_text, target_etf, is_final_scene=is_final_scene, is_opening_scene=is_opening_scene)
        self._draw_cat_teacher(canvas, scene_theme)
        self._draw_header(canvas, idx, viewer_hook, market_reason, is_final_scene=is_final_scene, is_opening_scene=is_opening_scene)
        self._draw_caption(canvas, script_text, is_final_scene=is_final_scene)
        self._draw_decorations(canvas)
        self._draw_thumbnail_badge(canvas, scene_theme, target_etf, idx=idx, is_final_scene=is_final_scene)
        canvas.convert("RGB").save(out, quality=95)

    def _resolve_template_grid_path(self) -> Optional[Path]:
        candidates = []

        env_path = os.getenv("SHORTS_TEMPLATE_GRID_PATH", "").strip()
        if env_path:
            candidates.append(Path(env_path).expanduser())

        candidates.extend(
            [
                self.config.assets_dir / "shorts_template_grid.png",
                self.config.assets_dir / "shorts_template_grid.jpg",
                self.config.assets_dir / "shorts_template_grid.jpeg",
                self.config.assets_dir / "shorts_template_grid.webp",
            ]
        )

        inbound_dir = self.config.workspace.parent / "media" / "inbound"
        if inbound_dir.exists():
            recent = []
            for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                recent.extend(inbound_dir.glob(pattern))
            recent = sorted(recent, key=lambda p: p.stat().st_mtime, reverse=True)
            candidates.extend(recent)

        for candidate in candidates:
            if candidate and candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _resolve_font_path(self, bold: bool = False) -> str:
        custom_candidates = []
        font_dir = os.getenv("MEDIA_AGENT_FONT_DIR")
        if font_dir:
            base = Path(font_dir).expanduser()
            custom_candidates.extend(
                [
                    base / ("MaruBuri-Bold.otf" if bold else "MaruBuri-Regular.otf"),
                    base / ("MaruBuri-Bold.ttf" if bold else "MaruBuri-Regular.ttf"),
                    base / ("MaruBuri-SemiBold.otf" if bold else "MaruBuri-Light.otf"),
                    base / ("MaruBuri-SemiBold.ttf" if bold else "MaruBuri-Light.ttf"),
                ]
            )
        system_fallbacks = [
            "/System/Library/Fonts/Supplemental/AppleSDGothicNeoB.ttf" if bold else "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        ]
        for candidate in custom_candidates + system_fallbacks:
            if Path(candidate).exists():
                return candidate
        return "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

    def _load_template_panels(self) -> List[PIL.Image.Image]:
        if self._template_panels_cache is not None:
            return self._template_panels_cache
        if not self.template_grid_path or not self.template_grid_path.exists():
            self._template_panels_cache = []
            return self._template_panels_cache

        image = PIL.Image.open(self.template_grid_path).convert("RGBA")
        width, height = image.size
        cols, rows = 5, 2
        cell_w = width / cols
        cell_h = height / rows
        pad_x = max(2, int(cell_w * 0.015))
        pad_y = max(2, int(cell_h * 0.015))

        panels = []
        for row in range(rows):
            for col in range(cols):
                left = int(round(col * cell_w)) + pad_x
                top = int(round(row * cell_h)) + pad_y
                right = int(round((col + 1) * cell_w)) - pad_x
                bottom = int(round((row + 1) * cell_h)) - pad_y
                panel = image.crop((left, top, right, bottom))
                panels.append(panel)

        self._template_panels_cache = panels
        return panels

    def _panel_for_scene(self, idx: int) -> Optional[PIL.Image.Image]:
        panels = self._load_template_panels()
        if not panels:
            return None
        if not self.current_scene_order:
            self._refresh_scene_order()
        ordered_idx = self.current_scene_order[idx] if idx < len(self.current_scene_order) else idx
        ordered_idx = max(0, min(len(panels) - 1, ordered_idx))
        return panels[ordered_idx].copy()

    def _refresh_scene_order(self):
        panels = self._load_template_panels()
        if len(panels) >= self.config.scene_count:
            self.current_scene_order = sample(range(len(panels)), self.config.scene_count)
        else:
            self.current_scene_order = list(range(self.config.scene_count))

    def _create_scene_preview(self, scene_paths: List[str]):
        try:
            cards = [PIL.Image.open(path).convert("RGB").resize((180, 320), PIL.Image.Resampling.LANCZOS) for path in scene_paths]
            canvas = PIL.Image.new("RGB", (180 * len(cards) + 32, 356), (245, 239, 230))
            draw = PIL.ImageDraw.Draw(canvas)
            title_font = self._font(22, bold=True)
            sub_font = self._font(16, bold=False)
            draw.text((14, 10), "5컷 숏츠 프리뷰", fill=self.text_dark, font=title_font)
            order_text = "컷 순서: " + ", ".join(str(n + 1) for n in self.current_scene_order)
            draw.text((14, 38), order_text, fill=(88, 72, 52), font=sub_font)
            for i, card in enumerate(cards):
                x = 8 + i * 180
                y = 64
                canvas.paste(card, (x, y))
                draw.rounded_rectangle((x + 8, y + 8, x + 40, y + 34), radius=10, fill=(38, 50, 68))
                draw.text((x + 19, y + 13), str(i + 1), fill=self.white, font=self._font(16, bold=True))
            preview_path = self.config.temp_dir / "template_scene_preview.jpg"
            canvas.save(preview_path, quality=92)
            REPORT.add("Preview", "SUCCESS", f"프리뷰 저장 완료: {preview_path.name}")
        except Exception as e:
            REPORT.add("Preview", "WARNING", f"프리뷰 생성 실패: {e}")

    def _render_scene_from_template_grid(self, out: Path, idx: int, script_text: str, chalk_text: str, target_etf: str, viewer_hook: str, market_reason: str):
        panel = self._panel_for_scene(idx)
        if panel is None:
            self.template_grid_path = None
            self._render_scene(out, idx, script_text, chalk_text, target_etf, viewer_hook, market_reason)
            return

        canvas = panel.resize((self.config.width, self.config.height), PIL.Image.Resampling.LANCZOS).convert("RGBA")
        overlay = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(overlay)

        is_final_scene = idx == self.config.scene_count - 1
        is_opening_scene = idx == 0
        header_pill = (36, 46, 206, 102)
        draw.rounded_rectangle(header_pill, radius=22, fill=(18, 28, 42, 214))
        pill_text = "마무리" if is_final_scene else ("오프닝" if is_opening_scene else f"씬 {idx + 1}")
        draw.text((66, 64), pill_text, fill=self.white, font=self._font(22, bold=True))

        hook_text = self._compress_hook(viewer_hook) if is_opening_scene else ("팔로우하세요." if is_final_scene else self._summarize_scene_caption(market_reason or viewer_hook))
        hook_font = self._fit_font(draw, hook_text, 30, 400, bold=True, min_size=20)
        self._draw_multiline_center(draw, hook_text, (250, 48, 670, 110), hook_font, self.white, 4, stroke_width=2)

        board_box = (72, 68, 648, 592)
        board_title = chalk_text or self._short_target_label(target_etf) or "ETF"
        board_font = self._fit_font(draw, board_title, 62, board_box[2] - board_box[0] - 24, bold=True, min_size=34)
        self._draw_multiline_center(draw, board_title, board_box, board_font, self.white, 18, stroke_width=4)

        script_box = (54, 878, 666, 1192)
        draw.rounded_rectangle(script_box, radius=28, fill=(255, 250, 243, 205), outline=(102, 70, 41, 110), width=3)
        label_box = (74, 894, 220, 936)
        draw.rounded_rectangle(label_box, radius=16, fill=(67, 44, 23, 235))
        draw.text((100, 905), "핵심 스크립트", fill=self.white, font=self._font(20, bold=True))

        caption = "팔로우하세요." if is_final_scene else (script_text or "핵심 내용을 짧게 정리합니다.")
        caption_font = self._fit_font(draw, caption, 34, 520, bold=True, min_size=24)
        self._draw_multiline_center(draw, caption, (90, 950, 630, 1160), caption_font, self.text_dark, 12, stroke_width=0)

        canvas.alpha_composite(overlay)
        canvas.convert("RGB").save(out, quality=95)

    def _draw_background(self, canvas: PIL.Image.Image):
        draw = PIL.ImageDraw.Draw(canvas)
        top_color = (247, 244, 238)
        bottom_color = (223, 231, 241)
        for y in range(self.config.height):
            blend = y / self.config.height
            color = (
                int(top_color[0] * (1 - blend) + bottom_color[0] * blend),
                int(top_color[1] * (1 - blend) + bottom_color[1] * blend),
                int(top_color[2] * (1 - blend) + bottom_color[2] * blend),
                255,
            )
            draw.line((0, y, self.config.width, y), fill=color)

        glow = (255, 217, 122)
        draw.ellipse((484, 30, 710, 184), fill=(*glow, 56))
        draw.ellipse((520, 54, 674, 152), fill=(*glow, 82))
        draw.rounded_rectangle((18, 28, 702, 1088), radius=58, fill=(255, 255, 255, 94), outline=(255, 255, 255, 126), width=2)
        draw.rounded_rectangle((0, 1080, self.config.width, self.config.height), radius=0, fill=(20, 34, 58, 255))
        for y in range(1080, self.config.height, 28):
            draw.line((0, y, self.config.width, y), fill=(255, 255, 255, 20), width=1)

    def _draw_board(self, canvas: PIL.Image.Image, idx: int, chalk_text: str, target_etf: str, is_final_scene: bool = False, is_opening_scene: bool = False):
        layer = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        x1, y1, x2, y2 = 154, 164, 682, 836
        draw.rounded_rectangle((x1 + 10, y1 + 18, x2 + 18, y2 + 26), radius=26, fill=(0, 0, 0, 64))
        draw.rounded_rectangle((x1 - 18, y1 - 18, x2 + 18, y2 + 18), radius=32, fill=(220, 230, 244, 180))
        draw.rounded_rectangle((x1 - 5, y1 - 5, x2 + 5, y2 + 5), radius=24, outline=(120, 86, 60, 255), width=5)
        draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=(21, 51, 43))

        for gy in range(y1 + 28, y2, 38):
            draw.line((x1 + 20, gy, x2 - 20, gy), fill=(255, 255, 255, 18), width=1)
        for gx in range(x1 + 24, x2, 38):
            draw.line((gx, y1 + 22, gx, y2 - 22), fill=(255, 255, 255, 10), width=1)

        accent_rgb = self.accent
        title_text = "CTA" if is_final_scene else f"브리핑 {idx + 1}"
        title_font = self._fit_font(draw, title_text, 30, 390, bold=True, min_size=22)
        self._draw_text_with_outline(draw, (188, 214), title_text, title_font, accent_rgb, (58, 42, 25), stroke_width=3)
        summary_font = self._fit_font(draw, chalk_text or "뉴스 핵심 정리", 64, 450, bold=True, min_size=44)
        etf_label = "다음 흐름" if is_final_scene else f"주목 ETF {target_etf}"
        etf_font = self._fit_font(draw, etf_label, 44, 388, bold=True, min_size=32)
        summary_box = (188, 282, 650, 566) if not is_final_scene else (188, 300, 650, 590)
        if is_opening_scene:
            summary_box = (188, 304, 650, 584)
        self._draw_multiline_center(draw, chalk_text or "뉴스 핵심 정리", summary_box, summary_font, self.white, 22, stroke_width=4)

        badge = (206, 634, 630, 758)
        fill = (255, 255, 255, 18) if not is_final_scene else (*self.accent, 228)
        outline = (255, 255, 255, 48) if not is_final_scene else (255, 255, 255, 90)
        text_fill = self.white if not is_final_scene else self.text_dark
        draw.rounded_rectangle(badge, radius=26, fill=fill, outline=outline, width=2)
        if is_final_scene:
            self._draw_multiline_center(draw, etf_label, (220, 650, 616, 744), etf_font, text_fill, 8, stroke_width=0)
            primary_btn = (198, 542, 638, 624)
            draw.rounded_rectangle(primary_btn, radius=30, fill=(*self.accent, 248), outline=(255, 255, 255, 110), width=2)
            self._draw_multiline_center(draw, "팔로우", (212, 556, 624, 608), self._font(38, bold=True), self.text_dark, 4)
            draw.text((286, 780), "롱폼 링크", fill=(232, 238, 247), font=self._font(22, bold=True))
        else:
            self._draw_multiline_center(draw, f"주목 ETF\n{target_etf}", (220, 650, 616, 744), etf_font, text_fill, 10, stroke_width=2)

        chalk = PIL.Image.effect_noise((x2 - x1, y2 - y1), 10).convert("L")
        chalk = chalk.point(lambda p: int(p * 0.10))
        tint = PIL.Image.new("RGBA", (x2 - x1, y2 - y1), (255, 255, 255, 0))
        tint.putalpha(chalk)
        layer.alpha_composite(tint, (x1, y1))
        canvas.alpha_composite(layer)

    def _draw_cat_teacher(self, canvas: PIL.Image.Image, scene_theme: dict):
        layer = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        scale = 1.1
        cx, cy = 112, 720
        fur = (246, 223, 191, 255)
        fur_shadow = (225, 196, 160, 255)
        stripe = (166, 116, 83, 255)
        ear = (246, 191, 194, 255)
        suit = (73, 117, 176, 255)
        suit_dark = (46, 83, 135, 255)
        paw_y_offset = scene_theme.get("paw_y_offset", 0)
        pointer_tilt = scene_theme.get("pointer_tilt", 0)
        pose = scene_theme.get("pose", "pointer")

        def sx(v):
            return int(round(v * scale))

        draw.ellipse((cx - sx(100), cy + sx(96), cx + sx(106), cy + sx(472)), fill=(0, 0, 0, 34))
        draw.ellipse((cx - sx(82), cy - sx(244), cx + sx(82), cy - sx(78)), fill=fur, outline=self.text_dark, width=4)
        draw.ellipse((cx - sx(70), cy - sx(228), cx + sx(70), cy - sx(95)), fill=fur_shadow)
        draw.polygon([(cx - sx(58), cy - sx(216)), (cx - sx(18), cy - sx(288)), (cx + sx(8), cy - sx(198))], fill=fur, outline=self.text_dark)
        draw.polygon([(cx + sx(58), cy - sx(216)), (cx + sx(18), cy - sx(288)), (cx - sx(8), cy - sx(198))], fill=fur, outline=self.text_dark)
        draw.polygon([(cx - sx(40), cy - sx(214)), (cx - sx(16), cy - sx(260)), (cx + sx(0), cy - sx(205))], fill=ear)
        draw.polygon([(cx + sx(40), cy - sx(214)), (cx + sx(16), cy - sx(260)), (cx - sx(0), cy - sx(205))], fill=ear)
        draw.ellipse((cx - sx(18), cy - sx(240), cx + sx(18), cy - sx(208)), fill=stripe)
        draw.rectangle((cx - sx(12), cy - sx(200), cx + sx(12), cy - sx(130)), fill=stripe)
        self._draw_cat_face(draw, cx, cy, scene_theme["expression"])
        for y in (-152, -138, -124):
            draw.line((cx - sx(20), cy + sx(y), cx - sx(74), cy + sx(y - 10)), fill=self.text_dark, width=3)
            draw.line((cx + sx(20), cy + sx(y), cx + sx(74), cy + sx(y - 10)), fill=self.text_dark, width=3)

        draw.rounded_rectangle((cx - sx(60), cy - sx(88), cx + sx(68), cy + sx(118)), radius=sx(34), fill=suit, outline=self.text_dark, width=4)
        draw.polygon([(cx - sx(28), cy - sx(78)), (cx, cy - sx(24)), (cx + sx(28), cy - sx(78))], fill=self.white)
        draw.polygon([(cx - sx(18), cy - sx(80)), (cx, cy - sx(34)), (cx + sx(18), cy - sx(80))], fill=suit_dark)
        draw.rectangle((cx - sx(7), cy - sx(28), cx + sx(7), cy + sx(76)), fill=suit_dark)
        draw.ellipse((cx - sx(48), cy + sx(90), cx - sx(8), cy + sx(124)), fill=suit_dark)
        draw.ellipse((cx + sx(8), cy + sx(90), cx + sx(48), cy + sx(124)), fill=suit_dark)

        pointer_color = scene_theme["pointer"]
        if pose == "wave":
            raised_paw = (cx + sx(18), cy - sx(172), cx + sx(110), cy - sx(98))
            draw.rounded_rectangle(raised_paw, radius=sx(18), fill=fur, outline=self.text_dark, width=3)
            for toe in range(4):
                tx = cx + sx(34 + toe * 18)
                draw.line((tx, cy - sx(168), tx + sx(4), cy - sx(190)), fill=self.text_dark, width=2)
        else:
            paw = (cx + sx(38), cy - sx(24) + paw_y_offset, cx + sx(132), cy + sx(14) + paw_y_offset)
            draw.rounded_rectangle(paw, radius=sx(15), fill=fur, outline=self.text_dark, width=3)
            stick_x1 = cx + sx(126)
            stick_y1 = cy - sx(174) + paw_y_offset
            stick_x2 = cx + sx(141) + pointer_tilt
            stick_y2 = cy + sx(14) + paw_y_offset
            draw.line((stick_x1, stick_y1, stick_x2, stick_y2), fill=(97, 80, 62, 255), width=sx(15))
            tip_center_x = stick_x1 - sx(1) + pointer_tilt
            tip_center_y = stick_y1 - sx(3)
            draw.ellipse((tip_center_x - sx(15), tip_center_y - sx(13), tip_center_x + sx(14), tip_center_y + sx(13)), fill=self.white, outline=self.text_dark, width=2)
            draw.ellipse((tip_center_x - sx(9), tip_center_y - sx(7), tip_center_x + sx(8), tip_center_y + sx(6)), fill=pointer_color)

        canvas.alpha_composite(layer)

    def _draw_caption(self, canvas: PIL.Image.Image, script_text: str, is_final_scene: bool = False):
        layer = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        box = (40, 850, 680, 1038)
        draw.rounded_rectangle((box[0] + 8, box[1] + 14, box[2] + 10, box[3] + 14), radius=30, fill=(0, 0, 0, 50))
        draw.rounded_rectangle(box, radius=30, fill=(11, 17, 28, 238), outline=(255, 255, 255, 30), width=2)
        label = "지금 체크" if is_final_scene else "핵심 포인트"
        draw.rounded_rectangle((58, 868, 214, 912), radius=18, fill=(*self.accent, 238))
        draw.text((88, 879), label, fill=self.text_dark, font=self._font(22, bold=True))
        summarized = self._summarize_caption(script_text)
        caption_font = self._fit_font(draw, summarized, 39, 540, bold=True, min_size=28)
        self._draw_multiline_center(draw, summarized, (78, 922, 642, 1008), caption_font, self.white, 12)
        canvas.alpha_composite(layer)

    def _draw_header(self, canvas: PIL.Image.Image, idx: int, viewer_hook: str, market_reason: str, is_final_scene: bool = False, is_opening_scene: bool = False):
        layer = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        pill = (44, 54, 224, 108)
        draw.rounded_rectangle(pill, radius=24, fill=(17, 30, 52, 228))
        pill_text = "다음" if is_final_scene else ("이유" if is_opening_scene else "브리핑")
        draw.text((86, 70), pill_text, fill=self.white, font=self._font(24, bold=True))

        hook = self._compress_hook(viewer_hook) or "왜 언급됐나"
        reason = self._summarize_scene_caption(market_reason) or "시장 이유를 정리합니다."
        if is_opening_scene:
            reason = ""
        if is_final_scene:
            hook = "팔로우 먼저"
            reason = "기준 설명은 롱폼 링크"
        hook_font = self._fit_font(draw, hook, 34, 340, bold=True, min_size=24)
        reason_font = self._fit_font(draw, reason, 18, 250, bold=False, min_size=15)
        self._draw_multiline_center(draw, hook, (338, 54, 668, 96), hook_font, self.text_dark, 4)
        if reason:
            self._draw_multiline_center(draw, reason, (426, 104, 664, 134), reason_font, (54, 63, 76), 3)
        canvas.alpha_composite(layer)

    def _draw_decorations(self, canvas: PIL.Image.Image):
        draw = PIL.ImageDraw.Draw(canvas)
        for x, y, r in [(604, 172, 9), (642, 220, 6), (578, 258, 5)]:
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 42))
        draw.polygon([(646, 1188), (654, 1204), (670, 1212), (654, 1220), (646, 1236), (638, 1220), (622, 1212), (638, 1204)], fill=(255, 255, 255, 170))

    def _draw_thumbnail_badge(self, canvas: PIL.Image.Image, scene_theme: dict, target_etf: str, idx: int = 0, is_final_scene: bool = False):
        layer = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(layer)
        if idx == 0:
            badge = (506, 182, 606, 236)
            draw.rounded_rectangle(badge, radius=20, fill=(*self.accent, 244), outline=(255, 255, 255, 120), width=2)
            draw.text((531, 196), "숫자", fill=self.text_dark, font=self._font(20, bold=True))
        elif is_final_scene:
            badge = (494, 176, 618, 236)
            draw.rounded_rectangle(badge, radius=22, fill=(17, 30, 52, 228), outline=(255, 255, 255, 84), width=2)
            draw.text((522, 192), "팔로우", fill=self.white, font=self._font(20, bold=True))
        canvas.alpha_composite(layer)

    def _draw_cat_face(self, draw, cx: int, cy: int, expression: str):
        draw.ellipse((cx - 58, cy - 176, cx - 22, cy - 143), fill=self.text_dark)
        draw.ellipse((cx + 22, cy - 176, cx + 58, cy - 143), fill=self.text_dark)
        draw.ellipse((cx - 47, cy - 168, cx - 34, cy - 156), fill=self.white)
        draw.ellipse((cx + 34, cy - 168, cx + 47, cy - 156), fill=self.white)
        draw.polygon([(cx, cy - 142), (cx - 12, cy - 126), (cx + 12, cy - 126)], fill=(239, 140, 144, 255))
        if expression == "excited":
            draw.arc((cx - 22, cy - 126, cx + 22, cy - 88), 8, 172, fill=self.text_dark, width=4)
            draw.arc((cx - 60, cy - 188, cx - 20, cy - 154), 200, 340, fill=self.text_dark, width=3)
            draw.arc((cx + 20, cy - 188, cx + 60, cy - 154), 200, 340, fill=self.text_dark, width=3)
        elif expression == "serious":
            draw.line((cx - 56, cy - 182, cx - 20, cy - 164), fill=self.text_dark, width=4)
            draw.line((cx + 20, cy - 164, cx + 56, cy - 182), fill=self.text_dark, width=4)
            draw.line((cx - 20, cy - 110, cx + 20, cy - 110), fill=self.text_dark, width=4)
        elif expression == "wink":
            draw.line((cx - 54, cy - 164, cx - 24, cy - 164), fill=self.text_dark, width=4)
            draw.arc((cx + 22, cy - 176, cx + 58, cy - 142), 180, 360, fill=self.text_dark, width=4)
            draw.arc((cx - 24, cy - 124, cx + 24, cy - 92), 15, 170, fill=self.text_dark, width=4)
        elif expression == "surprised":
            draw.ellipse((cx - 52, cy - 173, cx - 24, cy - 145), outline=self.text_dark, width=4)
            draw.ellipse((cx + 24, cy - 173, cx + 52, cy - 145), outline=self.text_dark, width=4)
            draw.ellipse((cx - 10, cy - 118, cx + 10, cy - 94), outline=self.text_dark, width=4)
        else:
            draw.arc((cx - 20, cy - 124, cx + 20, cy - 96), 10, 170, fill=self.text_dark, width=3)

    def _scene_theme(self, idx: int, script_text: str, is_final_scene: bool = False, is_opening_scene: bool = False) -> dict:
        expressions = ["confident", "serious", "excited", "wink", "surprised"]
        expression = expressions[idx % len(expressions)]
        pose = "pointer"
        if "하락" in script_text or "리스크" in script_text or "불안" in script_text:
            expression = "serious"
        elif "기회" in script_text or "반등" in script_text or "강세" in script_text:
            expression = "excited"
        elif "놀라" in script_text or "급등" in script_text or "급락" in script_text:
            expression = "surprised"
        elif "핵심" in script_text or "포인트" in script_text or "정리" in script_text:
            expression = "wink"
        if is_opening_scene:
            expression = "excited"
        if is_final_scene:
            expression = "wink"
            pose = "wave"
        motion_cycle = [(-6, -8), (2, 5), (-3, -4), (4, 7), (-5, -6)]
        paw_y_offset, pointer_tilt = motion_cycle[idx % len(motion_cycle)]
        return {
            "expression": expression,
            "pointer": (255, 196, 93, 255),
            "accent": self.accent,
            "paw_y_offset": paw_y_offset,
            "pointer_tilt": pointer_tilt,
            "pose": pose,
        }

    def create_thumbnail_cover(self, script_data: dict, out: Path):
        if self.template_grid_path:
            self._create_thumbnail_from_template(script_data, out)
            return

        headline = self._thumbnail_headline(script_data)
        target_etf = script_data.get("target_etf", "ETF")
        scene_theme = self._scene_theme(0, headline)
        numeric_badge = self._extract_numeric_badge(script_data)
        canvas = PIL.Image.new("RGBA", (1280, 720), (244, 237, 225, 255))
        draw = PIL.ImageDraw.Draw(canvas)

        top_color = (255, 246, 229)
        bottom_color = (243, 225, 206)
        for x in range(1280):
            blend = x / 1280
            color = (
                int(top_color[0] * (1 - blend) + bottom_color[0] * blend),
                int(top_color[1] * (1 - blend) + bottom_color[1] * blend),
                int(top_color[2] * (1 - blend) + bottom_color[2] * blend),
                255,
            )
            draw.line((x, 0, x, 720), fill=color)

        draw.rounded_rectangle((38, 34, 1242, 686), radius=42, fill=(255, 248, 239, 92), outline=(255, 255, 255, 120), width=2)
        draw.rounded_rectangle((56, 52, 168, 132), radius=28, fill=(*self.accent, 248))
        draw.text((86, 74), "ETF", fill=self.text_dark, font=self._font(32, bold=True))

        board = (430, 88, 1204, 582)
        draw.rounded_rectangle((board[0] + 12, board[1] + 16, board[2] + 20, board[3] + 22), radius=34, fill=(0, 0, 0, 58))
        draw.rounded_rectangle((board[0] - 18, board[1] - 18, board[2] + 18, board[3] + 18), radius=40, fill=self.board_frame)
        draw.rounded_rectangle(board, radius=30, fill=self.board_color)
        draw.rounded_rectangle((472, 120, 670, 210), radius=34, fill=(17, 30, 52, 214))
        draw.text((520, 150), "핵심 숫자", fill=self.white, font=self._font(30, bold=True))
        self._draw_multiline_center(draw, headline, (486, 214, 1158, 372), self._font(70, bold=True), self.white, 18, stroke_width=3)
        if numeric_badge:
            draw.rounded_rectangle((846, 102, 1144, 182), radius=30, fill=(*self.accent, 242))
            self._draw_multiline_center(draw, numeric_badge, (862, 118, 1128, 166), self._font(36, bold=True), self.text_dark, 6)
        draw.rounded_rectangle((500, 396, 812, 468), radius=26, fill=(15, 30, 49, 188), outline=(255, 255, 255, 52), width=2)
        draw.text((570, 418), "주목 ETF", fill=(255, 233, 166), font=self._font(30, bold=True))
        draw.rounded_rectangle((494, 466, 1158, 556), radius=24, fill=(255, 255, 255, 14), outline=(255, 255, 255, 42), width=2)
        target_label = self._short_target_label(target_etf)
        draw.rounded_rectangle((540, 474, 1112, 548), radius=22, fill=(12, 24, 40, 166), outline=(255, 255, 255, 34), width=2)
        self._draw_multiline_center(draw, target_label, (552, 482, 1100, 540), self._font(56, bold=True), (255, 248, 232), 8, stroke_width=0)

        self._draw_thumbnail_cat(draw, scene_theme)
        self._draw_thumbnail_chart(draw, scene_theme)
        draw.rounded_rectangle((894, 582, 1136, 650), radius=26, fill=(*self.accent, 240))
        draw.text((948, 606), "이유", fill=self.text_dark, font=self._font(28, bold=True))

        canvas.convert("RGB").save(out, quality=95)
        REPORT.add("Thumbnail", "SUCCESS", f"썸네일 저장 완료: {out.name}")

    def _create_thumbnail_from_template(self, script_data: dict, out: Path):
        panels = self._load_template_panels()
        if not panels:
            self.template_grid_path = None
            self.create_thumbnail_cover(script_data, out)
            return

        if not self.current_scene_order:
            self._refresh_scene_order()

        hero_idx = self.current_scene_order[0] if self.current_scene_order else 0
        hero = panels[hero_idx].copy().resize((1280, 720), PIL.Image.Resampling.LANCZOS).convert("RGBA")
        overlay = PIL.Image.new("RGBA", hero.size, (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(overlay)

        draw.rounded_rectangle((24, 24, 1256, 696), radius=40, fill=(0, 0, 0, 18), outline=(255, 255, 255, 130), width=3)
        draw.rounded_rectangle((44, 40, 170, 112), radius=26, fill=(*self.accent, 244))
        draw.text((80, 62), "ETF", fill=self.text_dark, font=self._font(28, bold=True))

        headline = self._thumbnail_headline(script_data)
        target_label = self._short_target_label(script_data.get("target_etf", "ETF"))
        numeric_badge = self._extract_numeric_badge(script_data)

        title_box = (620, 84, 1210, 356)
        draw.rounded_rectangle(title_box, radius=36, fill=(15, 24, 40, 182), outline=(255, 255, 255, 80), width=2)
        self._draw_multiline_center(draw, headline, (650, 120, 1180, 282), self._font(66, bold=True), self.white, 14, stroke_width=3)

        draw.rounded_rectangle((676, 320, 1154, 410), radius=26, fill=(255, 248, 238, 220), outline=(85, 57, 31, 110), width=2)
        self._draw_multiline_center(draw, target_label, (700, 338, 1130, 392), self._font(44, bold=True), self.text_dark, 8)

        if numeric_badge:
            draw.rounded_rectangle((976, 40, 1192, 108), radius=24, fill=(38, 50, 68, 228))
            self._draw_multiline_center(draw, numeric_badge, (992, 54, 1176, 94), self._font(28, bold=True), self.white, 4)

        hook = self._compress_hook(script_data.get("viewer_hook", "오늘 핵심"), limit=18)
        draw.rounded_rectangle((694, 602, 1176, 664), radius=24, fill=(*self.accent, 236))
        self._draw_multiline_center(draw, hook, (714, 614, 1156, 650), self._font(28, bold=True), self.text_dark, 4)

        hero.alpha_composite(overlay)
        hero.convert("RGB").save(out, quality=95)
        REPORT.add("Thumbnail", "SUCCESS", f"썸네일 저장 완료: {out.name}")

    def _draw_thumbnail_cat(self, draw, scene_theme: dict):
        cx, cy = 238, 474
        fur = (246, 223, 191, 255)
        suit = (73, 117, 176, 255)
        suit_dark = (46, 83, 135, 255)
        ear = (246, 191, 194, 255)
        draw.ellipse((86, 188, 400, 644), fill=(0, 0, 0, 34))
        draw.ellipse((cx - 118, cy - 220, cx + 118, cy - 10), fill=fur, outline=self.text_dark, width=6)
        draw.polygon([(cx - 90, cy - 154), (cx - 42, cy - 292), (cx + 18, cy - 154)], fill=fur, outline=self.text_dark)
        draw.polygon([(cx + 90, cy - 154), (cx + 42, cy - 292), (cx - 18, cy - 154)], fill=fur, outline=self.text_dark)
        draw.polygon([(cx - 58, cy - 164), (cx - 28, cy - 248), (cx + 4, cy - 164)], fill=ear)
        draw.polygon([(cx + 58, cy - 164), (cx + 28, cy - 248), (cx - 4, cy - 164)], fill=ear)
        self._draw_cat_face(draw, cx, cy - 16, scene_theme["expression"])
        draw.rounded_rectangle((cx - 102, cy - 4, cx + 110, cy + 228), radius=52, fill=suit, outline=self.text_dark, width=6)
        draw.polygon([(cx - 48, cy + 8), (cx, cy + 104), (cx + 48, cy + 8)], fill=self.white)
        draw.rectangle((cx - 12, cy + 86, cx + 12, cy + 202), fill=suit_dark)
        draw.rounded_rectangle((cx + 60, cy + 30, cx + 202, cy + 72), radius=18, fill=fur, outline=self.text_dark, width=4)
        draw.rounded_rectangle((cx + 194, cy - 144, cx + 214, cy + 74), radius=10, fill=(97, 80, 62, 255))
        draw.ellipse((cx + 186, cy - 164, cx + 222, cy - 132), fill=scene_theme["pointer"], outline=self.text_dark, width=3)

    def _draw_thumbnail_chart(self, draw, scene_theme: dict):
        draw.rounded_rectangle((980, 74, 1210, 156), radius=28, fill=(255, 255, 255, 134))
        draw.text((1044, 98), "ETF", fill=self.text_dark, font=self._font(30, bold=True))

    def _draw_multiline_center(self, draw, text: str, box, font, fill, spacing: int, stroke_width: int = 0, stroke_fill=None):
        wrapped = self._wrap_text(draw, text, font, box[2] - box[0])
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="center", stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = box[0] + ((box[2] - box[0]) - text_w) / 2
        y = box[1] + ((box[3] - box[1]) - text_h) / 2
        shadow_color = (0, 0, 0, 70) if len(fill) == 4 else (0, 0, 0)
        draw.multiline_text((x + 2, y + 2), wrapped, font=font, fill=shadow_color, spacing=spacing, align="center", stroke_width=stroke_width, stroke_fill=shadow_color)
        draw.multiline_text((x, y), wrapped, font=font, fill=fill, spacing=spacing, align="center", stroke_width=stroke_width, stroke_fill=stroke_fill or shadow_color)

    def _draw_text_with_outline(self, draw, pos, text: str, font, fill, outline_fill, stroke_width: int = 2):
        draw.text(pos, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=outline_fill)

    def _extract_numeric_badge(self, script_data: dict) -> str:
        candidates = [
            script_data.get("title", ""),
            script_data.get("viewer_hook", ""),
            " ".join(script_data.get("chalk_summary", [])[:2]),
        ]
        for text in candidates:
            text = str(text)
            for token in text.replace("?", " ").replace("!", " ").split():
                if any(ch.isdigit() for ch in token):
                    return token[:18]
        format_label = script_data.get("format_label") or "오늘 핵심"
        if "초보" in format_label:
            return "초보 체크"
        if "이슈" in format_label:
            return "이슈 연결"
        return "오늘 핵심"

    def _compress_hook(self, text: str, limit: int = 14) -> str:
        text = " ".join(str(text).split())
        if not text:
            return "왜 언급됐나"
        for token in ["오늘 ", "오늘의 ", "빠르게 ", "같이 ", "바로 ", "지금 ", "정말 "]:
            text = text.replace(token, "")
        text = text.replace("ETF", "ETF ").strip()
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        if "?" in text:
            text = text.split("?", 1)[0] + "?"
        cut = text[:limit].rstrip(" ,.")
        return cut

    def _thumbnail_headline(self, script_data: dict) -> str:
        lines = script_data.get("chalk_summary", []) or [script_data.get("target_etf", "ETF")]
        cleaned = []
        for raw in lines[:2]:
            raw = " ".join(str(raw).replace("\n", " ").split())
            if not raw:
                continue
            if len(raw) > 8:
                raw = raw[:8].rstrip()
            cleaned.append(raw)
        if not cleaned:
            cleaned = [self._short_target_label(script_data.get("target_etf", "ETF"))]
        return "\n".join(cleaned[:2])

    def _short_target_label(self, target_etf: str) -> str:
        text = " ".join(str(target_etf).split())
        replacements = {
            "KODEX ": "KODEX\n",
            "TIGER ": "TIGER\n",
            "ACE ": "ACE\n",
            "PLUS ": "PLUS\n",
        }
        for src, dst in replacements.items():
            if text.startswith(src):
                text = text.replace(src, dst, 1)
                break
        lines = str(text).splitlines()[:2]
        cleaned = []
        for line in lines:
            cleaned.append(line[:8].rstrip())
        return "\n".join(cleaned)[:18]

    def _tail_cta(self, script_data: dict, longform_cta: str, newsletter_cta: str) -> str:
        cta = str(script_data.get("cta", ""))
        content_format = str(script_data.get("content_format", ""))
        format_label = str(script_data.get("format_label", ""))
        if "롱폼" in cta or "기초" in cta:
            return longform_cta
        if "주간" in cta or "링크" in cta or "뉴스레터" in cta:
            return newsletter_cta
        if content_format == "beginner" or "초보" in format_label:
            return longform_cta
        if content_format == "issue":
            return newsletter_cta
        return newsletter_cta

    def _primary_cta(self, cta: str) -> str:
        text = " ".join(str(cta).split())
        if not text:
            return "이 흐름 계속 볼 거면 팔로우하세요."
        if "팔로우" in text:
            return "이 흐름 계속 볼 거면 팔로우하세요."
        if "롱폼" in text or "기초" in text:
            return "기준 설명은 채널 롱폼에서 이어서 보세요."
        if "뉴스레터" in text or "링크" in text or "주간" in text:
            return "주간 ETF 요약은 프로필 링크에서 확인하세요."
        return text

    def _wrap_text(self, draw, text: str, font, max_width: int) -> str:
        if not text:
            return ""
        paragraphs = str(text).splitlines()
        wrapped_paragraphs = []
        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                wrapped_paragraphs.append("")
                continue
            lines = []
            current = words[0]
            for word in words[1:]:
                trial = f"{current} {word}"
                if draw.textlength(trial, font=font) <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            wrapped_paragraphs.append("\n".join(lines))
        return "\n".join(wrapped_paragraphs)

    def _summarize_caption(self, text: str) -> str:
        return self._summarize_scene_caption(text)

    def _summarize_scene_caption(self, text: str) -> str:
        text = " ".join(str(text).split())
        if not text:
            return ""

        sentences = []
        current = ""
        for ch in text:
            current += ch
            if ch in ".!?。！？":
                cleaned = current.strip()
                if cleaned:
                    sentences.append(cleaned)
                current = ""
        if current.strip():
            sentences.append(current.strip())

        if not sentences:
            return text

        target = max(1, int(len(text) * 0.5))
        selected = []
        total = 0
        for sentence in sentences:
            candidate_total = total + len(sentence)
            if selected and candidate_total > target * 1.2:
                break
            selected.append(sentence)
            total = candidate_total
            if total >= target:
                break

        if not selected:
            first = sentences[0]
            cutoff = max(18, int(len(first) * 0.7))
            trimmed = first[:cutoff].rstrip(" ,")
            last_space = trimmed.rfind(" ")
            if last_space > max(10, cutoff // 2):
                trimmed = trimmed[:last_space]
            result = trimmed
        else:
            result = " ".join(selected).strip()

        if result[-1] not in ".!?。！？":
            result += "."
        return result

    def _font(self, size: int, bold: bool = False):
        font_path = self.bold_font if bold else self.font
        try:
            return PIL.ImageFont.truetype(font_path, size)
        except Exception:
            return PIL.ImageFont.load_default()

    def _fit_font(self, draw, text: str, start_size: int, max_width: int, bold: bool = False, min_size: int = 18):
        lines = str(text).splitlines() or [str(text)]
        for size in range(start_size, min_size - 1, -1):
            font = self._font(size, bold=bold)
            if all(draw.textlength(line or " ", font=font) <= max_width for line in lines):
                return font
        return self._font(min_size, bold=bold)


class PerformanceLogger:
    def __init__(self, config: AppConfig):
        self.config = config

    def log_generation(self, script_data: dict, video_path: Path, thumbnail_path: Optional[Path], metadata_path: Path):
        self.config.analytics_dir.mkdir(exist_ok=True)
        log_path = self.config.analytics_dir / "shorts_generation_log.jsonl"
        payload = {
            "logged_at": datetime.now().isoformat(),
            "content_type": "shorts",
            "content_format": script_data.get("content_format"),
            "format_label": script_data.get("format_label"),
            "target_etf": script_data.get("target_etf"),
            "title": script_data.get("title"),
            "viewer_hook": script_data.get("viewer_hook"),
            "market_reason": script_data.get("market_reason"),
            "cta": script_data.get("cta"),
            "scene_count": len(script_data.get("scenes", [])),
            "chalk_summary": script_data.get("chalk_summary"),
            "video_path": str(video_path),
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "metadata_path": str(metadata_path),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        REPORT.add("Analytics", "SUCCESS", f"성과 로그 저장: {log_path.name}")
        return log_path


class MediaDirector:
    def __init__(self, config: AppConfig):
        self.config = config

    def execute(self, images, audio, output_name):
        print("🎬 [Director] 최종 영상 조립 중...")
        if not audio:
            REPORT.add("Final", "ERROR", "오디오가 없어 영상 조립 실패")
            return False

        target_duration = max(self.config.min_duration_sec, min(audio.duration, self.config.max_duration_sec))
        dps = target_duration / len(images)
        clips = [ImageClip(path).with_duration(dps) for path in images]

        try:
            final = concatenate_videoclips(clips, method="compose")
            final = final.with_audio(audio.subclipped(0, min(audio.duration, target_duration)))
            final.write_videofile(str(output_name), fps=24, codec="libx264", audio_codec="aac")
            REPORT.add("Final", "SUCCESS", f"영상 저장 완료: {output_name.name}")
            return True
        except Exception as e:
            REPORT.add("Final", "ERROR", f"렌더링 실패: {e}")
            return False


class MetadataWriter:
    def __init__(self, config: AppConfig):
        self.config = config
        self.default_tags = [
            "ETF브리핑",
            "주식전망",
            "경제뉴스",
            "시장브리핑",
            "국내ETF",
            "코스피",
            "재테크",
            "주식초보",
            "섹터분석",
            "ETF비교",
            "유튜브쇼츠",
            "shorts",
        ]

    def write(self, script_data: dict, video_path: Path, thumbnail_path: Optional[Path] = None):
        incoming_tags = script_data.get("tags", [])
        tags = self._merge_tags(incoming_tags, script_data.get("target_etf"))
        base_description = script_data.get("description", "경제 뉴스 흐름을 바탕으로 ETF를 짧게 정리한 브리핑입니다. 본 영상은 투자 권유가 아닌 정보 정리용 콘텐츠입니다.")
        content_format = str(script_data.get("content_format", ""))
        longform_cta = "ETF 기본 개념과 포트폴리오 구성은 채널 롱폼에서 이어집니다."
        newsletter_cta = "주간 ETF 흐름 요약은 프로필 링크에서 이어집니다."
        if content_format == "beginner":
            longform_cta = "초보자용 ETF 기준 설명은 채널 롱폼에서 이어집니다."
        elif content_format == "issue":
            newsletter_cta = "이슈별 ETF 흐름 요약은 프로필 링크에서 이어집니다."
        short_cta = self._primary_cta(script_data.get("cta", "이 흐름 계속 볼 거면 팔로우하고 다음 브리핑도 이어서 보세요."))
        trust_line = "\n오늘 다룬 내용은 뉴스와 시장 흐름을 바탕으로 정리했으며, 투자 판단 전에는 구성 종목과 변동성을 꼭 함께 확인하세요."
        clean_title = self._clean_title(script_data.get("title", f"주목 ETF 흐름 | {script_data.get('target_etf', '')}"))
        payload = {
            "title": clean_title,
            "description": base_description + trust_line + "\n\n" + short_cta + "\n\n" + self._tail_cta(script_data, longform_cta, newsletter_cta),
            "tags": tags,
            "target_etf": script_data.get("target_etf"),
            "content_format": script_data.get("content_format"),
            "format_label": script_data.get("format_label"),
            "viewer_hook": script_data.get("viewer_hook"),
            "market_reason": script_data.get("market_reason"),
            "cta": script_data.get("cta"),
            "video_path": str(video_path),
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "privacy_status": self.config.privacy_status,
            "created_at": datetime.now().isoformat(),
        }
        out = video_path.with_suffix(".json")
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        REPORT.add("Metadata", "SUCCESS", f"업로드 메타데이터 저장: {out.name}")
        return out

    def _merge_tags(self, incoming_tags, target_etf: Optional[str]):
        merged = []
        blocked_tags = {"ETF추천", "급등주", "무조건오름", "유튜브쇼츠", "shorts"}
        for tag in list(incoming_tags) + self.default_tags + ([target_etf] if target_etf else []):
            if not tag:
                continue
            clean = str(tag).strip().replace("#", "")
            if clean in blocked_tags:
                continue
            if clean and clean not in merged:
                merged.append(clean)
        return merged[:8]

    def _primary_cta(self, cta: str) -> str:
        text = " ".join(str(cta).split())
        if not text:
            return "팔로우하세요."
        if "팔로우" in text:
            return "팔로우하세요."
        if "롱폼" in text or "기초" in text:
            return "롱폼에서 이어보세요."
        if "뉴스레터" in text or "링크" in text or "주간" in text:
            return "프로필 링크에서 확인하세요."
        return text

    def _clean_title(self, title: str) -> str:
        text = " ".join(str(title).split())
        for token in ["지금 ", "오늘 ", "정말 ", "빠르게 "]:
            text = text.replace(token, "")
        if len(text) > 32:
            text = text[:32].rstrip(" ,.")
        return text

    def _tail_cta(self, script_data: dict, longform_cta: str, newsletter_cta: str) -> str:
        cta = str(script_data.get("cta", ""))
        content_format = str(script_data.get("content_format", ""))
        format_label = str(script_data.get("format_label", ""))
        if "롱폼" in cta or "기초" in cta:
            return longform_cta
        if "주간" in cta or "링크" in cta or "뉴스레터" in cta:
            return newsletter_cta
        if content_format == "beginner" or "초보" in format_label:
            return longform_cta
        if content_format == "issue":
            return newsletter_cta
        return newsletter_cta


def run_factory():
    config = AppConfig.from_env()
    config.temp_dir.mkdir(exist_ok=True)
    config.output_dir.mkdir(exist_ok=True)
    config.assets_dir.mkdir(exist_ok=True)
    config.analytics_dir.mkdir(exist_ok=True)

    client = genai.Client(api_key=config.gemini_api_key)
    analyst = EconomyAnalyst(client, config)
    script_data = analyst.execute()
    if not script_data:
        REPORT.print_summary()
        raise SystemExit(1)

    audio_clip = AudioProducer(config).execute(script_data["scenes"])
    artist = TemplateArtist(config)
    image_paths = artist.execute(script_data)

    timestamp = datetime.now().strftime("%m%d_%H%M")
    output_path = config.output_dir / f"shorts_{timestamp}.mp4"
    thumbnail_path = config.output_dir / f"shorts_{timestamp}_thumb.jpg"
    render_ok = MediaDirector(config).execute(image_paths, audio_clip, output_path)
    artist.create_thumbnail_cover(script_data, thumbnail_path)
    metadata_path = MetadataWriter(config).write(script_data, output_path, thumbnail_path)
    PerformanceLogger(config).log_generation(script_data, output_path, thumbnail_path, metadata_path)

    REPORT.print_summary()
    if render_ok:
        print(f"🚀 영상 완성본 경로: {output_path}")
        print(f"🖼️ 썸네일 경로: {thumbnail_path}")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    run_factory()
