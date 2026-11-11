import asyncio
from pathlib import Path
import edge_tts

VOICE = "te-IN-ShrutiNeural"
LONG_RATE = "+5%"
SHORT_RATE = "+15%"

async def _make(text, path, rate):
    await edge_tts.Communicate(
        text,
        VOICE,
        rate=rate,
        volume="+0%",
        pitch="+0Hz"
    ).save(str(path))

def make_voice(text, path, kind="long"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = SHORT_RATE if kind == "short" else LONG_RATE
    asyncio.run(_make(text, path, rate))

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Telugu TTS output is empty or unexpectedly small")
