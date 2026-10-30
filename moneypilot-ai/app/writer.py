import json
from google import genai
from .config import GEMINI_API_KEY,GEMINI_MODEL
def create_pair(topic):
    if not GEMINI_API_KEY: raise RuntimeError("Set GEMINI_API_KEY in .env")
    client=genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
      "You are MoneyPilot AI, a business and financial-literacy editor. Produce original, accurate, engaging scripts. "
      "Never invent figures, dates, quotes or sources. Do not give personalized investment, tax or legal advice. "
      "Prefer primary sources and include 2-4 source URLs. Output ONLY valid JSON with keys topic_title, short, long. "
      "short must contain title, description, script, hashtags, source_urls; 100-135 spoken words. "
      "long must contain title, description, script, hashtags, source_urls; 800-1050 spoken words. "
      "Use a hook, clear explanations, examples and a useful takeaway. Do not repeat the short verbatim. "
      "Descriptions must say educational content, not personal financial advice. "
      "Topic candidate: "+json.dumps(topic)
    )
    response=client.models.generate_content(model=GEMINI_MODEL,contents=prompt)
    raw=(response.text or "").strip().removeprefix("```json").removesuffix("```").strip()
    data=json.loads(raw)
    for k in ("short","long"):
        for field in ("title","description","script","source_urls"):
            if not data.get(k,{}).get(field): raise ValueError(f"Missing {k}.{field}")
    return data
