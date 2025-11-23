import streamlit as st
import subprocess
import requests
import urllib.parse
from pathlib import Path
import os
import shutil

# Configuração da Página
st.set_page_config(
    page_title="Demucs Mixer",
    page_icon="🎧",
    layout="wide"
)

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
BASE_DIR = Path.cwd()
SRC_DIR = BASE_DIR / "src"
SEPARATED_DIR = BASE_DIR / "separated" / "htdemucs"

# Cria os diretórios se não existirem
SRC_DIR.mkdir(exist_ok=True)
SEPARATED_DIR.mkdir(parents=True, exist_ok=True)

# --- FUNÇÕES DE PROCESSAMENTO ---

def download_audio(video_url, music_name):
    """Baixa o áudio usando a API fornecida."""
    mp3_path = SRC_DIR / f"{music_name}.mp3"
    
    # Se o arquivo já existe, remove para baixar novo (ou pode pular se preferir)
    if mp3_path.exists():
        os.remove(mp3_path)

    encoded_url = urllib.parse.quote(video_url, "")
    # Nota: O token CSRF pode expirar. Se parar de funcionar, precisará atualizar.
    api_url = f"https://www.clipto.com/api/youtube/mp3?url={encoded_url}&csrfToken=8crUK66l-IsnUGoga9wzUzPRRfb4Inx9MEIw"

    try:
        with st.spinner(f"⬇️ Baixando '{music_name}'..."):
            r = requests.get(api_url, stream=True)
            r.raise_for_status()
            
            with open(mp3_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        return mp3_path
    except Exception as e:
        st.error(f"Erro no download: {e}")
        return None

def process_demucs(mp3_path, music_name):
    """Roda o Demucs e o FFmpeg."""
    
    # 1. Rodar Demucs
    with st.spinner("🎧 Rodando Demucs (Separando faixas)... Isso pode demorar."):
        # Chama o demucs via subprocess
        # O output padrão do demucs costuma ser 'separated/htdemucs/{nome_arquivo}'
        result = subprocess.run(["demucs", str(mp3_path)], capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error("Erro ao rodar Demucs:")
            st.code(result.stderr)
            return False

    # 2. Localizar diretório de saída
    # O Demucs cria uma pasta com o nome do arquivo original (sem extensão) dentro de separated/htdemucs
    # Como baixamos como "{music_name}.mp3", a pasta será "{music_name}"
    target_dir = SEPARATED_DIR / music_name
    
    if not target_dir.exists():
        st.error(f"❌ A pasta de saída não foi encontrada: {target_dir}")
        return False

    # 3. Misturar Bateria e Baixo
    drums = target_dir / "drums.wav"
    bass = target_dir / "bass.wav"
    output_file = target_dir / "mixed_audio.wav"

    if not drums.exists() or not bass.exists():
        st.warning(f"⚠️ Não foi possível encontrar drums.wav ou bass.wav em {target_dir}")
        return False

    with st.spinner("🎛️ Misturando Bateria e Baixo..."):
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-i", str(drums),
            "-i", str(bass),
            "-filter_complex", "amix=inputs=2:duration=longest",
            str(output_file)
        ]
        subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return output_file

# --- INTERFACE (SIDEBAR) ---

with st.sidebar:
    st.header("🎛️ Novo Processamento")
    
    input_url = st.text_input("🔗 Link do YouTube", placeholder="https://youtube.com/...")
    input_name = st.text_input("📝 Nome da Música (sem espaços preferencialmente)", placeholder="Ex: Coldplay_Yellow")
    
    btn_processar = st.button("🚀 Baixar e Separar", type="primary")

    if btn_processar:
        if not input_url or not input_name:
            st.warning("Preencha o Link e o Nome!")
        else:
            # Limpa o nome para evitar erros de sistema de arquivo
            clean_name = "".join([c for c in input_name if c.isalnum() or c in (' ', '_', '-')]).strip()
            
            path_mp3 = download_audio(input_url, clean_name)
            
            if path_mp3:
                final_mix = process_demucs(path_mp3, clean_name)
                if final_mix:
                    st.success(f"✅ Sucesso! '{clean_name}' processada.")
                    st.rerun() # Recarrega a página para mostrar na lista

# --- INTERFACE (ÁREA PRINCIPAL) ---

st.title("📂 Galeria de Mixes (Bateria + Baixo)")
st.markdown("Lista de arquivos `mixed_audio.wav` encontrados em `separated/htdemucs/`")

st.divider()

# Listagem de arquivos usando Pathlib (mais robusto que regex para arquivos)
# Ele itera sobre os diretórios dentro de htdemucs
found_any = False

if SEPARATED_DIR.exists():
    # Lista todas as subpastas
    subfolders = [f for f in SEPARATED_DIR.iterdir() if f.is_dir()]
    
    # Ordena por data de modificação (mais recentes primeiro)
    subfolders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    for folder in subfolders:
        mix_file = folder / "mixed_audio.wav"
        
        # Verifica se o arquivo mix existe dentro da pasta
        if mix_file.exists():
            found_any = True
            
            # Cria um card visual para cada música
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader(f"🎵 {folder.name}")
                    st.audio(str(mix_file), format="audio/wav")
                
                with col2:
                    st.info(f"📁 {folder.name}")
                    # Botão opcional para download direto
                    with open(mix_file, "rb") as file:
                        st.download_button(
                            label="⬇️ Download WAV",
                            data=file,
                            file_name=f"{folder.name}_drum_bass.wav",
                            mime="audio/wav",
                            key=f"dl_{folder.name}"
                        )
            st.divider()

if not found_any:
    st.info("Nenhuma música processada encontrada ainda. Use a barra lateral para adicionar!")