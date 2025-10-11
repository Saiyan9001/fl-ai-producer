#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FL Studio Piano Roll Script: Export notes to JSON

Exports MIDI notes from the current piano roll to a JSON file.
"""
import json
import os

try:
    import flpianoroll
    MOCK_MODE = False
except ImportError:
    MOCK_MODE = True
    print("FL Piano Roll API not available - running in mock mode")


def export_notes_to_json(json_path: str):
    """
    Export notes from the piano roll to a JSON file.
    
    Args:
        json_path: Path where JSON file will be saved
    """
    try:
        if MOCK_MODE:
            # Generate mock data for testing
            notes = [
                {"pitch": 60, "start": 0.0, "duration": 0.5, "velocity": 100},
                {"pitch": 64, "start": 0.5, "duration": 0.5, "velocity": 100},
                {"pitch": 67, "start": 1.0, "duration": 0.5, "velocity": 100},
            ]
            print(f"Mock mode: exporting {len(notes)} mock notes")
        else:
            # Get notes from FL Piano Roll
            note_count = flpianoroll.noteCount()
            notes = []
            
            for i in range(note_count):
                note_data = flpianoroll.getNote(i)
                notes.append({
                    'pitch': note_data.pitch,
                    'start': note_data.time,
                    'duration': note_data.length,
                    'velocity': note_data.velocity
                })
        
        # Save to JSON
        data = {
            'notes': notes,
            'count': len(notes)
        }
        
        os.makedirs(os.path.dirname(json_path) or '.', exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Successfully exported {len(notes)} notes to {json_path}")
        
    except Exception as e:
        print(f"Error exporting notes: {e}")


# Entry point for FL Studio script
if __name__ == "__main__":
    # Default path for development/testing
    json_path = os.path.expanduser("~/Documents/fl-ai-producer-notes.json")
    export_notes_to_json(json_path)
