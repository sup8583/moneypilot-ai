from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from app.config import CLIENT_SECRET,TOKEN_FILE
SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
if not Path(CLIENT_SECRET).exists():raise SystemExit("Download a Desktop OAuth client JSON and save it as client_secret.json")
flow=InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET,SCOPES)
creds=flow.run_local_server(port=0,access_type="offline",prompt="consent")
Path(TOKEN_FILE).write_text(creds.to_json(),encoding="utf-8")
print("OAuth token saved. Keep token.json private.")
