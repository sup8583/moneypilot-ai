from pathlib import Path
from io import BytesIO
import html
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .config import CHANNEL, TAGLINE

GOLD = (239, 184, 75)
WHITE = (248, 249, 251)
MUTED = (204, 214, 226)
HEADERS = {"User-Agent": "MoneyPilotAI/2.0 (documentary educational video)"}
PEXELS_API = "https://api.pexels.com/videos/search"


def font(size, bold=False):
    # Kohinoor Telugu with RAQM shapes Telugu vowel signs and conjuncts.
    paths = [
        "/System/Library/Fonts/KohinoorTelugu.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for font_path in paths:
        try:
            if font_path.endswith("KohinoorTelugu.ttc"):
                return ImageFont.truetype(
                    font_path, size, layout_engine=ImageFont.Layout.RAQM
                )
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def clean(value):
    if isinstance(value, dict):
        value = value.get("value", "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()


def wrap(draw, text, f, max_width):
    lines, line = [], ""
    for word in str(text).split():
        test = (line + " " + word).strip()
        if not line or draw.textbbox((0, 0), test, font=f)[2] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _download(url, dest, timeout=35):
    response = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    response.raise_for_status()
    total = 0
    with open(dest, "wb") as handle:
        for chunk in response.iter_content(1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > 120 * 1024 * 1024:
                raise ValueError("Asset exceeds 120 MB download limit")
            handle.write(chunk)
    return dest


def search_pexels_video(query, folder, index):
    """Find a real-world video clip. Requires a free Pexels API key in .env."""
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        return None, None
    try:
        response = requests.get(
            PEXELS_API,
            headers={"Authorization": api_key, **HEADERS},
            params={"query": query, "per_page": 8, "orientation": "landscape"},
            timeout=25,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
        # Prefer HD landscape clips with a useful duration, and avoid tiny preview files.
        candidates = []
        for video in videos:
            for file in video.get("video_files", []):
                width, height = file.get("width") or 0, file.get("height") or 0
                link = file.get("link")
                if link and width >= 1280 and height >= 720 and file.get("file_type") == "video/mp4":
                    candidates.append((width * height, video, file))
        if not candidates:
            return None, None
        candidates.sort(key=lambda item: item[0], reverse=True)
        _, video, file = candidates[0]
        dest = folder / f"scene_{index:02d}.mp4"
        _download(file["link"], dest)
        credit = (
            f"Pexels video by {video.get('user', {}).get('name', 'Unknown creator')} | "
            f"{video.get('url', '')} | Pexels license: https://www.pexels.com/license/"
        )
        return dest, credit
    except Exception as exc:
        print(f"Pexels video unavailable for scene {index}: {exc}")
        return None, None



def _tokens(text):
    stop = {"with","from","that","this","their","about","into","over","under","what","when",
            "where","which","while","after","before","people","close","shot","video","footage",
            "documentary","cinematic","the","and","for"}
    return {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", str(text or "")) if w.lower() not in stop}


def _scene_query(scene, title=""):
    """Use explicit storyboard search phrase only when it is concrete and topic-relevant."""
    narration = str(scene.get("voiceover", ""))
    query = str(scene.get("visual_query", "")).strip()
    qtokens = _tokens(query)
    ntokens = _tokens(narration)
    finance_terms = {
        "bank","banking","branch","atm","cash","currency","loan","credit","debt","deposit",
        "payment","card","transaction","interest","mortgage","finance","financial","stock",
        "trading","exchange","investor","investment","market","economy","inflation","money",
        "company","business","factory","retail","commerce","fintech","digital","wallet",
        "insurance","revenue","profit","capital","bond","fund","central","reserve"
    }
    nature_terms = {"bird","forest","beach","ocean","lake","cloud","mountain","flower","wildlife","desert"}
    # Reject obvious generic/nature-only searches unless narration itself is about them.
    if qtokens & nature_terms and not (ntokens & nature_terms):
        query = ""
    if len(qtokens) < 2 or (not (qtokens & ntokens) and not (qtokens & finance_terms)):
        query = ""
    if not query:
        # Build a grounded query from narration vocabulary rather than using generic finance art.
        preferred = [w for w in re.findall(r"[A-Za-z]{4,}", narration)
                     if w.lower() in finance_terms or w.lower() in {
                         "office","worker","customer","factory","store","shop","computer",
                         "smartphone","terminal","cashier","executive","street","building",
                         "warehouse","server","screen","branch","payment","card"
                     }]
        if preferred:
            query = " ".join(dict.fromkeys(preferred[:5])) + " real world"
        else:
            query = (title + " real business documentary footage").strip()
    return " ".join(query.split()[:8])



def _has_sustained_black(video_path, threshold=0.45):
    """Reject downloaded stock footage containing sustained black frames."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-i", str(video_path),
                "-vf", "blackdetect=d=0.45:pix_th=0.10",
                "-an", "-f", "null", "-"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"Black-frame scan failed: {video_path}")
            return True

        events = re.findall(
            r"black_start:([0-9.]+) black_end:([0-9.]+)",
            result.stderr
        )

        for begin, finish in events:
            black_duration = float(finish) - float(begin)
            if black_duration >= threshold:
                print(
                    f"Rejected black footage: {Path(video_path).name} "
                    f"({black_duration:.2f}s black)"
                )
                return True

        return False

    except Exception as exc:
        print(f"Unable to validate footage {video_path}: {exc}")
        return True


def search_pixabay_video(query, folder, index, seen_ids=None):
    """Download semantically relevant footage and reject clips with black sections."""
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return None, None, None

    seen_ids = seen_ids if seen_ids is not None else set()

    try:
        response = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": api_key,
                "q": query,
                "video_type": "film",
                "per_page": 30,
                "safesearch": "true",
                "min_width": 1280
            },
            headers=HEADERS,
            timeout=25,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])

        qtokens = _tokens(query)
        ranked = []

        for hit in hits:
            hit_id = str(hit.get("id", ""))
            if not hit_id or hit_id in seen_ids:
                continue

            tags = _tokens(hit.get("tags", ""))
            overlap = len(qtokens & tags)
            minimum_overlap = 2 if len(qtokens) >= 3 else 1

            if overlap < minimum_overlap:
                continue

            variants = hit.get("videos", {})
            chosen = next(
                (
                    variants.get(n)
                    for n in ("medium", "small", "large")
                    if (variants.get(n) or {}).get("url")
                    and (variants.get(n) or {}).get("width", 0) >= 720
                    and (variants.get(n) or {}).get("size", 0)
                    <= 100 * 1024 * 1024
                ),
                None
            )

            if not chosen:
                continue

            score = overlap * 10 + min(int(hit.get("duration", 0)), 60) / 20
            ranked.append((score, hit, chosen))

        ranked.sort(key=lambda item: item[0], reverse=True)

        dest = folder / f"scene_{index:02d}.mp4"

        for _, hit, chosen in ranked:
            try:
                _download(chosen["url"], dest)

                # Validate each candidate before accepting it.
                if _has_sustained_black(dest):
                    dest.unlink(missing_ok=True)
                    continue

                hit_id = str(hit.get("id"))
                seen_ids.add(hit_id)

                page = hit.get("pageURL", "https://pixabay.com/videos/")
                user = hit.get("user", "Pixabay contributor")
                credit = (
                    f"Pixabay video by {user} | {page} | "
                    "Pixabay Content License: "
                    "https://pixabay.com/service/license-summary/"
                )

                return dest, credit, hit_id

            except Exception as exc:
                print(
                    f"Rejected Pixabay candidate {hit.get('id')} "
                    f"for scene {index}: {exc}"
                )
                dest.unlink(missing_ok=True)
                continue

        print(f"No black-free Pixabay footage found for scene {index}.")
        return None, None, None

    except Exception as exc:
        print(f"Pixabay video unavailable for scene {index}: {exc}")
        return None, None, None


def search_commons(query, folder, index):
    """Fetch a relevant, reusable photo from Wikimedia Commons and retain attribution."""
    params = {
        "action": "query", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 12,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1920, "format": "json"
    }
    try:
        response = requests.get("https://commons.wikimedia.org/w/api.php", params=params,
                                headers=HEADERS, timeout=25)
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
    except Exception as exc:
        print(f"Wikimedia search unavailable for scene {index}: {exc}")
        return None, None

    # Sort by title/query overlap to reduce unrelated search hits.
    terms = {t.lower() for t in re.findall(r"[a-zA-Z]{4,}", query)}
    ranked = []
    for page in pages.values():
        title = page.get("title", "").lower()
        score = sum(1 for term in terms if term in title)
        ranked.append((score, page))
    ranked.sort(key=lambda item: item[0], reverse=True)
    # Do not use a vaguely related Commons result as a visual match.
    ranked = [item for item in ranked if item[0] >= (2 if len(terms) >= 3 else 1)]

    for _, page in ranked:
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if len(r.content) > 25 * 1024 * 1024:
                continue
            im = Image.open(BytesIO(r.content)).convert("RGB")
            if im.width < 900 or im.height < 500:
                continue
            dest = folder / f"scene_{index:02d}.jpg"
            im.save(dest, "JPEG", quality=94, optimize=True)
            meta = info.get("extmetadata", {})
            artist = clean(meta.get("Artist")) or "Author not listed"
            license_name = clean(meta.get("LicenseShortName")) or "License not listed"
            license_url = clean(meta.get("LicenseUrl"))
            source = page.get("canonicalurl") or page.get("fullurl") or url
            credit = f"{page.get('title', 'Wikimedia Commons image')} | {artist} | {license_name} | {license_url} | {source}"
            return dest, credit
        except Exception:
            continue
    return None, None


def create_fallback_art(size, index):
    """Last-resort original art. A report flags this so it is never mistaken for real footage."""
    w, h = size
    im = Image.new("RGB", size, (7, 17, 31))
    d = ImageDraw.Draw(im)
    for x in range(0, w, max(50, w // 20)):
        d.line((x, 0, x, h), fill=(15, 34, 53), width=1)
    for y in range(0, h, max(50, h // 12)):
        d.line((0, y, w, y), fill=(15, 34, 53), width=1)
    if index % 3 == 0:
        for j, height in enumerate([.22, .34, .48, .62, .78]):
            x = int(w * (.12 + j * .15))
            d.rounded_rectangle((x, int(h*(.82-height)), x+int(w*.075), int(h*.82)),
                                radius=16, fill=(27, 59 + j*7, 83 + j*8))
    elif index % 3 == 1:
        d.ellipse((int(w*.52), int(h*.13), int(w*.92), int(h*.85)),
                  outline=GOLD, width=max(4, w//240))
        d.line((int(w*.12), int(h*.68), int(w*.82), int(h*.28)), fill=(76, 142, 170), width=max(5,w//180))
    else:
        for j in range(5):
            x = int(w*(.18+j*.13))
            d.rectangle((x, int(h*.35), x+int(w*.075), int(h*.82)), fill=(25, 54, 78))
            d.polygon([(x,int(h*.35)),(x+int(w*.037),int(h*.22)),(x+int(w*.075),int(h*.35))], fill=(44,81,105))
    return im


def crop_photo(path, size):
    return ImageOps.fit(Image.open(path).convert("RGB"), size, method=Image.Resampling.LANCZOS,
                        centering=(.52, .45))


def draw_scene(photo, headline, dest, size, index, total, vertical=False):
    w, h = size
    try:
        art = crop_photo(photo, size) if photo else ImageOps.fit(create_fallback_art(size, index), size)
    except Exception:
        art = ImageOps.fit(create_fallback_art(size, index), size)
    shade = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    if vertical:
        sd.rectangle((0, 0, w, int(h*.20)), fill=(3, 9, 17, 105))
        sd.rectangle((0, int(h*.68), w, h), fill=(3, 9, 17, 185))
        pad, headline_y, headline_size = int(w*.07), int(h*.73), 58
    else:
        sd.rectangle((0, 0, w, int(h*.16)), fill=(3, 9, 17, 95))
        sd.rectangle((0, int(h*.69), w, h), fill=(3, 9, 17, 185))
        pad, headline_y, headline_size = int(w*.065), int(h*.74), 56
    art = art.convert("RGBA")
    art.alpha_composite(shade)
    d = ImageDraw.Draw(art)
    d.text((pad, int(h*.055)), CHANNEL.upper(), font=font(max(25,w//52), True), fill=GOLD)
    f = font(headline_size, True)
    lines = wrap(d, headline, f, int(w*.86))[:2]
    y = headline_y
    for line in lines:
        d.text((pad, y), line, font=f, fill=WHITE, stroke_width=2, stroke_fill=(0,0,0,180))
        y += int(headline_size*1.18)
    d.text((pad, int(h*.94)), TAGLINE, font=font(max(18,w//95)), fill=MUTED)
    d.text((int(w*.88), int(h*.94)), f"{index:02d}/{total:02d}",
           font=font(max(18,w//95), True), fill=GOLD)
    art.convert("RGB").save(dest, "JPEG", quality=94, optimize=True)


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _make_video_clip(source, dest, seconds, size, index):
    """Create a scene-length crop from downloaded real footage with a gentle push-in."""
    fps = 30
    frames = max(2, int(seconds * fps))
    # Loop short source clips if needed; trim output to exact scene duration.
    zoom = "min(zoom+0.00045,1.045)" if index % 2 else "max(1.045-on/({frames}*30)*0.045,1.0)".format(frames=frames)
    vf = (f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,"
          f"crop={size[0]}:{size[1]},zoompan=z='{zoom}':d={frames}:s={size[0]}x{size[1]}:fps={fps},"
          f"fade=t=in:st=0:d=0.25,format=yuv420p")
    _run(["ffmpeg","-y","-stream_loop","-1","-i",str(source),"-t",f"{seconds:.3f}",
          "-vf",vf,"-an","-c:v","libx264","-preset","fast","-crf","21",str(dest)])


def render(script, audio, out, vertical=False, title="", storyboard=None):
    """Prefer real stock footage, then relevant documentary photos, and flag all synthetic fallbacks."""
    out = Path(out)
    work = out.parent / (out.stem + "_frames")
    visual_dir = work / "visuals"
    clips_dir = work / "scene_clips"
    visual_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    size = (1080, 1920) if vertical else (1920, 1080)
    scenes = storyboard or []
    if not scenes:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
        scenes = [{"voiceover": s, "on_screen_text": title or "The story behind the money",
                   "visual_query": title or "financial district"} for s in sentences]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
                           capture_output=True, text=True, check=True)
    duration = float(probe.stdout.strip())
    total_words = max(1, sum(len(str(s.get("voiceover", "")).split()) for s in scenes))
    assets, credits, clip_paths = {}, [], []
    pixabay_enabled = bool(os.getenv("PIXABAY_API_KEY", "").strip())
    pexels_enabled = bool(os.getenv("PEXELS_API_KEY", "").strip())
    seen_pixabay_ids = set()
    seen_visual_fingerprints = set()

    def fetch_one(pair):
        i, scene = pair
        query = _scene_query(scene, title)
        if pixabay_enabled:
            clip, credit, media_id = search_pixabay_video(query, visual_dir, i, seen_pixabay_ids)
            if clip:
                return i, "video", clip, credit, query, media_id
        # Use the same topic-grounded query for photos; never substitute broad nature imagery.
        photo, credit = search_commons(query, visual_dir, i)
        if photo:
            return i, "photo", photo, credit, query, None
        return i, "missing", None, None, query, None

    # Search sequentially: the duplicate-ID set is shared, so parallel searches
    # could otherwise select the same Pixabay clip for multiple scenes.
    for i, scene in enumerate(scenes, 1):
        result = fetch_one((i, scene))
        _, kind, asset, credit, query, media_id = result
        assets[i] = (kind, asset, query, media_id)
        if credit:
            credits.append(credit)

    scene_report = []
    for i, scene in enumerate(scenes, 1):
        kind, asset, query, media_id = assets[i]
        words = max(1, len(str(scene.get("voiceover", "")).split()))
        seconds = max(3.0, duration * words / total_words)
        clip = clips_dir / f"scene_{i:02d}.mp4"
        if kind == "video":
            _make_video_clip(asset, clip, seconds, size, i)
            scene_report.append({"scene": i, "asset_type": "real_video", "query": query, "asset": str(asset), "media_id": media_id})
        else:
            frame = work / f"scene_{i:02d}.jpg"
            if kind == "photo":
                draw_scene(asset, scene.get("on_screen_text") or title or "", frame, size, i, len(scenes), vertical)
                scene_report.append({"scene": i, "asset_type": "real_photo", "query": query, "asset": str(asset), "media_id": media_id})
            else:
                draw_scene(None, scene.get("on_screen_text") or title or "", frame, size, i, len(scenes), vertical)
                scene_report.append({"scene": i, "asset_type": "synthetic_fallback", "query": query, "warning": "No relevant stock video or photo passed semantic matching; replace before publishing."})
            fps = 30
            frames = max(2, int(seconds * fps))
            zoom = "min(zoom+0.0007,1.07)" if i % 2 else "max(1.07-on/({frames}*30)*0.07,1.0)".format(frames=frames)
            vf = (f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,"
                  f"crop={size[0]}:{size[1]},zoompan=z='{zoom}':d={frames}:s={size[0]}x{size[1]}:fps={fps},"
                  f"fade=t=in:st=0:d=0.3,format=yuv420p")
            _run(["ffmpeg","-y","-loop","1","-i",str(frame),"-vf",vf,"-frames:v",str(frames),
                  "-an","-c:v","libx264","-preset","fast","-crf","21",str(clip)])
        clip_paths.append(clip)

    concat_file = work / "clips.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clip_paths), encoding="utf-8")
    credits_path = out.parent / "media_credits.txt"
    credits_path.write_text(
        "Media credits — verify each asset's license and attribution requirements before publication:\n" +
        ("\n".join("- " + c for c in credits) if credits else "No externally sourced assets were retrieved.") + "\n",
        encoding="utf-8"
    )
    report_path = out.parent / f"{out.stem}_visual_report.json"
    report_path.write_text(json.dumps({
        "scene_count": len(scene_report),
        "real_video_scenes": sum(x["asset_type"] == "real_video" for x in scene_report),
        "real_photo_scenes": sum(x["asset_type"] == "real_photo" for x in scene_report),
        "synthetic_fallback_scenes": sum(x["asset_type"] == "synthetic_fallback" for x in scene_report),
        "pixabay_enabled": pixabay_enabled,
        "pexels_enabled": pexels_enabled,
        "scenes": scene_report,
        "unique_pixabay_assets": len(seen_pixabay_ids),
        "publishing_note": "Replace all synthetic_fallback scenes; review semantic relevance and verify source licenses before publishing."
    }, indent=2), encoding="utf-8")
    _run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat_file),"-i",str(audio),
          "-map","0:v:0","-map","1:a:0","-vf","fps=30,format=yuv420p",
          "-c:v","libx264","-preset","fast","-crf","21","-c:a","aac","-b:a","192k",
          "-af","loudnorm=I=-16:TP=-1.5:LRA=11","-shortest","-movflags","+faststart",str(out)])

    # Validate output duration and scan for sustained black frames before marking complete.
    probe = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(out)],
        capture_output=True, text=True, check=True)
    rendered_duration = float(probe.stdout.strip())
    if rendered_duration < duration * 0.95:
        raise RuntimeError(f"Rendered video is unexpectedly short ({rendered_duration:.1f}s vs audio {duration:.1f}s).")
    scan = subprocess.run(
        ["ffmpeg","-hide_banner","-i",str(out),"-vf","blackdetect=d=0.45:pix_th=0.10",
         "-an","-f","null","-"], capture_output=True, text=True)
    black_events = re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", scan.stderr)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["rendered_duration_seconds"] = round(rendered_duration, 2)
    report["sustained_black_frames"] = [
        {"start": float(a), "end": float(b), "duration": round(float(b)-float(a), 2)}
        for a,b in black_events
    ]
    report["black_frame_check"] = "failed" if black_events else "passed"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if black_events:
        raise RuntimeError(f"Black-frame check failed: {len(black_events)} sustained black segment(s). See {report_path}")
    print(f"Rendered {len(scenes)} scenes: {sum(x['asset_type']=='real_video' for x in scene_report)} real video, "
          f"{sum(x['asset_type']=='real_photo' for x in scene_report)} real photos, "
          f"{sum(x['asset_type']=='synthetic_fallback' for x in scene_report)} synthetic fallbacks.")
    print(f"Visual report: {report_path}")
    return out


def thumbnail(title, path, visual_dir=None, thumbnail_text=None):
    """Use a real downloaded scene photo as thumbnail focal point."""
    size = (1280, 720)
    candidates = sorted(Path(visual_dir).glob("scene_*.jpg")) if visual_dir else []
    try:
        im = crop_photo(candidates[0], size) if candidates else ImageOps.fit(create_fallback_art(size, 4), size)
    except Exception:
        im = ImageOps.fit(create_fallback_art(size, 4), size)
    im = im.convert("RGBA")
    overlay = Image.new("RGBA", size, (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0,0,1280,720), fill=(3,10,20,65))
    od.rectangle((0,380,1280,720), fill=(3,10,20,175))
    im.alpha_composite(overlay)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((28,28,1252,692), radius=24, outline=GOLD, width=5)
    d.text((72,62), CHANNEL.upper(), font=font(34,True), fill=GOLD)
    hook = (thumbnail_text or title).upper()
    f = font(78, True)
    lines = wrap(d, hook, f, 1090)[:2]
    y = 455 if len(lines) == 1 else 420
    for line in lines:
        d.text((72,y),line,font=f,fill=WHITE,stroke_width=3,stroke_fill=(0,0,0,210))
        y += 92
    d.text((72,640), TAGLINE, font=font(25), fill=MUTED)
    im.convert("RGB").save(path, "JPEG", quality=95, optimize=True)
