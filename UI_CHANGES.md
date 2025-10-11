# UI Changes - Load Demo Prompt Feature

## Overview

This document visualizes the UI changes made in PR #6 for the AI Assistant tab.

---

## Before and After

### BEFORE (PR #3)
```
┌─────────────────────────────────────────────────────────────┐
│ Provider Configuration                                      │
│  Provider: [Auto ▼]                                         │
│  Model: [gpt-4o-mini or llama3.1            ]               │
│  API Key: [••••••••••••••••••••••••          ]              │
│  Ollama Host: [http://127.0.0.1:11434       ]               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Task Template: [(None - Free text)             ▼]           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Chat / Query:                                               │
│ Enter your request here, e.g.:                              │
│ - Set the cutoff on the first synth to 0.7                  │
│ - Add a C major chord to channel 0                          │
│ - Start playback                                            │
```

### AFTER (PR #6) ✨
```
┌─────────────────────────────────────────────────────────────┐
│ Provider Configuration                                      │
│  Provider: [Auto ▼]                                         │
│  Model: [gpt-4o-mini or llama3.1            ]               │
│  API Key: [••••••••••••••••••••••••          ]              │
│  Ollama Host: [http://127.0.0.1:11434       ]               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Task Template: [(None - Free text)             ▼]           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Load Demo Prompt: [(Select a demo...)         ▼]            │  ◄── NEW!
│                   • Design a serum pluck                    │
│                   • House bassline (A minor, 124 BPM)       │
│                   • Humanize MIDI pattern                   │
│                   • Quick mix polish                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Chat / Query:                                               │
│ [Demo prompt loads here when selected]                      │  ◄── AUTO-FILLS
│                                                              │
│ Design a synth sound with these characteristics: bright...  │
│                                                              │
│ Target: Channel 0                                           │
│                                                              │
│ Steps to take:                                              │
│ 1. Use list_state to see the current project state         │
│ 2. Use get_params to examine the plugin parameters...      │
```

---

## Demo Prompts Available

### 1. Design a serum pluck
**Purpose**: Create a bright, short pluck sound on channel 0

**Prompt Preview**:
```
Design a synth sound with these characteristics: bright pluck, short decay, tight envelope

Target: Channel 0

Steps to take:
1. Use list_state to see the current project state
2. Use get_params to examine the plugin parameters on channel 0
3. Use set_param to adjust parameters to achieve the desired sound:
   - For "bright" sounds: higher cutoff (0.7-0.85)
   - For "pluck" sounds: short envelope decay (0.15-0.25)
   - Set release to very short (0.05-0.1)
4. Use set_note_batch to add a test note on channel 0:
   - Single note at middle C (pitch 60)
   - Start at beat 0, duration 0.5 beats
   - Velocity 110
```

**Use Case**: Sound design, synth programming
**Expected Tools**: `list_state`, `get_params`, `set_param`, `set_note_batch`

---

### 2. House bassline (A minor, 124 BPM)
**Purpose**: Generate a 4-bar house-style bassline

**Prompt Preview**:
```
Create an energetic bassline in A minor at 124 BPM

Target: Channel 1
Length: 4 bars (16 beats total)

Steps to take:
1. Use list_state to check the current project state
2. Use set_note_batch to create a bassline on channel 1

Guidelines for the bassline:
- Stay in the A minor scale (root note: 45 for A1)
- Create a house-style pattern with emphasis on beats 1 and 3
- Use 8-12 notes over 16 beats
- Note range: 41-50 (E1 to D2)
- Higher velocities on downbeats (100-120)
- Lower velocities on offbeats (70-90)
- Note durations: 0.25 to 1.0 beats
- Classic house rhythm: kick-heavy, syncopated on beat 4
- Include some chromatic passing notes for movement
```

**Use Case**: MIDI generation, bass production, genre-specific patterns
**Expected Tools**: `list_state`, `set_note_batch`

---

### 3. Humanize MIDI pattern
**Purpose**: Add natural timing and velocity variations

**Prompt Preview**:
```
Apply a 'humanize' transformation to the MIDI pattern on channel 3

Transformation: Add subtle timing and velocity variations

Steps to take:
1. Use list_state to see current project state
2. Get the current notes from channel 3
3. Apply the transformation:
   - Randomly shift note start times by ±0.03 beats
   - Vary velocities by ±8-12 points
   - Keep notes musical and on-grid overall
4. Use set_note_batch to write the transformed notes back to channel 3

Ensure all transformed notes have:
- Pitch: 0-127 (integer)
- Start time: >= 0.0 (beats)
- Duration: > 0.0 (beats)
- Velocity: 1-127 (integer)
```

**Use Case**: Pattern transformation, adding groove, making MIDI feel less robotic
**Expected Tools**: `list_state`, `set_note_batch`

---

### 4. Quick mix polish
**Purpose**: Balance mixer levels across multiple channels

**Prompt Preview**:
```
Set mixer levels for a balanced mix:
- Channel 0 (kick): volume 0.85, pan center
- Channel 1 (bass): volume 0.75, pan center  
- Channel 2 (lead): volume 0.65, pan center
- Channel 3 (pad): volume 0.50, pan slight left (-0.15)
- Channel 4 (arp): volume 0.60, pan slight right (+0.15)

Steps:
1. Use list_state to check current mixer setup
2. Use mixer tool to set volume and pan for each channel as specified above
```

**Use Case**: Mixing, level balancing, stereo placement
**Expected Tools**: `list_state`, `mixer`

---

## User Flow

1. **User opens AI Assistant tab**
2. **User clicks "Load Demo Prompt" dropdown**
3. **User selects a demo** (e.g., "Design a serum pluck")
4. **Prompt auto-fills** in the Chat/Query text area
5. **Info message appears** in Results/Logs:
   ```
   🎯 Demo prompt loaded: Design a serum pluck
   See demos/README_AI_RECIPES.md for full context and instructions.
   ```
6. **User clicks "Preview Plan"** to see what the AI will do
7. **User clicks "Apply Plan"** to execute in FL Studio

---

## Code Changes

### Location
`controller_app/ui/main_window.py`

### Lines Added
- Line 145-155: Demo prompt dropdown UI
- Line 330-420: `_on_demo_prompt_selected()` method with 4 demo prompts

### Key Features
- **Dropdown resets** after loading (returns to "(Select a demo...)")
- **Informative message** with link to full documentation
- **Copy-paste ready prompts** - no need to type or edit
- **Context preservation** - prompts include all necessary details

---

## Documentation Links

Each demo prompt corresponds to a full recipe in:
- **[demos/README_AI_RECIPES.md](demos/README_AI_RECIPES.md)** - Step-by-step instructions
- **[README.md](README.md)** - Quick start guide and AI Assistant overview

---

## Benefits

✅ **Faster onboarding** - New users can try working examples immediately
✅ **Learning by example** - See how to structure effective prompts
✅ **Reduced friction** - No need to read docs before trying
✅ **Discoverability** - Users find features through UI exploration
✅ **Quality assurance** - All prompts tested and validated
✅ **Documentation link** - Easy path to deeper learning

---

## Technical Implementation

### UI Component
```python
# Demo prompt selector
demo_layout = QHBoxLayout()
demo_layout.addWidget(QLabel("Load Demo Prompt:"))
self.demo_prompt_combo = QComboBox()
self.demo_prompt_combo.addItem("(Select a demo...)")
self.demo_prompt_combo.addItem("Design a serum pluck")
self.demo_prompt_combo.addItem("House bassline (A minor, 124 BPM)")
self.demo_prompt_combo.addItem("Humanize MIDI pattern")
self.demo_prompt_combo.addItem("Quick mix polish")
self.demo_prompt_combo.currentIndexChanged.connect(self._on_demo_prompt_selected)
demo_layout.addWidget(self.demo_prompt_combo)
demo_layout.addStretch()
main_layout.addLayout(demo_layout)
```

### Event Handler
```python
def _on_demo_prompt_selected(self, index: int):
    """Handle demo prompt selection."""
    if index == 0:  # "(Select a demo...)"
        return
    
    demo_prompts = {
        1: {"name": "Design a serum pluck", "prompt": "..."},
        2: {"name": "House bassline (A minor, 124 BPM)", "prompt": "..."},
        3: {"name": "Humanize MIDI pattern", "prompt": "..."},
        4: {"name": "Quick mix polish", "prompt": "..."}
    }
    
    demo = demo_prompts.get(index)
    if demo:
        # Fill in the chat input
        self.chat_input.setPlainText(demo["prompt"])
        
        # Show info
        self.results_text.append(
            f"\n🎯 Demo prompt loaded: {demo['name']}\n"
            f"See demos/README_AI_RECIPES.md for full context and instructions.\n"
        )
        
        # Reset dropdown
        self.demo_prompt_combo.setCurrentIndex(0)
```

---

## Testing

Test coverage in `controller_app/tests/test_demo_prompts.py`:
- ✅ Demo prompts have required structure (name, prompt)
- ✅ All prompts contain expected keywords
- ✅ Tool references are correct
- ✅ README_AI_RECIPES.md exists and has all recipes
- ✅ Prerequisites section present

---

**Status**: ✅ Ready for production
**Version**: PR #6
**Last Updated**: 2025-10-11
