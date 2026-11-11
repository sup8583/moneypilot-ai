import os
from dotenv import load_dotenv
load_dotenv()

def e(key, default=""):
    return os.getenv(key, default).strip()

GEMINI_API_KEY = e("GEMINI_API_KEY")
GEMINI_MODEL = e("GEMINI_MODEL", "gemini-2.5-flash")
MODE = e("MODE", "draft")
CLIENT_SECRET = e("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = e("YOUTUBE_TOKEN_FILE", "token.json")
SHORT_TIME = e("SHORT_PUBLISH_TIME", "19:00")
LONG_TIME = e("LONG_PUBLISH_TIME", "21:00")
TIMEZONE = e("TIMEZONE", "Asia/Kolkata")
CHANNEL = e("CHANNEL_NAME", "MoneyPilot AI")
TAGLINE = e("CHANNEL_TAGLINE", "Understand Money. Build Wealth.")
