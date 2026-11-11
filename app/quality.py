import re
from urllib.parse import urlparse

def word_count(text):
    return len(re.findall(r"\b[\w’'-]+\b", str(text or "")))

def validate_pair(data):
    errors = []
    if not isinstance(data, dict):
        raise ValueError("Gemini did not return a JSON object.")
    if not data.get("topic_title"):
        errors.append("Missing topic_title")
    for kind, low, high, scenes_low, scenes_high in (
        ("short", 95, 145, 7, 10), ("long", 1000, 1400, 45, 65)
    ):
        item = data.get(kind) or {}
        for field in ("title","thumbnail_text","description","script","source_urls"):
            if not item.get(field):
                errors.append(f"Missing {kind}.{field}")
        if len(str(item.get("title",""))) > 100:
            errors.append(f"{kind}.title exceeds YouTube's 100-character limit")
        if not 2 <= len(str(item.get("thumbnail_text","")).split()) <= 5:
            errors.append(f"{kind}.thumbnail_text must contain 2-5 words")
        count = word_count(item.get("script"))
        if not low <= count <= high:
            errors.append(f"{kind}.script has {count} words; expected {low}-{high}")
        urls = item.get("source_urls") or []
        if not isinstance(urls,list) or not 2 <= len(urls) <= 4:
            errors.append(f"{kind}.source_urls must contain 2-4 URLs")
        else:
            for url in urls:
                parsed = urlparse(str(url))
                if parsed.scheme != "https" or not parsed.netloc:
                    errors.append(f"Invalid source URL in {kind}: {url}")
        scenes = item.get("storyboard") or []
        if not isinstance(scenes,list) or not scenes_low <= len(scenes) <= scenes_high:
            errors.append(f"{kind}.storyboard must contain {scenes_low}-{scenes_high} scenes")
        else:
            scene_voice = []
            for index, scene in enumerate(scenes,1):
                if not isinstance(scene,dict) or not all(scene.get(k) for k in ("voiceover","on_screen_text","visual_query")):
                    errors.append(f"{kind}.storyboard scene {index} is incomplete")
                    continue
                if len(str(scene["on_screen_text"]).split()) > 5:
                    errors.append(f"{kind}.storyboard scene {index} headline is too long")
                scene_voice.append(str(scene["voiceover"]).strip())
            joined = " ".join(scene_voice)
            script = re.sub(r"\s+"," ",str(item.get("script",""))).strip()
            joined = re.sub(r"\s+"," ",joined).strip()
            if joined != script:
                errors.append(f"{kind}.storyboard voiceover must reproduce the script exactly")
    if errors:
        raise ValueError("Content quality gate failed:\n- " + "\n- ".join(errors))
    return {
        "status":"passed",
        "short_words":word_count(data["short"]["script"]),
        "long_words":word_count(data["long"]["script"]),
        "short_scenes":len(data["short"]["storyboard"]),
        "long_scenes":len(data["long"]["storyboard"]),
        "note":"URL format is checked; source claims still require independent verification before publication."
    }
