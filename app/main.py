import argparse,json
from pathlib import Path
from datetime import date
from .research import find_topic
from .writer import create_pair
from .voice import make_voice
from .video import render,thumbnail
from .youtube import upload_pair
from .config import MODE
def run(mode=None):
    mode=mode or MODE
    if mode not in {"draft","private_upload","scheduled_upload"}:raise ValueError("Invalid MODE")
    day=date.today().isoformat(); out=Path("output")/day;out.mkdir(parents=True,exist_ok=True)
    topic=find_topic(); data=create_pair(topic)
    (out/"content.json").write_text(json.dumps({"topic":topic,**data},indent=2),encoding="utf-8")
    files={}
    for kind in ("short","long"):
        audio=out/f"{kind}.mp3";video=out/f"{kind}.mp4";thumb=out/f"{kind}.jpg"
        make_voice(data[kind]["script"],audio)
        render(data[kind]["script"],audio,video,vertical=(kind=="short"))
        thumbnail(data[kind]["title"],thumb);files[kind]=video
    uploads=upload_pair(files,data,mode,day)
    (out/"upload_results.json").write_text(json.dumps(uploads,indent=2))
    print(json.dumps({"day":day,"topic":data["topic_title"],"mode":mode,"files":{k:str(v) for k,v in files.items()},"uploads":uploads},indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["draft","private_upload","scheduled_upload"])
    args=p.parse_args();run(args.mode)
