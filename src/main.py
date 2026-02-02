import streamlit as st
import subprocess
import requests
import urllib.parse
from pathlib import Path
import os
import shutil
import base64
import streamlit.components.v1 as components

BASE_DIR = Path.cwd()
SRC_DIR = BASE_DIR / "src"
SEPARATED_DIR = BASE_DIR / "separated" / "htdemucs"

SRC_DIR.mkdir(exist_ok=True)
SEPARATED_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="Mateus Sono IA",
    layout="wide"
)

def sanitize_name(name: str) -> str:
    clean = "".join([c if c.isalnum() or c in ('-', '_') else "_" for c in name])
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean.strip("_")

def convert_to_mp3(file_path: Path) -> Path:
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
    with st.spinner(f"Separando faixas de {music_name}..."):
        result = subprocess.run(
            ["demucs", "-n", "htdemucs", str(input_mp3)], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            
            st.error(f"Erro no processamento: {result.stderr}")
            with st.expander("Detalhes do erro"):
                st.code(result.stdout)
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


    if input_mp3.exists():
        try:
            input_mp3.unlink()
        except Exception as e:
            st.warning(f"Não foi possível remover arquivo original: {e}")

    return True

if "selected_music" not in st.session_state:
    st.session_state.selected_music = None

def handle_delete(folder_path):
    import time
    try:
        if folder_path.exists():
            shutil.rmtree(folder_path)
        
        st.session_state.selected_music = None
        time.sleep(0.1)
        st.toast("Música apagada com sucesso!", icon="✅")
        time.sleep(0.5)
    except Exception as e:
        st.toast(f"Erro ao apagar: {e}", icon="❌")
        time.sleep(1)

def get_stem_player_html(stems_dict):
    audio_data = {}
    
    for name, path in stems_dict.items():
        if path.exists():
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                audio_data[name] = f"data:audio/mp3;base64,{b64}"
    
    if not audio_data:
        return "<div>Sem áudio</div>"

    html_code = f"""
    <style>
        .player-container {{
            background: #262730;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #4f4f4f;
            color: #FAFAFA;
            font-family: sans-serif;
        }}
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            align-items: center;
        }}
        .play-btn {{
            background: #2196F3;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 16px;
            transition: background 0.2s;
            width: 140px;
        }}
        .play-btn:hover {{
            background: #1976D2;
        }}
        .track-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .track-card {{
            background: #0E1117;
            padding: 15px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #333;
        }}
        .track-name {{
            font-weight: bold;
            font-size: 14px;
        }}
        
        .switch {{
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }}
        .switch input {{ 
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }}
        .slider:before {{
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }}
        input:checked + .slider {{
            background-color: #2196F3;
        }}
        input:checked + .slider:before {{
            transform: translateX(26px);
        }}
        input[disabled] + .slider {{
            background-color: #555;
            cursor: not-allowed;
        }}
        
        input[type=range] {{
            width: 100%;
            cursor: pointer;
        }}
    </style>

    <div class="player-container">
        <h3 style="margin-top:0; margin-bottom: 20px;">🎚️ Mixer Multifaixa</h3>
        
        <div class="controls">
            <button id="mainPlayBtn" class="play-btn" onclick="playAll()">▶ PLAY</button>
            <input type="range" id="progressBar" value="0" oninput="seekAll(this.value)">
        </div>

        <div class="track-grid">
    """

    labels_pt = {
        "vocals": "VOZ",
        "drums": "BATERIA",
        "bass": "BAIXO",
        "other": "OUTROS"
    }

    for name, b64_src in audio_data.items():
        label = labels_pt.get(name, name.upper())
        html_code += f"""
        <div class="track-card">
            <span class="track-name">{label}</span>
            <label class="switch">
                <input type="checkbox" id="chk_{name}" checked onchange="toggleMute('{name}')">
                <span class="slider"></span>
            </label>
            <audio id="audio_{name}" src="{b64_src}" preload="auto" ontimeupdate="updateProgress()"></audio>
        </div>
        """

    html_code += """
        </div>
    </div>

    <script>
        const tracks = document.querySelectorAll('audio');
        const progress = document.getElementById('progressBar');
        const playBtn = document.getElementById('mainPlayBtn');
        var isPlaying = false;

        function playAll() {
            if (!isPlaying) {
                tracks.forEach(t => t.play());
                playBtn.innerText = "⏸ PAUSE";
                isPlaying = true;
            } else {
                tracks.forEach(t => t.pause());
                playBtn.innerText = "▶ PLAY";
                isPlaying = false;
            }
        }

        function seekAll(val) {
            if(tracks.length > 0) {
                const duration = tracks[0].duration;
                if(duration) {
                    const time = (val / 100) * duration;
                    tracks.forEach(t => t.currentTime = time);
                }
            }
        }

        function updateProgress() {
            if (tracks.length > 0 && tracks[0].duration) {
                const val = (tracks[0].currentTime / tracks[0].duration) * 100;
                progress.value = val;
            }
        }

        function toggleMute(name) {
            const audio = document.getElementById('audio_' + name);
            const chk = document.getElementById('chk_' + name);
            audio.muted = !chk.checked;
        }
    </script>
    """
    return html_code

def render_list_view(subfolders):
    st.markdown("### 🎵 Minhas Músicas")
    st.caption("Selecione uma música para abrir o mixer multifaixa")
    st.divider()

    if not subfolders:
        st.info("📂 Nenhuma música processada ainda. Use o menu lateral para começar!")
        return

    for folder in subfolders:
        with st.container(border=True):
            col_icon, col_name, col_action = st.columns([0.05, 0.7, 0.25])
            
            with col_icon:
                st.markdown("### 🎼")
            
            with col_name:
                st.markdown(f"**{folder.name}**")
                
                stem_count = len(list(folder.glob("*.mp3")))
                if stem_count > 0:
                    st.caption(f"🎚️ {stem_count} faixas disponíveis")
            
            with col_action:
                if st.button("▶ ABRIR", key=f"open_{folder.name}", use_container_width=True, type="primary"):
                    st.session_state.selected_music = folder.name
                    st.rerun()

def render_detail_view(folder_path):
    if not folder_path.exists():
        st.error("Pasta não encontrada.")
        if st.button("Voltar"):
            st.session_state.selected_music = None
            st.rerun()
        return

    col_back, col_title, col_delete = st.columns([0.1, 0.7, 0.2])
    
    with col_back:
        if st.button("⬅", help="Voltar para lista", use_container_width=True):
            st.session_state.selected_music = None
            st.rerun()
    
    with col_title:
        st.markdown(f"### 🎵 {folder_path.name}")
    
    with col_delete:
        st.markdown("""
            <style>
            div[data-testid="stPopover"] > button[kind="secondary"] {
                 background-color: #FF4B4B !important;
                 border-color: #FF4B4B !important;
                 color: white !important;
            }
            div[data-testid="stPopover"] > button {
                 background-color: #FF4B4B !important;
                 border-color: #FF4B4B !important;
                 color: white !important;
            }
            div[data-testid="stPopoverBody"] button[kind="primary"] {
                 background-color: #FF4B4B !important;
                 border-color: #FF4B4B !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        with st.popover("APAGAR", help="Deletar música", use_container_width=True):
            st.button("CONFIRMAR EXCLUSÃO", type="primary", on_click=handle_delete, args=(folder_path,), use_container_width=True)

    st.divider()

    stems_dict = {
        "vocals": folder_path / "vocals.mp3",
        "drums": folder_path / "drums.mp3",
        "bass": folder_path / "bass.mp3",
        "other": folder_path / "other.mp3"
    }
    
    if all(p.exists() for p in stems_dict.values()):
        st.markdown("#### 🎚️ Mixer Multifaixa")
        components.html(get_stem_player_html(stems_dict), height=400)
    else:
        st.warning("⚠️ Arquivos de áudio não encontrados.")

    st.divider()
    
    mixed = folder_path / "mixed_audio.mp3"
    
    if mixed.exists():
        st.markdown("#### 💿 Mix Automático")
        with st.container(border=True):
            col_play, col_download = st.columns([0.7, 0.3])
            
            with col_play:
                st.caption("🥁 Bateria + 🎸 Baixo")
                st.audio(str(mixed), format="audio/mp3")
            
            with col_download:
                st.write("")
                st.write("")
                with open(mixed, "rb") as f:
                    st.download_button(
                        label="⬇ Baixar Mix",
                        data=f,
                        file_name=f"{folder_path.name}_mix.mp3",
                        mime="audio/mpeg",
                        use_container_width=True
                    )

    st.divider()
    st.markdown("#### 📦 Faixas Individuais")
    
    stem_list = ["vocals.mp3", "drums.mp3", "bass.mp3", "other.mp3"]
    labels_pt = {
        "vocals.mp3": ("🎤", "VOZ"), 
        "drums.mp3": ("🥁", "BATERIA"), 
        "bass.mp3": ("🎸", "BAIXO"), 
        "other.mp3": ("🎹", "OUTROS")
    }
    
    cols = st.columns(2)
    for idx, stem_name in enumerate(stem_list):
        stem_path = folder_path / stem_name
        if stem_path.exists():
            with cols[idx % 2]:
                with st.container(border=True):
                    icon, label = labels_pt.get(stem_name, ("🎵", stem_name))
                    st.markdown(f"**{icon} {label}**")
                    
                    with open(stem_path, "rb") as f:
                        st.download_button(
                            label="⬇ Download",
                            data=f,
                            file_name=f"{folder_path.name}_{stem_name}",
                            mime="audio/mpeg",
                            key=f"dl_{stem_name}_{folder_path.name}",
                            use_container_width=True
                        )

with st.sidebar:
    st.header("Mateus Sono IA")
    
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    if "input_url_value" not in st.session_state:
        st.session_state.input_url_value = ""
    
    if "input_name_value" not in st.session_state:
        st.session_state.input_name_value = ""
    
    input_url = st.text_input(
        "URL do YouTube", 
        value=st.session_state.input_url_value, 
        key="url_input",
        placeholder="Ex: youtube.com/watch?v=video-url"
    )
    input_name_user = st.text_input(
        "Nome da musica", 
        value=st.session_state.input_name_value, 
        key="name_input",
        placeholder="Ex: Sem Limites"
    )
    
    st.write("") 
    
    if st.session_state.processing:
        st.button("⏳ Processando...", type="primary", disabled=True, use_container_width=True)
        
        input_url = st.session_state.input_url_value
        input_name_user = st.session_state.input_name_value
        
        if input_url and input_name_user:
            mp3_file, final_name = download_audio(input_url, input_name_user)
            if mp3_file and mp3_file.exists():
                success = process_demucs(mp3_file, final_name)
                if success:
                    st.success("Processamento finalizado!")
                    st.session_state.processing = False
                    st.session_state.input_url_value = ""
                    st.session_state.input_name_value = ""
                    st.rerun()
                else:
                    st.session_state.processing = False
                    st.rerun()
            else:
                st.session_state.processing = False
                st.rerun()
    else:
        if st.button("INICIAR PROCESSAMENTO", type="primary", use_container_width=True):
            if not input_url:
                st.warning("O campo URL é obrigatório.")
            elif not input_name_user:
                st.warning("Defina um nome para o projeto.")
            else:
                st.session_state.input_url_value = input_url
                st.session_state.input_name_value = input_name_user
                st.session_state.processing = True
                st.rerun()

if SEPARATED_DIR.exists():
    subfolders = sorted(
        [f for f in SEPARATED_DIR.iterdir() if f.is_dir()],
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )
else:
    subfolders = []

if st.session_state.selected_music:
    target_folder = SEPARATED_DIR / st.session_state.selected_music
    render_detail_view(target_folder)
else:
    render_list_view(subfolders)