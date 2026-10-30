from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .config import CLIENT_SECRET,TOKEN_FILE,SHORT_TIME,LONG_TIME,TIMEZONE
SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
def credentials():
    p=Path(TOKEN_FILE)
    if not p.exists(): raise RuntimeError("No token.json; run python scripts/youtube_auth.py")
    c=Credentials.from_authorized_user_file(str(p),SCOPES)
    if c.expired and c.refresh_token:
        c.refresh(Request());p.write_text(c.to_json())
    if not c.valid: raise RuntimeError("YouTube OAuth expired; re-authorize locally")
    return c
def slot(clock,day):
    tz=ZoneInfo(TIMEZONE); d=datetime.fromisoformat(day).date()
    h,m=map(int,clock.split(":")); local=datetime(d.year,d.month,d.day,h,m,tzinfo=tz)
    if local<=datetime.now(tz):local+=timedelta(days=1)
    return local.astimezone(ZoneInfo("UTC")).isoformat(timespec="seconds").replace("+00:00","Z")
def upload(path,item,mode,publish_at=None):
    yt=build("youtube","v3",credentials=credentials())
    status={"privacyStatus":"private","selfDeclaredMadeForKids":False}
    if mode=="scheduled_upload":status["publishAt"]=publish_at
    body={"snippet":{"title":item["title"][:100],"description":item["description"][:5000],
        "tags":item.get("hashtags",[])[:15],"categoryId":"27","defaultLanguage":"en"},"status":status}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(path),chunksize=-1,resumable=True))
    response=None
    while response is None:_,response=req.next_chunk()
    return {"id":response["id"],"url":"https://youtube.com/watch?v="+response["id"],"status":status}
def upload_pair(files,data,mode,day):
    if mode=="draft":return []
    result=[]
    for kind,clock in [("short",SHORT_TIME),("long",LONG_TIME)]:
        when=slot(clock,day) if mode=="scheduled_upload" else None
        result.append(upload(files[kind],data[kind],mode,when))
    return result
