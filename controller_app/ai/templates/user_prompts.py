"""
User Prompt Templates for Music Tasks

Provides pre-built prompt templates for common music production tasks.
Each template generates a structured prompt that the AI agent can interpret
to perform specific DAW operations.
"""
from typing import Dict, Any, List, Optional


def design_synth_prompt(
    style_tags: str,
    channel_ref: str = "0",
    add_test_note: bool = True
) -> Dict[str, Any]:
    """
    Generate a prompt for designing a synth sound.
    
    Args:
        style_tags: Style description (e.g., "dark pluck, detuned, short decay")
        channel_ref: Target channel reference (default: "0")
        add_test_note: Whether to add a test MIDI note (default: True)
        
    Returns:
        Dictionary with prompt and metadata
    """
    prompt = f"""Design a synth sound with these characteristics: {style_tags}

Target: Channel {channel_ref}

Steps to take:
1. Use list_state to see the current project state
2. Use get_params to examine the plugin parameters on channel {channel_ref}
3. Use set_param to adjust parameters to achieve the desired sound:
   - For "dark" sounds: lower cutoff (0.2-0.5)
   - For "bright" sounds: higher cutoff (0.6-0.9)
   - For "pluck" sounds: short envelope decay (0.1-0.3)
   - For "pad" sounds: long envelope (0.6-0.9)
   - For "detuned" sounds: adjust detune/unison parameters (0.5-0.7)
"""
    
    if add_test_note:
        prompt += f"""4. Use set_note_batch to add a test note on channel {channel_ref}:
   - Single note at middle C (pitch 60)
   - Start at beat 0, duration 1 beat
   - Velocity 100
"""
    
    return {
        "prompt": prompt,
        "category": "sound_design",
        "tool_calls_expected": ["list_state", "get_params", "set_param"],
        "parameters": {
            "style_tags": style_tags,
            "channel_ref": channel_ref,
            "add_test_note": add_test_note
        }
    }


def make_melody_prompt(
    key: str = "C",
    scale: str = "major",
    tempo: Optional[int] = None,
    mood: str = "happy",
    channel_ref: str = "0",
    num_bars: int = 4
) -> Dict[str, Any]:
    """
    Generate a prompt for creating a melody.
    
    Args:
        key: Musical key (e.g., "C", "D#", "Bb")
        scale: Scale type (e.g., "major", "minor", "pentatonic")
        tempo: BPM (if None, uses project tempo)
        mood: Mood description (e.g., "happy", "sad", "energetic")
        channel_ref: Target channel reference
        num_bars: Number of bars (4 beats each)
        
    Returns:
        Dictionary with prompt and metadata
    """
    # Define scale patterns (intervals from root)
    scale_patterns = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "pentatonic": [0, 2, 4, 7, 9],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11]
    }
    
    # Get root note (C = 60)
    note_map = {
        "C": 60, "C#": 61, "Db": 61, "D": 62, "D#": 63, "Eb": 63,
        "E": 64, "F": 65, "F#": 66, "Gb": 66, "G": 67, "G#": 68,
        "Ab": 68, "A": 69, "A#": 70, "Bb": 70, "B": 71
    }
    root_note = note_map.get(key, 60)
    
    tempo_info = f"at {tempo} BPM" if tempo else "using the project tempo"
    
    prompt = f"""Create a {mood} melody in {key} {scale} {tempo_info}

Target: Channel {channel_ref}
Length: {num_bars} bars (16 beats total)

Steps to take:
1. Use list_state to check the current project state
2. Use set_note_batch to create a melody on channel {channel_ref}

Guidelines for the melody:
- Stay in the {key} {scale} scale
- Root note: {root_note} (MIDI note number)
- Create {num_bars * 4} to {num_bars * 8} notes over {num_bars * 4} beats
- For "{mood}" mood:
"""
    
    if mood.lower() in ["happy", "upbeat", "energetic"]:
        prompt += """  - Use mostly major intervals
  - Higher note velocities (90-120)
  - More rhythmic variety with shorter notes
  - Jump between scale degrees
"""
    elif mood.lower() in ["sad", "melancholy", "dark"]:
        prompt += """  - Use minor intervals and lower register
  - Lower note velocities (60-90)
  - Longer, sustained notes
  - Stepwise motion
"""
    else:
        prompt += """  - Mix of intervals for variety
  - Medium velocities (70-100)
  - Balance between steps and leaps
"""
    
    prompt += f"""- Note durations: 0.25 to 2.0 beats
- Velocity range: 60-127
- Ensure notes don't overlap (adjust start times)
"""
    
    return {
        "prompt": prompt,
        "category": "melody_generation",
        "tool_calls_expected": ["list_state", "set_note_batch"],
        "parameters": {
            "key": key,
            "scale": scale,
            "tempo": tempo,
            "mood": mood,
            "channel_ref": channel_ref,
            "num_bars": num_bars,
            "root_note": root_note
        }
    }


def recreate_instrument_prompt(
    timbre_analysis: Dict[str, Any],
    target_channel: str = "0"
) -> Dict[str, Any]:
    """
    Generate a prompt for recreating an instrument from audio analysis.
    
    Args:
        timbre_analysis: Dictionary with audio analysis results
            Expected keys: brightness, noisiness, attack_time, sustain_level
        target_channel: Target channel reference
        
    Returns:
        Dictionary with prompt and metadata
    """
    brightness = timbre_analysis.get("brightness", 0.5)
    noisiness = timbre_analysis.get("noisiness", 0.3)
    attack_time = timbre_analysis.get("attack_time", 0.1)
    sustain_level = timbre_analysis.get("sustain_level", 0.7)
    
    prompt = f"""Recreate an instrument based on audio analysis results

Target: Channel {target_channel}

Audio characteristics:
- Brightness: {brightness:.2f} (0=dark, 1=bright)
- Noisiness: {noisiness:.2f} (0=pure, 1=noisy)
- Attack time: {attack_time:.2f} (0=immediate, 1=slow)
- Sustain level: {sustain_level:.2f} (0=short, 1=sustained)

Steps to take:
1. Use list_state to see the current project and plugin on channel {target_channel}
2. Use get_params to examine available parameters
3. Use set_param to configure the plugin based on the analysis:
   
   For filter/cutoff (if available):
   - Brightness {brightness:.2f} → cutoff around {brightness:.2f}
   
   For envelope attack (if available):
   - Attack time {attack_time:.2f} → attack around {attack_time:.2f}
   
   For envelope sustain (if available):
   - Sustain level {sustain_level:.2f} → sustain around {sustain_level:.2f}
   
   For noise/texture parameters (if available):
   - Noisiness {noisiness:.2f} → adjust noise mix or similar parameter
   
4. Optionally use mixer tool to adjust EQ or levels if needed
"""
    
    return {
        "prompt": prompt,
        "category": "instrument_recreation",
        "tool_calls_expected": ["list_state", "get_params", "set_param", "mixer"],
        "parameters": {
            "timbre_analysis": timbre_analysis,
            "target_channel": target_channel,
            "brightness": brightness,
            "noisiness": noisiness,
            "attack_time": attack_time,
            "sustain_level": sustain_level
        }
    }


def remix_pattern_prompt(
    transformation: str,
    channel_ref: str = "0",
    selection_range: Optional[tuple] = None
) -> Dict[str, Any]:
    """
    Generate a prompt for remixing/transforming a MIDI pattern.
    
    Args:
        transformation: Type of transformation
            ("humanize", "invert", "reverse", "change_rhythm", "transpose")
        channel_ref: Target channel reference
        selection_range: Optional (start_beat, end_beat) tuple for selection
        
    Returns:
        Dictionary with prompt and metadata
    """
    range_text = ""
    if selection_range:
        start, end = selection_range
        range_text = f" from beat {start} to {end}"
    
    transformations = {
        "humanize": {
            "desc": "Add subtle timing and velocity variations",
            "steps": """- Randomly shift note start times by ±0.05 beats
- Vary velocities by ±5-15 points
- Keep notes musical and on-grid overall"""
        },
        "invert": {
            "desc": "Invert the melodic intervals",
            "steps": """- Find the average pitch of all notes
- Invert each note around that center pitch
- Keep all notes in valid MIDI range (0-127)"""
        },
        "reverse": {
            "desc": "Reverse the note sequence in time",
            "steps": """- Reverse the order of notes
- Adjust start times so the pattern plays backwards
- Maintain note durations"""
        },
        "change_rhythm": {
            "desc": "Modify rhythmic patterns",
            "steps": """- Identify current note timing patterns
- Apply rhythmic transformation (e.g., swing, double-time, triplets)
- Keep pitches the same"""
        },
        "transpose": {
            "desc": "Shift all notes up or down",
            "steps": """- Add or subtract semitones from all note pitches
- Keep all notes in valid MIDI range (0-127)
- Maintain rhythm and velocity"""
        }
    }
    
    trans_info = transformations.get(transformation, {
        "desc": "Transform the pattern",
        "steps": "- Apply the specified transformation"
    })
    
    prompt = f"""Apply a '{transformation}' transformation to the MIDI pattern{range_text}

Target: Channel {channel_ref}
Transformation: {trans_info['desc']}

Steps to take:
1. Use list_state to see current project state
2. Get the current notes from channel {channel_ref}
   (Note: In a full implementation, we'd read existing notes from the channel)
3. Apply the transformation:
{trans_info['steps']}
4. Use set_note_batch to write the transformed notes back to channel {channel_ref}

Ensure all transformed notes have:
- Pitch: 0-127 (integer)
- Start time: >= 0.0 (beats)
- Duration: > 0.0 (beats)
- Velocity: 1-127 (integer)
"""
    
    return {
        "prompt": prompt,
        "category": "pattern_remix",
        "tool_calls_expected": ["list_state", "set_note_batch"],
        "parameters": {
            "transformation": transformation,
            "channel_ref": channel_ref,
            "selection_range": selection_range
        }
    }


def get_all_templates() -> Dict[str, callable]:
    """
    Get all available template functions.
    
    Returns:
        Dictionary mapping template names to functions
    """
    return {
        "design_synth": design_synth_prompt,
        "make_melody": make_melody_prompt,
        "recreate_instrument": recreate_instrument_prompt,
        "remix_pattern": remix_pattern_prompt
    }


def get_template_names() -> List[str]:
    """
    Get list of available template names.
    
    Returns:
        List of template names
    """
    return list(get_all_templates().keys())
