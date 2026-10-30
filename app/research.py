import feedparser
from urllib.parse import quote
SEEDS=[
"how Costco makes money business model","how McDonalds makes money business model",
"how Amazon makes money revenue streams","compound interest explained",
"why startups fail case study","how banks make money explained",
"luxury brands business model","how Netflix makes money",
"inflation explained purchasing power","payment networks business model"
]
def find_topic():
    for seed in SEEDS:
        url="https://news.google.com/rss/search?q="+quote(seed)+"&hl=en-US&gl=US&ceid=US:en"
        feed=feedparser.parse(url)
        for item in feed.entries[:5]:
            title=getattr(item,"title","").strip()
            link=getattr(item,"link","")
            if title and link:
                return {"title":title,"url":link}
    return {"title":"How compound interest works: a practical money explainer",
            "url":"https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator"}
