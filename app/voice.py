import asyncio
from pathlib import Path
import edge_tts

# Telugu documentary narration
VOICE = "te-IN-MohanNeural"

async def _make(text, path):
    await edge_tts.Communicate(
        text,
        VOICE,
        rate="-2%",
        volume="+0%",
        pitch="+0Hz"
    ).save(str(path))

def make_voice(text, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_make(text, path))

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Telugu TTS output is empty or unexpectedly small")
