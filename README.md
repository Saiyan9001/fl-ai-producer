# 🎧 FL-AI-Producer
**An Intelligent AI Assistant for FL Studio**  
Windows 11 · FL Studio 21.2+ · Python 3.11

---

## 🧠 Overview
**FL-AI-Producer** is an AI-powered assistant designed to interact directly with **FL Studio** through its official Python scripting APIs.  
It allows you to:
- Control plugin parameters (knobs, sliders, automation)
- Insert notes directly into the Piano Roll
- Analyze and transcribe audio (MP3/WAV) into multi-layer MIDI
- Suggest plugin parameter adjustments based on audio timbre
- Work either through direct FL Studio API integration or via virtual MIDI fallback

The goal: a self-contained “AI Producer” capable of creating, arranging, and sound-designing within FL Studio—hands-free.

---

## 🏗️ Architecture

The project consists of **two main components** that communicate over **localhost ZeroMQ (127.0.0.1:5555)** using validated JSON messages.

### 1) `controller_app` — AI & Desktop Controller
A standalone **PySide6 desktop application** that:
- Hosts an **IPC ZeroMQ server** for communication with FL Studio scripts
- Provides a user interface for plugin control, piano-roll tools, and MP3 → MIDI transcription
- Runs audio AI models (melody, harmony, and percussion extraction)

**Folder structure**
```
controller_app/
├── ai/
│   ├── melody_transcriber.py      # CREPE + librosa transcription to MIDI
│   ├── timbre_descriptor.py       # MFCC/spectral feature → plugin hints
│   └── stems_simple.py            # Optional HPSS for harmonic/percussive split
├── ipc/
│   ├── server.py                  # ZeroMQ REP server with strict JSON schema
│   ├── schema.py                  # Pydantic models for IPC messages
│   └── __init__.py
├── midi/
│   └── vmidi.py                   # Virtual MIDI (loopMIDI) fallback
├── ui/
│   ├── main_window.py             # PySide6 MainWindow + tabs
│   └── components.py              # Reusable widgets
├── tests/
│   ├── test_ipc.py
│   └── test_transcriber.py
└── packaging/
    └── build.ps1                  # PyInstaller build script
```

### 2) `fl_scripts` — FL Studio Integration
Python scripts placed inside FL Studio’s user script folders.

**Structure**
```
fl_scripts/
├── controller/                    # FL MIDI Controller Script
│   ├── main.py
│   ├── ipc_client.py
│   ├── device_Definition.py
│   └── NOTES.md
├── pianoroll/                     # Piano Roll Scripts
│   ├── insert_notes_from_json.py
│   ├── export_notes_to_json.py
│   ├── helpers.py
│   └── NOTES.md
└── shared/
    ├── message_schemas.py
    └── utils.py
```

---

## ✨ Features

### 🎹 FL Studio Integration
- **Channels & Plugins**: enumerate, select, and modify plugin parameters
- **Transport Control**: play, stop, record, pattern select
- **Mixer Control**: volume, pan per track
- **Piano Roll Insert/Export**: add notes programmatically or export to JSON

### 🎧 AI Audio Understanding
- **MP3/WAV Transcription**: convert an audio clip into melody, bass, chords, percussion layers
- **MIDI Export**: save as multi-track MIDI using PrettyMIDI
- **Timbre Analysis**: derive MFCC/spectral profiles to suggest plugin tweaks

### 🖥️ GUI
- Connection status
- Plugin parameter grid with real-time knobs
- Piano Roll preview
- MP3/WAV transcribe panel with **Send to FL** and **Export MIDI** actions
- Optional **loopMIDI** fallback mode

---

## ⚙️ Installation

### 1) Prerequisites
- **Windows 11 x64**
- **Python 3.11**
- **FL Studio 21.2 or later** with scripting enabled
- (Optional) loopMIDI for virtual MIDI
- Microsoft C++ Redistributables (2022+)

### 2) Clone and Install
```bash
git clone https://github.com/yourname/fl-ai-producer.git
cd fl-ai-producer
pip install -r controller_app/requirements.txt
```

### 3) Reconcile Repository Structure
Before running the application, ensure all required files are present:
```bash
python tools/audit_repo.py --fix
```

This will verify the repository structure against the architecture defined in this README and create any missing files with minimal valid implementations.

### 4) Install FL Scripts
Copy the script folders:

**Controller Script**
```
%USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\FL-AI-Producer\
```

**Piano Roll Scripts**
```
%USERPROFILE%\Documents\Image-Line\FL Studio\Scripts\Piano roll\FL-AI-Producer\
```

Restart FL Studio → Options → MIDI Settings → enable the device **FL-AI-Producer** (if applicable) and check the Script Output window.

---

## 🚀 Usage

### 1) Launch the Controller App
```bash
python controller_app/app.py
```
You should see `IPC listening on 127.0.0.1:5555` in the console and the GUI should open.

### 2) Verify Connection
In FL Studio, open **View → Script Output**; the controller script should log a successful connection.

### 3) Control Plugins
- Select a channel → plugin → adjust parameters from the GUI.
- Changes should reflect in FL Studio in real time.

### 4) Generate Notes
- In the **AI** tab, choose an MP3/WAV file.
- Click **Transcribe** → preview layers → **Send to FL**.
- In FL Studio Piano Roll menu → **Script → FL-AI-Producer → Insert from JSON**.
- Alternatively, **Export MIDI** and import into FL Studio manually.

### 5) Use the AI Assistant
The **AI Assistant** tab provides natural language control over FL Studio via OpenAI or local models (Ollama).

**Configuration**:
- **OpenAI**: Set your API key in the **API Key** field. The app uses `gpt-4o-mini` by default.
- **Ollama (Local)**: Ensure Ollama is running at `http://127.0.0.1:11434` with a model installed (e.g., `llama3.1`).
- **Auto mode**: Tries OpenAI first (if key is set), otherwise falls back to Ollama.

**Privacy Note**: When using OpenAI, your prompts and project metadata (channel names, parameter values) are sent to OpenAI's API. When using Ollama, all processing happens locally on your machine—no data leaves your computer.

**Quick Start**:
1. Select a provider (Auto/OpenAI/Ollama) and configure credentials.
2. Use **"Load Demo Prompt"** dropdown to load pre-built recipes (e.g., "Design a serum pluck").
3. Click **"Preview Plan"** to see what the AI will do (dry-run mode).
4. Click **"Apply Plan"** to execute changes in FL Studio.

**Example Prompts**:
- `"Set the cutoff on channel 0 to 0.7"`
- `"Create a C major chord on channel 1"`
- `"Start playback"`

For detailed recipes and step-by-step examples, see **[demos/README_AI_RECIPES.md](demos/README_AI_RECIPES.md)**.

### 6) Optional VMIDI Mode
If direct FL API is unavailable, enable **Virtual MIDI Mode** and map CCs to plugin parameters using FL’s **Link to Controller…** function. The app exposes a documented CC map.

---

## 🔒 Security & Privacy

### API Key Storage
- **API keys are stored in memory only** during runtime—they are never written to disk by the application.
- Keys can be provided via:
  1. The UI input field (stored in memory for the session)
  2. Environment variables (e.g., `OPENAI_API_KEY`)
  3. **Optional `.env` file** in the repository root (add to `.gitignore` to prevent accidental commits)

⚠️ **Never commit API keys to version control.** Always add `.env` to your `.gitignore` file.

### Data Privacy
- **OpenAI**: When using OpenAI models, your queries and FL Studio metadata (channel names, parameter values) are sent to OpenAI's API. Review [OpenAI's privacy policy](https://openai.com/policies/privacy-policy) for details.
- **Ollama (Local)**: All processing happens locally on your machine. No data is sent to external servers.

### Recommended Practices
1. Use environment variables or `.env` files for API keys—avoid hardcoding
2. Rotate API keys periodically
3. Use Ollama for sensitive projects that should not leave your machine
4. Review the [AI Assistant README](controller_app/ai/AGENT_README.md) for details on tool execution safeguards

### CLI Tools
Check your provider configuration:
```bash
python -m controller_app.ai.agent --provider-check
```

Run self-tests:
```bash
python -m controller_app.ai.agent --selftest
```

---

## 🧪 Testing
Run all unit tests locally:
```bash
pytest -v
```
- `test_ipc.py` spins up the ZeroMQ server and round-trips mock requests.
- `test_transcriber.py` generates synthetic audio to verify AI transcription.

Tests that require FL-specific modules use mocks and will skip gracefully when FL is not present.

---

## 📦 Building the Executable
To build a stand-alone Windows binary:
```powershell
cd controller_app/packaging
.\build.ps1
```
This runs PyInstaller and produces `fl-ai-producer.exe` with Qt and ZeroMQ included.  
See the GitHub Actions workflow (`.github/workflows/ci.yml`) for CI build automation.

---

## 🧰 Development Notes

- **IPC Protocol**: JSON over ZeroMQ REQ/REP; validated via Pydantic models (`controller_app/ipc/schema.py` and mirrored in `fl_scripts/shared/message_schemas.py`).
- **Message Types**: `ping`, `list_state`, `get_params`, `set_param`, `transport`, `mixer`, `channel`, `set_note_batch`, `apply_pianoroll_notes`.
- **Parameter Scaling**: normalized 0–1 externally; mapped to plugin-specific units internally. Values are clamped and can be smoothed (EMA) to avoid zipper noise.
- **Piano Roll Scripting**: `flpianoroll` is used for insertion/export; ensure scripts are launched from the Piano Roll Script menu (not the MIDI script host).
- **Threading**: GUI and ZeroMQ server run on separate threads. Avoid blocking calls in the UI thread.
- **Mock Mode**: When FL APIs are not available, dummy objects provide safe fallbacks for tests and local development.
- **Audio Stack**: CREPE (F0), librosa (chroma/onsets/HPSS), PrettyMIDI (export). Audio is resampled to 16 kHz mono for analysis by default.

---

## 🗂️ Repository Map (Top Level)
```
.
├── controller_app/
├── fl_scripts/
├── .github/workflows/ci.yml
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## 🛠️ Troubleshooting

### General Issues
- **Firewall/Port**: Ensure port **5555** on localhost is not blocked.
- **No Connection in FL**: Verify script paths, restart FL Studio, check **View → Script Output** for errors.
- **CREPE/Tensor backends**: If installation fails, prefer the CPU variant or switch to the alternative (TensorFlow ↔ PyTorch) specified in `requirements.txt`.
- **Audio Codecs**: For MP3 support, ensure `pydub` with FFmpeg or use WAV during testing.
- **No Knob Movement**: Confirm you selected the correct channel/plugin; some plugins expose parameters differently—use the parameter **name search** in the UI.
- **VMIDI**: If ports are missing, (1) create a port in loopMIDI, (2) restart the app, (3) link parameters in FL Studio via **Link to Controller…**.

### AI Assistant Issues
- **"OpenAI API key is not set"**: 
  - Enter your OpenAI API key in the **API Key** field (get one at https://platform.openai.com/api-keys)
  - Or switch to **Ollama** for local models (no API key required)
  
- **"OpenAI API error: Unauthorized" or "Invalid API key"**:
  - Your API key may be expired or incorrect
  - Generate a new key at https://platform.openai.com/api-keys
  - Ensure the key starts with `sk-` and is copied completely
  
- **"Ollama connection failed" or "Model not found"**:
  - Ensure Ollama is installed and running: `ollama serve`
  - Check that the Ollama host is correct (default: `http://127.0.0.1:11434`)
  - Install a model if missing: `ollama pull llama3.1`
  - Verify the model name matches what's in the **Model** field
  
- **"Preview Plan" shows no actions**:
  - The AI may not understand the prompt—try being more specific
  - Reference tool names explicitly: `list_state`, `set_param`, `set_note_batch`, etc.
  - Use the **"Load Demo Prompt"** dropdown for working examples
  
- **Parameters didn't change after applying plan**:
  - Check that the target channel has a plugin loaded
  - Use `get_params` in your prompt first to see available parameters
  - Some plugins don't expose all parameters to FL Studio's scripting API

---

## ❓ FAQ

**Q: Can this control third‑party VSTs?**  
A: Yes—provided the plugin exposes parameters to FL Studio. Values are set via `plugins.setParamValue` and should work for most VST/VST3 plugins.

**Q: Does it write automation clips?**  
A: The controller sets parameter values in real time. You can record automation by enabling FL Studio’s recording and moving parameters via the app.

**Q: Will it extract exact synth patches from audio?**  
A: It provides **timbre hints** (filters/envelopes) to get you close. Exact patch‑matching is not guaranteed and often requires manual tweaking.

**Q: Can I use this without FL’s Python scripting?**  
A: Yes, via **Virtual MIDI Mode**, but with reduced features (manual CC mapping, MIDI import).

---

## 📜 License
Choose a license and place it as `LICENSE` in the repository (MIT is a common default).

---

## 🙌 Acknowledgments
- Image-Line for FL Studio and scripting APIs
- CREPE, librosa, PrettyMIDI authors/maintainers
- loopMIDI by Tobias Erichsen

---

## 🔀 Legacy Option: FL Studio 9 (VMIDI-only)
If you need FL Studio 9 compatibility, use a separate branch (e.g., `fl9-legacy`) with **virtual MIDI only** (no FL Python API). The app will:
- Send notes/CC via a virtual MIDI port
- Export Standard MIDI Files for manual import
- Provide a “CC Mapping Profile” system
- Include a `README_FL9.md` explaining explicit limitations
