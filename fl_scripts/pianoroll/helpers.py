#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for FL Studio Piano Roll scripts
"""


def midi_note_to_name(note_number: int) -> str:
    """
    Convert MIDI note number to note name.
    
    Args:
        note_number: MIDI note number (0-127)
        
    Returns:
        Note name (e.g., "C4", "A#5")
    """
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_number // 12) - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"


def note_name_to_midi(note_name: str) -> str:
    """
    Convert note name to MIDI note number.
    
    Args:
        note_name: Note name (e.g., "C4", "A#5")
        
    Returns:
        MIDI note number (0-127)
    """
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
             'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    
    # Parse note name
    note = note_name[:-1]
    octave = int(note_name[-1])
    
    return (octave + 1) * 12 + notes[note]


def quantize_time(time: float, grid: float = 0.25) -> float:
    """
    Quantize time to grid.
    
    Args:
        time: Time in beats
        grid: Grid size in beats (default: 1/16 note = 0.25)
        
    Returns:
        Quantized time
    """
    return round(time / grid) * grid


def transpose_notes(notes: list, semitones: int) -> list:
    """
    Transpose notes by semitones.
    
    Args:
        notes: List of note dictionaries
        semitones: Number of semitones to transpose
        
    Returns:
        Transposed notes
    """
    transposed = []
    for note in notes:
        new_note = note.copy()
        new_pitch = note['pitch'] + semitones
        # Clamp to MIDI range
        new_note['pitch'] = max(0, min(127, new_pitch))
        transposed.append(new_note)
    return transposed
