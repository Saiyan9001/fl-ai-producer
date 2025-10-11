# 🎯 AI Recipe Book — End-to-End Examples

This guide provides **step-by-step AI assistant recipes** for common music production tasks in FL Studio. Each recipe demonstrates how to use natural language prompts to accomplish real-world goals.

---

## 📋 Prerequisites

Before using these recipes:

1. **Configure your AI provider** in the AI Assistant tab:
   - Set your **OpenAI API key** (for GPT models), or
   - Set your **Ollama host** (for local models like `llama3.1`)
2. **Launch FL Studio** with the FL-AI-Producer controller script installed
3. **Verify connection** — check `View → Script Output` in FL Studio
4. **Start the Controller App** — run `python controller_app/app.py`

---

## 🎹 Recipe 1: Design a Serum Pluck in 3 Steps

**Goal**: Create a bright, short pluck sound on channel 0.

### Step 1: Load the Preset Prompt
In the **AI Assistant** tab, select **"Load Demo Prompt"** → **"Design a serum pluck"** from the dropdown.

Or enter manually:
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

### Step 2: Preview the Plan
Click **"Preview Plan"**. The AI will analyze your request and show proposed actions:
- ✅ Read project state
- ✅ Get plugin parameters on channel 0
- ✅ Set cutoff to ~0.8
- ✅ Set decay to ~0.2
- ✅ Set release to ~0.08
- ✅ Add test note at C5

### Step 3: Apply
Click **"Apply Plan"** to execute the changes in FL Studio. Listen to the result and iterate if needed.

**Pro Tip**: Adjust the prompt for different styles:
- `"dark pluck, detuned"` → lower cutoff, add detune
- `"metallic pluck, bright"` → high cutoff, add resonance

---

## 🎵 Recipe 2: Write a House Bassline at 124 BPM in A Minor

**Goal**: Generate a 4-bar house bassline with classic rhythm.

### Step 1: Enter the Prompt
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

### Step 2: Preview and Adjust
Click **"Preview Plan"**. If the pattern looks too sparse or dense, modify the prompt:
- For a **busier bassline**: "Create 12-16 notes over 16 beats"
- For a **simpler bassline**: "Create 4-6 notes over 16 beats, mainly on downbeats"

### Step 3: Execute and Export
1. Click **"Apply Plan"**
2. In FL Studio, open the **Piano Roll** for channel 1
3. Review the generated notes
4. If satisfied, continue building your track!

**Variations**:
- `"melodic bassline"` → more pitch movement, longer notes
- `"minimal techno bassline at 128 BPM"` → fewer notes, more repetition

---

## 🎼 Recipe 3: Recreate a Melody from MP3 (Transcribe → Quantize → Insert)

**Goal**: Extract a melody from an audio file and insert it into FL Studio.

### Step 1: Transcribe Audio
1. Switch to the **"AI"** tab (transcription tab, not AI Assistant)
2. Click **"Browse"** and select your MP3/WAV file
3. Click **"Transcribe"**
4. Wait for processing (CREPE will extract the melody layer)

### Step 2: Quantize and Preview
1. In the results panel, check **"Melody"** layer
2. Adjust **quantization** (e.g., 1/16 notes for tighter timing)
3. Click **"Preview"** to hear the extracted melody

### Step 3: Send to FL Studio
Option A — **Direct Insert**:
1. Click **"Send to FL"**
2. In FL Studio, open the target channel's **Piano Roll**
3. Go to **Piano Roll → Script → FL-AI-Producer → Insert from JSON**
4. Notes appear in the piano roll

Option B — **Export MIDI**:
1. Click **"Export MIDI"**
2. Save the `.mid` file
3. In FL Studio, drag the MIDI file to the desired channel

**Refinement with AI Assistant**:
After inserting, switch to the **AI Assistant** tab and prompt:
```
Quantize the notes on channel 2 to 1/8 note grid and fix any overlapping notes
```

---

## 🎚️ Recipe 4: Quick Mix Polish (Mixer Levels + EQ Hints)

**Goal**: Balance levels and apply basic EQ across multiple channels.

### Step 1: Check Your Project
Prompt:
```
Use list_state to show me the current mixer and channel setup
```

### Step 2: Set Mixer Levels
Prompt:
```
Set mixer levels for a balanced mix:
- Channel 0 (kick): volume 0.85, pan center
- Channel 1 (bass): volume 0.75, pan center  
- Channel 2 (lead): volume 0.65, pan center
- Channel 3 (pad): volume 0.50, pan slight left (-0.15)
- Channel 4 (arp): volume 0.60, pan slight right (+0.15)
```

### Step 3: Apply EQ Suggestions
Prompt:
```
For channel 0 (kick):
- Boost low end (filter cutoff around 0.3 if available)
- Ensure tight punch

For channel 1 (bass):
- Roll off highs slightly (cutoff around 0.6)
- Keep mids clear

For channel 2 (lead):
- Boost brightness (cutoff around 0.75)
```

**Note**: The AI will translate these into `set_param` calls if your plugins expose filter/EQ parameters. Not all plugins have the same parameter names, so the AI will adapt based on what it discovers via `get_params`.

### Step 4: Fine-Tune Manually
Use the **Plugins** tab in the Controller App to make real-time adjustments while listening.

---

## 🎛️ Recipe 5: Humanize MIDI (Add Timing & Velocity Variation)

**Goal**: Make a robotic MIDI pattern sound more natural.

### Prompt:
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

**Result**: The AI reads existing notes, applies subtle randomization, and writes them back.

---

## 🎨 Recipe 6: Multi-Step Sound Design Workflow

**Goal**: Design a custom pad sound, test it, and refine it.

### Step 1: Initial Design
```
Design a synth sound: lush pad, long attack, sustained, warm

Target: Channel 0

Steps:
1. Use list_state to see the current project state
2. Use get_params to examine the plugin parameters on channel 0
3. Use set_param to adjust parameters:
   - For "lush pad": high cutoff (0.7-0.8), long attack (0.4-0.6), long release (0.7-0.9)
   - For "warm": slightly reduce brightness, add some detuning if available
4. Use set_note_batch to add a test chord:
   - Note at pitch 60 (C4), start 0, duration 4 beats, velocity 90
   - Note at pitch 64 (E4), start 0, duration 4 beats, velocity 85
   - Note at pitch 67 (G4), start 0, duration 4 beats, velocity 85
```

### Step 2: Listen and Refine
After applying, listen in FL Studio. Then refine:
```
Adjust channel 0: increase attack to 0.7 for slower fade-in
```

### Step 3: Add Movement
```
On channel 0, adjust the filter cutoff to 0.65 to make the pad darker and more cinematic
```

---

## 💡 Tips for Writing Effective Prompts

1. **Be Specific**: Include target channels, parameter ranges, and exact values when possible
2. **Use Step-by-Step Instructions**: The AI works best with clear, ordered steps
3. **Reference Tools**: Mention tool names like `list_state`, `set_param`, `set_note_batch`, `mixer`
4. **Iterate**: Start with a broad prompt, preview, then refine with follow-up prompts
5. **Check Results**: Always preview the plan before applying to understand what will happen

---

## 🔧 Troubleshooting Recipe Prompts

**Problem**: "AI didn't understand my prompt"
- **Solution**: Break the task into smaller steps and reference specific tools

**Problem**: "Parameters didn't change"
- **Solution**: Check that the plugin on the target channel exposes the parameter you're trying to control. Use `get_params` to see available parameters.

**Problem**: "Notes weren't inserted"
- **Solution**: Verify the channel exists and has an instrument loaded. Check the Results/Logs for error messages.

**Problem**: "AI made too many changes"
- **Solution**: Use **Preview Plan** first, uncheck unwanted actions, then apply

---

## 📚 Next Steps

- Explore the **Template Selector** for pre-built prompts
- Read `controller_app/ai/AGENT_README.md` for technical details on the agent system
- Experiment with your own prompts and share your recipes!

---

**Happy producing! 🎧**
