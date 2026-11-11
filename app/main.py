import argparse
import json
from pathlib import Path
from datetime import date
from .research import find_topic
from .writer import create_pair
from .voice import make_voice
from .video import render, thumbnail
from .quality import validate_pair


def run(mode="draft"):
    if mode != "draft":
        raise ValueError("Documentary quality build is draft-only. YouTube uploads remain disabled until reviewed.")
    day = date.today().isoformat()
    out = Path("output") / day / "en"
    out.mkdir(parents=True, exist_ok=True)
    topic = find_topic()
    data = create_pair(topic)
    quality_report = validate_pair(data)
    (out / "content.json").write_text(
        json.dumps({"topic": topic, **data}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "quality_report.json").write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
    files, thumbnails = {}, {}
    for kind in ("short", "long"):
        audio, video, thumb = out/f"{kind}.mp3", out/f"{kind}.mp4", out/f"{kind}.jpg"
        make_voice(data[kind]["script"], audio)
        render(data[kind]["script"], audio, video, vertical=(kind=="short"),
               title=data[kind]["title"], storyboard=data[kind]["storyboard"])
        thumbnail(data[kind]["title"], thumb,
                  visual_dir=video.parent/(video.stem+"_frames")/"visuals",
                  thumbnail_text=data[kind].get("thumbnail_text"))
        files[kind], thumbnails[kind] = video, thumb
    print(json.dumps({
        "day": day, "language": "English", "visual_style": "documentary",
        "narration_style": "natural", "topic": data["topic_title"], "mode": "draft",
        "quality_report": quality_report,
        "files": {k: str(v) for k,v in files.items()},
        "thumbnails": {k: str(v) for k,v in thumbnails.items()},
        "uploads": [],
        "next_step": "Review the documentary visuals, narration, source claims and thumbnails. Uploading is disabled."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["draft"], default="draft")
    run(parser.parse_args().mode)
