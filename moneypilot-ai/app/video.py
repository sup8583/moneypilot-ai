from pathlib import Path
import subprocess,re
from PIL import Image,ImageDraw,ImageFont
from .config import CHANNEL,TAGLINE
BG=(9,17,31); GOLD=(239,184,75); WHITE=(245,247,250); MUTED=(160,174,192)
def getfont(n,b=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if b else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(p,n)
    except:return ImageFont.load_default()
def chunks(text,limit):
    out=[]; cur=[]
    for s in re.split(r'(?<=[.!?])\s+',text.strip()):
        words=s.split()
        if cur and len(cur)+len(words)>limit: out.append(" ".join(cur));cur=[]
        cur+=words
    if cur:out.append(" ".join(cur))
    return out or [text]
def draw_card(text,path,size,i,total):
    w,h=size; im=Image.new("RGB",size,BG); d=ImageDraw.Draw(im)
    d.rounded_rectangle((int(w*.05),int(h*.06),int(w*.95),int(h*.94)),radius=30,outline=(55,72,98),width=4)
    d.text((int(w*.09),int(h*.11)),CHANNEL.upper(),font=getfont(max(24,w//55),True),fill=GOLD)
    f=getfont(max(34,int(w*.05)),True); words=text.split(); lines=[]; line=""
    for word in words:
        test=(line+" "+word).strip()
        if d.textbbox((0,0),test,font=f)[2]<w*.78:line=test
        else:lines.append(line);line=word
    if line:lines.append(line)
    y=(h-len(lines)*int(f.size*1.35))//2
    for line in lines:
        box=d.textbbox((0,0),line,font=f);d.text(((w-(box[2]-box[0]))//2,y),line,font=f,fill=WHITE);y+=int(f.size*1.35)
    d.text((int(w*.09),int(h*.86)),TAGLINE,font=getfont(max(18,w//85)),fill=MUTED)
    d.text((int(w*.85),int(h*.86)),f"{i}/{total}",font=getfont(max(18,w//85),True),fill=GOLD)
    im.save(path)
def render(script,audio,out,vertical=False):
    out=Path(out); work=out.parent/(out.stem+"_frames");work.mkdir(parents=True,exist_ok=True)
    size=(1080,1920) if vertical else (1920,1080); parts=chunks(script,10 if vertical else 18)
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],capture_output=True,text=True,check=True)
    duration=float(probe.stdout.strip()); total=max(1,len(script.split())); listing=work/"concat.txt"
    with listing.open("w") as f:
        for i,part in enumerate(parts,1):
            img=work/f"{i:04}.png";draw_card(part,img,size,i,len(parts))
            secs=max(2,duration*len(part.split())/total)
            f.write(f"file '{img.resolve().as_posix()}'\nduration {secs:.3f}\n")
        f.write(f"file '{img.resolve().as_posix()}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-i",str(audio),
        "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","25",
        "-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(out)],check=True,capture_output=True)
    return out
def thumbnail(title,path):
    im=Image.new("RGB",(1280,720),BG);d=ImageDraw.Draw(im)
    d.text((80,70),CHANNEL.upper(),font=getfont(38,True),fill=GOLD)
    f=getfont(76,True); words=title.upper().split(); lines=[];line=""
    for word in words:
        test=(line+" "+word).strip()
        if d.textbbox((0,0),test,font=f)[2]<1120:line=test
        else:lines.append(line);line=word
    if line:lines.append(line)
    y=250
    for line in lines[:4]:d.text((80,y),line,font=f,fill=WHITE);y+=95
    d.text((80,635),TAGLINE,font=getfont(28),fill=MUTED);im.save(path)
