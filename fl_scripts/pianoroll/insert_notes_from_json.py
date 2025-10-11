#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FL Studio Piano Roll Script: Insert notes from JSON

Reads MIDI notes from a JSON file and inserts them into the current piano roll.
"""
import json
import os

try:
    import flpianoroll
    MOCK_MODE = False
except ImportError:
    MOCK_MODE = True
    print("FL Piano Roll API not available - running in mock mode")


def insert_notes_from_json(json_path: str):
    """
    Insert notes from a JSON file into the piano roll.
    
    Args:
        json_path: Path to JSON file containing note data
    """
    if not os.path.exists(json_path):
        print(f"Error: File not found: {json_path}")
        return
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        notes = data.get('notes', [])
        print(f"Loading {len(notes)} notes from {json_path}")
        
        if MOCK_MODE:
            print("Mock mode: would insert notes:", notes[:3], "...")
            return
        
        # Insert notes into piano roll
        for note in notes:
            pitch = note.get('pitch', 60)
            start = note.get('start', 0)
            duration = note.get('duration', 0.5)
            velocity = note.get('velocity', 100)
            
            # Use FL Piano Roll API to add note
            flpianoroll.addNote(pitch, start, duration, velocity)
        
        print(f"Successfully inserted {len(notes)} notes")
        
    except Exception as e:
        print(f"Error inserting notes: {e}")


# Entry point for FL Studio script
if __name__ == "__main__":
    # Default path for development/testing
    json_path = os.path.expanduser("~/Documents/fl-ai-producer-notes.json")
    insert_notes_from_json(json_path)
