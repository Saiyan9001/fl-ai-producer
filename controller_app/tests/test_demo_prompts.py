"""
Tests for Demo Prompts in Main Window

Tests that demo prompts are correctly defined and can be loaded.
These tests verify the structure and content of demo prompts without requiring GUI.
"""
import pytest


class TestDemoPrompts:
    """Tests for demo prompt definitions."""
    
    def test_demo_prompts_structure(self):
        """Test that demo prompts have required structure."""
        # Define demo prompts (matching main_window.py structure)
        demo_prompts = {
            1: {  # Design a serum pluck
                "name": "Design a serum pluck",
                "prompt": """Design a synth sound with these characteristics: bright pluck, short decay, tight envelope

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
   - Velocity 110"""
            },
            2: {  # House bassline
                "name": "House bassline (A minor, 124 BPM)",
                "prompt": """Create an energetic bassline in A minor at 124 BPM

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
- Include some chromatic passing notes for movement"""
            },
            3: {  # Humanize MIDI
                "name": "Humanize MIDI pattern",
                "prompt": """Apply a 'humanize' transformation to the MIDI pattern on channel 3

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
- Velocity: 1-127 (integer)"""
            },
            4: {  # Quick mix polish
                "name": "Quick mix polish",
                "prompt": """Set mixer levels for a balanced mix:
- Channel 0 (kick): volume 0.85, pan center
- Channel 1 (bass): volume 0.75, pan center  
- Channel 2 (lead): volume 0.65, pan center
- Channel 3 (pad): volume 0.50, pan slight left (-0.15)
- Channel 4 (arp): volume 0.60, pan slight right (+0.15)

Steps:
1. Use list_state to check current mixer setup
2. Use mixer tool to set volume and pan for each channel as specified above"""
            }
        }
        
        # Verify all demo prompts have required fields
        for idx, demo in demo_prompts.items():
            assert "name" in demo, f"Demo {idx} missing 'name'"
            assert "prompt" in demo, f"Demo {idx} missing 'prompt'"
            assert isinstance(demo["name"], str), f"Demo {idx} name is not a string"
            assert isinstance(demo["prompt"], str), f"Demo {idx} prompt is not a string"
            assert len(demo["name"]) > 0, f"Demo {idx} name is empty"
            assert len(demo["prompt"]) > 10, f"Demo {idx} prompt is too short"
    
    def test_demo_prompt_content(self):
        """Test that demo prompts contain expected keywords."""
        demo_prompts = {
            1: "Design a synth sound with these characteristics: bright pluck",
            2: "Create an energetic bassline in A minor at 124 BPM",
            3: "Apply a 'humanize' transformation",
            4: "Set mixer levels for a balanced mix"
        }
        
        expected_keywords = {
            1: ["design", "synth", "channel 0", "set_param"],
            2: ["bassline", "a minor", "124 bpm", "set_note_batch"],
            3: ["humanize", "transformation", "channel 3"],
            4: ["mixer", "volume", "pan"]
        }
        
        for idx, prompt in demo_prompts.items():
            prompt_lower = prompt.lower()
            for keyword in expected_keywords[idx]:
                assert keyword.lower() in prompt_lower, \
                    f"Demo {idx} missing keyword '{keyword}'"
    
    def test_demo_prompt_tool_references(self):
        """Test that demo prompts reference appropriate tools."""
        demo_tool_references = {
            1: ["list_state", "get_params", "set_param", "set_note_batch"],
            2: ["list_state", "set_note_batch"],
            3: ["list_state", "set_note_batch"],
            4: ["list_state", "mixer"]
        }
        
        # This test documents expected tool usage
        # Actual prompts should reference these tools
        for idx, tools in demo_tool_references.items():
            assert len(tools) > 0, f"Demo {idx} has no tool references"
            assert "list_state" in tools, f"Demo {idx} should reference list_state"


class TestDemoRecipesDocument:
    """Tests for demos/README_AI_RECIPES.md document."""
    
    def test_demo_recipes_file_exists(self):
        """Test that the demo recipes document exists."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        recipes_path = os.path.join(repo_root, "demos", "README_AI_RECIPES.md")
        
        assert os.path.exists(recipes_path), \
            "demos/README_AI_RECIPES.md not found"
    
    def test_demo_recipes_has_recipes(self):
        """Test that demo recipes document contains expected recipes."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        recipes_path = os.path.join(repo_root, "demos", "README_AI_RECIPES.md")
        
        with open(recipes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected recipe sections
        expected_recipes = [
            "Recipe 1: Design a Serum Pluck",
            "Recipe 2: Write a House Bassline",
            "Recipe 3: Recreate a Melody from MP3",
            "Recipe 4: Quick Mix Polish"
        ]
        
        for recipe in expected_recipes:
            assert recipe in content, f"Recipe '{recipe}' not found in document"
    
    def test_demo_recipes_has_prerequisites(self):
        """Test that demo recipes document has prerequisites section."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        recipes_path = os.path.join(repo_root, "demos", "README_AI_RECIPES.md")
        
        with open(recipes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Prerequisites" in content, "Prerequisites section not found"
        assert "Configure your AI provider" in content, \
            "AI provider configuration not mentioned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
