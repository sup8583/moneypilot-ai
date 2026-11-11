import json
import re
import time
from google import genai
from .config import GEMINI_API_KEY, GEMINI_MODEL
from .quality import validate_pair


def _parse_json(raw):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\\s*", "", raw, flags=re.I)
    raw = re.sub(r"\\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object")
    return json.loads(raw[start:end + 1])



def _generate(client, prompt):
    model = GEMINI_MODEL
    max_attempts = 5

    print(f"Using configured Gemini model: {model}")

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return _parse_json(response.text)

        except Exception as exc:
            message = str(exc).lower()
            status = getattr(exc, "code", None) or getattr(exc, "status_code", None)

            retryable = (
                status in (429, 500, 502, 503, 504)
                or any(token in message for token in (
                    "429", "500", "502", "503", "504",
                    "unavailable", "high demand",
                    "temporarily", "resource exhausted",
                    "rate limit"
                ))
            )

            if not retryable or attempt == max_attempts - 1:
                raise RuntimeError(
                    f"Gemini generation failed after {attempt + 1} "
                    f"attempt(s). Model: {model}. Error: {exc}"
                ) from exc

            delay = min(10 * (2 ** attempt), 60)

            print(
                f"Gemini temporarily unavailable. "
                f"Retry {attempt + 1}/{max_attempts - 1} "
                f"in {delay} seconds..."
            )
            time.sleep(delay)

    raise RuntimeError("Gemini generation failed.")

def create_pair(topic):
    if not GEMINI_API_KEY:
        raise RuntimeError("Set GEMINI_API_KEY in .env")
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
You are the executive producer of MoneyPilot AI, an English-only premium financial documentary YouTube channel.
Create TWO publication-quality scripts and precise documentary storyboards from this topic candidate:
{json.dumps(topic, ensure_ascii=False)}

EDITORIAL STANDARD:
- Natural, confident documentary narration. Clear, warm, measured, never robotic or salesy.
- Strong curiosity hook in the first sentence; no generic "welcome back" opening.
- Accuracy over drama. Never invent numbers, dates, quotes, sources, causation or company claims.
- Prioritize primary sources: annual reports, investor relations, SEC filings, regulators, central banks, official statistics, IMF, World Bank, OECD and peer-reviewed research.
- Distinguish facts, interpretation and hypothetical examples. Never give personalized financial, investment, tax or legal advice.
- Long video narrative: hook, stakes, context, how it works, real-world example, counterpoint/limitations, implications and memorable conclusion.
- Short is a self-contained story with one clear insight, not a teaser that withholds the answer.
- Avoid repeated conclusions, filler, unsupported claims, clickbait and jargon without explanation.

OUTPUT JSON keys: topic_title, short, long.
Each video: title, thumbnail_text, description, script, hashtags, source_urls, storyboard.
- short script 105-135 words; long script 1,100-1,300 words.
- short storyboard 7-10 scenes; long storyboard 45-65 scenes.
- Each scene has exactly voiceover, on_screen_text, visual_query.
- Scene voiceovers must reproduce the full script exactly, in order, with no omissions or added words.
- Each scene should cover roughly 15-28 spoken words (short scenes 10-18 words). Each on_screen_text is 2-5 words only; it is an editorial caption, not a paragraph.
- visual_query must describe a visible, filmable object/action directly supported by that scene's voiceover. Use concrete phrases such as "bank teller counting cash", "customer tapping contactless payment card", "small business owner reviewing invoices", "stock exchange trading floor", "factory assembly line". Avoid vague phrases such as "money concept", "business success", "financial future", "economy background". Never use nature, wildlife, clouds, beaches, landscapes or abstract patterns unless narration explicitly describes them.
- Prioritize the actual company, product, institution, industry, place, person-at-work or transaction described in the narration. Do not use generic office footage as a substitute for a specific institution or activity.
- Do not repeat the same visual subject in adjacent scenes. Use charts only when explaining a specific number or mechanism; describe the chart's actual data in the query.
- If a scene is conceptual and no honest live-action visual exists, use an explicit "original graphic:" visual_query describing a specific diagram or data visualization. Do not invent footage.
- thumbnail_text must be a compelling 2-5 word hook, not the full title.
- Titles under 75 characters preferred, max 100. Description includes education-only disclaimer.
- Include 2-4 real relevant HTTPS source URLs, favor primary sources. Do not fabricate URLs. Use official source landing pages if exact report URLs are uncertain.
- 3-5 hashtags without #.
- English only.

Return only valid JSON. Do not include markdown fences or commentary.
"""
    data = _generate(client, prompt)
    data["language"] = "en"
    data["language_name"] = "English"
    data["quality_report"] = validate_pair(data)
    return data
