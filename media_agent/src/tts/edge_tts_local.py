from __future__ import annotations

import asyncio
from pathlib import Path
import edge_tts


def synthesize(text: str, output_path: Path, cfg: dict) -> Path:
    voice = str(cfg.get('voice', 'ko-KR-HyunsuMultilingualNeural')).strip()
    rate = str(cfg.get('rate', '-8%')).strip()
    pitch = str(cfg.get('pitch', '-4Hz')).strip()

    async def main():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(output_path))

    asyncio.run(main())
    return output_path
