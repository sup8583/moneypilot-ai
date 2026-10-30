# MoneyPilot AI

Starter automation for an English faceless business-and-money YouTube channel.

## What it does
- Finds candidate topics from Google News RSS feeds.
- Uses Gemini API to draft an original Short and long-form script with source URLs.
- Generates narration with Edge TTS.
- Creates original typography-led videos with Pillow + FFmpeg.
- Creates thumbnails.
- Optionally uploads privately or schedules uploads through YouTube Data API OAuth.
- Runs daily through GitHub Actions.

## Important limitations
- The first run must be reviewed. AI-generated financial claims must be checked against primary sources.
- New/unverified YouTube API projects may have uploads restricted to private until compliance review. Confirm your project status before relying on scheduled public publishing.
- Free API tiers, quotas, TTS availability and GitHub runner limits can change. This is not guaranteed to remain within ₹500/month.
- This starter intentionally uses original text graphics, not scraped clips/music. It does not promise monetization or views.

## Local setup
1. Install Python 3.11+ and FFmpeg (`brew install ffmpeg` on macOS; `sudo apt install ffmpeg` on Ubuntu).
2. Create a venv and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`, add a Gemini API key from https://aistudio.google.com/ and keep `MODE=draft`.
4. Run:
   ```bash
   python -m app.main
   ```
5. Watch both MP4 files in `output/YYYY-MM-DD/`.

## YouTube OAuth (one-time)
1. In https://console.cloud.google.com/ create a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen. If using External + Testing, add your Google account as a test user.
3. Create OAuth Client ID → Desktop app. Download JSON as `client_secret.json` into the project root.
4. Run `python scripts/youtube_auth.py`, sign in with the Google account that owns the new channel, and grant `youtube.upload`.
5. Keep `client_secret.json` and `token.json private. Never commit or paste them into chat.

## GitHub Actions
1. Create a public GitHub repository named `moneypilot-ai` and push these files.
2. In Settings → Secrets and variables → Actions add:
   - `GEMINI_API_KEY`
   - `YOUTUBE_CLIENT_SECRET_JSON` (contents of client_secret.json)
   - `YOUTUBE_TOKEN_JSON` (contents of token.json)
3. Set repository variable `PIPELINE_MODE=draft`.
4. Run Actions → MoneyPilot daily production → Run workflow → `draft`.
5. Inspect the uploaded workflow artifact. Then test `private_upload`. Use `scheduled_upload` only after the API project is eligible for public scheduling and private upload testing works.
6. Scheduled workflow is 09:30 UTC (15:00 India time), with target slots 19:00 and 21:00 Asia/Kolkata.

## Modes
- `draft`: renders files only.
- `private_upload`: uploads as private for manual inspection.
- `scheduled_upload`: uploads as private with `publishAt` at the configured local times. Public release is subject to YouTube API project eligibility and scheduling rules.

## Editorial rules
Use primary sources (company annual reports, regulators, central banks and government education sites), do not invent figures or quotes, do not give personalized investment/tax/legal advice, disclose affiliate relationships, and use only original or licensed media.
