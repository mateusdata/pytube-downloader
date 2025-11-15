from pytubefix import YouTube
from pytubefix.cli import on_progress

url = input('Digite a URL do video do Youtube:')

yt = YouTube(url, on_progress_callback=on_progress)
ys = yt.streams.get_highest_resolution()

print(yt.title)

ys.download(output_path="./videos")
