# Repository Audit Tool

## Overview

The `tools/audit_repo.py` script is a comprehensive repository structure verification and auto-fix tool for the FL-AI-Producer project. It ensures that the repository matches the architecture defined in the README and creates any missing files with minimal, working implementations.

## Features

- ✅ **Structure Verification**: Checks for presence of all expected files and directories
- ✅ **Clear Output**: Displays a formatted table with ✅/❌ status for each file
- ✅ **Auto-Fix Mode**: Creates missing files with minimal valid implementations using `--fix` flag
- ✅ **CI Integration**: Runs automatically in GitHub Actions workflow
- ✅ **Exit Codes**: Returns proper exit codes for CI/CD integration

## Usage

### Check Repository Structure

```bash
python tools/audit_repo.py
```

Output example:
```
================================================================================
FL-AI-Producer Repository Audit
================================================================================
File Path                                                    Status    
--------------------------------------------------------------------------------
.github/workflows/ci.yml                                     ✅         
.gitignore                                                   ✅         
pyproject.toml                                               ✅         
controller_app/midi/vmidi.py                                 ✅         
...
--------------------------------------------------------------------------------
Total: 26 files | Present: 26 | Missing: 0
================================================================================

✅ All expected files are present.
```

### Auto-Fix Missing Files

```bash
python tools/audit_repo.py --fix
```

This will:
1. Check all expected files
2. Create any missing files with minimal valid implementations
3. Preserve all existing files (never overwrites)
4. Create necessary parent directories

## What It Checks

The audit tool verifies 26 files across three categories:

### Root Files (4 files)
- `.github/workflows/ci.yml` - CI/CD workflow with audit and test jobs
- `.gitignore` - Git ignore patterns
- `pyproject.toml` - Python project metadata and dependencies
- `README.md` - Project documentation

### Controller App (12 files)
- `app.py` - Main application entry point
- `requirements.txt` - Python dependencies
- `ai/melody_transcriber.py` - CREPE + librosa transcription to MIDI
- `ai/timbre_descriptor.py` - MFCC/spectral feature analysis
- `ipc/server.py` - ZeroMQ REP server
- `ipc/schema.py` - Pydantic models for IPC messages
- `midi/vmidi.py` - Virtual MIDI (loopMIDI) fallback implementation
- `ui/main_window.py` - PySide6 main window with tabs
- `ui/components.py` - Reusable UI widgets
- `tests/test_ipc.py` - IPC server tests
- `tests/test_transcriber.py` - Audio transcription tests
- `packaging/build.ps1` - PyInstaller build script

### FL Scripts (10 files)
- `controller/main.py` - FL MIDI script entry points
- `controller/ipc_client.py` - ZeroMQ REQ client
- `controller/device_Definition.py` - FL device definition
- `controller/NOTES.md` - Installation guide
- `pianoroll/insert_notes_from_json.py` - Import notes from JSON to piano roll
- `pianoroll/export_notes_to_json.py` - Export notes from piano roll to JSON
- `pianoroll/helpers.py` - Piano roll utility functions
- `pianoroll/NOTES.md` - Piano roll scripts documentation
- `shared/message_schemas.py` - JSON message schemas
- `shared/utils.py` - Shared utility functions

## File Templates

The tool creates minimal but functional implementations for missing files:

### Example: Virtual MIDI Module
```python
class VirtualMIDI:
    """Virtual MIDI device handler for loopMIDI fallback."""
    
    def __init__(self, port_name: str = "FL-AI-Producer"):
        self.port_name = port_name
        self.connected = False
    
    def connect(self) -> bool:
        self.connected = True
        return self.connected
    
    def disconnect(self):
        self.connected = False
```

### Example: Piano Roll Helpers
```python
def midi_note_to_name(note_number: int) -> str:
    """Convert MIDI note number to note name."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_number // 12) - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"
```

All templates:
- Include proper docstrings
- Have Windows-safe shebangs and encoding headers
- Import gracefully with mocks for unavailable FL APIs
- Are fully functional and testable

## CI Integration

The audit tool is integrated into the GitHub Actions workflow:

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run repository audit
        run: python tools/audit_repo.py
  
  test:
    needs: audit
    # ... test steps
```

The audit job runs **before** tests, ensuring the repository structure is valid before running any tests.

## Exit Codes

- `0` - Success: All files present or successfully created with --fix
- `1` - Failure: Missing files and --fix not specified

## Installation in Workflow

The audit tool is automatically available when the repository is cloned. For new contributors:

1. Clone the repository
2. Run audit with --fix before first use:
   ```bash
   python tools/audit_repo.py --fix
   ```
3. Install dependencies:
   ```bash
   pip install -r controller_app/requirements.txt
   ```

## Testing the Audit Tool

The audit tool has its own test suite at `tools/test_audit_repo.py`:

```bash
python tools/test_audit_repo.py
```

This verifies:
- Repository root detection
- File checking logic
- Template content availability
- All expected files are present

## Implementation Details

### Structure Definition

Files are defined in the `EXPECTED_FILES` dictionary:
```python
EXPECTED_FILES = {
    "controller_app": [...],
    "fl_scripts": [...],
    "root": [...],
}
```

### Template System

Templates are stored in the `get_file_template()` function as a dictionary mapping file paths to content. This keeps all templates in one place and makes them easy to maintain.

### Safe File Creation

The `create_missing_file()` function:
- Creates parent directories if needed
- Never overwrites existing files
- Uses UTF-8 encoding
- Reports each file created

## Benefits

1. **Foundation Check**: Ensures repository structure is correct before development
2. **Onboarding**: New contributors can quickly scaffold the project
3. **CI Safety**: Catches missing files before tests run
4. **Documentation**: The audit tool serves as living documentation of the expected structure
5. **Consistency**: All developers work with the same file structure

## Maintenance

To add new files to the audit:

1. Update `EXPECTED_FILES` dictionary in `audit_repo.py`
2. Add a template in `get_file_template()` function
3. Run `python tools/test_audit_repo.py` to verify
4. Update this README if needed

## Related Files

- `tools/audit_repo.py` - Main audit script
- `tools/test_audit_repo.py` - Test suite for audit tool
- `.github/workflows/ci.yml` - CI workflow using the audit tool
- `README.md` - Project README (source of truth for architecture)
