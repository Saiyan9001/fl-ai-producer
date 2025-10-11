#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test piano roll scripts
"""
import sys
import os
import pytest
from pathlib import Path

# Add fl_scripts to path
repo_root = Path(__file__).parent.parent.parent
fl_scripts_dir = repo_root / 'fl_scripts'
if str(fl_scripts_dir) not in sys.path:
    sys.path.insert(0, str(fl_scripts_dir))

from pianoroll.helpers import (
    midi_note_to_name,
    note_name_to_midi,
    quantize_time,
    transpose_notes
)


def test_midi_note_to_name():
    """Test MIDI note number to name conversion."""
    assert midi_note_to_name(60) == "C4"
    assert midi_note_to_name(69) == "A4"
    assert midi_note_to_name(72) == "C5"
    assert midi_note_to_name(48) == "C3"


def test_note_name_to_midi():
    """Test note name to MIDI number conversion."""
    assert note_name_to_midi("C4") == 60
    assert note_name_to_midi("A4") == 69
    assert note_name_to_midi("C5") == 72


def test_midi_note_roundtrip():
    """Test roundtrip conversion between MIDI and note names."""
    for midi_num in [48, 60, 69, 72, 84]:
        note_name = midi_note_to_name(midi_num)
        converted_back = note_name_to_midi(note_name)
        assert converted_back == midi_num


def test_quantize_time():
    """Test time quantization to grid."""
    # Test 1/16 note grid (0.25)
    assert quantize_time(0.0, 0.25) == 0.0
    assert quantize_time(0.1, 0.25) == 0.0
    assert quantize_time(0.13, 0.25) == 0.25
    assert quantize_time(0.5, 0.25) == 0.5
    assert quantize_time(1.3, 0.25) == 1.25
    
    # Test 1/8 note grid (0.5)
    assert quantize_time(1.3, 0.5) == 1.5
    assert quantize_time(1.75, 0.5) == 2.0  # Changed from 1.7 to 1.75 (closer to 2.0 than 1.5)


def test_transpose_notes():
    """Test note transposition."""
    notes = [
        {"pitch": 60, "start": 0.0, "duration": 0.5, "velocity": 100},
        {"pitch": 64, "start": 0.5, "duration": 0.5, "velocity": 100},
        {"pitch": 67, "start": 1.0, "duration": 0.5, "velocity": 100},
    ]
    
    # Transpose up by 2 semitones
    transposed_up = transpose_notes(notes, 2)
    assert transposed_up[0]["pitch"] == 62
    assert transposed_up[1]["pitch"] == 66
    assert transposed_up[2]["pitch"] == 69
    
    # Transpose down by 3 semitones
    transposed_down = transpose_notes(notes, -3)
    assert transposed_down[0]["pitch"] == 57
    assert transposed_down[1]["pitch"] == 61
    assert transposed_down[2]["pitch"] == 64


def test_transpose_notes_clamping():
    """Test that transposition clamps to MIDI range."""
    # Test upper bound
    high_note = [{"pitch": 126, "start": 0.0, "duration": 0.5, "velocity": 100}]
    transposed = transpose_notes(high_note, 5)
    assert transposed[0]["pitch"] == 127  # Should be clamped to max
    
    # Test lower bound
    low_note = [{"pitch": 1, "start": 0.0, "duration": 0.5, "velocity": 100}]
    transposed = transpose_notes(low_note, -5)
    assert transposed[0]["pitch"] == 0  # Should be clamped to min


def test_transpose_preserves_other_properties():
    """Test that transposition preserves note properties other than pitch."""
    notes = [{"pitch": 60, "start": 1.5, "duration": 0.75, "velocity": 80}]
    transposed = transpose_notes(notes, 3)
    
    assert transposed[0]["start"] == 1.5
    assert transposed[0]["duration"] == 0.75
    assert transposed[0]["velocity"] == 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
