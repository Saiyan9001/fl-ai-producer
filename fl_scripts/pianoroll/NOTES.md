# FL Studio Piano Roll Scripts

## Overview
These scripts enable interaction with FL Studio's Piano Roll, allowing import/export of MIDI notes via JSON files.

## Scripts

### insert_notes_from_json.py
Reads MIDI notes from a JSON file and inserts them into the current piano roll.

**Usage:**
1. Generate notes using the FL-AI-Producer desktop app
2. Save notes to `~/Documents/fl-ai-producer-notes.json`
3. In FL Studio Piano Roll: **Tools → Scripting → FL-AI-Producer → Insert from JSON**

### export_notes_to_json.py
Exports MIDI notes from the current piano roll to a JSON file.

**Usage:**
1. Open a pattern in Piano Roll
2. In FL Studio Piano Roll: **Tools → Scripting → FL-AI-Producer → Export to JSON**
3. Notes will be saved to `~/Documents/fl-ai-producer-notes.json`

### helpers.py
Utility functions for note manipulation:
- `midi_note_to_name()` - Convert MIDI number to note name
- `note_name_to_midi()` - Convert note name to MIDI number
- `quantize_time()` - Snap times to grid
- `transpose_notes()` - Transpose notes by semitones

## JSON Format

```json
{
  "notes": [
    {
      "pitch": 60,
      "start": 0.0,
      "duration": 0.5,
      "velocity": 100
    }
  ],
  "count": 1
}
```

## Installation

Copy this directory to:
```
%USERPROFILE%\Documents\Image-Line\FL Studio\Scripts\Piano roll\FL-AI-Producer\
```

Restart FL Studio to detect the scripts.
