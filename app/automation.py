import json
from datetime import date
from pathlib import Path

from google import genai

from .config import GEMINI_API_KEY
from .research import find_topic
from .writer import create_pair
from .telugu import translate_content
from .voice import make_voice
from .video import render, thumbnail
from .quality import validate_pair


def run():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    day = date.today().isoformat()
    out = Path("output") / day / "te"
    out.mkdir(parents=True, exist_ok=True)

    print("1/6 Researching a fresh topic...")
    topic = find_topic()

    print("2/6 Creating documentary scripts...")
    english = create_pair(topic)

    print("3/6 Translating into Telugu...")
    telugu = translate_content(english)

    telugu["topic"] = topic
    report = validate_pair(telugu)

    (out / "content.json").write_text(
        json.dumps(telugu, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (out / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    results = {}
    for kind in ("short", "long"):
        print(f"4/6 Generating {kind} narration...")
        audio = out / f"{kind}.mp3"
        video = out / f"{kind}.mp4"
        thumb = out / f"{kind}.jpg"

        make_voice(telugu[kind]["script"], audio, kind=kind)

        print(f"5/6 Rendering {kind} video...")
        render(
            telugu[kind]["script"],
            audio,
            video,
            vertical=(kind == "short"),
            title=telugu[kind]["title"],
            storyboard=telugu[kind]["storyboard"],
        )
        thumbnail(
            telugu[kind]["title"],
            thumb,
            visual_dir=video.parent / f"{video.stem}_frames" / "visuals",
            thumbnail_text=telugu[kind].get("thumbnail_text"),
        )
        results[kind] = {
            "video": str(video),
            "thumbnail": str(thumb),
            "audio": str(audio),
        }

    print("6/6 Production complete.")
    print(json.dumps({
        "date": day,
        "language": "Telugu",
        "voice": "te-IN-ShrutiNeural",
        "topic": telugu["topic_title"],
        "quality": report,
        "files": results,
        "upload_status": "not uploaded; review required",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
