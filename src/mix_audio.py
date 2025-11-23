
import subprocess
from pathlib import Path
import requests, urllib.parse
from tqdm import tqdm


music_name = "Coldplay"
mp3_path = Path("src") / f"{music_name}.mp3"


video = "https://www.youtube.com/watch?v=1G4isv_Fylg&list=RD1G4isv_Fylg&start_radio=1"


url = urllib.parse.quote(video, "")
clip = f"https://www.clipto.com/api/youtube/mp3?url={url}&csrfToken=8crUK66l-IsnUGoga9wzUzPRRfb4Inx9MEIw"

print(f"⬇️ Baixando música em: {mp3_path}")
r = requests.get(clip, stream=True)
total = int(r.headers.get("content-length", 0))

with open(mp3_path, "wb") as f:
    for chunk in tqdm(r.iter_content(1024), total=total//1024, unit="KB"):
        f.write(chunk)


print(f"🎧 1. Rodando Demucs em: {mp3_path}")
subprocess.run(["demucs", str(mp3_path)])


separated_root = Path("separated")
found_dir = None

for model_dir in separated_root.iterdir():
    candidate = model_dir / music_name
    if candidate.exists():
        found_dir = candidate
        break

if not found_dir:
    print("❌ ERRO: Demucs não produziu a pasta de saída.")
    print("   Verifique se o arquivo realmente existe:", mp3_path)
    exit(1)

print(f"🎛️ 2. Misturando Bateria e Baixo em: {found_dir}")

drums = found_dir / "drums.wav"
bass = found_dir / "bass.wav"
output_file = found_dir / "mixed_audio.wav"

if not drums.exists() or not bass.exists():
    print(f"❌ Arquivos separados não encontrados em: {found_dir}")
    exit(1)


subprocess.run([
    "ffmpeg", "-y",
    "-i", str(drums),
    "-i", str(bass),
    "-filter_complex", "amix=inputs=2:duration=longest",
    str(output_file)
])

print(f"✅ Finalizado: {output_file}")
