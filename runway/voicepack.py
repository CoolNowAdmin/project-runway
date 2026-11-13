"""Singapore voice pack: free Microsoft neural voices through edge-tts (no key). Used by the Ask page's read-aloud.

Singapore has en-SG and ta-SG voices; Malay and Mandarin have no Singapore voice, so they use the nearest.
shortcut: edge-tts is an unofficial endpoint that can change without notice; the page falls back to device voices.
"""

from __future__ import annotations

import asyncio
import base64

VOICES = {"en": "en-SG-LunaNeural", "ta": "ta-SG-VenbaNeural", "ms": "ms-MY-YasminNeural", "zh": "zh-CN-XiaoxiaoNeural"}
MAX_CHARS = 700  # about a minute of speech; keeps the reply small


def speak(text: str, lang: str) -> str | None:
    """mp3 as base64, or None if the voice, the text or the network is unusable."""
    voice, text = VOICES.get(lang), text.strip()[:MAX_CHARS]
    if not voice or not text:
        return None

    async def run() -> bytes:
        import edge_tts

        return b"".join([c["data"] async for c in edge_tts.Communicate(text, voice, rate="-8%").stream() if c["type"] == "audio"])

    for attempt in (1, 2):  # the service sometimes returns nothing once; a second try usually works
        try:
            audio = asyncio.run(asyncio.wait_for(run(), 20))
            break
        except Exception as exc:  # network, bad voice, library change: the caller falls back
            print(f"[runway] voice pack failed (try {attempt}): {type(exc).__name__}: {exc}", flush=True)
    else:
        return None
    return base64.b64encode(audio).decode() if audio else None
