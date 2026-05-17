from __future__ import annotations

from pathlib import Path
import requests


def synthesize(text: str, output_path: Path, cfg: dict) -> Path:
    base_url = str(cfg.get('base_url', 'http://127.0.0.1:9880')).rstrip('/')
    ref_audio_path = str(cfg.get('ref_audio_path', '')).strip()
    prompt_text = str(cfg.get('prompt_text', '')).strip()
    text_lang = str(cfg.get('text_lang', 'ko')).strip()
    prompt_lang = str(cfg.get('prompt_lang', text_lang)).strip()
    text_split_method = str(cfg.get('text_split_method', 'cut5')).strip()
    speed_factor = float(cfg.get('speed_factor', 1.0))
    media_type = str(cfg.get('media_type', 'wav')).strip()

    if not ref_audio_path:
        raise RuntimeError('GPT-SoVITS ref_audio_path missing')
    if not Path(ref_audio_path).expanduser().exists():
        raise RuntimeError(f'GPT-SoVITS ref_audio_path not found: {ref_audio_path}')
    if not prompt_text:
        raise RuntimeError('GPT-SoVITS prompt_text missing')

    payload = {
        'text': text,
        'text_lang': text_lang,
        'ref_audio_path': str(Path(ref_audio_path).expanduser()),
        'prompt_lang': prompt_lang,
        'prompt_text': prompt_text,
        'text_split_method': text_split_method,
        'speed_factor': speed_factor,
        'media_type': media_type,
        'streaming_mode': False,
    }
    response = requests.post(f'{base_url}/tts', json=payload, timeout=300)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path
