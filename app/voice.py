import asyncio
from pathlib import Path
import edge_tts
async def _make(text,path):
    await edge_tts.Communicate(text,"en-US-GuyNeural",rate="+0%").save(str(path))
def make_voice(text,path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    asyncio.run(_make(text,path))
    if Path(path).stat().st_size<1000: raise RuntimeError("TTS output is empty")
