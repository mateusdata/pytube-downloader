import streamlit as st
import subprocess
import requests
import urllib.parse
from pathlib import Path
import os
import shutil


st.set_page_config(
    page_title="Mateus Sono",
    layout="wide"
)


BASE_DIR = Path.cwd()
SRC_DIR = BASE_DIR / "src"
SEPARATED_DIR = BASE_DIR / "separated" / "htdemucs"

SRC_DIR.mkdir(exist_ok=True)
SEPARATED_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_name(name: str) -> str:
    """Limpa caracteres especiais e espaços do nome do arquivo."""
    clean = "".join([c if c.isalnum() or c in ('-', '_') else "_" for c in name])
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean.strip("_")

def convert_to_mp3(file_path: Path) -> Path:
    """Converte WAV para MP3 usando ffmpeg."""
    if file_path.suffix == ".mp3":
        return file_path
        
    mp3_path = file_path.with_suffix(".mp3")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(file_path),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(mp3_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if mp3_path.exists() and mp3_path.stat().st_size > 0:
        try:
            file_path.unlink() 
        except Exception:
            pass
        return mp3_path
    return file_path

def download_audio(video_url: str, music_name: str) -> tuple[Path | None, str]:
    """Baixa o áudio do YouTube via API externa."""
    if not music_name:
        music_name = "audio_temp"
        
    final_name = sanitize_name(music_name)
    mp3_path = SRC_DIR / f"{final_name}.mp3"
    
    if mp3_path.exists():
        mp3_path.unlink()

    encoded_url = urllib.parse.quote(video_url, "")
    api_url = f"https://www.clipto.com/api/youtube/mp3?url={encoded_url}&csrfToken=8crUK66l-IsnUGoga9wzUzPRRfb4Inx9MEIw"

    try:
        with st.spinner(f"Baixando {final_name}..."):
            r = requests.get(api_url, stream=True)
            r.raise_for_status()
            with open(mp3_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        return mp3_path, final_name
    except Exception as e:
        st.error(f"Erro no download: {e}")
        return None, final_name

def process_demucs(input_mp3: Path, music_name: str) -> bool:
    """
    Roda o Demucs para separar faixas, converte para MP3 e cria as mixagens.
    """
    with st.spinner(f"Separando faixas de {music_name}..."):
        result = subprocess.run(
            ["demucs", "-n", "htdemucs", str(input_mp3)], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            st.error("Erro no processamento interno.")
            return False

    target_dir = SEPARATED_DIR / input_mp3.stem
    if not target_dir.exists():
        st.error("Diretório de saída não encontrado.")
        return False

    stems = ["vocals.wav", "drums.wav", "bass.wav", "other.wav"]
    mp3_stems = {}

    with st.spinner("Otimizando arquivos (WAV para MP3)..."):
        for stem in stems:
            stem_path = target_dir / stem
            if stem_path.exists():
                new_path = convert_to_mp3(stem_path)
                mp3_stems[stem.replace(".wav", "")] = new_path

    
    vocals = mp3_stems.get("vocals")
    drums = mp3_stems.get("drums")
    bass = mp3_stems.get("bass")
    
    
    mixed_file = target_dir / "mixed_audio.mp3"      
    mixed_voice_file = target_dir / "mixed_audio_voice.mp3" 

    
    if drums and bass and drums.exists() and bass.exists():
        with st.spinner("Criando Mixagem (Bateria + Baixo)..."):
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(drums),
                "-i", str(bass),
                "-filter_complex", "amix=inputs=2:duration=longest",
                "-codec:a", "libmp3lame", "-qscale:a", "2",
                str(mixed_file)
            ]
            subprocess.run(cmd_mix, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    
    if drums and bass and vocals and drums.exists() and bass.exists() and vocals.exists():
        with st.spinner("Criando Mixagem Completa (Voz + Bateria + Baixo)..."):
            cmd_mix_voice = [
                "ffmpeg", "-y",
                "-i", str(vocals),
                "-i", str(drums),
                "-i", str(bass),
                "-filter_complex", "amix=inputs=3:duration=longest", 
                "-codec:a", "libmp3lame", "-qscale:a", "2",
                str(mixed_voice_file)
            ]
            subprocess.run(cmd_mix_voice, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        input_mp3.unlink()
    except:
        pass

    return True



with st.sidebar:
    st.header("Mateus Sono")
    
    input_url = st.text_input("URL do YouTube")
    input_name_user = st.text_input("Nome da musica")

    st.markdown("### Configurações")
    show_mixed = st.toggle("Mostrar Mix (Drums + Bass)", value=True)
    show_stems = st.toggle("Mostrar Faixas Individuais", value=False)
    
    st.write("") 
    
    btn_process = st.button("INICIAR PROCESSAMENTO", type="primary", use_container_width=True)

    if btn_process:
        if not input_url:
            st.warning("O campo URL é obrigatório.")
        elif not input_name_user:
            st.warning("Defina um nome para o projeto.")
        else:
            mp3_file, final_name = download_audio(input_url, input_name_user)
            if mp3_file and mp3_file.exists():
                success = process_demucs(mp3_file, final_name)
                if success:
                    st.success("Processamento finalizado.")
                    st.rerun()


st.title("Dashboard de Músicas Separadas")
st.markdown("Minhas músicas.")
st.divider()

if SEPARATED_DIR.exists():
    subfolders = sorted(
        [f for f in SEPARATED_DIR.iterdir() if f.is_dir()],
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )

    if not subfolders:
        st.info("Nenhuma sessão encontrada.")

    for folder in subfolders:
        with st.container(border=True):
            col_info, col_actions = st.columns([0.7, 0.3])
            
            with col_info:
                st.subheader(folder.name)
            
            mixed = folder / "mixed_audio.mp3"
            
           
            if show_mixed and mixed.exists():
                st.audio(str(mixed), format="audio/mp3")
                
                with open(mixed, "rb") as f:
                    st.download_button(
                        label="DOWNLOAD MIX (BATERIA + BAIXO)",
                        data=f,
                        file_name=f"{folder.name}_mix_drums_bass.mp3",
                        mime="audio/mpeg",
                        key=f"dl_mix_{folder.name}",
                        use_container_width=True
                    )

           
            if show_stems:
                with st.expander("Ver Faixas Individuais e Mix de Voz"):
                    
                    
                    mixed_voice = folder / "mixed_audio_voice.mp3"
                    if mixed_voice.exists():
                        st.markdown("#### Mix Completo (Voz + Bateria + Baixo)")
                        st.audio(str(mixed_voice), format="audio/mp3")
                        with open(mixed_voice, "rb") as f:
                            st.download_button(
                                label="Download Mix Completo",
                                data=f,
                                file_name=f"{folder.name}_mix_voice_drums_bass.mp3",
                                mime="audio/mpeg",
                                key=f"dl_mix_voice_{folder.name}"
                            )
                        st.divider() 

                    
                    stem_list = ["vocals.mp3", "drums.mp3", "bass.mp3", "other.mp3"]
                    for stem_name in stem_list:
                        stem_path = folder / stem_name
                        if stem_path.exists():
                            st.write(f"**{stem_name.replace('.mp3', '').upper()}**")
                            st.audio(str(stem_path), format="audio/mp3")
                            with open(stem_path, "rb") as f:
                                st.download_button(
                                    label="Download",
                                    data=f,
                                    file_name=f"{folder.name}_{stem_name}",
                                    mime="audio/mpeg",
                                    key=f"dl_{stem_name}_{folder.name}"
                                )