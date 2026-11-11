import json
from datetime import date
from pathlib import Path

from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .writer import _generate
from .voice import make_voice
from .video import render, thumbnail

SOURCE = Path("output/2026-10-31/en/content.json")
OUT = Path("output") / date.today().isoformat() / "te"


def translate_content(original):
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
Translate this existing financial documentary content into natural,
professional Telugu. Use Telugu script.

This is a faithful translation, NOT a new script or a new topic.

Rules:
- Preserve every fact, figure, date, percentage, name and financial claim.
- Do not add, remove, invent, summarize or reinterpret claims.
- Preserve the short and long video structures and scene order.
- Translate title, thumbnail_text, description, script, hashtags,
  every storyboard voiceover and every storyboard on_screen_text.
- Keep storyboard visual_query values in English exactly as supplied.
  They are search queries for finding relevant footage.
- Preserve source_urls exactly.
- Keep the same JSON keys and structure.
- Use fluent spoken Telugu suitable for documentary narration.
- Avoid unnecessary English words; retain proper nouns and standard
  financial abbreviations where appropriate.
- Return valid JSON only, with no Markdown fences or commentary.

Original content:
{json.dumps(original, ensure_ascii=False)}
"""

    translated = _generate(client, prompt)

    # Preserve source metadata and search queries exactly.
    translated["topic"] = original.get("topic", {})
    for kind in ("short", "long"):
        src = original[kind]
        dst = translated[kind]

        dst["source_urls"] = src.get("source_urls", [])

        src_scenes = src.get("storyboard", [])
        dst_scenes = dst.get("storyboard", [])

        if len(src_scenes) != len(dst_scenes):
            raise ValueError(
                f"{kind}: scene count changed during translation "
                f"({len(src_scenes)} -> {len(dst_scenes)})"
            )

        for i, scene in enumerate(dst_scenes):
            scene["visual_query"] = src_scenes[i].get("visual_query", "")

        for key in ("script", "title", "description", "thumbnail_text", "hashtags"):
            if key not in dst:
                raise ValueError(f"{kind}: missing translated field {key}")

    if not translated.get("topic_title"):
        translated["topic_title"] = original.get("topic_title", "")

    return translated


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"English source not found: {SOURCE}")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing from configuration.")

    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    print(f"Translating existing story: {original.get('topic_title', 'Untitled')}")

    data = translate_content(original)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "content.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    results = {}

    for kind in ("short", "long"):
        audio = OUT / f"{kind}.mp3"
        video = OUT / f"{kind}.mp4"
        thumb = OUT / f"{kind}.jpg"

        print(f"Generating Telugu {kind} narration...")
        make_voice(data[kind]["script"], audio)

        print(f"Rendering Telugu {kind} video...")
        render(
            data[kind]["script"],
            audio,
            video,
            vertical=(kind == "short"),
            title=data[kind]["title"],
            storyboard=data[kind]["storyboard"],
        )

        print(f"Creating Telugu {kind} thumbnail...")
        thumbnail(
            data[kind]["title"],
            thumb,
            visual_dir=video.parent / f"{video.stem}_frames" / "visuals",
            thumbnail_text=data[kind].get("thumbnail_text"),
        )

        results[kind] = {
            "video": str(video),
            "audio": str(audio),
            "thumbnail": str(thumb),
        }

    print(json.dumps({
        "language": "Telugu",
        "source": str(SOURCE),
        "output": str(OUT),
        "topic": data["topic_title"],
        "files": results,
        "youtube_upload": "disabled",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
