import requests, urllib.parse
from tqdm import tqdm

video="https://www.youtube.com/watch?v=kNJPalON82E&list=RDkNJPalON82E&start_radio=1"
music_name="vanessa.mp3"

url=urllib.parse.quote(video, "")
clip=f"https://www.clipto.com/api/youtube/mp3?url={url}&csrfToken=8crUK66l-IsnUGoga9wzUzPRRfb4Inx9MEIw"

r=requests.get(clip, stream=True)
total=int(r.headers.get('content-length', 0))

with open(f"src/{music_name}", "wb") as f:
    for chunk in tqdm(r.iter_content(1024), total=total//1024, unit="KB"):
        f.write(chunk)
