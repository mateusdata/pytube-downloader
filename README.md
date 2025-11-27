# sound-ai

A Python project for downloading YouTube videos using pytube and separating audio tracks.

## Setup

This project uses `uv` for dependency management. Make sure you have `uv` installed on your system.

### Installing uv

If you don't have `uv` installed, you can install it using pip:

```bash
pip install uv
```

### Installation

1. Clone the repository
2. Create and activate virtual environment:
    ```bash
    # Create virtual environment
    uv venv
    
    # Activate virtual environment (Fish shell)
    source .venv/bin/activate.fish
    
    # Activate virtual environment (Bash/Zsh)
    source .venv/bin/activate
    ```
3. Install dependencies:
    ```bash
    uv pip install .
    ```
4. Run the Streamlit web version for audio track separation:
    ```bash
    streamlit run src/streamlit.py
    ```


